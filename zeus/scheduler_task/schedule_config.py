#!/usr/bin/python3
#  ******************************************************************************
#  Copyright (C) 2023 isoftstone Technologies Co., Ltd. All rights reserved.
#  licensed under the Mulan PSL v2.
#  You can use this software according to the terms and conditions of the Mulan PSL v2.
#  You may obtain a copy of Mulan PSL v2 at:
#      http://license.coscl.org.cn/MulanPSL2
#  THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
#  PURPOSE.
#  See the Mulan PSL v2 for more details.
#  ******************************************************************************/
"""
@FileName: schedule_config.py
@Time: 2024/1/19 11:31
@Author: JiaoSiMao
Description:
"""


class ScheduleConfig:
    JOBS = [
        {
            'id': '1000',
            'func': 'zeus.scheduler_task.view:SyncStatus.update_sync_status_scheduler',  # 函数所在python文件名：函数名
            'trigger': 'cron',  # 使用cron触发器
            'day': '*',  # *表示每一天
            'hour': '*',
            'minute': '0/5',
            'second': '0'
        }
    ]
