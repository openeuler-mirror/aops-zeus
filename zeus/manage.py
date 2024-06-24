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

try:
    from gevent import monkey

    monkey.patch_all(ssl=False)
except:
    pass

from vulcanus import init_application, LOGGER
from vulcanus.timed import TimedTaskManager
from zeus.conf import configuration
from zeus.url import URLS
from zeus.conf.constant import TIMED_TASK_CONFIG_PATH
from zeus.cron import task_meta
from zeus.host_manager.terminal import socketio


def _init_timed_task(application):
    """
    Initialize and create a scheduled task

    Args:
        application:flask.Application
    """
    timed_task = TimedTaskManager(app=application, config_path=TIMED_TASK_CONFIG_PATH)
    if not timed_task.timed_config:
        LOGGER.warning(
            "If you want to start a scheduled task, please add a timed config."
        )
        return

    for task_info in timed_task.timed_config.values():
        task_type = task_info.get("type")
        if task_type not in task_meta:
            continue
        meta_class = task_meta[task_type]
        timed_task.add_job(meta_class(timed_config=task_info))

    timed_task.start()


def main():
    _app = init_application(name="zeus", settings=configuration, register_urls=URLS)
    socketio.init_app(app=_app)
    _init_timed_task(application=_app)
    return _app

app = main()

if __name__ == "__main__":
    app.run(host=configuration.zeus.get("IP"), port=configuration.zeus.get("PORT"))
    socketio.run(
        app,
        host=configuration.zeus.get("IP"),
        port=configuration.zeus.get("PORT"),
    )
