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
from unittest import mock

import sqlalchemy

from vulcanus.exceptions import DatabaseConnectionFailed
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse
from zeus.conf.constant import DELETE_HOST
from zeus.database.proxy.host import HostProxy
from zeus.tests import BaseTestCase

client = BaseTestCase.create_app()
header = {"Content-Type": "application/json; charset=UTF-8"}
header_with_token = {"Content-Type": "application/json; charset=UTF-8", "access_token": "123456"}


class TestDeleteHost(BaseTestCase):
    def setUp(self) -> None:
        self.mock_args = {'host_list': [1, 2, 3]}

    def test_delete_host_should_return_token_error_when_part_of_input_with_no_token(self):
        resp = client.delete(DELETE_HOST, json=self.mock_args, headers=header)
        self.assertEqual(state.TOKEN_ERROR, resp.json.get('label'), resp.json)

    def test_delete_host_should_return_400_when_no_input(self):
        resp = client.delete(DELETE_HOST, headers=header_with_token)
        self.assertEqual(400, resp.status_code, resp.json)

    @mock.patch.object(BaseResponse, "verify_request")
    @mock.patch.object(HostProxy, '_create_session')
    def test_delete_host_should_return_database_error_when_database_cannot_connect(
        self, mock_mysql_connect, mock_verify_request
    ):
        mock_verify_request.return_value = self.mock_args, state.SUCCEED
        mock_mysql_connect.side_effect = DatabaseConnectionFailed("Connection error")
        resp = client.delete(DELETE_HOST, json=self.mock_args, headers=header_with_token)
        self.assertEqual(state.DATABASE_CONNECT_ERROR, resp.json.get('label'), resp.json)

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(HostProxy, "delete_host")
    @mock.patch.object(BaseResponse, "verify_request")
    @mock.patch.object(HostProxy, '_create_session')
    def test_delete_host_should_return_database_delete_error_when_database_query_error_or_delete_error(
        self, mock_mysql_connect, mock_verify_request, mock_delete_host, mock_close
    ):
        mock_verify_request.return_value = self.mock_args, state.SUCCEED
        mock_mysql_connect.return_value = None
        mock_delete_host.return_value = state.DATABASE_DELETE_ERROR, {}
        mock_close.return_value = None
        resp = client.delete(DELETE_HOST, json=self.mock_args, headers=header_with_token)
        self.assertEqual(state.DATABASE_DELETE_ERROR, resp.json.get("label"), resp.json)

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(HostProxy, "delete_host")
    @mock.patch.object(BaseResponse, "verify_request")
    @mock.patch.object(HostProxy, '_create_session')
    def test_delete_host_should_return_succeed_error_when_delete_successfully(
        self, mock_mysql_connect, mock_verify_request, mock_delete_host, mock_close
    ):
        mock_verify_request.return_value = self.mock_args, state.SUCCEED
        mock_mysql_connect.return_value = None
        mock_delete_host.return_value = state.DATABASE_DELETE_ERROR, {}
        mock_close.return_value = None
        resp = client.delete(DELETE_HOST, json=self.mock_args, headers=header_with_token)
        self.assertEqual(state.DATABASE_DELETE_ERROR, resp.json.get("label"), resp.json)
