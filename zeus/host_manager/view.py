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
from typing import Dict, Iterable, List, Tuple, Union

import paramiko
import requests
from flask import jsonify, request, send_file
from marshmallow import Schema
from marshmallow.fields import Boolean

from vulcanus.database.helper import operate
from vulcanus.database.table import Host
from vulcanus.log.log import LOGGER
from vulcanus.multi_thread_handler import MultiThreadHandler
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
from vulcanus.restful.response import BaseResponse
from vulcanus.restful.serialize.validate import validate
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
    AddHostBatchSchema,
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
            return self.response(code=state.DATABASE_CONNECT_ERROR,
                                 data={"host_infos": error_host_infos})

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
            params.get('host_ip'), params.get('ssh_port'), params.get('ssh_user'),
            params.get('password'))
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


class AddHostBatch(BaseResponse):
    """
    Interface for add host batch from web.
    Restful API: POST
    """

    add_succeed = "succeed"
    add_failed = "failed"

    def post(self):
        """
        Handle function

        Returns:
            tuple:
                status code, message, data
        """
        self.add_result = []
        # Validate request
        status, args = self.verify_request(AddHostBatchSchema)
        if status != state.SUCCEED:
            return self.response(code=status, data=self.add_result)

        # Connect database
        proxy = HostProxy()
        if not proxy.connect(SESSION):
            LOGGER.error("connect to database error")
            self.update_add_result(
                args["host_list"],
                {"result": self.add_failed, "reason": "connect to database error"})
            return self.response(code=state.DATABASE_CONNECT_ERROR, data=self.add_result)

        # Query hosts with groups, validate hostname or host address
        status, hosts, groups = proxy.get_hosts_and_groups(args.get('username'))
        if status != state.SUCCEED:
            self.update_add_result(
                args["host_list"],
                {"result": self.add_failed, "reason": "query data from database fail"})
            return self.response(code=status, data=self.add_result)

        valid_hosts = self.validate_host_info(args, hosts, groups)
        if len(valid_hosts) == 0:
            return self.response(code=state.ADD_HOST_FAILED,
                                 message="invalid host info or all hosts has been added",
                                 data=self.add_result)

        # Generate Rsa-key pair and save public_key on host
        multi_thread = MultiThreadHandler(lambda data: self.update_rsa_key_to_host(*data),
                                          valid_hosts, None)
        multi_thread.create_thread()
        result = multi_thread.get_result()

        # Add host
        status = proxy.add_host_batch(result)
        if status != state.SUCCEED:
            self.update_add_result(valid_hosts,
                                   {"result": self.add_failed, "reason": "Insert Database error"})
            return self.response(code=status, data=self.add_result)
        self.update_add_result(valid_hosts, {"result": self.add_succeed})

        # Judge the returned status code
        if len(valid_hosts) < len(args["host_list"]):
            return self.response(code=state.PARTIAL_SUCCEED, data=self.add_result)
        return self.response(code=status, data=self.add_result)

    def validate_host_info(self, data: dict, hosts: list, groups: list) -> list:
        """
        Check whether the data is repeated, and generate a list of valid data

        Args:
            data(dict): e.g
                {
                    "host_list":[{
                        "host_ip": "127.0.0.1,
                        "ssh_port": 22,
                        "ssh_user": "root",
                        "password": "password",
                        "host_name": "test_host",
                        "host_group_name": "test_group",
                        "management": False,
                    }],
                    "username": "admin"
                }
            hosts(list): list of host object
            groups(list): list of host group object
        Returns:
            list: e.g
            [{
                "host_ip": "127.0.0.1,
                "ssh_port": 22,
                "ssh_user": "root",
                "password": "password",
                "host_name": "test_host",
                "host_group_name": "test_group",
                "management": False,
            }]
        """
        valid_host = []
        group_id_info = {}
        for group in groups:
            group_id_info[group.host_group_name] = group.host_group_id

        for host_info in data["host_list"]:
            if host_info.get("host_group_name") not in group_id_info:
                LOGGER.warning(f"invalid host group when add host {host_info['host_name']}")
                self.update_add_result(
                    [host_info], {"result": self.add_failed, "reason": "invalid host group name"})
                continue

            password = host_info.pop("password")
            host_info.update({
                "host_group_id": group_id_info.get(host_info['host_group_name']),
                "user": data["username"]}
            )
            host = Host(**host_info)
            if host in hosts:
                LOGGER.warning(
                    f"host name or host ip is existed when add host {host_info['host_name']}.")
                self.update_add_result([host_info], {
                    "result": self.add_failed,
                    "reason": "host name or host ip is existed!"
                })
                continue

            valid_host.append((host, password))
        return valid_host

    @staticmethod
    def update_rsa_key_to_host(host: Host, password: str) -> Host:
        """
        save ssh public key to client and update its private key in host

        Args:
            host(Host): host object
            password(str): password for ssh login

        Returns:
            host object
        """
        status, pkey = save_ssh_public_key_to_client(
            host.host_ip, host.ssh_port, host.ssh_user, password)
        if status == state.SUCCEED:
            host.status = HostStatus.ONLINE
            host.pkey = pkey
        return host

    def update_add_result(self, hosts: list, update_info: dict) -> None:
        """
        update result of add host

        Args:
            hosts: list of host info
            update_info(dict): info which needs to be updated

        """
        if len(hosts) == 0:
            return

        if isinstance(hosts[0], dict):
            for host in hosts:
                new_host = {
                    "host_ip": host.get("host_ip"),
                    "ssh_port": host.get("ssh_port"),
                    "ssh_user": host.get("ssh_user"),
                    "host_name": host.get("host_name"),
                    "host_group_name": host.get("host_group_name"),
                    "management": host.get("management")
                }
                new_host.update(update_info)
                self.add_result.append(new_host)
        else:
            for host, _ in hosts:
                new_host = {
                    "host_ip": host.host_ip,
                    "ssh_port": host.ssh_port,
                    "ssh_user": host.ssh_user,
                    "host_name": host.host_name,
                    "host_group_name": host.host_group_name,
                    "management": host.management,
                }
                new_host.update(update_info)
                self.add_result.append(new_host)

    def verify_request(self, schema: Schema) -> tuple:
        """
        Verify args and token

        Args:
            schema(object): the class of the validator

        Returns:
            tuple:
                status code, dict
        """
        args = request.get_json() or {}
        args, errors = validate(schema, args)

        if errors:
            LOGGER.error(errors)
            self.parse_validate_error(args.get("host_list"), errors.get("host_list"))
            return state.PARAM_ERROR, {}

        if self.validate_host_repeated(args.get("host_list")):
            return state.PARAM_ERROR, {}

        if self.verify_token(request.headers.get('access_token'), args) != state.SUCCEED:
            self.update_add_result(
                args.get("host_list"), {"result": self.add_failed, "reason": state.TOKEN_ERROR})
            return state.TOKEN_ERROR, {}

        for host in args.get('host_list'):
            if host["management"] in Boolean.truthy:
                host["management"] = True
            else:
                host["management"] = False

        return state.SUCCEED, args

    def parse_validate_error(self, host_list: list, errors: Union[list, dict]) -> None:
        """
        Parse the error and update it to add result

        Args:
            host_list(list): host info list
            errors(dict or list): validation log,
            if the host list is in the wrong format, errors data format will be a list;
            e.g
                ['Not a valid list.']
            if part of the host list is in the wrong format, errors data will be a dict.
            e.g
                {0: {'host_name': ['Not a valid string.']}}

        Return:
           No Return
        """
        if not host_list or not isinstance(host_list, list):
            self.add_result.append(errors[0])
            return

        if not isinstance(errors, dict):
            return self.update_add_result(
                host_list, {"result": self.add_failed, "reason": errors[0]})

        index_list = list(errors.keys())
        index_list.sort(reverse=True)
        for index in index_list:
            self.update_add_result(
                [host_list.pop(int(index))], {
                    "result": self.add_failed, "reason": errors[index].__str__()
                })

        self.update_add_result(host_list, {"result": self.add_failed})

    def validate_host_repeated(self, host_list: list) -> bool:
        """
        Determine  host name ro ssh host address  is duplicated

        Args:
            host_list(list): host info list

        returns:
            bool: True or False

        """
        host_name_dict = {}
        host_ssh_address_dict = {}
        errors = {}
        for index, host in enumerate(host_list):
            host_ssh_address = f'{host["host_ip"]}:{host["ssh_port"]}'
            if host["host_name"] in host_name_dict:
                errors.update({
                    host_name_dict[host["host_name"]]: "there is a duplicate host name "
                                                       "or host address!"
                })

                errors.update({index: "there is a duplicate host name or host address!"})
                host_ssh_address_dict.update({host_ssh_address: index})
            elif host_ssh_address in host_ssh_address_dict:
                errors.update({
                    host_ssh_address_dict[host_ssh_address]: "there is a duplicate host name "
                                                             "or host address!"
                })

                errors.update({index: "there is a duplicate host name or host address!"})
                host_name_dict.update({host["host_name"]: index})
            else:
                host_name_dict.update({host["host_name"]: index})
                host_ssh_address_dict.update({host_ssh_address: index})

        if errors:
            self.parse_validate_error(host_list, errors)
            return True
        return False
