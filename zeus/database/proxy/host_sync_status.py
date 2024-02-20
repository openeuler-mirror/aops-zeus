#!/usr/bin/python3
# ******************************************************************************
# Copyright (C) 2023 isoftstone Technologies Co., Ltd. All rights reserved.
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
from typing import Tuple

import sqlalchemy
from vulcanus.database.proxy import MysqlProxy
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp.state import (
    DATABASE_DELETE_ERROR,
    DATABASE_INSERT_ERROR,
    SUCCEED, DATABASE_QUERY_ERROR,
)
from zeus.database.table import HostSyncStatus


class HostSyncProxy(MysqlProxy):
    """
    Host related table operation
    """

    def add_host_sync_status(self, data) -> int:
        """
        add host to table

        Args:
            host_sync_status: parameter, e.g.
                {
                    "host_id": 1,
                    "host_ip": "192.168.1.1",
                    "domain_name": "aops",
                    "sync_status": 0
                }

        Returns:
            int: SUCCEED or DATABASE_INSERT_ERROR
        """
        host_id = data.get('host_id')
        host_ip = data.get('host_ip')
        domain_name = data.get('domain_name')
        sync_status = data.get('sync_status')
        host_sync_status = HostSyncStatus(host_id=host_id, host_ip=host_ip, domain_name=domain_name,
                                          sync_status=sync_status)
        try:

            self.session.add(host_sync_status)
            self.session.commit()
            LOGGER.info(f"add {host_sync_status.domain_name} {host_sync_status.host_ip} host sync status succeed")
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error(f"add {host_sync_status.domain_name} {host_sync_status.host_ip} host sync status fail")
            self.session.rollback()
            return DATABASE_INSERT_ERROR

    def add_host_sync_status_batch(self, host_sync_list: list) -> str:
        """
        Add host to the table in batches

        Args:
            host_sync_list(list): list of host sync status object

        Returns:
            str: SUCCEED or DATABASE_INSERT_ERROR
        """
        try:
            self.session.bulk_save_objects(host_sync_list)
            self.session.commit()
            LOGGER.info(f"add host {[host_sync_status.host_ip for host_sync_status in host_sync_list]} succeed")
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            self.session.rollback()
            return DATABASE_INSERT_ERROR

    def delete_host_sync_status(self, data):
        """
        Delete host from table

        Args:
            data(dict): parameter, e.g.
                {
                    "host_id": 1,
                    "domain_name": "aops",
                }

        Returns:
            int
        """
        host_id = data['host_id']
        domain_name = data['domain_name']
        try:
            # query matched host sync status
            hostSyncStatus = self.session.query(HostSyncStatus). \
                filter(HostSyncStatus.host_id == host_id). \
                filter(HostSyncStatus.domain_name == domain_name). \
                all()
            for host_sync in hostSyncStatus:
                self.session.delete(host_sync)
            self.session.commit()
            LOGGER.info(f"delete {domain_name} {host_id} host sync status succeed")
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("delete host sync status fail")
            self.session.rollback()
            return DATABASE_DELETE_ERROR

    def get_host_sync_status(self, data) -> Tuple[int, dict]:
        host_id = data['host_id']
        domain_name = data['domain_name']
        try:
            host_sync_status = self.session.query(HostSyncStatus). \
                filter(HostSyncStatus.host_id == host_id). \
                filter(HostSyncStatus.domain_name == domain_name).one_or_none()
            return SUCCEED, host_sync_status
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR, {}

    def get_domain_host_sync_status(self, domain_name: str):
        try:
            host_sync_status = self.session.query(HostSyncStatus). \
                filter(HostSyncStatus.domain_name == domain_name).all()
            result = []
            for host_sync in host_sync_status:
                single_host_sync_status = {
                    "host_id": host_sync.host_id,
                    "host_ip": host_sync.host_ip,
                    "domain_name": host_sync.domain_name,
                    "sync_status": host_sync.sync_status
                }
                result.append(single_host_sync_status)
            self.session.commit()
            LOGGER.debug("query host sync status %s basic info succeed", result)
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR, []

    def update_domain_host_sync_status(self, domain_diff_resp: list):
        try:
            saved_ids = []
            for domain_diff in domain_diff_resp:
                update_count = self.session.query(HostSyncStatus).filter(
                    HostSyncStatus.host_id == domain_diff.get("host_id")). \
                    filter(HostSyncStatus.domain_name == domain_diff.get("domain_name")).update(domain_diff)
                saved_ids.append(update_count)
                self.session.commit()
                LOGGER.debug("update host sync status { %s, %s }basic info succeed", domain_diff.get("host_id"),
                             domain_diff.get("domain_name"))
            if saved_ids:
                return SUCCEED, saved_ids
            return DATABASE_QUERY_ERROR, []
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR, []
