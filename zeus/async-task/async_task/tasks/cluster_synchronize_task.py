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
import os
import re
import shutil
import socket

import retrying
import yaml
from async_task.base import AsyncTask
from async_task.settings import configuration
from retrying import retry
from vulcanus import LOGGER
from vulcanus.conf.constant import (
    CANAL_ADAPTER_BIN_PATH,
    CANAL_ADAPTER_CONF_PATH,
    CANAL_BIN_PATH,
    CANAL_CONF_PATH,
    TaskStatus,
    CANAL_INSTANCE,
    INSTANCE_PATH,
    CANAL_PROPERTIES,
    CANAL_ADAPTER_APPLICATION,
    RDB_CONF_PATH,
    CANAL_DB_USERNAME,
    CANAL_DB_PASSWORD,
)
from vulcanus.exceptions import SynchronizeError
from vulcanus.restful.response import BaseResponse


class ClusterSynchronizeTask(AsyncTask):
    # The name of the task registered in celery
    name = "cluster_synchronize_task"

    def run(self, cluster_id, cluster_ip, local_cluster_ip, *args, **kwargs):
        """
        Run the task with the given host model and task info.

        Args:
            cluster_info: A dictionary containing the cluster information.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            None
        """
        self._canal_deployer_synchronize(cluster_id, cluster_ip)
        self._canal_adapter_synchronize(cluster_id, cluster_ip, local_cluster_ip)
        self._restart_canal()
        self._canal_synchronize_etl(cluster_id)

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
        result = {
            "cluster_id": kwargs.get("cluster_id"),
            "synchronous_state": TaskStatus.SUCCEED,
        }
        self.send_notification(channel=self.name, message=json.dumps(result))
        LOGGER.info("synchronize {} {}".format(kwargs.get("cluster_id"), TaskStatus.SUCCEED))

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
        result = {
            "cluster_id": kwargs.get("cluster_id"),
            "synchronous_state": TaskStatus.FAIL,
        }
        self.send_notification(channel=self.name, message=json.dumps(result))
        LOGGER.info("synchronize {} {}".format(kwargs.get("cluster_id"), TaskStatus.FAIL))

    def _canal_deployer_synchronize(self, cluster_id: str, cluster_ip: str):
        """
        configure canal_deployer
        """
        try:
            self._canal_properties(cluster_id)
            self._canal_instance(cluster_id, cluster_ip)

        except FileNotFoundError as error:
            self.update_state(state='FAILURE')
            raise SynchronizeError("cluster:{} synchronize canal_deployer failed, with msg: {}".format(cluster_id, error))

    def _canal_properties(self, cluster_id: str):
        with open(CANAL_PROPERTIES, mode='r+', encoding="utf-8") as canal_properties:
            conf = canal_properties.read()
            destinations_config = re.search("canal.destinations.*", conf)
            LOGGER.info(f"destinations_config is:{str(destinations_config.group(0))}")
            if not destinations_config:
                self.update_state(state='FAILURE')
                raise SynchronizeError(
                    "cluster:{} synchronize canal_deployer failed, canal.destinations not found")
            destinations = destinations_config.group(0).replace('canal.destinations = ', '').split(',')
            destinations = [i for i in destinations if i != '']
            destinations.append(cluster_id)
            destinations = list(set(destinations))
            after_replace_conf = re.sub(
                "canal.destinations.*", 'canal.destinations = ' + ','.join(destinations), conf, count=0, flags=0
            )

            canal_properties.seek(0)
            canal_properties.truncate()
            canal_properties.write(after_replace_conf)

    def _canal_instance(self, cluster_id: str, cluster_ip: str):
        if os.path.exists(CANAL_CONF_PATH + cluster_id):
            shutil.rmtree(CANAL_CONF_PATH + cluster_id)
        os.mkdir(CANAL_CONF_PATH + cluster_id)
        with open(INSTANCE_PATH, "r", encoding="utf-8") as instance_properties:
            instance = instance_properties.read()
            address = "canal.instance.master.address=" + cluster_ip + ":3306"
            instance = re.sub("canal.instance.master.address=.*", address, instance, count=0, flags=0)
            instance = re.sub(
                "canal.instance.dbUsername=.*", "canal.instance.dbUsername=" + CANAL_DB_USERNAME, instance, count=0, flags=0
            )
            instance = re.sub(
                "canal.instance.dbPassword=.*", "canal.instance.dbPassword=" + CANAL_DB_PASSWORD, instance, count=0, flags=0
            )
            instance = re.sub("canal.mq.topic=.*", "canal.mq.topic=" + cluster_id, instance, count=0, flags=0)

        with open(
            CANAL_CONF_PATH + cluster_id + CANAL_INSTANCE, "w", encoding="utf-8"
        ) as new_instance_properties:
            new_instance_properties.write(instance)

    def _canal_adapter_synchronize(self, cluster_id: str, cluster_ip: str, local_cluster_ip: str):
        """
        configure canal_adapter
        """
        try:
            self._canal_adapter_application(cluster_id, cluster_ip, local_cluster_ip)
            self._canal_adapter_rdb(cluster_id)
        except (FileNotFoundError, yaml.YAMLError, AttributeError) as error:
            self.update_state(state='FAILURE')
            raise SynchronizeError("cluster:{} synchronize canal_adapter failed, with msg: {}".format(cluster_id, error))

    def _canal_adapter_application(self, cluster_id: str, cluster_ip: str, local_cluster_ip: str):
        with open(CANAL_ADAPTER_APPLICATION, mode='r+', encoding="utf-8") as file_context:
            application = file_context.read()
            conf = yaml.safe_load(application)
            url = f"jdbc:mysql://{cluster_ip}:{configuration.mysql.port}/{configuration.mysql.database}?useUnicode=true&allowPublicKeyRetrieval=true&useSSL=false"
            data_source = dict({"url": url, "username": CANAL_DB_USERNAME, "password": CANAL_DB_PASSWORD})
            if not conf.get("canal.conf"):
                self.update_state(state='FAILURE')
                raise SynchronizeError(
                    "cluster:{} synchronize canal_adapter failed, not found canal.conf")
            data_sources_conf = conf.get("canal.conf").get("srcDataSources")
            if not data_sources_conf:
                data_sources_conf = {cluster_id: data_source}
                conf.get("canal.conf")["srcDataSources"] = data_sources_conf
            else:
                data_sources_conf[cluster_id] = data_source

            outer_adapters = [{"name": "logger"}]
            outer_adapter = {"name": "rdb", "key": cluster_id}
            properties = {
                "jdbc.driverClassName": "com.mysql.jdbc.Driver",
                "jdbc.url": f"jdbc:mysql://{local_cluster_ip}:{configuration.mysql.port}/{configuration.mysql.database}?useUnicode=true&allowPublicKeyRetrieval=true&useSSL=false",
                "jdbc.username": configuration.mysql.username,
                "jdbc.password": configuration.mysql.password,
            }
            outer_adapter["properties"] = properties
            outer_adapters.append(outer_adapter)
            groups = [{"groupId": "g1", "outerAdapters": outer_adapters}]
            canal_adapters = conf.get("canal.conf").get("canalAdapters") or []
            for adapter in canal_adapters[:]:
                if adapter.get("instance") == cluster_id:
                    canal_adapters.remove(adapter)
            canal_adapters.append({"instance": cluster_id, "groups": groups})
            conf["canal.conf"]["canalAdapters"] = canal_adapters
            file_context.seek(0)
            file_context.truncate()
            yaml.dump(conf, file_context)

    def _canal_adapter_rdb(self, cluster_id: str):
        rdb_files = os.listdir(RDB_CONF_PATH)
        for rdb_file in rdb_files:
            with open(RDB_CONF_PATH + rdb_file, "r", encoding="utf-8") as file_context:
                rdb_info = file_context.read()
                conf = yaml.safe_load(rdb_info)
                conf.update({"dataSourceKey": cluster_id})
                conf.update({"destination": cluster_id})
                conf.update({"outerAdapterKey": cluster_id})
            with open(
                CANAL_ADAPTER_CONF_PATH + 'rdb/' + cluster_id + "_" + rdb_file, "w", encoding="utf-8"
            ) as file_context:
                yaml.dump(conf, file_context)

    def _canal_synchronize_etl(self, cluster_id: str):
        """
        Complete data synchronization
        """
        rdb_files = os.listdir(CANAL_ADAPTER_CONF_PATH + 'rdb')
        for rdb_file in rdb_files:
            if not rdb_file.startswith(cluster_id):
                continue
            try:
                self._execute_synchronize_etl(cluster_id, rdb_file)
            except retrying.RetryError as error:
                LOGGER.error(f"synchronize {rdb_file} fail")
                raise SynchronizeError("cluster:{} synchronize {} failed, with msg: {}".format(cluster_id, rdb_file, error))

    @retry(retry_on_result=lambda result: result is False, stop_max_attempt_number=3, wait_fixed=20000)
    def _execute_synchronize_etl(self, cluster_id: str, rdb_file: str):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(('8.8.8.8', 80))
            ip_address = sock.getsockname()[0]
        finally:
            sock.close()
        result = BaseResponse.get_response(
            method="Post", url="http://" + ip_address + ":8081/etl/rdb/" + cluster_id + "/" + rdb_file
        )
        if "succeeded" not in result:
            return False
        if result.get("succeeded"):
            return True
        if re.match(r".*doesn't exist$", result.get("errorMessage")):
            return True
        return False

    @staticmethod
    def _restart_canal():
        os.system(f"bash {CANAL_BIN_PATH}restart.sh")
        os.system(f"bash {CANAL_ADAPTER_BIN_PATH}restart.sh")
