import os
import re
from pathlib import Path
from zeus.operation_service.app.core.framework.common.result_code import PluginResultCode
from zeus.operation_service.app.core.framework.plugins.base_plugin import BasePlugin
from zeus.operation_service.app.core.framework.tools.common_tools import compare_remote_and_local_file
from vulcanus.log.log import LOGGER

COLOR_PATTERN = r'\x1b(\[.*?[@-~]|\].*?(\x07|\x1b\\))'
class Copy(BasePlugin):

    def run(self):
        result = dict()
        src = self._task_vars["src"]
        dest = self._task_vars["dest"]
        dest = Path(dest).as_posix()
        if dest.startswith("~"):
            dest = self.handle_tilde(dest)
        LOGGER.info("[Copy]: From %s to %s", src, dest)
        if not os.path.exists(src) or os.path.isdir(src):
            result["error_code"] = PluginResultCode.ERROR
            result["error_msg"] = "no such file exist or the path is dir:" + src
            return result

        remote_dir = os.path.dirname(dest)

        # 递归创建目录
        if not self._sftp_con.exists(remote_dir):
            self.mkdirs(remote_dir)
        if not self._sftp_con.exists(remote_dir):
            LOGGER.error(f"[Copy]: make remote dir failed: {remote_dir}")

        # 传输文件
        if self._sftp_con.exists(dest):
            self._sftp_con.delete(dest)
        self._sftp_con.PutBinFile(src, dest)
        if not self._sftp_con.exists(dest):
            LOGGER.error("[Copy]: copy file failed, remote file not exists")
            result["error_code"] = PluginResultCode.ERROR
            result["error_msg"] = "upload file failed: " + src
            return result

        # 通过 sha256 摘要信息判断是否上传成功
        if not compare_remote_and_local_file(self.get_ssh_con(), dest, src):
            LOGGER.error("[Copy]: copy file failed, incorrect SHA256 digest information")
            result["error_code"] = PluginResultCode.ERROR
            result["error_msg"] = "check sha256sum failed: " + src
            return result
        # chmod chown
        # 验证用户是否合法
        if "owner" in self._task_vars and "group" in self._task_vars:
            self._sftp_con.chown(dest, self._task_vars["owner"], self._task_vars["group"])
        if "mode" in self._task_vars:
            self._sftp_con.chmod(dest, self._task_vars["mode"])
        LOGGER.info("[Copy]: copy file success")
        result["error_code"] = PluginResultCode.SUCCESS
        result["error_msg"] = "success"
        return result

    def mkdirs(self, remote_dir):
        if not self._sftp_con.exists(remote_dir):
            self.mkdirs(os.path.dirname(remote_dir))
        else:
            return
        self._sftp_con.mkdir(remote_dir)
        LOGGER.info(f"[Copy]: mkdir {remote_dir} successfully")

    def handle_tilde(self, remote_path):
        home_path = self._ssh_con.cmd("cd ~ && pwd")
        home_path_without_color = re.sub(COLOR_PATTERN, '', home_path).strip("\r")
        return remote_path.replace("~", home_path_without_color, 1)
