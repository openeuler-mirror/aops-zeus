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
from unittest import TestCase

from flask import Flask

from vulcanus.database.proxy import MysqlProxy
import zeus



class BaseTestCase(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        MysqlProxy.engine = "mock_engine"
    @staticmethod
    def create_app():
        app = Flask("test")

        for blue, api in zeus.BLUE_POINT:
            api.init_app(app)
            app.register_blueprint(blue)

        app.testing = True
        return app.test_client()
