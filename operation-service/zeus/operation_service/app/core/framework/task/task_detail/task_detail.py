import json
import time
from abc import abstractmethod

from vulcanus.log.log import LOGGER
from zeus.operation_service.app.proxy.host import HostProxy
from zeus.operation_service.app.proxy.host_group import HostGroupProxy


class TaskDetail:
    def __init__(self, validated_data):
        self.task_name = validated_data.get('task_name')
        self.hosts = validated_data.get('host_ids')
        self.actions = validated_data.get('action_ids', list())
        self.create_time = round(time.time() * 1000)
        self.node_list = list()
        self.case_list = list()
        self.case_nodes = list()
        self.ext_props = dict()
        self.ext_props['only_push'] = validated_data.get('only_push', False)
        self.ext_props['remote_path'] = validated_data.get('remote_path', None)
        self.ext_props['scheduler_info'] = validated_data.get('scheduler_info', None)

    def get_task_detail(self):
        LOGGER.warning(f"start build task detail, [task_name]: {self.task_name}")
        self.parse()
        task_total = 0
        for case_node in self.case_nodes:
            task_total = task_total + len(case_node['node_indexes'])
        return json.dumps(self.__dict__, ensure_ascii=False), task_total

    def parse(self):
        # node->case->case_node 顺序不可变
        self.node_list = self.generate_node_list()
        self.case_list = self.generate_case_list()
        self.case_nodes = self.generate_case_nodes()
        LOGGER.warning(f"case_nodes: {self.case_nodes}")

    def generate_node_list(self):
        # LOGGER.warning(f"hosts group {str(self.hosts.items())}")
        node_list = list()
        # for host_id, host_groups in self.hosts.items():
        for host_id in self.hosts:
            db_host = HostProxy().get_host_by_id(host_id)
            host = dict()
            host['host_groups'] = list()
            host['host_id'] = host_id
            # for host_group_id in host_groups:
            #     host['host_groups'].append(HostGroupProxy().get_host_group_by_id(host_group_id).get("cluster_name"))
            host['host_name'] = db_host.get("host_name")
            host['ip'] = db_host.get("host_ip")
            node_list.append(host)
        return node_list

    @abstractmethod
    def generate_case_list(self) -> list:
        pass

    @abstractmethod
    def generate_case_nodes(self) -> list:
        pass
