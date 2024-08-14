from handler import AbstractRequestHandler
from simple_logger import Logger
from server import Server
from threading import Lock
from searchers import Searcher
import file_manager
import handler
import sw_dumper
import nas_dumper
import users_list
import time
import pickle

dump_tree_path = "all_tree.pickle"
main_locker = Lock()
logger = Logger(file="search_port_logs/log.txt", lock=main_locker)   # логер
f_manager = file_manager.FileManager()                                                  # взаимодействие с dump-файлами
sw_dump = sw_dumper.Dumper(logger=logger)                                               # создатель dump-sw
nas_dump = nas_dumper.RequestNAS(host=("127.0.0.1", 5768))                              # создатель dump-nas
search = Searcher()                                                                     # поисковик портов, логинов, mac'ов


class StreamRequestHandler(AbstractRequestHandler):
    def init_handlers(self):
        self.add_handler(0x05, self.get_nas_dbs)
        self.add_handler(0x06, self.dump_sw_dbs)
        self.add_handler(0x07, self.dump_nas_dbs)
        self.add_handler(0x08, self.get_file)
        self.add_handler(0x09, self.get_all_users)
        self.add_handler(0x10, self.delete_file)
        self.add_handler(0x11, self.search_sw)
        self.add_handler(0x12, self.get_nas_lst)
        self.add_handler(0x13, self.search_global)
        self.add_handler(0x14, self.search_get_result)
        self.add_handler(0x15, self.search_check_running)
        self.add_handler(0x16, self.search_killer_thread)
        self.add_handler(0x17, self.search_only_nas)
        self.add_handler(0x18, self.search_select)

    def search_select(self):
        logger.INFO(f"Запрос поиска, MAC={self.payload_object[0]}, LOGIN={self.payload_object[1]}", sender=self.user)
        if search.check_running():
            search.search_select(
                mac=self.payload_object[0].upper(),
                login=self.payload_object[1],
                select_nas=self.payload_object[2],
                select_sw=self.payload_object[3]
            )
            return self.send_response(handler.OPCODE_SUCCESS, payload="ok")
        return self.send_response(handler.OPCODE_LINE_BUSY, payload="Сервер занят другим процессом")

    def search_global(self):
        logger.INFO(f"Запрос поиска, MAC={self.payload_object[0]}, LOGIN={self.payload_object[1]}", sender=self.user)
        if search.check_running():
            search.search_select(mac=self.payload_object[0].upper(), login=self.payload_object[1])
            return self.send_response(handler.OPCODE_SUCCESS, payload="ok")
        return self.send_response(handler.OPCODE_LINE_BUSY, payload="Сервер занят другим процессом")

    def search_get_result(self):
        rslt = search.get_result()
        if not rslt:
            return self.send_response(handler.OPCODE_LINE_BUSY, payload="wait")
        return self.send_response(handler.OPCODE_LINE_BUSY, payload=rslt)

    def search_check_running(self):
        if search.check_running():
            return self.send_response(handler.OPCODE_SUCCESS, payload="ok")
        else:
            return self.send_response(handler.OPCODE_LINE_BUSY, payload="В данный момент времени сервер выполняет другую процедуру")

    def search_killer_thread(self):
        search.finalize()
        logger.INFO(f"Kill Thread signal (operation = Search)", sender=self.user)
        return self.send_response(handler.OPCODE_SUCCESS, payload="Процедура поиска будет прервана в ближайшее время")

    def search_only_nas(self):
        logger.INFO(f"Запрос поиска ONLY_NAS (mac={self.payload_object[0]}, login={self.payload_object[1]})", sender=self.user)
        search.only_nas(login=self.payload_object[1], mac=self.payload_object[0])
        return self.send_response(handler.OPCODE_SUCCESS, payload="ok")

    def get_nas_lst(self):
        path = self.payload_object
        try:
            nas_lst = pickle.loads(f_manager.get_file(path=path))
            logger.INFO(f"Запрос файла по пути: {path}", sender=self.user)
        except FileNotFoundError:
            logger.WARNING(f"Не удалось найти файл по пути: {path}", sender=self.user)
            return self.send_response(handler.OPCODE_NOT_FOUND, payload="Файл не найден")

        lst = []
        users = users_list.GetUsersDumpTree(dump_tree_path).get
        for nas in nas_lst:
            for login, mac in nas.items():
                user = "Не удалось найти данные"
                for carbon_user in users:
                    _login = carbon_user["login"]
                    if login == _login:
                        user = carbon_user["name"]
                        break
                lst.append((login, mac, user))
        return self.send_response(handler.OPCODE_SUCCESS, payload=lst)

    def search_sw(self):
        file_path, search_str = self.payload_object
        logger.INFO(f"Поиск <{search_str}> в dump-файле: {file_path}")
        try:
            sw_lst = pickle.loads(f_manager.get_file(path=file_path))
        except FileNotFoundError:
            logger.WARNING(f"Не удалось найти файл по пути: {file_path}")
            return self.send_response(handler.OPCODE_NOT_FOUND, payload=f"Не удалось найти файл по пути: {file_path}")

        if not search_str:
            return self.send_response(handler.OPCODE_SUCCESS, payload=sw_lst)

        searched = []
        for sw in sw_lst:
            for mac, _ in sw["ports"]:
                if search_str.upper() in mac:
                    searched.append(sw)
                    break

        return self.send_response(handler.OPCODE_SUCCESS, payload=searched)

    def get_all_users(self):
        logger.INFO("Запросил список Carbon-пользователей", sender=self.user)
        try:
            users = users_list.GetUsersDumpTree(file_path=dump_tree_path).get
        except OSError:
            logger.WARNING("Не удалось получить список Carbon-пользователей")
            return self.send_response(handler.OPCODE_NOT_SUCCESS, payload="Не удалось получить список Carbon-пользователей")
        return self.send_response(handler.OPCODE_SUCCESS, payload=users)

    def get_file(self):
        file_path = self.payload_object
        logger.INFO(f"Запросил файл по пути: {file_path}", sender=self.user)
        try:
            payload = f_manager.get_file(path=file_path)
        except FileNotFoundError:
            logger.WARNING(f"Не удалось найти файл по пути: {file_path}")
            return self.send_response(handler.OPCODE_NOT_FOUND, payload=f"Не удалось найти файл по пути: {file_path}")
        return self.send_response(handler.OPCODE_SUCCESS, bytes_payload=payload)

    def delete_file(self):
        file_path = self.payload_object
        try:
            f_manager.delete_file(path=file_path)
        except FileNotFoundError:
            logger.WARNING(f"Не удалось удалить файл по пути: {file_path}")
            return self.send_response(handler.OPCODE_NOT_FOUND, payload=f"Не удалось удалить файл по пути: {file_path}")
        logger.INFO(f"Удален файл по пути: {file_path}")
        return self.send_response(handler.OPCODE_SUCCESS, payload=f"Файл успешно удалён")

    def dump_nas_dbs(self):
        logger.INFO("Начал процесс снятия DUMP-файла", sender=self.user)
        sessions = nas_dump.get_pppoe()
        if sessions:
            serialized = pickle.dumps(sessions)
            f_manager.create_file(filename=f"nasdump-{int(time.time())}", root_path="NAS", payload=serialized)
            logger.INFO("Данные получены и записаны в DUMP-файл")
            return self.send_response(handler.OPCODE_SUCCESS, payload="Данные получены и записаны в DUMP-файл")
        else:
            logger.WARNING("DUMP файл, процесс прерван")
            return self.send_response(handler.OPCODE_NOT_SUCCESS, payload="Не удалось получить данные NAS, процесс прерван")

    def dump_sw_dbs(self):
        if sw_dump.dump_all_sw():
            return self.send_response(handler.OPCODE_SUCCESS_WAIT, payload="Процесс снятия DUMP-файла запущен, дождитесь завершения.")
        return self.send_response(handler.OPCODE_LINE_BUSY, payload="Сервер уже занят процессом снятия DUMP-файла, дождитесь завершения.")

    def get_nas_dbs(self):
        data = f_manager.get_path_files()
        logger.INFO("Запрос структуры файлов NAS_DUMP, SW_DUMP", sender=self.user)
        return self.send_response(handler.OPCODE_SUCCESS, payload=data)


server = Server(host=("", 5002), handler_class=StreamRequestHandler, logger=logger, lock=main_locker)


if __name__ == "__main__":
    server.start()
    server.join()
