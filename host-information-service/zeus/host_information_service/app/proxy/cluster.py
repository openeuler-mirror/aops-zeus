#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
from typing import Tuple

import sqlalchemy
import sqlalchemy.exc
from sqlalchemy import and_, or_
from vulcanus.cache import RedisCacheManage
from vulcanus.conf import constant
from vulcanus.database.proxy import MysqlProxy, RedisProxy
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp import state
from vulcanus.restful.resp.state import (
    DATA_EXIST,
    DATABASE_DELETE_ERROR,
    DATABASE_INSERT_ERROR,
    DATABASE_QUERY_ERROR,
    DATABASE_UPDATE_ERROR,
    NO_DATA,
    PERMESSION_ERROR,
    REPEAT_DATA,
    SUCCEED,
)
from zeus.host_information_service.app import cache
from zeus.host_information_service.app.serialize.cluster import (
    GetClusterInfo_ResponseSchema,
    GetLocalClusterInfo_ResponseSchema,
)
from zeus.host_information_service.database.table import Cluster, Host, HostGroup


class ClusterProxy(MysqlProxy):
    def add_cluster(
        self, cluster_id: str, cluster_name: str, description: str, cluster_ip: str, synchronous_state: str
    ):
        if cache.user_role != constant.UserRoleType.ADMINISTRATOR:
            return PERMESSION_ERROR
        check_status = self._check_cluster_no_added(cluster_id, cluster_name, cluster_ip)
        if check_status != state.SUCCEED:
            return check_status

        cluster = Cluster(
            cluster_id=cluster_id,
            subcluster=True,
            cluster_name=cluster_name,
            backend_ip=cluster_ip,
            description=description,
            synchronous_state=synchronous_state,
            private_key="",
            public_key="",
        )
        try:
            self.session.add(cluster)
            self.session.commit()
            LOGGER.debug(f"add cluster succeed: {cluster_id}.")
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error(f"add cluster fail: {cluster_id}.")
            self.session.rollback()
            return DATABASE_INSERT_ERROR

    def get_cluster_info(self, cluster_ids: list) -> Tuple[str, list]:
        try:
            clusters_info = list()
            filters = {} if not cluster_ids else {Cluster.cluster_id.in_(cluster_ids)}
            clusters = self.session.query(Cluster).filter(*filters).all()
            clusters_info = GetClusterInfo_ResponseSchema(many=True).dump(clusters)
            exist_cluster_ids = [cluster_info["cluster_id"] for cluster_info in clusters_info]
            unexist_cluster_ids = (set(cluster_ids)).difference(set(exist_cluster_ids))
            if unexist_cluster_ids:
                LOGGER.error(f"get cluster info failed: {unexist_cluster_ids} not found in database")
                return NO_DATA, []
            return SUCCEED, clusters_info
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("get cluster info failed.")
            return DATABASE_QUERY_ERROR, clusters_info

    def get_cluster_group_info(self) -> Tuple[str, dict]:
        try:
            cluster_group_info = dict()
            host_groups = self.session.query(
                HostGroup.cluster_id, HostGroup.host_group_id, HostGroup.host_group_name
            ).all()
            for host_group in host_groups:
                cluster_group_info.setdefault(host_group.cluster_id, []).append(
                    {host_group.host_group_id: host_group.host_group_name}
                )
            LOGGER.debug("get cluster group info success.")
            return SUCCEED, cluster_group_info
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("get cluster group info failed.")
            return DATABASE_QUERY_ERROR, cluster_group_info

    def _check_cluster_no_added(self, cluster_id: str, cluster_name: str, cluster_ip: str) -> str:
        """Check if cluster info has been added in database.

        Args:
            cluster_id (str)
            cluster_name (str): cluster name
            cluster_ip (str): cluster ip

        Returns:
            Tuple[str, str]: check result, exist cluster info
        """
        if self.session.query(Cluster).filter(Cluster.cluster_id == cluster_id).count():
            return DATA_EXIST

        filters = {or_(Cluster.cluster_name == cluster_name, Cluster.backend_ip == cluster_ip)}

        if self.session.query(Cluster).filter(*filters).count():
            return REPEAT_DATA

        return SUCCEED

    def update_cluster_synchronous_state(self, cluster_id: str, synchronous_state: str):
        try:
            self.session.query(Cluster).filter(Cluster.cluster_id == cluster_id).update(
                {
                    "synchronous_state": synchronous_state,
                },
                synchronize_session=False,
            )
            self.session.commit()
            LOGGER.debug(f"update cluster: {cluster_id} synchronous_state succeed.")
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error(f"update cluster: {cluster_id} synchronous_state failed.")
            self.session.rollback()
            return DATABASE_UPDATE_ERROR

        self._refresh_synchronize_cache()
        return SUCCEED

    def update_cluster(
        self, cluster_id: str, cluster_name: str, description: str, cluster_ip: str, synchronous_state: str = None
    ):
        if cache.user_role != constant.UserRoleType.ADMINISTRATOR:
            return PERMESSION_ERROR
        try:
            if not self.session.query(Cluster).filter(Cluster.cluster_id == cluster_id).count():
                return NO_DATA
            check_res = self._check_update_param_vaild(cluster_id, cluster_name, description, cluster_ip)
            if check_res != SUCCEED:
                return check_res

            update_param = {
                "cluster_name": cluster_name,
                "backend_ip": cluster_ip,
                "description": description,
            }
            if synchronous_state:
                update_param["synchronous_state"] = synchronous_state
            self.session.query(Cluster).filter(Cluster.cluster_id == cluster_id).update(
                update_param, synchronize_session=False
            )

            self.session.commit()
            LOGGER.debug(f"update cluster succeed: {cluster_id}.")
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error(f"update cluster failed: {cluster_id}.")
            self.session.rollback()
            return DATABASE_UPDATE_ERROR

        self._delete_cluster_cache(cluster_id)

        return SUCCEED

    def _delete_cluster_cache(self, cluster_id: str):
        RedisProxy.redis_connect.delete("clusters")
        RedisProxy.redis_connect.delete("cluster_groups")

        if RedisProxy.redis_connect.keys("*_clusters"):
            RedisProxy.redis_connect.delete(*RedisProxy.redis_connect.keys("*_clusters"))
        if RedisProxy.redis_connect.keys("*_group_hosts"):
            RedisProxy.redis_connect.delete(*RedisProxy.redis_connect.keys("*_group_hosts"))
        if RedisProxy.redis_connect.keys("*_rsa_key"):
            RedisProxy.redis_connect.delete(*RedisProxy.redis_connect.keys("*_rsa_key"))

        local_cluster = cache.location_cluster
        if local_cluster and local_cluster["cluster_id"] == cluster_id:
            RedisProxy.redis_connect.delete("location_cluster")

    def _check_update_param_vaild(self, cluster_id: str, cluster_name: str, description: str, cluster_ip: str):
        filters = {
            and_(
                Cluster.cluster_id != cluster_id,
                or_(Cluster.cluster_name == cluster_name, Cluster.backend_ip == cluster_ip),
            )
        }
        if self.session.query(Cluster).filter(*filters).count():
            return REPEAT_DATA
        return SUCCEED

    def cancel_synchronize_cluster(self, cluster_id: str):
        """
        Delete cluster info in table

        Args:
            cluster_id: cluster_id id

        Returns:
            str
        """
        try:
            host_group_id_subquery = self.session.query(HostGroup).filter(HostGroup.cluster_id == cluster_id).subquery()
            self.session.query(Host).filter(Host.host_group_id == host_group_id_subquery.c.host_group_id).delete(
                synchronize_session=False
            )
            self.session.query(HostGroup).filter(HostGroup.cluster_id == cluster_id).delete(synchronize_session=False)
            self.session.query(Cluster).filter(Cluster.cluster_id == cluster_id).delete(synchronize_session=False)

            self.session.commit()
            self._refresh_synchronize_cache()
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("delete cluster %s info fail", cluster_id)
            self.session.rollback()
            return DATABASE_DELETE_ERROR

    @staticmethod
    def _refresh_synchronize_cache():
        if RedisProxy.redis_connect.keys("*_clusters"):
            RedisProxy.redis_connect.delete(*RedisProxy.redis_connect.keys("*_clusters"))
        if RedisProxy.redis_connect.keys("*_group_hosts"):
            RedisProxy.redis_connect.delete(*RedisProxy.redis_connect.keys("*_group_hosts"))
        if RedisProxy.redis_connect.keys("*_rsa_key"):
            RedisProxy.redis_connect.delete(*RedisProxy.redis_connect.keys("*_rsa_key"))
        RedisProxy.redis_connect.delete(RedisCacheManage.ALL_CLUSTER_KEY)
        RedisProxy.redis_connect.delete(RedisCacheManage.CLUSTER_GROUPS)
        RedisProxy.redis_connect.delete(RedisCacheManage.GROUPS_HOSTS)
        return state.SUCCEED

    def get_local_cluster_info(self) -> Tuple[str, dict]:
        """Get local cluster info, which is unique.

        Returns:
            Tuple[str, dict]: status_code, cluster_info
        """
        try:
            cluster_info = dict()
            local_cluster = self.session.query(Cluster).filter_by(subcluster=False).one_or_none()
            if not local_cluster:
                LOGGER.error("get local cluster info failed.")
                return NO_DATA, cluster_info

        except sqlalchemy.orm.exc.MultipleResultsFound as error:
            LOGGER.error(error)
            LOGGER.error("local cluster info should be unique.")
            return REPEAT_DATA, cluster_info
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("get local cluster info failed.")
            return DATABASE_QUERY_ERROR, cluster_info

        cluster_info = GetLocalClusterInfo_ResponseSchema(many=False).dump(local_cluster)
        LOGGER.debug("get local cluster info succeed.")

        RedisProxy.redis_connect.delete("location_cluster")
        RedisProxy.redis_connect.hmset("location_cluster", cluster_info)
        cluster_info.pop("private_key")
        cluster_info.pop("public_key")
        return SUCCEED, cluster_info
