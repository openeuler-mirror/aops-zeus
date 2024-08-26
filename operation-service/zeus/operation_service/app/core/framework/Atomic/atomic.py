import threading


class Atomic:

    def __init__(self, value):
        self.value = value
        self._lock = threading.Lock()

    def get_value(self):
        with self._lock:
            return self.value

    def set_value(self, value):
        with self._lock:
            self.value = value
