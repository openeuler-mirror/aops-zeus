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
"""
Time:
Author:
Description: manager constant
"""
import os
from vulcanus.conf.constant import BASE_CONFIG_PATH

# path of manager configuration
MANAGER_CONFIG_PATH = os.path.join(BASE_CONFIG_PATH, 'zeus.ini')

# ceres
CERES_PLUGIN_START = "/v1/ceres/plugin/start"
CERES_PLUGIN_STOP = "/v1/ceres/plugin/stop"
CERES_COLLECT_ITEMS_CHANGE = "/v1/ceres/collect/items/change"
CERES_APPLICATION_INFO = "/v1/ceres/application/info"
CERES_COLLECT_FILE = '/v1/ceres/file/collect'
CERES_HOST_INFO = '/v1/ceres/host/info'
CERES_PLUGIN_INFO = '/v1/ceres/plugin/info'
CERES_CVE_REPO_SET = '/v1/ceres/cve/repo/set'
CERES_CVE_SCAN = '/v1/ceres/cve/scan'
CERES_CVE_FIX = '/v1/ceres/cve/fix'

# check
CHECK_IDENTIFY_SCENE = "/check/scene/identify"
CHECK_WORKFLOW_HOST_EXIST = '/check/workflow/host/exist'

# host template file content
HOST_TEMPLATE_FILE_CONTENT = """host_ip,ssh_port,ssh_user,password,host_name,host_group_name,management
test_ip_1,22,root,password,test_host,test_host_group,False
test_ip_2,22,root,password,test_host,test_host_group,False
"""


# cve task status
class CveTaskStatus:
    SUCCEED = 'succeed'
    FAIL = 'fail'
    UNKNOWN = 'unknown'


class HostStatus:
    ONLINE = 0
    OFFLINE = 1
    UNESTABLISHED = 2
