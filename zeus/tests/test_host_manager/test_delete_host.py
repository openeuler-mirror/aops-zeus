#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2022-2022. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
import unittest
from unittest import mock

from flask import Flask

from zeus import BLUE_POINT
from zeus.database.proxy.host import HostProxy
from vulcanus.restful.resp.state import TOKEN_ERROR, DATABASE_CONNECT_ERROR

app = Flask("check")
for blue, api in BLUE_POINT:
    api.init_app(blue)
    app.register_blueprint(blue)

app.testing = True
client = app.test_client()
header = {
    "Content-Type": "application/json; charset=UTF-8"
}
header_with_token = {
    "Content-Type": "application/json; charset=UTF-8",
    "access_token": "123456"
}


class TestDeleteHost(unittest.TestCase):

    def test_delete_host_should_return_token_error_when_part_of_input_with_no_token(self):
        input_data = {'host_list': [1, 2, 3]}
        resp = client.delete('/manage/host/delete',
                             json=input_data, headers=header)

        self.assertEqual(TOKEN_ERROR, resp.json.get('code'), resp.json)

    def test_delete_host_should_return_400_when_no_input(self):
        resp = client.delete('/manage/host/delete', headers=header_with_token)
        self.assertEqual(400, resp.status_code, resp.json)

    @mock.patch.object(HostProxy, 'connect')
    def test_delete_host_should_return_database_error_when_database_cannot_connect(
            self, mock_mysql_connect):
        input_data = {'host_list': [1, 2, 3]}
        mock_mysql_connect.return_value = False
        resp = client.delete('/manage/host/delete',
                             json=input_data, headers=header_with_token)
        self.assertEqual(DATABASE_CONNECT_ERROR,
                         resp.json.get('label'), resp.json)
