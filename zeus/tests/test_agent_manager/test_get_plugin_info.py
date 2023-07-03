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
Time: 2023/6/8
Author: 
Description: 
"""
import json
from unittest import mock

import sqlalchemy

from vulcanus.conf.constant import AGENT_PLUGIN_INFO
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse
from zeus.database.proxy.host import HostProxy
from zeus.tests import BaseTestCase


class TestGetPluginInfo(BaseTestCase):
    header = {
        "Content-Type": "application/json; charset=UTF-8"
    }
    header_with_token = {
        "Content-Type": "application/json; charset=UTF-8",
        "access_token": "123456"
    }
    client = BaseTestCase.create_app()

    def setUp(self) -> None:
        self.mock_host_id = 1
        self.mock_host_info = {
            "host_id": 1,
            "ssh_port": 23,
            "ssh_user": "user",
            "password": "password",
            "host_name": "test1",
            "host_group_name": "group1",
            "management": True,
            "username": "mock_user"
        }

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch("zeus.agent_manager.view.execute_command_and_parse_its_result")
    @mock.patch.object(HostProxy, "get_host_info")
    @mock.patch.object(HostProxy, "_create_session")
    @mock.patch.object(BaseResponse, "verify_request")
    def test_get_plugin_info_should_return_plugin_info_when_all_is_right(
            self, mock_verify, mock_connect, mock_host_info, mock_execute, mock_close_db):
        mock_verify.return_value = {"host_id": self.mock_host_id, "username": "mock_user"}, state.SUCCEED
        mock_connect.return_value = None
        mock_host_info.return_value = state.SUCCEED, [self.mock_host_info]
        mock_plugin_info = [
            {
                "plugin_name": "gala-gopher",
                "collect_items": [{"support_auto": False, "probe_name": "example", "probe_status": "on"}],
                "status": "active",
                "resource": [
                    {"name": "cpu", "current_value": "0.2%", "limit_value": None},
                    {"name": "memory", "current_value": "29344 kB", "limit_value": None}],
                "is_installed": True
            }
        ]
        mock_execute.return_value = state.SUCCEED, json.dumps(mock_plugin_info)
        mock_close_db.return_value = None
        response = self.client.get(f"{AGENT_PLUGIN_INFO}?host_id={self.mock_host_id}", headers=self.header_with_token)
        self.assertEqual(state.SUCCEED, response.json.get("label"), response.json)

    @mock.patch.object(BaseResponse, "verify_token")
    def test_get_plugin_info_should_return_token_error_when_request_with_invalid_token_or_with_no_token(self,
                                                                                                        mock_token):
        mock_token.return_value = state.TOKEN_ERROR
        response = self.client.get(f"{AGENT_PLUGIN_INFO}?host_id={self.mock_host_id}", headers=self.header_with_token)
        self.assertEqual(state.TOKEN_ERROR, response.json.get("label"), response.json)

    @mock.patch.object(BaseResponse, "verify_request")
    def test_get_plugin_info_should_return_param_error_when_request_without_args(self, mock_verify):
        mock_verify.return_value = {}, state.PARAM_ERROR
        response = self.client.get(AGENT_PLUGIN_INFO, headers=self.header_with_token)
        self.assertEqual(state.PARAM_ERROR, response.json.get("label"), response.json)

    @mock.patch.object(BaseResponse, "verify_token")
    def test_get_plugin_info_should_return_param_error_when_request_invalid_args(self, mock_verify):
        invalid_args = [
            "a", "", "#", "1.1", " "
        ]
        mock_verify.return_value = {}, state.PARAM_ERROR
        response = []
        for invalid_arg in invalid_args:
            resp = self.client.get(f"{AGENT_PLUGIN_INFO}?host_id={invalid_arg}", headers=self.header_with_token)
            response.append(resp.json.get('label'))
        self.assertEqual([state.PARAM_ERROR] * len(invalid_args), response)

    @mock.patch.object(HostProxy, "_create_session")
    @mock.patch.object(BaseResponse, "verify_request")
    def test_get_plugin_info_should_return_database_connect_error_when_cannot_connect_database(
            self, mock_verify, mock_connect):
        mock_verify.return_value = {}, state.SUCCEED
        mock_connect.side_effect = sqlalchemy.exc.SQLAlchemyError("Connection error")
        response = self.client.get(AGENT_PLUGIN_INFO, headers=self.header_with_token)
        self.assertEqual(state.DATABASE_CONNECT_ERROR, response.json.get("label"), response.json)

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(HostProxy, "get_host_info")
    @mock.patch.object(HostProxy, "_create_session")
    @mock.patch.object(BaseResponse, "verify_request")
    def test_get_plugin_info_should_return_no_data_when_input_host_id_is_not_in_database(
            self, mock_verify, mock_connect, mock_host_info, mock_close_db):
        mock_verify.return_value = {"host_id": self.mock_host_id, "username": "mock_user"}, state.SUCCEED
        mock_connect.return_value = None
        mock_host_info.return_value = state.SUCCEED, []
        mock_close_db.return_value = None
        response = self.client.get(AGENT_PLUGIN_INFO, headers=self.header_with_token)
        self.assertEqual(state.NO_DATA, response.json.get("label"), response.json)

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(HostProxy, "get_host_info")
    @mock.patch.object(HostProxy, "_create_session")
    @mock.patch.object(BaseResponse, "verify_request")
    def test_get_plugin_info_should_return_database_query_error_when_query_host_info_error(
            self, mock_verify, mock_connect, mock_host_info, mock_close_db):
        mock_verify.return_value = {"host_id": self.mock_host_id, "username": "mock_user"}, state.SUCCEED
        mock_connect.return_value = None
        mock_host_info.return_value = state.DATABASE_QUERY_ERROR, []
        mock_close_db.return_value = None
        response = self.client.get(AGENT_PLUGIN_INFO, headers=self.header_with_token)
        self.assertEqual(state.DATABASE_QUERY_ERROR, response.json.get("label"), response.json)

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch("zeus.agent_manager.view.execute_command_and_parse_its_result")
    @mock.patch.object(HostProxy, "get_host_info")
    @mock.patch.object(HostProxy, "_create_session")
    @mock.patch.object(BaseResponse, "verify_request")
    def test_get_plugin_info_should_return_error_label_when_command_execute_failed(
            self, mock_verify, mock_connect, mock_host_info, mock_execute, mock_close_db):
        mock_verify.return_value = {"host_id": self.mock_host_id, "username": "mock_user"}, state.SUCCEED
        mock_connect.return_value = None
        mock_host_info.return_value = state.SUCCEED, [self.mock_host_info]
        mock_execute.return_value = state.SSH_CONNECTION_ERROR, "SSH CONNECT ERROR"
        mock_close_db.return_value = None
        response = self.client.get(f"{AGENT_PLUGIN_INFO}?host_id={self.mock_host_id}", headers=self.header_with_token)
        self.assertEqual(state.SSH_CONNECTION_ERROR, response.json.get("label"), response.json)
