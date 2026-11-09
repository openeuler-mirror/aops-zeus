# ruff: noqa: I001, E402
import os
import sys
import types
import unittest

# ---- 环境准备：将 operation-service/ 加入路径 ----
_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.append(_root)


# ---- Stub vulcanus 与 apscheduler，避免触发 app/__init__.py 的真实外部依赖 ----
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


class _StubConfigHandle:
    def __init__(self, *args, **kwargs):
        self.parser = types.SimpleNamespace(domain="test")


_stub("vulcanus.conf").ConfigHandle = _StubConfigHandle


class _StubBackgroundScheduler:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class _StubSQLAlchemyJobStore:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


_stub("apscheduler")
_stub("apscheduler.schedulers")
_stub("apscheduler.schedulers.background").BackgroundScheduler = _StubBackgroundScheduler
_stub("apscheduler.jobstores")
_stub("apscheduler.jobstores.sqlalchemy").SQLAlchemyJobStore = _StubSQLAlchemyJobStore


# ---- 导入被测代码 ----
from zeus.operation_service.app.constant import (  # noqa: E402
    BASE_DIR,
    RESULTS_DIR,
    SCRIPTS_DIR,
    SingletonMeta,
    Shcheduler,
    WORK_DIR,
    RemoteExecutionResultCode,
    ResultCodeEnum,
    TaskOperationResultCode,
)


class TestPathConstants(unittest.TestCase):
    """路径常量正确性测试"""

    def test_base_dir_is_string(self):
        self.assertIsInstance(BASE_DIR, str)

    def test_scripts_dir_is_substring_of_base(self):
        self.assertIn(BASE_DIR, SCRIPTS_DIR)

    def test_work_dir_is_substring_of_base(self):
        self.assertIn(BASE_DIR, WORK_DIR)

    def test_results_dir_is_substring_of_base(self):
        self.assertIn(BASE_DIR, RESULTS_DIR)

    def test_scripts_work_results_are_distinct(self):
        dirs = {SCRIPTS_DIR, WORK_DIR, RESULTS_DIR}
        self.assertEqual(len(dirs), 3)


class TestSingletonMeta(unittest.TestCase):
    """SingletonMeta 单例行为测试"""

    def test_same_instance_returned_on_repeated_construction(self):

        class DummyClass(metaclass=SingletonMeta):
            pass

        a = DummyClass()
        b = DummyClass()
        self.assertIs(a, b)

    def test_different_classes_have_different_instances(self):

        class DummyA(metaclass=SingletonMeta):
            pass

        class DummyB(metaclass=SingletonMeta):
            pass

        self.assertIsNot(DummyA(), DummyB())


class TestScheduler(unittest.TestCase):
    """Shcheduler 构造行为测试"""

    def test_scheduler_attribute_created(self):
        engine = object()
        scheduler_obj = Shcheduler(engine)
        self.assertIsInstance(scheduler_obj.scheduler, _StubBackgroundScheduler)

    def test_is_singleton(self):
        engine = object()
        s1 = Shcheduler(engine)
        s2 = Shcheduler(engine)
        self.assertIs(s1, s2)


class TestResultCodeEnum(unittest.TestCase):
    """ResultCodeEnum 基类 code/msg 属性测试"""

    def test_subclass_is_result_code_enum(self):
        self.assertTrue(issubclass(RemoteExecutionResultCode, ResultCodeEnum))
        self.assertTrue(issubclass(TaskOperationResultCode, ResultCodeEnum))

    def test_code_returns_first_element(self):
        member = RemoteExecutionResultCode.SUCCESS_COMMON
        self.assertEqual(member.code, 1020021000)

    def test_msg_returns_second_element(self):
        member = RemoteExecutionResultCode.SUCCESS_COMMON
        self.assertEqual(member.msg, "OK")


class TestRemoteExecutionResultCode(unittest.TestCase):
    """远程执行错误码子类成员完整性测试"""

    def test_known_members_exist(self):
        for name in ["SUCCESS_COMMON", "SUCCESS_ADD_COMMAND", "ERR_UNKNOWN", "ERR_COMMAND_EXIST"]:
            self.assertTrue(hasattr(RemoteExecutionResultCode, name), f"缺少成员 {name}")


class TestTaskOperationResultCode(unittest.TestCase):
    """任务操作错误码子类成员完整性测试"""

    def test_known_members_exist(self):
        for name in ["SUCCESS_COMMON", "ERR_HOST_NOT_EXIST", "ERR_TASK_FINISHED", "ERR_UNKNOWN"]:
            self.assertTrue(hasattr(TaskOperationResultCode, name), f"缺少成员 {name}")


if __name__ == "__main__":
    unittest.main()
