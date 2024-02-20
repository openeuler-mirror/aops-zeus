#!/usr/bin/python3
#  ******************************************************************************
#  Copyright (C) 2023 isoftstone Technologies Co., Ltd. All rights reserved.
#  licensed under the Mulan PSL v2.
#  You can use this software according to the terms and conditions of the Mulan PSL v2.
#  You may obtain a copy of Mulan PSL v2 at:
#      http://license.coscl.org.cn/MulanPSL2
#  THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
#  PURPOSE.
#  See the Mulan PSL v2 for more details.
#  ******************************************************************************/
"""
@FileName: conf_tools.py
@Time: 2024/1/22 13:38
@Author: JiaoSiMao
Description:
"""
import ast
import configparser
import os

from zeus.conf import MANAGER_CONFIG_PATH


class ConfTools(object):

    @staticmethod
    def load_url_by_conf():
        """
        desc: get the url of sync conf
        """
        cf = configparser.ConfigParser()
        if os.path.exists(MANAGER_CONFIG_PATH):
            cf.read(MANAGER_CONFIG_PATH, encoding="utf-8")
        else:
            parent = os.path.dirname(os.path.realpath(__file__))
            conf_path = os.path.join(parent, "../config/zeus.ini")
            cf.read(conf_path, encoding="utf-8")

        update_sync_status_address = ast.literal_eval(cf.get("update_sync_status", "update_sync_status_address"))
        domain_list_api = ast.literal_eval(cf.get("update_sync_status", "domain_list_api"))
        expected_confs_api = ast.literal_eval(cf.get("update_sync_status", "expected_confs_api"))
        domain_conf_diff_api = ast.literal_eval(cf.get("update_sync_status", "domain_conf_diff_api"))

        update_sync_status_port = str(cf.get("update_sync_status", "update_sync_status_port"))
        domain_list_url = "{address}:{port}{api}".format(address=update_sync_status_address, api=domain_list_api,
                                                         port=update_sync_status_port)
        expected_confs_url = "{address}:{port}{api}".format(address=update_sync_status_address, api=expected_confs_api,
                                                            port=update_sync_status_port)
        domain_conf_diff_url = "{address}:{port}{api}".format(address=update_sync_status_address,
                                                              api=domain_conf_diff_api,
                                                              port=update_sync_status_port)

        url = {"domain_list_url": domain_list_url, "expected_confs_url": expected_confs_url,
               "domain_conf_diff_url": domain_conf_diff_url}
        return url
