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
from sqlalchemy import Column
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.sqltypes import String

Base = declarative_base()


class Route(Base):
    """
    web route table, each route_id is a record stored in Permission table.
    """

    __tablename__ = "route"

    route_id = Column(String(36), primary_key=True)
    route = Column(String(40), nullable=False)
    description = Column(String(60))


class Role(Base):
    """
    role table
    """

    __tablename__ = "role"

    role_id = Column(String(36), primary_key=True)
    # right now, role type could be normal or administrator
    role_type = Column(String(15))


class Permission(Base):
    """
    permission table
    """

    __tablename__ = "permission"

    permission_id = Column(String(36), primary_key=True)
    # right now, permission type could be host_group or route
    type = Column(String(15))
    object_id = Column(String(36), nullable=False)
    cluster_id = Column(String(36), nullable=False)


class UserRoleAssociation(Base):
    """
    User role match table.
    """

    __tablename__ = "user_role_association"

    username = Column(String(36), primary_key=True)
    role_id = Column(String(36), primary_key=True)


class RolePermissionAssociation(Base):
    """
    User role match table.
    """

    __tablename__ = "role_permission_association"

    role_id = Column(String(36), primary_key=True)
    permission_id = Column(String(36), primary_key=True)


class UserClusterAssociation(Base):
    """
    User cluster tables' association table, record user and cluster's matching relationship
    """

    __tablename__ = "user_cluster_association"

    id = Column(String(36), primary_key=True)
    username = Column(String(36))
    cluster_id = Column(String(36))
    cluster_username = Column(String(36), nullable=False)
    private_key = Column(String(4096))


class UserMap(Base):
    __tablename__ = "user_map"

    username = Column(String(36), primary_key=True)
    manager_cluster_id = Column(String(36))
    manager_username = Column(String(36), primary_key=True)
    public_key = Column(String(4096))


class UserToken(Base):
    """
    User token from oauth2 and local.
    """

    __tablename__ = "user_token"

    username = Column(String(36), primary_key=True)
    generated_time = Column(String(20))
    access_token = Column(String(255))
    refresh_token = Column(String(255))
    local_access_token = Column(String(255))


class UserInfo(Base):
    """
    User info.
    """

    __tablename__ = "user_info"

    username = Column(String(36), primary_key=True)
    email = Column(String(40))
