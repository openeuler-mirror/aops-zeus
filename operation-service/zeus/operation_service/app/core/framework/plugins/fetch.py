import os
import re
import traceback
from pathlib import Path
from zeus.operation_service.app.constant import BASE_DIR
from zeus.operation_service.app.core.framework.common.result_code import PluginResultCode
from zeus.operation_service.app.core.framework.plugins.base_plugin import BasePlugin
from vulcanus.log.log import LOGGER


class Fetch(BasePlugin):
    """
    功能：从远端指定路径获取文件
    参数：
        src: 远端路径
        dest: 本地保存路径
        is_overwrite (optional): 是否覆盖本地文件，默认不覆盖
        filename (optional): 本地文件名，不选时默认为 远端IP_远端文件名
    """
    def run(self):
        result = dict()
        remote_src = self._task_vars["src"]
        local_dest_path = self._task_vars["dest"]
        is_overwrite = self._task_vars.get("is_overwrite", False)
        filename = self._task_vars.get("filename", "")
        local_dest_path = Path(os.path.dirname(BASE_DIR)).joinpath(local_dest_path)
        LOGGER.info("[Fetch]: From %s to %s", remote_src, local_dest_path)
        if not self._sftp_con.exists(remote_src):
            result["error_code"] = PluginResultCode.ERROR
            result["error_msg"] = "no such file or dir exist"
            LOGGER.warning("no such file or dir exist")
            return result

        if not self._sftp_con.is_file(remote_src):
            result["error_code"] = PluginResultCode.ERROR
            result["error_msg"] = "remote path is a dir"
            LOGGER.warning("remote path is a dir")
            return result

        if not os.path.exists(local_dest_path):
            os.makedirs(local_dest_path)

        if filename:
            local_dest_path = os.path.join(local_dest_path, filename)
        else:
            local_dest_path = os.path.join(local_dest_path, "_".join([self._host.get("ip"), os.path.basename(remote_src)]))

        if not is_overwrite:
            i = 1
            while os.path.exists(local_dest_path):
                if i == 1:
                    local_dest_path += "(1)"
                local_dest_path = re.sub(r'\(\d+\)$', f'({i})', local_dest_path)
                i += 1
        try:
            self._sftp_con.GetBinFile(remote_src, local_dest_path)
        except Exception as e:
            LOGGER.exception("Catch an exception: %s", traceback.format_exc())
            result["error_code"] = PluginResultCode.ERROR
            result["error_msg"] = "Fetch file failed"
            return result
        #  chmod chown
        LOGGER.info("fetch success")

        result["error_code"] = PluginResultCode.SUCCESS
        result["error_msg"] = "success"
        return result
