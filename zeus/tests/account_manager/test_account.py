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
"""
Time:
Author:
Description:
"""
import unittest

from vulcanus.database.helper import drop_tables, create_database_engine
from vulcanus.database.proxy import MysqlProxy
from vulcanus.restful.resp.state import LOGIN_ERROR, REPEAT_PASSWORD, SUCCEED
from zeus.database.proxy.account import UserProxy
from zeus.database.table import User, Base, create_utils_tables


class TestAccountDatabase(unittest.TestCase):
    def setUp(self):
        # create engine to database
        mysql_host = "127.0.0.1"
        mysql_port = 3306
        mysql_url_format = "mysql+pymysql://@%s:%s/%s"
        mysql_database_name = "aops_test"
        engine_url = mysql_url_format % (mysql_host, mysql_port, mysql_database_name)
        MysqlProxy.engine = create_database_engine(engine_url, 100, 7200)
        self.proxy = UserProxy()
        self.proxy.connect()
        # create all tables
        create_utils_tables(Base, self.proxy.engine)

    def tearDown(self):
        self.proxy.session.close()
        drop_tables(Base, MysqlProxy.engine)

    def test_api_user(self):
        # ==============add user ===================
        data = [{"username": "admin", "password": "changeme"}, {"username": "test", "password": "123456"}]
        for user in data:
            res = self.proxy.add_user(user)
            self.assertEqual(res, SUCCEED)
        condition = {}
        res = self.proxy.select([User], condition)
        self.assertEqual(len(res[1]), 2)

        # ==============user login=====================
        # unknown username
        data = {"username": "test1", "password": "aa"}
        res = self.proxy.login(data)
        self.assertEqual(res[0], LOGIN_ERROR)
        # wrong password
        data = {"username": "test", "password": "2111"}
        res = self.proxy.login(data)
        self.assertEqual(res[0], LOGIN_ERROR)
        # right
        data = {"username": "test", "password": "123456"}
        res = self.proxy.login(data)
        self.assertEqual(res[0], SUCCEED)

        # =============change password===================
        # new password is the same as origin
        data = {"username": "test", "password": "123456", "old_password": "123456"}
        self.assertEqual(self.proxy.change_password(data), REPEAT_PASSWORD)

        # right
        data = {"username": "test", "password": "444", "old_password": "123456"}
        self.assertEqual(self.proxy.change_password(data), SUCCEED)

        res = self.proxy.login(data)
        self.assertEqual(res[0], SUCCEED)
