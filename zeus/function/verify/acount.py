#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2021. All rights reserved.
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
from marshmallow import Schema
from marshmallow import fields


class LoginSchema(Schema):
    """
    validators for parameter of /manage/account/login
    """
    username = fields.String(required=True, validate=ValidateRules.account_name_check)
    password = fields.String(required=True, validate=ValidateRules.account_password_check)


class AddUserSchema(LoginSchema):
    """
    validators for parameter of /manage/account/add
    """
    email = fields.Email(required=True)


class ChangePasswordSchema(Schema):
    """
    validators for parameter of /manage/account/change
    """
    password = fields.String(required=True, validate=lambda s: len(s) > 0)
    old_password = fields.String(required=True, validate=lambda s: len(s) > 0)


class CertificateSchema(Schema):
    """
    validators for parameter of /manage/account/certificate
    """
    key = fields.String(required=True, validate=lambda s: len(s) > 0)


class BindAuthAccountSchema(Schema):
    """
    validators for parameter of /manage/account/bindaccount
    """
    username = fields.String(required=True, validate=lambda s: len(s) > 0)
    auth_account = fields.String(required=True, validate=lambda s: len(s) > 0)
    password = fields.String(required=True, validate=lambda s: len(s) > 0)


class GiteeAuthLoginSchema(Schema):
    """
    validators for parameter of /manage/account/gitee/login
    """
    code = fields.String(required=True, validate=lambda s: len(s) > 0)


class RefreshTokenSchema(Schema):
    """
    validators for parameter of /manage/account/refreshtoken
    """
    refresh_token = fields.String(required=True, validate=lambda s: len(s) > 0)
