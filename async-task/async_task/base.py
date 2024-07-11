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
from io import StringIO
from typing import Tuple

import celery
import paramiko
from async_task.settings import configuration
from async_task.ssh import SSHClient, SSHClientConfig
from paramiko.ssh_exception import SSHException
from redis.exceptions import RedisError
from retrying import retry
from vulcanus.database.proxy import RedisProxy
from vulcanus.log.log import LOGGER


class CeleryConfig:
    RESULT_BACKEND = f"redis://{configuration.redis.host}:{configuration.redis.port}/1"
    BROKER_URL = f"redis://{configuration.redis.host}:{configuration.redis.port}/0"
    RESULT_SERIALIZER = "json"
    RESULT_EXPIRES = 3600
    TIMEZONE = "Asia/Shanghai"
    BROKER_CONNECTION_RETRY_ON_STARTUP = True


class AsyncTask(celery.Task):

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
        raise NotImplementedError

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
        raise NotImplementedError

    def __repr__(self):
        return self.name

    @property
    def task_id(self):
        return self.request.id

    @staticmethod
    def ssh_execute_command(host_info: dict, command: str, **kwargs) -> Tuple[int, str, str]:
        """
            Connects to the specified host via SSH and executes the given command.

            Args:
                host_info(dict): host ssh info
                    Example:
                        {
                            "ip": "192.168.1.100",
                            "port": 22,
                            "username": "user",
                            "password": "password",
                            "private_key": "private key string"
                        }
                command (str): The command to execute on the remote host.
                **kwargs: Additional keyword arguments.Such as window_size, max_packet_size, timeout

        Returns:
            Tuple[int, str, str]: A tuple containing the command exit status, stdout, and stderr.
        """
        try:
            private_key = paramiko.RSAKey.from_private_key(StringIO(host_info.get("pkey")))
        except SSHException as e:
            LOGGER.error("Failed to load key information, with msg{}".format(e))
            private_key = None
        client_config = SSHClientConfig(
            hostname=host_info.get("host_ip"),
            port=host_info.get("ssh_port"),
            username=host_info.get("ssh_user"),
            password=host_info.get("password"),
            private_key=private_key,
        )
        return SSHClient(client_config).execute_command(command, **kwargs)

    @retry(
        stop_max_attempt_number=3,
        wait_exponential_multiplier=1000,
        wait_exponential_max=5000,
        retry_on_exception=lambda exception: isinstance(exception, RedisError),
    )
    def send_notification(self, channel, message):
        """
        Publishes a message to a Redis channel.

        Args:
            channel (str): The name of the channel to publish to.
            message (str): The message to publish.

        Returns:
            int: The number of clients that received the message.
        """
        try:
            if not RedisProxy.redis_connect:
                RedisProxy(host=configuration.redis.host, port=configuration.redis.port)
            return RedisProxy.redis_connect.publish(channel, message)
        except RedisError as e:
            LOGGER.error("Failed to publishes a message to a Redis channel, with msg{}".format(e))
