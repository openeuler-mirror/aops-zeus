import glob
import logging
import os
import shutil
import subprocess
import xml.etree.ElementTree as eT
from multiprocessing.pool import ThreadPool

from .task_executor import TaskExecutor

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(filename='/opt/.agent/agent.log', level=logging.DEBUG, format=LOG_FORMAT)
LOG = logging.getLogger()


class DataCollectExecutor(TaskExecutor):
    def __init__(self, config_json):
        super(DataCollectExecutor, self).__init__(config_json)
        self.task_name = config_json.get('task_name')

    def run_single_item(self, task: dict):
        self.env['UPLOAD_DIR'] = os.path.join(self.agent_path, self.task_id,
                                              task.get('asset_name'), task.get("item_name"))
        super().run_single_item(task=task)

    def execute(self, asset_item):
        check_task = list()
        asset_name = asset_item["asset_name"]
        asset_item_list = asset_item["check_items"]
        items_path = glob.glob(os.path.join(self.agent_path, "assets", asset_name, "*Items"))[0]
        for path, dir_list, file_list in os.walk(os.path.join(items_path, "datacollection", "Items")):
            for file in file_list:
                item_tree = eT.parse(os.path.join(path, file))
                item_id = item_tree.getroot().find('ItemID').get('value')
                if item_id in asset_item_list:
                    script_dir = item_tree.getroot().find('CollectDir').get('dir')
                    item_name = item_tree.getroot().find('name').get('name_en')

                    # 去除空格
                    item_name = item_name.replace(' ', '')
                    data_collect_tools_path = os.path.join(self.agent_path, "data_collect_tools")
                    execute_dir = os.path.join(items_path, "datacollection", "Scripts", script_dir)
                    self.copy_dirs(data_collect_tools_path, execute_dir)
                    collect_shell = os.path.join(execute_dir, "collect.sh")
                    command = ["sh", collect_shell]
                    check_task.append(
                        {"command": command, "item_name": item_name, "check_id": item_id, "asset_name": asset_name})
        pool = ThreadPool(1)
        for task in check_task:
            pool.apply_async(self.run_single_item, args=(task,))
        pool.close()
        pool.join()

    def post_execute(self):
        zip_file_path = os.path.join(self.agent_path, self.task_name)
        zip_upload_dir = os.path.join(self.agent_path, self.task_id)
        shutil.make_archive(zip_file_path, 'zip', zip_upload_dir)
