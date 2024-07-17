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
from copy import deepcopy
from urllib.parse import urlencode

import gevent
import requests
from flask import g, request
from gevent.pool import Pool
from retrying import retry
from vulcanus.conf.constant import DISTRIBUTE
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp import make_response, state
from vulcanus.restful.response import BaseResponse
from vulcanus.rsa import load_private_key, sign_data

from zeus.distribute_service.app import cache


class DistributeAPI(BaseResponse):
    """
    Interface for distribution service
    """

    def __init__(self):
        super(DistributeAPI, self).__init__()
        self.pool = Pool(100)
        self._cluster_response = dict()
        self._headers = None
        self._user_cluster_private_key = None
        self._location_cluster = None
        self._files = None

    def _remote(self, body, url, method="get", headers=None):
        @retry(
            stop_max_attempt_number=3,
            wait_exponential_multiplier=1000,
            wait_exponential_max=10000,
            retry_on_exception=lambda exception: isinstance(exception, requests.exceptions.RequestException),
        )
        def _response():
            if headers and self._files:
                del headers["Content-Type"]
                headers["Content-Disposition"] = 'form-data; name="file"'
            response = BaseResponse.get_response(method=method, url=url, data=body, header=headers, files=self._files)
            if response["label"] in (state.SERVER_ERROR, state.HTTP_CONNECT_ERROR):
                raise requests.exceptions.RequestException
            return response

        try:
            return _response()
        except requests.exceptions.RequestException:
            LOGGER.error(f"Remote failed max retries: {url}")
            return make_response(label=state.SERVER_ERROR)

    def _request_handler(self, body, method):
        LOGGER.debug("distribute service request param: %s", body)
        if not isinstance(body, dict):
            return self.response(code=state.PARAM_ERROR)
        self._headers = g.headers
        self._user_cluster_private_key = cache.get_user_cluster_private_key or dict()
        self._cluster = [key for key in body.keys()]
        response = self._distribute_service(body, method)
        return response

    @property
    def clusters(self):
        return {cluster_id: cluster for cluster_id, cluster in cache.clusters.items() if cluster_id in self._cluster}

    def _signature(self, data, cluster_id):
        sub_cluster = self._user_cluster_private_key.get(cluster_id)
        if not sub_cluster:
            return None, None
        cluster_username = sub_cluster["cluster_username"]
        key = load_private_key(sub_cluster["private_key"])
        signature = sign_data(data, key)
        return signature, cluster_username

    def _fetch_cluster(self, cluster, url, body, method):
        headers = deepcopy(self._headers)
        if cluster["cluster_id"] != self._location_cluster["cluster_id"]:
            signature, cluster_username = self._signature(data=body, cluster_id=cluster["cluster_id"])
            if not all([signature, cluster_username]):
                self._cluster_response.update(
                    {
                        cluster["cluster_id"]: {
                            "label": state.PERMESSION_ERROR,
                            "data": None,
                        }
                    }
                )
                return

            del headers["Access-Token"]
            headers["X-Permission"] = "RSA"
            headers["X-Signature"] = signature
            headers["X-Cluster-Username"] = cluster_username
        if method == "GET":
            url = url[: url.find("?")] + "?" + urlencode(body)

        cluster_execute_result = self._remote(body, "http://" + cluster["cluster_ip"] + url, method, headers)
        self._cluster_response.update(
            {
                cluster["cluster_id"]: {
                    "label": cluster_execute_result["label"],
                    "data": cluster_execute_result.get("data"),
                }
            }
        )

    def _distribute_service(self, body, method):

        user_clusters = cache.get_user_clusters()
        if not user_clusters:
            LOGGER.error("exists unmanaged cluster")
            return self.response(code=state.PERMESSION_ERROR)

        if set(self.clusters.keys()).difference(set(user_clusters)):
            LOGGER.error("exists unmanaged cluster")
            return self.response(code=state.PERMESSION_ERROR)

        try:
            distribute_url = request.headers["X-Real-Url"].replace(DISTRIBUTE, "")
        except KeyError:
            return self.response(code=state.UNKNOWN_ERROR)
        self._location_cluster = cache.location_cluster
        gevent.joinall(
            [
                self.pool.spawn(self._fetch_cluster, cluster, distribute_url, body[cluster_id], method)
                for cluster_id, cluster in self.clusters.items()
            ]
        )

        return self.response(code=state.SUCCEED, data=self._cluster_response)

    @BaseResponse.handle()
    def get(self, **param):
        return self._request_handler(param, "GET")

    def _set_files(self, file):
        self._files = {"file": (file.filename, file, "mime/type")}
        param = {request.form["cluster_id"]: dict(request.form)}
        return param

    @BaseResponse.handle()
    def post(self, **param):
        if request.files:
            param = self._set_files(request.files['file'])

        return self._request_handler(param, "POST")

    @BaseResponse.handle()
    def put(self, **param):
        return self._request_handler(param, "PUT")

    @BaseResponse.handle()
    def delete(self, **param):
        return self._request_handler(param, "DELETE")
