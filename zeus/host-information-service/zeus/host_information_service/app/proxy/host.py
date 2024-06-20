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
from typing import Any, Dict, List, Optional, Tuple

import sqlalchemy
from sqlalchemy import or_
from vulcanus.cache import RedisCacheManage
from vulcanus.database.helper import sort_and_page
from vulcanus.database.proxy import MysqlProxy, RedisProxy
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp.state import (
    DATA_EXIST,
    DATABASE_DELETE_ERROR,
    DATABASE_INSERT_ERROR,
    DATABASE_QUERY_ERROR,
    DATABASE_UPDATE_ERROR,
    NO_DATA,
    PARAM_ERROR,
    SUCCEED,
)

from zeus.host_information_service.app import cache
from zeus.host_information_service.app.serialize.host import GetHostsPage_ResponseSchema, HostsInfo_ResponseSchema
from zeus.host_information_service.database import Host, HostGroup
from zeus.host_information_service.database.table import Cluster


class HostProxy(MysqlProxy):
    """
    Host related table operation
    """

    def _add_host_handler(self, host_info: dict) -> Tuple[str, Any]:
        host_group = self.session.query(HostGroup).filter(HostGroup.host_group_id == host_info["host_group_id"]).first()
        if not host_group:
            return PARAM_ERROR, None

        if (
            self.session.query(Host)
            .filter(
                Host.host_ip == host_info["host_ip"],
                Host.ssh_port == host_info["ssh_port"],
                Host.cluster_id == host_group.cluster_id,
            )
            .first()
        ):
            return DATA_EXIST, None

        return SUCCEED, host_group

    def add_host(self, host_info: dict, status, private_key=None) -> str:
        """
        add host to table

        Args:
            host: parameter, e.g.
                {
                    "user": "admin",
                    "host_name": "test-host",
                    "host_group_id": "uuid",
                    "host_ip": "127.0.0.1",
                    "management": False,
                    "ssh_user": "root",
                    "pkey": "string",
                    "ssh_port": 22,
                }

        Returns:
            str: SUCCEED or DATABASE_INSERT_ERROR or PARAM_ERROR
        """
        try:
            handler_check_result, host_group = self._add_host_handler(host_info)
            if handler_check_result != SUCCEED:
                return handler_check_result
            host = Host(
                **host_info,
                cluster_id=host_group.cluster_id,
                host_group_name=host_group.host_group_name,
                status=status,
                pkey=private_key,
                host_id=str(uuid.uuid4()),
            )

            self.session.add(host)
            self.session.commit()
            LOGGER.info(f"add host {host.host_ip} succeed")
            return SUCCEED

        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error(f"add host {host.host_ip} fail")
            self.session.rollback()
            return DATABASE_INSERT_ERROR

    def get_hosts(self, host_page_filter: dict):
        """
        Get host according to host group from table

        Args:
            host_page_filter (dict): parameter, e.g.
                {
                    "host_group_list": ["group1", "group2"]
                    "management": False
                }

        Returns:
            int: status code
            dict: query result
        """
        result = {}
        try:
            result = self._query_hosts_page(host_page_filter)
            LOGGER.debug("Query hosts succeed")
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("Query hosts fail")
            return DATABASE_QUERY_ERROR, result

    @staticmethod
    def _get_hosts_page_filters(host_page_filter, groups: dict):
        """
        Generate filters

        Args:
            groups: e.g
                {
                    "group1": 1,
                    "group2": 2
                }

        """
        group_ids = list(groups.keys())
        if host_page_filter["host_group_list"]:
            group_ids = set(group_ids).intersection(set(host_page_filter["host_group_list"]))

        filters = {Host.host_group_id.in_(group_ids)}
        if host_page_filter["cluster_list"]:
            filters.add(Host.cluster_id.in_(host_page_filter["cluster_list"]))

        if host_page_filter["management"] is not None:
            filters.add(Host.management == host_page_filter["management"])
        if host_page_filter["search_key"]:
            filters.add(
                or_(
                    Host.host_name.like("%" + host_page_filter["search_key"] + "%"),
                    Host.host_ip.like("%" + host_page_filter["search_key"] + "%"),
                )
            )
        if host_page_filter["status"]:
            filters.add(Host.status.in_(host_page_filter["status"]))

        return filters

    def _query_hosts_page(self, host_page_filter: dict):
        """
        Sort host info by specified column

        Args:
            host_page_filter: sorted condition info

        Returns:
            dict
        """
        result = {"total_count": 0, "total_page": 0, "host_infos": []}
        groups = cache.get_user_group_hosts()
        if not groups:
            return result

        filters = self._get_hosts_page_filters(host_page_filter, groups)

        host_query = (
            self.session.query(
                Host.host_id,
                Host.host_name,
                Host.host_group_name,
                Host.host_ip,
                Host.management,
                Host.scene,
                Host.os_version,
                Host.ssh_port,
                Host.cluster_id,
                Cluster.cluster_name,
            )
            .outerjoin(Cluster, Cluster.cluster_id == Host.cluster_id)
            .filter(*filters)
        )

        result["total_count"] = host_query.count()
        if not result["total_count"]:
            return result

        processed_hosts_query, result["total_page"] = sort_and_page(
            host_query,
            host_page_filter["sort"],
            host_page_filter["direction"],
            host_page_filter["per_page"],
            host_page_filter["page"],
        )
        result['host_infos'] = GetHostsPage_ResponseSchema(many=True).dump(processed_hosts_query.all())

        return result

    def _validate_host_info(self, hosts: list) -> Tuple[str, List]:
        """

        Args:
            hosts: e.g
            [{
                "host_ip": "127.0.0.1,
                "ssh_port": 22,
                "ssh_user": "root",
                "password": "password",
                "host_name": "test_host",
                "host_group_name": "test_group",
                "management": False,
            }]
        """
        right_hosts = []
        error_hosts = []
        host_ips = [host["host_ip"] for host in hosts]
        groups = self.session.query(HostGroup.host_group_name, HostGroup.host_group_id, HostGroup.cluster_id).all()
        groups_dict = {group.host_group_name: group for group in groups}
        exists_hosts = self.session.query(Host.host_ip, Host.ssh_port).filter(Host.host_ip.in_(host_ips)).all()
        host_sets = {host.host_ip + ":" + str(host.ssh_port) for host in exists_hosts}
        for host in hosts:
            validate_message = ""
            if host["host_ip"] + ":" + str(host["ssh_port"]) in host_sets:
                validate_message = "host exists"

            if host["host_group_name"] not in groups_dict:
                validate_message += " host group not exists"

            if validate_message:
                host["reason"] = validate_message
                host["result"] = "failed"
                error_hosts.append(host)
                continue
            host["host_group_id"] = groups_dict[host["host_group_name"]].host_group_id
            host["cluster_id"] = groups_dict[host["host_group_name"]].cluster_id
            right_hosts.append(host)
        if error_hosts:
            return PARAM_ERROR, error_hosts

        return SUCCEED, right_hosts

    def add_host_batch(self, host_list: list) -> str:
        """
        Add host to the table in batches

        Args:
            host_list(list): list of host object

        Returns:
            str: SUCCEED or DATABASE_INSERT_ERROR
        """
        try:

            self.session.bulk_save_objects(host_list)
            self.session.commit()
            LOGGER.info(f"add host {[host.host_ip for host in host_list]}succeed")
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            self.session.rollback()
            return DATABASE_INSERT_ERROR

    def delete_host(self, host_ids: list):
        """
        Delete host from table

        Args:
            host_id: host id

        Returns:
            str
        """
        try:
            hosts = self.session.query(Host.host_group_id, Host.host_id).filter(Host.host_id.in_(host_ids)).all()
            if hosts and not self.session.query(Host).filter(Host.host_id.in_(host_ids)).delete(
                synchronize_session=False
            ):
                return DATABASE_DELETE_ERROR

            self.session.commit()
            RedisProxy.redis_connect.delete(RedisCacheManage.GROUPS_HOSTS)
            RedisProxy.redis_connect.delete(*RedisProxy.redis_connect.keys("*_group_hosts"))
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("delete hosts %s fail", host_ids)
            return DATABASE_DELETE_ERROR

    def update_host_info(self, host_id: str, host_info: dict) -> str:
        """
        update host info to host table

        Args:
            host_info: e.g
                {
                    "host_name": "new_host_name",
                    "management": True,
                    ...
                }

        Returns:
            str: SUCCEED or DATABASE_UPDATE_ERROR
        """
        if "ssh_pkey" in host_info:
            host_info.pop("ssh_pkey")
        try:
            exists_host = (
                self.session.query(Host)
                .filter(
                    Host.host_ip == host_info["host_ip"],
                    Host.ssh_port == host_info["ssh_port"],
                    Host.host_id != host_id,
                    Host.cluster_id == cache.location_cluster["cluster_id"],
                )
                .first()
            )
            if exists_host:
                return DATA_EXIST
            if host_info["host_group_id"]:
                host_group = (
                    self.session.query(HostGroup.host_group_name, HostGroup.cluster_id)
                    .filter(HostGroup.host_group_id == host_info["host_group_id"])
                    .first()
                )
                if not host_group:
                    return PARAM_ERROR
                host_info["cluster_id"] = host_group.cluster_id
                host_info["host_group_name"] = host_group.host_group_name
            host = self.session.query(Host).filter(Host.host_id == host_id).first()
            if not host:
                return NO_DATA
            # update host info
            wait_update_host_info = {key: value for key, value in host_info.items() if value}
            if "pkey" in host_info:
                wait_update_host_info.update(dict(pkey=host_info["pkey"]))
            if "status" in host_info:
                wait_update_host_info.update(dict(status=host_info["status"]))
            self.session.query(Host).filter(Host.host_id == host_id).update(
                wait_update_host_info, synchronize_session=False
            )
            self.session.commit()
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            self.session.rollback()
            return DATABASE_UPDATE_ERROR

    def get_host_info(self, host_id: str) -> Host:
        try:
            host = (
                self.session.query(
                    Host.host_id,
                    Host.host_name,
                    Host.host_group_name,
                    Host.host_ip,
                    Host.management,
                    Host.scene,
                    Host.os_version,
                    Host.ssh_port,
                    Host.last_scan,
                    Host.repo_id,
                    Host.status,
                    Host.reboot,
                    Host.pkey,
                    Host.ssh_user,
                    Host.cluster_id,
                    Host.host_group_id,
                    Host.ext_props,
                    Cluster.cluster_name,
                )
                .outerjoin(Cluster, Cluster.cluster_id == Host.cluster_id)
                .filter(Host.host_id == host_id)
                .first()
            )
            if not host:
                return NO_DATA, None
            return SUCCEED, host
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR, None

    def get_host_count(self, filter_param: dict):
        """
        Get host count

        Args:
            filter_param (dict): e.g.
                {
                    "status": "online",
                    "host_ids":[],
                    "host_group_ids":[],
                    "cluster_list": [],
                    "reboot": True/False,
                    "fields": []
                }

        Returns:
            str: status code
            dict: query result
        """
        result = dict(host_count=0)
        groups = cache.get_user_group_hosts()
        if not groups:
            return SUCCEED, result
        try:
            filters = self._create_host_query_filter(filter_param, groups)
            result['host_count'] = self.session.query(Host).filter(*filters).count()
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("query host count fail")
            return DATABASE_QUERY_ERROR, result

    def _create_host_query_filter(self, filter_param: dict, groups: dict):
        """
        Args:
            filter_param: e.g
                {
                    "status": "online",
                    "host_ids":[],
                    "host_group_ids":[],
                    "cluster_list": [],
                    "reboot": True/False,
                    "fields": [],
                    "host_name":"",
                    "repo":[]
                }

            groups: e.g.
                {
                    "group_1": 1,
                    "group_2": 2,
                }
        """
        group_ids = list(groups.keys())
        if filter_param["host_group_ids"]:
            group_ids = set(group_ids).intersection(set(filter_param["host_group_ids"]))

        filters = {Host.host_group_id.in_(group_ids)}

        if filter_param["cluster_list"]:
            filters.add(Host.cluster_id.in_(filter_param["cluster_list"]))

        if filter_param.get("host_name"):
            filters.add(Host.host_name.like(f"%{filter_param['host_name']}%"))
        if filter_param.get("repo"):
            filters.add(Host.repo_id.in_(filter_param["repo"]))
        if filter_param["status"]:
            filters.add(Host.status.in_([filter_param["status"]]))
        if filter_param["host_ids"]:
            filters.add(Host.host_id.in_(filter_param["host_ids"]))
        if filter_param["reboot"] is not None:
            filters.add(Host.reboot == filter_param["reboot"])
        return filters

    def get_filter_hosts(self, filter_param: dict):
        """
        Get the filtered hosts

        Args:
            filter_param: e.g
                {
                    "status": "online",
                    "host_ids":[],
                    "host_group_ids":[],
                    "cluster_list": [],
                    "reboot": True/False,
                    "fields": [],
                    "host_name": "",
                    "repo":[]
                }
        """
        groups = cache.get_user_group_hosts()
        if not groups:
            return SUCCEED, []
        try:
            filters = self._create_host_query_filter(filter_param, groups)
            hosts = self.session.query(Host).filter(*filters).all()
            hosts_serialized = (
                HostsInfo_ResponseSchema(many=True, only=filter_param["fields"])
                if filter_param["fields"]
                else HostsInfo_ResponseSchema(many=True)
            )

            return SUCCEED, hosts_serialized.dump(hosts)
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("query host fail")
            return DATABASE_QUERY_ERROR, None

    def update_host_association_information(self, host_id: int, update_info: Dict[str, Optional[Any]]) -> None:
        """
        Updates the association information for a given host.

        This function updates the fields of a host specified by the host_id with the provided
        update_info dictionary. Only fields with non-None values in update_info will be updated.

        Args:
            host_id (int): The ID of the host to update.
            update_info (Dict[str, Optional[Any]]): A dictionary containing the fields to update and their new values.
                Fields with None values will be ignored.

        Returns:
            None

        Raises:
            sqlalchemy.exc.SQLAlchemyError: If there is an error during the update operation.
        """
        try:
            self.session.query(Host).filter(Host.host_id == host_id).update(
                {key: value for key, value in update_info.items() if value is not None}
            )
            self.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("Failed to update association information!")
            self.session.rollback()
