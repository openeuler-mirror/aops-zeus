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
from zeus.user_access_service.app.views.account import (
    AccessTokenAPI,
    AccountsAllAPI,
    BindManagerUser,
    CacheClusterPermissionAPI,
    ChangePassword,
    ClusterKeyAPI,
    ClusterSync,
    Logout,
    ManagedClusterAPI,
    Oauth2AuthorizeAddUser,
    Oauth2AuthorizeLogin,
    Oauth2AuthorizeLogout,
    Oauth2AuthorizeUri,
    RefreshToken,
    RegisterClusterAPI,
    UnbindManagerUserAPI,
)
from zeus.user_access_service.app.views.permission import AccountPageAPI, PermissionAccountBindAPI, PermissionAPI

URLS = [
    (Oauth2AuthorizeUri, constant.OAUTH2_AUTHORIZE_URI),
    (Logout, constant.LOGOUT),
    (Oauth2AuthorizeLogin, constant.USER_LOGIN),
    (ChangePassword, constant.CHANGE_PASSWORD),
    (Oauth2AuthorizeAddUser, constant.ADD_USER),
    (RefreshToken, constant.REFRESH_TOKEN),
    (Oauth2AuthorizeLogout, constant.LOGOUT_REDIRECT),
    (BindManagerUser, constant.CLUSTER_USER_BIND),
    (RegisterClusterAPI, constant.REGISTER_CLUSTER),
    (CacheClusterPermissionAPI, constant.CLUSTER_PERMISSION_CACHE),
    (ManagedClusterAPI, constant.MANAGED_CLUSTER),
    (ClusterKeyAPI, constant.CLUSTER_PRIVATE_KEY),
    (UnbindManagerUserAPI, constant.CLUSTER_MANAGED_CANCEL),
    (AccountPageAPI, constant.USERS),
    (PermissionAPI, constant.PERMISSIONS),
    (PermissionAccountBindAPI, constant.PERMISSION_BIND),
    (AccountsAllAPI, constant.USERS_ALL),
    (ClusterSync, constant.CLUSTER_SYNC),
    (AccessTokenAPI, constant.ACCESS_TOKEN),
]
