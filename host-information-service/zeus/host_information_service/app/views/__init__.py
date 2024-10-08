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

from zeus.host_information_service.app.views.host import (
    BatchAddHostAPI,
    HostCountAPI,
    HostFilterAPI,
    HostInfoManageAPI,
    HostManageAPI,
    HostStatusAPI,
    HostTemplateAPI,
    SingleHostStatusAPI,
)
from zeus.host_information_service.app.views.host_group import HostGroupInfoManageAPI, HostGroupManageAPI

__all__ = (
    "BatchAddHostAPI",
    "HostManageAPI",
    "HostInfoManageAPI",
    "HostTemplateAPI",
    "HostCountAPI",
    "SingleHostStatusAPI",
    "HostFilterAPI",
    "HostStatusAPI",
    "HostGroupManageAPI",
    "HostGroupInfoManageAPI",
)
