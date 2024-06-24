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
Description: default config of manager
"""
zeus = {"IP": "127.0.0.1", "PORT": 11111}

mysql = {
    "IP": "127.0.0.1",
    "PORT": 3306,
    "DATABASE_NAME": "aops",
    "ENGINE_FORMAT": "mysql+pymysql://@%s:%s/%s",
    "POOL_SIZE": 100,
    "POOL_RECYCLE": 7200,
}

diana = {"IP": "127.0.0.1", "PORT": 11112}

apollo = {"IP": "127.0.0.1", "PORT": 11116}

redis = {"IP": "127.0.0.1", "PORT": 6379}

prometheus = {"IP": "127.0.0.1", "PORT": 9090, "QUERY_RANGE_STEP": "15s"}

agent = {"DEFAULT_INSTANCE_PORT": 8888}

serial = {"SERIAL_COUNT": 10}

update_sync_status = {"UPDATE_SYNC_STATUS_ADDRESS": "http://127.0.0.1", "UPDATE_SYNC_STATUS_PORT": 11114}
