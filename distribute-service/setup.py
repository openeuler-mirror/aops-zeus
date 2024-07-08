#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2021. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
from setuptools import find_packages, setup

setup(
    name='zeus-distribute',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'Flask',
        'Flask-RESTful',
        'requests',
        'gevent',
        "retrying",
    ],
    data_files=[
        ('/etc/aops/conf.d', ['zeus-distribute.yml']),
        ('/usr/lib/systemd/system', ["zeus-distribute.service"]),
    ],
    zip_safe=False,
)
