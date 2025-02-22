#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2021. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
import time

from async_task.base import AsyncTask
from async_task.settings import configuration
from vulcanus import LOGGER
from vulcanus.restful.resp.state import SUCCEED
from vulcanus.restful.response import BaseResponse


class CveFixExecuteTask(AsyncTask):
    # The name of the task registered in celery
    name = "cve_fix_and_execute_task"
    task_execute_url = "/vulnerabilities/task/execute"
    task_execute_running_url = "/vulnerabilities/task/execute/running"

    def headers(self, token):
        headers = {"Content-Type": "application/json", "Access-Token": token}
        return headers

    def run(self, task_ids, token, *args, **kwargs):
        """
        Run the task with the given host model and task info.

        Args:
            task_ids: Task id list.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            None
        """
        if not task_ids:
            LOGGER.warning("cve fix execute task ids is empty.")
            return

        execute_task_url = f"http://{configuration.domain}{self.task_execute_url}"
        for task_id in task_ids:
            response_data = BaseResponse.get_response(
                method="Post", url=execute_task_url, data=dict(task_id=task_id), header=self.headers(token)
            )
            response_status = response_data.get("label")
            if response_status != SUCCEED:
                LOGGER.error(
                    "cve fix execute task failed, task id: %s, response message: %s", task_id, response_data["message"]
                )
                continue
            while self._check_task_status(task_id, token):
                time.sleep(10)

    def _check_task_status(self, task_id, token):
        task_running_url = f"http://{configuration.domain}{self.task_execute_running_url}"
        response_data = BaseResponse.get_response(
            method="Get", url=task_running_url, data=dict(task_id=task_id), header=self.headers(token)
        )
        if response_data.get("label") == SUCCEED:
            return response_data["data"]

        return False

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
        pass

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Error handler.

        This is run by the worker when the task fails.

        Returns:
            None: The return value of this handler is ignored.
        """
        pass
