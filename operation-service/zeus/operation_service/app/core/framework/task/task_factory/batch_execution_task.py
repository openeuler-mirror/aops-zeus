#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
from datetime import datetime
import time
from vulcanus.log.log import LOGGER

from zeus.operation_service.app.proxy.task import TaskProxy
from zeus.operation_service.app.proxy.command import CommandProxy
from zeus.operation_service.app.core.framework.task.task_detail.task_detail_parser import TaskDetailParser
from zeus.operation_service.app.core.framework.common.constant import TaskType
from zeus.operation_service.app.core.framework.common.result_code import TaskResultCode
from zeus.operation_service.app.core.framework.task.task_factory.base_task import BaseTask


class BatchExecutionTask(BaseTask):

    def _post_success(self):
        dbproxy = TaskProxy()
        task = dbproxy.get_task_by_id(self.task_id)
        if task.status == TaskResultCode.RUNNING.code:
            dbproxy.update_task(
                task_id=self.task_id, 
                status=TaskResultCode.SUCCESS.code, 
                end_time=datetime.now(),
                progress=1.0
            )

    class TaskYaml(BaseTask.TaskYaml):
        def __init__(self, task_params: dict):
            super().__init__(task_params)
            self.workflow_template = "workflow_template.yml"
            self.task_type = TaskType.COMMAND_EXECUTION

        def generate_agent_config(self, task_assets, task_case_node):
            LOGGER.info("BatchExecutionTask: The configuration file does not need to be generated.")

        def init_context_params(self):
            context_hosts = self.generate_host_list()
            context_steps = self.generate_command_list()
            context = {
                "hosts": context_hosts,
                "jobs": [{
                    "name": "command_job",
                    "hosts": "[" + ",".join([x["hostname"] for x in context_hosts]) + "]",
                    "steps": context_steps
                }],
                
            }
            return context

        def generate_command_list(self):
            context_steps = list()
            task_detail_parser = TaskDetailParser(self.task.task_detail)
            task_case_list = task_detail_parser.get_task_case_list()
            command_ids = list(map(lambda x: x["id"], task_case_list[0]["commands"]))

            db_proxy = CommandProxy()
            db_proxy.connect()
            dependency = ""
            for command_id in command_ids:
                step_info = dict()
                _, command = db_proxy.get_command_info(command_id)
                step_info["name"] = f"command_{command.command_id}"
                step_info["dependency"] = dependency
                dependency = step_info["name"]
                step_items_info = list()
                step_items_info.append("name: batch_execution_shell")
                step_items_info.append(f"cmd: {command.content}")
                step_info["step_items"] = step_items_info
                context_steps.append(step_info)
            return context_steps
