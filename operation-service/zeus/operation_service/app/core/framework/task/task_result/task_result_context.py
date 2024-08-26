from zeus.operation_service.app.core.framework.common.constant import TaskType
from zeus.operation_service.app.core.framework.task.task_result.batch_execution_task_result_detail import BatchExecutionResultDetail
from zeus.operation_service.app.core.framework.task.task_result.script_execution_task_result_detail import BatchScriptExecutionDetail


class TaskResultContext:
    task_result_detail_map = {
        TaskType.COMMAND_EXECUTION: BatchExecutionResultDetail,
        TaskType.SCRIPT_EXECUTION: BatchScriptExecutionDetail,
    }

    def __init__(self, task):
        self.task_result_detail = self.task_result_detail_map.get(task.task_type)(task)

    def update_progress(self, request):
        return self.task_result_detail.update_progress(request)

    def download_task_result(self, request):
        return self.task_result_detail.download_task_result(request)

    def get_items_detail(self, data):
        return self.task_result_detail.get_items_detail(data)

    def generate_hosts_assets(self):
        return self.task_result_detail.generate_hosts_assets()
