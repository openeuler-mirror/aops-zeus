import json


class TaskDetailParser:
    def __init__(self, task_detail_json):
        self.task_detail = json.loads(task_detail_json)

    def get_task_hosts(self):
        return self.task_detail["node_list"]

    def get_task_hosts_id(self):
        res = list()
        for item in self.task_detail["node_list"]:
            res.append(item["host_id"])
        return res

    def get_task_assets(self):
        return self.task_detail["case_list"]

    def get_task_assets_id(self):
        res = list()
        for item in self.task_detail["case_list"]:
            res.append(item["asset_id"])
        return res

    def get_task_case_nodes(self):
        return self.task_detail["case_nodes"]

    def get_task_case_list(self):
        return self.task_detail["case_list"]
    
    def get_task_ext_props(self):
        return self.task_detail['ext_props']
