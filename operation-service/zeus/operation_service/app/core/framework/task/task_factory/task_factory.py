import os
import shutil


from vulcanus.log.log import LOGGER
from zeus.operation_service.app.constant import WORK_DIR
from zeus.operation_service.app.core.framework.task.task_factory.batch_script_execution import BatchScriptExecutionTask
from zeus.operation_service.database import Task
from zeus.operation_service.app.core.framework.task.task_detail.task_detail_parser import TaskDetailParser
from zeus.operation_service.app.core.framework.common.constant import TaskType
from zeus.operation_service.app.core.framework.task.task_factory.batch_execution_task import BatchExecutionTask



class TaskFactory:

    @staticmethod
    def task_factory():
        return {
            TaskType.COMMAND_EXECUTION: BatchExecutionTask,
            TaskType.SCRIPT_EXECUTION: BatchScriptExecutionTask,
        }

    @staticmethod
    def init_task(task_type: str):
        return TaskFactory.task_factory().get(task_type)

    @staticmethod
    def get_tasks_with_task_type(task: Task, params: dict):
        LOGGER.warning(f"{task.task_name} {params.get('task_id')} begin to {task.task_type} tasks")
        task_detail_parser = TaskDetailParser(task.task_detail)
        task_hosts = task_detail_parser.get_task_hosts()
        params['task_hosts'] = task_hosts
        params['task_assets'] = task_detail_parser.get_task_assets()
        task_case_nodes = task_detail_parser.get_task_case_nodes()
        to_do_tasks = list()
        # 对多个不同类型的节点资产包任务初始化任务
        for index, task_case_node in enumerate(task_case_nodes):
            TaskFactory.pre_task(task, index, task_case_node, params)
            LOGGER.warning(f"{params['task_name']} init: timeout={params.get('task_timeout')}")
            to_do_task = TaskFactory.init_task(task_type=task.task_type)(task_param=params)
            to_do_task.init()
            to_do_tasks.append(to_do_task)
        return to_do_tasks

    @staticmethod
    def pre_task(task: Task, index, task_case_node, params):
        """初始化任务agent压缩包和workflow.yaml生成
        """
        task_name = "_".join([task.task_name, str(task.task_id), str(index)])
        # agent临时路径
        local_path = os.path.join(WORK_DIR, params.get('task_id'), task_name, 'agent')
        os.makedirs(local_path)
        params['node_indexes'] = task_case_node.get('node_indexes')
        params['task_name'] = task_name
        params['local_path'] = local_path
        params['task'] = task
        task_yaml = TaskFactory.init_task(task_type=task.task_type).TaskYaml(params)
        # 生成workflow.yaml文件，任务根据workflow.yaml执行
        task_yaml.generate_workflow_yaml()
