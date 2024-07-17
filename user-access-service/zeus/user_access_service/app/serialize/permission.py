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

from zeus.user_access_service.database.table import User


class GetAccountPage_RequestSchema(Schema):
    """
    Account page request schema
    """

    username = fields.String(required=False, missing=None)
    page = fields.Integer(required=False, missing=None, validate=lambda s: s > 0)
    per_page = fields.Integer(required=False, missing=None, validate=lambda s: 50 > s > 0)


class GetAccountPage_ResponseSchema(Schema):
    """
    Account page response schema
    """

    role_type = fields.String(required=False, missing=None)

    clusters_num = fields.Integer(required=False, missing=None)

    class Meta:
        model = User
        fields = ('username', 'role_type', 'clusters_num', "email")


class GetPermission_RequestSchema(Schema):
    """
    Permission request schema
    """

    username = fields.String(required=False, missing=None)
    cluster_id = fields.String(required=False, missing=None)


class DeletePermission_RequestSchema(Schema):
    """
    Permission delete request schema
    """

    manager_username = fields.String(required=False, missing=None)
    cluster_id = fields.String(required=False, missing=None)


class PermissionSchema(Schema):
    """
    Permission info schema
    """

    cluster_id = fields.String(required=True, validate=validate.Length(min=1, max=36))

    host_group = fields.List(
        fields.String(required=True, validate=validate.Length(min=1, max=36)),
        required=False,
        missing=None,
    )


class SetPermission_RequestSchema(Schema):
    """
    Set permission request schema
    """

    username = fields.String(required=True, validate=validate.Length(min=1, max=36))
    permission = fields.List(
        fields.Nested(PermissionSchema(), required=True), required=False, missing=None, validate=lambda s: len(s) > 0
    )


class BindPermission_RequestSchema(Schema):
    """
    Bind permission request schema
    """

    cluster_id = fields.String(required=True, validate=validate.Length(min=1, max=36))
    manager_username = fields.String(required=True, validate=validate.Length(min=1, max=36))
    public_key = fields.String(required=True, validate=validate.Length(max=4096))
    host_group = fields.List(
        fields.String(required=True, validate=validate.Length(min=1, max=36)),
        required=True,
    )
