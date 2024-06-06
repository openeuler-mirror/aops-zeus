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
    AccountsAllAPI,
    AddUser,
    AuthRedirectUrl,
    BindAuthAccount,
    BindManagerUser,
    CacheClusterPermissionAPI,
    ChangePassword,
    ClusterKeyAPI,
    ClusterSync,
    GiteeAuthLogin,
    Login,
    Logout,
    ManagedClusterAPI,
    RefreshToken,
    RegisterClusterAPI,
    UnbindManagerUserAPI,
)
from zeus.user_access_service.app.views.permission import AccountPageAPI, PermissionAccountBindAPI, PermissionAPI

URLS = [
    (Login, constant.USER_LOGIN),
    (ChangePassword, constant.CHANGE_PASSWORD),
    (AddUser, constant.ADD_USER),
    (GiteeAuthLogin, constant.GITEE_AUTH_LOGIN),
    (AuthRedirectUrl, constant.AUTH_REDIRECT_URL),
    (BindAuthAccount, constant.BIND_AUTH_ACCOUNT),
    (RefreshToken, constant.REFRESH_TOKEN),
    (Logout, constant.LOGOUT),
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
]
