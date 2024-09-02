#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2024. All rights reserved.
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
Description: For account related interfaces
"""
from marshmallow import Schema, fields, validate
from vulcanus.restful.serialize.validate import ValidateRules


class Oauth2AuthorizeLoginSchema(Schema):
    """
    validators for parameter of /accounts/login
    """

    code = fields.String(required=True, validate=validate.Length(min=1, max=200))


class Oauth2AuthorizedLogoutSchema(Schema):
    """
    validators for parameter of /accounts/logout
    """

    username = fields.String(required=True, validate=validate.Length(min=5, max=20))
    encrypted_string = fields.String(required=True, validate=validate.Length(min=1, max=200))


class Oauth2AuthorizeAddUserSchema(Schema):
    """
    validators for parameter of /accounts/register
    """

    username = fields.String(required=True, validate=ValidateRules.account_name_check)
    email = fields.Email(required=True)


class ChangePasswordSchema(Schema):
    """
    validators for parameter of /accounts/password
    """

    username = fields.String(required=True, validate=ValidateRules.account_name_check)
    password = fields.String(required=True, validate=ValidateRules.account_password_check)
    old_password = fields.String(required=True, validate=validate.Length(min=6, max=20))


class ResetPasswordSchema(Schema):
    username = fields.String(required=True, validate=validate.Length(min=5, max=20))


class CertificateSchema(Schema):
    """
    validators for parameter of /user/account/certificate
    """

    key = fields.String(required=True, validate=lambda s: len(s) > 0)


class BindManagerUserSchema(Schema):
    username = fields.String(required=True, validate=validate.Length(min=1, max=36))
    password = fields.String(required=True, validate=validate.Length(min=1, max=255))
    manager_username = fields.String(required=True, validate=validate.Length(min=1, max=36))
    manager_cluster_id = fields.String(required=True, validate=validate.Length(min=1, max=36))
    public_key = fields.String(required=True, validate=validate.Length(min=1, max=4096))


class RegisterClusterSchema(Schema):
    """
    Add a single cluster.
    """

    cluster_name = fields.String(required=True, validate=validate.Length(min=1, max=20))
    description = fields.String(required=True, validate=validate.Length(min=1, max=60))
    cluster_ip = fields.String(required=True, validate=ValidateRules.ipv4_address_check)
    cluster_username = fields.String(required=True, validate=validate.Length(min=1, max=36))
    cluster_password = fields.String(required=True, validate=validate.Length(min=1, max=255))


class DeleteClusterSchema(Schema):
    """
    Delete cluster.
    """

    cluster_id = fields.String(required=True, validate=validate.Length(min=1, max=36))


class BatchRegisterClusterSchema(Schema):
    """
    Batch add cluster.
    """

    cluster_info = fields.List(
        fields.Nested(RegisterClusterSchema(), required=True), required=True, validate=lambda s: len(s) > 0
    )


class ClusterKeySchema(Schema):
    """
    Get cluster key info.
    """

    cluster_ids = fields.List(
        fields.String(required=True, validate=validate.Length(min=1, max=36)),
        required=False,
        missing=None,
    )


class UnbindManagerUserSchema(Schema):
    """
    Unbind manager user.
    """

    cluster_id = fields.String(required=True, validate=validate.Length(min=1, max=36))
    cluster_username = fields.String(required=True, validate=lambda s: len(s) > 0)
    signature = fields.String(required=True)


class ClusterSyncSchema(Schema):
    """
    cluster sync.
    """

    cluster_id = fields.String(required=True, validate=validate.Length(min=1, max=36))
    cluster_ip = fields.String(required=True, validate=validate.Length(min=1, max=16))


class GenerateTokenSchema(Schema):
    """
    Generate token.
    """

    client_id = fields.String(required=True, validate=validate.Length(min=1, max=48))
    access_token = fields.String(required=True, validate=validate.Length(min=1, max=255))
