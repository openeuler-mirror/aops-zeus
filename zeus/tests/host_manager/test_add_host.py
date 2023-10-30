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
from paramiko import AuthenticationException
from sqlalchemy.orm.collections import InstrumentedList

from vulcanus.restful.response import BaseResponse
from vulcanus.restful.resp.state import (
    DATABASE_INSERT_ERROR,
    DATABASE_QUERY_ERROR,
    DATA_EXIST,
    EXECUTE_COMMAND_ERROR,
    PARAM_ERROR,
    SSH_AUTHENTICATION_ERROR,
    SSH_CONNECTION_ERROR,
    SUCCEED,
    TOKEN_ERROR,
)
from vulcanus.exceptions import DatabaseConnectionFailed
from zeus.conf.constant import ADD_HOST
from zeus.conf import configuration
from zeus.database.proxy.host import HostProxy
from zeus.database.table import Host, HostGroup
from zeus.host_manager.ssh import SSH
from zeus.host_manager.view import AddHost, save_ssh_public_key_to_client
from zeus.tests import BaseTestCase

client = BaseTestCase.create_app()
header = {"Content-Type": "application/json; charset=UTF-8"}
header_with_token = {"Content-Type": "application/json; charset=UTF-8", "access_token": "123456"}


class TestAddHost(unittest.TestCase):
    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch("zeus.host_manager.view.save_ssh_public_key_to_client")
    @mock.patch.object(BaseResponse, 'verify_token')
    @mock.patch.object(HostProxy, 'add_host')
    @mock.patch.object(AddHost, 'validate_host_info')
    @mock.patch.object(HostProxy, '_create_session')
    def test_add_host_should_add_host_succeed_when_input_valid_data_with_token(
        self, mock_connect, mock_validate_host_info, add_host, mock_token, mock_save_key, mock_close
    ):
        host_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "host_name": "test_host",
            "host_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
        }
        mock_connect.return_value = None
        mock_validate_host_info.return_value = SUCCEED, Host()
        add_host.return_value = SUCCEED
        mock_token.return_value = SUCCEED
        mock_save_key.return_value = SUCCEED, {"pkey": "private_key"}
        mock_close.return_value = None
        response = client.post(ADD_HOST, data=json.dumps(host_data), headers=header_with_token)
        self.assertEqual("Succeed", response.json.get('label'))

    def test_add_host_should_return_token_error_when_request_interface_without_token(self):
        host_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "host_name": "test_host",
            "host_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
        }
        response = client.post(ADD_HOST, data=json.dumps(host_data), headers=header)
        self.assertEqual("Token.Error", response.json.get('label'))

    @mock.patch.object(BaseResponse, 'verify_token')
    def test_add_host_should_return_token_error_when_request_interface_with_invalid_token(self, mock_token):
        mock_token.return_value = TOKEN_ERROR
        host_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "host_name": "test_host",
            "host_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
        }
        response = client.post(ADD_HOST, data=json.dumps(host_data), headers=header_with_token)
        self.assertEqual("Token.Error", response.json.get('label'))

    @mock.patch.object(HostProxy, '_create_session')
    @mock.patch.object(BaseResponse, 'verify_token')
    def test_add_host_should_return_database_connect_error_when_all_input_is_right_but_cannot_connect_database(
        self, mock_token, mock_connect
    ):
        host_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "host_name": "test_host",
            "host_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
        }
        mock_token.return_value = SUCCEED
        mock_connect.side_effect = DatabaseConnectionFailed("Connection error")
        response = client.post(ADD_HOST, data=json.dumps(host_data), headers=header_with_token)
        self.assertEqual("Database.Connect.Error", response.json.get('label'))

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(AddHost, 'validate_host_info')
    @mock.patch.object(HostProxy, '_create_session')
    @mock.patch.object(BaseResponse, 'verify_token')
    def test_add_host_should_return_database_query_error_when_input_all_is_right_but_query_hosts_failed(
        self, mock_token, mock_connect, mock_hosts, mock_close
    ):
        host_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "host_name": "test_host",
            "host_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
        }
        mock_token.return_value = SUCCEED
        mock_connect.return_value = None
        mock_hosts.return_value = DATABASE_QUERY_ERROR, InstrumentedList([])
        mock_close.return_value = None
        response = client.post(ADD_HOST, data=json.dumps(host_data), headers=header_with_token)
        self.assertEqual("Database.Query.Error", response.json.get('label'))

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(HostProxy, 'add_host')
    @mock.patch.object(AddHost, 'validate_host_info')
    @mock.patch.object(HostProxy, '_create_session')
    @mock.patch.object(BaseResponse, 'verify_token')
    def test_add_host_should_add_host_failed_when_input_valid_data_with_token_but_add_host_to_database_failed(
        self, mock_token, mock_connect, mock_validate_host, mock_add_host, mock_close
    ):
        host_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "host_name": "test_host",
            "host_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
        }
        mock_token.return_value = SUCCEED
        mock_connect.return_value = None
        mock_validate_host.return_value = SUCCEED, Host()
        mock_add_host.return_value = DATABASE_INSERT_ERROR
        mock_close.return_value = None
        response = client.post(ADD_HOST, data=json.dumps(host_data), headers=header_with_token)
        self.assertEqual("Database.Insert.Error", response.json.get('label'))

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(AddHost, 'validate_host_info')
    @mock.patch.object(HostProxy, '_create_session')
    @mock.patch.object(BaseResponse, 'verify_request')
    @mock.patch.object(BaseResponse, 'verify_token')
    def test_add_host_should_host_existed_when_host_is_in_database(
        self, mock_token, mcok_request, mock_connect, mock_validate_host_info, mock_close
    ):
        host_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "host_name": "test_host_1",
            "host_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
            "username": "admin",
        }

        mock_token.return_value = SUCCEED
        mcok_request.return_value = host_data, SUCCEED
        mock_connect.return_value = None
        mock_validate_host_info.return_value = DATA_EXIST, Host()
        mock_close.return_value = None
        response = client.post(ADD_HOST, data=json.dumps(host_data), headers=header_with_token)
        self.assertEqual("Data.Exist", response.json.get('label'))

    @mock.patch.object(HostProxy, "__exit__")
    @mock.patch.object(AddHost, 'validate_host_info')
    @mock.patch.object(HostProxy, '_create_session')
    @mock.patch.object(BaseResponse, 'verify_token')
    def test_add_host_should_param_error_when_host_group_is_not_in_database(
        self, mock_token, mock_connect, mock_validate_host_info, mock_close
    ):
        host_data = {
            "ssh_user": "test_user",
            "password": "test_password",
            "host_name": "test_host_1",
            "host_ip": "127.0.0.1",
            "host_group_name": "test_host_group_1",
            "ssh_port": 22,
            "management": False,
        }
        mock_token.return_value = SUCCEED
        mock_connect.return_value = None
        mock_validate_host_info.return_value = PARAM_ERROR, Host()
        mock_close.return_value = None
        response = client.post(ADD_HOST, data=json.dumps(host_data), headers=header_with_token)
        self.assertEqual("Param.Error", response.json.get('label'))

    @mock.patch.object(BaseResponse, 'verify_token')
    def test_add_host_should_param_error_when_input_host_attr_is_not_valid(self, mock_token):
        mock_token.return_value = SUCCEED
        host_infos = [
            {
                "host_name": "",
                "ssh_user": "test_user",
                "password": "test_password",
                "host_ip": "",
                "ssh_port": 0,
            },
            {
                "ssh_user": "",
                "password": 123456,
                "host_group_name": 1,
                "ssh_port": -22,
            },
            {
                "host_name": "test_host_1",
                "ssh_user": 2,
                "password": True,
                "host_ip": "ip",
                "management": True,
            },
            {
                "host_name": "test_host_1",
                "ssh_user": "test_user",
                "password": "test_password",
                "host_group_name": "test_host_group",
                "host_ip": 22,
                "ssh_port": -22,
                "management": True,
            },
            {
                "host_name": "",
                "ssh_user": "",
                "password": "test_password",
                "host_ip": 22,
                "ssh_port": -22,
                "management": True,
            },
            {
                "host_name": "",
                "ssh_user": 123,
                "password": 123,
                "host_group_name": "test_host_group",
                "host_ip": "127.0.0.1",
                "ssh_port": -22,
                "management": False,
            },
            {
                "host_name": "",
                "ssh_user": 123,
                "host_group_name": "test_host_group",
                "host_ip": "1271.0.0.1",
                "ssh_port": 0,
            },
            {
                "host_name": "",
                "password": "",
                "host_group_name": "",
                "host_ip": 123,
                "ssh_port": -22,
                "management": True,
            },
            {
                "host_name": "",
                "ssh_user": "test_user",
                "password": "",
                "host_group_name": 123,
                "management": True,
            },
            {
                "host_name": 123,
                "ssh_user": "",
                "password": "test_password",
                "host_ip": "1271.0.0.1",
                "management": True,
            },
            {
                "host_name": 123,
                "ssh_user": "",
                "host_group_name": 123,
                "host_ip": "127.0.0.1",
                "ssh_port": -22,
                "management": True,
            },
            {
                "host_name": 123,
                "ssh_user": 123,
                "password": "test_password",
                "host_group_name": "",
            },
            {
                "host_name": 123,
                "password": "",
                "host_group_name": "test_host_group",
                "host_ip": "127q.0.0.1",
                "ssh_port": 22,
            },
            {
                "host_name": 123,
                "host_group_name": "test_host_group",
                "host_ip": 123,
                "management": False,
            },
            {
                "host_name": 123,
                "ssh_user": "test_user",
                "password": 123,
                "host_group_name": "",
                "host_ip": "127.0.0.1",
                "ssh_port": 0,
                "management": False,
            },
            {
                "host_name": 123,
                "ssh_user": "test_user",
                "host_group_name": 123,
                "host_ip": 123,
                "ssh_port": 22,
            },
            {
                "ssh_user": "",
                "password": 123,
                "host_group_name": "test_host_group",
                "management": False,
            },
            {
                "ssh_user": 123,
                "password": "",
                "host_ip": "127.0.0.1",
                "ssh_port": 22,
            },
            {
                "ssh_user": 123,
                "password": "test_password",
                "host_group_name": "",
                "host_ip": 123,
                "ssh_port": 0,
                "management": True,
            },
            {
                "password": "test_password",
                "host_group_name": 123,
                "host_ip": "1271.0.0.1",
                "ssh_port": 0,
                "management": True,
            },
            {
                "ssh_user": "test_user",
                "host_ip": "1271.0.0.1",
                "ssh_port": -22,
                "management": False,
            },
            {
                "host_name": "test_host_1",
                "ssh_user": "",
                "password": "",
                "host_group_name": "",
                "host_ip": "1271.0.0.1",
                "ssh_port": 0,
                "management": False,
            },
            {"host_name": "test_host_1", "ssh_user": "", "host_group_name": "", "ssh_port": 22},
            {
                "host_name": "test_host_1",
                "ssh_user": 123,
                "password": 123,
                "host_group_name": 123,
                "host_ip": 123,
                "ssh_port": -22,
            },
            {
                "host_name": "test_host_1",
                "password": 123,
                "ssh_port": 22,
                "management": True,
            },
            {
                "host_name": "test_host_1",
                "password": "test_password",
                "host_group_name": 123,
                "host_ip": "127.0.0.1",
                "management": False,
            },
        ]
        result = []
        for host in host_infos:
            response = client.post(ADD_HOST, data=json.dumps(host), headers=header_with_token)
            result.append(response.json.get("label"))
        self.assertEqual(result, ["Param.Error"] * len(host_infos))

    @mock.patch("zeus.host_manager.view.generate_key")
    @mock.patch.object(SSH, "execute_command")
    @mock.patch.object(SSH, "client")
    def test_save_ssh_public_key_to_client_should_return_add_succeed_and_pkey_when_save_public_key_succeed(
        self, mock_ssh, mock_execute_command, mock_key_pair
    ):
        mock_ssh.return_value = paramiko.client.SSHClient()
        mock_key_pair.return_value = "private_key", "public_key"
        mock_execute_command.return_value = 0, '', BytesIO()
        mock_data = {"ssh_user": "test_user", "password": "test_password", "host_ip": "127.0.0.1", "ssh_port": 22}
        self.assertEqual(
            (SUCCEED, "private_key"),
            save_ssh_public_key_to_client(
                mock_data['host_ip'], mock_data['ssh_port'], mock_data["ssh_user"], mock_data["password"]
            ),
        )

    @mock.patch("zeus.host_manager.view.generate_key")
    @mock.patch.object(SSH, "client")
    def test_save_ssh_public_key_to_client_should_return_ssh_connect_error_when_connect_host_failed(
        self, mock_ssh, mock_key_pair
    ):
        mock_ssh.side_effect = socket.error()
        mock_key_pair.return_value = "private_key", "public_key"
        mock_data = {"ssh_user": "test_user", "password": "test_password", "host_ip": "127.0.0.1", "ssh_port": 22}
        self.assertEqual(
            SSH_CONNECTION_ERROR,
            save_ssh_public_key_to_client(
                mock_data['host_ip'], mock_data['ssh_port'], mock_data["ssh_user"], mock_data["password"]
            )[0],
        )

    @mock.patch("zeus.host_manager.view.generate_key")
    @mock.patch.object(SSH, "client")
    def test_save_ssh_public_key_to_client_should_return_ssh_authentication_error_when_authentication_failed(
        self, mock_ssh, mock_key_pair
    ):
        mock_ssh.side_effect = AuthenticationException
        mock_key_pair.return_value = "private_key", "public_key"
        mock_data = {"ssh_user": "test_user", "password": "test_password", "host_ip": "127.0.0.1", "ssh_port": 22}
        self.assertEqual(
            SSH_AUTHENTICATION_ERROR,
            save_ssh_public_key_to_client(
                mock_data['host_ip'], mock_data['ssh_port'], mock_data["ssh_user"], mock_data["password"]
            )[0],
        )

    @mock.patch("zeus.host_manager.view.generate_key")
    @mock.patch.object(SSH, "execute_command")
    @mock.patch.object(SSH, "client")
    def test_save_ssh_public_key_to_client_should_return_execute_command_error_when_save_key_to_host_failed(
        self, mock_ssh, mock_execute_command, mock_key_pair
    ):
        mock_ssh.return_value = paramiko.client.SSHClient()
        mock_key_pair.return_value = "private_key", "public_key"
        mock_execute_command.return_value = '', '', BytesIO(b"error")
        mock_data = {"ssh_user": "test_user", "password": "test_password", "host_ip": "127.0.0.1", "ssh_port": 22}
        self.assertEqual(
            EXECUTE_COMMAND_ERROR,
            save_ssh_public_key_to_client(
                mock_data['host_ip'], mock_data['ssh_port'], mock_data["ssh_user"], mock_data["password"]
            )[0],
        )

    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    def test_validate_host_info_should_return_host_object_when_host_info_is_valid(self, mock_hosts_with_groups):
        mock_host_info = {
            "ssh_user": "test_user",
            "host_name": "test_host_2",
            "host_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
            "user": "admin",
        }
        mock_group = HostGroup(host_group_id=1, host_group_name="test_host_group", description="test", username="admin")
        mock_hosts_with_groups.return_value = SUCCEED, InstrumentedList(), InstrumentedList([mock_group])
        target = AddHost()
        target.proxy = HostProxy()
        self.assertEqual(target.validate_host_info(mock_host_info)[0], SUCCEED)

    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    def test_validate_host_info_should_return_param_error_when_host_group_not_in_database(self, mock_hosts_with_groups):
        mock_host_info = {
            "ssh_user": "test_user",
            "host_name": "test_host_2",
            "host_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
            "user": "admin",
        }
        mock_group = HostGroup(host_group_id=1, host_group_name="test_group", description="test", username="admin")
        mock_hosts_with_groups.return_value = SUCCEED, InstrumentedList(), InstrumentedList([mock_group])
        target = AddHost()
        target.proxy = HostProxy()
        self.assertEqual(target.validate_host_info(mock_host_info)[0], PARAM_ERROR)

    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    def test_validate_host_info_should_return_data_exist_when_host_name_in_database(self, mock_hosts_with_groups):
        mock_host_info = {
            "ssh_user": "test_user",
            "host_name": "test_host",
            "host_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
            "username": "admin",
        }

        mock_host = Host(
            **{
                "ssh_user": "test_user",
                "host_name": "test_host",
                "host_ip": "127.0.0.2",
                "host_group_name": "test_host_group",
                "host_group_id": 1,
                "ssh_port": 22,
                "management": False,
                "user": "admin",
            }
        )
        mock_group = HostGroup(host_group_id=1, host_group_name="test_host_group", description="test", username="admin")
        mock_hosts_with_groups.return_value = SUCCEED, InstrumentedList([mock_host]), InstrumentedList([mock_group])
        target = AddHost()
        target.proxy = HostProxy()
        self.assertEqual(DATA_EXIST, target.validate_host_info(mock_host_info)[0])

    @mock.patch.object(HostProxy, "get_hosts_and_groups")
    def test_validate_host_info_should_return_data_exist_when_host_ip_in_database(self, mock_hosts_with_groups):
        mock_host_info = {
            "ssh_user": "test_user",
            "host_name": "test_host_1",
            "host_ip": "127.0.0.1",
            "host_group_name": "test_host_group",
            "ssh_port": 22,
            "management": False,
            "username": "admin",
        }

        mock_host = Host(
            **{
                "ssh_user": "test_user",
                "host_name": "test_host_2",
                "host_ip": "127.0.0.1",
                "host_group_name": "test_host_group",
                "host_group_id": 1,
                "ssh_port": 22,
                "management": False,
                "user": "admin",
            }
        )
        mock_group = HostGroup(host_group_id=1, host_group_name="test_host_group", description="test", username="admin")
        mock_hosts_with_groups.return_value = SUCCEED, InstrumentedList([mock_host]), InstrumentedList([mock_group])
        target = AddHost()
        target.proxy = HostProxy()
        self.assertEqual(DATA_EXIST, target.validate_host_info(mock_host_info)[0])
