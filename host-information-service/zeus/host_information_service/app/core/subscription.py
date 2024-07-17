#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2022. All rights reserved.
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
from typing import List

from redis import Redis, RedisError
from vulcanus.conf.constant import TaskStatus
from vulcanus.exceptions.database_exception import DatabaseConnectionFailed
from vulcanus.log.log import LOGGER

from zeus.host_information_service.app.proxy.cluster import ClusterProxy
from zeus.host_information_service.app.proxy.host import HostProxy

__all__ = ['TaskCallbackSubscribe']


class TaskCallbackSubscribe:
    """
    Handles callback logic for different task channels.
    """

    def __init__(self, subscribe_client: Redis, channels: List[str]) -> None:
        self._subscribe = subscribe_client
        self._channels = channels
        self.subscribe_message = None

    def __call__(self, *args, **kwds):
        """
        Subscribe to Redis channels and execute a callback function for each received message.
        """
        while True:
            try:
                subscribe = self._subscribe.pubsub()
                for channel in self._channels:
                    subscribe.subscribe(channel)

                for message in subscribe.listen():
                    if message["type"] != "message":
                        continue

                    self._callback(message["channel"], json.loads(message["data"]))
            except RedisError as error:
                LOGGER.error(f"Failed to subscribe to channels {self._channels}: {error}")
                time.sleep(1)
            except Exception as error:
                LOGGER.error(error)
                time.sleep(1)

    def _cve_scan_task(self, task_execute_result: dict) -> None:
        if task_execute_result.get("status") != TaskStatus.SUCCEED:
            return
        lock = f"cve_scan_task_subscribe-{task_execute_result['task_id']}-{task_execute_result['host_id']}"
        if not self._subscribe.set(lock, 'locked', nx=True, ex=30):
            LOGGER.warning("Another cve scan task is running, skip this subscribe.")
            return
        try:
            with HostProxy() as proxy:
                proxy.update_host_association_information(
                    task_execute_result.get("host_id"),
                    {"reboot": task_execute_result.get("reboot"), "last_scan": int(time.time())},
                )
        except DatabaseConnectionFailed:
            LOGGER.error(
                f"Failed to handle the result of task cve scan (ID: {task_execute_result.get('task_id')})"
                f"{task_execute_result.get('host_id')}."
            )

    def _repo_set_task(self, task_execute_result: dict) -> None:
        if task_execute_result.get("status") != TaskStatus.SUCCEED:
            return
        lock = f"repo_set_task_subscribe-{task_execute_result['task_id']}-{task_execute_result['host_id']}"
        if not self._subscribe.set(lock, 'locked', nx=True, ex=30):
            LOGGER.warning("Another repo set task is running, skip this subscribe.")
            return
        try:
            with HostProxy() as proxy:
                proxy.update_host_association_information(
                    task_execute_result.get("host_id"), {"repo_id": task_execute_result.get("repo_id")}
                )
        except DatabaseConnectionFailed:
            LOGGER.error(
                f"Failed to handle the result of task repo set (ID: {task_execute_result.get('task_id')})"
                f"{task_execute_result.get('host_id')}."
            )

    def _cluster_synchronize_cancel_task(self, task_execute_result: dict) -> None:
        lock = f"cluster_synchronize_cancel_task_host_subscribe-{task_execute_result['cluster_id']}"
        if not self._subscribe.set(lock, 'locked', nx=True, ex=30):
            LOGGER.warning("Another repo set task is running, skip this subscribe.")
            return
        try:
            with ClusterProxy() as proxy:
                proxy.cancel_synchronize_cluster(task_execute_result.get("cluster_id"))
        except DatabaseConnectionFailed:
            LOGGER.error(f"Failed to delete cluster: {task_execute_result.get('cluster_id')} relative info.")

    def _cluster_synchronize_task(self, task_execute_result: dict) -> None:
        lock = f"cluster_synchronize_task_subscribe-{task_execute_result['cluster_id']}"
        if not self._subscribe.set(lock, 'locked', nx=True, ex=30):
            LOGGER.warning("Another repo set task is running, skip this subscribe.")
            return
        try:
            with ClusterProxy() as proxy:
                proxy.update_cluster_synchronous_state(
                    task_execute_result.get("cluster_id"), task_execute_result.get("synchronous_state")
                )
        except DatabaseConnectionFailed:
            LOGGER.error(f"Failed to update cluster: {task_execute_result.get('cluster_id')} synchronize state.")

    def _callback(self, channel: str, task_execute_result: dict) -> None:
        """
        Handles callback based on the task channel and task execution result.

        Args:
            channel (str): The name of the task channel.
            task_execute_result (dict): The result of the task execution.
        """
        channel_func = getattr(self, f"_{channel}")
        if not channel_func or not callable(channel_func):
            LOGGER.error("Unsupported task type")
            return
        channel_func(task_execute_result)
