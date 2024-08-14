import struct
import socket
import pickle


class RequestNAS:
    def __init__(self, host: tuple):
        self.host = host
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def get_pppoe(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(1)
            self.sock.connect(self.host)
            _len = struct.unpack(">I", self.recv_chunk(4))[0]
            payload = pickle.loads(self.recv_chunk(_len))
            return payload
        except (OSError, struct.error):
            return

    def recv_chunk(self, nbytes):
        buffer = b""
        while len(buffer) < nbytes:
            data = self.sock.recv(nbytes - len(buffer))
            if not data:
                raise OSError
            buffer += data
        return buffer
