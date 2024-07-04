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

import yaml
from async_task.base import AsyncTask
from vulcanus import LOGGER
from vulcanus.conf.constant import CANAL_ADAPTER_CONF_PATH, CANAL_CONF_PATH, CANAL_PROPERTIES, CANAL_ADAPTER_APPLICATION
from vulcanus.exceptions import SynchronizeError


class ClusterSynchronizeCancelTask(AsyncTask):
    # The name of the task registered in celery
    name = "cluster_synchronize_cancel_task"

    def run(self, cluster_id, *args, **kwargs):
        """
        Run the task with the given host model and task info.

        Args:
            cluster_id: cluster_id.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            None
        """
        self._canal_deployer_cancel(cluster_id)
        self._canal_adapter_cancel(cluster_id)

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
        cluster_id = kwargs.get("cluster_id")
        result = {"status": "succeed", "cluster_id": cluster_id}
        self.send_notification(channel=self.name, message=json.dumps(result))
        LOGGER.info("cancel synchronize " + str(cluster_id) + "succeed")

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
        cluster_id = kwargs.get("cluster_id")
        LOGGER.info("cancel synchronize " + str(cluster_id) + "failed")

    def _canal_deployer_cancel(self, cluster_id: str):
        """
        configure canal_deployer
        """
        try:
            with open(CANAL_PROPERTIES, mode='r+', encoding="utf-8") as canal_properties:
                conf = canal_properties.read()
                destinations_config = re.search("canal.destinations.*", conf)
                destinations = list(set(destinations_config.group(0).replace('canal.destinations = ', '').split(',')))
                destinations.remove(cluster_id)
                new_conf = re.sub(
                    "canal.destinations.*", 'canal.destinations = ' + ','.join(destinations), conf, count=0, flags=0
                )
                canal_properties.seek(0)
                canal_properties.truncate()
                canal_properties.write(new_conf)

            if os.path.exists(CANAL_CONF_PATH + cluster_id):
                shutil.rmtree(CANAL_CONF_PATH + cluster_id)

        except (FileNotFoundError, IOError) as error:
            self.update_state(state='FAILURE')
            raise SynchronizeError(
                "cluster:{} cancel synchronize canal_deployer failed, with msg{}".format(cluster_id, error))

    def _canal_adapter_cancel(self, cluster_id: str):
        """
        configure canal_adapter cancel
        """
        try:
            with open(CANAL_ADAPTER_APPLICATION, mode='r+', encoding="utf-8") as file_context:
                application = file_context.read()
                conf = yaml.safe_load(application)
                if not conf.get("canal.conf"):
                    self.update_state(state='FAILURE')
                    raise SynchronizeError(
                        "cluster:{} cancel synchronize canal_adapter failed, not found canal.conf")
                data_sources_conf = conf.get("canal.conf").get("srcDataSources")
                if not data_sources_conf:
                    self.update_state(state='FAILURE')
                    raise SynchronizeError(
                        "cluster:{} cancel synchronize canal_adapter failed, not found srcDataSources")
                if data_sources_conf.get(cluster_id):
                    data_sources_conf.pop(cluster_id)

                canal_adapters = conf.get("canal.conf").get("canalAdapters")
                for adapter in canal_adapters[:]:
                    if adapter.get("instance") == cluster_id:
                        canal_adapters.remove(adapter)
                file_context.seek(0)
                file_context.truncate()
                yaml.dump(conf, file_context)

            rdb_files = os.listdir(os.path.join(CANAL_ADAPTER_CONF_PATH, 'rdb'))
            for rdb_file in rdb_files:
                if rdb_file.startswith(cluster_id):
                    file_path = os.path.join(CANAL_ADAPTER_CONF_PATH, 'rdb/', rdb_file)
                    os.remove(file_path)
        except (FileNotFoundError, IOError, AttributeError) as error:
            self.update_state(state='FAILURE')
            raise SynchronizeError(
                "cluster:{} cancel synchronize canal_adapter failed, with msg{}".format(cluster_id, error))
