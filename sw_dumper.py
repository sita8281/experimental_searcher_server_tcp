import sw_poll
import queue
import threading
import file_manager
import time
import pickle
import db_sdeil


class Dumper:
    def __init__(self, logger):
        self._logger = logger  # объект обязательно передается из обработчика сервера
        self.hosts = db_sdeil.all_info()
        self._filemanager = file_manager.FileManager()
        self._queue = queue.Queue()
        self._poller = sw_poll.RunStreamThreads(self.hosts, self._queue)
        self._thread = threading.Thread()

        self.temp_dump = None

    def _run_dump(self, temp=False):
        self.temp_dump = None
        self._queue = queue.Queue()
        self._poller = sw_poll.RunStreamThreads(self.hosts, self._queue)
        self._thread = threading.Thread(target=self._polling_queue, args=(temp,), daemon=True)
        self._thread.start()
        self._poller.start()
        self._logger.INFO(
            f"\n\nПроцесс снятия DUMP-файлов запущен.."
        )

    def _is_busy(self):
        return self._thread.is_alive()

    def _polling_queue(self, temp=False):
        dump = []

        while True:
            try:
                data = self._queue.get(timeout=5)
                # print(
                #     str(data["host"]).ljust(30),
                #     data["name"].ljust(60),
                #     data["device"].ljust(15),
                #     data["status"].ljust(10),
                #     str(len(data["data"])).ljust(8)
                # )
                dump.append(data)
                self._logger.INFO(
                    f"{data['host'][0].ljust(18)}"
                    f"{data['name'].ljust(60)}"
                    "Опрос завершен."
                )
            except queue.Empty:
                if not self._poller.is_alive():
                    break

        if dump:
            if not temp:
                self._filemanager.create_file(
                    filename=f"swdump-{int(time.time())}",
                    root_path="SW",
                    payload=pickle.dumps(dump)
                )
            else:
                self.temp_dump = dump
                # print(len(self.temp_dump), "количество")
            self._logger.INFO(
                f"\n\nКоличество опрошенных хостов: {len(dump)}"
            )
        else:
            self._logger.WARNING(
                f"\n\nНе удалось собрать данные во время опроса хостов"
            )

    def dump_all_sw(self):
        """
        Запустить снятие файловой базы свитчей
        :return:
        """
        if self._is_busy():
            return
        self._run_dump()
        return True

    def temp_all_sw(self):
        """
        Запустить снятие временной базы свитчей
        :return:
        """
        if self._is_busy():
            return
        self._run_dump(temp=True)
        return True

    def get_temp_dump(self):
        """
        Получить временный список всех свитчей и их портов
        :return:
        """
        pass

