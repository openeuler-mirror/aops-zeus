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
from typing import Tuple

from flask import Response, json, request, g

from vulcanus.database.helper import operate, judge_return_code
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse
from zeus.account_manager.cache import UserCache
from zeus.database.proxy.host import HostProxy
from zeus.function.model import ClientConnectArgs
from zeus.function.verify.agent import (
    AgentPluginInfoSchema,
    GetHostSceneSchema,
    SetAgentMetricStatusSchema,
    SetAgentPluginStatusSchema
)
from zeus.conf.constant import (
    CERES_PLUGIN_INFO,
    CERES_PLUGIN_START,
    CERES_PLUGIN_STOP,
    CERES_APPLICATION_INFO,
    CERES_COLLECT_ITEMS_CHANGE,
    CHECK_IDENTIFY_SCENE
)
from zeus.conf import configuration
from zeus.host_manager.ssh import execute_command_and_parse_its_result


class AgentPluginInfo(BaseResponse):
    """
    Interface for user get agent plugin info
    """

    @BaseResponse.handle(schema=AgentPluginInfoSchema)
    def get(self, **params) -> Response:
        """
        Interface for get agent plugin info

        Returns:
            Response: response body
        """
        proxy = HostProxy()
        if not proxy.connect(g.session):
            return self.response(state.DATABASE_CONNECT_ERROR)
        status, host = proxy.get_host_info(
            {"username": params["username"], "host_list": [params["host_id"]]})
        if status != state.SUCCEED:
            LOGGER.error(f"query host {params['host_id']} info failed.")
            return self.response(code=status)
        if len(host) == 0:
            return self.response(state.NO_DATA)

        status, result = execute_command_and_parse_its_result(
            ClientConnectArgs(host[0].get("host_ip"), host[0].get("ssh_port"),
                              host[0].get("ssh_user"), host[0].get("pkey")), CERES_PLUGIN_INFO)
        if status != state.SUCCEED:
            return self.response(code=status)

        return self.response(code=status, data={"info": json.loads(result)})


class GetHostScene(BaseResponse):
    """
    Interface for get host scene.
    Restful API: get
    """

    @staticmethod
    def __get_check_url(route: str) -> Tuple[str, dict]:
        """
        Get url of check restful

        Args:
            route(str): route of restful

        Returns:
            tuple: (url, header)
        """
        check_ip = configuration.diana.get("IP")
        check_port = configuration.diana.get("PORT")
        check_url = f"http://{check_ip}:{check_port}{route}"
        check_header = {
            "Content-Type": "application/json; charset=UTF-8"
        }
        return check_url, check_header

    @staticmethod
    def __get_scene_data_from_ceres(host: dict) -> dict:
        """
        Get applications and collect items required for scene identification
        form agent

        Args:
            host(dict): host ssh connect info

        Returns:
            dict
        """

        host_scene_info = {"applications": [], "collect_items": {}}
        client_connect_args = ClientConnectArgs(host.get("host_ip"), host.get("ssh_port"),
                                                host.get("ssh_user"), host.get("pkey"))
        status, running_applications = execute_command_and_parse_its_result(
            client_connect_args, CERES_APPLICATION_INFO)
        if status == state.SUCCEED:
            host_scene_info["applications"] = json.loads(running_applications)

        status, collect_items = execute_command_and_parse_its_result(client_connect_args,
                                                                     CERES_PLUGIN_INFO)
        if status == state.SUCCEED:
            host_scene_info["collect_items"] = json.loads(collect_items)
        return host_scene_info

    @BaseResponse.handle(schema=GetHostSceneSchema)
    def get(self, **params) -> Response:
        """
        Get host scene

        Returns:
            dict: response body
        """
        proxy = HostProxy()
        if not proxy.connect(g.session):
            return self.response(state.DATABASE_CONNECT_ERROR)

        status, host_list = proxy.get_host_info(
            {"username": params["username"], "host_list": [params["host_id"]]})
        if status != state.SUCCEED:
            LOGGER.error(f"query host {params['host_id']} info failed.")
            return self.response(code=status)
        if len(host_list) == 0:
            return self.response(code=state.NO_DATA)
        # get application info and collect items from agent
        host_scene_info = self.__get_scene_data_from_ceres(host_list[0])

        # get scene and recommend collect items from check
        check_url_get_scene, check_header = self.__get_check_url(CHECK_IDENTIFY_SCENE)
        check_header['access_token'] = request.headers.get("access_token")
        response = self.get_response("post", check_url_get_scene, host_scene_info, check_header)
        status_code = response.get("label")
        if status_code != state.SUCCEED:
            LOGGER.error("Get scene of host %s from check failed.", params["host_id"])
            return self.response(code=status_code)

        scene_ret = response.get("data", dict()).get("scene_name")
        status_code = proxy.save_scene({"host_id": params["host_id"], "scene": scene_ret})
        if status_code != state.SUCCEED:
            LOGGER.error("save scene of host %s failed.", params["host_id"])
            return self.response(code=status_code)

        response_data = {"scene": scene_ret,
                         "collect_items": response.get("collect_items")}
        return self.response(code=status_code, data=response_data)


class SetAgentPluginStatus(BaseResponse):
    """
    Interface for get host scene.
    Restful API: POST
    """
    status_url_map = {
        "active": CERES_PLUGIN_START,
        "inactive": CERES_PLUGIN_STOP
    }

    @BaseResponse.handle(schema=SetAgentPluginStatusSchema)
    def post(self, **params) -> Response:
        """
        Get host scene

        Returns:
            dict: response body
        """
        ret = {"failed_list": [], "succeed_list": []}
        proxy = HostProxy()
        if not proxy.connect(g.session):
            return self.response(state.DATABASE_CONNECT_ERROR)

        status, host = proxy.get_host_info(
            {"username": params["username"], "host_list": [params["host_id"]]})
        if status != state.SUCCEED:
            LOGGER.error(f"query host {params['host_id']} info failed.")
            return self.response(code=status)

        if len(host) == 0:
            return self.response(state.NO_DATA)

        plugin_status_list = params.get('plugins')
        for plugin_name, plugin_status in plugin_status_list.items():
            if plugin_status not in SetAgentPluginStatus.status_url_map:
                LOGGER.error("Unknown plugin status of host %s plugin %s." %
                             params.get("host_id"), plugin_name)
                ret["failed_list"].append(plugin_name)
                continue

            command = SetAgentPluginStatus.status_url_map[plugin_status] % plugin_name
            status, result = execute_command_and_parse_its_result(
                ClientConnectArgs(host[0].get("host_ip"), host[0].get("ssh_port"),
                                  host[0].get("ssh_user"), host[0].get("pkey")), command)
            if status != state.SUCCEED:
                ret["failed_list"].append(plugin_name)
            else:
                ret["succeed_list"].append(plugin_name)

        return self.response(code=judge_return_code(ret, state.SET_AGENT_PLUGIN_STATUS_FAILED),
                             data=ret)


class SetAgentMetricStatus(BaseResponse):
    """
    Interface for get host scene.
    Restful API: POST
    """

    @BaseResponse.handle(schema=SetAgentMetricStatusSchema)
    def post(self, **params) -> Response:
        """
        Set agent metric status

        Returns:
            dict: response body
        """
        proxy = HostProxy()
        if not proxy.connect(g.session):
            return self.response(state.DATABASE_CONNECT_ERROR)

        status, host = proxy.get_host_info(
            {"username": params["username"], "host_list": [params["host_id"]]})
        if status != state.SUCCEED:
            LOGGER.error(f"query host {params['host_id']} info failed.")
            return self.response(code=status)
        if len(host) == 0:
            return self.response(state.NO_DATA)

        command = CERES_COLLECT_ITEMS_CHANGE % json.dumps(params.get("plugins"))
        status, result = execute_command_and_parse_its_result(
            ClientConnectArgs(host[0].get("host_ip"), host[0].get("ssh_port"),
                              host[0].get("ssh_user"), host[0].get("pkey")), command)
        if status == state.SUCCEED:
            return self.response(code=status, data=json.loads(result))

        return self.response(code=status)
