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
import random
import string
import uuid

import sqlalchemy
from flask import g
from sqlalchemy import func
from vulcanus.conf.constant import ADMIN_USER, DISTRIBUTE, PERMISSION_BIND, PERMISSIONS, UserRoleType
from vulcanus.database.helper import sort_and_page
from vulcanus.database.proxy import MysqlProxy, RedisProxy
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp.state import DATABASE_DELETE_ERROR, DATABASE_INSERT_ERROR, DATABASE_QUERY_ERROR, SUCCEED
from vulcanus.restful.response import BaseResponse
from vulcanus.rsa import generate_rsa_key_pair, get_private_key_pem_str, get_public_key_pem_str

from zeus.user_access_service.app import cache
from zeus.user_access_service.app.serialize.permission import GetAccountPage_ResponseSchema
from zeus.user_access_service.app.settings import configuration
from zeus.user_access_service.database.table import (
    Permission,
    Role,
    RolePermissionAssociation,
    User,
    UserClusterAssociation,
    UserMap,
    UserRoleAssociation,
)


class PermissionProxy(MysqlProxy):
    """
    Permission proxy
    """

    def get_accounts(self, page_filter):
        """
        Get accounts by page

        Args:
            data(dict): parameter, e.g.
                {
                    "username": "xxx",
                    "page": 1,
                    "per_page": 10
                }

        Returns:
            str: status code
            dict: accounts infos
        """
        accounts = None
        try:
            accounts = self._query_account_page(page_filter)
            LOGGER.debug("query accounts page succeed")
            return SUCCEED, accounts
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("query accounts page fail")
            return DATABASE_QUERY_ERROR, accounts

    def _query_account_page(self, page_filter):
        result = {"total_count": 0, "total_page": 0, "result": []}
        if cache.user_role != UserRoleType.ADMINISTRATOR:
            return result
        filters = {User.managed == False}
        if page_filter["username"]:
            filters.add(User.username.like("%{}%".format(page_filter["username"])))

        cluster_subquery = (
            self.session.query(
                UserClusterAssociation.username,
                func.count(UserClusterAssociation.cluster_id).label("clusters_num"),
            )
            .group_by(UserClusterAssociation.username)
            .distinct()
            .subquery()
        )
        role_subquery = (
            self.session.query(UserRoleAssociation.username, Role.role_type)
            .outerjoin(Role, Role.role_id == UserRoleAssociation.role_id)
            .subquery()
        )
        filters.add(role_subquery.c.role_type != UserRoleType.ADMINISTRATOR)
        accounts_query = (
            self.session.query(
                User.username,
                User.email,
                role_subquery.c.role_type,
                func.coalesce(cluster_subquery.c.clusters_num, 0).label("clusters_num"),
            )
            .outerjoin(cluster_subquery, cluster_subquery.c.username == User.username)
            .outerjoin(role_subquery, role_subquery.c.username == User.username)
            .filter(*filters)
        )
        result["total_count"] = accounts_query.count()
        if not result["total_count"]:
            return result
        processed_query, total_page = sort_and_page(
            accounts_query, None, None, page_filter["per_page"], page_filter["page"]
        )
        result['total_page'] = total_page
        result['result'] = GetAccountPage_ResponseSchema(many=True).dump(processed_query.all())
        return result

    def get_permissions(self, username, cluster_id=None):
        """ """
        try:
            role = cache.user_role
            if role == UserRoleType.ADMINISTRATOR and (username == ADMIN_USER or not username):
                permissions = self._query_all_permissions()
            else:
                permissions = self._query_permissions(username, cluster_id)
            return SUCCEED, permissions
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("query permissions fail")
            return DATABASE_QUERY_ERROR, None

    def _query_all_permissions(self):
        """
        Query admin all permissions
        """
        cluster_groups = cache.cluster_groups
        all_permissions = []
        for cluster_id, cluster in cache.clusters.items():
            all_permissions.append(
                {
                    "cluster_id": cluster_id,
                    "cluster_name": cluster["cluster_name"],
                    "host_groups": (
                        [
                            dict(host_group_id=host_group_id, host_group_name=group_name)
                            for host_groups in cluster_groups[cluster_id]
                            for host_group_id, group_name in host_groups.items()
                        ]
                        if cluster_id in cluster_groups
                        else []
                    ),
                }
            )
        return all_permissions

    def _query_permissions(self, username, cluster_id=None):
        """
        Query user permissions

        Args:
            username (str): username
            cluster_id (str): cluster id
        """
        role_ids_subquery = (
            self.session.query(UserRoleAssociation.role_id).filter(UserRoleAssociation.username == username).subquery()
        )
        permissions_ids_subquery = (
            self.session.query(RolePermissionAssociation.permission_id)
            .filter(RolePermissionAssociation.role_id == role_ids_subquery.c.role_id)
            .subquery()
        )
        filters = set()
        if cluster_id:
            filters.add(Permission.cluster_id == cluster_id)
        user_clusters_groups = (
            self.session.query(Permission.cluster_id, Permission.object_id)
            .join(permissions_ids_subquery, Permission.permission_id == permissions_ids_subquery.c.permission_id)
            .filter(*filters)
            .all()
        )
        if not user_clusters_groups:
            return None
        clusters = cache.clusters
        cluster_groups = cache.cluster_groups
        permission_cluster_groups = {permission.object_id: permission.cluster_id for permission in user_clusters_groups}
        permissions = []
        for cluster_id in set(permission_cluster_groups.values()):
            cluster = clusters.get(cluster_id)
            host_groups = []
            for _host_groups in cluster_groups.get(cluster_id, []):
                for host_group_id, group_name in _host_groups.items():
                    if host_group_id not in permission_cluster_groups:
                        continue
                    host_groups.append(dict(host_group_id=host_group_id, host_group_name=group_name))
            permissions.append(
                {"cluster_id": cluster_id, "cluster_name": cluster["cluster_name"], "host_groups": host_groups}
            )
        return permissions

    def set_permissions(self, username, permissions):
        """
        Set permissions by username and permissions
        """
        try:
            status_code = self._set_permissions(username, permissions)
            if status_code == SUCCEED:
                self._delete_user_cache(username)
            return status_code
        except sqlalchemy.exc.SQLAlchemyError as error:
            self.session.rollback()
            LOGGER.error(error)
            LOGGER.error("set permissions fail")
            return DATABASE_INSERT_ERROR

    def _location_cluster_permissions(self, username, host_groups: dict, cluster_users):
        """
        Set location cluster permissions

        Args:
            username (str): username
            host_groups (list): host groups,e.g ["host_group_id1", "host_group_id2"]
            cluster_users (dict): cluster users,e.g
            {
                "cluster_id1": {
                    "private_key": "private_key1",
                    "cluster_username": "cluster_username1"
                }
            }
        """
        user_cluster_associations = (
            [
                UserClusterAssociation(
                    id=str(uuid.uuid4()),
                    username=username,
                    cluster_username=username,
                    cluster_id=cache.location_cluster["cluster_id"],
                    private_key=None,
                )
            ]
            if host_groups and cache.location_cluster["cluster_id"] in host_groups
            else []
        )
        # delete permissions
        self.session.query(UserClusterAssociation).filter(UserClusterAssociation.username == username).delete(
            synchronize_session=False
        )
        if cluster_users:
            for cluster_id, user_cluster in cluster_users.items():
                user_cluster_associations.append(
                    UserClusterAssociation(
                        id=str(uuid.uuid4()),
                        username=username,
                        cluster_id=cluster_id,
                        private_key=user_cluster["private_key"],
                        cluster_username=user_cluster["cluster_username"],
                    )
                )
        if user_cluster_associations:
            self.session.bulk_save_objects(user_cluster_associations)

        user_role = (
            self.session.query(UserRoleAssociation.role_id).filter(UserRoleAssociation.username == username).first()
        )
        wait_delete_permissions = (
            self.session.query(RolePermissionAssociation)
            .filter(RolePermissionAssociation.role_id == user_role.role_id)
            .all()
        )
        if wait_delete_permissions:
            delete_permission_ids = [role_permission.permission_id for role_permission in wait_delete_permissions]
            self.session.query(Permission).filter(Permission.permission_id.in_(delete_permission_ids)).delete(
                synchronize_session=False
            )
            self.session.query(RolePermissionAssociation).filter(
                RolePermissionAssociation.role_id == user_role.role_id
            ).delete(synchronize_session=False)

        permission_ids = []
        permissions = []
        if host_groups:
            for cluster_id, host_group_ids in host_groups.items():
                for host_group_id in host_group_ids:
                    permission_id = str(uuid.uuid4())
                    permissions.append(
                        Permission(
                            permission_id=permission_id,
                            object_id=host_group_id,
                            cluster_id=cluster_id,
                            type="host_group",
                        )
                    )
                    permission_ids.append(permission_id)
            self.session.bulk_save_objects(permissions)

        if permission_ids:
            self.session.bulk_save_objects(
                [
                    RolePermissionAssociation(role_id=user_role.role_id, permission_id=permission_id)
                    for permission_id in permission_ids
                ]
            )
        self.session.commit()

    def _set_permissions(self, username, permissions):
        """

        Args:
            username (str): username
            permissions (list): permissions,e.g
                [
                    {
                        "cluster_id": "xxxx",
                        "host_group": [
                            "host_group1",
                            "host_group2"
                        ]
                    }
                ]
        """

        if not self._remove_permissions(username):
            return DATABASE_DELETE_ERROR
        if not permissions:
            self._location_cluster_permissions(username, None, None)
            return SUCCEED

        cluster_permissions = {permission["cluster_id"]: generate_rsa_key_pair() for permission in permissions}
        distribute_body = dict()
        host_groups = dict()
        for permission in permissions:
            host_groups[permission["cluster_id"]] = permission["host_group"]
            if permission["cluster_id"] == cache.location_cluster["cluster_id"]:
                continue
            distribute_body[permission["cluster_id"]] = {
                "cluster_id": cache.location_cluster["cluster_id"],
                "manager_username": username,
                "host_group": permission["host_group"],
                "public_key": get_public_key_pem_str(cluster_permissions[permission["cluster_id"]][-1]),
            }
        cluster_users = dict()
        # Permissions for binding subsets
        if distribute_body:
            response = BaseResponse.get_response(
                method="post",
                url="http://" + configuration.domain + DISTRIBUTE + PERMISSION_BIND,
                data=distribute_body,
                header=g.headers,
            )
            response_data = response.get("data") or dict()
            cluster_users = {
                cluster_id: dict(
                    cluster_username=bind_users["data"],
                    private_key=get_private_key_pem_str(cluster_permissions[cluster_id][0]),
                )
                for cluster_id, bind_users in response_data.items()
                if bind_users["label"] == SUCCEED
            }
        for cluster_id in list(host_groups.keys()):
            if cluster_id != cache.location_cluster["cluster_id"] and cluster_id not in cluster_users:
                del host_groups[cluster_id]
        self._location_cluster_permissions(username, host_groups, cluster_users)
        return SUCCEED

    def _remove_permissions(self, username):
        cancel_permissions_cluster_ids = (
            self.session.query(UserClusterAssociation.cluster_id)
            .filter(
                UserClusterAssociation.username == username,
                UserClusterAssociation.cluster_id != cache.location_cluster["cluster_id"],
            )
            .all()
        )
        if not cancel_permissions_cluster_ids:
            return True

        body = {
            cluster.cluster_id: dict(manager_username=username, cluster_id=cache.location_cluster["cluster_id"])
            for cluster in cancel_permissions_cluster_ids
        }
        response = BaseResponse.get_response(
            method="delete",
            url="http://" + configuration.domain + DISTRIBUTE + PERMISSIONS,
            data=body,
            header=g.headers,
        )
        if response["label"] != SUCCEED:
            return False

        response_data = response.get("data") or dict()
        if all(delete_result["label"] == SUCCEED for _, delete_result in response_data.items()):
            return True

        return False

    def bind_permissions(self, bind_permissions):
        """
        bind user permissions
        """
        try:
            cluster_username = self._bind_permission(bind_permissions)
            return SUCCEED, cluster_username
        except sqlalchemy.exc.SQLAlchemyError as error:
            self.session.rollback()
            LOGGER.error(error)
            LOGGER.error("set permissions fail")
            return DATABASE_INSERT_ERROR, None

    def _bind_permission(self, permissions):
        """

        Args:
            {
                "cluster_id": "xxx",
                "manager_username": "user1",
                "host_group": ["host_group1", "host_group2"],
                "public_key": "xxx"
            }
        """
        user_map = (
            self.session.query(UserMap)
            .filter(
                UserMap.manager_username == permissions["manager_username"],
                UserMap.manager_cluster_id == permissions["cluster_id"],
            )
            .first()
        )
        if user_map:
            cluster_username = user_map.username
            user_role = (
                self.session.query(UserRoleAssociation.role_id)
                .filter(UserRoleAssociation.username == cluster_username)
                .first()
            )
            self.session.query(UserMap).filter(
                UserMap.manager_username == permissions["manager_username"],
                UserMap.manager_cluster_id == permissions["cluster_id"],
            ).update({"public_key": permissions["public_key"]}, synchronize_session=False)
            role_id = user_role.role_id
        else:
            cluster_username = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(20))
            self.session.add(
                UserMap(
                    username=cluster_username,
                    manager_username=permissions["manager_username"],
                    manager_cluster_id=permissions["cluster_id"],
                    public_key=permissions["public_key"],
                )
            )
            self.session.add(
                User(username=cluster_username, password=User.hash_password(cluster_username), managed=True)
            )
            role_id = str(uuid.uuid4())
            self.session.add(Role(role_id=role_id, role_type=UserRoleType.NORMAL))
            self.session.add(UserRoleAssociation(username=cluster_username, role_id=role_id))
            self.session.add(
                UserClusterAssociation(
                    username=cluster_username,
                    cluster_id=cache.location_cluster["cluster_id"],
                    cluster_username=cluster_username,
                    id=str(uuid.uuid4()),
                    private_key="",
                )
            )

        wait_insert_permissions = []
        role_permissions = []
        for host_group_id in permissions["host_group"]:
            permission_id = str(uuid.uuid4())
            wait_insert_permissions.append(
                Permission(
                    permission_id=permission_id,
                    object_id=host_group_id,
                    cluster_id=cache.location_cluster["cluster_id"],
                    type="host_group",
                )
            )
            role_permissions.append(RolePermissionAssociation(role_id=role_id, permission_id=permission_id))

        self.session.bulk_save_objects(wait_insert_permissions)
        if role_permissions:
            self.session.bulk_save_objects(role_permissions)

        self.session.commit()
        self._delete_user_cache(cluster_username)
        return cluster_username

    def _delete_user_cache(self, username):
        RedisProxy.redis_connect.delete(username + "_clusters")
        RedisProxy.redis_connect.delete(username + "_group_hosts")
        RedisProxy.redis_connect.delete(username + "_role")
        RedisProxy.redis_connect.delete(username + "_rsa_key")

    def delete_permissions(self, username, cluster_id):
        """
        delete user permissions
        """
        try:
            status_code = self._delete_permissions(username, cluster_id)
            return status_code
        except sqlalchemy.exc.SQLAlchemyError as error:
            self.session.rollback()
            LOGGER.error(error)
            LOGGER.error("Delete permissions fail")
            return DATABASE_DELETE_ERROR

    def _delete_permissions(self, username, cluster_id):
        """ """
        user_map = (
            self.session.query(UserMap)
            .filter(UserMap.manager_username == username, UserMap.manager_cluster_id == cluster_id)
            .first()
        )
        if not user_map:
            return SUCCEED

        cluster_user = user_map.username
        self.session.query(User).filter(User.username == cluster_user).delete(synchronize_session=False)
        self.session.query(UserMap).filter(
            UserMap.username == cluster_user, UserMap.manager_cluster_id == cluster_id
        ).delete(synchronize_session=False)

        self.session.query(UserClusterAssociation).filter(
            UserClusterAssociation.username == cluster_user, cluster_id == cache.location_cluster["cluster_id"]
        ).delete(synchronize_session=False)
        user_role_association = (
            self.session.query(UserRoleAssociation).filter(UserRoleAssociation.username == cluster_user).first()
        )
        if not user_role_association:
            return SUCCEED
        self.session.query(UserRoleAssociation).filter(UserRoleAssociation.username == cluster_user).delete(
            synchronize_session=False
        )
        self.session.query(Role).filter(Role.role_id == user_role_association.role_id).delete(synchronize_session=False)
        role_permission_ids = (
            self.session.query(RolePermissionAssociation.permission_id)
            .filter(RolePermissionAssociation.role_id == user_role_association.role_id)
            .all()
        )
        if role_permission_ids:
            role_permission_id_list = [role_permission.permission_id for role_permission in role_permission_ids]
            self.session.query(Permission).filter(Permission.permission_id.in_(role_permission_id_list)).delete(
                synchronize_session=False
            )
            self.session.query(RolePermissionAssociation).filter(
                RolePermissionAssociation.role_id == user_role_association.role_id
            ).delete(synchronize_session=False)

        self._delete_user_cache(cluster_user)
        self.session.commit()
        return SUCCEED
