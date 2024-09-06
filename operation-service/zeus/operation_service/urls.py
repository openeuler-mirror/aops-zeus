#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2021. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
from vulcanus.conf import constant

from zeus.operation_service.app.views.command import (
    CommandManageAPI,
    CommandInfoManageAPI
)

from zeus.operation_service.app.views.script import (
    ScriptManageAPI,
    ScriptInfoManageAPI,
    SupportOSInfoManageAPI
)

from zeus.operation_service.app.views.operate import (
    OperateManageAPI,
    OperateInfoManageAPI
)

from zeus.operation_service.app.views.task import (
    TaskManageAPI,
    TaskInfoManageAPI,
    TaskResultAPI
)


URLS = [
    (CommandManageAPI, "/operations/commands"),
    (CommandInfoManageAPI, "/operations/commands" + "/<string:command_id>"),
    (ScriptManageAPI, "/operations/scripts"),
    (ScriptInfoManageAPI, "/operations/scripts" + "/<string:script_id>"),
    (SupportOSInfoManageAPI, "/operations/scripts/support_info"),
    (OperateManageAPI, "/operations/operate"),
    (OperateInfoManageAPI, "/operations/operate" + "/<string:operate_id>"),
    (TaskManageAPI, "/operations/tasks"),
    (TaskInfoManageAPI, "/operations/tasks" + "/<string:task_id>"),
    (TaskResultAPI, "/operations/tasks/host_items_result")
    # (HostManageAPI, constant.HOSTS),
    # (HostInfoManageAPI, constant.HOSTS + "/<string:host_id>"),
    # (HostFilterAPI, constant.HOSTS_FILTER),
    # (BatchAddHostAPI, constant.BATCH_ADD_HOSTS),
    # (HostStatusAPI, constant.HOSTS_STATUS),
    # (SingleHostStatusAPI, constant.HOSTS_STATUS + "/<string:host_id>"),
    # (HostCountAPI, constant.HOSTS_COUNT),
    # (HostTemplateAPI, constant.HOSTS_TEMPLATE),
    # (HostGroupManageAPI, constant.HOSTS_GROUP),
    # (ClusterManageAPI, constant.CLUSTER_MANAGE),
    # (LocalClusterIdAPI, constant.LOCAL_CLUSTER_INFO),
    # (HostGroupInfoManageAPI, constant.HOSTS_GROUP + "/<string:group_id>"),
    # (ClusterGroupInfoCacheAPI, constant.CLUSTER_GROUP_CACHE),
    # (AllHostGroupMapAPI, constant.ALL_HOST_GROUP_MAP),
]
