from threading import Thread
from file_manager import FileManager
from datetime import datetime
import pickle
import traceback

f_manager = FileManager()


def get_nas_lst(select_names=()):
    lst = []
    nas_paths = list(f_manager.get_path_files()["NAS"])
    for nas_path in nas_paths:
        timestamp = int(nas_path[3].split(".")[0].split("-")[1])
        name = nas_path[0]
        date = datetime.fromtimestamp(timestamp).strftime('%Y/%m/%d %H:%M:%S')
        logins = [(login, mac) for nas in pickle.loads(f_manager.get_file(nas_path[3])) for login, mac in nas.items()]

        if select_names:
            if not name in select_names:
                continue
        lst.append((name, date, logins))
    return lst


def get_sw_lst(select_names=()):
    lst = []
    sw_paths = list(f_manager.get_path_files()["SW"])
    for sw_path in sw_paths:
        timestamp = int(sw_path[3].split(".")[0].split("-")[1])
        name = sw_path[0]
        date = datetime.fromtimestamp(timestamp).strftime('%Y/%m/%d %H:%M:%S')

        if select_names:
            if not name in select_names:
                continue

        sw_dataset = []
        for sw in pickle.loads(f_manager.get_file(sw_path[3])):
            if not sw["ports"]:
                continue
            sw_dataset.append((sw["name"], sw["host"][0], sw["ports"]))
        lst.append((name, date, sw_dataset))
    return lst


class StopThread(Exception):
    pass


class BaseSearchThread(Thread):
    def __init__(self, mac="", login="", select_nas=(), select_sw=()):
        super().__init__(daemon=True)
        self.kill_flag = False
        self.error = ""
        self.result = None
        self.nas = select_nas
        self.sw = select_sw
        self.mac = mac
        self.login = login

    def action(self):
        pass

    def kill(self):
        self.kill_flag = True

    def search_sw(self):
        res = []
        for file_name, date, payload in get_sw_lst(self.sw):

            if self.kill_flag:
                raise StopThread

            l_res = []
            for sw_name, sw_ip, sw_ports in payload:
                res_ports = []
                for mac, port in sw_ports:
                    if self.mac == mac:
                        res_ports.append((mac, port))
                if res_ports:
                    l_res.append((sw_name, sw_ip, res_ports))
            if l_res:
                res.append((file_name, date, l_res))
        return res

    def search_nas(self):
        res = []
        for file_name, date, payload in get_nas_lst(select_names=self.nas):
            if self.kill_flag:
                raise StopThread
            for login, mac in payload:
                if mac == self.mac:
                    res.append((file_name, date, (login, mac)))
                elif login == self.login:
                    res.append((file_name, date, (login, mac)))
        return res

    def run(self) -> None:
        try:
            self.action()
        except Exception:
            self.error = traceback.format_exc()


class SearchNAS(BaseSearchThread):
    def action(self) -> None:
        self.result = self.search_nas()


class SearchSW(BaseSearchThread):
    def action(self):
        self.result = self.search_sw()


class SearchSelect(BaseSearchThread):
    def action(self):
        res = []
        nas_lst = self.search_nas()
        for nas_name, nas_date, payload in nas_lst:
            self.mac = payload[1]
            sw_lst = self.search_sw()
            if sw_lst:
                res.append((nas_name, nas_date, payload, sw_lst))
            else:
                res.append((nas_name, nas_date, payload, None))
        self.result = res


class Searcher:
    def __init__(self):
        self._thread = SearchSW()

    def finalize(self):
        self._thread.kill()

    def check_running(self):
        if self._thread.is_alive():
            return
        return True

    def get_result(self):
        if self._thread.is_alive():
            return
        return self._thread.result, self._thread.error

    def only_nas(self, login="", mac="", select_nas=()):
        self._thread = SearchNAS(login=login, mac=mac, select_nas=select_nas)
        self._thread.start()

    def only_sw(self, mac="", select_sw=()):
        self._thread = SearchSW(mac=mac, select_sw=select_sw)
        self._thread.start()

    def search_select(self, mac="", login="", select_sw=(), select_nas=()):
        self._thread = SearchSelect(mac=mac, login=login, select_sw=select_sw, select_nas=select_nas)
        self._thread.start()
