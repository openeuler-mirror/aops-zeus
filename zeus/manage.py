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
Description: Manager that start aops-zeus
"""
import os
import sqlalchemy

from vulcanus.database.table import User, Base, create_utils_tables
from vulcanus.conf.constant import BASE_CONFIG_PATH
from vulcanus.log.log import LOGGER
from vulcanus.restful.status import SUCCEED
from vulcanus.manage import init_app
from vulcanus.readconfig import read_json_config_file
from zeus.conf import configuration
from zeus.database import SESSION, ENGINE
from zeus.database.factory.mapping import MAPPINGS
from zeus.database.proxy.deploy import DeployProxy
from zeus.database.proxy.account import UserProxy

DEFAULT_TASK_PATH = os.path.join(BASE_CONFIG_PATH, 'default.json')


def init_user():
    """
    Initialize user, add a default user: admin
    """
    try:
        create_utils_tables(Base, ENGINE)
    except sqlalchemy.exc.SQLAlchemyError:
        raise sqlalchemy.exc.SQLAlchemyError("create tables fail")

    proxy = UserProxy()
    if not proxy.connect(SESSION):
        raise ValueError("connect to mysql fail")

    data = {
        "username": "admin",
        "password": "changeme"
    }
    res = proxy.select([User.username], {"username": data['username']})
    # user has been added to database, return
    if res[1]:
        return

    res = proxy.add_user(data)
    if res != SUCCEED:
        raise ValueError("add admin user fail")

    LOGGER.info("initialize default admin user succeed")


def init_es():
    """
    Initialize elasticsearch index and add default task
    """
    proxy = DeployProxy(configuration=configuration)
    if not proxy.connect():
        raise ValueError("connect to elasticsearch fail")

    for index_name, body in MAPPINGS.items():
        res = proxy.create_index(index_name, body)
        if not res:
            raise ValueError("create elasticsearch index %s fail", index_name)

    LOGGER.info("create elasticsearch index succeed")
    # update es settings
    settings = {
        "max_result_window": configuration.elasticsearch.get('MAX_ES_QUERY_NUM')
    }
    proxy.update_settings(**settings)
    # add default task
    data = {
        "username": "",
        "task_list": [""]
    }
    task_info = read_json_config_file(DEFAULT_TASK_PATH)
    if task_info is None:
        return

    for default_task in task_info['tasks']:
        data["username"] = default_task["username"]
        data["task_list"][0] = default_task["task_id"]
        task_name = default_task["task_name"]
        res = proxy.get_task(data)
        if res[1]["task_infos"]:
            LOGGER.info("default task %s has existed, ignore", task_name)
            continue
        res = proxy.add_task(default_task)


def init_database():
    """
    Initialize database
    """
    init_user()
    init_es()


init_database()
app, config = init_app('zeus')

if __name__ == "__main__":
    ip = config.get('IP')
    port = config.get('PORT')
    app.run(host=ip, port=port)
