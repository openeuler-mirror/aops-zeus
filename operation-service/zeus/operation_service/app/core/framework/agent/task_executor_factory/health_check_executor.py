import glob
import logging
import os
import shutil
import stat
import subprocess
import xml.etree.ElementTree as eT
from multiprocessing.pool import ThreadPool

from .task_executor import TaskExecutor

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(filename='/opt/.agent/agent.log', level=logging.DEBUG, format=LOG_FORMAT)
LOG = logging.getLogger()


class HealthCheckExecutor(TaskExecutor):

    def __init__(self, config_json):
        super(HealthCheckExecutor, self).__init__(config_json)
        self._asset_folder_name = "healthcheck"

    def prepare_env(self):
        if os.path.exists("/opt/apmtool/sudoexecute"):
            return
        if not os.path.exists("/opt/apmtool"):
            os.makedirs("/opt/apmtool", exist_ok=True)
        shutil.copyfile(os.path.join(self.agent_path, "sudoexecute.sh"), "/opt/apmtool/sudoexecute")
        shutil.chown("/opt/apmtool/sudoexecute", user=0, group=0)
        os.chmod("/opt/apmtool/sudoexecute", mode=stat.S_IREAD | stat.S_IEXEC)

    def run_single_item(self, task: dict):
        self.env["INSPECTION_ASSET_PATH"] = task["items_path"]
        super().run_single_item(task=task)

    def execute(self, asset_item):
        check_task = list()
        asset_name = asset_item["asset_name"]
        asset_item_list = self.get_check_items(asset_item)
        items_path = glob.glob(os.path.join(self.agent_path, "assets", asset_name, "*Items"))[0]
        for path, dir_list, file_list in os.walk(os.path.join(items_path, self._asset_folder_name, "Items")):
            for f in file_list:
                item_tree = eT.parse(os.path.join(path, f))
                item_root = item_tree.getroot()
                check_id = item_root[0].attrib['value']
                LOG.info("run check item: {}".format(check_id))
                if check_id in asset_item_list:
                    # run .py
                    py_file = self.parse_py_path(item_root)
                    # 恢复脚本不存在，则跳过检查
                    if not py_file:
                        continue
                    absolute_py_file = os.path.join(items_path, *py_file.split("/")[1:])
                    # build command
                    python_path = "python3"
                    command = list()
                    command.append(python_path)
                    command.extend(absolute_py_file.split(" "))
                    recoverable = True if item_root.find('Recovery') else False
                    # execute
                    # 超时控制
                    check_task.append({"items_path": items_path, "command": command,
                                       "check_id": check_id, "recoverable": recoverable})

        pool = ThreadPool(5)

        for task in check_task:
            pool.apply_async(self.run_single_item, args=(task,))
        pool.close()
        pool.join()

    def parse_py_path(self, item_root):
        return item_root[1].attrib['name_value']

    def get_check_items(self, asset_item):
        return asset_item["check_items"]
