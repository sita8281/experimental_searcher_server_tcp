from threading import Thread
import socket
import time
import zlib
import parsers

table_keys = {
    'cisco': (b'User Access Verification', b'..\nenable\n..\nshow mac address-table\n' + b' ' * 100),
    'zyxel': (b'User name:', b'admin\n..\nshow mac address-table all\n' + b' ' * 100),
    'dlink': (b'D-Link', b'admin\n..\nshow fdb\n' + b' ' * 100),
    'orion': (b'Login:', b'admin\n..\nshow mac-address-table l2-address\n' + b' ' * 100)
}


class StreamConnection(Thread):
    def __init__(self, queue, host, name):
        super().__init__(daemon=True)
        self.host = host
        self.name = name
        self.buffer = b''
        self.device = 'unknown'
        self.cmd = b''
        self.status = 'success'
        self.queue = queue
        self.ports_lst = []

    def run(self) -> None:
        try:
            self.connect()
            self.recv_before_timeout()
            self.check_device()
            self.recv_before_timeout()
        except OSError:
            self.status = "error"

        if self.device == "dlink":
            self.ports_lst = parsers.parser(self.buffer.decode("cp1251"))
        elif self.device == "cisco":
            self.ports_lst = parsers.cisco(self.buffer.decode("cp1251"))
        elif self.device == "zyxel":
            self.ports_lst = parsers.zyxel(self.buffer.decode("cp1251"))
        elif self.device == "orion":
            self.ports_lst = parsers.orion(self.buffer.decode("cp1251"))

        self.queue.put({
            'host': self.host,
            'name': self.name,
            'device': self.device,
            'status': self.status,
            'data': zlib.compress(self.buffer),
            'ports': self.ports_lst
        })

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(2)
        self.sock.connect(self.host)

    def check_device(self):
        for device, lst in table_keys.items():
            if lst[0] in self.buffer:
                self.device = device
                self.sock.sendall(lst[1])
                return

    def recv_before_timeout(self):
        while True:
            try:
                data_b = self.sock.recv(8192)
                if not data_b:
                    return
                self.buffer += data_b
            except socket.timeout:
                return


class RunStreamThreads(Thread):
    def __init__(self, hosts, queue):
        super().__init__(daemon=True)
        self.hosts = hosts
        self.live_threads = []
        self.queue = queue

    def run(self) -> None:
        self.run_threads()
        while True:
            time.sleep(5)
            live_count = 0
            for th in self.live_threads:
                if th.is_alive():
                    live_count += 1
                    break
            if live_count == 0:
                return

    def run_threads(self):
        for count, host in enumerate(self.hosts):
            if count % 10 == 0:
                time.sleep(2)
            th = StreamConnection(self.queue, (host[0], 23), host[1])
            th.start()
            self.live_threads.append(th)
