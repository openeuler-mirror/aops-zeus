#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2021. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
from async_task.tasks import async_task
from async_task.timed import timed_subclass
from vulcanus.timed import TimedTaskManager


def timed():
    """
    Start the scheduled task configured in the system
    """
    timed_task = TimedTaskManager(config_path="/etc/aops/crontab.yml")

    timed_task_map = {task.name: task for task in timed_subclass}

    for task_info in timed_task.timed_config.values():
        if not task_info["enable"]:
            continue
        if task_info["task"] not in timed_task_map:
            continue
        _task = timed_task_map[task_info["task"]]
        timed_task.add_job(_task(timed_config=task_info))
    timed_task.start()


def task():
    async_task.worker_main(argv=['worker', '--loglevel=info', '--pidfile=/opt/aops/celery/celery.pid'])


def main():
    timed()
    task()


if __name__ == '__main__':
    main()
