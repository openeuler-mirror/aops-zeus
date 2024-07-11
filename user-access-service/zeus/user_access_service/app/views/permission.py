#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2022. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
from vulcanus.conf.constant import UserRoleType
from vulcanus.database.proxy import RedisProxy
from vulcanus.restful.response import BaseResponse, state

from zeus.user_access_service.app.proxy.permission import PermissionProxy
from zeus.user_access_service.app.serialize.permission import (
    BindPermission_RequestSchema,
    DeletePermission_RequestSchema,
    GetAccountPage_RequestSchema,
    GetPermission_RequestSchema,
    SetPermission_RequestSchema,
)


class AccountPageAPI(BaseResponse):
    """
    Interface for get account page
    """

    @BaseResponse.handle(schema=GetAccountPage_RequestSchema, proxy=PermissionProxy)
    def get(self, callback: PermissionProxy, **params):
        status_code, result = callback.get_accounts(params)
        return self.response(code=status_code, data=result)


class PermissionAPI(BaseResponse):
    """
    Interface for permission
    """

    @BaseResponse.handle(proxy=PermissionProxy, schema=GetPermission_RequestSchema)
    def get(self, callback: PermissionProxy, **params):
        status_code, permissions = callback.get_permissions(
            username=params["username"], cluster_id=params["cluster_id"]
        )
        return self.response(code=status_code, data=permissions)

    @BaseResponse.handle(proxy=PermissionProxy, schema=SetPermission_RequestSchema)
    def post(self, callback: PermissionProxy, **params):
        status_code = callback.set_permissions(
            username=params["username"],
            permissions=params["permission"],
        )
        return self.response(code=status_code)

    @BaseResponse.handle(proxy=PermissionProxy, schema=DeletePermission_RequestSchema)
    def delete(self, callback: PermissionProxy, **params):
        """
        delete permission by username and cluster id
        """
        status_code = callback.delete_permissions(username=params["manager_username"], cluster_id=params["cluster_id"])
        return self.response(code=status_code)


class PermissionAccountBindAPI(BaseResponse):
    """
    Interface for permission account bind
    """

    @BaseResponse.handle(proxy=PermissionProxy, schema=BindPermission_RequestSchema)
    def post(self, callback: PermissionProxy, **params):
        status_code, username = callback.bind_permissions(params)
        if status_code == state.SUCCEED:
            RedisProxy.redis_connect.set(username + "_role", UserRoleType.NORMAL)

        return self.response(code=status_code, data=username)
