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
import socket
from io import StringIO
from typing import Tuple

import paramiko
from paramiko import sftp

from vulcanus.log.log import LOGGER
from vulcanus.restful.resp import state

__all__ = ["SSH", "generate_key", "execute_command_and_parse_its_result"]

from zeus.function.model import ClientConnectArgs


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
        self._client_args = {
            'hostname': ip,
            'username': username,
            'port': port,
            "password": password,
            "pkey": pkey
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


def execute_command_and_parse_its_result(connect_args: ClientConnectArgs, command: str) -> tuple:
    """
    create a ssh client, execute command and parse result

    Args:
        connect_args(ClientConnectArgs): e.g
            ClientArgs(host_ip='127.0.0.1', ssh_port=22, ssh_user='root', pkey=RSAKey string)
        command(str): shell command

    Returns:
        tuple:
            status, result
    """
    if not connect_args.pkey:
        return state.SSH_AUTHENTICATION_ERROR, f"ssh authentication failed when connect host " \
                                               f"{connect_args.host_ip}"
    try:
        client = SSH(
            ip=connect_args.host_ip,
            username=connect_args.ssh_user,
            port=connect_args.ssh_port,
            pkey=paramiko.RSAKey.from_private_key(StringIO(connect_args.pkey))
        )
        exit_status, stdout, stderr = client.execute_command(command, connect_args.timeout)
    except socket.error as error:
        LOGGER.error(error)
        return state.SSH_CONNECTION_ERROR, "SSH.Connection.Error"
    except paramiko.ssh_exception.SSHException as error:
        LOGGER.error(error)
        return state.SSH_AUTHENTICATION_ERROR, "SSH.Authentication.Error"

    client.close()
    if exit_status == 0:
        return state.SUCCEED, stdout
    LOGGER.error(stderr)
    return state.EXECUTE_COMMAND_ERROR, stderr


def execute_command_sftp_result(connect_args: ClientConnectArgs, local_path=None, remote_path=None):
    """
    create a ssh client, execute command and parse result

    Args:
        connect_args(ClientConnectArgs): e.g
            ClientArgs(host_ip='127.0.0.1', ssh_port=22, ssh_user='root', pkey=RSAKey string)
        command(str): shell command

    Returns:
        tuple:
            status, result
    """
    global sftp_client, client
    if not connect_args.pkey:
        return state.SSH_AUTHENTICATION_ERROR, f"ssh authentication failed when connect host " \
                                               f"{connect_args.host_ip}"
    try:
        client = SSH(
            ip=connect_args.host_ip,
            username=connect_args.ssh_user,
            port=connect_args.ssh_port,
            pkey=paramiko.RSAKey.from_private_key(StringIO(connect_args.pkey))
        )
        sftp_client = client.client().open_sftp()

        # Specifies the path to the local file and the remote file
        # Upload files to a remote server
        sftp_client.put(local_path, remote_path)
        return state.SUCCEED
    except socket.error as error:
        LOGGER.error(error)
        return state.SSH_CONNECTION_ERROR, "SSH.Connection.Error"
    except paramiko.ssh_exception.SSHException as error:
        LOGGER.error(error)
        return state.SSH_AUTHENTICATION_ERROR, "SSH.Authentication.Error"
    except Exception as error:
        LOGGER.error(error)
        return state.SSH_AUTHENTICATION_ERROR, "SSH.Authentication.Error"
    finally:
        sftp_client.close()
        client.close()
