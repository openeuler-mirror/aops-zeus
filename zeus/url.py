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
from vulcanus.conf.constant import (
    ADD_GROUP,
    ADD_HOST,
    ADD_USER,
    AGENT_METRIC_SET,
    AGENT_PLUGIN_INFO,
    AGENT_PLUGIN_SET,
    CHANGE_PASSWORD,
    COLLECT_CONFIG,
    DELETE_GROUP,
    DELETE_HOST,
    EXECUTE_CVE_FIX,
    EXECUTE_CVE_SCAN,
    EXECUTE_REPO_SET,
    GET_GROUP,
    GET_HOST_COUNT,
    HOST_SCENE_GET,
    QUERY_HOST,
    QUERY_HOST_DETAIL,
    REGISTER_HOST,
    USER_CERTIFICATE,
    CHANGE_PASSWORD,
    ADD_USER,
    AGENT_PLUGIN_INFO,
    AGENT_PLUGIN_SET,
    AGENT_METRIC_SET,
    HOST_SCENE_GET,
    EXECUTE_REPO_SET,
    GITEE_AUTH_LOGIN,
    AUTH_REDIRECT_URL,
    BIND_AUTH_ACCOUNT
)

from zeus.account_manager import view as account_view
from zeus.agent_manager import view as agent_view
from zeus.config_manager import view as config_view
from zeus.host_manager import view as host_view
from zeus.vulnerability_manage import view as vulnerability_view

URLS = []

SPECIFIC_URLS = {
    "ACCOUNT_URLS": [
        (account_view.Login, USER_LOGIN),
        (account_view.Certificate, USER_CERTIFICATE),
        (account_view.ChangePassword, CHANGE_PASSWORD),
        (account_view.AddUser, ADD_USER),
        (account_view.GiteeAuthLogin, GITEE_AUTH_LOGIN),
        (account_view.AuthRedirectUrl, AUTH_REDIRECT_URL),
        (account_view.BindAuthAccount, BIND_AUTH_ACCOUNT)
    ],
    "HOST_URLS": [
        (host_view.RegisterHost, REGISTER_HOST),
        (host_view.AddHost, ADD_HOST),
        (host_view.DeleteHost, DELETE_HOST),
        (host_view.GetHost, QUERY_HOST),
        (host_view.GetHostInfo, QUERY_HOST_DETAIL),
        (host_view.GetHostCount, GET_HOST_COUNT)
    ],
    "HOST_GROUP_URLS": [
        (host_view.AddHostGroup, ADD_GROUP),
        (host_view.DeleteHostGroup, DELETE_GROUP),
        (host_view.GetHostGroup, GET_GROUP)
    ],
    "CONFIG_URLS": [
        (config_view.CollectConfig, COLLECT_CONFIG)
    ],
    'AGENT_URLS': [
        (agent_view.AgentPluginInfo, AGENT_PLUGIN_INFO),
        (agent_view.SetAgentPluginStatus, AGENT_PLUGIN_SET),
        (agent_view.SetAgentMetricStatus, AGENT_METRIC_SET),
        (agent_view.GetHostScene, HOST_SCENE_GET)
    ],
    'CVE_URLS': [
        (vulnerability_view.ExecuteRepoSetTask, EXECUTE_REPO_SET),
        (vulnerability_view.ExecuteCveScanTask, EXECUTE_CVE_SCAN),
        (vulnerability_view.ExecuteCveFixTask, EXECUTE_CVE_FIX)
    ]

}

for _, value in SPECIFIC_URLS.items():
    URLS.extend(value)
