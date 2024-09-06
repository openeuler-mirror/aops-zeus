from zeus.operation_service.app.core.framework.Atomic.atomic import Atomic


class AtomicInteger(Atomic):

    def __init__(self, value):
        super(AtomicInteger, self).__init__(value)

    def add(self, value):
        with self._lock:
            self.value += value

    def increment(self):
        with self._lock:
            self.value += 1

    def decrease(self):
        with self._lock:
            self.value -= 1