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
from vulcanus.restful.response import BaseResponse
from vulcanus.database.proxy import RedisProxy
from vulcanus.conf.constant import REFRESH_TOKEN_EXP
from vulcanus.log.log import LOGGER
from vulcanus.token import decode_token, generate_token
from vulcanus.restful.resp import state
from zeus.account_manager.cache import UserCache
from zeus.database.proxy.account import UserProxy
from zeus.function.verify.acount import (
    BindAuthAccountSchema,
    GiteeAuthLoginSchema,
    LoginSchema,
    ChangePasswordSchema,
    AddUserSchema,
    RefreshTokenSchema
)


class AddUser(BaseResponse):
    """
    Interface for register user.
    Restful API: post
    """

    @BaseResponse.handle(schema=AddUserSchema, token=False, proxy=UserProxy())
    def post(self, callback: UserProxy, **params):
        """
        Add user

        Args:
            username (str)
            password (str)

        Returns:
            dict: response body
        """
        status_code = callback.add_user(params)
        return self.response(code=status_code)


class Login(BaseResponse):
    """
    Interface for user login.
    Restful API: post
    """

    @BaseResponse.handle(schema=LoginSchema, token=False, proxy=UserProxy())
    def post(self, callback: UserProxy, **params):
        """
        User login

        Args:
            username (str)
            password (str)

        Returns:
            dict: response body
        """
        status_code, auth_result = callback.login(params)
        if status_code == state.SUCCEED:
            token_info = decode_token(auth_result["token"])
            RedisProxy.redis_connect.set(
                "token_" + token_info["key"], auth_result["token"])
            RedisProxy.redis_connect.set(
                "refresh_token_" + token_info["key"], auth_result["refresh_token"])
        return self.response(code=status_code, data=auth_result)


class AuthRedirectUrl(BaseResponse):
    """
    Forward address of third-party authentication login
    """

    @BaseResponse.handle(token=False)
    def get(self, **params):
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
        proxy = UserProxy()
        redirect_url = proxy.auth_redirect_url()
        return self.response(code=state.SUCCEED, data=redirect_url)


class GiteeAuthLogin(BaseResponse):
    """
    Gitee authentication is used to login
    Restful API: post
    """

    @BaseResponse.handle(schema=GiteeAuthLoginSchema, token=False, proxy=UserProxy())
    def get(self, callback: UserProxy, **params):

        status_code, auth_result = callback.gitee_auth_login(
            code=params["code"])
        if status_code == state.SUCCEED:
            token_info = decode_token(auth_result["token"])
            RedisProxy.redis_connect.set(
                "token_" + token_info["key"], auth_result["token"])
            RedisProxy.redis_connect.set(
                "refresh_token_" + token_info["key"], auth_result["refresh_token"])

        return self.response(code=status_code, data=auth_result)


class BindAuthAccount(BaseResponse):
    """
    Local users and authorized users are bound to each other
    Restful API: post
    """

    @BaseResponse.handle(schema=BindAuthAccountSchema, token=False, proxy=UserProxy())
    def post(self, callback: UserProxy, **params):

        status_code, auth_result = callback.bind_auth_account(
            auth_account=params["auth_account"], username=params["username"], password=params["password"])
        return self.response(code=status_code, data=auth_result)


class ChangePassword(BaseResponse):
    """
    Interface for user change password.
    Restful API: post
    """

    @BaseResponse.handle(schema=ChangePasswordSchema, proxy=UserProxy())
    def post(self, callback: UserProxy, **params):
        """
        Change password

        Args:
            password (str): new password

        Returns:
            dict: response body
        """
        status_code, user = callback.change_password(params)
        if status_code == state.SUCCEED:
            UserCache.update(user.username, user)
        return self.response(code=status_code)


class RefreshToken(BaseResponse):
    """
    Interface for refresh token.
    Restful API: post
    """

    @BaseResponse.handle(schema=RefreshTokenSchema, token=False)
    def post(self, **params):
        """
        Refresh token

        Returns:
            dict: response body
        """
        status = self.verify_token(params.get("refresh_token"), params)
        if status != state.SUCCEED:
            return self.response(code=status, message="token refreshing failure.")
        try:
            username = decode_token(params.get("refresh_token"))["key"]
            token = generate_token(unique_iden=username)
            refresh_token = generate_token(
                unique_iden=username, minutes=REFRESH_TOKEN_EXP)
        except ValueError:
            LOGGER.error("Token generation failed,token refreshing failure.")
            return self.response(code=state.GENERATION_TOKEN_ERROR)

        RedisProxy.redis_connect.set("token_" + username, token)
        RedisProxy.redis_connect.set(
            "refresh_token_" + username, refresh_token)

        return self.response(code=state.SUCCEED, data=dict(token=token, refresh_token=refresh_token))
