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
Description: Restful APIs for user
"""
from flask import jsonify
from vulcanus.restful.response import BaseResponse
from vulcanus.restful.status import SUCCEED, DATABASE_CONNECT_ERROR
from vulcanus.database.helper import operate
from vulcanus.database.proxy import RedisProxy
from vulcanus.token import decode_token
from zeus.account_manager.cache import UserCache
from zeus.account_manager.key import HostKey
from zeus.database import SESSION
from zeus.database.proxy.account import UserProxy
from zeus.function.verify.acount import (
    BindAuthAccountSchema,
    GiteeAuthLoginSchema,
    LoginSchema,
    CertificateSchema,
    ChangePasswordSchema,
    AddUserSchema
)


class AddUser(BaseResponse):
    """
    Interface for register user.
    Restful API: post
    """

    @staticmethod
    def _handle(args):
        status_code = operate(UserProxy(), args, 'add_user', SESSION)
        return status_code

    def post(self):
        """
        Add user

        Args:
            username (str)
            password (str)

        Returns:
            dict: response body
        """
        return jsonify(self.handle_request(AddUserSchema,
                                           self,
                                           need_token=False,
                                           debug=False))


class Login(BaseResponse):
    """
    Interface for user login.
    Restful API: post
    """
    @staticmethod
    def _handle(args):
        status_code, auth_result = operate(UserProxy(), args, 'login', SESSION)
        if status_code == SUCCEED:
            token_info = decode_token(auth_result["token"])
            RedisProxy.redis_connect.set(
                "token_" + token_info["key"], auth_result["token"])
            RedisProxy.redis_connect.set(
                "refresh_token_" + token_info["key"], auth_result["refresh_token"])
        return status_code, auth_result

    def post(self):
        """
        User login

        Args:
            username (str)
            password (str)

        Returns:
            dict: response body
        """
        return jsonify(self.handle_request(LoginSchema,
                                           self,
                                           need_token=False,
                                           debug=False))


class AuthRedirectUrl(BaseResponse):
    """
    Forward address of third-party authentication login
    """

    @staticmethod
    def _handle(args):
        proxy = UserProxy()
        redirect_url = proxy.auth_redirect_url()
        return SUCCEED, redirect_url

    def get(self):
        """
        Auth redirect url

        Args:
            host: http://openeuler.org

        Returns:
            dict: eg. 
            {
                "gitee": "https://gitee.com"
            }

        """
        return jsonify(self.handle_request(None,
                                           self,
                                           need_token=False,
                                           debug=False))


class GiteeAuthLogin(BaseResponse):
    """
    Gitee authentication is used to login
    Restful API: post
    """

    @staticmethod
    def _handle(args):
        proxy = UserProxy()
        if not proxy.connect(SESSION):
            return DATABASE_CONNECT_ERROR, {}
        status_code, auth_result = proxy.gitee_auth_login(code=args["code"])
        if status_code == SUCCEED:
            token_info = decode_token(auth_result["token"])
            RedisProxy.redis_connect.set(
                "token_" + token_info["key"], auth_result["token"])
            RedisProxy.redis_connect.set(
                "refresh_token_" + token_info["key"], auth_result["refresh_token"])
        return status_code, auth_result

    def get(self):
        return jsonify(self.handle_request(GiteeAuthLoginSchema,
                                           self,
                                           need_token=False,
                                           debug=False))


class BindAuthAccount(BaseResponse):
    """
    Local users and authorized users are bound to each other
    Restful API: post
    """
    @staticmethod
    def _handle(args):
        proxy = UserProxy()
        if not proxy.connect(SESSION):
            return DATABASE_CONNECT_ERROR, {}
        status_code, auth_result = proxy.bind_auth_account(
            auth_account=args["auth_account"], username=args["username"], password=args["password"])

        return status_code, auth_result

    def post(self):
        return jsonify(self.handle_request(BindAuthAccountSchema,
                                           self,
                                           need_token=False,
                                           debug=False))


class ChangePassword(BaseResponse):
    """
    Interface for user change password.
    Restful API: post
    """
    @staticmethod
    def _handle(args):
        proxy = UserProxy()
        if not proxy.connect(SESSION):
            return DATABASE_CONNECT_ERROR, {}

        status_code, user = proxy.change_password(args)
        if status_code == SUCCEED:
            UserCache.update(user.username, user)

        return status_code

    def post(self):
        """
        Change password

        Args:
            password (str): new password

        Returns:
            dict: response body
        """
        return jsonify(self.handle_request(ChangePasswordSchema,
                                           self,
                                           debug=False))


class Certificate(BaseResponse):
    """
    Interface for user certificate.
    Restful API: post
    """
    @staticmethod
    def _handle(args):
        """
        Handle function

        Args:
            args (dict)

        Returns:
            int: status code
        """
        HostKey.update(args['username'], args['key'])

        return SUCCEED

    def post(self):
        """
        Certificate  user

        Args:
            key (strs)

        Returns:
            dict: response body
        """
        return jsonify(self.handle_request(CertificateSchema, self, debug=False))
