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
"""
Time:
Author:
Description: Restful APIs for host
"""
import json
import socket
from io import BytesIO
from typing import Dict, Iterable, List, Tuple

import paramiko
import requests
from flask import jsonify, request, send_file

from vulcanus.database.helper import operate
from vulcanus.database.table import Host
from vulcanus.log.log import LOGGER
from vulcanus.multi_thread_handler import MultiThreadHandler
from vulcanus.restful.response import BaseResponse
from vulcanus.restful.resp import state
from vulcanus.restful.resp.state import (
    DATABASE_CONNECT_ERROR,
    DATABASE_DELETE_ERROR,
    DATA_EXIST,
    EXECUTE_COMMAND_ERROR,
    NO_DATA, PARAM_ERROR,
    SSH_AUTHENTICATION_ERROR,
    SSH_CONNECTION_ERROR,
    SUCCEED,
    TOKEN_ERROR
)
from zeus.database.proxy.host import HostProxy
from zeus.account_manager.cache import UserCache
from zeus.conf import configuration
from zeus.conf.constant import (
    CERES_HOST_INFO,
    CHECK_WORKFLOW_HOST_EXIST,
    HOST_TEMPLATE_FILE_CONTENT,
    HostStatus
)
from zeus.database import SESSION
from zeus.function.verify.host import (
    AddHostGroupSchema,
    AddHostSchema,
    DeleteHostGroupSchema,
    DeleteHostSchema,
    GetHostGroupSchema,
    GetHostInfoSchema,
    GetHostSchema,
    HostSchema
)
from zeus.host_manager.ssh import SSH, generate_key


class DeleteHost(BaseResponse):
    """
    Interface for delete host.
    Restful API: DELETE
    """

    @BaseResponse.handle(schema=DeleteHostSchema, proxy=HostProxy(), session=SESSION)
    def delete(self, callback: HostProxy, **params):
        """
        Delete host

        Args:
            host_list (list): host id list

        Returns:
            dict: response body
        """
        status_code, result = callback.delete_host(params)
        return self.response(code=status_code, data=result)


class GetHost(BaseResponse):
    """
    Interface for get host.
    Restful API: POST
    """

    @BaseResponse.handle(schema=GetHostSchema, proxy=HostProxy(), session=SESSION)
    def post(self, callback: HostProxy, **params):
        """
        Get host

        Args:
            host_group_list (list): host group name list
            management (bool): whether it's a manage node
            sort (str): sort according to specified field
            direction (str): sort direction
            page (int): current page
            per_page (int): count per page

        Returns:
            dict: response body
        """
        status_code, result = callback.get_host(params)
        return self.response(code=status_code, data=result)


class GetHostCount(BaseResponse):
    """
    Interface for get host count.
    Restful API: POST
    """
    @BaseResponse.handle(proxy=HostProxy(), session=SESSION)
    def post(self, callback: HostProxy, **params):
        """
        Get host

        Args:

        Returns:
            dict: response body
        """
        status_code, result = callback.get_host_count(params)
        return self.response(code=status_code, data=result)


class AddHostGroup(BaseResponse):
    """
    Interface for add host group.
    Restful API: POST
    """

    @BaseResponse.handle(schema=AddHostGroupSchema, proxy=HostProxy(), session=SESSION)
    def post(self, callback: HostProxy, **params):
        """
        Add host group

        Args:
            host_group_name (str): group name
            description (str): group description

        Returns:
            dict: response body
        """
        status_code = callback.add_host_group(params)
        return self.response(code=status_code)


class DeleteHostGroup(BaseResponse):
    """
    Interface for delete host group.
    Restful API: DELETE
    """

    @BaseResponse.handle(schema=DeleteHostGroupSchema, proxy=HostProxy(), session=SESSION)
    def delete(self, callback: HostProxy, **params):
        """
        Delete host group

        Args:
            host_group_list (list): group name list

        Returns:
            dict: response body
        """

        status_code, result = callback.delete_host_group(params)
        return self.response(code=status_code, data=result)


class GetHostGroup(BaseResponse):
    """
    Interface for get host group.
    Restful API: POST
    """

    @BaseResponse.handle(schema=GetHostGroupSchema, proxy=HostProxy(), session=SESSION)
    def post(self, callback: HostProxy, **params):
        """
        Get host group

        Args:
            sort (str): sort according to specified field
            direction (str): sort direction
            page (int): current page
            per_page (int): count per page

        Returns:
            dict: response body
        """
        status_code, result = callback.get_host_group(params)
        return self.response(code=status_code, data=result)


class GetHostInfo(BaseResponse):
    """
    Interface for get host info.
    Restful API: POST
    """

    @staticmethod
    def get_host_info(data: Dict) -> Dict:
        """
        Get host info from ceres.

        Args:
            data(dict): e.g
                {
                    "host_id": xx,
                    "info_type": ["cpu", "os", "memory", "disk"],
                    "address": "ip:port",
                    "headers": {
                        "content-type": "application/json",
                        "access_token": "host token"
                    }
                }

        Returns:
            dict: e.g
            {
                "host_id":"host id",
                "host_info": {
                    "cpu": {...},
                    "os":  {...},
                    "memory": {...},
                    "disk": [{...}]
                }
            }
        """
        headers = data.pop('headers')
        url = f'http://{data.pop("address")}{CERES_HOST_INFO}'
        res = {'host_id': data.get('host_id'), 'host_info': {}}
        info_type = data.get('info_type')
        try:
            response = requests.post(url,
                                     data=json.dumps(info_type),
                                     headers=headers,
                                     timeout=5)
        except requests.exceptions.ConnectionError as error:
            LOGGER.error(error)
            return res

        if response.status_code == requests.status_codes.ok:
            res['host_info'] = response.json().get('resp', {})
            return res
        LOGGER.warning('Failed to get host info!')
        return res

    @staticmethod
    def generate_fail_data(host_list: Iterable) -> List[dict]:
        """
        convert host list to fail data format

        Args:
            host_list (Iterable): e.g
                [host_id1, host_id2... ] or { host_id1, host_id2...}

        Returns:
            dict: e.g
                [
                    {
                        "host_id": host_id,
                        "host_info":{}
                    }
                    ...
                ]
        """
        res = []
        for host_id in host_list:
            res.append({
                "host_id": host_id,
                "host_info": {}
            })
        return res

    def analyse_query_result(self, all_host: List[str],
                             multithreading_execute_result: List) -> List:
        """
        Analyze multi-threaded execution results,
        find out the data which fails to execute,
        and generate the final execution result.
        Args:
            all_host(list): e.g
                [host_id1, host_id2... ]
            multithreading_execute_result(list): e.g
                [
                    {
                    "host_id":"success host id",
                    "host_info": {
                        "cpu": {...},
                        "os":" {...},
                        "memory": {...}.
                        "disk": [{...}]
                        },
                    }
                ]

        Returns:
            list: e.g
                [
                    {
                    "host_id":"success host id",
                    "host_info": {
                        "cpu": {...},
                        "os":" {...},
                        "memory": {...}.
                        "disk": [{...}]
                        },
                    }.
                    {
                    "host_id":"fail host id",
                    "host_info": {}
                    }.
                ]


        """
        host_infos = []
        success_host = set()
        for result in multithreading_execute_result:
            if result.get('host_info'):
                host_infos.append(result)
                success_host.add(result.get('host_id'))

        fail_host = set(all_host) - success_host
        host_infos.extend(self.generate_fail_data(fail_host))
        return host_infos

    @BaseResponse.handle(schema=GetHostInfoSchema)
    def post(self, **params):
        """
        Get host info

        Args:
            host_list (list): host id list
            basic (bool)

        Returns:
            dict: response body
        """
        basic = params.get('basic')
        proxy = HostProxy()
        if proxy.connect(SESSION) is None:
            LOGGER.error("connect to database error")
            return self.response(code=state.DATABASE_CONNECT_ERROR, data={"host_infos": error_host_infos})

        if basic:
            status_code, result = proxy.get_host_info(params)
            return self.response(code=status_code, data=result)
        user = UserCache.get(params.get('username'))
        error_host_infos = self.generate_fail_data(params.get('host_list'))
        if user is None:
            return self.response(code=state.TOKEN_ERROR, data={"host_infos": error_host_infos})

        # query host address from database

        _, host_address_list = proxy.get_host_address(
            params.get('host_list'))
        if len(host_address_list) == 0:
            LOGGER.warning("database has no such host id.")
            return self.response(code=state.NO_DATA, data={"host_infos": error_host_infos})

        # generate tasks
        tasks = []
        for host_id, address in host_address_list.items():
            tasks.append({
                'host_id': host_id,
                'info_type': [],
                'address': address,
                "headers": {'content-type': 'application/json',
                            'access_token': user.token}
            })
        # execute multi threading
        multi_thread_handler = MultiThreadHandler(
            self.get_host_info, tasks, None)
        multi_thread_handler.create_thread()
        result_list = multi_thread_handler.get_result()

        # analyse execute result and generate target data format
        host_infos = self.analyse_query_result(
            params.get('host_list'), result_list)
        return self.response(code=state.SUCCEED, data={"host_infos": host_infos})


class AddHost(BaseResponse):
    """
    Interface for add host from web.
    Restful API: POST
    """

    def validate_host_info(self, host_info: dict) -> Tuple[int, Host]:
        """
        query hosts info and groups info, validate that the host info is valid
        return host object

        Args:
            host_info (dict): e.g
            {
                "host_name":"host name",
                "ssh_user":"root",
                "password":"password",
                "host_group_name":"host_group_name",
                "host_ip":"127.0.0.1",
                "ssh_port":"22",
                "management":false,
                "username": "admin"
            }

        Returns:
            tuple:
                status code, host object
        """
        status, hosts, groups = self.proxy.get_hosts_and_groups(
            host_info.get('username'))
        if status != state.SUCCEED:
            return status, Host()

        group_id = None
        for group in groups:
            if group.host_group_name == host_info.get('host_group_name'):
                group_id = group.host_group_id

        if group_id is None:
            LOGGER.warning(f"host group doesn't exist "
                           f"which named {host_info.get('host_group_name')} !")
            return state.PARAM_ERROR, Host()

        host = Host(**{
            "host_name": host_info.get("host_name"),
            "ssh_user": host_info.get("ssh_user"),
            "host_group_name": host_info.get("host_group_name"),
            "host_group_id": group_id,
            "host_ip": host_info.get("host_ip"),
            "ssh_port": host_info.get("ssh_port"),
            "user": host_info.get("username"),
            "management": host_info.get("management"),
        })
        if host in hosts:
            return state.DATA_EXIST, Host()
        return state.SUCCEED, host

    @BaseResponse.handle(schema=AddHostSchema)
    def post(self, **params):
        """
        Get host info

        Args:
            args (dict): e.g
            {
                "host_name":"host name",
                "ssh_user":"root",
                "password":"password",
                "host_group_name":"host_group_name",
                "host_ip":"127.0.0.1",
                "ssh_port":"22",
                "management":false,
                "username": "admin"
            }

        Returns:
            dict: response body
        """
        self.proxy = HostProxy()
        if not self.proxy.connect(SESSION):
            LOGGER.error("connect to database error")
            return self.response(code=state.DATABASE_CONNECT_ERROR)

        status, host = self.validate_host_info(params)
        if status != state.SUCCEED:
            return self.response(code=status)

        status, private_key = save_ssh_public_key_to_client(
            params.get('host_ip'), params.get('ssh_port'), params.get('ssh_user'), params.get('password'))
        if status == state.SUCCEED:
            host.pkey = private_key
            host.status = HostStatus.ONLINE
        return self.response(code=self.proxy.add_host(host))


def save_ssh_public_key_to_client(hostname: str, port: int, username: str, password: str) -> tuple:
    """
    generate RSA key pair,save public key to the target host machine

    Args:
        hostname(str):   host ip address
        username(str):   remote login user
        port(int):   remote login port
        password(str)

    Returns:
        tuple:
            status code(int), private key string
    """
    private_key, public_key = generate_key()
    command = f"mkdir -p -m 700 ~/.ssh " \
              f"&& echo {public_key!r} >> ~/.ssh/authorized_keys" \
              f"&& chmod 600 ~/.ssh/authorized_keys"
    try:
        client = SSH(hostname=hostname, username=username,
                     port=port, password=password)
        _, _, stderr = client.execute_command(command)
    except socket.error as error:
        LOGGER.error(error)
        return state.SSH_CONNECTION_ERROR, ""
    except paramiko.ssh_exception.SSHException as error:
        LOGGER.error(error)
        return state.SSH_AUTHENTICATION_ERROR, ""

    if stderr.read().decode("utf8"):
        LOGGER.error(f"save public key on host failed, host ip is {hostname}!")
        return state.EXECUTE_COMMAND_ERROR, ""

    return state.SUCCEED, private_key


class GetHostTemplateFile(BaseResponse):
    """
    Interface for download host template file.
    Restful API: Get
    """

    def get(self):
        """
        download host template file

        Returns:
            BytesIO
        """
        args, verify_code = self.verify_request()
        if verify_code != SUCCEED:
            return self.response(code=TOKEN_ERROR)

        file = BytesIO()
        file.write(HOST_TEMPLATE_FILE_CONTENT.encode('utf-8'))
        file.seek(0)

        return send_file(file, as_attachment=True, attachment_filename="template.csv")
