#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
from zeus.operation_service.app.proxy.command import CommandProxy
from zeus.operation_service.app.core.framework.task.task_detail.task_detail import TaskDetail


class BatchExecutionDetail(TaskDetail):
    def generate_case_list(self):
        case_list = list()
        commands_info = dict()
        commands_info["macro_command_name"] = f"{self.task_name}_{'_'.join(map(str, self.actions))}"
        commands_brief_info = list()
        for command_id in self.actions:
            single_command_info = dict()
            db_proxy = CommandProxy()
            db_proxy.connect()
            _status, command = db_proxy.get_command_info(command_id=command_id)
            if not command:
                continue
            single_command_info['name'] = command.command_name
            single_command_info['id'] = command_id
            single_command_info['content'] = command.content
            single_command_info['lang'] = command.lang
            commands_brief_info.append(single_command_info)
        commands_info["commands"] = commands_brief_info
        case_list.append(commands_info)
        return case_list

    def generate_case_nodes(self):
        case_nodes = list()
        case_node = dict()
        case_node['case_indexes'] = dict()
        case_node['node_indexes'] = list(range(len(self.node_list)))
        for i in range(len(self.case_list)):
            asset_items_len = len(self.case_list[i]['commands'])
            case_node['case_indexes'][str(i)] = list(range(asset_items_len))
        case_nodes.append(case_node)
        return case_nodes
    