#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2022. All rights reserved.
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
from werkzeug.security import generate_password_hash

from vulcanus.database.helper import drop_tables, create_database_engine
from vulcanus.database.proxy import MysqlProxy
from vulcanus.restful.resp.state import DATA_EXIST, PARTIAL_SUCCEED, SUCCEED, DATA_DEPENDENCY_ERROR
from vulcanus.common import ValidateUtils
from zeus.database.table import Host, User, Base, create_utils_tables
from zeus.database.proxy.host import HostProxy


class TestHostDatabase(unittest.TestCase):
    def setUp(self):
        # create engine to database
        mysql_host = "127.0.0.1"
        mysql_port = 3306
        mysql_url_format = "mysql+pymysql://@%s:%s/%s"
        mysql_database_name = "aops_test"
        engine_url = mysql_url_format % (mysql_host, mysql_port, mysql_database_name)
        MysqlProxy.engine = create_database_engine(engine_url, 100, 7200)
        self.proxy = HostProxy()
        self.proxy.connect()
        # create all tables
        create_utils_tables(Base, self.proxy.engine)
        # create user
        data = {"username": "admin", "password": "123456"}
        password_hash = generate_password_hash(data['password'])
        user = User(username=data['username'], password=password_hash)
        self.proxy.session.add(user)
        self.proxy.session.commit()

    def tearDown(self):
        drop_tables(Base, self.proxy.engine)

    def test_api_host_group(self):
        # ==============add host group===================
        group_data1 = {"username": "admin", "host_group_name": "group1", "description": "xxx", "host_group_id": 1}
        group_data2 = {
            "username": "admin",
            "host_group_name": "group2",
            "description": "xxx",
            "host_group_id": 2
            # "host_count": 3
        }
        group_data3 = {
            "username": "admin",
            "host_group_name": "group3",
            "description": "xxx",
            "host_group_id": 3
            # "host_count": 1
        }
        group_data4 = {"username": "admin", "host_group_name": "group1", "description": "xxx", "host_group_id": 1}
        host = [
            {
                "user": "admin",
                "host_name": "host1",
                "host_group_name": "group2",
                "host_id": 1,
                "host_ip": "127.0.0.1",
                "management": False,
                "os_version": "openEuler 2203",
                "host_group_id": 2,
            },
            {
                "user": "admin",
                "host_name": "host2",
                "host_group_name": "group2",
                "host_id": 2,
                "host_ip": "127.0.0.2",
                "management": False,
                "os_version": "openEuler 2003",
                "host_group_id": 2,
            },
            {
                "user": "admin",
                "host_name": "host3",
                "host_group_name": "group2",
                "host_id": 3,
                "host_ip": "127.0.0.3",
                "management": False,
                "os_version": "openEuler 2109",
                "host_group_id": 2,
            },
            {
                "user": "admin",
                "host_name": "host4",
                "host_group_name": "group3",
                "host_id": 4,
                "host_ip": "127.0.0.4",
                "management": False,
                "os_version": "openEuler 2003",
                "host_group_id": 3,
            },
        ]

        res = self.proxy.add_host_group(group_data1)
        self.assertEqual(res, SUCCEED)
        res = self.proxy.add_host_group(group_data3)
        self.assertEqual(res, SUCCEED)
        res = self.proxy.add_host_group(group_data2)
        self.assertEqual(res, SUCCEED)
        res = self.proxy.add_host_group(group_data4)
        self.assertEqual(res, DATA_EXIST)

        for data in host:
            self.proxy.add_host(Host(**data))
        # ==============get host group=================
        args = {"username": "admin", "sort": "host_group_name"}
        expected_res = [
            {
                'host_group_name': 'group1',
                'description': 'xxx',
                'host_count': 0,
            },
            {'host_group_name': 'group2', 'description': 'xxx', 'host_count': 3},
            {'host_group_name': 'group3', 'description': 'xxx', 'host_count': 1},
        ]
        res = self.proxy.get_host_group(args)

        self.assertEqual(res[0], SUCCEED)
        self.assertEqual(res[1]['host_group_infos'], expected_res)

        args = {"username": "admin", "sort": "host_count", "direction": "desc", "page": 2, "per_page": 2}
        expected_res = [{'host_group_name': 'group1', 'description': 'xxx', 'host_count': 0}]
        res = self.proxy.get_host_group(args)
        self.assertEqual(res[0], SUCCEED)
        self.assertEqual(res[1]['host_group_infos'], expected_res)

        args = {"username": "admin", "sort": "host_count", "direction": "desc"}
        expected_res = [
            {'host_group_name': 'group2', 'description': 'xxx', 'host_count': 3},
            {'host_group_name': 'group3', 'description': 'xxx', 'host_count': 1},
            {'host_group_name': 'group1', 'description': 'xxx', 'host_count': 0},
        ]
        res = self.proxy.get_host_group(args)
        self.assertEqual(res[0], SUCCEED)
        self.assertEqual(res[1]['host_group_infos'], expected_res)

        # ===============delete host group=============
        args = {"host_group_list": ["group2"], "username": "admin"}
        res = self.proxy.delete_host_group(args)

        self.assertEqual(res[1]['deleted'], [])
        self.assertEqual(res[0], DATA_DEPENDENCY_ERROR)

        args = {"host_group_list": ["group1"], "username": "admin"}
        res = self.proxy.delete_host_group(args)

        self.assertEqual(res[1]['deleted'], ["group1"])

    def test_api_host(self):
        # ==============add host group===================
        group_data1 = {"username": "admin", "host_group_name": "group1", "description": "xxx", "host_group_id": 1}
        group_data2 = {
            "username": "admin",
            "host_group_name": "group2",
            "description": "xxx",
            "host_group_id": 2
            # "host_count": 0
        }
        self.proxy.add_host_group(group_data1)
        self.proxy.add_host_group(group_data2)

        # ==============add host===================
        data = [
            {
                "host_name": "host1",
                "host_group_name": "group1",
                "host_ip": "127.0.0.1",
                "management": False,
                "user": "admin",
                "os_version": "openEuler2003",
                "host_group_id": 1,
            },
            {
                "host_name": "host2",
                "host_group_name": "group1",
                "host_ip": "127.0.0.2",
                "management": True,
                "user": "admin",
                "os_version": "openEuler2109",
                "host_group_id": 1,
            },
            {
                "host_name": "host3",
                "host_group_name": "group2",
                "host_ip": "127.0.0.3",
                "management": False,
                "user": "admin",
                "os_version": "openEuler2203",
                "host_group_id": 2,
            },
            {
                "host_name": "host4",
                "host_group_name": "group2",
                "host_ip": "127.0.0.4",
                "management": True,
                "user": "admin",
                "os_version": "openEuler2209",
                "host_group_id": 2,
            },
            {
                "host_name": "host5",
                "host_group_name": "group2",
                "host_ip": "127.0.0.5",
                "management": False,
                "user": "admin",
                "os_version": "openEuler",
                "host_group_id": 2,
            },
        ]
        for host in data:
            res = self.proxy.add_host(Host(**host))
            self.assertEqual(res, SUCCEED)

        condition = {}
        res = self.proxy.select([Host], condition)
        self.assertEqual(5, len(res[1]))

        args = {"username": "admin"}
        expected_res = [
            {'host_group_name': 'group1', 'description': 'xxx', 'host_count': 2},
            {'host_group_name': 'group2', 'description': 'xxx', 'host_count': 3},
        ]
        res = self.proxy.get_host_group(args)
        self.assertEqual(res[0], SUCCEED)
        self.assertEqual(res[1]['host_group_infos'], expected_res)

        # ==============get host=====================
        args = {
            "host_group_list": [],
            "sort": "host_name",
            "direction": "desc",
            "page": 1,
            "per_page": 2,
            "username": "admin",
        }

        res = self.proxy.get_host(args)
        expected_res = [
            {
                "host_id": 5,
                "host_name": "host5",
                "host_group_name": "group2",
                "host_ip": "127.0.0.5",
                "management": False,
                "scene": None,
                "os_version": "openEuler",
                "ssh_port": 22,
            },
            {
                "host_id": 4,
                "host_name": "host4",
                "host_group_name": "group2",
                "host_ip": "127.0.0.4",
                "management": True,
                "scene": None,
                "os_version": "openEuler2209",
                "ssh_port": 22,
            },
        ]
        self.assertEqual(res[1]['total_count'], 5)
        self.assertEqual(res[1]['host_infos'], expected_res)

        args = {
            "host_group_list": [],
            "sort": "host_name",
            "direction": "asc",
            "page": 2,
            "per_page": 2,
            "username": "admin",
        }

        res = self.proxy.get_host(args)
        expected_res = [
            {
                "host_id": 3,
                "host_name": "host3",
                "host_group_name": "group2",
                "host_ip": "127.0.0.3",
                "management": False,
                "scene": None,
                "os_version": "openEuler2203",
                "ssh_port": 22,
            },
            {
                "host_id": 4,
                "host_name": "host4",
                "host_group_name": "group2",
                "host_ip": "127.0.0.4",
                "management": True,
                "scene": None,
                "os_version": "openEuler2209",
                "ssh_port": 22,
            },
        ]
        self.assertEqual(res[1]['total_count'], 5)
        self.assertEqual(res[1]['host_infos'], expected_res)

        # ===============get host count================
        args = {"username": "admin"}
        expected_res = 5
        res = self.proxy.get_host_count(args)
        self.assertEqual(expected_res, res[1]["host_count"])

        # ================get host info=================
        args = {"username": "admin", "host_list": [1, 2]}
        expected_res = [
            {
                "host_name": "host1",
                "host_group_name": "group1",
                "host_id": 1,
                "host_ip": "127.0.0.1",
                "management": False,
                "status": 2,
                "scene": None,
                "os_version": "openEuler2003",
                "ssh_port": 22,
                "pkey": None,
                "ssh_user": "root",
            },
            {
                "host_name": "host2",
                "host_group_name": "group1",
                "host_id": 2,
                "host_ip": "127.0.0.2",
                "management": True,
                "status": 2,
                "scene": None,
                "os_version": "openEuler2109",
                "ssh_port": 22,
                "pkey": None,
                "ssh_user": "root",
            },
        ]
        res = self.proxy.get_host_info(args)
        self.assertTrue(ValidateUtils.compare_two_object(expected_res, res[1]))

        # =====================get host info by user===============
        args = {}
        expected_res = {
            "admin": [
                {"host_name": "host1", "host_group_name": "group1", "host_id": 1, "host_ip": "127.0.0.1"},
                {"host_name": "host2", "host_group_name": "group1", "host_id": 2, "host_ip": "127.0.0.2"},
                {"host_name": "host3", "host_group_name": "group2", "host_id": 3, "host_ip": "127.0.0.3"},
                {"host_name": "host4", "host_group_name": "group2", "host_id": 4, "host_ip": "127.0.0.4"},
                {"host_name": "host5", "host_group_name": "group2", "host_id": 5, "host_ip": "127.0.0.5"},
            ]
        }
        res = self.proxy.get_total_host_info_by_user(args)
        self.assertTrue(ValidateUtils.compare_two_object(expected_res, res[1]['host_infos']))

        # ==============delete host===================
        args = {"username": "admin", "host_list": [1, 9]}
        res = self.proxy.delete_host(args)
        self.assertEqual(res[0], PARTIAL_SUCCEED)
        self.assertEqual(list(res[1]["fail_list"].keys()), [9])
        self.assertEqual(res[1]['succeed_list'][0], 1)

        args = {"host_group_list": ["group1"], "username": "admin"}
        res = self.proxy.get_host(args)
        self.assertEqual(res[1]['total_count'], 1)
