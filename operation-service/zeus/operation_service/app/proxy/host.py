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
from vulcanus.conf.constant import HOSTS, HOSTS_FILTER
from zeus.operation_service.app.settings import configuration
from flask import g
from urllib.parse import urlencode


class HostProxy:
    """
    Host related table operation
    """

    def get_host_by_id(self, host_id) -> dict:
        url = f"http://{configuration.domain}{HOSTS}/{host_id}"
        response = BaseResponse.get_response(method="GET", url=url, header=g.headers)
        if response.get("label") != state.SUCCEED:
            return {}

        return response.get("data")

    def get_host_pkey_by_id(self, host_id) -> str:
        params = {
            "fields": ['host_id','host_ip','host_name','last_scan','repo_id','host_group_name','cluster_id','pkey'],
            "host_ids": [host_id]
            }

        url = f"http://{configuration.domain}{HOSTS_FILTER}?{urlencode(params)}"
        response = BaseResponse.get_response(method="GET", url=url, header=g.headers)
        hosts = response.get("data")
        if response.get("label") != state.SUCCEED or not hosts:
            return ""
        host_info = response.get("data")[0]
        return host_info.get("pkey")
