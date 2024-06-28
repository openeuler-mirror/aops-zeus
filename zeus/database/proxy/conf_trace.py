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
@FileName: conf_trace.py
@Time: 2024/4/23 14:24
@Author: JiaoSiMao
Description:
"""
import datetime
import json
import math
import uuid

import sqlalchemy
from sqlalchemy import desc, asc, func

from vulcanus.database.proxy import MysqlProxy
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp.state import (
    DATABASE_INSERT_ERROR,
    SUCCEED, DATABASE_QUERY_ERROR, DATABASE_DELETE_ERROR,
)

from zeus.database.table import ConfTraceInfo


class ConfTraceProxy(MysqlProxy):
    """
        Conf trace related table operation
        """

    def add_conf_trace_info(self, data):
        """
        add conf trace info to table

        Args:
            data: parameter, e.g.
                {
                    "domain_name": "aops",
                    "host_id": 1,
                    "conf_name": "/etc/hostname",
                    "info": ""
                }

        Returns:
            int: SUCCEED or DATABASE_INSERT_ERROR
        """
        domain_name = data.get('domain_name')
        host_id = int(data.get('host_id'))
        conf_name = data.get('file')
        info = json.dumps(data)
        conf_trace_info = ConfTraceInfo(UUID=str(uuid.uuid4()), domain_name=domain_name, host_id=host_id,
                                        conf_name=conf_name, info=info, create_time=datetime.datetime.now())
        try:

            self.session.add(conf_trace_info)
            self.session.commit()
            LOGGER.info(
                f"add {conf_trace_info.domain_name} {conf_trace_info.host_id} {conf_trace_info.conf_name} conf trace "
                f"info succeed")
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error(
                f"add {conf_trace_info.domain_name} {conf_trace_info.host_ip} {conf_trace_info.conf_name} conf trace "
                f"info fail")
            self.session.rollback()
            return DATABASE_INSERT_ERROR

    def query_conf_trace_info(self, data):
        """
            query conf trace info from table

            Args:
                data: parameter, e.g.
                    {
                        "domain_name": "aops",
                        "host_id": 1,
                        "conf_name": "/etc/hostname",
                    }

            Returns:
                int: SUCCEED or DATABASE_INSERT_ERROR
        """
        result = {}
        try:
            result = self._sort_trace_info_by_column(data)
            self.session.commit()
            LOGGER.debug("query conf trace info succeed")
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("query conf trace info fail")
            return DATABASE_QUERY_ERROR, result

    def delete_conf_trace_info(self, data):
        """
            delete conf trace info from table

            Args:
                data: parameter, e.g.
                    {
                        "domain_name": "aops",
                        "host_ids": [1]
                    }

            Returns:
                int: SUCCEED or DATABASE_INSERT_ERROR
        """
        domainName = data['domain_name']
        host_ids = data['host_ids']
        try:
            # delete matched conf trace info
            if host_ids:
                conf_trace_filters = {ConfTraceInfo.host_id.in_(host_ids), ConfTraceInfo.domain_name == domainName}
            else:
                conf_trace_filters = {ConfTraceInfo.domain_name == domainName}
            confTraceInfos = self.session.query(ConfTraceInfo).filter(*conf_trace_filters).all()
            for confTraceInfo in confTraceInfos:
                self.session.delete(confTraceInfo)
            self.session.commit()
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("delete conf trace info fail")
            self.session.rollback()
            return DATABASE_DELETE_ERROR

    @staticmethod
    def _get_conf_trace_filters(data):
        """
        Generate filters

        Args:
            data(dict)

        Returns:
            set
        """
        domain_name = data.get('domain_name')
        host_id = data.get('host_id')
        conf_name = data.get('conf_name')
        filters = {ConfTraceInfo.host_id > 0}
        if domain_name:
            filters.add(ConfTraceInfo.domain_name == domain_name)
        if host_id:
            filters.add(ConfTraceInfo.host_id == host_id)
        if conf_name:
            filters.add(ConfTraceInfo.conf_name == conf_name)
        return filters

    def _get_conf_trace_count(self, filters):
        """
        Query according to filters

        Args:
            filters(set): query filters

        Returns:
            int
        """
        total_count = self.session.query(func.count(ConfTraceInfo.UUID)).filter(*filters).scalar()
        return total_count

    def _sort_trace_info_by_column(self, data):
        """
        Sort conf trace info by specified column

        Args:
            data(dict): sorted condition info

        Returns:
            dict
        """
        result = {"total_count": 0, "total_page": 0, "conf_trace_infos": []}
        sort = data.get('sort')
        direction = desc if data.get('direction') == 'desc' else asc
        page = data.get('page')
        per_page = data.get('per_page')
        total_page = 1
        filters = self._get_conf_trace_filters(data)
        total_count = self._get_conf_trace_count(filters)
        if total_count == 0:
            return result

        if sort:
            if page and per_page:
                total_page = math.ceil(total_count / per_page)
                conf_trace_infos = (
                    self.session.query(ConfTraceInfo)
                    .filter(*filters)
                    .order_by(direction(getattr(ConfTraceInfo, sort)))
                    .offset((page - 1) * per_page)
                    .limit(per_page)
                    .all()
                )
            else:
                conf_trace_infos = self.session.query(ConfTraceInfo).filter(*filters).order_by(
                    direction(getattr(ConfTraceInfo, sort))).all()
        else:
            if page and per_page:
                total_page = math.ceil(total_count / per_page)
                conf_trace_infos = self.session.query(ConfTraceInfo).filter(*filters).offset(
                    (page - 1) * per_page).limit(per_page).all()
            else:
                conf_trace_infos = self.session.query(ConfTraceInfo).filter(*filters).all()

        LOGGER.error(f"conf_trace_infos is {conf_trace_infos}")
        for conf_trace_info in conf_trace_infos:
            info_dict = json.loads(conf_trace_info.info)
            info_str = f"进程:{info_dict.get('cmd')} 修改了文件:{info_dict.get('file')}"
            ptrace_data = "=> ".join(f"{item['cmd']}:{item['pid']}" for item in info_dict.get('ptrace'))
            ptrace = f"{info_dict.get('cmd')} => {ptrace_data}"
            conf_trace_info = {
                "UUID": conf_trace_info.UUID,
                "domain_name": conf_trace_info.domain_name,
                "host_id": conf_trace_info.host_id,
                "conf_name": conf_trace_info.conf_name,
                "info": info_str,
                "create_time": str(conf_trace_info.create_time),
                "ptrace": ptrace
            }
            result["conf_trace_infos"].append(conf_trace_info)

        result["total_page"] = total_page
        result["total_count"] = total_count
        LOGGER.error(f"result is {result}")
        return result
