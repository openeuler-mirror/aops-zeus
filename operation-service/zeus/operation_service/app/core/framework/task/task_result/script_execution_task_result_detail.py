#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
import os.path
from zeus.operation_service.app.constant import TaskOperationResultCode
from vulcanus.restful.resp import state
from zeus.operation_service.app.proxy.host import HostProxy
from zeus.operation_service.app.constant import RESULTS_DIR
from zeus.operation_service.app.core.framework.common.result_code import TaskResultCode
from zeus.operation_service.app.core.framework.task.task_result.task_result_detail import TaskResultDetail


class BatchScriptExecutionDetail(TaskResultDetail):

    def get_items_detail(self, data):
        node_index = data['node_index']
        host_id = self.task_detail['node_list'][node_index]['host_id']
        host = HostProxy().get_host_by_id(host_id)

        if self.task.status == TaskResultCode.RUNNING.code:
            return state.REPEAT_TASK_EXECUTION, {}

        host_result = list()
        result_path = os.path.join(RESULTS_DIR, self.task.task_type, self.task.task_id)
        result_file = os.path.join(result_path, f"result_{host.get('host_ip')}.log")

        if not os.path.exists(result_file):
            return state.TASK_RESULT_NOT_FOUND, {}

        with open(result_file, "r") as f:
            for line in f:
                host_result.append(line)

        return state.SUCCEED, host_result
