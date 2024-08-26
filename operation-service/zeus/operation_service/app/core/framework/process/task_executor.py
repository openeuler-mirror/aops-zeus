from zeus.operation_service.app.core.framework.common.crypto_tool import AESCrypt
from zeus.operation_service.app.core.framework.common.result_code import PluginResultCode
from zeus.operation_service.app.core.framework.tools import ssh, sftp
from zeus.operation_service.app.core.framework.tools.task_result import TaskResult
from vulcanus.log.log import LOGGER


class TaskExecutor:
    def __init__(self, host, task):
        self._host = host
        self._task = task
        self._ssh_con = ssh.RemoteControl(self._host["ip"],
                                          self._host["username"],
                                          self._host["password"],
                                          self._host["passwordless"],
                                          self._host["port"])
        self._sftp_con = sftp.FileMgr(self._ssh_con)
        self._ssh_con.timeout = 60 * 60

    def run(self):
        self._build_handler()
        module_result = dict()
        module_result["error_msg"] = "Module execution failed"
        module_result["error_code"] = PluginResultCode.FAILED
        try:
            module_result = self._handler.run()
        except Exception as e:
            LOGGER.error(e)
        finally:
            self._ssh_con.close()

        return TaskResult(self._host, self._task, module_result)

    def _build_handler(self):
        module_name = self._task["name"]
        package = __import__("zeus.operation_service.app.core.framework.plugins", fromlist=[module_name])
        module = getattr(package, module_name)
        clazz = getattr(module, module_name.title().replace("_", ""))
        self._handler = clazz(self._ssh_con, self._sftp_con, self._task, self._host)
