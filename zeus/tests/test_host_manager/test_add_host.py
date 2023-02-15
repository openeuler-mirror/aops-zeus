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
import socket
import unittest
from io import BytesIO
from unittest import mock

import paramiko
from flask import Flask
from paramiko import AuthenticationException
from sqlalchemy.orm.collections import InstrumentedList

from vulcanus.conf.constant import ADD_HOST
from vulcanus.database.table import Host, HostGroup, User
from vulcanus.restful.response import BaseResponse
from vulcanus.restful.status import (
    DATABASE_CONNECT_ERROR,
    DATABASE_INSERT_ERROR,
    DATABASE_QUERY_ERROR,
    DATA_EXIST,
    EXECUTE_COMMAND_ERROR,
    PARAM_ERROR,
    SSH_AUTHENTICATION_ERROR,
    SSH_CONNECTION_ERROR,
    SUCCEED,
    TOKEN_ERROR
)
from zeus import BLUE_POINT
from zeus.database.proxy.host import HostProxy
from zeus.host_manager.ssh import SSH
from zeus.host_manager.view import AddHost, save_ssh_public_key_to_client

app = Flask("check")
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
    "access_token": "123456"
}


class TestAddHost(unittest.TestCase):
    @mock.patch("zeus.host_manager.view.save_ssh_public_key_to_client")
    @mock.patch.object(BaseResponse, 'verify_token')
    @mock.patch.object(HostProxy, 'add_host')
    @mock.patch.object(AddHost, 'validate_host_info')
    @mock.patch.object(HostProxy, 'connect')
    def test_add_host_should_add_host_succeed_when_input_valid_data_with_token(
            self, mock_connect, mock_validate_host_info, add_host, mock_token, mock_save_key):
        host_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "host_name": "test_host",
            "public_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
        }
        mock_connect.return_value = True
        mock_validate_host_info.return_value = SUCCEED, Host()
        add_host.return_value = SUCCEED
        mock_token.return_value = SUCCEED
        mock_save_key.return_value = SUCCEED, {"pkey": "private_key"}
        response = client.post(ADD_HOST, data=json.dumps(host_data), headers=header_with_token)
        self.assertEqual(SUCCEED, response.json.get('code'))

    def test_add_host_should_return_token_error_when_request_interface_without_token(self):
        host_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "host_name": "test_host",
            "public_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
        }
        response = client.post(ADD_HOST, data=json.dumps(host_data), headers=header)
        self.assertEqual(TOKEN_ERROR, response.json.get('code'))

    @mock.patch.object(BaseResponse, 'verify_token')
    def test_add_host_should_return_token_error_when_request_interface_with_invalid_token(self,
                                                                                          mock_token):
        mock_token.return_value = TOKEN_ERROR
        host_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "host_name": "test_host",
            "public_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
        }
        response = client.post(ADD_HOST, data=json.dumps(host_data), headers=header_with_token)
        self.assertEqual(TOKEN_ERROR, response.json.get('code'))

    @mock.patch.object(HostProxy, 'connect')
    @mock.patch.object(BaseResponse, 'verify_token')
    def test_add_host_should_return_database_connect_error_when_all_input_is_right_but_cannot_connect_database(
            self, mock_token, mock_connect):
        host_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "host_name": "test_host",
            "public_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
        }
        mock_token.return_value = SUCCEED
        mock_connect.return_value = False
        response = client.post(ADD_HOST, data=json.dumps(host_data), headers=header_with_token)
        self.assertEqual(DATABASE_CONNECT_ERROR, response.json.get('code'))

    @mock.patch.object(AddHost, 'validate_host_info')
    @mock.patch.object(HostProxy, 'connect')
    @mock.patch.object(BaseResponse, 'verify_token')
    def test_add_host_should_return_database_query_error_when_input_all_is_right_but_query_hosts_failed(
            self, mock_token, mock_connect, mock_hosts):
        host_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "host_name": "test_host",
            "public_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
        }
        mock_token.return_value = SUCCEED
        mock_connect.return_value = True
        mock_hosts.return_value = DATABASE_QUERY_ERROR, InstrumentedList([])
        response = client.post(ADD_HOST, data=json.dumps(host_data), headers=header_with_token)
        self.assertEqual(DATABASE_QUERY_ERROR, response.json.get('code'))

    @mock.patch.object(HostProxy, 'add_host')
    @mock.patch.object(AddHost, 'validate_host_info')
    @mock.patch.object(HostProxy, 'connect')
    @mock.patch.object(BaseResponse, 'verify_token')
    def test_add_host_should_add_host_failed_when_input_valid_data_with_token_but_add_host_to_database_failed(
            self, mock_token, mock_connect, mock_validate_host, mock_add_host):
        host_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "host_name": "test_host",
            "public_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
        }
        mock_token.return_value = SUCCEED
        mock_connect.return_value = True
        mock_validate_host.return_value = SUCCEED, Host()
        mock_add_host.return_value = DATABASE_INSERT_ERROR
        response = client.post(ADD_HOST, data=json.dumps(host_data), headers=header_with_token)
        self.assertEqual(DATABASE_INSERT_ERROR, response.json.get('code'))

    @mock.patch.object(AddHost, 'validate_host_info')
    @mock.patch.object(HostProxy, 'connect')
    @mock.patch.object(BaseResponse, 'verify_request')
    @mock.patch.object(BaseResponse, 'verify_token')
    def test_add_host_should_host_existed_when_host_is_in_database(
            self, mock_token, mcok_request, mock_connect, mock_validate_host_info):
        host_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "host_name": "test_host_1",
            "public_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
            "username": "admin"
        }

        mock_token.return_value = SUCCEED
        mcok_request.return_value = host_data, SUCCEED
        mock_connect.return_value = True
        mock_validate_host_info.return_value = DATA_EXIST, Host()
        response = client.post(ADD_HOST, data=json.dumps(host_data), headers=header_with_token)
        self.assertEqual(DATA_EXIST, response.json.get('code'))

    @mock.patch.object(AddHost, 'validate_host_info')
    @mock.patch.object(HostProxy, 'connect')
    @mock.patch.object(BaseResponse, 'verify_token')
    def test_add_host_should_param_error_when_host_group_is_not_in_database(
            self, mock_token, mock_connect, mock_validate_host_info):
        host_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "host_name": "test_host_1",
            "public_ip": "127.0.0.1",
            "host_group_name": "test_host_group_1",
            "ssh_port": 22,
            "management": False,
        }
        mock_token.return_value = SUCCEED
        mock_connect.return_value = True
        mock_validate_host_info.return_value = PARAM_ERROR, Host()
        response = client.post(ADD_HOST, data=json.dumps(host_data), headers=header_with_token)
        self.assertEqual(PARAM_ERROR, response.json.get('code'))

    @mock.patch.object(BaseResponse, 'verify_token')
    def test_add_host_should_param_error_when_input_host_attr_is_not_valid(self, mock_token):
        mock_token.return_value = SUCCEED
        host_infos = [
            {
                "host_name": "",
                "ssh_user": "test_user",
                "password": "test_password",
                "public_ip": "",
                "ssh_port": 0,
            }, {
                "ssh_user": "",
                "password": 123456,
                "host_group_name": 1,
                "ssh_port": -22,
            }, {
                "host_name": "test_host_1",
                "ssh_user": 2,
                "password": True,
                "public_ip": "ip",
                "management": True,
            }, {
                "host_name": "test_host_1",
                "ssh_user": "test_user",
                "password": "test_password",
                "host_group_name": "test_host_group",
                "public_ip": 22,
                "ssh_port": -22,
                "management": True,
            }, {
                "host_name": "",
                "ssh_user": "",
                "password": "test_password",
                "public_ip": 22,
                "ssh_port": -22,
                "management": True,
            }, {
                "host_name": "",
                "ssh_user": 123,
                "password": 123,
                "host_group_name": "test_host_group",
                "public_ip": "127.0.0.1",
                "ssh_port": -22,
                "management": False,
            }, {
                "host_name": "",
                "ssh_user": 123,
                "host_group_name": "test_host_group",
                "public_ip": "1271.0.0.1",
                "ssh_port": 0,
            }, {
                "host_name": "",
                "password": "",
                "host_group_name": "",
                "public_ip": 123,
                "ssh_port": -22,
                "management": True,
            }, {
                "host_name": "",
                "ssh_user": "test_user",
                "password": "",
                "host_group_name": 123,
                "management": True,
            }, {
                "host_name": 123,
                "ssh_user": "",
                "password": "test_password",
                "public_ip": "1271.0.0.1",
                "management": True,
            }, {
                "host_name": 123,
                "ssh_user": "",
                "host_group_name": 123,
                "public_ip": "127.0.0.1",
                "ssh_port": -22,
                "management": True,
            }, {
                "host_name": 123,
                "ssh_user": 123,
                "password": "test_password",
                "host_group_name": "",
            }, {
                "host_name": 123,
                "password": "",
                "host_group_name": "test_host_group",
                "public_ip": "127q.0.0.1",
                "ssh_port": 22,
            }, {
                "host_name": 123,
                "host_group_name": "test_host_group",
                "public_ip": 123,
                "management": False,
            }, {
                "host_name": 123,
                "ssh_user": "test_user",
                "password": 123,
                "host_group_name": "",
                "public_ip": "127.0.0.1",
                "ssh_port": 0,
                "management": False,
            }, {
                "host_name": 123,
                "ssh_user": "test_user",
                "host_group_name": 123,
                "public_ip": 123,
                "ssh_port": 22,
            }, {
                "ssh_user": "",
                "password": 123,
                "host_group_name": "test_host_group",
                "management": False,
            }, {
                "ssh_user": 123,
                "password": "",
                "public_ip": "127.0.0.1",
                "ssh_port": 22,
            }, {
                "ssh_user": 123,
                "password": "test_password",
                "host_group_name": "",
                "public_ip": 123,
                "ssh_port": 0,
                "management": True,
            }, {
                "password": "test_password",
                "host_group_name": 123,
                "public_ip": "1271.0.0.1",
                "ssh_port": 0,
                "management": True,
            }, {
                "ssh_user": "test_user",
                "public_ip": "1271.0.0.1",
                "ssh_port": -22,
                "management": False,
            }, {
                "host_name": "test_host_1",
                "ssh_user": "",
                "password": "",
                "host_group_name": "",
                "public_ip": "1271.0.0.1",
                "ssh_port": 0,
                "management": False,
            }, {
                "host_name": "test_host_1",
                "ssh_user": "",
                "host_group_name": "",
                "ssh_port": 22
            }, {
                "host_name": "test_host_1",
                "ssh_user": 123,
                "password": 123,
                "host_group_name": 123,
                "public_ip": 123,
                "ssh_port": -22,
            }, {
                "host_name": "test_host_1",
                "password": 123,
                "ssh_port": 22,
                "management": True,
            }, {
                "host_name": "test_host_1",
                "password": "test_password",
                "host_group_name": 123,
                "public_ip": "127.0.0.1",
                "management": False,
            }
        ]
        result = []
        for host in host_infos:
            response = client.post(ADD_HOST, data=json.dumps(host), headers=header_with_token)
            result.append(response.json.get("code"))
        self.assertEqual(result, [PARAM_ERROR] * len(host_infos))

    @mock.patch("zeus.host_manager.view.generate_key")
    @mock.patch.object(SSH, "execute_command")
    @mock.patch.object(SSH, "client")
    def test_save_ssh_public_key_to_client_should_return_add_succeed_and_pkey_when_save_public_key_succeed(
            self, mock_ssh, mock_execute_command, mock_key_pair):
        mock_ssh.return_value = paramiko.client.SSHClient()
        mock_key_pair.return_value = "private_key", "public_key"
        mock_execute_command.return_value = '', '', BytesIO()
        mock_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "public_ip": "127.0.0.1",
            "ssh_port": 22
        }
        self.assertEqual((SUCCEED, "private_key"),
                         save_ssh_public_key_to_client(mock_data['public_ip'],
                                                       mock_data['ssh_port'],
                                                       mock_data["ssh_user"],
                                                       mock_data["password"]))

    @mock.patch("zeus.host_manager.view.generate_key")
    @mock.patch.object(SSH, "client")
    def test_save_ssh_public_key_to_client_should_return_ssh_connect_error_when_connect_host_failed(
            self, mock_ssh, mock_key_pair):
        mock_ssh.side_effect = socket.error()
        mock_key_pair.return_value = "private_key", "public_key"
        mock_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "public_ip": "127.0.0.1",
            "ssh_port": 22
        }
        self.assertEqual(SSH_CONNECTION_ERROR,
                         save_ssh_public_key_to_client(mock_data['public_ip'],
                                                       mock_data['ssh_port'],
                                                       mock_data["ssh_user"],
                                                       mock_data["password"])[0])

    @mock.patch("zeus.host_manager.view.generate_key")
    @mock.patch.object(SSH, "client")
    def test_save_ssh_public_key_to_client_should_return_ssh_authentication_error_when_authentication_failed(
            self, mock_ssh, mock_key_pair):
        mock_ssh.side_effect = AuthenticationException
        mock_key_pair.return_value = "private_key", "public_key"
        mock_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "public_ip": "127.0.0.1",
            "ssh_port": 22
        }
        self.assertEqual(SSH_AUTHENTICATION_ERROR,
                         save_ssh_public_key_to_client(mock_data['public_ip'],
                                                       mock_data['ssh_port'],
                                                       mock_data["ssh_user"],
                                                       mock_data["password"])[0])

    @mock.patch("zeus.host_manager.view.generate_key")
    @mock.patch.object(SSH, "execute_command")
    @mock.patch.object(SSH, "client")
    def test_save_ssh_public_key_to_client_should_return_execute_command_error_when_save_key_to_host_failed(
            self, mock_ssh, mock_execute_command, mock_key_pair):
        mock_ssh.return_value = paramiko.client.SSHClient()
        mock_key_pair.return_value = "private_key", "public_key"
        mock_execute_command.return_value = '', '', BytesIO(b"error")
        mock_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "public_ip": "127.0.0.1",
            "ssh_port": 22
        }
        self.assertEqual(EXECUTE_COMMAND_ERROR,
                         save_ssh_public_key_to_client(mock_data['public_ip'],
                                                       mock_data['ssh_port'],
                                                       mock_data["ssh_user"],
                                                       mock_data["password"])[0])

    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    def test_validate_host_info_should_return_host_object_when_host_info_is_valid(
            self, mock_hosts_with_groups):
        mock_host_info = {
            "ssh_user": "test_user",
            "host_name": "test_host_2",
            "public_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
            "user": "admin"
        }
        mock_group = HostGroup(host_group_id=1, host_group_name="test_host_group", description="test", username="admin")
        mock_hosts_with_groups.return_value = SUCCEED, InstrumentedList(), InstrumentedList([mock_group])
        target = AddHost()
        target.proxy = HostProxy()
        self.assertEqual(target.validate_host_info(mock_host_info)[0], SUCCEED)

    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    def test_validate_host_info_should_return_param_error_when_host_group_not_in_database(
            self, mock_hosts_with_groups):
        mock_host_info = {
            "ssh_user": "test_user",
            "host_name": "test_host_2",
            "public_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
            "user": "admin"
        }
        mock_group = HostGroup(host_group_id=1, host_group_name="test_group", description="test", username="admin")
        mock_hosts_with_groups.return_value = SUCCEED, InstrumentedList(), InstrumentedList([mock_group])
        target = AddHost()
        target.proxy = HostProxy()
        self.assertEqual(target.validate_host_info(mock_host_info)[0], PARAM_ERROR)

    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    def test_validate_host_info_should_return_data_exist_when_host_name_in_database(
            self, mock_hosts_with_groups):
        mock_host_info = {
            "ssh_user": "test_user",
            "host_name": "test_host",
            "public_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
            "username": "admin"
        }

        mock_host = Host(**{
            "ssh_user": "test_user",
            "host_name": "test_host",
            "public_ip": "127.0.0.2",
            "host_group_name": "test_host_group",
            "host_group_id": 1,
            "ssh_port": 22,
            "management": False,
            "user": "admin"
        })
        mock_group = HostGroup(host_group_id=1, host_group_name="test_host_group",
                               description="test", username="admin")
        mock_hosts_with_groups.return_value = SUCCEED, InstrumentedList([mock_host]), InstrumentedList([mock_group])
        target = AddHost()
        target.proxy = HostProxy()
        self.assertEqual(DATA_EXIST, target.validate_host_info(mock_host_info)[0])

    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    def test_validate_host_info_should_return_data_exist_when_host_ip_in_database(
            self, mock_hosts_with_groups):
        mock_host_info = {
            "ssh_user": "test_user",
            "host_name": "test_host_1",
            "public_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
            "username": "admin"
        }

        mock_host = Host(**{
            "ssh_user": "test_user",
            "host_name": "test_host_2",
            "public_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "host_group_id": 1,
            "ssh_port": 22,
            "management": False,
            "user": "admin"
        })
        mock_group = HostGroup(host_group_id=1, host_group_name="test_host_group",
                               description="test", username="admin")
        mock_hosts_with_groups.return_value = SUCCEED, InstrumentedList([mock_host]), InstrumentedList([mock_group])
        target = AddHost()
        target.proxy = HostProxy()
        self.assertEqual(DATA_EXIST, target.validate_host_info(mock_host_info)[0])
