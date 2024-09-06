import os.path
import time

from zeus.operation_service.app.core.framework.common.result_code import PluginResultCode
from zeus.operation_service.app.core.framework.plugins.base_plugin import BasePlugin
from zeus.operation_service.app.core.framework.tools.common_tools import compare_remote_and_local_file


class Script(BasePlugin):

    def run(self):
        result = dict()
        local_script = self._task_vars["script"]

        filename = os.path.basename(local_script)
        remote_tmp_dir = "/tmp/REF_{}".format(time.time())
        remote_script_file = remote_tmp_dir + "/" + filename

        # 多进程概率报错（因为文件夹可能被别的进程创建）
        if not self._sftp_con.exists(remote_tmp_dir):
            self._sftp_con.mkdir(remote_tmp_dir)

        if not os.path.exists(local_script):
            result["error_code"] = PluginResultCode.ERROR
            result["error_msg"] = "no such file exist"
            return result

        self._sftp_con.PutBinFile(local_script, remote_script_file)
        if not compare_remote_and_local_file(self.get_ssh_con(), remote_script_file, local_script):
            result["error_code"] = PluginResultCode.ERROR
            result["error_msg"] = "check sha256sum failed: " + local_script
            return result

        cmd = "bash {}".format(remote_script_file)
        echo = self._ssh_con.cmd(cmd)

        result["error_code"] = PluginResultCode.SUCCESS
        result["error_msg"] = echo

        return result
