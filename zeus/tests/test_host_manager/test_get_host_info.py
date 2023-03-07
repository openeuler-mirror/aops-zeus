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

import requests
from flask import Flask

from vulcanus.conf.constant import QUERY_HOST_DETAIL
from vulcanus.database.proxy import MysqlProxy
from vulcanus.multi_thread_handler import MultiThreadHandler
from zeus import BLUE_POINT
from zeus.account_manager.cache import UserCache, UserInfo
from zeus.database.proxy.host import HostProxy
from vulcanus.restful.resp.state import SUCCEED, TOKEN_ERROR, DATABASE_CONNECT_ERROR, NO_DATA, \
    PARAM_ERROR
from zeus.host_manager.view import GetHostInfo

app = Flask("test")
for blue, api in BLUE_POINT:
    api.init_app(blue)
    app.register_blueprint(blue)

app.testing = True
client = app.test_client()
header = {
    "Content-Type": "application/json; charset=UTF-8"
}
header_with_token = {
    "Content-Type": "application/json; charset=UTF-8",
    "access_token": "mock_token"
}


class TestGetHostInfo(unittest.TestCase):
    MOCK_ARGS = {
        "host_list": [1, 2],
        "basic": False
    }

    @mock.patch.object(MultiThreadHandler, "get_result")
    @mock.patch.object(MultiThreadHandler, "create_thread")
    @mock.patch.object(HostProxy, 'get_host_address')
    @mock.patch.object(MysqlProxy, 'connect')
    @mock.patch.object(UserCache, 'get')
    def test_get_host_info_from_ceres_should_return_host_info_when_all_is_right(
            self, mock_user, mock_connect, mock_host_address, mock_create_thread, mock_get_result):
        mock_connect.return_value = ''
        mock_create_thread.return_value = None
        mock_user.return_value = UserInfo('admin', 'mock', 'mock')
        mock_host_address.return_value = SUCCEED, {
            1: "mock_address1",
            2: "mock_address2"
        }

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
        response = client.post(QUERY_HOST_DETAIL,
                               data=json.dumps(self.MOCK_ARGS),
                               headers=header_with_token)
        fail_host_list = []
        for res in response.json.get("host_infos"):
            if res.get('host_info') is {}:
                fail_host_list.append(res.get('host_id'))
        self.assertEqual([], fail_host_list)

    def test_get_host_info_from_ceres_should_return_token_error_data_when_request_with_no_token(
            self):
        response = client.post(QUERY_HOST_DETAIL,
                               data=json.dumps(self.MOCK_ARGS),
                               headers=header)
        self.assertEqual(TOKEN_ERROR, response.json.get('label'))

    @mock.patch.object(UserCache, 'get')
    def test_get_host_info_from_ceres_should_return_all_host_info_is_empty_when_token_is_error(
            self, mock_user):
        mock_user.return_value = None
        response = client.post(QUERY_HOST_DETAIL,
                               data=json.dumps(self.MOCK_ARGS),
                               headers=header)
        self.assertEqual(TOKEN_ERROR, response.json.get('label'))

    @mock.patch.object(MysqlProxy, 'connect')
    @mock.patch.object(UserCache, 'get')
    def test_get_host_info_from_ceres_should_return_connect_error_when_cannot_connect_database(
            self, mock_user, mock_connect):
        mock_user.return_value = UserInfo('admin', 'mock', 'mock')
        mock_connect.return_value = None
        response = client.post(QUERY_HOST_DETAIL,
                               data=json.dumps(self.MOCK_ARGS),
                               headers=header_with_token)
        self.assertEqual(DATABASE_CONNECT_ERROR, response.json.get('label'))

    @mock.patch.object(HostProxy, 'get_host_address')
    @mock.patch.object(MysqlProxy, 'connect')
    @mock.patch.object(UserCache, 'get')
    def test_get_host_info_from_ceres_should_return_no_data_when_input_host_id_is_not_in_database(
            self, mock_user, mock_connect, mock_host_address):
        mock_user.return_value = UserInfo('admin', 'mock', 'mock')
        mock_connect.return_value = ''
        mock_host_address.return_value = SUCCEED, {}
        response = client.post(QUERY_HOST_DETAIL,
                               data=json.dumps(self.MOCK_ARGS),
                               headers=header_with_token)
        self.assertEqual(NO_DATA, response.json.get('label'))

    def test_get_host_info_from_ceres_should_return_param_error_when_input_incorrect_param(
            self, ):
        mock_incorrect_data = {
            "host_list": {},
            "basic": False
        }
        response = client.post(QUERY_HOST_DETAIL,
                               data=json.dumps(mock_incorrect_data),
                               headers=header_with_token)
        self.assertEqual(PARAM_ERROR, response.json.get('label'))

    @mock.patch.object(requests, "post")
    def test_get_host_info_should_return_host_info_is_empty_when_http_connect_error(
            self, mock_request):
        mock_request.side_effect = requests.exceptions.ConnectionError()
        mock_args = {
            "host_id": 1,
            "info_type": ["cpu", "os", "memory", "disk"],
            "address": "mock_address",
            "headers": {
                "content-type": "application/json",
                "access_token": "host token"
            }
        }
        result = GetHostInfo.get_host_info(mock_args)
        self.assertEqual({"host_id": 1, "host_info": {}}, result)
