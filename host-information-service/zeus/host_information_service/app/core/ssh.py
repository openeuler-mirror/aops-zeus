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

    Attributes:
        ip(str):   host ip address, the field is used to record ip information in method
        paramiko.client.SSHClient()
        username(str):   remote login user
        port(int or str):   remote login port
        password(str)
        pkey(str): RSA-KEY string

    Notes:
        In this project, the password field is used when connect to the host for the first
        time, and the pkey field is used when need to execute the command on the client.
    """

    def __init__(self, ip, username, port, password=None, pkey=None):
        self._client_args = {'hostname': ip, 'username': username, 'port': port, "password": password, "pkey": pkey}
        self._client = self.client()

    def client(self):
        """
        generate SSHClient and connect to remote node
        """
        ssh_client = paramiko.client.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        ssh_client.connect(**self._client_args, timeout=5)
        return ssh_client

    def execute_command(self, command: str, timeout: float = None) -> tuple:
        """
        create a ssh client, execute command and parse result

        Args:
            command(str): shell command
            timeout(float): the maximum time to wait for the result of command execution

        Returns:
            tuple:
                status, result, error message
        """
        open_channel = self._client.get_transport().open_session(timeout=timeout)
        open_channel.set_combine_stderr(False)
        open_channel.exec_command(command)
        statue = open_channel.recv_exit_status()
        stdout = open_channel.makefile("rb", -1).read().decode()
        stderr = open_channel.makefile_stderr("rb", -1).read().decode()
        return statue, stdout, stderr

    def close(self):
        """
        close open_channel
        """
        self._client.close()
