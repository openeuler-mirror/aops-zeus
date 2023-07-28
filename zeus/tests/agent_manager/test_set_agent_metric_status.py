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
Time: 2023/6/10
Author:
Description: 
"""
import json
from unittest import mock

import sqlalchemy

from vulcanus.conf.constant import AGENT_METRIC_SET
from vulcanus.database.proxy import MysqlProxy
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse
from zeus.database.proxy.host import HostProxy
from zeus.tests import BaseTestCase


class TestSetAgentMetricStatus(BaseTestCase):
    client = BaseTestCase.create_app()

    def setUp(self) -> None:
        self.mock_args = {
            "host_id": 1,
            "plugins": {
                "plugin_1": {
                    "metric_1": "on",
                    "metric_2": "on",
                    "metric_3": "on"
                }
            }
        }

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

        self.header = {
            "Content-Type": "application/json; charset=UTF-8"
        }
        self.header_with_token = {
            "Content-Type": "application/json; charset=UTF-8",
            "access_token": "123456"
        }

    @mock.patch.object(MysqlProxy, "__exit__")
    @mock.patch("zeus.agent_manager.view.execute_command_and_parse_its_result")
    @mock.patch.object(HostProxy, "get_host_info")
    @mock.patch.object(MysqlProxy, "_create_session")
    @mock.patch.object(BaseResponse, "verify_request")
    def test_set_agent_metrics_status_should_return_set_succeed_when_all_is_right(
            self, mock_verify_request, mock_connect, mock_get_host_info, mock_execute_command, mock_close_db):
        self.mock_args["username"] = "mock_user"
        mock_verify_request.return_value = self.mock_args, state.SUCCEED
        mock_connect.return_value = None
        mock_get_host_info.return_value = state.SUCCEED, [self.mock_host_info]
        mock_execute_command.return_value = state.SUCCEED, json.dumps({
            "resp": {
                "plugin_1": {
                    "failure": [
                    ],
                    "success": [
                        "metric_1",
                        "metric_3",
                        "metric_2"
                    ]
                }
            }
        })
        mock_close_db.return_value = None
        response = self.client.post(AGENT_METRIC_SET, data=json.dumps(self.mock_args), headers=self.header_with_token)
        fail_list = []
        for plugin, metrics_set_res in response.json.get("data").get("resp").items():
            if metrics_set_res.get("failure"):
                fail_list.append(plugin)
        self.assertEqual(state.SUCCEED, response.json.get("label"))
        self.assertEqual([], fail_list)

    @mock.patch.object(BaseResponse, "verify_token")
    def test_set_agent_metrics_status_should_return_token_error_when_request_with_no_token_or_invalid_token(
            self, mock_verify_token):
        mock_verify_token.return_value = state.TOKEN_ERROR
        response = self.client.post(AGENT_METRIC_SET, data=json.dumps(self.mock_args), headers=self.header_with_token)
        self.assertEqual(state.TOKEN_ERROR, response.json.get("label"))

    def test_set_agent_metrics_status_should_return_400_when_request_with_no_args(self):
        response = self.client.post(AGENT_METRIC_SET, headers=self.header_with_token)
        self.assertEqual(400, response.status_code)

    def test_set_agent_metrics_status_should_return_405_when_request_with_incorrect_method(self):
        response = self.client.put(AGENT_METRIC_SET, data=json.dumps(self.mock_args), headers=self.header_with_token)
        self.assertEqual(405, response.status_code)

    def test_set_agent_metrics_status_should_return_param_error_when_request_with_incorrect_args(self):
        self.mock_args.pop("host_id")
        response = self.client.post(AGENT_METRIC_SET, data=json.dumps(self.mock_args), headers=self.header_with_token)
        self.assertEqual(state.PARAM_ERROR, response.json.get("label"))

    @mock.patch.object(MysqlProxy, "_create_session")
    @mock.patch.object(BaseResponse, "verify_request")
    def test_set_agent_metrics_status_should_return_database_connect_error_when_connect_database_error(
            self, mock_verify_request, mock_connect):
        mock_verify_request.return_value = self.mock_args, state.SUCCEED
        mock_connect.side_effect = sqlalchemy.exc.SQLAlchemyError("Connection error")
        response = self.client.post(AGENT_METRIC_SET, data=json.dumps(self.mock_args), headers=self.header_with_token)
        self.assertEqual(state.DATABASE_CONNECT_ERROR, response.json.get("label"))

    @mock.patch.object(MysqlProxy, "__exit__")
    @mock.patch.object(HostProxy, "get_host_info")
    @mock.patch.object(MysqlProxy, "_create_session")
    @mock.patch.object(BaseResponse, "verify_request")
    def test_set_agent_metrics_status_should_return_database_query_error_when_query_host_info_error(
            self, mock_verify_request, mock_connect, mock_get_host_info, mock_close_db):
        self.mock_args["username"] = "mock_user"
        mock_verify_request.return_value = self.mock_args, state.SUCCEED
        mock_connect.return_value = None
        mock_get_host_info.return_value = state.DATABASE_QUERY_ERROR, []
        mock_close_db.return_value = None
        response = self.client.post(AGENT_METRIC_SET, data=json.dumps(self.mock_args), headers=self.header_with_token)
        self.assertEqual(state.DATABASE_QUERY_ERROR, response.json.get("label"))

    @mock.patch.object(MysqlProxy, "__exit__")
    @mock.patch.object(HostProxy, "get_host_info")
    @mock.patch.object(MysqlProxy, "_create_session")
    @mock.patch.object(BaseResponse, "verify_request")
    def test_set_agent_metrics_status_should_return_no_data_when_input_host_id_is_not_in_database(
            self, mock_verify_request, mock_connect, mock_get_host_info, mock_close_db):
        self.mock_args["username"] = "mock_user"
        mock_verify_request.return_value = self.mock_args, state.SUCCEED
        mock_connect.return_value = None
        mock_get_host_info.return_value = state.SUCCEED, []
        mock_close_db.return_value = None
        response = self.client.post(AGENT_METRIC_SET, data=json.dumps(self.mock_args), headers=self.header_with_token)
        self.assertEqual(state.NO_DATA, response.json.get("label"))

    @mock.patch.object(MysqlProxy, "__exit__")
    @mock.patch("zeus.agent_manager.view.execute_command_and_parse_its_result")
    @mock.patch.object(HostProxy, "get_host_info")
    @mock.patch.object(MysqlProxy, "_create_session")
    @mock.patch.object(BaseResponse, "verify_request")
    def test_set_agent_metrics_status_should_return_ssh_connect_error_when_ssh_connect_host_failed(
            self, mock_verify_request, mock_connect, mock_get_host_info, mock_execute_command, mock_close_db):
        self.mock_args["username"] = "mock_user"
        mock_verify_request.return_value = self.mock_args, state.SUCCEED
        mock_connect.return_value = None
        mock_get_host_info.return_value = state.SUCCEED, [self.mock_host_info]
        mock_execute_command.return_value = state.SSH_CONNECTION_ERROR, "SSH CONNECT ERROR"
        mock_close_db.return_value = None
        response = self.client.post(AGENT_METRIC_SET, data=json.dumps(self.mock_args), headers=self.header_with_token)
        self.assertEqual(state.SSH_CONNECTION_ERROR, response.json.get("label"))
