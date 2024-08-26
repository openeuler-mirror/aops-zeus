from zeus.operation_service.app.core.framework.Atomic.atomic_integer import AtomicInteger
from zeus.operation_service.app.core.framework.Atomic.atomic_string import AtomicString
from zeus.operation_service.app.core.framework.common.result_code import PluginResultCode
from zeus.operation_service.app.core.framework.task_dispatcher import TaskDispatcher
from vulcanus.log.log import LOGGER


class WorkNode:
    def __init__(self, worknode_name, task_id, step):
        self.name = worknode_name
        self.pre_status = AtomicInteger(0)
        self.status_reason = AtomicString("")
        self.dependency_account = AtomicInteger(0)
        self._status = "waiting"
        self.step = step
        self.task_id = task_id
        self._hosts_map = WorkNode.init_hosts_map(step)
        self.next_nodes = []

    def set_status(self, status):
        self._status = status

    def add_next_node(self, next_node):
        self.next_nodes.append(next_node)

    def get_status(self):
        return self._status

    def work(self, handle_result_func):

        # 如果前置依赖失败且该step不是必须做的时候，直接返回失败
        if self.pre_status.value == -1:
            if (self.step and self.step.essential == "False") or not self.step:
                LOGGER.warning(f"{self.name} pre status failed, no execute")
                result_msg = dict()
                result_msg["result_code"] = PluginResultCode.PRE_DEPENDENCY_ERROR
                result_msg["work_node_name"] = self.name
                result_msg['errors_info'] = self.status_reason.value
                return handle_result_func(result_msg)
        if self.step is None:
            result_msg = dict()
            result_msg["result_code"] = PluginResultCode.SUCCESS
            result_msg["work_node_name"] = self.name
            result_msg['errors_info'] = dict()
            return handle_result_func(result_msg)
        task_context = dict()
        task_context["hosts"] = list()
        for item in self._hosts_map.values():
            task_context["hosts"].append(item)
        task_context["task"] = self.step.get_module()
        task_context["batch_size"] = 5
        task_context["callback"] = handle_result_func
        task_context["work_node_name"] = self.name
        task_context["task_id"] = self.task_id
        task_context["timeout"] = 900
        # 多个节点批量执行step
        return TaskDispatcher(task_context).run()

    def get_next_free_nodes(self):
        next_free_nodes = []
        for dependency_node in self.next_nodes:
            dependency_node.dependency_account.decrease()
            if dependency_node.dependency_account.get_value() == 0:
                next_free_nodes.append(dependency_node)
        return next_free_nodes

    @staticmethod
    def init_hosts_map(step):
        if step is None:
            return {}
        return step.get_hosts_map()
