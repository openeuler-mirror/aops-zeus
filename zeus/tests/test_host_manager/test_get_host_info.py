#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2022-2022. All rights reserved.
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
import unittest
from unittest import mock

import sqlalchemy

from vulcanus.conf.constant import QUERY_HOST_DETAIL
from vulcanus.database.proxy import MysqlProxy
from vulcanus.multi_thread_handler import MultiThreadHandler
from vulcanus.restful.resp.state import (
    SUCCEED,
    TOKEN_ERROR,
    DATABASE_CONNECT_ERROR,
    PARAM_ERROR, SSH_CONNECTION_ERROR
)
from vulcanus.restful.response import BaseResponse
from zeus.database.proxy.host import HostProxy
from zeus.host_manager.view import GetHostInfo
from zeus.tests import BaseTestCase

client = BaseTestCase.create_app()
header = {
    "Content-Type": "application/json; charset=UTF-8"
}
header_with_token = {
    "Content-Type": "application/json; charset=UTF-8",
    "access_token": "mock_token"
}


class TestGetHostInfo(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_args = {
            "host_list": [1, 2],
            "basic": False
        }
        self.mock_host_basic_info = [
            {
                "host_id": 1,
                "host_ip": "host_ip_1",
                "pkey": "rsa-pkey-1",
                "ssh_user": "root",
                "ssh_port": 22
            },
            {
                "host_id": 2,
                "host_ip": "host_ip_2",
                "pkey": "rsa-pkey-2",
                "ssh_user": "root",
                "ssh_port": 22
            }
        ]

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(MultiThreadHandler, "get_result")
    @mock.patch.object(MultiThreadHandler, "create_thread")
    @mock.patch.object(HostProxy, 'get_host_info')
    @mock.patch.object(MysqlProxy, '_create_session')
    @mock.patch.object(BaseResponse, 'verify_request')
    def test_get_host_info_from_ceres_should_return_host_info_when_all_is_right(
            self, mock_verify_request, mock_connect, mock_host_basic_info, mock_create_thread, mock_get_result, mock_close):
        mock_verify_request.return_value = self.mock_args, SUCCEED
        mock_create_thread.return_value = None
        mock_connect.return_value = None
        mock_host_basic_info.return_value = SUCCEED, self.mock_host_basic_info
        mock_get_result.return_value = [
            {
                "host_id": 1,
                "host_info": {
                    "cpu": {},
                    "os": {},
                    "memory": {},
                    "disk": [{}]
                }
            },
            {
                "host_id": 2,
                "host_info": {
                    "cpu": {},
                    "os": {},
                    "memory": {},
                    "disk": [{}]
                }
            }
        ]
        mock_close.return_value = None
        response = client.post(QUERY_HOST_DETAIL, data=json.dumps(self.mock_args), headers=header_with_token)
        fail_host_list = []
        for res in response.json.get("data").get("host_infos"):
            if res.get('host_info') is {}:
                fail_host_list.append(res.get('host_id'))
        self.assertEqual([], fail_host_list)

    def test_get_host_info_from_ceres_should_return_token_error_data_when_request_with_no_token(self):
        response = client.post(QUERY_HOST_DETAIL, data=json.dumps(self.mock_args), headers=header)
        self.assertEqual(TOKEN_ERROR, response.json.get('label'))

    @mock.patch.object(BaseResponse, 'verify_token')
    def test_get_host_info_from_ceres_should_return_all_host_info_is_empty_when_token_is_error(self, mock_token):
        mock_token.return_value = TOKEN_ERROR
        response = client.post(QUERY_HOST_DETAIL, data=json.dumps(self.mock_args), headers=header)
        self.assertEqual(TOKEN_ERROR, response.json.get('label'))

    @mock.patch.object(MysqlProxy, '_create_session')
    @mock.patch.object(BaseResponse, 'verify_request')
    def test_get_host_info_from_ceres_should_return_connect_error_when_cannot_connect_database(
            self, mock_verify_request, mock_connect):
        mock_verify_request.return_value = self.mock_args, SUCCEED
        mock_connect.side_effect = mock_connect.side_effect = sqlalchemy.exc.SQLAlchemyError("Connection error")
        response = client.post(QUERY_HOST_DETAIL, data=json.dumps(self.mock_args), headers=header_with_token)
        self.assertEqual(DATABASE_CONNECT_ERROR, response.json.get('label'))

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(HostProxy, 'get_host_info')
    @mock.patch.object(MysqlProxy, '_create_session')
    @mock.patch.object(BaseResponse, 'verify_token')
    def test_get_host_info_from_ceres_should_return_all_host_info_is_empty_when_input_host_id_is_not_in_database(
            self, mock_token, mock_connect, mock_host_basic_info, mock_close):
        mock_token.return_value = SUCCEED
        mock_connect.return_value = None
        mock_host_basic_info.return_value = SUCCEED, []
        mock_close.return_value = None
        response = client.post(QUERY_HOST_DETAIL, data=json.dumps(self.mock_args), headers=header_with_token)
        host_info_list = []
        for host_info in response.json.get("data").get("host_infos"):
            if host_info.get("host_info"):
                host_info_list.append(host_info)
        self.assertEqual([], host_info_list, response.json)

    def test_get_host_info_from_ceres_should_return_param_error_when_input_incorrect_param(self):
        mock_incorrect_data = {"host_list": {}, "basic": False}
        response = client.post(QUERY_HOST_DETAIL, data=json.dumps(mock_incorrect_data), headers=header_with_token)
        self.assertEqual(PARAM_ERROR, response.json.get('label'))

    @mock.patch("zeus.host_manager.view.execute_command_and_parse_its_result")
    def test_get_host_info_should_return_host_info_is_empty_when_connect_host_failed(self, mock_execute_command):
        mock_execute_command.return_value = SSH_CONNECTION_ERROR, "SSH.Connection.Error"
        result = GetHostInfo.get_host_info(self.mock_host_basic_info[0], [])
        self.assertEqual({"host_id": 1, "host_info": {}}, result)
