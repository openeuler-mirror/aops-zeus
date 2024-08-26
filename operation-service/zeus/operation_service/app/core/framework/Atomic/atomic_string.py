from zeus.operation_service.app.core.framework.Atomic.atomic import Atomic


class AtomicString(Atomic):
    def __init__(self, value):
        super(AtomicString, self).__init__(value)