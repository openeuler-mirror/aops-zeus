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
Description: Restful APIs for user
"""

from flask import g
from jwt.exceptions import ExpiredSignatureError
from vulcanus.conf.constant import REFRESH_TOKEN_EXP
from vulcanus.database.proxy import RedisProxy
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse
from vulcanus.token import decode_token, generate_token

from zeus.user_access_service.app.proxy.account import UserProxy
from zeus.user_access_service.app.serialize.account import (
    AddUserSchema,
    BindAuthAccountSchema,
    BindManagerUserSchema,
    ChangePasswordSchema,
    ClusterKeySchema,
    ClusterSyncSchema,
    DeleteClusterSchema,
    GenerateTokenSchema,
    GiteeAuthLoginSchema,
    LoginSchema,
    RefreshTokenSchema,
    RegisterClusterSchema,
    ResetPasswordSchema,
    UnbindManagerUserSchema,
)
from zeus.user_access_service.app.settings import configuration


class AddUser(BaseResponse):
    """
    Interface for register user.
    Restful API: post
    """

    @BaseResponse.handle(schema=AddUserSchema, token=False, proxy=UserProxy)
    def post(self, callback: UserProxy, **params):
        """
        Add user

        Args:
            username (str)
            password (str)
            email (str)

        Returns:
            dict: response body
        """
        register_res = callback.register_user(params)
        if register_res != state.SUCCEED:
            return self.response(code=register_res, message="register user failed.")
        return self.response(code=state.SUCCEED)


class Login(BaseResponse):
    """
    Interface for user login.
    Restful API: post
    """

    @BaseResponse.handle(schema=LoginSchema, token=False, proxy=UserProxy)
    def post(self, callback: UserProxy, **params):
        """
        User login

        Args:
            username (str)
            password (str)

        Returns:
            dict: response body
        """
        g.username = params.get('username')
        status_code, auth_result = callback.login(params)
        if status_code == state.SUCCEED:
            # token 20min expire
            RedisProxy.redis_connect.set("token_" + g.username, auth_result["token"], 20 * 60)
            # refresh_token 24h expire
            RedisProxy.redis_connect.set("refresh_token_" + g.username, auth_result["refresh_token"], 24 * 60 * 60)
            g.headers.update({"Access-Token": auth_result["token"]})
            cache_res = callback.cache_user_permissions(g.username)

        return self.response(code=status_code, data=auth_result)


class AuthRedirectUrl(BaseResponse):
    """
    Forward address of third-party authentication login
    """

    @BaseResponse.handle(proxy=UserProxy, token=False)
    def get(self, callback: UserProxy):
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
        redirect_url = callback.auth_redirect_url()
        return self.response(code=state.SUCCEED, data=redirect_url)


class GiteeAuthLogin(BaseResponse):
    """
    Gitee authentication is used to login
    Restful API: post
    """

    @BaseResponse.handle(schema=GiteeAuthLoginSchema, token=False, proxy=UserProxy)
    def get(self, callback: UserProxy, **params: dict):
        status_code, auth_result = callback.gitee_auth_login(code=params["code"])
        if status_code == state.SUCCEED:
            token_info = decode_token(auth_result["token"])
            RedisProxy.redis_connect.set("token_" + token_info["key"], auth_result["token"], 20 * 60)
            RedisProxy.redis_connect.set(
                "refresh_token_" + token_info["key"], auth_result["refresh_token"], 24 * 60 * 60
            )
        return self.response(code=status_code, data=auth_result)


class BindAuthAccount(BaseResponse):
    """
    Local users and authorized users are bound to each other
    Restful API: post
    """

    @BaseResponse.handle(schema=BindAuthAccountSchema, token=False, proxy=UserProxy)
    def post(self, callback: UserProxy, **params: dict):
        status_code, auth_result = callback.bind_auth_account(
            auth_account=params["auth_account"], username=params["username"], password=params["password"]
        )
        if status_code == state.SUCCEED:
            RedisProxy.redis_connect.set("token_" + params["username"], auth_result["token"], 20 * 60)
            RedisProxy.redis_connect.set(
                "refresh_token_" + params["username"], auth_result["refresh_token"], 24 * 60 * 60
            )
        return self.response(code=status_code, data=auth_result)


class ChangePassword(BaseResponse):
    """
    Interface for user change password.
    Restful API: post
    """

    @BaseResponse.handle(schema=ChangePasswordSchema, proxy=UserProxy)
    def put(self, callback: UserProxy, **params: dict):
        """
        Change password

        Args:
            password (str): new password

        Returns:
            dict: response body
        """
        return self.response(code=callback.change_password(params))

    @BaseResponse.handle(schema=ResetPasswordSchema, proxy=UserProxy)
    def post(self, callback: UserProxy, **params: dict):
        reset_res = callback.reset_password(params)
        if reset_res != state.SUCCEED:
            return self.response(code=reset_res)
        return self.response(code=state.SUCCEED)


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
        try:
            refresh_token_info = decode_token(params.get("refresh_token"))
        except ExpiredSignatureError:
            return self.response(code=state.TOKEN_EXPIRE, message="token expired.")
        except ValueError:
            self.response(code=state.TOKEN_ERROR, message="token refreshing failure.")

        username = refresh_token_info["key"]
        old_refresh_token = RedisProxy.redis_connect.get("refresh_token_" + username)
        if not old_refresh_token or old_refresh_token != params.get("refresh_token"):
            return self.response(code=state.TOKEN_ERROR, message="Invalid token.")

        try:
            token = generate_token(unique_iden=username)
            refresh_token = generate_token(unique_iden=username, minutes=REFRESH_TOKEN_EXP)
        except ValueError:
            LOGGER.error("Token generation failed,token refreshing failure.")
            return self.response(code=state.GENERATION_TOKEN_ERROR)
        # Remove an expired token
        RedisProxy.redis_connect.delete("token_" + username)
        RedisProxy.redis_connect.delete("refresh_token_" + username)
        # Set a new token value
        RedisProxy.redis_connect.set("token_" + username, token, 20 * 60)
        RedisProxy.redis_connect.set("refresh_token_" + username, refresh_token, 24 * 60 * 60)

        return self.response(code=state.SUCCEED, data=dict(token=token, refresh_token=refresh_token))


class Logout(BaseResponse):
    """
    Interface for logout.
    Restful API: post
    """

    @BaseResponse.handle()
    def get(self):
        """
        Refresh token

        Returns:
            dict: response body
        """
        if not g.username:
            return self.response(code=state.LOGOUT_ERROR)
        RedisProxy.redis_connect.delete("token_" + g.username)
        RedisProxy.redis_connect.delete("refresh_token_" + g.username)
        RedisProxy.redis_connect.delete(g.username + "_role")
        RedisProxy.redis_connect.delete(g.username + "_clusters")
        RedisProxy.redis_connect.delete(g.username + "_group_hosts")
        RedisProxy.redis_connect.delete(g.username + "_rsa_key")
        return self.response(code=state.SUCCEED)


class BindManagerUser(BaseResponse):
    @BaseResponse.handle(schema=BindManagerUserSchema, token=False, proxy=UserProxy)
    def post(self, callback: UserProxy, **params):
        """Bind manager user for cluster.

        Args:
            {
                "username":"admin",
                "password":"xxx",
                "manager_username":"admin123",
                "manager_cluster_id":"1",
                "public_key": "xxx"
            }

        Returns:
            dict: {
                "user_name": "cluster_username",
                "cluster_id": "cluster_id",
            }
        """
        status_code, data = callback.bind_local_cluster_with_manager(**params)
        if status_code != state.SUCCEED:
            return self.response(code=status_code)
        return self.response(code=state.SUCCEED, data=data)


class RegisterClusterAPI(BaseResponse):
    @BaseResponse.handle(schema=RegisterClusterSchema, proxy=UserProxy)
    def post(self, callback: UserProxy, **params):
        """Register cluster.

        Args:
            args (dict): e.g.
            {
                "cluster_name": "cluster name",
                "description": "description",
                "cluster_ip": "127.0.0.1",
                "cluster_username": "admin",
                "cluster_password": "changeme",
            }

        Returns:
            dict:
            {
                "code": 200,
                "label": "Succeed",
                "message": "operation succeed",
            }
        """
        register_res = callback.register_cluster(params)
        return self.response(code=register_res)


class CacheClusterPermissionAPI(BaseResponse):
    @BaseResponse.handle(proxy=UserProxy)
    def get(self, callback: UserProxy):
        """Cache cluster permission.

        Returns:
            response body
        """
        query_res = callback.cache_user_permissions(g.username)
        return self.response(code=query_res)


class ManagedClusterAPI(BaseResponse):
    @BaseResponse.handle(schema=DeleteClusterSchema, proxy=UserProxy)
    def delete(self, callback: UserProxy, **params):
        """_summary_

        Args:
            args (str): e.g.
            {
                "cluster_id": "cluster_id,
            }

        Returns:
            dict:
            {
                "code": 200,
                "data": [
                    {
                        "cluster_name": "cluster1",
                        "result": "succeed",
                    }
                ]
                "label": "Succeed",
                "message": "operation succeed",
            }
        """
        delete_res = callback.delete_managed_cluster(params)
        return self.response(code=delete_res)

    @BaseResponse.handle(proxy=UserProxy)
    def get(self, callback: UserProxy, **params):
        """Get user managed cluster info.

        Returns:
            dict:
            {
                "code": 200,
                "data": [
                    {
                        "cluster_id": "xxx",
                        "cluster_ip": "xxx",
                        "cluster_name": "xxx",
                        "subcluster": true,
                        "description": "xxx",
                    },
                    {
                        "cluster_id": "xxx",
                        "cluster_ip": "xxx",
                        "cluster_name": "xxx",
                        "subcluster": false,
                        "description": "xxx",
                    },
                ]
                "label": "Succeed",
                "message": "operation succeed",
            }
        """
        get_res, cluster_infos = callback.get_user_managed_cluster_info(params)
        if get_res != state.SUCCEED:
            return self.response(code=get_res, messgae="get user managed cluster info failed.")
        return self.response(code=state.SUCCEED, data=cluster_infos)


class ClusterKeyAPI(BaseResponse):
    @BaseResponse.handle(proxy=UserProxy, schema=ClusterKeySchema)
    def get(self, callback: UserProxy, **params):
        """Get user cluster key info.

        Args:
            params (dict):
            {
                {"cluster_ids": ["cluster_id1", "cluster_id2"]}
            }

        Returns:
            dict:
            {
                "code": 200,
                "data": [
                    {
                        "cluster_id": "xxxx",
                        "cluster_username": "xxxx",
                        "private_key": "xxxx",
                        "public_key": "xxxx",
                    },
                ],
                "label": "Succeed",
                "message": "operation succeed"
            }
        """
        get_status, cluster_key_info = callback.get_user_cluster_key(params)
        if get_status != state.SUCCEED:
            return self.response(code=get_status, message="get user cluster key info failed.")
        return self.response(code=state.SUCCEED, data=cluster_key_info)


class UnbindManagerUserAPI(BaseResponse):
    @BaseResponse.handle(proxy=UserProxy, token=False, schema=UnbindManagerUserSchema)
    def delete(self, callback: UserProxy, **params):
        """Unbind manager user for local cluster.

        Args:
            params (dict):
            {
                 "cluster_id": "id1",
                 "cluster_username": "cluster_username",
                 "signature": xxx
            }

        Returns:
            dict:
            {
                "code": 200,
                "label": "Succeed",
                "message": "operation succeed"
            }
        """
        unbind_status = callback.unbind_local_cluster_with_manager(**params)
        return self.response(code=unbind_status)


class AccountsAllAPI(BaseResponse):
    @BaseResponse.handle(proxy=UserProxy, token=False)
    def get(self, callback: UserProxy):
        """Get all accounts info.

        Returns:
            dict:
            {
                "code": 200,
                "data": [
                    {
                        "username": "user1",
                        "email": "xxx"
                    },
                ],
                "label": "Succeed",
                "message": "operation succeed"
            }
        """
        get_res, accounts_info = callback.get_all_accounts_info()
        if get_res != state.SUCCEED:
            return self.response(code=get_res)
        return self.response(code=state.SUCCEED, data=accounts_info)


class ClusterSync(BaseResponse):
    @BaseResponse.handle(proxy=UserProxy, schema=ClusterSyncSchema)
    def post(self, callback: UserProxy, **params):
        """Get all accounts info.

        Returns:
            dict:
            {
                "code": 200,
                "label": "Succeed",
                "message": "operation succeed"
            }
        """
        cluster_id = params.get("cluster_id")
        cluster_ip = params.get('cluster_ip')
        get_res = callback.cluster_synchronize(cluster_id, cluster_ip)
        return self.response(code=get_res)


class AccessTokenAPI(BaseResponse):

    @BaseResponse.handle(schema=GenerateTokenSchema, token=False)
    def post(self, **parmas):
        """
        generate access token

        Returns:
            dict: response body
        """

        validate_token = BaseResponse.get_response(
            method="post",
            url=f"http://{configuration.domain}/oauth2/introspect",
            data=dict(token=parmas.get("access_token"), client_id=parmas.get("client_id")),
        )
        if validate_token["label"] != state.SUCCEED:
            return self.response(code=state.GENERATION_TOKEN_ERROR)
        username = validate_token["data"]
        token = generate_token(unique_iden=username, minutes=60 * 24, aud=parmas.get("client_id"))
        RedisProxy.redis_connect.set("token-" + username + "-" + parmas.get("client_id"), token, 24 * 60 * 60)
        return self.response(code=state.SUCCEED, data=dict(access_token=token))
