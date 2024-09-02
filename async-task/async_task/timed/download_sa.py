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


class TimedDownloadSATask(TimedTask):
    """
    Timed download sa tasks
    """

    name = "download-sa"

    def execute(self):
        """
        First read the downloaded history from the database, and then obtain the url list of the security announcements
        to be downloaded incrementally. Download all the security announcements in the list to the local, parse the
        security announcements and store them in the database, and update the data in the history table.
        """
        LOGGER.info("Begin to download advisory in %s.", str(datetime.datetime.now()))

        try:
            cvrf_url = self.timed_config["meta"]["cvrf_url"]
        except KeyError:
            cvrf_url = "https://repo.openeuler.org/security/data/cvrf"
        try:
            if not RedisProxy.redis_connect:
                RedisProxy(host=configuration.redis.host, port=configuration.redis.port)

            RedisProxy.redis_connect.publish(
                "download_sa",
                json.dumps(dict(cvrf=cvrf_url, name=TimedDownloadSATask.name, time=str(datetime.datetime.now()))),
            )
        except (DatabaseConnectionFailed, redis.RedisError) as error:
            LOGGER.error("Failed to connect to redis, error: %s", error)
