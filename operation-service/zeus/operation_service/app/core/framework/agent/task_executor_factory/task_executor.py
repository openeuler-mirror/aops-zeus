import json
import logging
import os
import shutil
import socket
import subprocess
from abc import ABC, abstractmethod
from urllib import request

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(filename='/opt/.agent/agent.log', level=logging.DEBUG, format=LOG_FORMAT)
LOG = logging.getLogger()


class TaskExecutor(ABC):
    def __init__(self, config_json):
        self.task_id = config_json['task_id']
        self.manage_ip = config_json['manage_ip']
        self.manage_port = config_json['manage_port']
        self.assets = config_json["asset"]
        self.task_type = config_json['task_type']
        self.agent_path = config_json['agent_path']
        self.RETURN_DATA = list()
        self.env = dict(os.environ)

    def get_host_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self.manage_ip, 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip

    def prepare_env(self):
        pass

    @abstractmethod
    def execute(self, asset_item):
        pass

    def post_execute(self):
        pass

    def run_single_item(self, task: dict):
        try:
            info = subprocess.check_output(task["command"], shell=False,
                                           env=self.env).decode("utf-8").strip()
            self.RETURN_DATA.append({
                'item_path': task["check_id"],
                'check_res': info
            })
        except Exception:
            self.RETURN_DATA.append({
                'item_path': task["check_id"],
                'check_res': "[{\"ErrInfo\": \"Execution failed\","
                             "\"ErrLevel\": 4,\"Suggest\": \"Contact Huawei technical support.\"}]"
            })

    def start(self):
        self.prepare_env()
        for asset_item in self.assets:
            asset_id = asset_item["asset_id"]
            self.execute(asset_item)
            # report progress
            url = 'http://{}:{}/rest/task/v1/tasks/{}'.format(self.manage_ip, self.manage_port, self.task_id)
            params = {
                'assetId': asset_id,
                'data': self.RETURN_DATA,
                'host': self.get_host_ip(),
                'task_id': self.task_id
            }
            headers = {'Accept-Charset': 'utf-8', 'Content-Type': 'application/json'}
            req = request.Request(url=url, headers=headers, data=json.dumps(params).encode('utf-8'), method="PATCH")
            try:
                response = request.urlopen(req)
                LOG.info(f"Response: {response.read().decode('utf-8')}")
            except Exception as e:
                LOG.error(f"get exception: {e}")

            self.RETURN_DATA.clear()
        self.post_execute()

    def copy_dirs(self, src, dest):
        if not os.path.exists(dest):
            shutil.copytree(src, dest)
            return
        for file in os.listdir(src):
            file_path = os.path.join(src, file)
            if os.path.isdir(file_path):
                dest_dir_path = os.path.join(dest, file)
                if not os.path.exists(dest_dir_path):
                    os.makedirs(dest_dir_path)
                self.copy_dirs(file_path, dest_dir_path)
            else:
                shutil.copy(file_path, dest)
