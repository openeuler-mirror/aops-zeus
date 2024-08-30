import json
import os
from abc import ABC
from vulcanus.log.log import LOGGER
from zeus.operation_service.app.constant import TaskOperationResultCode
from zeus.operation_service.database import Task
from zeus.operation_service.app.core.task_exception import TaskException
from zeus.operation_service.app.core.framework.common.constant import TaskType


class TaskResultDetail(ABC):
    def __init__(self, task: Task):
        self.task = task
        self.task_detail = json.loads(task.task_detail)
        self.node_list = self.task_detail['node_list']
        self.case_list = self.task_detail['case_list']
        self.case_nodes = self.task_detail['case_nodes']

    def update_progress(self, request):
        pass

    def get_items_detail(self, request):
        pass

    def generate_hosts_assets(self):
        '''
        生成主机组、主机对应资产包
        {
          "host_groups": {
            "Openeuler-group1": [
              "hostnameA"
            ]
          },
          "host_assets": {
            "hostnameA": {
              "node_index": 0,
              "assets": {
                "0": {
                  "zh": "巡检包0",
                  "en": "healthcheck0",
                  "verson": "1.0.0"
                },
              }
            }
          }
        }
        '''
        hosts_assets = dict()
        hosts_assets['host_groups'] = dict()
        hosts_assets['host_assets'] = dict()
        LOGGER.warning(f"case_nodes: {self.case_nodes}")
        for case_node in self.case_nodes:
            for node_index in case_node['node_indexes']:
                self.generate_host_group(hosts_assets['host_groups'], self.node_list[node_index])
                self.generate_host_assets(hosts_assets['host_assets'], node_index, case_node)
        LOGGER.warning(f"hosts_assets: {hosts_assets}")
        return hosts_assets

    @staticmethod
    def generate_host_group(host_groups, host_detail):
        """
        生成 host_groups
          "host_groups": {
            "groupA": [
                "host1",
                "host2"
            ],
            "groupB": [
                "host1",
                "host3"
            ]
        }
        """
        host = host_detail['host']

        # 如果主机没有主机组，则默认在default主机组
        if len(host_detail['host_groups']) == 0:
            if "default" not in host_groups.keys():
                host_groups["default"] = list()
            host_groups["default"].append(host)
            return
        for host_group in host_detail['host_groups']:
            if host_group not in host_groups.keys():
                host_groups[host_group] = list()
            host_groups[host_group].append(host)

    def generate_host_assets(self, host_assets, node_index, case_node):
        host_name = self.node_list[node_index]['host']
        host_assets[host_name] = dict()
        host_assets[host_name]['node_index'] = node_index
        if self.task.task_type == TaskType.DATA_COLLECT or self.task.task_type == TaskType.HEALTH_CHECK or self.task.task_type == TaskType.SECURITY_MANAGE:
            host_assets[host_name]['assets'] = dict()
            for asset_id, _ in case_node['case_indexes'].items():
                host_assets[host_name]['assets'][asset_id] = self.case_list[int(asset_id)]['asset_name']
                host_assets[host_name]['assets'][asset_id]["version"] = self.case_list[int(asset_id)].get(
                    'asset_version')
