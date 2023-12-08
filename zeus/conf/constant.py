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
CERES_PLUGIN_START = "aops-ceres plugin --start %s"
CERES_PLUGIN_STOP = "aops-ceres plugin --stop %s"
CERES_COLLECT_ITEMS_CHANGE = "aops-ceres plugin --change-collect-items '%s'"
CERES_PLUGIN_INFO = "aops-ceres plugin --info"
CERES_APPLICATION_INFO = "aops-ceres collect --application"
CERES_COLLECT_FILE = "aops-ceres collect --file '%s'"
CERES_HOST_INFO = "aops-ceres collect --host '%s'"
CERES_CVE_REPO_SET = "aops-ceres apollo --set-repo '%s'"
CERES_CVE_SCAN = "aops-ceres apollo --scan '%s'"
CERES_CVE_FIX = "aops-ceres apollo --fix '%s'"
CERES_HOTPATCH_REMOVE = "aops-ceres apollo --remove-hotpatch '%s'"
CERES_SYNC_CONF = "aops-ceres sync --conf '%s'"
CERES_OBJECT_FILE_CONF = "aops-ceres ragdoll --list '%s'"

# zeus route
ADD_HOST = "/manage/host/add"
ADD_HOST_BATCH = "/manage/host/add/batch"
GET_HOST_TEMPLATE_FILE = "/manage/host/file/template"
DELETE_HOST = "/manage/host/delete"
QUERY_HOST = "/manage/host/get"
GET_HOST_COUNT = "/manage/host/count"
AUTH_REDIRECT_URL = "/manage/account/authredirecturl"
BIND_AUTH_ACCOUNT = "/manage/account/bindaccount"
REFRESH_TOKEN = "/manage/account/refreshtoken"
UPDATE_HOST = "/manage/host/update"

QUERY_HOST_DETAIL = "/manage/host/info/query"
HOST_SCENE_GET = '/manage/host/scene/get'

ADD_GROUP = "/manage/host/group/add"
DELETE_GROUP = "/manage/host/group/delete"
GET_GROUP = "/manage/host/group/get"

COLLECT_CONFIG = '/manage/config/collect'
SYNC_CONFIG = '/manage/config/sync'
OBJECT_FILE_CONFIG = '/manage/config/objectfile'

USER_LOGIN = "/manage/account/login"
LOGOUT = "/manage/account/logout"
CHANGE_PASSWORD = '/manage/account/change'
ADD_USER = '/manage/account/add'
GITEE_AUTH_LOGIN = "/manage/account/gitee/login"

AGENT_PLUGIN_INFO = '/manage/agent/plugin/info'
AGENT_PLUGIN_SET = '/manage/agent/plugin/set'
AGENT_METRIC_SET = '/manage/agent/metric/set'

EXECUTE_REPO_SET = '/manage/vulnerability/repo/set'
EXECUTE_CVE_FIX = '/manage/vulnerability/cve/fix'
EXECUTE_CVE_SCAN = '/manage/vulnerability/cve/scan'
EXECUTE_CVE_ROLLBACK = "/manage/vulnerability/cve/rollback"
EXECUTE_HOTPATCH_REMOVE = "/manage/vulnerability/cve/hotpatch-remove"

# metric config
QUERY_METRIC_NAMES = '/manage/host/metric/names'
QUERY_METRIC_DATA = '/manage/host/metric/data'
QUERY_METRIC_LIST = '/manage/host/metric/list'

# auth login
GITEE_OAUTH = "https://gitee.com/oauth/authorize"
GITEE_TOKEN = "https://gitee.com/oauth/token?grant_type=authorization_code"
GITEE_USERINFO = "https://gitee.com/api/v5/user"

# apollo
VUL_TASK_CVE_SCAN_NOTICE = "/vulnerability/task/callback/cve/scan/notice"

# check
CHECK_IDENTIFY_SCENE = "/check/scene/identify"
CHECK_WORKFLOW_HOST_EXIST = '/check/workflow/host/exist'

# host template file content
HOST_TEMPLATE_FILE_CONTENT = """host_ip,ssh_port,ssh_user,password,ssh_pkey,host_name,host_group_name,management
127.0.0.1,22,root,password,private key,test_host,test_host_group,FALSE
127.0.0.1,23,root,password,private key,test_host,test_host_group,FALSE
,,,,,,,
"提示:",,,,,,,
"1. 除登录密码与SSH登录秘钥外,其余信息都应提供有效值",,,,,,,
"2. 登录密码与SSH登录秘钥可选择一种填入,当两者都提供时,以SSH登录秘钥为准",,,,,,,
"3. 添加的主机信息不应存在重复信息(主机名称重复或者主机IP+端口重复)",,,,,,,
"4. 上传本文件前,请删除此部分提示内容",,,,,,,
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
