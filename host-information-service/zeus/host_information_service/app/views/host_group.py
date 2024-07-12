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
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse

from zeus.host_information_service.app import cache
from zeus.host_information_service.app.proxy.host_group import HostGroupProxy
from zeus.host_information_service.app.serialize.host_group import (
    AddHostGroupSchema,
    GetHostGroupPage_RequestSchema,
    HostGroupSchema,
)


class HostGroupManageAPI(BaseResponse):
    """
    Interface for get host group
    """

    @BaseResponse.handle(schema=GetHostGroupPage_RequestSchema, proxy=HostGroupProxy)
    def get(self, callback: HostGroupProxy, **params):
        """
        Get host group

        Args:
            cluster_ids (list): cluster ids
            sort (str): sort according to specified field
            direction (str): sort direction
            page (int): current page
            per_page (int): count per page

        Returns:
            dict: response body
        """
        status_code, result = callback.get_host_groups(params)
        return self.response(code=status_code, data=result)

    @BaseResponse.handle(schema=AddHostGroupSchema, proxy=HostGroupProxy)
    def post(self, callback: HostGroupProxy, **params):
        """
        Add host group

        Args:
            host_group_name (str): group name
            description (str): group description
            cluster_id (str): cluster id

        Returns:
            dict: response body
        """
        if cache.user_role != UserRoleType.ADMINISTRATOR:
            return self.response(code=state.PERMESSION_ERROR)

        status_code = callback.add_host_group(params)
        return self.response(code=status_code)


class HostGroupInfoManageAPI(BaseResponse):
    """
    Interface for delete host group and get host group info
    """

    @BaseResponse.handle(proxy=HostGroupProxy)
    def get(self, callback: HostGroupProxy, group_id, **params):
        status_code, host_group = callback.get_host_group_info(group_id)
        if host_group:
            host_group = HostGroupSchema().dump(host_group)

        return self.response(code=status_code, data=host_group)

    @BaseResponse.handle(proxy=HostGroupProxy)
    def delete(self, callback: HostGroupProxy, group_id, **params):
        """
        Delete host group

        Args:
            group_id (int): host group id
        """
        if cache.user_role != UserRoleType.ADMINISTRATOR:
            return self.response(code=state.PERMESSION_ERROR)

        status_code = callback.delete_host_group(group_id)
        return self.response(code=status_code)


class AllHostGroupMapAPI(BaseResponse):
    """
    Interface for get all host group map
    """

    @BaseResponse.handle(proxy=HostGroupProxy)
    def get(self, callback: HostGroupProxy, **params):
        status_code, host_groups = callback.get_all_host_groups_map()

        return self.response(code=status_code, data=host_groups)
