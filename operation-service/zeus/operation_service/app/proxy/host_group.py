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
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse
from vulcanus.conf.constant import HOSTS_GROUP
from zeus.operation_service.app.settings import configuration
from flask import g


class HostGroupProxy:
    """
    HostGroup related table operation
    """

    def get_host_group_by_id(self, host_group_id) -> dict:
        url = f"http://{configuration.domain}{HOSTS_GROUP}/{host_group_id}"
        response_data = BaseResponse.get_response(method="GET", url=url, header=g.headers)
        if response_data.get("label") != state.SUCCEED:
            return {}

        return response_data.get("data")