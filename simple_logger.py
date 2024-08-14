from datetime import datetime


class Logger:
    """
    Простейший логер событий, пишет в файл и имеет заглушку под callback лог
    """
    def __init__(self, file, lock):

        self._callback = None
        self._file = file
        self._lock = lock

    def _write_file(self, msg):
        with self._lock:
            try:
                with open(file=self._file, mode="a", encoding="utf-8") as file:
                    file.write(msg + "\n")
            except OSError:
                pass

    def _write_broadcast(self, msg):
        if self._callback:
            self._callback(msg)

    def _send_log(self, msg, sender, level):
        time = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        level = f"[{level}]".ljust(9)
        if not sender:
            send = f":server:"
        else:
            send = f":{sender}:"
        text = f"{time} {level} {send} {msg}"
        print(text)
        self._write_file(text)
        self._write_broadcast(text)

    def INFO(self, message: str, sender=None):
        self._send_log(message, sender, level="INFO")

    def WARNING(self, message: str, sender=None):
        self._send_log(message, sender, level="WARNING")

    def ERROR(self, message: str, sender=None):
        self._send_log(message, sender, level="ERROR")

    def set_callback_log(self, func):
        if callable(func):
            self._callback = func
