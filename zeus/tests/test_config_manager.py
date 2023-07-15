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
Description:
"""
import json
from unittest import mock

from vulcanus.conf.constant import COLLECT_CONFIG
from vulcanus.database.proxy import MysqlProxy
from vulcanus.multi_thread_handler import MultiThreadHandler
from vulcanus.restful.resp.state import (
    SUCCEED, PARAM_ERROR,
    DATABASE_CONNECT_ERROR,
    DATABASE_QUERY_ERROR,
    SSH_CONNECTION_ERROR
)
from zeus.config_manager.view import CollectConfig
from zeus.database.proxy.host import HostProxy
from zeus.tests import BaseTestCase

header = {"Content-Type": "application/json; charset=UTF-8"}


class TestConfigManage(BaseTestCase):
    client = BaseTestCase.create_app()
    MOCK_GET_FILE_CONTENT_ARGS = {
        "infos": [
            {"host_id": 1, "config_list": ["mock_path1", "mock_path2"]},
            {"host_id": 2, "config_list": ["mock_path3", "mock_path4"]},
        ]
    }

    MOCK_HOST_INFO = [
        {
            "host_id": 1,
            "host_ip": "host_ip2",
            "ssh_port": 22,
            "pkey": "mock_rsa_key",
            "ssh_user": "root"
        },
        {
            "host_id": 2,
            "host_ip": "host_ip2",
            "ssh_port": 22,
            "pkey": "mock_rsa_key",
            "ssh_user": "root"
        }
    ]

    @mock.patch.object(MultiThreadHandler, "get_result")
    @mock.patch.object(MultiThreadHandler, "create_thread")
    @mock.patch.object(HostProxy, 'get_host_info')
    @mock.patch.object(MysqlProxy, 'connect')
    def test_collect_config_should_return_get_all_file_content_when_all_is_right(
            self, mock_connect, mock_host_info, mock_create_thread, mock_get_result):
        mock_create_thread.return_value = None
        mock_connect.return_value = True
        mock_host_info.return_value = SUCCEED, self.MOCK_HOST_INFO
        mock_file_content = [{
            'fail_files': [],
            'infos': [],
            'success_files': ['mock_path'],
            'host_id': 1,
        },
            {
                'fail_files': [],
                'infos': [],
                'success_files': ['mock_path'],
                'host_id': 2,
            }
        ]
        mock_get_result.return_value = mock_file_content
        resp = self.client.post(
            '/manage/config/collect', data=json.dumps(self.MOCK_GET_FILE_CONTENT_ARGS), headers=header
        )
        all_fail_file_list = []
        for file_content in resp.json["data"]:
            all_fail_file_list.extend(file_content.get("fail_files"))
        self.assertEqual([], all_fail_file_list, resp.json)

    def test_collect_config_should_return_param_error_when_input_is_incorrect(self):
        mock_args = {
            "infos": [{"host_id": "id1", "config_list": ["test_config_path"]}]}
        resp = self.client.post('/manage/config/collect', data=json.dumps(mock_args),
                                headers=header)
        self.assertEqual(PARAM_ERROR, resp.json.get('label'), resp.json)

    def test_collect_config_should_return_400_when_no_input(self):
        resp = self.client.post('/manage/config/collect', headers=header)
        self.assertEqual(400, resp.status_code, resp.json)

    @mock.patch.object(MultiThreadHandler, "get_result")
    @mock.patch.object(MultiThreadHandler, "create_thread")
    @mock.patch.object(HostProxy, 'get_host_info')
    @mock.patch.object(MysqlProxy, 'connect')
    def test_collect_config_should_return_fail_list_when_input_host_id_not_in_database(
            self, mock_connect, mock_host_info, mock_create_thread, mock_get_result):
        mock_create_thread.return_value = None
        mock_connect.return_value = True
        mock_host_info.return_value = SUCCEED, [self.MOCK_HOST_INFO[0]]
        mock_file_content = [{
            'fail_files': [],
            'infos': [{
                'content': 'mock_str',
                'file_attr': {
                    'group': 'mock',
                    'mode': 'mock',
                    'owner': 'mock'},
                'path': 'mock_path1'
            }],
            'success_files': ['mock_path'],
            'host_id': 1
        }]
        mock_get_result.return_value = mock_file_content
        resp = self.client.post(
            '/manage/config/collect', data=json.dumps(self.MOCK_GET_FILE_CONTENT_ARGS), headers=header
        )
        all_fail_file_list = []
        for file_content in resp.json["data"]:
            all_fail_file_list.extend(file_content.get("fail_files"))
        expecte_fail_file = ['mock_path3', 'mock_path4']
        self.assertEqual(set(expecte_fail_file), set(all_fail_file_list))

    @mock.patch.object(MultiThreadHandler, "get_result")
    @mock.patch.object(MultiThreadHandler, "create_thread")
    @mock.patch.object(HostProxy, 'get_host_info')
    @mock.patch.object(MysqlProxy, 'connect')
    def test_collect_config_should_return_fail_list_when_get_file_failed_from_ceres(
            self, mock_connect, mock_host_info, mock_create_thread, mock_get_result):
        mock_create_thread.return_value = None
        mock_connect.return_value = True
        mock_host_info.return_value = SUCCEED, self.MOCK_HOST_INFO
        mock_file_content = [{"message": "error"}, {"message": "error"}]
        mock_get_result.return_value = mock_file_content

        expecte_fail_file = ['mock_path1', 'mock_path2', 'mock_path3', 'mock_path4']
        all_fail_file_list = []
        resp = self.client.post(COLLECT_CONFIG, data=json.dumps(self.MOCK_GET_FILE_CONTENT_ARGS), headers=header)
        for file_content in resp.json["data"]:
            all_fail_file_list.extend(file_content.get("fail_files"))
        self.assertEqual(set(expecte_fail_file), set(all_fail_file_list))

    @mock.patch("zeus.config_manager.view.execute_command_and_parse_its_result")
    def test_get_file_content_should_return_host_id_and_config_file_list_when_connect_host_failed(self, mock_execute):
        mock_execute.return_value = SSH_CONNECTION_ERROR, "SSH.Connection.Error"
        mock_host_info = {
            "host_id": 1,
            "host_ip": "host_ip2",
            "ssh_port": 22,
            "pkey": "mock_rsa_key",
            "ssh_user": "root"
        }
        mock_file_list = ["xx"]
        res = CollectConfig.get_file_content(mock_host_info, mock_file_list)
        self.assertEqual(mock_file_list, res.get("config_file_list"), res)

    @mock.patch("zeus.config_manager.view.execute_command_and_parse_its_result")
    def test_get_file_content_should_return_no_fail_files_when_read_file_content_successfully(self, mock_execute):
        mock_file_content = {
            'fail_files': [],
            'infos': [{
                'content': 'mock_str',
                'file_attr': {
                    'group': 'mock',
                    'mode': 'mock',
                    'owner': 'mock'},
                'path': 'mock_path1'
            }],
            'success_files': ['mock_path'],
            'host_id': 1
        }
        mock_execute.return_value = SUCCEED, json.dumps(mock_file_content)
        mock_host_info = {
            "host_id": 1,
            "host_ip": "host_ip2",
            "ssh_port": 22,
            "pkey": "mock_rsa_key",
            "ssh_user": "root"
        }
        mock_file_list = ["mock_path1"]

        collect_result = CollectConfig.get_file_content(mock_host_info, mock_file_list)
        self.assertEqual([], collect_result.get("fail_files"), collect_result)

    @mock.patch.object(MysqlProxy, 'connect')
    def test_collect_config_should_return_database_connect_error_when_failed_to_connect_database(self, mock_connect):
        mock_connect.return_value = None
        resp = self.client.post(COLLECT_CONFIG, data=json.dumps(self.MOCK_GET_FILE_CONTENT_ARGS), headers=header)
        self.assertEqual(DATABASE_CONNECT_ERROR, resp.json.get('label'))

    @mock.patch.object(HostProxy, 'get_host_info')
    @mock.patch.object(MysqlProxy, 'connect')
    def test_collect_config_should_return_database_query_error_when_query_host_info_failed(
            self, mock_connect, mock_query_host):
        mock_connect.return_value = True
        mock_query_host.return_value = DATABASE_QUERY_ERROR, []
        resp = self.client.post(COLLECT_CONFIG, data=json.dumps(self.MOCK_GET_FILE_CONTENT_ARGS), headers=header)
        self.assertEqual(DATABASE_QUERY_ERROR, resp.json.get("label"))
