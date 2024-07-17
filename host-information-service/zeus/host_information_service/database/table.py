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

from sqlalchemy import Column
from sqlalchemy.sql.sqltypes import Boolean, Integer, String
from vulcanus.database import Base


class Host(Base):  # pylint: disable=R0903
    """
    Host table
    """

    __tablename__ = "host"

    host_id = Column(String(36), primary_key=True)
    host_name = Column(String(50), nullable=False)
    host_ip = Column(String(16), nullable=False)
    management = Column(Boolean, nullable=False)
    host_group_name = Column(String(20))
    repo_id = Column(String(36))
    last_scan = Column(Integer)
    scene = Column(String(255))
    os_version = Column(String(40))
    ssh_user = Column(String(40), default="root")
    ssh_port = Column(Integer(), default=22)
    pkey = Column(String(4096))
    status = Column(Integer(), default=2)
    reboot = Column(Boolean, nullable=False, default=False)
    host_group_id = Column(String(36))
    cluster_id = Column(String(36))
    ext_props = Column(String(1024))


class HostGroup(Base):
    """
    Host group table
    """

    __tablename__ = "host_group"

    host_group_id = Column(String(36), primary_key=True)
    host_group_name = Column(String(20))
    cluster_id = Column(String(36))
    description = Column(String(60))


class Cluster(Base):
    """
    Cluster table
    """

    __tablename__ = "cluster"

    cluster_id = Column(String(36), primary_key=True)
    cluster_name = Column(String(20))
    description = Column(String(60))
    subcluster = Column(Boolean, default=False)
    backend_ip = Column(String(16))
    public_key = Column(String(4096))
    private_key = Column(String(4096))
    synchronous_state = Column(String(20))
