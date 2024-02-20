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
Description: Manager that start aops-zeus
"""
from zeus.scheduler_task.schedule_config import ScheduleConfig

try:
    from gevent import monkey

    monkey.patch_all(ssl=False)
except:
    pass

from vulcanus import init_application
from zeus.conf import configuration
from zeus.url import URLS
from flask_apscheduler import APScheduler

app = init_application(name="zeus", settings=configuration, register_urls=URLS)
app.config.from_object(ScheduleConfig())
scheduler = APScheduler()
# 将调度器对象与Flask应用程序实例(app)相关联
scheduler.init_app(app)
scheduler.start()

if __name__ == "__main__":
    app.run(host=configuration.zeus.get('IP'), port=configuration.zeus.get('PORT'))
