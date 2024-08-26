import os
import traceback
from vulcanus.log.log import LOGGER
from vulcanus.database.proxy import MysqlProxy

from zeus.operation_service.database import Task
from zeus.operation_service.app.proxy.task import TaskProxy
from zeus.operation_service.app.core.framework.task.task_factory.task_factory import TaskFactory
from zeus.operation_service.app.core.framework.task.task_pool import TaskPool
from zeus.operation_service.app.core.framework.common.result_code import TaskResultCode 
from zeus.operation_service.app.core.framework.common.constant import TaskType
from zeus.operation_service.app.core.file_util import FileUtil
from zeus.operation_service.app.core.task_exception import TaskException
from zeus.operation_service.app.constant import TaskOperationResultCode, WORK_DIR, RESULTS_DIR
from vulcanus.restful.resp.state import (
    SUCCEED,
    NO_DATA,
    TASK_START_FAILED
)


class TaskManager():

    def __init__(self) -> None:
        self.mysql_session = MysqlProxy()

    def do_action(self, task_id, action):
        action_map = {
            "start": self.start_task,
            "retry": self.retry_task
        }
        return action_map[action](task_id, {})

    def start_task(self, task_id, params: dict, reset_task_status=True):
        """
        1.获取hosts
        2.获取资产包
        3.获取巡检项
        4.构建下发数据
        """
        task_proxy = TaskProxy()
        task_proxy.connect()
        task: Task = task_proxy.get_task_by_id(task_id)

        if not task:
            return NO_DATA, None

        task_detail = task.task_detail
        # task_detail_parser = TaskDetailParser(task_detail)

        # 检查数据库中hosts与assets是否存在
        # task_hosts_id = task_detail_parser.get_task_hosts_id()
        # if Host.objects.filter(pk__in=task_hosts_id).count() < len(task_hosts_id):
        #     LOG.error("Start task failed: host not exist")
        #     raise TaskException(TaskOperationResultCode.ERR_HOST_NOT_EXIST)

        params['task_pool_timeout'] = 300
        params['max_running_task'] = 5
        params['task_timeout'] = 900
        params['task_id'] = task.task_id
        
        try:
            task_upload_path = os.path.join(RESULTS_DIR, task.task_type, task.task_id)
            if os.path.exists(task_upload_path):
                FileUtil.dir_remove(task_upload_path)
            os.makedirs(task_upload_path, exist_ok=False)
            work_path = os.path.join(WORK_DIR, task.task_id)
            if os.path.exists(work_path):
                FileUtil.dir_remove(work_path)
            os.makedirs(work_path, exist_ok=False)
            LOGGER.info(f"starting task: {task.task_name}")

            tasks = TaskFactory.get_tasks_with_task_type(task=task, params=params)
        except Exception as e:
            LOGGER.error(traceback.print_exc())
            FileUtil.dir_remove(task_upload_path)
            FileUtil.dir_remove(work_path)
            return SUCCEED, None
        if reset_task_status:
            task_proxy.reset_task_status(task_id)
        task_proxy.set_wait_status(task_id)
        LOGGER.warning(f"task pool timeout: {params['task_timeout']}s")
        for each_task in tasks:
            TaskPool(max_running_job=params['max_running_task'], timeout=params['task_timeout']).submit_task(each_task)
        return SUCCEED, None


    def retry_task(self, task_id, params: dict):
        task = TaskProxy().get_task_by_id(task_id)
        if task.status == TaskResultCode.RUNNING.code or task.status == TaskResultCode.WAITING.code:
            raise TaskException(TaskOperationResultCode.ERR_RETRY_RUNNING_TASK)
        if task.task_type == TaskType.COMMAND_EXECUTION:
            FileUtil.dir_remove(os.path.join(RESULTS_DIR, task.task_type, task.task_id))
        return self.start_task(task, params)


    def cancel_task(task_id, params: dict):
        task = TaskProxy().get_task_by_id(task_id)
        if task.status == TaskResultCode.RUNNING.code:
            TaskProxy().cancel_task(task_id)
            LOGGER.info(f"{params.get('user')} cancel task")
            return TaskOperationResultCode.SUCCESS_CANCEL_TASK, task
        else:
            LOGGER.error(f"{task.task_name} status:{task.status} is not running,cannot be cancelled")
            raise TaskException(TaskOperationResultCode.ERR_CANCEL_NOT_RUNNING_TASK)


    def recover_task(self, task_id, params: dict):
        params['recover'] = True
        return self.start_task(task_id, params, False)