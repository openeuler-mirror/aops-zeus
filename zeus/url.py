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
Description: url set
"""
from zeus.account_manager import view as account_view
from zeus.agent_manager import view as agent_view
from zeus.conf.constant import (
    ADD_GROUP,
    ADD_HOST,
    ADD_HOST_BATCH,
    ADD_USER,
    AGENT_METRIC_SET,
    AGENT_PLUGIN_INFO,
    AGENT_PLUGIN_SET,
    AUTH_REDIRECT_URL,
    BIND_AUTH_ACCOUNT,
    CHANGE_PASSWORD,
    COLLECT_CONFIG,
    DELETE_GROUP,
    DELETE_HOST,
    EXECUTE_CVE_FIX,
    EXECUTE_CVE_ROLLBACK,
    EXECUTE_CVE_SCAN,
    EXECUTE_HOTPATCH_REMOVE,
    EXECUTE_REPO_SET,
    GET_GROUP,
    GET_HOST_COUNT,
    GET_HOST_TEMPLATE_FILE,
    GITEE_AUTH_LOGIN,
    HOST_SCENE_GET,
    LOGOUT,
    QUERY_HOST,
    QUERY_HOST_DETAIL,
    QUERY_METRIC_DATA,
    QUERY_METRIC_LIST,
    QUERY_METRIC_NAMES,
    REFRESH_TOKEN,
    UPDATE_HOST,
    USER_LOGIN,
    SYNC_CONFIG,
    OBJECT_FILE_CONFIG,
    GET_HOST_STATUS,
    BATCH_SYNC_CONFIG,
    ADD_HOST_SYNC_STATUS,
    DELETE_HOST_SYNC_STATUS,
    GET_HOST_SYNC_STATUS,
    CONF_TRACE_MGMT,
    CONF_TRACE_DATA,
    CONF_TRACE_QUERY,
    CONF_TRACE_DELETE,
    DELETE_ALL_HOST_SYNC_STATUS
)
from zeus.config_manager import view as config_view
from zeus.host_manager import view as host_view
from zeus.metric_manager import view as metric_view
from zeus.vulnerability_manage import view as vulnerability_view
from zeus.conftrace_manage import view as conf_trace_view

URLS = []

SPECIFIC_URLS = {
    "ACCOUNT_URLS": [
        (account_view.Login, USER_LOGIN),
        (account_view.ChangePassword, CHANGE_PASSWORD),
        (account_view.AddUser, ADD_USER),
        (account_view.GiteeAuthLogin, GITEE_AUTH_LOGIN),
        (account_view.AuthRedirectUrl, AUTH_REDIRECT_URL),
        (account_view.BindAuthAccount, BIND_AUTH_ACCOUNT),
        (account_view.RefreshToken, REFRESH_TOKEN),
        (account_view.Logout, LOGOUT),
    ],
    "HOST_URLS": [
        (host_view.AddHost, ADD_HOST),
        (host_view.AddHostBatch, ADD_HOST_BATCH),
        (host_view.DeleteHost, DELETE_HOST),
        (host_view.UpdateHost, UPDATE_HOST),
        (host_view.GetHost, QUERY_HOST),
        (host_view.GetHostStatus, GET_HOST_STATUS),
        (host_view.GetHostInfo, QUERY_HOST_DETAIL),
        (host_view.GetHostCount, GET_HOST_COUNT),
        (host_view.GetHostTemplateFile, GET_HOST_TEMPLATE_FILE),
        (host_view.AddHostSyncStatus, ADD_HOST_SYNC_STATUS),
        (host_view.DeleteHostSyncStatus, DELETE_HOST_SYNC_STATUS),
        (host_view.DeleteAllHostSyncStatus, DELETE_ALL_HOST_SYNC_STATUS),
        (host_view.GetHostSyncStatus, GET_HOST_SYNC_STATUS)
    ],
    "HOST_GROUP_URLS": [
        (host_view.AddHostGroup, ADD_GROUP),
        (host_view.DeleteHostGroup, DELETE_GROUP),
        (host_view.GetHostGroup, GET_GROUP),
    ],
    "CONFIG_URLS": [
        (config_view.CollectConfig, COLLECT_CONFIG),
        (config_view.SyncConfig, SYNC_CONFIG),
        (config_view.ObjectFileConfig, OBJECT_FILE_CONFIG),
        (config_view.BatchSyncConfig, BATCH_SYNC_CONFIG)
    ],
    'AGENT_URLS': [
        (agent_view.AgentPluginInfo, AGENT_PLUGIN_INFO),
        (agent_view.SetAgentPluginStatus, AGENT_PLUGIN_SET),
        (agent_view.SetAgentMetricStatus, AGENT_METRIC_SET),
        (agent_view.GetHostScene, HOST_SCENE_GET),
    ],
    'CVE_URLS': [
        (vulnerability_view.ExecuteRepoSetTask, EXECUTE_REPO_SET),
        (vulnerability_view.ExecuteCveRollbackTask, EXECUTE_CVE_ROLLBACK),
        (vulnerability_view.ExecuteCveScanTask, EXECUTE_CVE_SCAN),
        (vulnerability_view.ExecuteCveFixTask, EXECUTE_CVE_FIX),
        (vulnerability_view.ExecuteHotpatchRemoveTask, EXECUTE_HOTPATCH_REMOVE),
    ],
    'METRIC': [
        (metric_view.QueryHostMetricNames, QUERY_METRIC_NAMES),
        (metric_view.QueryHostMetricData, QUERY_METRIC_DATA),
        (metric_view.QueryHostMetricList, QUERY_METRIC_LIST),
    ],
    'CONF_TRACE_URLS': [
        (conf_trace_view.ConfTraceMgmt, CONF_TRACE_MGMT),
        (conf_trace_view.ConfTraceData, CONF_TRACE_DATA),
        (conf_trace_view.ConfTraceQuery, CONF_TRACE_QUERY),
        (conf_trace_view.ConfTraceDataDelete, CONF_TRACE_DELETE),
    ]
}

for _, value in SPECIFIC_URLS.items():
    URLS.extend(value)
