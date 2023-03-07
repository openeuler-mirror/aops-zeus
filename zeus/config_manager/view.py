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
"""
Time:
Author:
Description: Restful APIs for host
"""
import json
from typing import List, Dict

import requests

from zeus.account_manager.cache import UserCache
from zeus.conf.constant import CERES_COLLECT_FILE
from vulcanus.multi_thread_handler import MultiThreadHandler
from zeus.database import SESSION
from zeus.function.verify.config import CollectConfigSchema
from zeus.database.proxy.host import HostProxy
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp import state, make_response
from vulcanus.restful.response import BaseResponse


def get_file_content(host_info: Dict) -> Dict:
    """
        Get target file content from ceres.

    Args:
        host_info (dict): e.g
            {
                host_id : xx,
                config_file_list  : xx,
                address : xx,
                header  : xx
            }
    Returns:
        dict: e.g
            {
                'fail_files': [],
                'infos': [{
                    'content': 'string',
                    'file_attr': {
                    'group': 'root',
                    'mode': '0644',
                    'owner': 'root'},
                    'path': 'file_path'
                    }],
                'success_files': ['file_path'],
                'host_id': 'host_id'
            }

    """
    host_id = host_info.get('host_id')
    address = host_info.get('address')
    config_file_list = host_info.get('config_file_list')
    headers = host_info.get('headers')
    url = f'http://{address}{CERES_COLLECT_FILE}'
    try:
        response = requests.post(url, data=json.dumps(config_file_list),
                                 headers=headers, timeout=5)
        if response.status_code == requests.status_codes.ok:
            res = json.loads(response.text)
            res['host_id'] = host_id
            return res

        LOGGER.warning(f"An unexpected error occurred when visit {url}")
        return {"host_id": host_id, "config_file_list": config_file_list}
    except requests.exceptions.ConnectionError:
        LOGGER.error(f'An error occurred when visit {url},'
                     f'{make_response(label=state.HTTP_CONNECT_ERROR)}')
        return {"host_id": host_id, "config_file_list": config_file_list}


def convert_host_id_to_failed_data_format(
        host_id_list: List[str], host_id_with_file: Dict[str, List]) -> List:
    """
    convert host id which can't visit to target data format

    Args:
        host_id_list:
        host_id_with_file: host id and all requested file path

    Returns:
        List[Dict]:  e.g
            [{
                host_id: host_id,
                success_files: [],
                fail_files: [all file path],
                content: 'empty string'
           }]
    """
    res = []
    for host_id in host_id_list:
        info = {
            'host_id': host_id,
            'success_files': [],
            'fail_files': host_id_with_file.get(host_id),
            'content': {}
        }
        res.append(info)
    return res


def make_multi_thread_tasks(host_address_list: Dict[str, str],
                            host_id_with_file: Dict[str, List],
                            headers: Dict[str, str]) -> List[Dict]:
    """
        Generate parameter groups for multi threading

    Args:
        host_address_list: host id with its ip address
        host_id_with_file: host id and all requested file path
        headers: HTTP headers

    Returns:
        dict e.g
            [{
                "host_id": "host_id",
                "config_file_list":[file_path],
                "address": "ip:port",
                "headers": "http headers"
            }]
    """
    task_list = []
    for host_id in host_address_list:
        task_list.append({
            "host_id": host_id,
            "config_file_list": host_id_with_file.get(host_id),
            "address": host_address_list.get(host_id),
            "headers": headers
        })
    return task_list


def generate_target_data_format(collect_result_list: List[Dict],
                                host_id_with_file: Dict[str, List]) -> List:
    """
    Generate target data format


    Args:
        collect_result_list: file content list
        host_id_with_file:  host id and all requested file path

    Returns:
        target data format: e.g
            [
                {
                    host_id: host_id,
                    infos: [
                        path: file_path,
                        content: string,
                        file_attr: {
                            owner: root,
                            mode: 0644,
                            group: root
                        }
                    ],
                    success_files:[ file_path ],
                    fail_files:[ file_path ]
                }
            ]
    """
    file_content = []
    valid_host_id = set()
    for collect_result in collect_result_list:
        if collect_result.get('infos') is not None:
            file_content.append(collect_result)
            valid_host_id.add(collect_result.get('host_id'))

    invalid_host_id = set(host_id_with_file.keys()) - valid_host_id
    read_failed_data = convert_host_id_to_failed_data_format(
        list(invalid_host_id), host_id_with_file)
    file_content.extend(read_failed_data)

    return file_content


class CollectConfig(BaseResponse):
    """
    Interface for collect config.
    Restful API: POST
    """

    @BaseResponse.handle(schema=CollectConfigSchema, token=False)
    def post(self, **param):
        """
        Get config
        Args:
            request(json): {
                "infos": [{
                    "host_id": "f",
                    "config_list": ["/xx", "/exxxo"]
                }]
            }
        Returns:
            dict: e.g
            {
                code: int,
                msg: string,
                resp:[
                    {
                        host_id: host_id,
                        infos: [
                            path: file_path1,
                            content: string,
                            file_attr: {
                                owner: root,
                                mode: 0644,
                                group: root
                            }
                            ...
                        ],
                        success_files:[
                            file_path1,
                            file_path2,
                            ...
                        ]
                        fail_files:[
                            file_path3,
                            ...
                        ]
                    }
                    ...
                ]
            }
        """
        # Get host id list
        host_id_with_config_file = {}
        for host in param.get('infos'):
            host_id_with_config_file[host.get(
                'host_id')] = host.get('config_list')

        # Generate headers
        user = UserCache.get('admin') or UserCache.get(param.get('username'))
        if user is None:
            file_content = convert_host_id_to_failed_data_format(
                list(host_id_with_config_file.keys()), host_id_with_config_file)
            return self.response(state.TOKEN_ERROR, data={"resp": file_content})

        headers = {'content-type': 'application/json',
                   'access_token': user.token}

        # Query host address from database
        proxy = HostProxy()
        if proxy.connect(SESSION) is None:
            file_content = convert_host_id_to_failed_data_format(
                list(host_id_with_config_file.keys()), host_id_with_config_file)
            return self.response(code=state.DATABASE_CONNECT_ERROR, data={"resp": file_content})

        status, host_address_list = proxy.get_host_address(
            list(host_id_with_config_file.keys()))
        if status != state.SUCCEED:
            file_content = convert_host_id_to_failed_data_format(
                list(host_id_with_config_file.keys()), host_id_with_config_file)
            return self.response(code=status, data={"resp": file_content})

        # Get file content
        host_info = make_multi_thread_tasks(
            host_address_list, host_id_with_config_file, headers)
        multi_thread = MultiThreadHandler(get_file_content, host_info, None)
        multi_thread.create_thread()
        collect_result_list = multi_thread.get_result()

        # Generate target data format
        file_content = generate_target_data_format(
            collect_result_list, host_id_with_config_file)
        return self.response(code=state.SUCCEED, data={"resp": file_content})
