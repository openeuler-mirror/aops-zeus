from zeus.operation_service.app.proxy.operate import OperateProxy
from zeus.operation_service.app.proxy.script import ScriptProxy
from zeus.operation_service.app.proxy.host import HostProxy
from zeus.operation_service.app.core.framework.task.task_detail.task_detail import TaskDetail


class BatchScriptExecutionDetail(TaskDetail):
    def generate_case_list(self):
        case_list = list()
        script_info = dict()
        script_info["macro_command_name"] = f"{self.task_name}_{'_'.join(map(str, self.actions))}"
        script_brief_info = list()

        host_types = set()
        for host in self.node_list:
            host_types.add((host['arch'], host['os_name']))

        # 一次只能跑一次脚本 len(self.actions)=1
        for operate_id in self.actions:
            scripts = ScriptProxy().get_script_by_operate_id(operate_id=operate_id)
            host_script_map = dict()
            for script in scripts:
                host_script_map[(script.arch,script.os_name)] = script
            for host_type in host_types:
                if host_type in host_script_map.keys():
                    script = host_script_map[host_type]
                    single_script_info = dict()
                    single_script_info['name'] = f"{script.script_name}_{script.os_name}_{script.arch}"
                    single_script_info['command'] = script.command
                    single_script_info['host_type'] = f"{script.os_name}_{script.arch}"
                    single_script_info['script_id'] = script.script_id
                    # _, operate = OperateProxy().get_operate_info(operate_id=operate_id)
                    # single_operate_info['name'] = operate.operate_name
                    # single_operate_info['id'] = operate_id
                    
                    # single_operate_info['command'] = operate['command']
                    #TODO: path需要适配
                    # single_operate_info['path'] = operate.path
                    script_brief_info.append(single_script_info)
        script_info["scripts"] = script_brief_info
        case_list.append(script_info)
        return case_list

    def generate_case_nodes(self):
        """
        自定义 case_nodes: case_index:{"script_idx": [node_idx,...]}
        "case_nodes": [
            {
                "case_indexes": {
                    "0": [0, 1]
                },
                "node_indexes": [
                    0,
                    1
                ]
            }
        ]
        """
        case_nodes = list()
        case_node = dict()
        case_node['case_indexes'] = dict()
        case_node['node_indexes'] = list(range(len(self.node_list)))

        # 一次只跑一个脚本 len(self.case_list) = 1
        for idx, script in enumerate(self.case_list[0]['scripts']):
            target_host_type = script['host_type']
            target_host = list()
            for host_idx, host in enumerate(self.node_list):
                if target_host_type == f"{host['os_name']}_{host['arch']}":
                    target_host.append(host_idx)
            case_node['case_indexes'][str(idx)] = target_host

        case_nodes.append(case_node)

        return case_nodes
    
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
            host['host'] = db_host.get("host_name")
            host['ip'] = db_host.get("host_ip")
            host['arch'] = db_host.get('arch')
            host['os_name'] = db_host.get('os_name')
            node_list.append(host)
        return node_list
