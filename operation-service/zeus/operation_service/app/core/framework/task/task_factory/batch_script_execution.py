#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
import time
import os
from datetime import datetime
from vulcanus.log.log import LOGGER
from zeus.operation_service.app.proxy.task import TaskProxy
from zeus.operation_service.app.core.framework.task.task_detail.task_detail_parser import TaskDetailParser
from zeus.operation_service.app.core.framework.common.constant import TaskType
from zeus.operation_service.app.core.framework.common.result_code import TaskResultCode
from zeus.operation_service.app.core.framework.task.task_factory.base_task import BaseTask
from zeus.operation_service.app.constant import SCRIPTS_DIR


class BatchScriptExecutionTask(BaseTask):

    def _post_success(self):
        TaskProxy().update_task(
            task_id=self.task_id, 
            status=TaskResultCode.SUCCESS.code, 
            end_time=datetime.now(),
            progress=1.0
        )

    class TaskYaml(BaseTask.TaskYaml):
        def __init__(self, task_params: dict):
            super().__init__(task_params)
            self.workflow_template = "workflow_template.yml"
            self.task_type = TaskType.SCRIPT_EXECUTION

        def generate_agent_config(self, task_assets, task_case_node):
            LOGGER.info("BatchScriptExecutionTask: The configuration file does not need to be generated.")

        def init_context_params(self):
            context_hosts = self.generate_host_list()
            context_jobs = self.generate_jobs_list()
            context = {
                "hosts": context_hosts,
                "jobs": context_jobs
            }
            return context

        def generate_step_list(self, case_idx):
            context_steps = list()
            task_detail_parser = TaskDetailParser(self.task.task_detail)
            task_case_list = task_detail_parser.get_task_case_list()
            script = task_case_list[0]['scripts'][case_idx]

            dependency = ""

            script_path = os.path.join(SCRIPTS_DIR, script['script_id'])

            step_info = dict()
            # 获取当前脚本文件并传送到远端
            copy_list = list()
            for index, file in enumerate(os.listdir(script_path)):
                copy_info = dict()
                copy_name = f"copy_file_to_cluster{index}"
                copy_list.append(copy_name)
                copy_info["name"] = copy_name
                copy_item_info = list()
                copy_item_info.append("name: copy")
                copy_item_info.append(f"src: {os.path.join(script_path, file)}")
                copy_item_info.append(f"dest: {os.path.join(self.remote_path, file)}")
                copy_item_info.append("owner: 0")
                copy_item_info.append("group: 0")
                copy_item_info.append("mode: 0755")
                copy_info["dependency"] = dependency
                copy_info["step_items"] = copy_item_info
                context_steps.append(copy_info)

            only_push = task_detail_parser.get_task_ext_props()['only_push']
            if not only_push:
                step_info["name"] = f"command_{script['script_id']}"
                step_info["dependency"] = ','.join(copy_list)
                step_items_info = list()
                step_items_info.append("name: script_execution_shell")
                command_format = script['command'].replace('\r\n', ' ').replace('\n', ' ')
                path = self.remote_path.replace('\\', '/')   # 避免后续在远端执行命令时反斜杠被转义
                step_items_info.append(f"cmd: cd {path}; {command_format}")
                step_info["step_items"] = step_items_info
                context_steps.append(step_info)
            return context_steps

        def generate_jobs_list(self):
            task_detail_parser = TaskDetailParser(self.task.task_detail)
            context_jobs = list()
            case_list = task_detail_parser.get_task_case_list()
            node_list = task_detail_parser.get_task_hosts()
            case_node = task_detail_parser.get_task_case_nodes()[0]

            for case_idx, case in enumerate(case_list[0]['scripts']):
                job_info = dict()
                job_info['name'] = case['name']
                host_idxs = case_node['case_indexes'][str(case_idx)]
                job_info['hosts'] = "[" + ",".join([node_list[idx]['host'] for idx in host_idxs]) + "]"
                job_info['steps'] = self.generate_step_list(case_idx)
                context_jobs.append(job_info)
            return context_jobs
