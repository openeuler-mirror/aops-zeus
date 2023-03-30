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
"""
Time: 2022-07-27
Author: YangYunYi
Description: Query raw data from Prometheus
"""
from typing import Dict, Tuple, List, Optional
from datetime import datetime
import datetime
from prometheus_api_client import PrometheusApiClientException
from vulcanus.database.proxy import PromDbProxy
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp.state import SUCCEED, DATABASE_QUERY_ERROR, NO_DATA, PARAM_ERROR, PARTIAL_SUCCEED


class MetricProxy(PromDbProxy):
    """
    Proxy of prometheus time series database
    """

    def __init__(self, configuration, host=None, port=None):
        """
        Init MetricProxy

        Args:
            configuration (Config)
            host (str)
            port (int)
        """
        PromDbProxy.__init__(self, configuration, host, port)
        self.default_instance_port = configuration.agent.get(
            'DEFAULT_INSTANCE_PORT') or 9100
        self.query_range_step = configuration.prometheus.get(
            'QUERY_RANGE_STEP') or "15s"

    @staticmethod
    def __metric_dict2str(metric: Dict) -> str:
        """
        Trans metric dict to string
        Args:
            metric (Dict):
                {
                    "__name__": "metric name1",
                    'instance': '172.168.128.164:9100',
                    'job': 'prometheus',
                    'label1': 'label_value1'
                    ...
                }

        Returns:
            metric_str(str): 'metric_name1{label1="value1", label2="values"}'
        """

        label_str = ""
        if "__name__" not in metric.keys():
            return label_str
        sorted_label_list = sorted(metric.items(), reverse=False)
        for label in sorted_label_list:
            # The job label is usually "prometheus" in this framework and
            # has no effect on subsequent data requests, so remove it to save space.
            # __name__ label move to the front.
            metric_key = label[0]
            metric_value = label[1]
            if metric_key in ["__name__", "job"]:
                continue
            label_str += "%s=\"%s\"," % (metric_key, metric_value)

        if label_str == "":
            # It's a metric with only a name and no personalized label
            ret = metric["__name__"]
        else:
            # Remove the comma of the last element
            ret = "%s{%s}" % (metric["__name__"], label_str[:-1])
        return ret

    def query_metric_names(self, query_ip: str) -> Tuple[int, dict]:
        """
        Query data
        Args:
            query_ip(str): query ip address

        Returns:
            int: status code
            dict: e.g
            {
                "results": ["metric1", "metric2"]
            }
        """

        query_ip = query_ip["query_ip"]
        query_host = {"host_id": "query_host_id", "host_ip": query_ip}

        query_metric_names = []
        res = {
            'results': query_metric_names
        }

        host_ip = query_host["host_ip"]
        host_port = query_host.get("instance_port", self.default_instance_port)

        ret, metric_list = self.query_metric_list_of_host(host_ip, host_port)

        if ret != SUCCEED:
            return ret, res

        for metric in metric_list:
            metric = metric.split('{')[0]
            if metric not in query_metric_names:
                query_metric_names.append(metric)

        return ret, res

    def query_metric_list(self, data: Dict[str, str]) -> Tuple[int, dict]:
        """
        Query metric list
        Args:
            data(dict): param e.g
                {
                    "query_ip": "str",
                    "metric_names": ["metric1", "metric2"]
                }

        Returns:
            int: status code
            dict: e.g
            {
                'results': {
                        "metric1": [
                            "metric1{label1="label1_value", label2="label2_value", ..., }",
                            "metric1{label1="label1_value", label2="label2_value", ..., }",
                        ],
                        "metric2": [
                            "metric2{label1="label1_value", label2="label2_value", ..., }",
                            "metric2{label1="label1_value", label2="label2_value", ..., }",
                        ]
                    }
            }
        """

        query_ip = data.get('query_ip')
        query_metric = data.get('metric_names')

        query_host = {"host_id": "query_host_id", "host_ip": query_ip}

        query_metric_list = {}
        res = {
            'results': query_metric_list
        }

        host_ip = query_host["host_ip"]
        host_port = query_host.get("instance_port", self.default_instance_port)

        ret, metric_list = self.query_metric_list_of_host(host_ip, host_port, )

        if ret != SUCCEED:
            LOGGER.warning("Host metric list query error")
            return ret, res

        for query_metric_name in query_metric:
            query_metric_list[query_metric_name] = []
            for metric in metric_list:
                metric_name = metric.split('{')[0]
                if metric_name != query_metric_name:
                    continue
                query_metric_list[query_metric_name].append(metric)

        return ret, res

    def query_metric_data(self, data: Dict[str, str]) -> Tuple[int, dict]:
        """
        Query metric data
        Args:
            data(dict): param e.g
                {
                    "time_range": "list",
                    "query_ip": "str",
                    "query_info": {
                        "metric1": [
                            "metric1{label1="label1_value", label2="label2_value", ..., }",
                            "metric1{label1="label1_value", label2="label2_value", ..., }",
                        ],
                        "metric2": [
                            "metric2{label1="label1_value", label2="label2_value", ..., }",
                            "metric2{label1="label1_value", label2="label2_value", ..., }",
                        ]
                    }
                }

        Returns:
            int: status code
            dict: e.g
            {
                'results': {
                        "metric1": {
                            "metric1{label1="label1_value", label2="label2_value", ..., }": [
                                [1658926441, '0'],
                                [1658926441, '0']
                            ],
                            "metric1{label1="label1_value", label2="label2_value", ..., }": [
                                [1658926441, '0'],
                                [1658926441, '0']
                            ],
                        },
                        "metric1": {
                            "metric2{label1="label1_value", label2="label2_value", ..., }": [
                                [1658926441, '0'],
                                [1658926441, '0']
                            ],
                            "metric2{label1="label1_value", label2="label2_value", ..., }": [
                                [1658926441, '0'],
                                [1658926441, '0']
                            ],
                        },
                    }
            }
        """
        time_range = data.get('time_range')
        query_ip = data.get('query_ip')
        query_info = data.get('query_info')

        query_host = {"host_id": "query_host_id", "host_ip": query_ip}

        host_ip = query_host["host_ip"]
        host_port = query_host.get("instance_port", self.default_instance_port)

        query_host_list = [query_host]
        query_data = {}
        res = {
            'results': query_data
        }

        # adjust query range step based on query time range
        # the default query range step is 15 seconds
        QUERY_RANGE_STEP = 15
        query_range_step = QUERY_RANGE_STEP
        query_range_seconds = time_range[1] - time_range[0]
        total_query_times = query_range_seconds/query_range_step

        while (total_query_times > 11000):
            query_range_step += 15
            total_query_times = query_range_seconds/query_range_step

        def add_two_dim_dict(thedict, key_a, key_b, val):
            if key_a in thedict:
                thedict[key_a].update({key_b: val})
            else:
                thedict.update({key_a: {key_b: val}})

        if not query_info:
            return SUCCEED, res

        for metric_name, metric_list in query_info.items():
            if not metric_list:
                _, metric_list = self.query_metric_list_of_host(
                    host_ip, host_port, metric_name)
            if not metric_list:
                query_data[metric_name] = []
            for metric_info in metric_list:
                data_status, monitor_data = self.query_data(
                    time_range=time_range, host_list=query_host_list, metric=metric_info, adjusted_range_step=query_range_step)
                values = []
                if data_status == SUCCEED:
                    values = monitor_data[query_host["host_id"]][metric_info]
                add_two_dim_dict(query_data, metric_name, metric_info, values)

        return SUCCEED, res

    def query_data(self, time_range: List[int], host_list: list, metric: Optional[str] = None, adjusted_range_step: Optional[int] = None) -> Tuple[int, Dict]:
        """
        Query data
        Args:
            time_range(list): time range
            host_list(list): host list, If the port is not specified, the default value is used
                [{"host_id": "id1", "host_ip": "172.168.128.164", "instance_port": 9100},
                 {"host_id": "id1", "host_ip": "172.168.128.164", "instance_port": 8080},
                 {"host_id": "id2", "host_ip": "172.168.128.165"}]

        Returns:
            ret(int): query ret
            host_data_list(dict): host data list ret
                    {
                        'id1': {
                            'metric1'{instance="172.168.128.164:9100",label1="value2"}':
                                                                               [[time1, 'value1'],
                                                                               [time2, 'value2'],
                            'metric12{instance="172.168.128.164:8080"}': [], => get data list is empty
                            'metric13{instance="172.168.128.164:8080"}': None => get no data
                        },
                        'id2': None => get no metric list of this host
                    }
        """

        host_data_list = {}
        if not host_list:
            return PARAM_ERROR, host_data_list

        status = SUCCEED
        for host in host_list:
            host_id = host["host_id"]
            host_ip = host["host_ip"]
            host_port = host.get("instance_port", self.default_instance_port)
            if host_id not in host_data_list.keys():
                host_data_list[host_id] = None

            ret, metric_list = self.query_metric_list_of_host(
                host_ip, host_port, metric)
            if ret != SUCCEED:
                status = PARTIAL_SUCCEED
                host_data_list[host_id] = None
                continue
            ret, data_list = self.__query_data_by_host(
                metric_list, time_range, adjusted_range_step)
            if ret != SUCCEED:
                status = PARTIAL_SUCCEED
            if not host_data_list[host_id]:
                host_data_list[host_id] = data_list
            else:
                host_data_list[host_id].update(data_list)

        return status, host_data_list

    def __parse_metric_data(self, metric_data: List) -> List[str]:
        """
        Parse metric data from prometheus to name<-> label_config dict
        Args:
            metric_data(List): metric list data from prometheus
                [{'metric':{
                    "__name__": "metric_name1",
                    'instance': '172.168.128.164:9100',
                    'job': 'prometheus',
                    'label1': 'label_value1'
                    ...
                    },
                  'value': [1658926441.526, '0']
                }]

        Returns:
            metric_list(List[str]):
                [
                    'metric_name1{label1="value1", label2="value2"}'
                ]
        """

        metric_list = []
        for metric_item in metric_data:
            metric_dict = metric_item["metric"]
            metric_str = self.__metric_dict2str(metric_dict)
            if metric_str == "":
                continue
            metric_list.append(metric_str)

        return metric_list

    def query_metric_list_of_host(self, host_ip: str, host_port: Optional[int] = None, metric: Optional[str] = None) -> Tuple[int, List[str]]:
        """
        Query metric list of a host
        Args:
            host_ip(str): host ip
            host_port(int): host port

        Returns:
            ret(int): query ret
            metric_list(list): metric list ret
                [
                    'metric_name1{label1="value1", label2="value2"}'
                ]
        """
        if not host_port:
            host_port = self.default_instance_port
        query_str = "{instance=\"%s:%s\"}" % (host_ip, str(host_port))
        if metric is not None:
            if metric.find('{') != -1:
                query_str = metric
            else:
                query_str = metric + query_str
        try:
            data = self._prom.custom_query(
                query=query_str
            )
            if not data:
                if query_str.startswith('{'):
                    LOGGER.error("Query metric list result is empty. "
                                 "Can not get metric list of host %s:%s " % (host_ip, host_port))
                return NO_DATA, []
            metric_list = self.__parse_metric_data(data)
            return SUCCEED, metric_list

        except (ValueError, TypeError, PrometheusApiClientException) as error:
            LOGGER.error("host %s:%d Prometheus query metric list failed. %s" % (
                host_ip, host_port, error))
            return DATABASE_QUERY_ERROR, []

    def __query_data_by_host(self, metrics_list: List[str], time_range: List[int], adjusted_range_step: Optional[int] = None) -> Tuple[int, Dict]:
        """
        Query data of a host
        Args:
            metrics_list(list): metric list of this host
            time_range(list): time range to query

        Returns:
            ret(int): query ret
            data_list(list): data list ret
                {
                    'metric1'{instance="172.168.128.164:9100",label1="value2"}':
                                                                       [[time1, 'value1'],
                                                                       [time2, 'value2'],
                    'metric12{instance="172.168.128.164:8080"}': [], => get data list is empty
                    'metric13{instance="172.168.128.164:8080"}': None => get no data
                }

        """
        start_time = datetime.datetime.fromtimestamp(time_range[0])
        end_time = datetime.datetime.fromtimestamp(time_range[1])

        query_range_step = self.query_range_step
        if adjusted_range_step is not None:
            query_range_step = adjusted_range_step

        data_list = {}
        ret = SUCCEED
        for metric in metrics_list:
            try:
                data = self._prom.custom_query_range(
                    query=metric,
                    start_time=start_time,
                    end_time=end_time,
                    step=query_range_step
                )
                if not data or "values" not in data[0]:
                    LOGGER.debug("Query data result is empty. "
                                 "metric %s in %d-%d doesn't record in the prometheus " % (
                                     metric, time_range[0], time_range[1]))
                    data_list[metric] = None
                    ret = PARTIAL_SUCCEED
                    continue
                data_list[metric] = data[0]["values"]

            except (ValueError, TypeError, PrometheusApiClientException) as error:
                LOGGER.error("Prometheus metric %s in %d-%d query data failed. %s" % (
                    metric, time_range[0], time_range[1], error))
                data_list[metric] = None
                ret = PARTIAL_SUCCEED
        return ret, data_list
