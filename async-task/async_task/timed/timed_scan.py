# !/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2023. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
import datetime
import json

import redis
from async_task.settings import configuration
from vulcanus.database.proxy import RedisProxy
from vulcanus.exceptions import DatabaseConnectionFailed
from vulcanus.log.log import LOGGER
from vulcanus.timed import TimedTask


class TimedScanTask(TimedTask):
    """
    Timed scan tasks
    """

    name = "cve-scan"

    def execute(self):
        """
        Start the scan after the specified time of day
        """
        LOGGER.info("Begin to scan the whole host in %s.", str(datetime.datetime.now()))

        try:
            if not RedisProxy.redis_connect:
                RedisProxy(host=configuration.redis.host, port=configuration.redis.port)

            return RedisProxy.redis_connect.publish(
                "cve_scan", json.dumps(dict(name=TimedScanTask.name, time=str(datetime.datetime.now())))
            )
        except (DatabaseConnectionFailed, redis.RedisError) as error:
            LOGGER.error("Failed to connect to redis, error: %s", error)
