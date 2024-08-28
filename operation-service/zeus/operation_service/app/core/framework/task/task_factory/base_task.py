import concurrent.futures
import os
import queue
import shutil
import traceback
from flask import render_template
from zeus.operation_service.app.constant import WORK_DIR
from zeus.operation_service.app.core.file_util import U_RW, G_READ, O_READ
from zeus.operation_service.app.core.framework.workflow.workflow_exception import WorkFlowException
from vulcanus.log.log import LOGGER
from zeus.operation_service.app.proxy.host import HostProxy
from zeus.operation_service.app.core.framework.common.result_code import TaskResultCode, WorkFlowResultCode
from zeus.operation_service.app.proxy.task import TaskProxy
from zeus.operation_service.app.core.framework.workflow.workflow import WorkFlow
from zeus.operation_service.app.core.framework.task.task_detail.task_detail_parser import TaskDetailParser

class BaseTask:

    def __init__(self, task_param: dict):
        self.task_id = task_param.get("task_id")
        self.task_name = task_param.get("task_name")
        self.node_indexes = task_param.get('node_indexes')
        self.task_hosts = task_param.get('task_hosts')
        self.workflow = WorkFlow(os.path.join(task_param.get("local_path"), "workflow.yaml"), task_param)

    def init(self):
        self.workflow.init()

    def _pre_start(self):
        LOGGER.warning(f"{self.task_name} begin running")
        task_proxy = TaskProxy()
        task = task_proxy.get_task_by_id(self.task_id)
        # 任务已经为运行状态，则返回，避免同个task的多个workflow重复设置
        if task.status == TaskResultCode.RUNNING.code:
            return
        task_proxy.set_running_status(self.task_id)
        task_proxy.update_progress(self.task_id, 0.005)

    def _post_success(self):
        """任务完成后的操作，子类实现"""
        pass

    def _clean_env(self):
        LOGGER.warning(f"begin to clean {self.task_name} env")
        shutil.rmtree(os.path.join(WORK_DIR, self.task_id))
        LOGGER.warning(f"clean {self.task_name} env successfully")

    def _handle_error_result(self, result_msg):
        LOGGER.error(f"Failed to run the workflow, failed node: {result_msg['work_node_name']}")
        for item in result_msg["errors_info"].items():
            LOGGER.error(f"Workflow failure details: [Host]: {item[0]}, [Msg]: {item[1]}")
        task_proxy = TaskProxy()
        task_proxy.set_failed_status(self.task_id, TaskResultCode.FAILED.code)

    def _handle_exception(self, exception):
        task_proxy = TaskProxy()

        if isinstance(exception, (queue.Empty, TimeoutError, WorkFlowException, concurrent.futures.TimeoutError)):
            LOGGER.error(f"{self.task_name} timeout")
            task_proxy.set_failed_status(self.task_id, TaskResultCode.TIMEOUT.code)
            return

        LOGGER.error(traceback.print_exc())
        task_proxy.set_failed_status(self.task_id, TaskResultCode.UNKNOWN.code)

    def run(self):
        try:
            self._pre_start()
            self.workflow.start()
            if self.workflow.status == WorkFlowResultCode.NORMAL.code:
                self._post_success()
            else:
                TaskProxy().set_failed_status(self.task_id, TaskResultCode.UNKNOWN.code)
        except Exception as e:
            self._handle_exception(e)
        finally:
            self._clean_env()
        return self

    class TaskYaml:
        def __init__(self, task_params: dict):
            self.node_indexes = task_params.get('node_indexes')
            self.task = task_params.get('task')
            self.task_hosts = task_params.get('task_hosts')
            self.task_id = task_params.get('task_id')
            self.local_path = task_params.get('local_path')
            task_detail_parser = TaskDetailParser(self.task.task_detail)
            self.remote_path = task_detail_parser.get_task_ext_props().get('remote_path', os.path.join("/opt/.agent", self.task_id))
            self.workflow_template = "workflow_template.yml"
            self.task_type = str()

        def generate_workflow_yaml(self):
            ctx = self.init_context_params()
            workflow_yaml = render_template(self.workflow_template, **ctx)
            # LOGGER.info(f"{self.local_path} workflow yaml: {workflow_yaml}")
            workflow_fd = os.open(os.path.join(self.local_path, "workflow.yaml"), os.O_WRONLY | os.O_CREAT,
                                  U_RW | G_READ | O_READ)
            with os.fdopen(workflow_fd, "w", encoding="utf-8") as f:
                f.write(workflow_yaml)

        def init_context_params(self):
            context = dict()
            return context

        def generate_host_list(self):
            context_hosts = list()
            for node_index in self.node_indexes:
                host_json = self.task_hosts[node_index]
                host = HostProxy().get_host_by_id(host_json["host_id"])
                context_hosts.append({
                    "hostname": host.get("host_name"),
                    "ip": host.get("host_ip"),
                    "port": host.get("ssh_port"),
                    "username": host.get("ssh_user"),
                    "password": HostProxy().get_host_pkey_by_id(host_json["host_id"]).replace('\n','\\n')
                })
            return context_hosts
