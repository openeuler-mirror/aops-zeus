from .health_check_executor import HealthCheckExecutor
import socket
import json


class SecurityManageExecutor(HealthCheckExecutor):

    def __init__(self, config_json):
        super().__init__(config_json)
        self._asset_folder_name = "securitymanage"
        self.recover = config_json.get('recover', False)
        self.local_ip = socket.gethostbyname(socket.gethostname())
        if self.recover:
            self.error_items = config_json['hosts_error'][self.local_ip]

    def parse_py_path(self, item_root):
        if self.recover:
            return item_root.find('Recovery').find('name').attrib['name_value'] if item_root.find('Recovery') else None
        return item_root.find('name').attrib['name_value']

    def run_single_item(self, task: dict):
        super().run_single_item(task)
        last_check_res = json.loads(self.RETURN_DATA[-1]['check_res'])
        if task["recoverable"] and self.recover == False and last_check_res[0]["ErrLevel"] not in [0, 4]:
            # 定义 ErrLevel 5 为待加固
            last_check_res[0]["ErrLevel"] = 5
            self.RETURN_DATA[-1]['check_res'] = json.dumps(last_check_res)
        return

    def get_check_items(self, asset_item):
        if self.recover:
            return self.error_items
        return asset_item["check_items"]
