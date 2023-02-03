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
from io import StringIO
from typing import Tuple

import paramiko

__all__ = ["SSH", "generate_key"]


def generate_key() -> Tuple[str, str]:
    """
    generate RSA key pair

    Returns:
        tuple:(private key, public key )
    """
    output = StringIO()
    key = paramiko.RSAKey.generate(2048)
    key.write_private_key(output)
    private_key = output.getvalue()
    public_key = f'ssh-rsa {key.get_base64()}'
    return private_key, public_key


class SSH:
    """
    A SSH client used to run command in remote node
    """

    def __init__(self, **kwargs):
        self._client_args = {
            'hostname': kwargs.get('hostname'),
            'username': kwargs.get('username'),
            'port': kwargs.get('port'),
            "password": kwargs.get('password')
        }
        self._client = self.client()

    def client(self):
        """
        generate SSHClient and connect to remote node
        """
        ssh_client = paramiko.client.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        ssh_client.connect(**self._client_args, timeout=5)
        return ssh_client

    def execute_command(self, command: str):
        return self._client.exec_command(command)