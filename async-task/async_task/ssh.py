from dataclasses import dataclass
from typing import Tuple

import paramiko
from paramiko.ssh_exception import SSHException
from vulcanus.log.log import LOGGER


@dataclass
class SSHClientConfig:
    """
    Initialize the SSHClientConfig object.

    Args:
        hostname (str): Hostname or IP address of the SSH server.
        port (int): Port number of the SSH server.
        username (str): Username for SSH authentication.
        password (str): Password for SSH authentication.
        private_key (paramiko.RSAKey): RSAKey object representing the private key.
    """

    hostname: str
    port: int = 22
    username: str = None
    password: str = None
    private_key: paramiko.RSAKey = None


class ShellExitCode:
    SUCCESS = 0
    FAILURE = 255


class SSHClient:
    def __init__(self, config: SSHClientConfig):
        """
        Initialize the SSHClient object.

        Args:
            config (SSHClientConfig): Configuration object containing SSH client settings.
        """
        self.hostname = config.hostname
        self.port = config.port
        self.username = config.username
        self.password = config.password
        self.private_key = config.private_key
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self, timeout=10) -> bool:
        """
        Connect to the SSH server.

        Returns:
            bool: True if connection is successful, False otherwise.
        """
        try:
            self.client.connect(
                hostname=self.hostname,
                port=self.port,
                username=self.username,
                password=self.password,
                pkey=self.private_key,
                timeout=timeout,
            )
            return True
        except SSHException as e:
            LOGGER.error(f"Failed to connect to {self.hostname}: {e}")
            return False

    def execute_command(self, command: str, **kwargs) -> Tuple[int, str, str]:
        """
        Execute a command on the remote server.

        Args:
            command (str): Command to execute on the remote server.
            **kwargs: Additional keyword arguments, such as timeout.

        Returns:
            Tuple[int, str, str]: A tuple containing the command exit status, stdout, and stderr.
        """
        try:
            ssh_connect = True
            if not self.client.get_transport() or not self.client.get_transport().is_active():
                ssh_connect = self.connect()
            if not ssh_connect:
                return ShellExitCode.FAILURE, "", str("ssh connect fail")
            open_channel = self.client.get_transport().open_session(**kwargs)
            open_channel.set_combine_stderr(False)
            open_channel.exec_command(command)
            status = open_channel.recv_exit_status()
            stdout = open_channel.makefile("rb", -1).read().decode()
            stderr = open_channel.makefile_stderr("rb", -1).read().decode()
            return status, stdout, stderr
        except SSHException as e:
            LOGGER.error(f"Failed to execute command '{command}': {e}")
            return ShellExitCode.FAILURE, "", str(e)

    def close(self):
        if self.client.get_transport():
            self.client.close()
