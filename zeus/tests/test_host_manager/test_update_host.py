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
from unittest import mock

import sqlalchemy
from sqlalchemy.orm.collections import InstrumentedList

from vulcanus.conf.constant import UPDATE_HOST
from vulcanus.database.proxy import MysqlProxy
from vulcanus.database.table import Host, HostGroup
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse
from zeus.database.proxy.host import HostProxy
from zeus.tests import BaseTestCase


class TestConfigManage(BaseTestCase):
    header = {"Content-Type": "application/json; charset=UTF-8"}
    client = BaseTestCase.create_app()

    def setUp(self) -> None:
        self.mock_host_list = [
            Host(
                host_id=1,
                host_name="mock_host_1",
                host_ip="mock_ip_1",
                host_group_name="group1",
                ssh_user="root",
                pkey="pkey",
                ssh_port=22,
                management=True,
                host_group_id=1,
            ),
            Host(
                host_id=2,
                host_name="mock_host_2",
                host_ip="mock_ip_2",
                host_group_name="group1",
                ssh_user="root",
                pkey="pkey",
                ssh_port=22,
                management=True,
                host_group_id=1,
            ),
            Host(
                host_id=3,
                host_name="mock_host_3",
                host_ip="mock_ip_3",
                host_group_name="group1",
                ssh_user="root",
                pkey="pkey",
                ssh_port=22,
                management=True,
                host_group_id=1,
            ),
        ]
        self.group_list = [
            HostGroup(host_group_id=1, host_group_name="group1", description="test", username="admin"),
            HostGroup(host_group_id=2, host_group_name="group2", description="test", username="admin"),
        ]
        self.mock_args = {
            "host_id": 1,
            "ssh_port": 23,
            "ssh_user": "user",
            "password": "password",
            "host_name": "test1",
            "host_group_name": "group1",
            "management": True,
            "username": "admin",
        }
        self.incorrect_host_id = 10

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(HostProxy, "update_host_info")
    @mock.patch.object(BaseResponse, "verify_request")
    @mock.patch("zeus.host_manager.view.save_ssh_public_key_to_client")
    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    @mock.patch.object(MysqlProxy, "_create_session")
    def test_update_host_should_return_update_succeed_when_all_right(
            self, mock_connect, mock_hosts_and_groups, mock_save_keys, mock_verify_request, mock_update, mock_close):
        mock_connect.return_value = None
        mock_hosts_and_groups.return_value = state.SUCCEED, InstrumentedList(
            self.mock_host_list), InstrumentedList(self.group_list)
        mock_save_keys.return_value = state.SUCCEED, "pkey"
        mock_verify_request.return_value = self.mock_args, state.SUCCEED
        mock_update.return_value = state.SUCCEED
        mock_close.return_value = None
        response = self.client.post(UPDATE_HOST, data=json.dumps(self.mock_args),
                                    headers=self.header)
        self.assertEqual(state.SUCCEED, response.json.get("label"), response.json)

    @mock.patch.object(MysqlProxy, "_create_session")
    @mock.patch.object(BaseResponse, "verify_request")
    def test_update_host_should_return_database_connect_error_when_connect_database_fail(
            self, mock_verify_request, mock_connect):
        mock_verify_request.return_value = self.mock_args, state.SUCCEED
        mock_connect.side_effect = sqlalchemy.exc.SQLAlchemyError("Connection error")
        response = self.client.post(UPDATE_HOST, data=json.dumps(self.mock_args),
                                    headers=self.header)
        self.assertEqual(state.DATABASE_CONNECT_ERROR, response.json.get("label"), response.json)

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    @mock.patch.object(BaseResponse, "verify_request")
    @mock.patch.object(MysqlProxy, "_create_session")
    def test_update_host_should_return_database_query_error_when_query_host_infos_fail(
            self, mock_connect, mock_verify_request, mock_hosts_and_groups, mock_close):
        mock_verify_request.return_value = self.mock_args, state.SUCCEED
        mock_hosts_and_groups.return_value = state.DATABASE_QUERY_ERROR, InstrumentedList(), InstrumentedList()
        mock_connect.return_value = None
        mock_close.return_value = None
        response = self.client.post(UPDATE_HOST, data=json.dumps(self.mock_args),
                                    headers=self.header)
        self.assertEqual(state.DATABASE_QUERY_ERROR, response.json.get("label"), response.json)

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    @mock.patch.object(BaseResponse, "verify_request")
    @mock.patch.object(MysqlProxy, "_create_session")
    def test_update_host_should_return_no_data_in_database_when_input_host_id_not_in_database(
            self, mock_connect, mock_verify_request, mock_hosts_and_groups, mock_close):
        mock_verify_request.return_value = self.mock_args, state.SUCCEED
        mock_hosts_and_groups.return_value = state.SUCCEED, InstrumentedList(
            self.mock_host_list), InstrumentedList(self.group_list)
        mock_connect.return_value = None
        mock_close.return_value = None
        self.mock_args.update({"host_id": self.incorrect_host_id})
        response = self.client.post(UPDATE_HOST, data=json.dumps(self.mock_args), headers=self.header)
        self.assertEqual(state.NO_DATA, response.json.get("label"), response.json)

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    @mock.patch.object(BaseResponse, "verify_request")
    @mock.patch.object(MysqlProxy, "_create_session")
    def test_update_host_should_return_param_error_when_input_host_name_in_database(
            self, mock_connect, mock_verify_request, mock_hosts_and_groups, mock_close):
        mock_verify_request.return_value = self.mock_args, state.SUCCEED
        mock_hosts_and_groups.return_value = state.SUCCEED, InstrumentedList(
            self.mock_host_list), InstrumentedList(self.group_list)
        mock_connect.return_value = None
        mock_close.return_value = None
        self.mock_args.update({"host_name": "mock_host_1"})
        response = self.client.post(UPDATE_HOST, data=json.dumps(self.mock_args), headers=self.header)
        self.assertEqual(state.PARAM_ERROR, response.json.get("label"), response.json)

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    @mock.patch.object(BaseResponse, "verify_request")
    @mock.patch.object(MysqlProxy, "_create_session")
    def test_update_host_should_return_param_error_when_input_host_group_name_not_in_database(
            self, mock_connect, mock_verify_request, mock_hosts_and_groups, mock_close):
        mock_verify_request.return_value = self.mock_args, state.SUCCEED
        mock_hosts_and_groups.return_value = state.SUCCEED, InstrumentedList(
            self.mock_host_list), InstrumentedList(self.group_list)
        mock_connect.return_value = None
        mock_close.return_value = None
        self.mock_args.update({"host_group_name": "group3"})
        response = self.client.post(UPDATE_HOST, data=json.dumps(self.mock_args), headers=self.header)
        self.assertEqual(state.PARAM_ERROR, response.json.get("label"), response.json)

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    @mock.patch.object(BaseResponse, "verify_request")
    @mock.patch.object(MysqlProxy, "_create_session")
    def test_update_host_should_return_param_error_when_input_ssh_address_in_database(
            self, mock_connect, mock_verify_request, mock_hosts_and_groups, mock_close):
        mock_verify_request.return_value = self.mock_args, state.SUCCEED
        mock_hosts_and_groups.return_value = state.SUCCEED, InstrumentedList(
            self.mock_host_list), InstrumentedList(self.group_list)
        mock_connect.return_value = None
        mock_close.return_value = None
        self.mock_args.update({"ssh_port": "22"})
        response = self.client.post(UPDATE_HOST, data=json.dumps(self.mock_args), headers=self.header)
        self.assertEqual(state.PARAM_ERROR, response.json.get("label"), response.json)

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(HostProxy, "update_host_info")
    @mock.patch("zeus.host_manager.view.save_ssh_public_key_to_client")
    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    @mock.patch.object(BaseResponse, "verify_request")
    @mock.patch.object(MysqlProxy, "_create_session")
    def test_update_host_should_return_database_update_error_when_update_host_info_fail(
            self, mock_connect, mock_verify_request, mock_hosts_and_groups, mock_ssh_key, mock_update_host, mock_close):
        mock_verify_request.return_value = self.mock_args, state.SUCCEED
        mock_hosts_and_groups.return_value = state.SUCCEED, InstrumentedList(
            self.mock_host_list), InstrumentedList(self.group_list)
        mock_connect.return_value = None
        mock_close.return_value = None
        mock_ssh_key.return_value = state.SUCCEED, "pkey"
        mock_update_host.return_value = state.DATABASE_UPDATE_ERROR
        response = self.client.post(UPDATE_HOST, data=json.dumps(self.mock_args), headers=self.header)
        self.assertEqual(state.DATABASE_UPDATE_ERROR, response.json.get("label"), response.json)

    def test_update_host_should_return_token_error_when_request_api_without_token(self):
        self.mock_args.pop("username")
        response = self.client.post(UPDATE_HOST, data=json.dumps(self.mock_args), headers=self.header)
        self.assertEqual(state.TOKEN_ERROR, response.json.get("label"), response.json)

    def test_update_host_should_return_param_error_when_request_api_without_args(self):
        response = self.client.post(UPDATE_HOST, data=json.dumps({}), headers=self.header)
        self.assertEqual(state.PARAM_ERROR, response.json.get("label"), response.json)
