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

from celery import Celery

from async_task.base import CeleryConfig
from async_task.tasks.cluster_synchronize_cancel_task import ClusterSynchronizeCancelTask
from async_task.tasks.cluster_synchronize_task import ClusterSynchronizeTask
from async_task.tasks.cve_fix_task import CveFixTask
from async_task.tasks.cve_rollback_task import CveRollbackTask
from async_task.tasks.cve_scan_task import CveScanTask
from async_task.tasks.hotpatch_remove_task import HotpatchRemoveTask
from async_task.tasks.repo_set_task import RepoSetTask

async_task = Celery(main="async_task")
async_task.config_from_object(CeleryConfig)
async_task.autodiscover_tasks(["async_task.tasks", "async_task.tasks.plugins"])


class Task:
    cve_fix_task = async_task.register_task(CveFixTask)
    cve_scan_task = async_task.register_task(CveScanTask)
    cve_rollback_task = async_task.register_task(CveRollbackTask)
    hotpatch_remove_task = async_task.register_task(HotpatchRemoveTask)
    repo_set_task = async_task.register_task(RepoSetTask)
    cluster_synchronize_task = async_task.register_task(ClusterSynchronizeTask)
    cluster_synchronize_cancel_task = async_task.register_task(ClusterSynchronizeCancelTask)


__all__ = ('Task', "async_task")
