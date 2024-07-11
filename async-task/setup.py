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
from setuptools import find_packages, setup

setup(
    name='async-task',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'celery',
    ],
    author='gongzt',
    data_files=[
        ('/etc/aops', ['crontab.yml']),
        ("/etc/aops/sync-conf.d", ["async_task/tasks/synchronize_conf/instance.properties"]),
        (
            "/etc/aops/sync-conf.d/rdb",
            [
                "async_task/tasks/synchronize_conf/rdb_conf/cve_fix_task.yml",
                "async_task/tasks/synchronize_conf/rdb_conf/cve_host_match.yml",
                "async_task/tasks/synchronize_conf/rdb_conf/cve_rollback_task.yml",
                "async_task/tasks/synchronize_conf/rdb_conf/host_group.yml",
                "async_task/tasks/synchronize_conf/rdb_conf/host.yml",
                "async_task/tasks/synchronize_conf/rdb_conf/hotpatch_remove_task.yml",
                "async_task/tasks/synchronize_conf/rdb_conf/repo.yml",
                "async_task/tasks/synchronize_conf/rdb_conf/task_host_repo.yml",
                "async_task/tasks/synchronize_conf/rdb_conf/vul_task.yml",
                "async_task/tasks/synchronize_conf/rdb_conf/domain.yml",
                "async_task/tasks/synchronize_conf/rdb_conf/domain_conf_info.yml",
                "async_task/tasks/synchronize_conf/rdb_conf/domain_host.yml",
                "async_task/tasks/synchronize_conf/rdb_conf/host_conf_sync_status.yml",
            ],
        ),
        ('/usr/lib/systemd/system', ['async-task.service']),
    ],
    entry_points={'console_scripts': ['async-task=async_task.__main__:main']},
    zip_safe=False,
)
