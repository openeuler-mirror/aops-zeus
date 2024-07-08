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
import uuid
from typing import Tuple

import sqlalchemy
from sqlalchemy import func
from vulcanus.cache import RedisCacheManage
from vulcanus.database.helper import sort_and_page
from vulcanus.database.proxy import MysqlProxy, RedisProxy
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp.state import (
    DATA_DEPENDENCY_ERROR,
    DATA_EXIST,
    DATABASE_DELETE_ERROR,
    DATABASE_INSERT_ERROR,
    DATABASE_QUERY_ERROR,
    NO_DATA,
    PARAM_ERROR,
    SUCCEED,
)

from zeus.host_information_service.app import cache
from zeus.host_information_service.app.serialize.host_group import GetHostGroupPage_ResponseSchema
from zeus.host_information_service.database import Host, HostGroup
from zeus.host_information_service.database.table import Cluster


class HostGroupProxy(MysqlProxy):
    """
    HostGroup related table operation
    """

    def get_host_groups(self, page_filter):
        """
        Get host group from table

        Args:
            data(dict): parameter, e.g.
                {
                    "cluster_ids": ["uuid"],
                    "sort": "host_group_name",
                    "direction": "asc",
                    "page": 1,
                    "per_page": 20,
                }

        Returns:
            int: status code
            dict: group infos
        """
        host_groups = None
        try:
            host_groups = self._query_host_groups_page(page_filter)
            LOGGER.debug("query host group succeed")
            return SUCCEED, host_groups
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("query host group fail")
            return DATABASE_QUERY_ERROR, host_groups

    def _query_host_groups_page(self, page_filter):
        result = {"total_count": 0, "total_page": 0, "host_group_infos": []}
        groups = cache.get_user_group_hosts()
        filters = {HostGroup.host_group_id.in_(list(groups.keys()))}
        if page_filter["cluster_ids"]:
            filters.add(HostGroup.cluster_id.in_(page_filter["cluster_ids"]))
        host_groups_query = (
            self.session.query(
                HostGroup.host_group_id,
                HostGroup.host_group_name,
                HostGroup.description,
                Cluster.cluster_id,
                Cluster.cluster_name,
                func.count(Host.host_id).label("host_count"),
            )
            .outerjoin(Host, HostGroup.host_group_id == Host.host_group_id)
            .outerjoin(Cluster, HostGroup.cluster_id == Cluster.cluster_id)
            .filter(*filters)
            .group_by(HostGroup.host_group_id)
        )
        result["total_count"] = host_groups_query.count()
        if not result["total_count"]:
            return result
        sort_column = self._get_group_column(page_filter["sort"])
        processed_query, total_page = sort_and_page(
            host_groups_query, sort_column, page_filter["direction"], page_filter["per_page"], page_filter["page"]
        )
        result['total_page'] = total_page
        result['host_group_infos'] = GetHostGroupPage_ResponseSchema(many=True).dump(processed_query.all())
        return result

    @staticmethod
    def _get_group_column(column_name):
        if not column_name:
            return None
        if column_name == "host_count":
            return func.count(Host.host_id)
        return getattr(HostGroup, column_name)

    def add_host_group(self, data) -> str:
        """
        Add host group to table

        Args:
            data(dict): parameter, e.g.
                {
                    "host_group_name": "group1",
                    "description": "des",
                    "cluster_id": "uuid"
                }
        """
        try:
            if not self.session.query(Cluster.cluster_id).filter(Cluster.cluster_id == data['cluster_id']).first():
                return PARAM_ERROR
            if (
                self.session.query(HostGroup)
                .filter(
                    HostGroup.host_group_name == data['host_group_name'], HostGroup.cluster_id == data['cluster_id']
                )
                .first()
            ):
                return DATA_EXIST
            self.session.add(HostGroup(**data, host_group_id=str(uuid.uuid4())))
            self.session.commit()
            LOGGER.info("add host group [%s] succeed", data['host_group_name'])
            RedisProxy.redis_connect.delete(RedisCacheManage.CLUSTER_GROUPS)
            RedisProxy.redis_connect.delete(cache.user_groups_key)
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            self.session.rollback()
            LOGGER.error("add host group [%s] fail", data['host_group_name'])
            return DATABASE_INSERT_ERROR

    def delete_host_group(self, host_group_id: int) -> str:
        """
        Delete host group from table

        Args:
            host_group_id (int):

        Returns:
            str: status code
        """
        try:
            host_group = self.session.query(HostGroup).filter(HostGroup.host_group_id == host_group_id).first()
            if not host_group:
                return SUCCEED
            host_count = self.session.query(Host).filter(Host.host_group_id == host_group_id).count()
            if host_count:
                LOGGER.error("host group %s delete fail", host_group_id)
                return DATA_DEPENDENCY_ERROR

            self.session.delete(host_group)
            self.session.commit()

            LOGGER.info("host group %s delete succeed", host_group_id)
            RedisProxy.redis_connect.delete(RedisCacheManage.CLUSTER_GROUPS)
            RedisProxy.redis_connect.delete(RedisCacheManage.GROUPS_HOSTS)
            RedisProxy.redis_connect.delete(*RedisProxy.redis_connect.keys("*_group_hosts"))
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("delete host group %s fail", host_group_id)
            self.session.rollback()
            return DATABASE_DELETE_ERROR

    def get_host_group_info(self, host_group_id: str) -> Tuple[str, HostGroup]:

        try:
            host_group = (
                self.session.query(
                    HostGroup.cluster_id,
                    Cluster.cluster_name,
                    HostGroup.host_group_id,
                    HostGroup.host_group_name,
                    HostGroup.description,
                )
                .outerjoin(Cluster, Cluster.cluster_id == HostGroup.cluster_id)
                .filter(HostGroup.host_group_id == host_group_id)
                .first()
            )
            if not host_group:
                return NO_DATA, None

            return SUCCEED, host_group
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR, None

    def get_all_host_groups_map(self) -> Tuple[str, HostGroup]:
        try:
            hosts = self.session.query(Host.host_group_id, Host.host_id).filter(Host.host_group_id != None).all()
            if not hosts:
                return NO_DATA, None
            hosts_groups = dict()
            for host in hosts:
                if host.host_group_id in hosts_groups:
                    hosts_groups[host.host_group_id].append(host.host_id)
                else:
                    hosts_groups[host.host_group_id] = [host.host_id]

            return SUCCEED, hosts_groups
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR, None
