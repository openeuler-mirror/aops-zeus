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
import os
import uuid
from typing import List, Tuple, Dict

import requests
import yaml

from zeus.account_manager.cache import UserCache
from zeus.conf.constant import CERES_COLLECT_FILE
from vulcanus.database.table import Host
from vulcanus.multi_thread_handler import MultiThreadHandler
from zeus.function.verify.config import CollectConfigSchema
from zeus.deploy_manager.ansible_runner.inventory_builder import InventoryBuilder
from zeus.deploy_manager.run_task import TaskRunner
from zeus.account_manager.key import HostKey
from zeus.conf import configuration
from zeus.database.proxy.host import HostProxy
from zeus.database import SESSION
from vulcanus.log.log import LOGGER
from vulcanus.restful.status import (
    StatusCode,
    SUCCEED,
    DATABASE_CONNECT_ERROR,
    TOKEN_ERROR,
    HTTP_CONNECT_ERROR
)
from vulcanus.restful.response import BaseResponse


def traversal_ansible_output(status, **kwargs):
    """
    traversal ansible output list
    Args:
        kwargs(dict):
            infos(list): host info get from database
            success_files(list): success files list
            fail_files(list): fail files list
            info(dict): host info from infos
            res_data(list): success list, skipped list of the ansible output
        status(str): success or skipped list

    """
    info = kwargs.get('info')
    res_data = kwargs.get('res_data')
    fail_files = kwargs.get('fail_files')
    success_files = kwargs.get('success_files')
    infos = kwargs.get('infos')
    host_name = str(info['host_name'])
    path = os.path.join('/home/dest/', host_name)
    if not res_data[status]:
        return
    for host in res_data[status].keys():
        if host != host_name:
            continue
        host_res = res_data[status][host]
        if host_res['task_name'] == "Check that if the file exists":
            continue
        for res_file in host_res['result']['results']:
            file_dict = {}
            if not res_file['item']['stat']['exists']:
                fail_files.append(res_file['item']['invocation']['module_args']['path'])
                continue
            file_dict['path'] = res_file['item']['stat']['path']
            success_files.append(file_dict['path'])
            file_dict['file_attr'] = {}
            file_dict['file_attr']['mode'] = res_file['item']['stat']['mode']
            file_dict['file_attr']['owner'] = res_file['item']['stat']['pw_name']
            file_dict['file_attr']['group'] = res_file['item']['stat']['gr_name']
            with open(path + file_dict['path'], 'r', encoding='utf-8') as file_conf:
                file_dict['content'] = ""
                for line in file_conf.readlines():
                    file_dict['content'] += line
            os.remove(path + file_dict['path'])
            infos.append(file_dict)


def generate_output(host_infos):
    """
    generate output file to the request
    Args:
        host_infos(list): host infos get from database

    Returns:
        dict:
            {
                "succeed_list": succeed_list,
                "fail_list": fail_list,
                "resp": resp_list,
                "is_par": is_par
            }
    """
    succeed_list = []
    fail_list = []
    resp_list = []
    is_par = False
    res, res_data = TaskRunner.run_playbook('read_config',
                                            "read_config",
                                            HostKey.key)
    task_id = str(uuid.uuid1()).replace('-', '')
    if res:
        succeed_list.append(task_id)
        LOGGER.info("task %s execute succeed", task_id)
    else:
        fail_list.append(task_id)
        LOGGER.warning("task %s execute fail", task_id)
        return {}

    for info in host_infos:
        host_id_dict = {'host_id': info['host_id']}
        infos = []
        success_files = []
        fail_files = []

        args_dict = {
            "res_data": res_data,
            "info": info,
            "fail_files": fail_files,
            "success_files": success_files,
            "infos": infos
        }
        traversal_ansible_output(status="success", **args_dict)
        traversal_ansible_output(status="skipped", **args_dict)
        host_id_dict['infos'] = infos
        host_id_dict['success_files'] = success_files
        host_id_dict['fail_files'] = fail_files
        if len(success_files) > 0 and len(fail_files) > 0:
            is_par = True
        resp_list.append(host_id_dict)

    return {"succeed_list": succeed_list,
            "fail_list": fail_list,
            "resp": resp_list,
            "is_par": is_par}


def generate_ansible_input_json(host_infos, inventory, params):
    """
    function to generate ansible input json file
    Args:
        host_infos(list): host infos get from database
        inventory(InventoryBuilder): Inventory class
        params(dict):  params of the requests
    Returns:
        dict: The ansible output
    """
    ansible_input_json = {'read_config_hosts': {}}
    for info in host_infos:
        # move host dir to vars
        inventory.move_host_vars_to_inventory(configuration.zeus.get('HOST_VARS'),
                                              str(info['host_name']))

        # read_config.json generate
        ansible_input_json_host = generate_host_dict(info, params)
        ansible_input_json['read_config_hosts'][info['host_name']] = ansible_input_json_host
    return ansible_input_json


def generate_host_dict(info, params):
    """
    Generate ansible host dict
    Args:
        info(dict): info of a host
        params(dict): params of the requests
    Returns:
        dict: dict of ansible host
    """
    ansible_input_json_host = {'ansible_host': info['public_ip'],
                               'ansible_python_interpreter': '/usr/bin/python3',
                               'config_list': []}
    for item in params['infos']:
        if item['host_id'] == info['host_id']:
            for config in item['config_list']:
                ansible_input_json_host['config_list'] \
                    .append({"src": config, "dest": "/home/dest"})
                break
    return ansible_input_json_host


def generate_yaml_vars():
    """
    generate yaml vars
    """
    # generate_read_config_vars.yaml
    yaml_init = {}
    yml_path = os.path.join('/tmp/', "read_config_vars.yml")
    with open(yml_path, 'w', encoding="utf-8") as file:
        yaml.dump(yaml_init, file)


def read_yaml_data(yaml_file):
    """
    read yaml file.

    Args:
        yaml_file:  yaml file

    Returns:
        dict: yaml content of the yaml file
    """
    with open(yaml_file, 'r', encoding="utf-8") as file:
        file_data = file.read()

    data = yaml.safe_load(file_data)
    return data


def get_host_address(host_id_list: List[str]) -> Tuple[int, dict]:
    """
        get host ip and agent port from database
    Args:
        host_id_list( List[str] ) : [host_id1, host_id2, ...]
    Returns:
        tuple:
            status_code, {host_id : ip_with_port}

    """
    proxy = HostProxy()
    if proxy.connect(SESSION):
        query_list = proxy.session.query(
            Host).filter(Host.host_id.in_(host_id_list)).all()
        proxy.close()
        host_address = {}
        for host_info in query_list:
            host_address[host_info.host_id] = f'{host_info.public_ip}:{host_info.agent_port}'
        return SUCCEED, host_address
    LOGGER.error("connect to database error")
    return DATABASE_CONNECT_ERROR, {}


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
        if response.status_code == SUCCEED:
            res = json.loads(response.text)
            res['host_id'] = host_id
            return res
        LOGGER.warning(f"An unexpected error occurred when visit {url}")
        return {"host_id": host_id, "config_file_list": config_file_list}
    except requests.exceptions.ConnectionError:
        LOGGER.error(f'An error occurred when visit {url},'
                     f'{StatusCode.make_response(HTTP_CONNECT_ERROR)}')
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
                    host_id: string,
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

    def _handle(self, args) -> Tuple[int, dict]:
        """
            Handle function

        Args:
            args (dict): request parameter

        Returns:
            tuple: (status code, result)

        Notes:
            The current username is set to admin by default.
        """
        # Get host id list
        host_id_with_config_file = {}
        for host in args.get('infos'):
            host_id_with_config_file[host.get('host_id')] = host.get('config_list')

        # Generate headers
        user = UserCache.get('admin') or UserCache.get(args.get('username'))
        if user is None:
            file_content = convert_host_id_to_failed_data_format(
                list(host_id_with_config_file.keys()), host_id_with_config_file)
            return TOKEN_ERROR, {"resp": file_content}
        headers = {'content-type': 'application/json', 'access_token': user.token}

        # Query host address from database
        status, host_address_list = get_host_address(list(host_id_with_config_file.keys()))
        if status != SUCCEED:
            file_content = convert_host_id_to_failed_data_format(
                list(host_id_with_config_file.keys()), host_id_with_config_file)
            return status, {"resp": file_content}

        # Get file content
        host_info = make_multi_thread_tasks(host_address_list, host_id_with_config_file, headers)
        multi_thread = MultiThreadHandler(get_file_content, host_info, None)
        multi_thread.create_thread()
        collect_result_list = multi_thread.get_result()

        # Generate target data format
        file_content = generate_target_data_format(collect_result_list, host_id_with_config_file)

        return SUCCEED, {"resp": file_content}

    def post(self):
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
                        host_id: string,
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

        return self.handle_request(CollectConfigSchema, self, need_token=False)


def inventory_operate(ansible_input_json, inventory):
    """
    inventory files' operation
    Args:
        ansible_input_json(json): json file of hosts
        inventory(class): InvenoryBuild Class include inventories' methods

    Returns:

    """
    inventory.import_host_list(ansible_input_json, "read_config", '/tmp')
    inventory.move_host_to_inventory('/tmp', 'read_config')
    generate_yaml_vars()
    inventory.move_playbook_vars_to_inventory('/tmp', 'read_config_vars.yml')
