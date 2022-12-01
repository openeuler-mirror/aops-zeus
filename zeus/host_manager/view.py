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
from typing import Dict, Tuple, List, Iterable

import requests
from flask import jsonify, request

from vulcanus.multi_thread_handler import MultiThreadHandler
from zeus.conf.constant import CERES_HOST_INFO, CHECK_WORKFLOW_HOST_EXIST
from vulcanus.restful.status import (
    SUCCEED,
    DATABASE_CONNECT_ERROR,
    NO_DATA,
    TOKEN_ERROR,
    DATABASE_DELETE_ERROR
)
from vulcanus.restful.response import BaseResponse
from vulcanus.database.helper import operate
from vulcanus.database.table import User, Host
from vulcanus.log.log import LOGGER
from zeus.database.proxy.host import HostProxy
from zeus.conf import configuration
from zeus.database import SESSION
from zeus.account_manager.cache import UserCache
from zeus.function.verify.host import (
    HostSchema,
    DeleteHostSchema,
    GetHostSchema,
    AddHostGroupSchema,
    DeleteHostGroupSchema,
    GetHostGroupSchema,
    GetHostInfoSchema
)


class AddHost(BaseResponse):
    """
    Interface for add host.
    Restful API: post
    """
    proxy = ""

    def _verify_user(self, username: str, password: str) -> Tuple[int, str]:
        # query from cache first
        user = UserCache.get(username)
        if user is None:
            LOGGER.error("no such user")
            return NO_DATA, ""

        res = User.check_hash_password(user.password, password)
        if not res:
            LOGGER.error("wrong username or password.")
            return TOKEN_ERROR, ""

        return SUCCEED, user.token

    def _handle(self, args: Dict) -> Tuple[int, Dict]:
        self.proxy = HostProxy()
        if not self.proxy.connect(SESSION):
            return DATABASE_CONNECT_ERROR, {}

        status_code, token = self._verify_user(
            args['username'], args.pop('password'))
        if status_code != SUCCEED:
            return status_code, {}

        status_code = self.proxy.add_host(args)
        if status_code == SUCCEED:
            return status_code, {"token": token}

        return status_code, {}

    def post(self):
        """
        Add host

        Args:
             (list)
            key (str)

        Returns:
            dict: response body
        """
        return jsonify(self.handle_request(HostSchema, self, need_token=False, debug=False))


class DeleteHost(BaseResponse):
    """
    Interface for delete host.
    Restful API: DELETE
    """

    def _handle(self, args):
        """
        Handle function

        Args:
            args (dict)

        Returns:
            int: status code
            dict: response body
        """
        proxy = HostProxy()
        if not proxy.connect(SESSION):
            return DATABASE_CONNECT_ERROR, {}

        args.pop('username')
        resp = self.get_response(
            'POST',
            f'http://{configuration.diana["IP"]}:{configuration.diana["PORT"]}{CHECK_WORKFLOW_HOST_EXIST}',
            args,
            {'content-type': 'application/json',
             'access_token': request.headers.get('access_token')}
        )

        res = {
            'succeed_list': [],
            'fail_list': {}
        }

        if resp.get('code') != SUCCEED:
            LOGGER.error('No valid information can be obtained when query'
                         'whether the host is running in the workflow')
            res['fail_list'].update(zip(args['host_list'],
                                        len(args['host_list']) * ("query workflow fail",)))
            return DATABASE_DELETE_ERROR, res

        host_id_in_workflow = []
        host_id_not_in_workflow = []
        for host_id in resp.get('result'):
            if resp.get('result')[host_id]:
                host_id_in_workflow.append(host_id)
            else:
                host_id_not_in_workflow.append(host_id)

        res['fail_list'].update(zip(host_id_in_workflow,
                                    len(host_id_in_workflow) * ("There are workflow in check",)))

        if len(host_id_not_in_workflow) == 0:
            return DATABASE_DELETE_ERROR, res

        args['host_list'] = host_id_not_in_workflow
        status_code, result = proxy.delete_host(args)
        result['fail_list'].update(res['fail_list'])
        result.pop('host_info')
        return status_code, result

    def delete(self):
        """
        Delete host

        Args:
            host_list (list): host id list

        Returns:
            dict: response body
        """
        return jsonify(self.handle_request(DeleteHostSchema, self))


class GetHost(BaseResponse):
    """
    Interface for get host.
    Restful API: POST
    """

    def post(self):
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
        return jsonify(self.handle_request_db(GetHostSchema,
                                              HostProxy(),
                                              'get_host',
                                              SESSION))


class GetHostCount(BaseResponse):
    """
    Interface for get host count.
    Restful API: POST
    """

    def post(self):
        """
        Get host

        Args:

        Returns:
            dict: response body
        """
        return jsonify(self.handle_request_db(None,
                                              HostProxy(),
                                              'get_host_count',
                                              SESSION))


class AddHostGroup(BaseResponse):
    """
    Interface for add host group.
    Restful API: POST
    """

    def post(self):
        """
        Add host group

        Args:
            host_group_name (str): group name
            description (str): group description

        Returns:
            dict: response body
        """
        return jsonify(self.handle_request_db(AddHostGroupSchema,
                                              HostProxy(),
                                              'add_host_group',
                                              SESSION))


class DeleteHostGroup(BaseResponse):
    """
    Interface for delete host group.
    Restful API: DELETE
    """

    def delete(self):
        """
        Delete host group

        Args:
            host_group_list (list): group name list

        Returns:
            dict: response body
        """
        return jsonify(self.handle_request_db(DeleteHostGroupSchema,
                                              HostProxy(),
                                              'delete_host_group',
                                              SESSION))


class GetHostGroup(BaseResponse):
    """
    Interface for get host group.
    Restful API: POST
    """

    def post(self):
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
        return jsonify(self.handle_request_db(GetHostGroupSchema,
                                              HostProxy(),
                                              'get_host_group',
                                              SESSION))


class GetHostInfo(BaseResponse):
    """
    Interface for get host info.
    Restful API: POST
    """

    def _handle(self, args) -> tuple:
        """
        Handle function

        Args:
            args (dict): request parameter

        Returns:
            tuple: (status code, result)
        """
        basic = args.get('basic')
        if basic:
            return operate(HostProxy(), args, 'get_host_info', SESSION)
        user = UserCache.get(args.get('username'))
        error_host_infos = self.generate_fail_data(args.get('host_list'))
        if user is None:
            return TOKEN_ERROR, {"host_infos": error_host_infos}

        # query host address from database
        proxy = HostProxy()
        if proxy.connect(SESSION) is None:
            LOGGER.error("connect to database error")
            return DATABASE_CONNECT_ERROR, {"host_infos": error_host_infos}

        status, host_address_list = proxy.get_host_address(args.get('host_list'))
        if len(host_address_list) == 0:
            LOGGER.warning("database has no such host id.")
            return NO_DATA, {"host_infos": error_host_infos}

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
        multi_thread_handler = MultiThreadHandler(self.get_host_info, tasks, None)
        multi_thread_handler.create_thread()
        result_list = multi_thread_handler.get_result()

        # analyse execute result and generate target data format
        host_infos = self.analyse_query_result(args.get('host_list'), result_list)
        return SUCCEED, {"host_infos": host_infos}

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

        if response.status_code == SUCCEED:
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

    def post(self):
        """
        Get host info

        Args:
            host_list (list): host id list
            basic (bool)

        Returns:
            dict: response body
        """
        return jsonify(self.handle_request(GetHostInfoSchema, self))
