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

import os
from distutils.sysconfig import get_python_lib

from setuptools import find_packages, setup

CLI_DIR = os.path.join(get_python_lib(), "zeus", "cli")


setup(
    name='aops-zeus',
    version='2.1.0',
    packages=find_packages(),
    install_requires=["click", "PyYAML", "pymysql", "kazoo"],
    data_files=[
        (CLI_DIR, ["zeus/cli/deploy.sh"]),
    ],
    entry_points={
        'console_scripts': [
            'aops-cli=zeus.aops:run',
        ],
    },
    zip_safe=False,
)
