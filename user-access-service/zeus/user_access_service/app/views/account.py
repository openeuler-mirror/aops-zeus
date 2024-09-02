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


from flask import g, make_response, request
from vulcanus.database.proxy import RedisProxy
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse
from vulcanus.token import generate_token
from zeus.user_access_service.app.proxy.account import UserProxy
from zeus.user_access_service.app.serialize.account import (
    BindManagerUserSchema,
    ChangePasswordSchema,
    ClusterKeySchema,
    ClusterSyncSchema,
    DeleteClusterSchema,
    GenerateTokenSchema,
    Oauth2AuthorizeAddUserSchema,
    Oauth2AuthorizedLogoutSchema,
    Oauth2AuthorizeLoginSchema,
    RegisterClusterSchema,
    ResetPasswordSchema,
    UnbindManagerUserSchema,
)
from zeus.user_access_service.app.settings import configuration


class Oauth2AuthorizeAddUser(BaseResponse):
    """
    Interface for oauth2 authorize register user.
    Restful API: post
    """

    @BaseResponse.handle(schema=Oauth2AuthorizeAddUserSchema, token=False, proxy=UserProxy)
    def post(self, callback: UserProxy, **params):
        """
        Add user

        Args:
            username (str)
            email (str)

        Returns:
            dict: response body
        """
        register_res = callback.oauth2_authorize_register_user(params)
        if register_res != state.SUCCEED:
            return self.response(code=register_res, message="register user failed.")
        return self.response(code=state.SUCCEED)


class Oauth2AuthorizeLogin(BaseResponse):
    """
    Interface for oauth2 authorized user login.
    Restful API: post
    """

    @BaseResponse.handle(schema=Oauth2AuthorizeLoginSchema, token=False, proxy=UserProxy)
    def post(self, callback: UserProxy, **params):
        """
        User login

        Args:
            code (str): authorization code

        Returns:
            dict: response body
        """
        status_code, auth_result = callback.oauth2_authorize_login(params)
        if status_code == state.SUCCEED:
            g.username = auth_result["username"]
            # token 20min expire
            RedisProxy.redis_connect.set(
                "token-" + auth_result["username"] + "-" + configuration.client_id, auth_result["token"], 20 * 60
            )
            g.headers.update({"Access-Token": auth_result["token"]})
            cache_res = callback.cache_user_permissions(auth_result["username"])

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

    @BaseResponse.handle(token=False, proxy=UserProxy)
    def get(self, callback: UserProxy):
        """
        Refresh token.

        Returns:
            dict: response body
        """
        invaild_token = request.headers.get("Access-Token")
        if not invaild_token:
            return self.response(code=state.GENERATION_TOKEN_ERROR, message='Not found token')

        if not RedisProxy.redis_connect.set(invaild_token + "-invaild-token", 'locked', nx=True, ex=30):
            LOGGER.warning("The RefreshToken call has been made and repeated execution is not allowed.")
            return self.response(code=state.GENERATION_TOKEN_ERROR, message='Token generated')

        refresh_res, refresh_data = callback.refresh_token(invaild_token)
        if refresh_res != state.SUCCEED:
            return self.response(code=refresh_res)
        if RedisProxy.redis_connect.keys("token-" + refresh_data["username"] + "-*"):
            RedisProxy.redis_connect.delete(*RedisProxy.redis_connect.keys("token-" + refresh_data["username"] + "-*"))
        # 20 minutes expire
        RedisProxy.redis_connect.set(
            "token-" + refresh_data["username"] + "-" + configuration.client_id, refresh_data["token"], 20 * 60
        )
        return self.response(code=state.SUCCEED, data=dict(token=refresh_data["token"]))


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


class Logout(BaseResponse):
    """
    Interface for logout.
    Restful API: post
    """

    @BaseResponse.handle(proxy=UserProxy)
    def get(self, callback: UserProxy):
        """
        Refresh token

        Returns:
            dict: response body
        """
        if not g.username:
            return self.response(code=state.LOGOUT_ERROR)
        logout_res = callback.logout(g.username)
        if logout_res != state.SUCCEED:
            return self.response(code=logout_res)
        response = make_response(self.response(code=state.SUCCEED))
        response.set_cookie('Authorization', '', expires=0)
        return response


class Oauth2AuthorizeLogout(BaseResponse):
    """
    Interface for logout.
    Restful API: post
    """

    @BaseResponse.handle(schema=Oauth2AuthorizedLogoutSchema, proxy=UserProxy, token=False)
    def post(self, callback: UserProxy, **params):
        """
        Oauth2 authorize logout.

        Args:
            {
                "username":"admin",
                "encrypted_string":"encrypted_string",
            }

        Returns:
            dict: response body

        """
        username = params.get("username")
        delete_res = callback.oauth2_authorize_logout(params)
        if delete_res != state.SUCCEED:
            return self.response(code=state.LOGOUT_ERROR)
        RedisProxy.redis_connect.delete(*RedisProxy.redis_connect.keys("token-" + username + "*"))
        RedisProxy.redis_connect.delete(username + "_role")
        RedisProxy.redis_connect.delete(username + "_clusters")
        RedisProxy.redis_connect.delete(username + "_group_hosts")
        RedisProxy.redis_connect.delete(username + "_rsa_key")
        return self.response(code=state.SUCCEED)


class Oauth2AuthorizeUri(BaseResponse):
    @BaseResponse.handle(token=False)
    def get(self):
        """
        Oauth2AuthorizeUri.
        """
        uri = (
            f"http://{configuration.domain}/oauth2/authorize?"
            f"client_id={configuration.client_id}&"
            f"redirect_uri={configuration.redirect_uri}&"
            f"scope=openid offline_access&"
            f"response_type=code&"
            f"prompt=consent&"
            f"state=235345&"
            f"nonce=loser"
        )

        return self.response(code=state.SUCCEED, data=uri)


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
