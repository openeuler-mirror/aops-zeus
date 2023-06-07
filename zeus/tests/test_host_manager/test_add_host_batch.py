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

from sqlalchemy.orm.collections import InstrumentedList

from vulcanus.conf.constant import ADD_HOST_BATCH
from vulcanus.database.proxy import MysqlProxy
from vulcanus.database.table import Host, HostGroup
from vulcanus.multi_thread_handler import MultiThreadHandler
from vulcanus.restful.resp import state
from zeus.database.proxy.host import HostProxy
from zeus.host_manager.view import AddHostBatch
from zeus.tests import BaseTestCase

client = BaseTestCase.create_app()
header = {
    "Content-Type": "application/json; charset=UTF-8"
}
header_with_token = {
    "Content-Type": "application/json; charset=UTF-8",
    "access_token": "123456"
}


class TestAddHostBatch(BaseTestCase):

    def setUp(self):
        self.mock_host_list = [
            {
                "host_name": "mock_host_1",
                "host_ip": "mock_ip_1",
                "host_group_name": "group1",
                "ssh_user": "root",
                "password": "password",
                "ssh_port": "22",
                "management": True
            },
            {
                "host_name": "mock_host_2",
                "host_ip": "mock_ip_2",
                "host_group_name": "group1",
                "ssh_user": "root",
                "password": "password",
                "ssh_port": "22",
                "management": True
            },
            {
                "host_name": "mock_host_3",
                "host_ip": "mock_ip_3",
                "host_group_name": "group1",
                "ssh_user": "root",
                "password": "password",
                "ssh_port": "22",
                "management": True
            }
        ]
        self.mock_group = HostGroup(host_group_id=1, host_group_name="group1", description="test",
                                    username="admin")

    @mock.patch.object(MultiThreadHandler, "get_result")
    @mock.patch.object(MultiThreadHandler, "create_thread")
    @mock.patch.object(HostProxy, "add_host_batch")
    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    @mock.patch.object(HostProxy, "connect")
    @mock.patch.object(AddHostBatch, "verify_request")
    def test_add_host_batch_should_add_host_succeed_when_input_valid_data_with_token(
            self, mock_verify_request, mock_connect, mock_hosts_with_groups,
            mock_add_host_batch, mock_create_thread, mock_get_result):
        mock_verify_request.return_value = state.SUCCEED, {"host_list": self.mock_host_list,
                                                           "username": "admin"}
        mock_connect.return_value = True
        mock_hosts_with_groups.return_value = state.SUCCEED, InstrumentedList(), InstrumentedList(
            [self.mock_group])
        mock_create_thread.return_value = None
        mock_get_result.return_value = self.mock_host_list
        mock_add_host_batch.return_value = state.SUCCEED
        response = client.post(ADD_HOST_BATCH, data={"host_list": self.mock_host_list},
                               headers=header_with_token)
        for host in self.mock_host_list:
            host.pop("host_group_id")
            host.pop("user")
            host.update({"result": "succeed"})
        self.assertEqual(self.mock_host_list, response.json.get("data"))

    @mock.patch.object(AddHostBatch, "verify_request")
    def test_add_host_batch_should_token_error_when_request_without_token_or_request_with_incorrect_token(
            self, mock_verify_request):
        mock_verify_request.return_value = state.TOKEN_ERROR, {}
        response = client.post(ADD_HOST_BATCH, data={"host_list": self.mock_host_list},
                               headers=header_with_token)
        self.assertEqual(state.TOKEN_ERROR, response.json.get('label'))

    @mock.patch.object(HostProxy, "connect")
    @mock.patch.object(AddHostBatch, "verify_request")
    def test_add_host_batch_should_database_connect_error_when_connect_database_failed(
            self, mock_verify_request, mock_connect_database):
        mock_verify_request.return_value = state.SUCCEED, {"host_list": self.mock_host_list}
        mock_connect_database.return_value = False
        response = client.post(ADD_HOST_BATCH, data={"host_list": self.mock_host_list},
                               headers=header_with_token)
        self.assertEqual(state.DATABASE_CONNECT_ERROR, response.json.get('label'))

    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    @mock.patch.object(HostProxy, "connect")
    @mock.patch.object(AddHostBatch, "verify_request")
    def test_add_host_batch_should_database_query_error_when_query_hosts_with_groups_failed(
            self, mock_verify_request, mock_connect_database, mock_query):
        mock_verify_request.return_value = state.SUCCEED, {"host_list": self.mock_host_list}
        mock_connect_database.return_value = True
        mock_query.return_value = state.DATABASE_QUERY_ERROR, InstrumentedList(), InstrumentedList()
        response = client.post(ADD_HOST_BATCH, data={"host_list": self.mock_host_list},
                               headers=header_with_token)
        self.assertEqual(state.DATABASE_QUERY_ERROR, response.json.get('label'))

    @mock.patch.object(MultiThreadHandler, "get_result")
    @mock.patch.object(MultiThreadHandler, "create_thread")
    @mock.patch.object(HostProxy, "add_host_batch")
    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    @mock.patch.object(HostProxy, "connect")
    @mock.patch.object(AddHostBatch, "verify_request")
    def test_add_host_batch_should_database_insert_error_when_insert_into_data_failed(
            self, mock_verify_request, mock_connect_database, mock_query,
            mock_add_host_batch, mock_create_thread, mock_get_result):
        mock_verify_request.return_value = state.SUCCEED, {"host_list": self.mock_host_list,
                                                           "username": "admin"}
        mock_connect_database.return_value = True
        mock_query.return_value = state.SUCCEED, InstrumentedList(), InstrumentedList(
            [self.mock_group])
        mock_create_thread.return_value = None
        mock_get_result.return_value = self.mock_host_list
        mock_add_host_batch.return_value = state.DATABASE_INSERT_ERROR
        response = client.post(ADD_HOST_BATCH, data={"host_list": self.mock_host_list},
                               headers=header_with_token)
        self.assertEqual(state.DATABASE_INSERT_ERROR, response.json.get('label'))

    def test_verify_request_should_return_param_error_when_request_args_is_incorrect(self):
        mock_incorrect_args_list = [
            [{
                "host_name": "hostname1",
                "ssh_user": "user1",
                "password": "password1",
                "host_group_name": "hostgroup1",
                "host_ip": "host_ip1",
                "ssh_port": "22",
                "management": True
            }],
            [{
                "host_name": 123,
                "ssh_user": 123,
                "password": 123,
                "host_group_name": 123,
                "host_ip": "host_ip1",
                "ssh_port": "port",
                "management": "Ok"
            }],
            [{
                "host_ip": "host_ip1",
            }],
            [{
                "host_name": "hostname1",
                "password": "password1",
                "host_group_name": False,
                "host_ip": "127.0.0.1",
                "ssh_port": "port",
            }],
            [{
                "ssh_user": 123,
                "password": "password1",
                "host_group_name": "error group",
                "host_ip": "127.0.0.1",
                "ssh_port": 22,
                "management": True
            }],
            [{
                "host_name": "hostname1",
                "ssh_user": 123,
                "password": 123,
                "host_ip": "host_ip1",
                "management": True
            }],
            [{
                "host_name": 123,
                "password": "password1",
                "host_group_name": "error group",
                "host_ip": "host_ip1",
                "ssh_port": "22",
                "management": "Ok"
            }],
            [{
                "ssh_user": "user1",
                "password": 123,
                "host_group_name": "hostgroup1",
                "host_ip": "host_ip1",
                "ssh_port": "22",
            }],
            [
                {
                    "host_name": "hostname1",
                    "ssh_user": "user1",
                    "password": "password1",
                    "host_group_name": "hostgroup1",
                    "host_ip": "127.0.0.1",
                    "ssh_port": 22,
                    "management": True
                },
                {
                    "host_name": "hostname1",
                    "ssh_user": "user1",
                    "password": "password1",
                    "host_group_name": "hostgroup1",
                    "host_ip": "127.0.0.1",
                    "ssh_port": 22,
                    "management": True
                }
            ],
            [{
                "host_name": "hostname1",
                "ssh_user": 123,
                "management": True
            }]

        ]
        response = []
        for host_list in mock_incorrect_args_list:
            resp = client.post(ADD_HOST_BATCH, data=json.dumps({"host_list": host_list}),
                               headers=header_with_token)
            response.append(resp.json.get('label'))
        self.assertEqual([state.PARAM_ERROR] * len(mock_incorrect_args_list), response)

    @mock.patch.object(AddHostBatch, "verify_token")
    @mock.patch("zeus.host_manager.view.validate")
    def test_verify_request_should_return_token_error_when_request_without_token_or_token_is_incorrect(
            self, mock_validate, mock_token_validator):
        mock_validate.return_value = {"host_list": self.mock_host_list}, {}
        mock_token_validator.return_value = state.TOKEN_ERROR
        response = client.post(ADD_HOST_BATCH, data=json.dumps({"host_list": self.mock_host_list}),
                               headers=header_with_token)
        self.assertEqual(state.TOKEN_ERROR, response.json.get('label'))

    @mock.patch.object(AddHostBatch, "verify_token")
    @mock.patch("zeus.host_manager.view.validate")
    def test_verify_request_should_return_param_error_when_request_args_have_duplicate_data(
            self, mock_validate, mock_token_validator):
        self.mock_host_list[0].update({"host_name": "mock_host_2"})
        mock_validate.return_value = {"host_list": self.mock_host_list}, {}
        mock_token_validator.return_value = state.SUCCEED
        response = client.post(ADD_HOST_BATCH, data=json.dumps({"host_list": self.mock_host_list}),
                               headers=header_with_token)
        self.assertEqual(state.PARAM_ERROR, response.json.get('label'))

    @mock.patch("zeus.host_manager.view.save_ssh_public_key_to_client")
    def test_multi_thread_handler_function_should_return_host_with_its_pkey_when_save_rsa_key_succeed(
            self, mock_save_key):
        mock_save_key.return_value = state.SUCCEED, "pkey"
        mock_host = Host(
            host_name="hostname1", ssh_user="user1", host_group_name="hostgroup1",
            host_ip="127.0.0.1", ssh_port=22, management=True
        )
        mock_args = mock_host, "password"
        mock_host.pkey = "pkey"
        self.assertEqual(mock_host, AddHostBatch().update_rsa_key_to_host(*mock_args))

    @mock.patch("zeus.host_manager.view.save_ssh_public_key_to_client")
    def test_multi_thread_handler_function_should_return_host_without_pkey_when_save_rsa_key_failed(
            self, mock_save_key):
        mock_save_key.return_value = state.SSH_AUTHENTICATION_ERROR, ""
        mock_host = Host(
            host_name="hostname1", ssh_user="user1", host_group_name="hostgroup1",
            host_ip="127.0.0.1", ssh_port=22, management=True
        )
        mock_args = mock_host, "password"
        self.assertEqual(mock_host, AddHostBatch().update_rsa_key_to_host(*mock_args))
