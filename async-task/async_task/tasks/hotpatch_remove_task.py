#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
import json
import time

from async_task.base import AsyncTask
from async_task.ssh import ShellExitCode
from vulcanus.conf.constant import TaskStatus


class HotpatchRemoveTask(AsyncTask):
    # The name of the task registered in celery
    name = "hotpatch_remove_task"

    # Shell command for executing task
    command = "aops-ceres apollo --remove-hotpatch '%s'"

    def run(self, host_info, task_info, *args, **kwargs):
        """
        Run the task with the given host model and task info.

        Args:
            host_info: A dictionary containing the SSH connection information.
            task_info: Information about the task to be executed.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            None
        """
        command = self.command % json.dumps({"cves": task_info.get("cves", [])})
        return self.ssh_execute_command(host_info, command)

    def on_success(self, retval, task_id, args, kwargs):
        """Success handler.

        Run by the worker if the task executes successfully.

        Arguments:
            retval (Any): The return value of the task.
            task_id (str): Unique id of the executed task.
            args (Tuple): Original arguments for the executed task.
            kwargs (Dict): Original keyword arguments for the executed task.

        Returns:
            None: The return value of this handler is ignored.
        """
        exit_code, stdout, stderr = retval
        host_info, task_info = args[:2]

        result = self._request_body(host_info, task_info.get("task_id"))
        if exit_code == ShellExitCode.SUCCESS:
            result.update(json.loads(stdout))
        else:
            result.update(
                {
                    "status": TaskStatus.FAIL,
                    "cves": [
                        {"cve_id": cve, "result": TaskStatus.FAIL, "log": stderr} for cve in task_info.get("cves")
                    ],
                }
            )

        self.send_notification(channel=self.name, message=json.dumps(result))

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Error handler.

        This is run by the worker when the task fails.

        Arguments:
            exc (Exception): The exception raised by the task.
            task_id (str): Unique id of the failed task.
            args (Tuple): Original arguments for the task that failed.
            kwargs (Dict): Original keyword arguments for the task that failed.
            einfo (~billiard.einfo.ExceptionInfo): Exception information.

        Returns:
            None: The return value of this handler is ignored.
        """
        host_info, task_info = args[:2]
        result = self._request_body(host_info, task_info.get("task_id"))
        result.update(
            {
                "status": TaskStatus.FAIL,
                "cves": [
                    {"cve_id": cve, "result": TaskStatus.FAIL, "log": einfo} for cve in task_info.get("cves")
                ],
            }
        )
        self.send_notification(channel=self.name, message=json.dumps(result))

    def _request_body(self, host_info: dict, task_id: str) -> dict:
        """
        Generate common data
        """
        request_body = {
            "execution_time": int(time.time()),
            "task_id": task_id,
            "host_id": host_info.get("host_id"),
            "host_ip": host_info.get("host_ip"),
            "host_name": host_info.get("host_name"),
        }
        return request_body
