import re
from zeus.operation_service.app.core.framework.common.result_code import PluginResultCode
from zeus.operation_service.app.core.framework.plugins.base_plugin import BasePlugin
from vulcanus.log.log import LOGGER

COLOR_PATTERN = r'\x1b(\[.*?[@-~]|\].*?(\x07|\x1b\\))'


class Shell(BasePlugin):

    def run(self):
        result = dict()
        exitcode = False
        result["error_code"] = PluginResultCode.SUCCESS
        cmd = self._task_vars["cmd"]
        echo = ""
        LOGGER.info("[Shell]: %s", cmd)
        try:
            echo = self._ssh_con.cmd(cmd)
            exitcode = self._ssh_con.get_last_result()
        except Exception:
            result["error_code"] = PluginResultCode.FAILED

        echo_without_color = re.sub(COLOR_PATTERN, '', echo).strip("\r")
        result["error_msg"] = {
            "echo": echo_without_color,
            "exitcode": exitcode
        }
        return result
