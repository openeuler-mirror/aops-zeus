#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2022-2022. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
from vulcanus.restful.response import BaseResponse
from zeus.database.proxy.metric import MetricProxy
from zeus.function.verify.metric import QueryHostMetricDataSchema, QueryHostMetricListSchema, QueryHostMetricNamesSchema
from zeus.conf import configuration


class QueryHostMetricNames(BaseResponse):
    """
    Interface for query host metric names from web.
    Restful API: GET
    """

    @BaseResponse.handle(schema=QueryHostMetricNamesSchema, proxy=MetricProxy(configuration))
    def get(self, callback: MetricProxy, **params):
        status_code, result = callback.query_metric_names(params)
        return self.response(code=status_code, data=result)


class QueryHostMetricData(BaseResponse):
    """
    Interface for query host metric data from web.
    Restful API: POST
    """

    @BaseResponse.handle(schema=QueryHostMetricDataSchema, proxy=MetricProxy(configuration))
    def post(self, callback: MetricProxy, **params):
        status_code, result = callback.query_metric_data(params)
        return self.response(code=status_code, data=result)


class QueryHostMetricList(BaseResponse):
    """
    Interface for query host metric list from web.
    Restful API: POST
    """

    @BaseResponse.handle(schema=QueryHostMetricListSchema, proxy=MetricProxy(configuration))
    def post(self, callback: MetricProxy, **params):
        status_code, result = callback.query_metric_list(params)
        return self.response(code=status_code, data=result)
