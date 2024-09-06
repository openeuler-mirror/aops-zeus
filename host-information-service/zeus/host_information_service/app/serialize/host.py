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
from marshmallow import Schema, ValidationError, fields, validate, validates_schema
from vulcanus.restful.serialize.validate import ValidateRules

from zeus.host_information_service.database import Host
from zeus.host_information_service.app.constant import HostTemplate


class _AddHost(Schema):
    ssh_user = fields.String(required=True, validate=lambda s: 32 >= len(s) > 0)
    password = fields.String(required=False, validate=lambda s: len(s) >= 0)
    host_name = fields.String(
        required=True, validate=[validate.Length(min=1, max=50), ValidateRules.space_character_check]
    )
    host_ip = fields.String(required=True, validate=ValidateRules.ipv4_address_check)
    ssh_pkey = fields.String(required=False, missing=None, validate=lambda s: 4096 >= len(s) >= 0)
    ssh_port = fields.Integer(required=True, validate=lambda s: 65535 >= s > 0)
    management = fields.Boolean(required=True, truthy={True}, falsy={False})

    @validates_schema
    def check_authentication_info(self, data, **kwargs):
        if not data.get("ssh_pkey") and not data.get("password"):
            raise ValidationError("At least one of the password and key needs to be provided")


class AddHostSchema(_AddHost):
    """
    Add a single host
    """

    host_group_id = fields.String(required=True, validate=lambda s: 36 >= len(s) > 0)


class GetHostsPage_RequestSchema(Schema):
    """
    Get host information page request schema
    """

    host_group_list = fields.List(fields.String(required=False), required=False, missing=None)
    cluster_list = fields.List(fields.String(required=False), required=False, missing=None)
    search_key = fields.String(required=False, missing=None, validate=lambda s: 50 >= len(s) > 0)
    management = fields.Boolean(required=False, missing=None)
    status = fields.List(fields.Integer(validate=lambda s: s >= 0), required=False, missing=None)
    sort = fields.String(required=False, missing=None, validate=validate.OneOf(["host_name", "host_group_name", ""]))
    direction = fields.String(required=False, missing=None, validate=validate.OneOf(["desc", "asc"]))
    page = fields.Integer(required=False, missing=None, validate=lambda s: s > 0)
    per_page = fields.Integer(required=False, missing=None, validate=lambda s: 50 > s > 0)


class GetHostsPage_ResponseSchema(Schema):
    """
    Get host information page response schema
    """

    cluster_name = fields.String(required=False, missing=None, validate=lambda s: 50 >= len(s) > 0)

    class Meta:
        model = Host
        fields = (
            "host_id",
            "host_name",
            "host_group_name",
            "host_ip",
            "management",
            "scene",
            "os_version",
            "ssh_port",
            "cluster_id",
            "cluster_name",
        )


class _AddHostBatch(_AddHost):
    """
    Batch add host by host group name
    """

    host_group_name = fields.String(required=True, validate=lambda s: 20 >= len(s) > 0)


class AddHostBatchSchema(Schema):
    """
    Batch add host info
    """

    host_list = fields.List(fields.Nested(_AddHostBatch(), required=True), required=True, validate=lambda s: len(s) > 0)


class UpdateHostSchema(Schema):
    """
    Update host info
    """

    host_ip = fields.String(required=False, missing=None, validate=ValidateRules.ipv4_address_check)
    ssh_user = fields.String(required=False, missing=None, validate=lambda s: 32 >= len(s) > 0)
    password = fields.String(required=False, missing=None, validate=lambda s: len(s) > 0)
    ssh_port = fields.Integer(required=False, missing=None, validate=lambda s: 65535 >= s > 0)
    host_name = fields.String(
        required=False, missing=None, validate=[validate.Length(min=1, max=50), ValidateRules.space_character_check]
    )
    host_group_id = fields.String(required=True, validate=lambda s: 36 >= len(s) > 0)
    management = fields.Boolean(required=False, missing=None, truthy={True}, falsy={False})
    ssh_pkey = fields.String(required=False, missing=None, validate=lambda s: 4096 >= len(s) >= 0)
    status = fields.Integer(required=False, missing=None, validate=validate.OneOf([0, 1, 2, 3]))
    last_scan = fields.Integer(required=False, missing=None, validate=lambda s: s > 0)
    repo_id = fields.String(required=False, missing=None, validate=lambda s: 36 >= len(s) >= 0)
    reboot = fields.Boolean(required=False, missing=None, truthy={True}, falsy={False})


class HostsInfo_ResponseSchema(Schema):
    """
    Get host information response schema
    """

    cluster_name = fields.String(required=False, missing=None, validate=lambda s: 50 >= len(s) > 0)

    class Meta:
        model = Host
        fields = (
            "host_id",
            "host_name",
            "host_group_name",
            "host_group_id",
            "host_ip",
            "management",
            "scene",
            "os_version",
            "ssh_port",
            "last_scan",
            "repo_id",
            "status",
            "reboot",
            "pkey",
            "ssh_user",
            "cluster_id",
            "cluster_name",
            "ext_props",
        )


class BatchHostsSchema(Schema):
    """
    Batch add host info
    """

    host_ids = fields.List(fields.String(required=True), required=True, validate=lambda s: len(s) > 0)


class HostFilterSchema(Schema):
    """
    Filter host info
    """

    status = fields.List(fields.String(required=True), required=False, missing=None)
    host_ids = fields.List(fields.String(required=True), required=False, missing=None, validate=lambda s: len(s) > 0)
    host_group_ids = fields.List(
        fields.String(required=True, validate=lambda s: 36 >= len(s) > 0), required=False, missing=None
    )
    host_name = fields.String(required=False, missing=None, validate=[validate.Length(min=1, max=50)])
    reboot = fields.Boolean(required=False, missing=None)
    repo = fields.List(fields.String(required=True, validate=lambda s: 36 >= len(s) > 0), required=False, missing=None)
    cluster_list = fields.List(
        fields.String(required=True, validate=lambda s: 36 >= len(s) > 0), required=False, missing=None
    )
    fields = fields.List(
        fields.String(
            required=True,
            validate=validate.OneOf(
                [
                    "host_id",
                    "host_name",
                    "host_ip",
                    "host_group_name",
                    "host_group_id",
                    "status",
                    "reboot",
                    "last_scan",
                    "repo_id",
                    "pkey",
                    "ssh_user",
                    "ssh_port",
                    "cluster_id",
                    "ext_props",
                ]
            ),
        ),
        required=False,
        missing=None,
    )


class HostIpsFilterSchema(Schema):
    """
    Filter host info by ip
    """
    host_ips = fields.List(fields.String(required=True), required=True, validate=lambda s: len(s) > 0)


class HostByIpsResponseSchema(Schema):
    """
    Get host information by ips response schema
    """

    cluster_name = fields.String(required=False, missing=None, validate=lambda s: 50 >= len(s) > 0)

    class Meta:
        model = Host
        fields = (
            "host_id",
            "host_name",
            "host_group_name",
            "host_ip",
            "cluster_id",
        )


class UpdateHostStatusSchema(Schema):
    """
    Update host status
    """

    status = fields.Integer(required=False, missing=None, validate=validate.OneOf([0, 1, 2, 3]))


class HostInfoSchema(Schema):
    """
    Host information schema
    """

    basic = fields.Boolean(required=False, missing=True, validate=validate.OneOf([True, False]))
    refresh = fields.Boolean(required=False, missing=False, validate=validate.OneOf([True, False]))


class TemplateLangSchema(Schema):
    """
    File template language
    """

    lang = fields.String(required=False, missing='en', validate=validate.OneOf(HostTemplate.support_lang()))
