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
"""
Time:
Author:
Description: Host table operation
"""
import math
from typing import Dict, List, Tuple

import sqlalchemy
from sqlalchemy import func
from sqlalchemy.sql.expression import asc, desc
from sqlalchemy.orm.collections import InstrumentedList

from vulcanus.database.helper import judge_return_code, sort_and_page
from vulcanus.database.proxy import MysqlProxy
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp.state import (
    DATABASE_DELETE_ERROR,
    DATABASE_INSERT_ERROR,
    DATABASE_QUERY_ERROR,
    DATABASE_UPDATE_ERROR,
    DATA_DEPENDENCY_ERROR,
    DATA_EXIST,
    NO_DATA,
    SUCCEED,
)
from zeus.database.table import Host, HostGroup, User


class HostProxy(MysqlProxy):
    """
    Host related table operation
    """

    def add_host_from_client(self, data: Dict) -> int:
        """
        Verify whether the data is valid and add valid data to the database

        Args:
            data: parameter, e.g.
                {
                    "username": "admin",
                    "host_name": "host1",
                    "host_group_name": "group1",
                    "host_ip": "127.0.0.1",
                    "management": False,
                    "agent_port": 1122,
                    "os_version": "openEuler 22.03 LTS"
                }

        Returns:
            int
        """
        username = data.pop('username')
        try:
            user = self.session.query(User).filter(User.username == username).first()
            hosts = user.hosts

            group_filters = {HostGroup.username == username, HostGroup.host_group_name == data['host_group_name']}
            host_group_res = self.session.query(HostGroup).filter(*group_filters).all()
            if len(host_group_res) == 0:
                return NO_DATA

            host_group = host_group_res[0]
            data['host_group_id'] = host_group.host_group_id
            data['user'] = username
            host = Host(**data)
            if host in hosts:
                LOGGER.error("host %s exist", data['host_name'])
                return DATA_EXIST

            host.host_group = host_group
            host.owner = user
            self.session.add(host)
            self.session.commit()
            return SUCCEED

        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("add host fail")
            self.session.rollback()
            return DATABASE_INSERT_ERROR

    def delete_host(self, data):
        """
        Delete host from table

        Args:
            data(dict): parameter, e.g.
                {
                    "host_list": [1, 2],
                    "username": "admin"
                }

        Returns:
            int
        """
        host_list = data['host_list']
        result = {"succeed_list": [], "fail_list": {}}
        host_info = {}
        try:
            # query matched host
            hosts = self.session.query(Host).filter(Host.host_id.in_(host_list)).all()
            for host in hosts:
                self.session.delete(host)
                result['succeed_list'].append(host.host_id)
                host_info[host.host_id] = host.host_name
            self.session.commit()
            fail_list = list(set(host_list) - set(result['succeed_list']))
            result['fail_list'].update(zip(fail_list, len(fail_list) * ("Can't find the data in database",)))
            status_code = judge_return_code(result, DATABASE_DELETE_ERROR)
            result['host_info'] = host_info
            return status_code, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("delete host %s fail", host_list)
            self.session.rollback()
            result['fail_list'].update(zip(host_list, len(host_list) * ("Connect database fail",)))
            return DATABASE_DELETE_ERROR, result

    def get_host(self, data):
        """
        Get host according to host group from table

        Args:
            data(dict): parameter, e.g.
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
            result = self._sort_host_by_column(data)
            self.session.commit()
            LOGGER.debug("query host succeed")
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("query host fail")
            return DATABASE_QUERY_ERROR, result

    def get_host_count(self, data):
        """
        Get host count

        Args:
            data(dict): parameter, e.g.
                {
                    "username": "admin
                }

        Returns:
            int: status code
            dict: query result
        """
        result = {}
        result['host_count'] = 0
        try:
            filters = self._get_host_filters(data)
            total_count = self._get_host_count(filters)
            result['host_count'] = total_count
            self.session.commit()
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("query host count fail")
            return DATABASE_QUERY_ERROR, result

    def _get_host_count(self, filters):
        """
        Query according to filters

        Args:
            filters(set): query filters

        Returns:
            int
        """
        total_count = self.session.query(func.count(Host.host_id)).filter(*filters).scalar()
        return total_count

    @staticmethod
    def _get_host_filters(data):
        """
        Generate filters

        Args:
            data(dict)

        Returns:
            set
        """
        username = data['username']
        host_group_list = data.get('host_group_list')
        management = data.get('management')
        filters = {Host.user == username}
        if host_group_list:
            filters.add(Host.host_group_name.in_(host_group_list))
        if management is not None:
            filters.add(Host.management == management)
        if data.get('status'):
            filters.add(Host.status.in_(data.get('status')))

        return filters

    def _sort_host_by_column(self, data):
        """
        Sort host info by specified column

        Args:
            data(dict): sorted condition info

        Returns:
            dict
        """
        result = {"total_count": 0, "total_page": 0, "host_infos": []}
        sort = data.get('sort')
        direction = desc if data.get('direction') == 'desc' else asc
        page = data.get('page')
        per_page = data.get('per_page')
        total_page = 1
        filters = self._get_host_filters(data)
        total_count = self._get_host_count(filters)
        if total_count == 0:
            return result

        if sort:
            if page and per_page:
                total_page = math.ceil(total_count / per_page)
                hosts = (
                    self.session.query(Host)
                    .filter(*filters)
                    .order_by(direction(getattr(Host, sort)))
                    .offset((page - 1) * per_page)
                    .limit(per_page)
                    .all()
                )
            else:
                hosts = self.session.query(Host).filter(*filters).order_by(direction(getattr(Host, sort))).all()
        else:
            if page and per_page:
                total_page = math.ceil(total_count / per_page)
                hosts = self.session.query(Host).filter(*filters).offset((page - 1) * per_page).limit(per_page).all()
            else:
                hosts = self.session.query(Host).filter(*filters).all()

        for host in hosts:
            host_info = {
                "host_id": host.host_id,
                "host_name": host.host_name,
                "host_group_name": host.host_group_name,
                "host_ip": host.host_ip,
                "management": host.management,
                "scene": host.scene,
                "os_version": host.os_version,
                "ssh_port": host.ssh_port,
            }
            result['host_infos'].append(host_info)

        result['total_page'] = total_page
        result['total_count'] = total_count

        return result

    def get_host_info(self, data, is_collect_file: bool = False):
        """
        Get host basic info according to host id from table

        Args:
            data(dict): parameter, e.g.
                {
                    "username": "admin"
                    "host_list": ["id1", "id2"]
                }
            is_collect_file (bool)

        Returns:
            int: status code
            dict: query result
        """
        username = data.get('username')
        host_list = data.get('host_list')
        result = []
        query_fields = [
            Host.host_id,
            Host.host_name,
            Host.host_ip,
            Host.os_version,
            Host.ssh_port,
            Host.host_group_name,
            Host.management,
            Host.status,
            Host.scene,
            Host.pkey,
            Host.ssh_user,
        ]
        filters = {Host.user == username} if not is_collect_file else set()
        if host_list:
            filters.add(Host.host_id.in_(host_list))
        try:
            hosts = self.session.query(*query_fields).filter(*filters).all()
            for host in hosts:
                host_info = {
                    "host_id": host.host_id,
                    "host_group_name": host.host_group_name,
                    "host_name": host.host_name,
                    "host_ip": host.host_ip,
                    "management": host.management,
                    "status": host.status,
                    "scene": host.scene,
                    "os_version": host.os_version,
                    "ssh_port": host.ssh_port,
                    "pkey": host.pkey,
                    "ssh_user": host.ssh_user,
                }
                result.append(host_info)
            self.session.commit()
            LOGGER.debug("query host %s basic info succeed", host_list)
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("query host %s basic info fail", host_list)
            return DATABASE_QUERY_ERROR, result

    def get_host_ssh_info(self, data):
        """
        Get host ssh info according to host id from table

        Args:
            data(dict): parameter, e.g.
                {
                    "username": "admin"
                    "host_list": ["id1", "id2"]
                }

        Returns:
            int: status code
            dict: query result
        """
        username = data.get('username')
        host_list = data.get('host_list')
        result = []
        query_fields = [
            Host.host_id,
            Host.host_ip,
            Host.ssh_port,
            Host.pkey,
            Host.ssh_user,
        ]
        filters = {Host.user == username}
        if host_list:
            filters.add(Host.host_id.in_(host_list))
        try:
            hosts = self.session.query(*query_fields).filter(*filters).all()
            for host in hosts:
                host_info = {
                    "host_id": host.host_id,
                    "host_ip": host.host_ip,
                    "ssh_port": host.ssh_port,
                    "pkey": host.pkey,
                    "ssh_user": host.ssh_user,
                }
                result.append(host_info)
            LOGGER.debug("query host %s ssh info succeed", host_list)
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("query host %s ssh info fail", host_list)
            return DATABASE_QUERY_ERROR, result

    def get_total_host_info_by_user(self, data):
        """
        Get host basic info according to user from table

        Args:
            data(dict): parameter, e.g.
                {
                    "username": ["admin"]
                }

        Returns:
            int: status code
            dict: query result
        """
        username = data.get('username')
        temp_res = {}
        result = {}
        result['host_infos'] = temp_res

        try:
            if username:
                users = self.session.query(User).filter(User.username.in_(username)).all()
            else:
                users = self.session.query(User).all()
            for user in users:
                name = user.username
                temp_res[name] = []
                for host in user.hosts:
                    host_info = {
                        "host_id": host.host_id,
                        "host_group_name": host.host_group_name,
                        "host_name": host.host_name,
                        "host_ip": host.host_ip,
                    }
                    temp_res[name].append(host_info)
            self.session.commit()
            LOGGER.debug("query host basic info succeed")
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("query host basic info fail")
            return DATABASE_QUERY_ERROR, result

    def add_host_group(self, data):
        """
        Add host group to table

        Args:
            data(dict): parameter, e.g.
                {
                    "host_group_name": "group1",
                    "description": "des",
                    "username": "admin",
                }

        Returns:
            int
        """
        username = data['username']
        host_group_name = data['host_group_name']
        try:
            user = self.session.query(User).filter(User.username == username).first()
            host_group = HostGroup(**data)
            if host_group in user.host_groups:
                return DATA_EXIST
            host_group.user = user
            self.session.add(host_group)
            self.session.commit()
            LOGGER.info("add host group [%s] succeed", host_group_name)
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            self.session.rollback()
            LOGGER.error("add host group [%s] fail", host_group_name)
            return DATABASE_INSERT_ERROR

    def delete_host_group(self, data):
        """
        Delete host group from table

        Args:
            data(dict): parameter, e.g.
                {
                    "host_group_list": ["group1"],
                    "username": "admin"
                }

        Returns:
            int: status code
            dict: deleted group
        """

        host_group_list = data['host_group_list']
        username = data['username']
        result = {"deleted": []}
        deleted = []
        not_deleted = []
        try:
            # Filter the group if there are hosts in the group
            host_groups = (
                self.session.query(HostGroup, func.count(Host.host_id).label("host_count"))
                .outerjoin(Host, HostGroup.host_group_id == Host.host_group_id)
                .filter(HostGroup.username == username)
                .filter(HostGroup.host_group_name.in_(host_group_list))
                .group_by(HostGroup.host_group_id)
                .all()
            )
            for host_group, host_count in host_groups:
                if host_count > 0:
                    not_deleted.append(host_group.host_group_name)
                    continue
                deleted.append(host_group.host_group_name)
                self.session.delete(host_group)
            self.session.commit()
            result["deleted"] = deleted
            if not_deleted:
                LOGGER.error("host group %s deleted, groups %s delete fail", deleted, not_deleted)
                return DATA_DEPENDENCY_ERROR, result
            LOGGER.info("host group %s delete succeed", deleted)
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            self.session.rollback()
            LOGGER.error("delete host group %s fail", host_group_list)
            return DATABASE_DELETE_ERROR, result

    def get_host_group(self, data):
        """
        Get host group from table

        Args:
            data(dict): parameter, e.g.
                {
                    "sort": "host_group_name",
                    "direction": "asc",
                    "page": 1,
                    "per_page": 20,
                    "username": "admin"
                }

        Returns:
            int: status code
            dict: group infos
        """
        result = {}
        try:
            result = self._sort_group_by_column(data)
            self.session.commit()
            LOGGER.debug("query host group succeed")
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("query host group fail")
            return DATABASE_QUERY_ERROR, result

    def _sort_group_by_column(self, data):
        result = {"total_count": 0, "total_page": 1, "host_group_infos": []}
        host_group_infos = (
            self.session.query(
                HostGroup.host_group_name, HostGroup.description, func.count(Host.host_id).label("host_count")
            )
            .outerjoin(Host, HostGroup.host_group_id == Host.host_group_id)
            .filter(HostGroup.username == data['username'])
            .group_by(HostGroup.host_group_id)
        )
        total_count = len(host_group_infos.all())
        if not total_count:
            return result

        sort_column = self._get_group_column(data.get('sort'))
        direction, page, per_page = data.get('direction'), data.get('page'), data.get('per_page')
        processed_query, total_page = sort_and_page(host_group_infos, sort_column, direction, per_page, page)
        infos = processed_query.all()
        host_group_infos = self._group_info_row2dict(infos)
        result['total_count'] = total_count
        result['total_page'] = total_page
        result['host_group_infos'] = host_group_infos
        return result

    @staticmethod
    def _get_group_column(column_name):
        if not column_name:
            return None
        if column_name == "host_count":
            return func.count(Host.host_id)
        return getattr(HostGroup, column_name)

    @staticmethod
    def _group_info_row2dict(rows):
        result = []
        for host_group in rows:
            result.append(
                {
                    "host_group_name": host_group.host_group_name,
                    "description": host_group.description,
                    "host_count": host_group.host_count,
                }
            )
        return result

    def _sort_group_by_column_old(self, data):
        """
        Sort group info by specified column

        Args:
            data(dict): sorted condition info

        Returns:
            dict
        """
        result = {"total_count": 0, "total_page": 0, "host_group_infos": []}
        sort = data.get('sort')
        direction = desc if data.get('direction') == 'desc' else asc
        page = data.get('page')
        per_page = data.get('per_page')
        total_page = 1

        user = self.session.query(User).filter(User.username == data['username']).first()
        total_count = len(user.host_groups)
        if total_count == 0:
            return result
        query_fields = [HostGroup.host_group_name, HostGroup.description, HostGroup.host_count]
        filters = {HostGroup.username == data['username']}
        if sort:
            if page and per_page:
                total_page = math.ceil(total_count / per_page)
                host_groups = (
                    self.session.query(*query_fields)
                    .filter(*filters)
                    .order_by(direction(getattr(HostGroup, sort)))
                    .offset((page - 1) * per_page)
                    .limit(per_page)
                    .all()
                )
            else:
                host_groups = (
                    self.session.query(*query_fields)
                    .filter(*filters)
                    .order_by(direction(getattr(HostGroup, sort)))
                    .all()
                )
        else:
            if page and per_page:
                total_page = math.ceil(total_count / per_page)
                host_groups = (
                    self.session.query(*query_fields)
                    .filter(*filters)
                    .offset((page - 1) * per_page)
                    .limit(per_page)
                    .all()
                )
            else:
                host_groups = self.session.query(*query_fields).filter(*filters).all()

        for host_group in host_groups:
            result['host_group_infos'].append(
                {
                    "host_group_name": host_group.host_group_name,
                    "description": host_group.description,
                    "host_count": host_group.host_count,
                }
            )

        result['total_page'] = total_page
        result['total_count'] = total_count

        return result

    def save_scene(self, data):
        """
        Save scene info of host

        Args:
            data(dict): parameter, e.g.
            {
                "scene": "big data",
                "host_id": "12345"
            }

        Returns:
            dict
        """
        scene = data.get("scene")
        host_id = data.get("host_id")
        try:
            host = self.session.query(Host).filter(Host.host_id == host_id).one()
            host.scene = scene
            self.session.commit()
            return SUCCEED

        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("Save host %s scene fail.", host_id)
            self.session.rollback()
            return DATABASE_INSERT_ERROR

    def get_host_address(self, host_id_list: List[str]) -> Tuple[int, dict]:
        """
            get host ip and agent port from database
        Args:
            host_id_list( List[str] ) : [host_id1, host_id2, ...]
        Returns:
            tuple:
                status_code, {host_id : ip_with_port}

        """
        result = {}
        try:
            query_list = self.session.query(Host).filter(Host.host_id.in_(host_id_list)).all()
            self.session.commit()

            for host_info in query_list:
                result[host_info.host_id] = f'{host_info.host_ip}:{host_info.agent_port}'
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR, result

    def query_host_groups(self, username: str) -> Tuple[int, dict]:
        """
        query all host groups by username

        Args:
            username(str): admin

        Returns:
            tuple:
                status_code, {group name : group id}
        """
        try:
            query_list = self.session.query(HostGroup).filter(HostGroup.username == username).all()
            result = {}
            for group_info in query_list:
                result[group_info.host_group_name] = group_info.host_group_id
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error(f"query groups of {username} fail")
            return DATABASE_QUERY_ERROR, {}

    def add_host(self, host: Host) -> int:
        """
        add host to table

        Args:
            host: parameter, e.g.
                {
                    "user": "admin",
                    "host_name": "test-host",
                    "host_group_name": "group1",
                    "host_ip": "127.0.0.1",
                    "management": False,
                    "ssh_user": "root",
                    "pkey": "string",
                    "ssh_port": 22,
                    "host_group_id": 1,
                }

        Returns:
            int: SUCCEED or DATABASE_INSERT_ERROR
        """
        try:
            self.session.add(host)
            self.session.commit()
            LOGGER.info(f"add host {host.host_ip} succeed")
            return SUCCEED

        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error(f"add host {host.host_ip} fail")
            self.session.rollback()
            return DATABASE_INSERT_ERROR

    def get_hosts_and_groups(self, username: str) -> Tuple[int, InstrumentedList, InstrumentedList]:
        """
        get all hosts by username

        Args:
            username(str): admin

        Returns:
            tuple:
                status_code, list of host object, list of group object
        """
        try:
            user = self.session.query(User).filter(User.username == username).one()
            return SUCCEED, user.hosts, user.host_groups
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR, InstrumentedList(), InstrumentedList()

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

    def update_host_info(self, host_id: str, update_info: dict) -> str:
        """
        update host info to host table

        Args:
            update_info(dict): e.g
                {
                    "host_id": host_id,
                    "host_name": "new_host_name",
                    "management": True,
                    ...
                }

        Returns:
            str: SUCCEED or DATABASE_UPDATE_ERROR
        """
        try:
            self.session.query(Host).filter(Host.host_id == host_id).update(update_info)
            self.session.commit()
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            self.session.rollback()
            return DATABASE_UPDATE_ERROR


    def update_host_status(self, host_info: list) -> str:
        """
        update host status to host table

        Args:
            host_info(list): e.g
                {
                    "host_id": host_id,
                    "status": status
                }

        Returns:
            str: SUCCEED or DATABASE_UPDATE_ERROR
        """
        try:
            for host in host_info:
                self.session.query(Host).filter(Host.host_id == host.get('host_id')).update(
                    {"status": host.get('status')})
            self.session.commit()
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            self.session.rollback()
            return DATABASE_UPDATE_ERROR
