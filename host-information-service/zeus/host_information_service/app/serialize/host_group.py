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
from marshmallow import Schema, fields, validate

from zeus.host_information_service.database import HostGroup


class GetHostGroupPage_ResponseSchema(Schema):
    """
    Get HostGroup page response schema
    """

    host_count = fields.Integer(required=False)
    cluster_name = fields.String(required=False, missing=None, validate=lambda s: 50 >= len(s) > 0)

    class Meta:
        model = HostGroup
        fields = ["host_group_id", "host_group_name", "description", "host_count", "cluster_name", "cluster_id"]


class GetHostGroupPage_RequestSchema(Schema):
    """
    Get HostGroup page request schema
    """

    cluster_ids = fields.List(fields.String(required=False), required=False, missing=None)
    sort = fields.String(required=False, missing=None, validate=validate.OneOf(["host_count", "host_group_name", ""]))
    direction = fields.String(required=False, missing="desc", validate=validate.OneOf(["desc", "asc"]))
    page = fields.Integer(required=False, missing=None, validate=lambda s: s > 0)
    per_page = fields.Integer(required=False, missing=None, validate=lambda s: 50 > s > 0)


class AddHostGroupSchema(Schema):
    """
    Add HostGroup request schema
    """

    host_group_name = fields.String(required=True, validate=lambda s: 0 < len(s) <= 20)
    description = fields.String(required=True, validate=lambda s: 0 < len(s) <= 60)
    cluster_id = fields.String(required=True, validate=lambda s: 36 >= len(s) > 0)


class HostGroupSchema(Schema):
    """
    HostGroup info response schema
    """

    cluster_name = fields.String(required=False, missing=None, validate=lambda s: 50 >= len(s) > 0)
    cluster_id = fields.String(required=True, validate=lambda s: 36 >= len(s) > 0)

    class Meta:
        model = HostGroup
        fields = ["host_group_id", "host_group_name", "description", "cluster_name", "cluster_id"]
