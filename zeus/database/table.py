#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2023. All rights reserved.
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
Description: mysql tables
"""
from sqlalchemy import Column, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Boolean, Integer, String
from werkzeug.security import check_password_hash, generate_password_hash

from vulcanus.database.helper import create_tables

Base = declarative_base()


class MyBase:  # pylint: disable=R0903
    """
    Class that provide helper function
    """

    def to_dict(self):
        """
        Transfer query data to dict

        Returns:
            dict
        """
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}  # pylint: disable=E1101


class Host(Base, MyBase):  # pylint: disable=R0903
    """
    Host table
    """

    __tablename__ = "host"

    host_id = Column(Integer(), primary_key=True, autoincrement=True)
    host_name = Column(String(50), nullable=False)
    host_ip = Column(String(16), nullable=False)
    management = Column(Boolean, nullable=False)
    host_group_name = Column(String(20))
    repo_name = Column(String(20))
    last_scan = Column(Integer)
    scene = Column(String(255))
    os_version = Column(String(40))
    ssh_user = Column(String(40), default="root")
    ssh_port = Column(Integer(), default=22)
    pkey = Column(String(4096))
    status = Column(Integer(), default=2)

    user = Column(String(40), ForeignKey('user.username'))
    host_group_id = Column(Integer, ForeignKey('host_group.host_group_id'))

    host_group = relationship('HostGroup', back_populates='hosts')
    owner = relationship('User', back_populates='hosts')

    def __eq__(self, o):
        return self.user == o.user and (
            self.host_name == o.host_name or f"{self.host_ip}{self.ssh_port}" == f"{o.host_ip}{o.ssh_port}"
        )


class HostGroup(Base, MyBase):
    """
    Host group table
    """

    __tablename__ = "host_group"

    host_group_id = Column(Integer, autoincrement=True, primary_key=True)
    host_group_name = Column(String(20))
    description = Column(String(60))
    username = Column(String(40), ForeignKey('user.username'))

    user = relationship('User', back_populates='host_groups')
    hosts = relationship('Host', back_populates='host_group')

    def __eq__(self, o):
        return self.username == o.username and self.host_group_name == o.host_group_name


class User(Base, MyBase):  # pylint: disable=R0903
    """
    User Table
    """

    __tablename__ = "user"

    username = Column(String(40), primary_key=True)
    password = Column(String(255), nullable=False)
    email = Column(String(40))

    host_groups = relationship('HostGroup', order_by=HostGroup.host_group_name, back_populates='user')
    hosts = relationship('Host', back_populates='owner')

    @staticmethod
    def hash_password(password):
        return generate_password_hash(password)

    @staticmethod
    def check_hash_password(raw_password, password):
        return check_password_hash(raw_password, password)


class Auth(Base, MyBase):
    """
    Auth table
    """

    __tablename__ = "auth"

    auth_id = Column(String(32), primary_key=True)
    auth_account = Column(String(20), nullable=False)
    email = Column(String(50))
    nick_name = Column(String(20))
    auth_type = Column(String(20))
    username = Column(String(40), ForeignKey('user.username'))


def create_utils_tables(base, engine):
    """
    Create basic database tables, e.g. user, host, hostgroup

    Args:
        base (instance): sqlalchemy.ext.declarative.declarative_base(),
                         actually a registry instance
        engine (instance): _engine.Engine instance
    """
    # pay attention, the sequence of list is important. Base table need to be listed first.
    tables = [User, HostGroup, Host, Auth]
    tables_objects = [base.metadata.tables[table.__tablename__] for table in tables]
    create_tables(base, engine, tables=tables_objects)
