#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2022-2023. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
from async_task.timed.correct import CorrectDataTask
from async_task.timed.download_sa import TimedDownloadSATask
from async_task.timed.send_notification import SendNotificationTask
from async_task.timed.timed_scan import TimedScanTask
from async_task.timed.upstream import DynamicUpdateUpstreamTask
from vulcanus.timed import TimedTask

timed_subclass = TimedTask.__subclasses__()

__all__ = (
    "timed_subclass",
    "CorrectDataTask",
    "TimedDownloadSATask",
    "SendNotificationTask",
    "TimedScanTask",
    "DynamicUpdateUpstreamTask",
)
