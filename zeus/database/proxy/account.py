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
Time: 2021-12-22 10:37:56
Author: peixiaochao
Description:
"""
import uuid
import secrets
import sqlalchemy
from werkzeug.security import generate_password_hash, check_password_hash

from vulcanus.log.log import LOGGER
from vulcanus.restful.status import DATABASE_INSERT_ERROR, DATABASE_QUERY_ERROR, \
    LOGIN_ERROR, REPEAT_PASSWORD, SUCCEED, AUTH_ERROR, AUTH_USERINFO_SYNC_ERROR, NO_BOUND, \
    GENERATION_TOKEN_ERROR, NO_DATA, DATABASE_UPDATE_ERROR, REPEAT_BIND
from vulcanus.database.proxy import MysqlProxy
from vulcanus.database.table import User, Auth
from vulcanus.conf.constant import GITEE_CLIENT_ID, GITEE_OAUTH,  GITEE_TOKEN, \
    GITEE_CLIENT_SECRET, GITEE_USERINFO, REFRESH_TOKEN_EXP, REDIRECT_URL
from vulcanus.restful.response import BaseResponse
from vulcanus.token import generate_token


class UserProxy(MysqlProxy):
    """
    User related table operation
    """

    def add_user(self, data):
        """
        Setup user

        Args:
            data(dict): parameter, e.g.
                {
                    "username": "xxx",
                    "password": "xxxxx
                }

        Returns:
            int: status code
        """
        username = data.get('username')
        password = data.get('password')
        token = secrets.token_hex(16)
        password_hash = User.hash_password(password)
        user = User(username=username, password=password_hash, token=token)

        try:
            self.session.add(user)
            self.session.commit()
            LOGGER.info("add user succeed")
            return SUCCEED

        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            self.session.rollback()
            return DATABASE_INSERT_ERROR

    def login(self, data):
        """
        Check user login

        Args:
            data(dict): parameter, e.g.
                {
                    "username": "xxx",
                    "password": "xxxxx
                }

        Returns:
            int: status code
            auth_result: token generated after authentication e.g
                {
                    "token": "xxxxx",
                    "refresh_token": "xxxxx"
                }
        """
        username = data.get('username')
        password = data.get('password')
        auth_result = dict(token=None, refresh_token=None)
        try:
            query_res = self.session.query(
                User).filter_by(username=username).all()
            if len(query_res) == 0:
                LOGGER.error("login with unknown username")
                return LOGIN_ERROR, auth_result

            self.session.commit()
            res = User.check_hash_password(query_res[0].password, password)

            if res:
                LOGGER.info("user login succeed")
                return self._generate_token(username=username)

            LOGGER.error("login with wrong password")
            return LOGIN_ERROR, auth_result

        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR, auth_result

    def change_password(self, data):
        """
        Change user password

        Args:
            data(dict): parameter, e.g.
                {
                    "username": "xxx",
                    "password": "xxxxx",
                    "old_password": "xxxxx"
                }

        Returns:
            int: status code
            User
        """
        username = data.get('username')
        password = data.get('password')
        old_password = data.get("old_password")

        try:
            change_user = self.session.query(
                User).filter_by(username=username).one_or_none()
            if not change_user:
                LOGGER.error("login with unknown username")
                return LOGIN_ERROR, ""

            if not check_password_hash(change_user.password, old_password):
                return LOGIN_ERROR, ""

            if check_password_hash(change_user.password, password):
                return REPEAT_PASSWORD, ""

            change_user.password = generate_password_hash(password)
            self.session.commit()
            LOGGER.error("change password succeed")
            return SUCCEED, change_user

        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("change password fail")
            return DATABASE_QUERY_ERROR, ""

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
        return f"{GITEE_OAUTH}?client_id={GITEE_CLIENT_ID}&scope=user_info&response_type=code&redirect_uri={REDIRECT_URL}"

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
        status_code, save_auth_result = self._gitee_account_info_update(
            userinfo)
        if status_code != SUCCEED:
            LOGGER.error(
                "Gitee authentication user information fails to be saved.")
            return AUTH_USERINFO_SYNC_ERROR, auth_result
        # authentication account is bound to the local account
        if not save_auth_result["bind_local_user"]:
            LOGGER.error("Please bind a local account.")
            auth_result["username"] = save_auth_result["userinfo"].auth_account
            return NO_BOUND, auth_result
        # The token of jwt is generated
        return self._generate_token(username=save_auth_result["userinfo"].username)

    def _generate_token(self, username):
        auth_result = dict(token=None, refresh_token=None, username=username)
        try:
            auth_result["token"] = generate_token(unique_iden=username)
            auth_result["refresh_token"] = generate_token(
                unique_iden=username, minutes=REFRESH_TOKEN_EXP)
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
            auth_userinfo = Auth(auth_account=userinfo.get(
                "login"), auth_type="gitee")
            gitee_auth_user = self.session.query(
                Auth).filter_by(auth_account=userinfo.get("login"), auth_type="gitee").one_or_none()
            if gitee_auth_user:
                gitee_auth_user.auth_account = userinfo.get("login")
                gitee_auth_user.nick_name = userinfo.get("name")
                if gitee_auth_user.username:
                    bind_local_user = True
                auth_userinfo = gitee_auth_user
            else:
                auth = Auth(auth_id=str(uuid.uuid1()).replace('-', ''), auth_account=userinfo.get(
                    "login"), nick_name=userinfo.get("name"), auth_type="gitee")
                self.session.add(auth)
            self.session.commit()
            LOGGER.debug(
                "Gitee user authentication information has been saved or updated.")

            return SUCCEED, dict(bind_local_user=bind_local_user, userinfo=auth_userinfo)
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR, dict(bind_local_user=bind_local_user, userinfo=auth_userinfo)

    def _get_gitee_auth_token(self, code: str):
        auth_url = f"{GITEE_TOKEN}&client_id={GITEE_CLIENT_ID}&code={code}&redirect_uri={REDIRECT_URL}"
        request_body = dict(client_secret=GITEE_CLIENT_SECRET)
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
        local_user = self.session.query(User).filter(
            User.username == username).one_or_none()
        if not local_user:
            return NO_DATA, auth_result

        if not check_password_hash(local_user.password, password):
            return LOGIN_ERROR, auth_result
        try:
            exists_bind_relation_auth = self.session.query(Auth).filter(
                Auth.username == username, Auth.auth_type == auth_type, Auth.auth_account != auth_account).count()
            if exists_bind_relation_auth:
                return REPEAT_BIND, auth_result
            bind_account = self.session.query(Auth).filter(
                Auth.auth_account == auth_account).one_or_none()
            if not bind_account:
                return NO_DATA, auth_result
            bind_account.username = username
            self.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_UPDATE_ERROR, auth_result

        return self._generate_token(username=username)
