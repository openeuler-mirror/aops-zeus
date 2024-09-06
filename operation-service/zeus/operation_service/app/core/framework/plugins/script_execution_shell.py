#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
import logging
import logging.config
import os
from datetime import datetime

from zeus.operation_service.app.constant import RESULTS_DIR
from zeus.operation_service.app.core.framework.common.constant import TaskType
from zeus.operation_service.app.core.framework.plugins.shell import Shell
from zeus.operation_service.app.core.file_util import U_RW, O_READ, G_READ


class ScriptExecutionShell(Shell):

    def run(self):
        result = super(ScriptExecutionShell, self).run()
        self.info(f"{self._task_vars['cmd']}\n{result.get('error_msg', {}).get('echo', '')}\n")
        return result

    def info(self, echo):
        log_file_path = os.path.join(RESULTS_DIR, TaskType.SCRIPT_EXECUTION,
                                     self._task_vars["task_metadata"]["task_id"])
        formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_fd = os.open(os.path.join(log_file_path, f'result_{self._host["ip"]}.log'), os.O_WRONLY | os.O_CREAT,
                          U_RW | G_READ | O_READ)
        with os.fdopen(file_fd, 'a') as file:
            file.write(f'[{formatted_time}]: {echo}')
