#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2022-2023. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
import os
import re
from functools import lru_cache

from async_task.settings import configuration
from vulcanus.registry.register_service.zookeeper import ZookeeperRegisterCenter
from vulcanus.timed import TimedTask


class DynamicUpdateUpstreamTask(TimedTask):
    """
    Timed correct data tasks
    """

    name = "upstream"
    zk = ZookeeperRegisterCenter(hosts=f"{configuration.zookeeper.host}:{configuration.zookeeper.port}")
    nginx = "/etc/nginx/nginx.conf"

    def execute(self):
        """
        Start the correct after the specified time of day.
        """
        if not self.zk.connected:
            self.zk.connect()

        self.config = self._load_nginx_config(config=self.nginx)
        if not self.config:
            return

        services = {
            child: self.zk.get_all_service_instance(service_name=child) for child in self.zk.get_children("/services")
        }
        if not services:
            return

        self._reload = False
        for service_name, instance_list in services.items():
            self._update_upstream(service_name, instance_list)

        if self._reload:
            self._save_and_reload_nginx()

    def _load_nginx_config(self, config):
        """
        Load the nginx config of the service

        Args:
            config: ngxin config path

        Returns:
            the config of the service
        """
        if not os.path.exists(config):
            return None
        try:
            with open(config, "r") as file:
                return file.read()
        except IOError:
            return None

    @lru_cache(maxsize=None, typed=True)
    def _replace_upstream(self, upstream_name, value):
        """
        Replace the upstream of the service

        Args:
            config: the config of the service
            upstream_name: the name of the upstream
            value: the new value of the upstream

        Returns:
            the config of the service after the replacement
        """
        pattern = r"upstream\s+" + re.escape(upstream_name) + r"\s*{([^}]*)}"
        regex = re.compile(pattern, re.MULTILINE | re.DOTALL)
        replace_config = regex.sub("upstream " + upstream_name + " {\n" + value + "\n}", self.config)
        self._reload = True
        return replace_config

    def _save_and_reload_nginx(self):
        """
        Save the config of the service and reload the nginx

        """
        try:
            with open(self.nginx, "w") as file:
                file.write(self.config)
        except IOError:
            return False

        os.system("nginx -s reload")

    def _update_upstream(self, service_name, instance_list):
        """
        Update the upstream of the service
        """
        microservice = [instance["address"] + ":" + str(instance["port"]) for instance in instance_list]
        wait_replace_upstream = os.linesep.join(["server " + service + ";" for service in sorted(microservice)])
        self.config = self._replace_upstream(service_name, wait_replace_upstream)
