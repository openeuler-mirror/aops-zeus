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
import base64
import json
import subprocess
import time
import uuid
from typing import Tuple

import celery
import celery.exceptions
import sqlalchemy
from flask import g
from vulcanus.conf import constant
from vulcanus.conf.constant import (
    OAUTH2_AUTHORIZE_TOKEN,
    OAUTH2_INTROSPECT,
    OAUTH2_LOGIN,
    OAUTH2_REFRESH_TOKEN,
    TaskStatus,
)
from vulcanus.database.proxy import MysqlProxy, RedisProxy
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp.state import (
    AUTH_ERROR,
    CLUSTER_MANAGE_ERROR,
    CLUSTER_REPEAT_BIND_ERROR,
    DATA_EXIST,
    DATABASE_DELETE_ERROR,
    DATABASE_INSERT_ERROR,
    DATABASE_QUERY_ERROR,
    DATABASE_UPDATE_ERROR,
    IP_PING_FAILED,
    NO_DATA,
    NO_MANAGED_DATA,
    PERMESSION_ERROR,
    REDIS_CACHEINFO_ERROR,
    REDIS_SYNCHRONIZE_TASK_FAILED,
    REPEAT_DATA,
    SUCCEED,
    SYNCHRONIZE_ERROR,
    TARGET_CLUSTER_DELETE_ERROR,
    TARGET_CLUSTER_MANAGE_ERROR,
    TOKEN_EXPIRE,
)
from vulcanus.restful.response import BaseResponse
from vulcanus.rsa import (
    generate_rsa_key_pair,
    get_private_key_pem_str,
    get_public_key_pem_str,
    load_private_key,
    load_public_key,
    sign_data,
    verify_signature,
)
from vulcanus.token import generate_token
from zeus.user_access_service.app import cache, celery_client
from zeus.user_access_service.app.settings import configuration
from zeus.user_access_service.database.table import (
    Permission,
    Role,
    RolePermissionAssociation,
    UserClusterAssociation,
    UserInfo,
    UserMap,
    UserRoleAssociation,
    UserToken,
)


class UserProxy(MysqlProxy):
    """
    User related table operation
    """

    def oauth2_authorize_register_user(self, data) -> str:
        """Register user.

        Args:
            data (dict):
            {
                username (str)
                email (str)
            }

        Returns:
            str: status_code
        """
        local_cluster_id = cache.location_cluster["cluster_id"]
        return self._oauth2_authorize_register_user(local_cluster_id, data)

    def _oauth2_authorize_register_user(self, local_cluster_id, data) -> str:
        """Register user, bind the local cluster, and default is normal user.

        Args:
            local_cluster_id (str): local cluster id
            data (dict):
            {
                username (str)
                email (str)
            }

        Returns:
            str : status_code
        """
        username = data.get('username')
        try:
            # bind current cluster for the user
            self._associate_cluster_with_user(username, local_cluster_id, username, "")
            # grant normal role for the user
            self._grant_user_role(username=username, role_type=constant.UserRoleType.NORMAL)
            # save user info
            self._save_user_info(data)
            self.session.commit()
            LOGGER.debug("add user succeed.")
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("add user failed.")
            self.session.rollback()
            return DATABASE_INSERT_ERROR
        return SUCCEED

    def _save_user_info(self, data: dict):
        user_info = UserInfo(username=data["username"], email=data["email"])
        self.session.add(user_info)

    def _grant_user_role(self, username: str, role_type: str):
        """Grant user role.

        Args:
            username (str): username
            role_type (str): role_type, "administrator" or "normal"
        """
        role_id = str(uuid.uuid1()).replace('-', '')
        user_role_assoc = UserRoleAssociation(username=username, role_id=role_id)
        role = Role(role_id=role_id, role_type=role_type)
        self.session.add(user_role_assoc)
        self.session.add(role)

    def refresh_token(self, invalid_token: str) -> Tuple[str, dict]:
        """
        Get new access token by refresh token.

        Args:
            invalid_token(str): expired access token

        Returns:
            Tuple[str, dict]
        """
        try:
            user_token = self.session.query(UserToken).filter_by(local_access_token=invalid_token).one_or_none()
            if not user_token:
                return TOKEN_EXPIRE, {}
            username = user_token.username
            refresh_res, oauth2_token = self._refresh_token(user_token.refresh_token)
            if refresh_res != SUCCEED:
                return refresh_res, {}
            local_access_token = generate_token(unique_iden=username, minutes=60 * 24, aud=configuration.client_id)
            self.session.query(UserToken).filter_by(username=username).update(
                {"access_token": oauth2_token.get("access_token"), "local_access_token": local_access_token}
            )
            self.session.commit()
        except sqlalchemy.orm.exc.MultipleResultsFound as error:
            LOGGER.error(error)
            LOGGER.error(f"user should be unique: {username}")
            return REPEAT_DATA, {}
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("user login failed.")
            return DATABASE_UPDATE_ERROR, {}

        return SUCCEED, dict(token=local_access_token, username=username)

    def _refresh_token(self, refresh_token: str) -> Tuple[str, dict]:
        data = {
            "refresh_token": refresh_token,
            "client_id": configuration.client_id,
        }
        query_url = f"http://{configuration.domain}{OAUTH2_REFRESH_TOKEN}"
        response_data = BaseResponse.get_response(method="Post", url=query_url, data=data, header=g.headers)
        response_status = response_data.get("label")
        if response_status != SUCCEED:
            return response_status, {}

        oauth2_token: dict = response_data.get("data")
        return SUCCEED, oauth2_token

    def login_status_check(self, username: str) -> str:
        """
        Login status check.

        Args:
            username(str): username

        Returns:
            str: status code
        """
        try:
            user_token = self.session.query(UserToken).filter_by(username=username).one()
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error(f"login status check: {username}.")
            return DATABASE_QUERY_ERROR

        return SUCCEED

    def oauth2_authorize_logout(self, params: dict):
        """
        Oauth2 authorize logout.

        Args:
            {
                "username":"admin",
                "encrypted_string":"encrypted_string",
            }

        Returns:
            int: status code
        """
        # decrypt data
        encrypted_data = params.get("encrypted_string")
        decrypt_data = base64.b64decode(encrypted_data.encode('utf-8'))
        decrypt_data = decrypt_data.decode('utf-8')
        username = params.get("username")
        # check the info of encrypted_string, it should be: {client_id: client_secret}
        if {configuration.client_id: configuration.client_secret} != eval(decrypt_data):
            LOGGER.error(f"decrypt encrypted string for logout user error: {username}.")
            return AUTH_ERROR
        try:
            self.session.query(UserToken).filter_by(username=username).delete(synchronize_session=False)
            self.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error(f"oauth2 authorize logout failed: {username}.")
            self.session.rollback()
            return DATABASE_DELETE_ERROR
        return SUCCEED

    def oauth2_authorize_login(self, data):
        """
        Oauth2 authorize login.

        Args:
            data(dict): parameter, e.g.
                {
                    "code": "xxxxx
                }

        Returns:
            int: status code
            auth_result: token generated after authentication e.g
                {
                    "token": "xxxxx",
                    "username": "xxxxx",
                    "role_type": "administrator/normal",
                }
        """
        authorization_code = data.get('code')
        auth_result = dict(token=None)
        try:
            get_res, oauth2_tokens = self._oauth2_authorize(authorization_code)
            if get_res != SUCCEED:
                LOGGER.error(f"get oauth2 token failed.")
                return get_res, auth_result
            username = oauth2_tokens["username"]
            role_type = self._get_user_role_type(username)
            local_access_token = generate_token(unique_iden=username, minutes=20, aud=configuration.client_id)
            self._record_user_token(username, oauth2_tokens, local_access_token)
            self.session.commit()
        except sqlalchemy.orm.exc.MultipleResultsFound as error:
            LOGGER.error(error)
            LOGGER.error(f"user should be unique: {username}")
            self.session.rollback()
            return REPEAT_DATA, auth_result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error(f"oauth2 authorize login failed: {username}.")
            self.session.rollback()
            return DATABASE_QUERY_ERROR, auth_result
        return SUCCEED, {"type": role_type, "token": local_access_token, "username": username}

    def _record_user_token(self, username: str, oauth2_tokens: dict, local_access_token: str):
        user_token = self.session.query(UserToken).filter_by(username=username).first()
        oauth2_access_token = oauth2_tokens.get("access_token")
        oauth2_refresh_token = oauth2_tokens.get("refresh_token")
        generated_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        if user_token:
            user_token.access_token = oauth2_access_token
            user_token.local_access_token = local_access_token
            user_token.refresh_token = oauth2_refresh_token
            user_token.generated_time = generated_time
        else:
            user_token = UserToken(
                username=username,
                access_token=oauth2_access_token,
                local_access_token=local_access_token,
                refresh_token=oauth2_refresh_token,
                generated_time=generated_time,
            )
        self.session.add(user_token)

    def _oauth2_authorize(self, authorization_code: str) -> Tuple[str, dict]:
        """
        Oauth2 authorize:
        1. get oauth2 tokens(include access_token, refresh_token and id_token)
           by 'authorization code' type.
        2. verify the oauth2 access_token.

        Args:
            authorization_code(str): authorization code

        Returns:
            [status_code, oauth2_tokens]
        """
        auth_res, oauth2_tokens = self._get_oauth2_authorized_token(authorization_code)
        if auth_res != SUCCEED:
            return auth_res, {}

        verified_res, username = self._verify_oauth2_access_token(oauth2_tokens.get("access_token"))
        if verified_res != SUCCEED:
            return verified_res, {}

        oauth2_tokens["username"] = username
        return SUCCEED, oauth2_tokens

    def _verify_oauth2_access_token(self, oauth2_access_token: str) -> Tuple[str, dict]:
        """Verify oauth2 token.

        Args:
            oauth2_access_token (str): oauth2 access token

        Returns:
            _type_: _description_
        """
        data = {"token": oauth2_access_token, "client_id": configuration.client_id}
        query_url = f"http://{configuration.domain}{OAUTH2_INTROSPECT}"
        response_data = BaseResponse.get_response(method="Post", url=query_url, data=data, header=g.headers)
        response_status = response_data.get("label")
        if response_status != SUCCEED:
            return response_status, {}

        verified_data: dict = response_data.get("data")
        return SUCCEED, verified_data

    def _get_oauth2_authorized_token(self, authorization_code: str) -> Tuple[str, dict]:
        """Get jwt authorized token by 'authorization_code' grant type.

        Args:
            code (str): authorization code

        Returns:
            Tuple[str, str]: status_code, oauth2_token
        """
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": configuration.redirect_uri,
            "client_id": configuration.client_id,
        }
        query_url = f"http://{configuration.domain}{OAUTH2_AUTHORIZE_TOKEN}"
        response_data = BaseResponse.get_response(method="Post", url=query_url, data=data, header=g.headers)
        response_status = response_data.get("label")
        if response_status != SUCCEED:
            return response_status, {}

        oauth2_tokens: dict = response_data.get("data")
        return SUCCEED, oauth2_tokens

    def _get_user_role_type(self, username: str) -> str:
        """Get user role type

        Args:
            username (str): username

        Returns:
            str: role_type, e.g. "administrator" or "normal"
        """
        user_role_subquery = (
            self.session.query(UserRoleAssociation).filter(UserRoleAssociation.username == username).subquery()
        )
        role = self.session.query(Role).filter(Role.role_id == user_role_subquery.c.role_id).one_or_none()
        if not role:
            return None
        return role.role_type

    def cache_user_permissions(self, username: str):
        """Cache user permissions in redis.

        Redis cache e.g.
        hashmap, key: "admin_clusters",    value: {"cluster_id": "cluster_name"}
        hashmap, key: "admin_group_hosts", value: {"group_id": "group_name"}
        string,  key: "admin_roles",       value: "administrator"

        """
        query_res, user_perm = self._get_user_permissions(username)
        if query_res != SUCCEED:
            return query_res
        format_res, result = self._format_cluster_permissions(user_perm)
        if format_res != SUCCEED:
            return format_res
        user_clusters, user_group_hosts = result
        RedisProxy.redis_connect.delete(username + "_role")
        RedisProxy.redis_connect.delete(username + "_clusters")
        RedisProxy.redis_connect.delete(username + "_group_hosts")
        RedisProxy.redis_connect.set(username + "_role", user_perm['role_type'])
        if user_clusters:
            RedisProxy.redis_connect.hmset(username + "_clusters", user_clusters)
        if user_group_hosts:
            RedisProxy.redis_connect.hmset(username + "_group_hosts", user_group_hosts)
            RedisProxy.redis_connect.expire(username + "_group_hosts", 60)
        return SUCCEED

    def _get_user_permissions(self, username: str) -> Tuple[str, dict]:
        """Get user permissions, including role type, host group permissions,
        and cluster permissions.

        Args:
            username (str): username

        Returns:
            Tuple[str, dict]: status_code, user_perm
        """
        try:
            user_perm = dict(role_type="", hosts_group=[], clusters=[])
            user_role_assoc_subquery = (
                self.session.query(UserRoleAssociation).filter(UserRoleAssociation.username == username).subquery()
            )
            role = self.session.query(Role).filter(Role.role_id == user_role_assoc_subquery.c.role_id).one_or_none()
            if not role:
                LOGGER.error("get user role type failed.")
                return NO_DATA, user_perm

            user_perm["role_type"] = role.role_type

            cluster_perm = list()
            hosts_group_perm = list()
            # get managed cluster_ids
            user_clusters_assoc = (
                self.session.query(UserClusterAssociation.cluster_id).filter_by(username=username).all()
            )
            if not user_clusters_assoc:
                return SUCCEED, user_perm
            for user_cluster_assoc in user_clusters_assoc:
                cluster_perm.append(user_cluster_assoc.cluster_id)

            user_perm["clusters"] = cluster_perm
            # get managed host_group_ids
            role_perms_assoc_subquery = (
                self.session.query(RolePermissionAssociation)
                .filter(RolePermissionAssociation.role_id == user_role_assoc_subquery.c.role_id)
                .subquery()
            )
            permissions = (
                self.session.query(Permission)
                .filter(Permission.permission_id == role_perms_assoc_subquery.c.permission_id)
                .all()
            )
            for permission in permissions:
                if permission.type != "host_group":
                    continue
                if permission.cluster_id not in cluster_perm:
                    LOGGER.error("cluster permission is not consistent in database.")
                    return DATABASE_QUERY_ERROR, user_perm
                if not permission.object_id:
                    continue
                hosts_group_perm.append(permission.object_id)

            user_perm["hosts_group"] = hosts_group_perm
            return SUCCEED, user_perm
        except sqlalchemy.orm.exc.MultipleResultsFound as error:
            LOGGER.error(error)
            return REPEAT_DATA, user_perm
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR, user_perm

    def _format_cluster_permissions(self, user_perm: dict) -> Tuple[str, Tuple[dict, dict]]:
        """Format cluster permissions for caching in redis."""
        role_type, clusters_id, hosts_group = user_perm["role_type"], user_perm["clusters"], user_perm["hosts_group"]

        clusters = cache.clusters
        cluster_groups = cache.cluster_groups
        user_clusters = dict()
        user_group_hosts = dict()
        for cluster_id in clusters_id:
            if cluster_id not in clusters:
                LOGGER.error(
                    f"cluster is managed by user, but cluster info not in redis, please check 'cluster' table for cluster id: {cluster_id}."
                )
                RedisProxy.redis_connect.delete("clusters")
                RedisProxy.redis_connect.delete("cluster_groups")
                return REDIS_CACHEINFO_ERROR, (None, None)
            cluster_info = clusters[cluster_id]
            user_clusters[cluster_id] = cluster_info["cluster_name"]

            if cluster_id not in cluster_groups:
                continue
            for group_info in cluster_groups[cluster_id]:
                group_id, group_name = next(iter(group_info.items()))
                if role_type != constant.UserRoleType.ADMINISTRATOR and group_id not in hosts_group:
                    continue
                user_group_hosts.update(group_info)

        return SUCCEED, (user_clusters, user_group_hosts)

    def get_user_role_type(self, username: str) -> Tuple[str, str]:
        try:
            role_type = self._get_user_role_type(username)
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("get user role type failed")
            return NO_DATA, ""
        return SUCCEED, role_type

    def bind_local_cluster_with_manager(self, **data) -> Tuple[str, str]:
        username = data.get('username')
        password = data.get('password')
        manager_username = data.get("manager_username")
        manager_cluster_id = data.get('manager_cluster_id')
        public_key = data.get('public_key')
        # validate cluster user admin permission
        validate_res = self._validate_user(username, password)
        if validate_res != SUCCEED:
            return validate_res, {}
        local_cluster_id = cache.location_cluster["cluster_id"]
        try:
            if manager_cluster_id == local_cluster_id:
                LOGGER.error(f"cannot process managing local cluster operation.")
                return CLUSTER_REPEAT_BIND_ERROR, {}
            check_res = self._check_cluster_no_manage_other_clusters()
            if not check_res:
                LOGGER.error(f"cannot manage cluster that has managed other clusters.")
                return TARGET_CLUSTER_MANAGE_ERROR, {}

            query_res = [
                user_map.manager_cluster_id for user_map in self.session.query(UserMap.manager_cluster_id).all()
            ]
            if not query_res:
                cluster_username = self._bind_local_cluster_with_manager(local_cluster_id, **data)
            elif set(query_res) - {manager_cluster_id}:
                LOGGER.error(f"local cluster has been binded with other manager cluster.")
                return TARGET_CLUSTER_MANAGE_ERROR, {}
            elif manager_cluster_id in query_res:
                update_data = self.session.query(UserMap).filter_by(manager_cluster_id=manager_cluster_id).one()
                cluster_username = update_data.username
                self.session.query(UserMap).filter_by(manager_cluster_id=manager_cluster_id).update(
                    {"public_key": public_key, "manager_username": manager_username}, synchronize_session=False
                )

                LOGGER.debug(
                    f"info in 'user_map' table has been updated for manager_user: {manager_username}, {manager_cluster_id}."
                )

            self.session.commit()
            LOGGER.debug(f"local cluster {local_cluster_id} binding with manager {manager_username} success.")
        except sqlalchemy.orm.exc.MultipleResultsFound as error:
            LOGGER.error(error)
            LOGGER.error(f"the data in 'user_map' table error, local cluster {local_cluster_id} binding failed.")
            self.session.rollback()
            return REPEAT_DATA, {}
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error(f"local cluster {local_cluster_id} binding failed.")
            self.session.rollback()
            return DATABASE_INSERT_ERROR, {}

        g.username = cluster_username
        g.headers["Access-Token"] = generate_token(unique_iden=g.username, minutes=60 * 24, aud=configuration.client_id)
        RedisProxy.redis_connect.set(
            "token-" + g.username + "-" + configuration.client_id, g.headers["Access-Token"], 20 * 60
        )
        cache_res = self.cache_user_permissions(cluster_username)
        if cache_res != SUCCEED:
            return cache_res, {}
        # for cache user rsa key
        get_res, _ = self.get_user_cluster_key(dict())
        if get_res != SUCCEED:
            return get_res, {}

        return SUCCEED, dict(user_name=cluster_username, cluster_id=local_cluster_id)

    def _check_cluster_no_manage_other_clusters(self):
        clusters_info = cache.clusters
        for cluster_id, cluster_info in clusters_info.items():
            if cluster_info["subcluster"] == True:
                return False
        return True

    def _bind_local_cluster_with_manager(self, local_cluster_id, **data):
        manager_username = data.get("manager_username")
        manager_cluster_id = data.get('manager_cluster_id')
        public_key = data.get('public_key')
        # create new admin user for current cluster corresponding to the manager user
        cluster_username = str(uuid.uuid1()).replace('-', '')

        # bind current cluster with the user
        self._associate_cluster_with_user(cluster_username, local_cluster_id, cluster_username, "")
        # grant admin role for the user
        self._grant_user_role(username=cluster_username, role_type=constant.UserRoleType.ADMINISTRATOR)
        self._associate_local_user_with_manager(cluster_username, manager_cluster_id, manager_username, public_key)
        return cluster_username

    def unbind_local_cluster_with_manager(self, **data):
        cluster_id = data.get("cluster_id")
        try:
            binded_usernames = [
                user_map.username
                for user_map in self.session.query(UserMap).filter_by(manager_cluster_id=cluster_id).all()
            ]
            if not binded_usernames:
                LOGGER.error(f"local cluster does not have managed data for cluster: {cluster_id}")
                return NO_MANAGED_DATA
            validate_res = self._validate_signature(**data)
            if validate_res == PERMESSION_ERROR:
                LOGGER.error(
                    f"unbind local cluster validate failed, please check cluster_username or signature parameter"
                )
                return validate_res

            user_map_subquery = self.session.query(UserMap).filter(UserMap.manager_cluster_id == cluster_id).subquery()
            self.session.query(UserClusterAssociation).filter(
                UserClusterAssociation.username == user_map_subquery.c.username
            ).delete(synchronize_session=False)
            user_role_assoc_subquery = (
                self.session.query(UserRoleAssociation)
                .filter(UserRoleAssociation.username == user_map_subquery.c.username)
                .subquery()
            )
            self.session.query(Role).filter(Role.role_id == user_role_assoc_subquery.c.role_id).delete(
                synchronize_session=False
            )
            self.session.query(UserRoleAssociation).filter(UserRoleAssociation.username == user_map_subquery.c.username)
            role_permission_assoc_subquery = (
                self.session.query(RolePermissionAssociation)
                .filter(RolePermissionAssociation.role_id == user_role_assoc_subquery.c.role_id)
                .subquery()
            )
            self.session.query(RolePermissionAssociation).filter(
                RolePermissionAssociation.role_id == user_role_assoc_subquery.c.role_id
            ).delete(synchronize_session=False)
            self.session.query(Permission).filter(
                Permission.permission_id == role_permission_assoc_subquery.c.permission_id
            ).delete(synchronize_session=False)
            self.session.query(UserMap).filter(UserMap.manager_cluster_id == cluster_id).delete(
                synchronize_session=False
            )
            self.session.commit()
            LOGGER.debug(f"unbind local cluster with manager cluster succeed: {cluster_id}")
            for binded_username in binded_usernames:
                RedisProxy.redis_connect.delete(binded_username + "_clusters")
                RedisProxy.redis_connect.delete(binded_username + "_group_hosts")
                RedisProxy.redis_connect.delete(binded_username + "_rsa_key")
                RedisProxy.redis_connect.delete(binded_username + "_role")

        except sqlalchemy.orm.exc.MultipleResultsFound as error:
            LOGGER.error(error)
            LOGGER.error(f"unbind local cluster with manager cluster failed: {cluster_id}")
            self.session.rollback()
            return REPEAT_DATA
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error(f"unbind local cluster with manager cluster failed: {cluster_id}")
            self.session.rollback()
            return DATABASE_UPDATE_ERROR

        return SUCCEED

    def _validate_signature(self, cluster_id: str, cluster_username: str, signature: str):
        data = {"cluster_id": cluster_id, "cluster_username": cluster_username}

        public_key = None
        user_map = (
            self.session.query(UserMap)
            .filter(UserMap.manager_cluster_id == cluster_id, UserMap.username == cluster_username)
            .one_or_none()
        )
        if user_map:
            public_key = user_map.public_key

        if not public_key or not verify_signature(data, signature, load_public_key(public_key)):
            return PERMESSION_ERROR
        return SUCCEED

    def _check_local_cluster_not_binded(self, manager_cluster_id: str):
        if not self.session.query(UserMap).filter().first():
            return SUCCEED
        user_map = self.session.query(UserMap).filter_by(manager_cluster_id=manager_cluster_id).one_or_none()
        if user_map.manager_cluster_id != manager_cluster_id:
            return CLUSTER_REPEAT_BIND_ERROR
        return DATA_EXIST

    def _associate_local_user_with_manager(self, username, manager_cluster_id, manager_username, public_key):
        user_map = UserMap(
            username=username,
            manager_cluster_id=manager_cluster_id,
            manager_username=manager_username,
            public_key=public_key,
        )
        self.session.add(user_map)

    def _validate_user(self, username: str, password: str) -> str:
        try:
            data = {"username": username, "password": password, "for_validate": True}
            query_url = f"http://{configuration.domain}{OAUTH2_LOGIN}"
            response_data = BaseResponse.get_response(method="Post", url=query_url, data=data, header=g.headers)
            response_status = response_data.get("label")
            if response_status != SUCCEED:
                return response_status

            user_role_assoc = self.session.query(UserRoleAssociation).filter_by(username=username).one_or_none()
            if not user_role_assoc:
                return NO_DATA
            role = self.session.query(Role).filter_by(role_id=user_role_assoc.role_id).one_or_none()
            if not role or role.role_type != constant.UserRoleType.ADMINISTRATOR:
                return PERMESSION_ERROR

        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR
        return SUCCEED

    def _associate_cluster_with_user(self, username: str, cluster_id: str, cluster_username: str, private_key: str):
        """Associate  cluster with user.

        Args:
            username (str): username
            local_cluster_id (str): local_cluster_id
        """
        user_cluster_assoc_id = str(uuid.uuid1()).replace('-', '')
        user_cluster_assoc = UserClusterAssociation(
            id=user_cluster_assoc_id,
            cluster_id=cluster_id,
            username=username,
            cluster_username=cluster_username,
            private_key=private_key,
        )
        self.session.add(user_cluster_assoc)

    def _synchronize_associate_cluster_with_user(
        self, username: str, cluster_id: str, cluster_username: str, private_key: str
    ):
        exist_user_cluster_assoc = (
            self.session.query(UserClusterAssociation).filter_by(cluster_id=cluster_id, username=username).one_or_none()
        )
        if exist_user_cluster_assoc:
            exist_user_cluster_assoc.cluster_username = cluster_username
            exist_user_cluster_assoc.private_key = private_key
            return
        self._associate_cluster_with_user(username, cluster_id, cluster_username, private_key)

    def _delete_user_managed_cluster_info(self, cluster_id: str):
        users_cluster_assoc = self.session.query(UserClusterAssociation).filter_by(cluster_id=cluster_id).count()
        if users_cluster_assoc == 0:
            LOGGER.debug(f"cluster info is not in user_cluster_assoc: {cluster_id}.")
        self.session.query(UserClusterAssociation).filter_by(cluster_id=cluster_id).delete(synchronize_session=False)
        permissions_subquery = self.session.query(Permission).filter(Permission.cluster_id == cluster_id).subquery()
        self.session.query(RolePermissionAssociation).filter(
            RolePermissionAssociation.permission_id == permissions_subquery.c.permission_id
        ).delete(synchronize_session=False)
        self.session.query(Permission).filter_by(cluster_id=cluster_id).delete(synchronize_session=False)
        return SUCCEED

    def get_user_managed_cluster_info(self, params) -> Tuple[str, list]:
        """Get user managed cluster info.

        Args:
            params (dict):
            {
                "cluster_ids":
            }

        Returns:
            Tuple[str, list]: status_code, cluster_infos
            e.g. SUCCEED, [
                            {
                                "cluster_id": "xxx",
                                "cluster_ip": "xxx",
                                "cluster_name": "xxx",
                                "subcluster": true,
                                "description": "xxx",
                            },
                           ]
        """
        cluster_ids = params.get("cluster_ids")
        managed_clusters = cache.get_user_clusters().keys()
        clusters = cache.clusters
        cluster_infos = []
        if cluster_ids and set(cluster_ids) > managed_clusters:
            LOGGER.error(
                f"get user managed cluster info failed, cannot find all query ids in managed_clusters '{managed_clusters}' for cluster_ids '{cluster_ids}'."
            )
            RedisProxy.redis_connect.delete(g.username + "_clusters")
            return PERMESSION_ERROR, []
        if managed_clusters > clusters.keys():
            LOGGER.error(
                f"get user managed cluster info failed, cannot find all ids in clusters '{clusters.keys()}' for managed_clusters '{managed_clusters}'."
            )
            RedisProxy.redis_connect.delete(g.username + "_clusters")
            RedisProxy.redis_connect.delete("clusters")
            return REDIS_CACHEINFO_ERROR, []
        for cluster_id, cluster_info in clusters.items():
            if cluster_ids and cluster_id not in cluster_ids:
                continue
            if managed_clusters and cluster_id not in managed_clusters:
                continue
            cluster_infos.append(cluster_info)
        return SUCCEED, cluster_infos

    def get_all_accounts_info(self) -> Tuple[str, list]:
        """Get all accounts info.

        Returns:
            Tuple[str, list]: status_code, users_info
        """
        try:
            users_info = []
            for user in self.session.query(UserInfo).all():
                users_info.append(dict(username=user.username, email=user.email))
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("get all accounts info failed.")
            return DATABASE_QUERY_ERROR, []
        return SUCCEED, users_info

    def get_user_cluster_key(self, params) -> Tuple[str, list]:
        """Get user cluster key info.
        When params is none, get all managed cluster key info and cache in redis.

        Args:
            params(dict):
            {
                "cluster_ids": ["cluster_id"]
            }

        Returns:
            Tuple[str, list]: status_code, cluster_key_info
        """
        cluster_ids = params.get("cluster_ids")
        managed_clusters = cache.get_user_clusters().keys()
        if cluster_ids and set(cluster_ids) > managed_clusters:
            no_managed_clusters = set(cluster_ids) - managed_clusters
            LOGGER.error(f"no permission to get cluster key: {no_managed_clusters}")
            return PERMESSION_ERROR, []
        query_cluster_ids = cluster_ids or managed_clusters
        get_status, cluster_key_info = self._get_user_cluster_key(g.username, query_cluster_ids)
        if get_status != SUCCEED:
            return get_status, []
        if not cluster_ids:
            self._cache_user_cluster_key(cluster_key_info)
        return SUCCEED, cluster_key_info

    def _get_user_cluster_key(self, username: str, cluster_ids: list) -> Tuple[str, list]:
        """Get user cluster key info.

        Args:
            username (str): username
            cluster_ids (list): cluster_ids

        Returns:
            Tuple[str, list]: status_code, cluster_key_infos
            e.g. SUCCEED, [
                            {
                                "cluster_id": "xxxx",
                                "cluster_username": "xxxx",
                                "private_key": "xxxx",
                                "public_key": "xxxx",
                            }
                          ]
        """
        try:
            cluster_key_infos = list()
            query_res = self.session.query(UserClusterAssociation).filter_by(username=username).all()
            for user_cluster_assoc in query_res:
                if cluster_ids and user_cluster_assoc.cluster_id not in cluster_ids:
                    continue
                user_map = self.session.query(UserMap).filter_by(username=user_cluster_assoc.username).one_or_none()
                public_key = ""
                if user_map:
                    public_key = user_map.public_key
                cluster_key_infos.append(
                    dict(
                        cluster_username=user_cluster_assoc.cluster_username,
                        cluster_id=user_cluster_assoc.cluster_id,
                        private_key=user_cluster_assoc.private_key,
                        public_key=public_key,
                    )
                )
        except sqlalchemy.orm.exc.MultipleResultsFound as error:
            LOGGER.error(error)
            LOGGER.error("get cluster key failed.")
            return REPEAT_DATA, []
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("get cluster key failed.")
            return DATABASE_QUERY_ERROR, []
        return SUCCEED, cluster_key_infos

    def _cache_user_cluster_key(self, clusters_key_info: list):
        """Cache cluster key in redis.

        Redis cache e.g.
        hashmap, key: "admin_rsa_key",    value: {
                                                "cluster_username": "cluster_username",
                                                "private_key": "private_key",
                                                "public_key": "public_key"
                                                 }
        """
        cache_dict = dict()
        for cluster_key_info in clusters_key_info:
            cache_dict[cluster_key_info["cluster_id"]] = json.dumps(
                {
                    "cluster_username": cluster_key_info["cluster_username"],
                    "private_key": cluster_key_info["private_key"],
                    "public_key": cluster_key_info["public_key"],
                }
            )
        if cache_dict:
            RedisProxy.redis_connect.hmset(g.username + "_rsa_key", cache_dict)

    def register_cluster(self, params) -> str:
        """Register cluster.

        Args:
            params (dict):
            {
                "cluster_name": "cluster1",
                "description": "Henan sub-cluster",
                "cluster_ip": "127.0.0.1",
                "cluster_username": "admin",
                "cluster_password": "changeme"
            }

        Returns:
            str: _description_
        """
        cluster_name = params.get('cluster_name')
        cluster_ip = params.get('cluster_ip')
        description = params.get('description')
        cluster_username = params.get('cluster_username')
        cluster_password = params.get('cluster_password')
        role_type = cache.user_role
        if not role_type or role_type != constant.UserRoleType.ADMINISTRATOR:
            return PERMESSION_ERROR
        manager_username = g.username
        private_key, public_key = generate_rsa_key_pair()
        private_key, public_key = get_private_key_pem_str(private_key), get_public_key_pem_str(public_key)

        manager_cluster_id = cache.location_cluster["cluster_id"]

        try:
            if self.session.query(UserMap).count() > 0:
                LOGGER.error(f"local cluster has been managed, cannot manage other cluster.")
                return CLUSTER_MANAGE_ERROR
            if not self._check_cluster_not_managed(cluster_ip, cluster_name):
                LOGGER.error(
                    f"register cluster failed, cluster info exists, please check: {cluster_ip}, {cluster_name}."
                )
                return CLUSTER_REPEAT_BIND_ERROR
            if not self._check_cluster_ip_vaild(cluster_ip):
                LOGGER.error(f"the cluster ip cannot be connected: {cluster_ip}")
                return IP_PING_FAILED
            bind_status, bind_infos = self._bind_with_manager_user_for_cluster(
                cluster_ip, cluster_username, cluster_password, manager_username, manager_cluster_id, public_key
            )
            if bind_status != SUCCEED:
                return bind_status
            binded_username, cluster_id = bind_infos["user_name"], bind_infos["cluster_id"]

            self._synchronize_associate_cluster_with_user(manager_username, cluster_id, binded_username, private_key)
            add_cluster_status = self._add_managed_cluster_info(cluster_id, cluster_name, description, cluster_ip)
            if add_cluster_status != SUCCEED:
                LOGGER.error("register cluster failed, add managed cluster info failed.")
                return add_cluster_status

            self.session.commit()
            self._start_cluster_synchronize_task(cluster_id, cluster_ip)
            LOGGER.debug(f"register cluster succeed: {cluster_ip}.")
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error(f"register cluster failed: {cluster_ip}.")
            self.session.rollback()
            return DATABASE_UPDATE_ERROR
        except celery.exceptions.CeleryError as error:
            LOGGER.error("Failed to start cluster synchronize task: %s", error)
            LOGGER.error(f"register cluster failed: {cluster_ip}.")
            self.session.rollback()
            return REDIS_SYNCHRONIZE_TASK_FAILED

        RedisProxy.redis_connect.delete(g.username + "_clusters")
        RedisProxy.redis_connect.delete(g.username + "_group_hosts")
        RedisProxy.redis_connect.delete(g.username + "_rsa_key")
        RedisProxy.redis_connect.delete("clusters")
        RedisProxy.redis_connect.delete("cluster_groups")
        return SUCCEED

    def _check_cluster_not_managed(self, cluster_ip: str, cluster_name: str):
        exist_clusters = cache.clusters
        for cluster_id, cluster in exist_clusters.items():
            if cluster["cluster_ip"] == cluster_ip:
                return False
            if cluster["cluster_name"] == cluster_name:
                return False
        return True

    def _check_cluster_ip_vaild(self, cluster_ip: str):
        response = subprocess.run(['ping', '-c', '1', cluster_ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if response.returncode == 0:
            return True
        return False

    def _bind_with_manager_user_for_cluster(
        self,
        cluster_ip: str,
        cluster_username: str,
        cluster_password: str,
        manager_username: str,
        manager_cluster_id: str,
        public_key: str,
    ) -> Tuple[str, dict]:
        data = {
            "username": cluster_username,
            "password": cluster_password,
            "manager_username": manager_username,
            "manager_cluster_id": manager_cluster_id,
            "public_key": public_key,
        }
        query_url = f"http://{cluster_ip}{constant.CLUSTER_USER_BIND}"
        response_data = BaseResponse.get_response(method="Post", url=query_url, data=data, header=g.headers)
        response_status = response_data.get("label")
        if response_status != SUCCEED:
            return response_status, None

        bind_infos: dict = response_data.get("data")
        return SUCCEED, bind_infos

    def _add_managed_cluster_info(self, cluster_id, cluster_name, description, cluster_ip):
        data = {
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "description": description,
            "cluster_ip": cluster_ip,
            "synchronous_state": TaskStatus.RUNNING,
        }
        query_url = f"http://{configuration.domain}{constant.CLUSTER_MANAGE}"
        response_data = BaseResponse.get_response(method="Post", url=query_url, data=data, header=g.headers)
        return response_data.get("label")

    def _update_managed_cluster_info(self, cluster_id, cluster_name, description, cluster_ip):
        data = {
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "description": description,
            "cluster_ip": cluster_ip,
        }
        query_url = f"http://{configuration.domain}{constant.CLUSTER_MANAGE}"
        response_data = BaseResponse.get_response(method="Put", url=query_url, data=data, header=g.headers)
        return response_data.get("label")

    def _start_cluster_synchronize_task(self, cluster_id, cluster_ip):
        local_cluster_ip = cache.location_cluster["cluster_ip"]
        celery_client.signature(
            "cluster_synchronize_task",
            kwargs=dict(cluster_id=cluster_id, cluster_ip=cluster_ip, local_cluster_ip=local_cluster_ip),
        ).apply_async()

    def delete_managed_cluster(self, params):
        cluster_id = params.get("cluster_id")
        managed_clusters = cache.get_user_clusters().keys()
        role_type = cache.user_role
        if not role_type or role_type != constant.UserRoleType.ADMINISTRATOR:
            return PERMESSION_ERROR
        if cluster_id == cache.location_cluster["cluster_id"]:
            LOGGER.error(f"cannot delete local cluster: {cluster_id}")
            return PERMESSION_ERROR
        if cluster_id not in managed_clusters:
            LOGGER.error(f"cluster is not managed: {cluster_id}.")
            return PERMESSION_ERROR
        try:
            manager_cluster_id = cache.location_cluster.get("cluster_id")
            managed_cluster = cache.clusters.get(cluster_id)
            managed_cluster_state = managed_cluster.get("synchronous_state", None)
            if managed_cluster_state not in [TaskStatus.SUCCEED, TaskStatus.FAIL]:
                LOGGER.error(
                    "cannot delete cluster, cluster is not in synchronize succeed or failed state, please wait..."
                )
                return TARGET_CLUSTER_DELETE_ERROR
            unbind_res = self._unbind_with_manager_user_for_cluster(cluster_id, manager_cluster_id)
            if unbind_res not in [SUCCEED, NO_MANAGED_DATA]:
                LOGGER.error("unbind manager user for cluster failed.")
                return unbind_res
            local_delete_res = self._delete_user_managed_cluster_info(cluster_id)
            if local_delete_res != SUCCEED:
                return local_delete_res

            self._stop_cluster_synchronize_task(cluster_id)
            self.session.commit()
            LOGGER.debug(f"unbind cluster with local succeed: {cluster_id}.")
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error(f"unbind cluster with local failed: {cluster_id}.")
            self.session.rollback()
            return DATABASE_UPDATE_ERROR
        except celery.exceptions.CeleryError as error:
            LOGGER.error("Failed to stop cluster synchronize task: %s", error)
            self.session.rollback()
            return REDIS_SYNCHRONIZE_TASK_FAILED

        self._delete_cluster_cache()

        return SUCCEED

    def _delete_cluster_cache(self):
        RedisProxy.redis_connect.delete("clusters")
        RedisProxy.redis_connect.delete("cluster_groups")
        if RedisProxy.redis_connect.keys("*_clusters"):
            RedisProxy.redis_connect.delete(*RedisProxy.redis_connect.keys("*_clusters"))
        if RedisProxy.redis_connect.keys("*_group_hosts"):
            RedisProxy.redis_connect.delete(*RedisProxy.redis_connect.keys("*_group_hosts"))
        if RedisProxy.redis_connect.keys("*_rsa_key"):
            RedisProxy.redis_connect.delete(*RedisProxy.redis_connect.keys("*_rsa_key"))

    def _unbind_with_manager_user_for_cluster(self, cluster_id: str, manager_cluster_id: str):
        clusters_private_key = cache.get_user_cluster_private_key or dict()
        sub_cluster_private_key = clusters_private_key.get(cluster_id, None)
        if not sub_cluster_private_key:
            LOGGER.error(f"cannot get subcluster private key: {cluster_id}")
            return REDIS_CACHEINFO_ERROR
        clusters_info = cache.clusters or dict()
        sub_cluster_info = clusters_info.get(cluster_id, None)
        if not sub_cluster_info:
            LOGGER.error(f"cannot get subcluster info: {cluster_id}")
            return REDIS_CACHEINFO_ERROR
        sub_cluster_username = sub_cluster_private_key["cluster_username"]
        sub_cluster_ip = sub_cluster_info["cluster_ip"]
        data = {"cluster_id": manager_cluster_id, "cluster_username": sub_cluster_username}
        private_key = load_private_key(sub_cluster_private_key["private_key"])
        signature = sign_data(data, private_key)
        data = {"cluster_id": manager_cluster_id, "cluster_username": sub_cluster_username, "signature": signature}
        query_url = f"http://{sub_cluster_ip}{constant.CLUSTER_MANAGED_CANCEL}"
        response_data = BaseResponse.get_response(method="Delete", url=query_url, data=data, header=g.headers)
        return response_data.get("label")

    def _stop_cluster_synchronize_task(self, cluster_id):
        celery_client.signature(
            "cluster_synchronize_cancel_task",
            kwargs=dict(cluster_id=cluster_id),
        ).apply_async()

    def cluster_synchronize(self, cluster_id: str, cluster_ip: str):
        role_type = cache.user_role
        if not role_type or role_type != constant.UserRoleType.ADMINISTRATOR:
            return PERMESSION_ERROR
        managed_clusters = cache.get_user_clusters().keys()
        if cluster_id not in managed_clusters:
            LOGGER.error(f"cluster is not managed: {cluster_id}.")
            return NO_DATA
        if cluster_id not in managed_clusters or cluster_id == cache.location_cluster["cluster_id"]:
            LOGGER.error(f"nonsupport to synchronize local cluster: {cluster_id}.")
            return SYNCHRONIZE_ERROR
        self._update_cluster_synchronize_info(cluster_id, TaskStatus.RUNNING)
        try:
            self._start_cluster_synchronize_task(cluster_id, cluster_ip)
        except celery.exceptions.CeleryError as error:
            self._update_cluster_synchronize_info(cluster_id, TaskStatus.FAIL)
            LOGGER.error("Failed to stop cluster synchronize task: %s", error)
            self.session.rollback()
            return REDIS_SYNCHRONIZE_TASK_FAILED

        return SUCCEED

    def _update_cluster_synchronize_info(self, cluster_id, synchronous_state):
        cluster = cache.clusters.get(cluster_id)
        data = {
            "cluster_id": cluster_id,
            "cluster_name": cluster["cluster_name"],
            "description": cluster["description"],
            "cluster_ip": cluster["cluster_ip"],
            "synchronous_state": synchronous_state,
        }
        query_url = f"http://{configuration.domain}{constant.CLUSTER_MANAGE}"
        response_data = BaseResponse.get_response(method="Put", url=query_url, data=data, header=g.headers)
        return response_data.get("label")
