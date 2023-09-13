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

from vulcanus.multi_thread_handler import MultiThreadHandler
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse
from zeus.conf import configuration
from zeus.conf.constant import CERES_COLLECT_FILE, CERES_SYNC_CONF
from zeus.database.proxy.host import HostProxy
from zeus.function.model import ClientConnectArgs
from zeus.function.verify.config import CollectConfigSchema, SyncConfigSchema
from zeus.host_manager.ssh import execute_command_and_parse_its_result


class CollectConfig(BaseResponse):
    """
    Interface for collect config.
    Restful API: POST
    """

    @staticmethod
    def get_file_content(host_info: Dict, file_list: list) -> Dict:
        """
            Get target file content from ceres.

        Args:
            host_info (dict): e.g
                {
                    host_id : xx,
                    address : xx,
                    header  : xx
                }
            file_list (list): e.g
                ["/etc/test.txt", "/tmp/test.csv"]
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
        command = CERES_COLLECT_FILE % json.dumps(file_list)
        status, content = execute_command_and_parse_its_result(
            ClientConnectArgs(
                host_info.get("host_ip"), host_info.get("ssh_port"), host_info.get("ssh_user"), host_info.get("pkey")
            ),
            command,
        )
        if status == state.SUCCEED:
            data = json.loads(content)
            data.update({"host_id": host_info["host_id"]})
            return data
        return {"host_id": host_info["host_id"], "config_file_list": file_list}

    @staticmethod
    def convert_host_id_to_failed_data_format(host_id_list: list, host_id_with_file: dict) -> list:
        """
        convert host id which can't visit to target data format

        Args:
            host_id_list (list)
            host_id_with_file: host id and all requested file path. e.g
                {
                    host_id_1: [config_path_1, config_path_2, ...],
                    host_id_2: [config_path_1, config_path_2, ...]
                }

        Returns:
            List[Dict]:  e.g
                [{
                    host_id: host_id,
                    success_files: [],
                    fail_files: [all file path],
                    infos: []
               }]
        """
        return [
            {'host_id': host_id, 'success_files': [], 'fail_files': host_id_with_file.get(host_id), 'infos': []}
            for host_id in host_id_list
        ]

    def generate_target_data_format(self, collect_result_list: List[Dict], host_id_with_file: Dict[str, List]) -> List:
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
        read_failed_data = self.convert_host_id_to_failed_data_format(list(invalid_host_id), host_id_with_file)
        file_content.extend(read_failed_data)

        return file_content

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
            host_id_with_config_file[host.get('host_id')] = host.get('config_list')

        # Query host address from database
        proxy = HostProxy()
        if not proxy.connect():
            file_content = self.convert_host_id_to_failed_data_format(
                list(host_id_with_config_file.keys()), host_id_with_config_file
            )
            return self.response(code=state.DATABASE_CONNECT_ERROR, data={"resp": file_content})

        status, host_list = proxy.get_host_info(
            {"username": "admin", "host_list": list(host_id_with_config_file.keys())}, True
        )
        if status != state.SUCCEED:
            file_content = self.convert_host_id_to_failed_data_format(
                list(host_id_with_config_file.keys()), host_id_with_config_file
            )
            return self.response(code=status, data={"resp": file_content})
        # Get file content
        tasks = [(host, host_id_with_config_file[host["host_id"]]) for host in host_list]
        multi_thread = MultiThreadHandler(lambda data: self.get_file_content(*data), tasks, None)
        multi_thread.create_thread()

        return self.response(
            state.SUCCEED, None, self.generate_target_data_format(multi_thread.get_result(), host_id_with_config_file)
        )


class SyncConfig(BaseResponse):

    @staticmethod
    def sync_config_content(host_info: Dict, sync_config_info: Dict):
        command = CERES_SYNC_CONF % json.dumps(sync_config_info)
        status, content = execute_command_and_parse_its_result(
            ClientConnectArgs(host_info.get("host_ip"), host_info.get("ssh_port"),
                              host_info.get("ssh_user"), host_info.get("pkey")), command)
        return status

    @BaseResponse.handle(schema=SyncConfigSchema, token=False)
    def put(self, **params):

        sync_config_info = dict()
        sync_config_info['file_path'] = params.get('file_path')
        sync_config_info['content'] = params.get('content')

        sync_result = {
            "file_path": sync_config_info['file_path'],
            "sync_result": False
        }

        # Query host address from database
        proxy = HostProxy(configuration)
        if not proxy.connect():
            return self.response(code=state.DATABASE_CONNECT_ERROR, data={"resp": sync_result})

        status, host_list = proxy.get_host_info(
            {"username": "admin", "host_list": [params.get('host_id')]}, True)
        if status != state.SUCCEED or len(host_list) == 1:
            return self.response(code=status, data={"resp": sync_result})

        host_info = host_list[0]
        status = self.sync_config_content(host_info, sync_config_info)
        if status == state.SUCCEED:
            sync_result['sync_result'] = True
            return self.response(code=state.SUCCEED, data={"resp": sync_result})
        return self.response(code=state.UNKNOWN_ERROR, data={"resp": sync_result})
