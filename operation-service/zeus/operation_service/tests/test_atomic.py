# ruff: noqa: I001, E402
import os
import sys
import threading
import types
import unittest

# ---- 环境准备：将 operation-service/ 加入路径 ----
_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.append(_root)


# ---- Stub vulcanus，避免触发 app/__init__.py 的真实外部依赖 ----
def _stub(fullname):
    if fullname not in sys.modules:
        mod = types.ModuleType(fullname)
        mod.__path__ = []
        sys.modules[fullname] = mod
    return sys.modules[fullname]


_stub("vulcanus")
_stub("vulcanus.cache").RedisCacheManage = type(
    "RedisCacheManage", (), {"__init__": lambda self, **kw: None}
)
_stub("vulcanus.database")
_stub("vulcanus.database.proxy").RedisProxy = type("RedisProxy", (), {"redis_connect": None})


class _StubParser:
    domain = "test"


class _StubConfigHandle:
    parser = _StubParser()

    def __init__(self, *args, **kwargs):
        pass


_stub("vulcanus.conf").ConfigHandle = _StubConfigHandle


# ---- 导入被测代码 ----
from zeus.operation_service.app.core.framework.Atomic.atomic import Atomic  # noqa: E402


class TestAtomic(unittest.TestCase):
    """Atomic 基类线程安全读写的单元测试"""

    def test_initial_int(self):
        atom = Atomic(10)
        self.assertEqual(atom.get_value(), 10)

    def test_initial_str(self):
        atom = Atomic("hello")
        self.assertEqual(atom.get_value(), "hello")

    def test_initial_list(self):
        atom = Atomic([1, 2, 3])
        self.assertEqual(atom.get_value(), [1, 2, 3])

    def test_initial_dict(self):
        atom = Atomic({"a": 1})
        self.assertEqual(atom.get_value(), {"a": 1})

    def test_initial_none(self):
        atom = Atomic(None)
        self.assertIsNone(atom.get_value())

    def test_initial_bool(self):
        atom = Atomic(True)
        self.assertTrue(atom.get_value())

    def test_set_value_int(self):
        atom = Atomic(0)
        atom.set_value(42)
        self.assertEqual(atom.get_value(), 42)

    def test_set_value_str(self):
        atom = Atomic(0)
        atom.set_value("new_val")
        self.assertEqual(atom.get_value(), "new_val")

    def test_set_value_replaces_reference(self):
        """set_value 替换为不同类型不报错"""
        atom = Atomic(10)
        atom.set_value("string_now")
        self.assertIsInstance(atom.get_value(), str)
        atom.set_value(999)
        self.assertIsInstance(atom.get_value(), int)

    def test_set_value_none(self):
        atom = Atomic("something")
        atom.set_value(None)
        self.assertIsNone(atom.get_value())

    def test_concurrent_set_values_distinct(self):
        """10个线程并发 set_value，最终为其中之一，不报错"""
        atom = Atomic(None)

        def writer(idx):
            atom.set_value(idx)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertIn(atom.get_value(), range(10))

    def test_concurrent_read_write_no_crash(self):
        """并发读+写不抛异常"""
        atom = Atomic(0)
        errors = []

        def writer():
            for i in range(100):
                atom.set_value(i)

        def reader():
            try:
                for _ in range(100):
                    _ = atom.get_value()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer) for _ in range(2)]
        threads += [threading.Thread(target=reader) for _ in range(2)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
