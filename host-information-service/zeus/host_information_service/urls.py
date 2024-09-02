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

from zeus.host_information_service.app.views.cluster import (
    ClusterGroupInfoCacheAPI,
    ClusterManageAPI,
    LocalClusterIdAPI,
)
from zeus.host_information_service.app.views.host import (
    BatchAddHostAPI,
    HostCountAPI,
    HostFilterAPI,
    HostInfoManageAPI,
    HostManageAPI,
    HostStatusAPI,
    HostTemplateAPI,
    SingleHostStatusAPI,
    HostIpFilterAPI,
)
from zeus.host_information_service.app.views.host_group import (
    AllHostGroupMapAPI,
    HostGroupInfoManageAPI,
    HostGroupManageAPI,
)

URLS = [
    (HostManageAPI, constant.HOSTS),
    (HostInfoManageAPI, constant.HOSTS + "/<string:host_id>"),
    (HostFilterAPI, constant.HOSTS_FILTER),
    (BatchAddHostAPI, constant.BATCH_ADD_HOSTS),
    (HostStatusAPI, constant.HOSTS_STATUS),
    (SingleHostStatusAPI, constant.HOSTS_STATUS + "/<string:host_id>"),
    (HostCountAPI, constant.HOSTS_COUNT),
    (HostTemplateAPI, constant.HOSTS_TEMPLATE),
    (HostGroupManageAPI, constant.HOSTS_GROUP),
    (ClusterManageAPI, constant.CLUSTER_MANAGE),
    (LocalClusterIdAPI, constant.LOCAL_CLUSTER_INFO),
    (HostGroupInfoManageAPI, constant.HOSTS_GROUP + "/<string:group_id>"),
    (ClusterGroupInfoCacheAPI, constant.CLUSTER_GROUP_CACHE),
    (AllHostGroupMapAPI, constant.ALL_HOST_GROUP_MAP),
    (HostIpFilterAPI, constant.HOSTS_IP_FILTER),
]
