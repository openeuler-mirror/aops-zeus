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
import unittest
from unittest import mock
import json

import requests
from flask import Flask
import responses
from sqlalchemy.orm import scoping

import zeus
from vulcanus.multi_thread_handler import MultiThreadHandler
from zeus.account_manager.cache import UserCache, UserInfo
from vulcanus.restful.status import SUCCEED, PARAM_ERROR, SERVER_ERROR, DATABASE_CONNECT_ERROR
from zeus.config_manager.view import get_file_content, get_host_address
from zeus.database.proxy.host import HostProxy

header = {
    "Content-Type": "application/json; charset=UTF-8"
}


class TestConfigManage(unittest.TestCase):
    MOCK_GET_FILE_CONTENT_ARGS = {
        "infos": [
            {
                "host_id": "mock_host_id1",
                "config_list": [
                    "mock_path1",
                    "mock_path2"
                ]},
            {
                "host_id": "mock_host_id2",
                "config_list": [
                    "mock_path3",
                    "mock_path4"
                ]}
        ]}

    def setUp(self) -> None:
        app = Flask("manager")

        for blue, api in zeus.BLUE_POINT:
            api.init_app(app)
            app.register_blueprint(blue)

        app.testing = True
        self.client = app.test_client()

    @mock.patch.object(MultiThreadHandler, "get_result")
    @mock.patch.object(MultiThreadHandler, "create_thread")
    @mock.patch('zeus.config_manager.view.get_host_address')
    @mock.patch.object(UserCache, 'get')
    def test_collect_config_should_return_get_all_file_content_when_all_is_right(
            self, mock_user, mock_host_address, mock_create_thread, mock_get_result):
        mock_create_thread.return_value = None
        mock_user.return_value = UserInfo('admin', 'mock', 'mock')
        mock_host_address.return_value = SUCCEED, {
            'mock_host_id1': "mock_address1",
            'mock_host_id2': "mock_address1"
        }
        mock_file_content = [{
            'fail_files': [],
            'infos': [],
            'success_files': ['mock_path'],
            'host_id': 'mock_host_id1',
        },
            {
                'fail_files': [],
                'infos': [],
                'success_files': ['mock_path'],
                'host_id': 'mock_host_id2',
            }
        ]
        mock_get_result.return_value = mock_file_content
        resp = self.client.post('/manage/config/collect',
                                data=json.dumps(self.MOCK_GET_FILE_CONTENT_ARGS),
                                headers=header)
        all_fail_file_list = []
        for file_content in resp.json.get('resp'):
            all_fail_file_list.extend(file_content.get("fail_files"))
        self.assertEqual([], all_fail_file_list, resp.json)

    def test_collect_config_should_return_param_error_when_input_is_incorrect(self):
        mock_args = {"infos": [{"host_id": 2333, "config_list": ["test_config_path"]}]}
        resp = self.client.post('/manage/config/collect', data=json.dumps(mock_args),
                                headers=header)
        self.assertEqual(PARAM_ERROR, resp.json.get('code'), resp.json)

    def test_collect_config_should_return_400_when_no_input(self):
        resp = self.client.post('/manage/config/collect', headers=header)
        self.assertEqual(400, resp.status_code, resp.json)

    @mock.patch.object(MultiThreadHandler, "get_result")
    @mock.patch.object(MultiThreadHandler, "create_thread")
    @mock.patch('zeus.config_manager.view.get_host_address')
    @mock.patch.object(UserCache, 'get')
    def test_collect_config_should_return_fail_list_when_input_host_id_not_in_database(
            self, mock_user, mock_host_address, mock_create_thread, mock_get_result):
        mock_create_thread.return_value = None
        mock_user.return_value = UserInfo('admin', 'mock', 'mock')
        mock_host_address.return_value = SUCCEED, {
            'mock_host_id1': "mock_address1",
        }
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
            'host_id': 'mock_host_id1'
        }]
        mock_get_result.return_value = mock_file_content
        resp = self.client.post('/manage/config/collect',
                                data=json.dumps(self.MOCK_GET_FILE_CONTENT_ARGS),
                                headers=header)
        all_fail_file_list = []
        for file_content in resp.json.get('resp'):
            all_fail_file_list.extend(file_content.get("fail_files"))
        expecte_fail_file = ['mock_path3', 'mock_path4']
        self.assertEqual(set(expecte_fail_file), set(all_fail_file_list))

    @mock.patch.object(MultiThreadHandler, "get_result")
    @mock.patch.object(MultiThreadHandler, "create_thread")
    @mock.patch('zeus.config_manager.view.get_host_address')
    @mock.patch.object(UserCache, 'get')
    def test_collect_config_should_return_fail_list_when_get_file_failed_from_ceres(
            self, mock_user, mock_host_address, mock_create_thread, mock_get_result):
        mock_create_thread.return_value = None
        mock_user.return_value = UserInfo('admin', 'mock', 'mock')
        mock_host_address.return_value = SUCCEED, {
            'mock_host_id1': "mock_address1",
            'mock_host_id2': "mock_address2",
        }

        mock_file_content = [{"message": "error"}, {"message": "error"}]

        mock_get_result.return_value = mock_file_content

        expecte_fail_file = ['mock_path1', 'mock_path2', 'mock_path3', 'mock_path4']
        all_fail_file_list = []
        resp = self.client.post('/manage/config/collect',
                                data=json.dumps(self.MOCK_GET_FILE_CONTENT_ARGS),
                                headers=header)
        for file_content in resp.json.get('resp'):
            all_fail_file_list.extend(file_content.get("fail_files"))
        self.assertEqual(set(expecte_fail_file), set(all_fail_file_list))

    @responses.activate
    def test_get_file_content_should_return_file_content_when_all_is_right(self):
        mock_agrs = {
            "host_id": "xx",
            "config_file_list": "xx",
            "address": "xx",
            "header": "xx"
        }

        mock_file_info = {
            'fail_files': [],
            'infos': [],
            'success_files': ['xx'],
        }
        responses.add(responses.POST,
                      'http://xx/v1/ceres/file/collect',
                      json=mock_file_info,
                      status=SUCCEED,
                      content_type='application/json'
                      )
        res = get_file_content(mock_agrs)
        self.assertEqual(None, res.get("config_file_list"), res)

    @responses.activate
    def test_get_file_content_should_return_host_id_and_config_file_list_when_response_status_code_is_not_success(
            self):
        mock_agrs = {
            "host_id": "xx",
            "config_file_list": "xx",
            "address": "xx",
            "header": "xx"
        }

        mock_file_info = {}
        responses.add(responses.POST,
                      'http://xx/v1/ceres/file/collect',
                      json=mock_file_info,
                      status=SERVER_ERROR,
                      content_type='application/json'
                      )
        res = get_file_content(mock_agrs)
        self.assertEqual("xx", res.get("config_file_list"), res)

    @mock.patch.object(requests, "post")
    def test_get_file_content_should_return_host_id_and_config_file_list_when_http_connect_failed(
            self, mock_request):
        mock_request.side_effect = requests.exceptions.ConnectionError()
        mock_agrs = {
            "host_id": "xx",
            "config_file_list": "xx",
            "address": "xx",
            "header": "xx"
        }
        res = get_file_content(mock_agrs)
        self.assertEqual("xx", res.get("config_file_list"), res)

    @mock.patch.object(HostProxy, 'connect')
    @mock.patch.object(scoping, 'scoped_session')
    def test_get_host_address_should_return_database_error_when_connect_database_failed(
            self, mock_session, mock_connect):
        mock_session.return_value = ''
        mock_connect.return_value = False
        res = get_host_address([])
        self.assertEqual((DATABASE_CONNECT_ERROR, {}), res)
