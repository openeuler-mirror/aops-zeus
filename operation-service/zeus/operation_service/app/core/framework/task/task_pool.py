import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from vulcanus.log.log import LOGGER
from zeus.operation_service.database import Task
from zeus.operation_service.app.settings import configuration
from zeus.operation_service.app.core.framework.common.result_code import TaskResultCode
from zeus.operation_service.app.core.framework.task.task_factory.base_task import BaseTask
from zeus.operation_service.app.proxy.task import TaskProxy

class TaskPool:

    def __init__(self, max_running_job=5, timeout=300):
        try:
            if not hasattr(TaskPool, "_pool_size"):
                self.running_tasks = list()
                self.waiting_queue = queue.Queue()
                self.timeout = timeout
                TaskPool._pool_size = max_running_job
                self.POLL_PRODUCE_POOL = ThreadPoolExecutor(TaskPool._pool_size,
                                                            thread_name_prefix=f"TaskPool-{id(self)}")
                LOGGER.warning(f"init pool size {max_running_job}, pool:{id(self.POLL_PRODUCE_POOL)},{id(self)}")
                threading.Thread(target=self.start, name="TaskPool-thread").start()
        except Exception as e:
            LOGGER.error(f"TaskPool __init__ failed, exception: {e}")
            self.handle_exception()

    def __new__(cls, *args, **kwargs):
        if not hasattr(TaskPool, "_instance"):
            LOGGER.info("task pool create new")
            TaskPool._instance = object.__new__(cls)
        return TaskPool._instance

    def handle_exception(self):
        for task in self.running_tasks:
            try:
                task = Task.objects.get(pk=task.task_id)
                if task.status == TaskResultCode.RUNNING.code or task.status == TaskResultCode.WAITING.code:
                    LOGGER.error(f"taskpool exception, set {task.task_type} {task.name} failed")
                    TaskProxy().set_failed_status(task.task_id, TaskResultCode.UNKNOWN.code)
            except Exception as e:
                LOGGER.error(f"TaskPool handle exception get exception {e}")

    def submit_task(self, task: BaseTask):
        LOGGER.warning(f"find pool, put task:{id(task)} into pool:{id(self.POLL_PRODUCE_POOL)}")
        self.running_tasks.append(task)
        self.waiting_queue.put(task)
        # 如果池子的任务大于最大任务数，则重启任务池，等待任务结束;避免持续启动任务，内存增大
        if len(self.running_tasks) >= configuration.task.max_task_number_in_task_pool:
            self.__del_self()
            self.POLL_PRODUCE_POOL.shutdown(wait=False)
            LOGGER.warning(
                f"task in pool exceed max task number; shutdown pool: {id(self.POLL_PRODUCE_POOL)} successfully")

    def start(self):
        all_tasks = list()
        try:
            while True:
                task_pool_timeout = configuration.task.task_pool_timeout
                task = self.waiting_queue.get(timeout=task_pool_timeout)
                LOGGER.info(f"get task: {task.task_name}, put into pool: {id(self.POLL_PRODUCE_POOL)}")
                all_tasks.append(self.POLL_PRODUCE_POOL.submit(task.run))
        except queue.Empty:
            self.__del_self()
            LOGGER.warning(f"get no task in {task_pool_timeout}s, begin to stop task pool")
            try:
                task_timeout = configuration.task.task_timeout
                for task in as_completed(all_tasks):
                    LOGGER.warning(
                        f"task {task.result(timeout=task_timeout)} finished")
                    self.running_tasks.remove(task.result())
                    LOGGER.warning(f"tasks {str(self.running_tasks)} is running")
                LOGGER.warning("all tasks finished")
            except Exception as e:
                LOGGER.error(f"get task result error: {e}, shutdown task pool: {id(self.POLL_PRODUCE_POOL)}")
                self.handle_exception()
        except Exception as e:
            LOGGER.error(f"task pool exception: {e}, shutdown task pool: {id(self.POLL_PRODUCE_POOL)}")
            self.__del_self()
            self.handle_exception()
        finally:
            self.POLL_PRODUCE_POOL.shutdown(wait=False)
            LOGGER.warning(f"shutdown pool: {id(self.POLL_PRODUCE_POOL)} successfully")

    def __del_self(self):
        LOGGER.warning(f"kill taskpool {id(self)}")
        if hasattr(TaskPool, "_instance"):
            delattr(TaskPool, "_instance")
        if hasattr(TaskPool, "_pool_size"):
            delattr(TaskPool, "_pool_size")
