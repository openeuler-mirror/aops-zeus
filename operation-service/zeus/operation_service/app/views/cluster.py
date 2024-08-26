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
import json

from vulcanus.database.proxy import RedisProxy
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse
from zeus.host_information_service.app.proxy.cluster import ClusterProxy
from zeus.host_information_service.app.serialize.cluster import (
    AddClusterSchema,
    QueryClusterSchema,
    UpdateClusterSchema,
)


class ClusterManageAPI(BaseResponse):
    @BaseResponse.handle(schema=QueryClusterSchema, proxy=ClusterProxy)
    def get(self, callback: ClusterProxy, **params):
        cluster_ids = params.get("cluster_ids")
        get_cluster_status, clusters_info = callback.get_cluster_info(cluster_ids)
        if get_cluster_status != state.SUCCEED:
            return self.response(code=get_cluster_status, message="get cluster info failed.")
        if not cluster_ids:
            self._cache_cluster_info(clusters_info)
        return self.response(code=state.SUCCEED, data=clusters_info)

    def _cache_cluster_info(self, clusters_info: list):
        RedisProxy.redis_connect.delete("clusters")
        cache_data = {cluster_info["cluster_id"]: json.dumps(cluster_info) for cluster_info in clusters_info}
        if cache_data:
            RedisProxy.redis_connect.hmset("clusters", cache_data)

    @BaseResponse.handle(schema=AddClusterSchema, proxy=ClusterProxy)
    def post(self, callback: ClusterProxy, **params):
        add_cluster_status = callback.add_cluster(**params)
        return self.response(code=add_cluster_status)

    @BaseResponse.handle(schema=UpdateClusterSchema, proxy=ClusterProxy)
    def put(self, callback: ClusterProxy, **params):
        """_summary_

        Args:
            args (dict): e.g.
            {
                "cluster_id": "xxx",
                "cluster_ip": "xxx",
                "cluster_name": "xxx",
                "description": "xxx",
                "synchronous_state": "xxx"
            }

        Returns:
            dict:
            {
                "code": 200,
                "label": "Succeed",
                "message": "operation succeed",
            }
        """
        update_cluster_status = callback.update_cluster(**params)
        return self.response(code=update_cluster_status)


class LocalClusterIdAPI(BaseResponse):
    @BaseResponse.handle(proxy=ClusterProxy, token=False)
    def get(self, callback: ClusterProxy):
        """Get local cluster id.

        Returns:
            dict:
            {
                "code": 200,
                "label": "Succeed",
                "message": "operation succeed",
                "data" : cluster_info e.g.
                    (dict)
                    {
                        "cluster_id": "xxx",
                        "cluster_name": "xxx",
                        "cluster_ip": "xxx",
                        "private_key": "xxx",
                        "public_key": "xxx"
                    }
            }
        """
        status_code, result = callback.get_local_cluster_info()
        if status_code != state.SUCCEED:
            return self.response(code=status_code)
        return self.response(code=state.SUCCEED, data=result)


class ClusterGroupInfoCacheAPI(BaseResponse):
    @BaseResponse.handle(proxy=ClusterProxy)
    def get(self, callback: ClusterProxy):
        status_code, clusters_group_info = callback.get_cluster_group_info()
        if status_code != state.SUCCEED:
            return self.response(code=status_code)
        if clusters_group_info:
            RedisProxy.redis_connect.hmset(
                "cluster_groups",
                {cluster_id: json.dumps(group_info) for cluster_id, group_info in clusters_group_info.items()},
            )
            RedisProxy.redis_connect.expire("cluster_groups", 60)
        return self.response(code=state.SUCCEED)
