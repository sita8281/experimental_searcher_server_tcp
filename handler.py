import socket
from threading import Thread
import pickle
import struct
import traceback

OPCODE_PING = b"\xfe"
OPCODE_SUCCESS = b"\x01"
OPCODE_NOT_SUCCESS = b"\x02"
OPCODE_SUCCESS_WAIT = b"\x03"
OPCODE_SHOW_INFO = b"\x04"
OPCODE_SHOW_WARNING = b"\x05"
OPCODE_SHOW_ERROR = b"\x06"
OPCODE_NOT_FOUND = b"\xfa"
OPCODE_INTERNAL_ERROR = b"\xfb"
OPCODE_LINE_BUSY = b"\xfc"
OPCODE_UNKNOWN_REQUEST = b"\xfd"
OPCODE_LOG = b"\xff"


class AbstractRequestHandler(Thread):
    def __init__(self, parent_server, client_sock, event_logger, thread_lock, user_login, address):
        """
        :param parent_server: родительский объект сервера
        :param client_sock: объект сокета клиента
        :param event_logger: логгер событий
        :param thread_lock: блокировщик потоков
        :param user_login: логин пользователя данного обработчика
        :param address: адрес сокета
        """
        super().__init__(daemon=True)

        self.server = parent_server
        self.sock = client_sock
        self.log = event_logger
        self.lock = thread_lock
        self.user = user_login
        self.addr = address

        self.kill_flag = False
        self._buffer = b""
        self._handlers_pool = []
        self.payload_object = None
        self.sock.settimeout(30)  # максимальная длительность простоя соединения

    def init_handlers(self):
        """
        Инициализатор обработчиков запросов
        """
        pass

    def run(self) -> None:
        self.init_handlers()  # инициализация обработчиков
        self.log.INFO(message=f"подключился к серверу {self.addr}", sender=self.user)
        try:
            self.check_requests()
        except socket.timeout:
            self.close_connection(error="timeout 30s")
        except OSError:
            self.close_connection()

    def check_requests(self):
        while True:
            code = self.recv_chunk(1)  # считывание кода запроса
            if code == OPCODE_PING:  # обработка ping-запроса
                continue
            len_payload = struct.unpack(">I", self.recv_chunk(4))[0]  # считывание длины payload
            payload = self.recv_chunk(len_payload)
            self.payload_object = pickle.loads(payload)

            for handler in self._handlers_pool:
                if handler[0] == code:
                    callback_func = handler[1]
                    try:
                        response = callback_func()
                        self._sendall(response)
                    except Exception as exc:
                        err = f"Неизвестная ошибка в обработчике запросов сервера\n{traceback.format_exc()}"
                        self.log.ERROR(
                            f"Неизвестная ошибка в обработчике запросов сервера: <{traceback.format_exc()}>",
                            sender=self.user
                        )
                        self._sendall(self.send_response(OPCODE_INTERNAL_ERROR, payload=err))
                    break
            else:
                self._sendall(self.send_response(OPCODE_UNKNOWN_REQUEST, payload="Сервер не распознал данный запрос"))

    def _sendall(self, payload):
        """
        Потоко-защищённый метод отправки в сокет
        :param payload: данные в байтах
        :return:
        """
        with self.lock:
            self.sock.sendall(payload)

    def send_log(self, text):
        """
        Метод broadcast рассылки лог-события, этот метод вызывает Logger через объект сервера
        :param text:
        :return:
        """
        try:
            self._sendall(self.send_response(OPCODE_LOG, text))
        except OSError:
            pass

    def add_handler(self, code: int, func) -> None:
        """
        Добавить обработку запроса
        :param code: byte-код запроса
        :param func: метод обработчик
        :return:
        """
        self._handlers_pool.append((
            code.to_bytes(1, "big"), func
        ))

    @staticmethod
    def send_response(code: bytes, payload: object = None, bytes_payload: bytes = None) -> bytes:
        if payload is None:
            serialized = bytes_payload
        else:
            serialized = pickle.dumps(payload)
        _len = struct.pack(">I", len(serialized))
        return b"".join([code, _len, serialized])

    def recv_chunk(self, nbytes) -> bytes:
        """
        Считавать n-байт
        :param nbytes: колличество считываемых байтов
        :return:
        """
        buffer = b""
        while len(buffer) < nbytes:
            data = self.sock.recv(nbytes - len(buffer))
            if not data:
                raise OSError
            buffer += data
        if self.kill_flag:
            raise OSError
        return buffer

    def close_connection(self, error=""):
        """
        Нужно вызывать при любом завершении сокета
        :return:
        """
        self.sock.close()
        self.server.close_client(self)
        self.log.INFO(message=f"отключился от сервера. <{error}>", sender=self.user)

    def kill(self):
        self.kill_flag = True







