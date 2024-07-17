#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2024. All rights reserved.
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
Description: setup up the A-ops user manager service.
"""

from setuptools import find_packages, setup

setup(
    name='zeus-user-access',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        "celery",
        "Flask",
        "marshmallow",
        "PyJWT",
        "SQLAlchemy",
        "Werkzeug",
    ],
    data_files=[
        ('/etc/aops/conf.d', ['zeus-user-access.yml']),
        ('/usr/lib/systemd/system', ["zeus-user-access.service"]),
        ("/opt/aops/database", ["zeus/user_access_service/database/zeus-user-access.sql"]),
    ],
    zip_safe=False,
)
