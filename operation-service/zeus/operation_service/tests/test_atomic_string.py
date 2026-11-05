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
from zeus.operation_service.app.core.framework.Atomic.atomic_string import AtomicString  # noqa: E402


class TestAtomicString(unittest.TestCase):
    """AtomicString 线程安全字符串操作的单元测试"""

    def test_initial_normal_string(self):
        atom = AtomicString("hello")
        self.assertEqual(atom.get_value(), "hello")

    def test_initial_empty_string(self):
        atom = AtomicString("")
        self.assertEqual(atom.get_value(), "")

    def test_initial_unicode(self):
        atom = AtomicString("你好，世界")
        self.assertEqual(atom.get_value(), "你好，世界")

    def test_initial_special_chars(self):
        atom = AtomicString("special\nchars\there")
        self.assertEqual(atom.get_value(), "special\nchars\there")

    def test_initial_none(self):
        atom = AtomicString(None)
        self.assertIsNone(atom.get_value())

    def test_initial_very_long(self):
        long_str = "x" * 100_000
        atom = AtomicString(long_str)
        self.assertEqual(atom.get_value(), long_str)

    def test_set_value(self):
        atom = AtomicString("old")
        atom.set_value("new")
        self.assertEqual(atom.get_value(), "new")

    def test_set_value_to_empty(self):
        atom = AtomicString("something")
        atom.set_value("")
        self.assertEqual(atom.get_value(), "")

    def test_set_value_to_none(self):
        atom = AtomicString("something")
        atom.set_value(None)
        self.assertIsNone(atom.get_value())

    def test_set_value_multiple_times(self):
        atom = AtomicString("a")
        atom.set_value("b")
        atom.set_value("c")
        atom.set_value("d")
        self.assertEqual(atom.get_value(), "d")

    def test_concurrent_set_and_get(self):
        """并发读写不抛异常，不崩溃"""
        atom = AtomicString("initial")
        errors = []

        def writer():
            for i in range(100):
                atom.set_value(f"vr{i}")

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
