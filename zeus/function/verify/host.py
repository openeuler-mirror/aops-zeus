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
"""
Time:
Author:
Description: For host related interfaces
"""
from vulcanus.restful.serialize.validate import ValidateRules
from marshmallow import fields, Schema, validate, validates_schema, ValidationError


class HostSchema(Schema):
    """
    validator for host info
    """

    host_name = fields.String(required=True, validate=lambda s: len(s) > 0)
    host_group_name = fields.String(required=True, validate=lambda s: len(s) > 0)
    host_ip = fields.IP(required=True)
    management = fields.Boolean(required=True)
    username = fields.String(required=True, validate=lambda s: 32 >= len(s) > 0)
    password = fields.String(required=True, validate=lambda s: len(s) > 0)
    agent_port = fields.Integer(required=True, validate=lambda s: 65535 >= s >= 0)
    os_version = fields.String(required=True, validate=lambda s: len(s) > 0)


class DeleteHostSchema(Schema):
    """
    validators for parameter of /manage/host/delete_host
    """

    host_list = fields.List(
        fields.Integer(required=True, validate=lambda s: s > 0), required=True, validate=lambda s: len(s) > 0
    )


class GetHostSchema(Schema):
    """
    validators for parameter of /manage/host/get_host
    """

    host_group_list = fields.List(fields.String(), required=True)
    search_key = fields.String(required=False, validate=lambda s: 50 >= len(s) > 0)
    management = fields.Boolean(required=False)
    status = fields.List(fields.Integer(validate=lambda s: s >= 0), required=False)
    sort = fields.String(required=False, validate=validate.OneOf(["host_name", "host_group_name", ""]))
    direction = fields.String(required=False, validate=validate.OneOf(["desc", "asc"]))
    page = fields.Integer(required=False, validate=lambda s: s > 0)
    per_page = fields.Integer(required=False, validate=lambda s: 50 > s > 0)


class GetHostStatusSchema(Schema):
    """
    validators for parameter of /manage/host/getstatus
    """

    host_list = fields.List(fields.Integer(), required=True)


class AddHostGroupSchema(Schema):
    """
    validators for parameter of /manage/host/add_host_group
    """

    host_group_name = fields.String(required=True, validate=lambda s: len(s) > 0)
    description = fields.String(required=True)


class DeleteHostGroupSchema(Schema):
    """
    validators for parameter of /manage/host/delete_host_group
    """

    host_group_list = fields.List(fields.String(), required=True, validate=lambda s: len(s) > 0)


class GetHostGroupSchema(Schema):
    """
    validators for parameter of /manage/host/get_host_group
    """

    sort = fields.String(required=False, validate=validate.OneOf(["host_count", "host_group_name", ""]))
    direction = fields.String(required=False, validate=validate.OneOf(["desc", "asc"]))
    page = fields.Integer(required=False, validate=lambda s: s > 0)
    per_page = fields.Integer(required=False, validate=lambda s: 50 > s > 0)


class GetHostInfoSchema(Schema):
    """
    validators for parameter of /manage/host/get_host_information
    """

    host_list = fields.List(fields.Integer(), required=True)
    basic = fields.Boolean(required=False)


class AddHostSchema(Schema):
    """
    validators for parameter of /manage/host/add
    """

    ssh_user = fields.String(required=True, validate=lambda s: 32 >= len(s) > 0)
    password = fields.String(required=True, allow_none=True, validate=lambda s: len(s) >= 0)
    host_name = fields.String(
        required=True, validate=[validate.Length(min=1, max=50), ValidateRules.space_character_check]
    )
    host_ip = fields.String(required=True, validate=ValidateRules.ipv4_address_check)
    ssh_pkey = fields.String(required=True, allow_none=True, validate=lambda s: 4096 >= len(s) >= 0)
    ssh_port = fields.Integer(required=True, validate=lambda s: 65535 >= s > 0)
    host_group_name = fields.String(required=True, validate=lambda s: 20 >= len(s) > 0)
    management = fields.Boolean(required=True, truthy={True}, falsy={False})

    @validates_schema
    def check_authentication_info(self, data, **kwargs):
        if not data.get("ssh_pkey") and not data.get("password"):
            raise ValidationError("At least one of the password and key needs to be provided")


class AddHostBatchSchema(Schema):
    """
    validators for parameter of /manage/host/add/batch
    """

    host_list = fields.List(fields.Nested(AddHostSchema(), required=True), required=True, validate=lambda s: len(s) > 0)


class UpdateHostSchema(Schema):
    """
    validators for parameter of /manage/host/update
    """

    host_id = fields.Integer(required=True, validate=lambda s: s > 0)
    ssh_user = fields.String(required=False, validate=lambda s: 32 >= len(s) > 0)
    password = fields.String(required=False, validate=lambda s: len(s) > 0)
    ssh_port = fields.Integer(required=False, validate=lambda s: 65535 >= s > 0)
    host_name = fields.String(
        required=False, validate=[validate.Length(min=1, max=50), ValidateRules.space_character_check]
    )
    host_group_name = fields.String(required=False, validate=lambda s: 20 >= len(s) > 0)
    management = fields.Boolean(required=False, truthy={True}, falsy={False})
    ssh_pkey = fields.String(required=False, validate=lambda s: 4096 >= len(s) >= 0)
