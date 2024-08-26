from zeus.operation_service.app.core.framework.common.constant import TaskType
from zeus.operation_service.app.core.framework.task.task_detail.batch_execution_task_detail import BatchExecutionDetail
from zeus.operation_service.app.core.framework.task.task_detail.script_execution_task_detail import BatchScriptExecutionDetail

class TaskDetailContext:
    task_detail_map = {
        TaskType.COMMAND_EXECUTION: BatchExecutionDetail,
        TaskType.SCRIPT_EXECUTION: BatchScriptExecutionDetail,
    }

    def __init__(self, validated_data):
        self.task_detail = TaskDetailContext.task_detail_map.get(validated_data.get('task_type'))(validated_data)

    def get_task_detail(self):
        return self.task_detail.get_task_detail()
