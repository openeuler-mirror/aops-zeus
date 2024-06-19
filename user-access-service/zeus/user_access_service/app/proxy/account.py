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
Time: 2024-6-5 10:37:56
Author: 
Description:
"""
import json
import subprocess
import uuid
from typing import Tuple

import sqlalchemy
from celery import Celery
from flask import g
from vulcanus.cache import RedisError
from vulcanus.conf import constant
from vulcanus.conf.constant import (GITEE_OAUTH, GITEE_TOKEN, GITEE_USERINFO, REFRESH_TOKEN_EXP,
                                    TaskStatus)
from vulcanus.database.proxy import MysqlProxy, RedisProxy
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp.state import (AUTH_ERROR, AUTH_USERINFO_SYNC_ERROR, CLUSTER_MANAGE_ERROR,
                                         CLUSTER_REPEAT_BIND_ERROR, DATA_EXIST,
                                         DATABASE_INSERT_ERROR, DATABASE_QUERY_ERROR,
                                         DATABASE_UPDATE_ERROR, GENERATION_TOKEN_ERROR,
                                         IP_PING_FAILED, LOGIN_ERROR, NO_BOUND, NO_DATA,
                                         PASSWORD_ERROR, PERMESSION_ERROR, REDIS_CACHEINFO_ERROR,
                                         REDIS_SYNCHRONIZE_TASK_FAILED, REPEAT_BIND, REPEAT_DATA,
                                         REPEAT_PASSWORD, SUCCEED, SYNCHRONIZE_ERROR,
                                         TARGET_CLUSTER_DELETE_ERROR, TARGET_CLUSTER_MANAGE_ERROR,
                                         USER_ERROR)
from vulcanus.restful.response import BaseResponse
from vulcanus.rsa import generate_rsa_key_pair, get_private_key_pem_str, get_public_key_pem_str
from vulcanus.token import generate_token
from werkzeug.security import check_password_hash, generate_password_hash
from zeus.user_access_service.app import cache
from zeus.user_access_service.app.constant import BACKEND, BROKER
from zeus.user_access_service.app.settings import configuration
from zeus.user_access_service.database.table import (Auth, Permission, Role,
                                                     RolePermissionAssociation, User,
                                                     UserClusterAssociation, UserMap,
                                                     UserRoleAssociation)


    def auth_redirect_url(self):
        """
        Go to the authentication address

        Args:
            host: https://openeuler.org

        Returns:
            dict: e.g
                {
                    "gitee": "http://gitee.com"
                }
        """
        redirect_url = dict()
        redirect_url["gitee"] = self._gitee_auth_redirect_url
        return redirect_url

    @property
    def _gitee_auth_redirect_url(self):
        client_id = configuration.individuation.gitee_client_id
        redirect_url = configuration.individuation.redirect_url
        if not all([client_id, redirect_url]):
            LOGGER.error("The 'gitee_client_id' 'redirect_url' configuration is missing.")

        return f"{GITEE_OAUTH}?client_id={client_id}&scope=user_info&response_type=code&redirect_uri={redirect_url}"

    def gitee_auth_login(self, code: str):
        """
        Gitee auth login

        Args:
            code: Specifies the code used to exchange tokens for login authentication
            host: Host domain name
        Returns:
            status_code: Login status code
            dict: e.g
                {
                    "token": "",
                    "refresh_token": ""
                }
        """
        token = self._get_gitee_auth_token(code)
        auth_result = dict(token=None, refresh_token=None)
        if not token:
            return AUTH_ERROR, auth_result
        userinfo = self._get_gitee_userinfo(token)
        if not userinfo:
            return LOGIN_ERROR, auth_result
        status_code, save_auth_result = self._gitee_account_info_update(userinfo)
        if status_code != SUCCEED:
            LOGGER.error("Gitee authentication user information fails to be saved.")
            return AUTH_USERINFO_SYNC_ERROR, auth_result
        # authentication account is bound to the local account
        if not save_auth_result["bind_local_user"]:
            LOGGER.error("Please bind a local account.")
            auth_result["username"] = save_auth_result["userinfo"].auth_account
            return NO_BOUND, auth_result
        # The token of jwt is generated
        return self._generate_auth_result(username=save_auth_result["userinfo"].username)

    def _generate_auth_result(self, username):
        gen_res, auth_result = self._generate_token(username)
        if gen_res != SUCCEED:
            return gen_res, auth_result
        get_res, role_type = self.get_user_role_type(username)
        if get_res != SUCCEED:
            return get_res, auth_result
        auth_result["type"] = role_type
        return SUCCEED, auth_result

    def _generate_token(self, username):
        auth_result = dict(token=None, refresh_token=None, username=username)
        try:
            auth_result["token"] = generate_token(unique_iden=username)
            auth_result["refresh_token"] = generate_token(unique_iden=username, minutes=REFRESH_TOKEN_EXP)
            return SUCCEED, auth_result

        except ValueError:
            LOGGER.error("Token generation failed.")
            return GENERATION_TOKEN_ERROR, auth_result

    def _gitee_account_info_update(self, userinfo: dict):
        """
        Deposit to gitee account or update information

        Args:
            userinfo: gitee user information e.g
                {
                    "login":"",
                    "name":"",
                }
        """
        try:
            bind_local_user = False
            auth_userinfo = Auth(auth_account=userinfo.get("login"), auth_type="gitee")
            gitee_auth_user = (
                self.session.query(Auth).filter_by(auth_account=userinfo.get("login"), auth_type="gitee").one_or_none()
            )
            if gitee_auth_user:
                gitee_auth_user.auth_account = userinfo.get("login")
                gitee_auth_user.nick_name = userinfo.get("name")
                if gitee_auth_user.username:
                    bind_local_user = True
                auth_userinfo = gitee_auth_user
            else:
                auth = Auth(
                    auth_id=str(uuid.uuid1()).replace('-', ''),
                    auth_account=userinfo.get("login"),
                    nick_name=userinfo.get("name"),
                    auth_type="gitee",
                )
                self.session.add(auth)
            self.session.commit()
            LOGGER.debug("Gitee user authentication information has been saved or updated.")

            return SUCCEED, dict(bind_local_user=bind_local_user, userinfo=auth_userinfo)
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR, dict(bind_local_user=bind_local_user, userinfo=auth_userinfo)

    def _get_gitee_auth_token(self, code: str):
        client_id = configuration.individuation.gitee_client_id
        redirect_url = configuration.individuation.redirect_url
        if not all([client_id, redirect_url]):
            LOGGER.error("The 'gitee_client_id' 'redirect_url' configuration is missing.")
            return None

        auth_url = f"{GITEE_TOKEN}&client_id={client_id}&code={code}&redirect_uri={redirect_url}"
        request_body = dict(client_secret=configuration.individuation.gitee_client_secret)
        response = BaseResponse.get_response('POST', auth_url, request_body)
        if "access_token" not in response:
            LOGGER.error("Gitee authentication failed to get token.")
            return None

        return response.get("access_token")

    def _get_gitee_userinfo(self, token: str):
        userinfo_url = f"{GITEE_USERINFO}?access_token={token}"
        response = BaseResponse.get_response('GET', userinfo_url, {})
        if "login" not in response:
            LOGGER.error("Description Failed to get gitee user information.")
            response = None

        return response

    def bind_auth_account(self, auth_account: str, username: str, password: str, auth_type="gitee"):
        """
        Local users and authorized users are bound to each

        Args:
            auth_account: Authenticated users, including gitee、github
            username: Local user name

        Returns:
            status_code: Status code
            auth_result: e.g
                {
                    "token":
                    "refresh_token"
                }
        """
        auth_result = dict(token=None, refresh_token=None, username=username)
        local_user = self.session.query(User).filter(User.username == username).one_or_none()
        if not local_user:
            return NO_DATA, auth_result

        if not check_password_hash(local_user.password, password):
            return LOGIN_ERROR, auth_result
        try:
            exists_bind_relation_auth = (
                self.session.query(Auth)
                .filter(Auth.username == username, Auth.auth_type == auth_type, Auth.auth_account != auth_account)
                .count()
            )
            if exists_bind_relation_auth:
                return REPEAT_BIND, auth_result
            bind_account = self.session.query(Auth).filter(Auth.auth_account == auth_account).one_or_none()
            if not bind_account:
                return NO_DATA, auth_result
            bind_account.username = username
            self.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_UPDATE_ERROR, auth_result

        return self._generate_auth_result(username=username)

    def get_user_role_type(self, username: str) -> Tuple[str, str]:
        try:
            role_type = self._get_user_role_type(username)
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("get user role type failed")
            return NO_DATA, ""
        return SUCCEED, role_type