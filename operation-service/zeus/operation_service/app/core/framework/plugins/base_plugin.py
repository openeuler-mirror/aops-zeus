from abc import abstractmethod, ABC


class BasePlugin(ABC):
    def __init__(self, ssh_con, sftp_con, task_vars, host):
        self._task_vars = task_vars
        self._ssh_con = ssh_con
        self._sftp_con = sftp_con
        self._host = host

    @abstractmethod
    def run(self):
        pass

    def get_ssh_con(self):
        return self._ssh_con

    def get_sftp_con(self):
        return self._sftp_con
