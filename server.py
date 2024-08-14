import socket
import db_sdeil
from threading import Thread

SUCCESS = b"\x01"
NOT_AUTH = b"\x02"
TIMEOUT = b"\x03"


class Server(Thread):
    def __init__(self, host, handler_class, logger, lock):
        super().__init__(daemon=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(host)
        self.sock.listen(1)

        self.host = host                    # ip, port сервера
        self.handler_class = handler_class  # обаботчик клиентов
        self.logger = logger                # простой логер событий
        self.lock = lock                    # глобальный блокировщик потоков
        self._clients = []                  # список активных клиентов

        self.logger.set_callback_log(self.broadcast_log)

    def broadcast_log(self, text: str) -> None:
        """
        Метод рассылки лог-событий всем клиентам
        :param text: Текст сообщения
        :return:
        """
        for client in self._clients:
            client.send_log(text)

    def close_client(self, client) -> None:
        """
        Закрыть соединение клиента
        :param client:
        :return:
        """
        with self.lock:
            if client in self._clients:
                client.kill()  # убить поток клиента
                self._clients.remove(client)  # удалить из списка активных соединений

    def accept_client(self) -> None:
        """
        Принять соединение от клиента
        :return:
        """
        while True:
            try:
                client_sock, client_addr = self.sock.accept()
                self.authenticate_client(client_sock, client_addr)
            except OSError:
                pass

    def authenticate_client(self, sock, addr: tuple) -> None:
        """
        Проверка логина и пароля клиента
        :param sock: Socket-объект клиента
        :param addr: Ip:Port адрес клиента
        :return:
        """
        sock.settimeout(0.2)
        db_users = db_sdeil.registered_users()
        account = [b"", b""]
        for key, _ in enumerate(account):
            while True:
                try:
                    byte_data = sock.recv(1)
                except socket.timeout:
                    sock.sendall(TIMEOUT)
                    sock.close()
                    raise OSError
                if byte_data == b"\n":
                    break
                elif byte_data == b"\r":
                    account[key] += byte_data[:-1]
                else:
                    account[key] += byte_data
        for user in db_users:
            if [user[0], user[1]] == [account[0].decode("utf-8"), account[1].decode("utf-8")]:
                client = self.handler_class(
                    parent_server=self,
                    client_sock=sock,
                    event_logger=self.logger,
                    thread_lock=self.lock,
                    user_login=user[0],
                    address=addr,
                )
                sock.sendall(SUCCESS)
                client.start()  # запуск обработчика клиента
                self._clients.append(client)  # добадление в список активных соединений
                return

        sock.sendall(NOT_AUTH)
        sock.close()

    @property
    def clients(self):
        return self._clients

    def run(self):
        """
        Запустить сервер
        :return:
        """
        if not self.host[0]:
            host = "0.0.0.0"
        else:
            host = self.host[0]
        self.logger.INFO(message=f"Listening -> {host}:{self.host[1]}", sender="server")
        self.accept_client()
