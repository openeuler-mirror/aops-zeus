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
@FileName: update_config_sync_status_task.py
@Time: 2024/3/5 16:56
@Author: JiaoSiMao
Description:
"""
import json

import requests
from vulcanus.log.log import LOGGER
from vulcanus.timed import TimedTask
from vulcanus.database.helper import make_mysql_engine_url, create_database_engine
from vulcanus.database.proxy import MysqlProxy
from vulcanus.restful.resp import state
from vulcanus.restful.resp.state import SUCCEED

from zeus.conf import configuration
from zeus.conf.constant import DIRECTORY_FILE_PATH_LIST
from zeus.config_manager.view import ObjectFileConfig, CollectConfig
from zeus.database.proxy.host import HostProxy
from zeus.database.proxy.host_sync_status import HostSyncProxy
from zeus.scheduler_task.view import SyncStatus
from zeus.utils.conf_tools import ConfTools


class UpdateConfigSyncStatusTask(TimedTask):
    @staticmethod
    def get_domain_files(domain_paths: dict, expected_confs_resp: list):
        # 获取domain中要获取文件内容的文件路径
        for domain_confs in expected_confs_resp:
            domain_name = domain_confs.get("domainName")
            conf_base_infos = domain_confs.get("confBaseInfos")
            file_list = []
            if conf_base_infos:
                for conf_info in conf_base_infos:
                    file_list.append(conf_info.get("filePath"))
            domain_paths[domain_name] = file_list

    @staticmethod
    def deal_pam_d_config(host_info, directory_path):
        # 先获取/etc/pam.d下有哪些文件
        status, content = ObjectFileConfig.object_file_config_content(
            host_info, directory_path
        )
        if status == state.SUCCEED:
            content_dict = json.loads(content)
            directory_paths = content_dict.get("resp")
            return directory_paths
        return []

    @staticmethod
    def deal_host_file_content(domain_result, host_file_content_result):
        host_id = host_file_content_result.get("host_id")
        infos = host_file_content_result.get("infos")
        file_content_list = []
        pam_d_file_list = []
        if infos:
            for info in infos:
                pam_d_file = {}
                info_path = str(info.get("path"))
                for file_path in DIRECTORY_FILE_PATH_LIST:
                    if info_path.find(file_path) == -1:
                        signal_file_content = {
                            "filePath": info.get("path"),
                            "contents": info.get("content"),
                        }
                        file_content_list.append(signal_file_content)
                    else:
                        pam_d_file[info_path] = info.get("content")
                        pam_d_file_list.append(pam_d_file)
        if pam_d_file_list:
            directory_file_dict = {}
            for file_path in DIRECTORY_FILE_PATH_LIST:
                directory_file_dict[file_path] = {}
            for path, content_list in directory_file_dict.items():
                for pam_d_file in pam_d_file_list:
                    pam_d_file_path = str(list(pam_d_file.keys())[0])
                    if path in pam_d_file_path:
                        content_list[pam_d_file_path] = pam_d_file.get(pam_d_file_path)
            for key, value in directory_file_dict.items():
                pam_d_file_content = {"filePath": key, "contents": json.dumps(value)}
                file_content_list.append(pam_d_file_content)
        if file_content_list:
            domain_result[str(host_id)] = file_content_list

    def collect_file_infos(self, param, host_infos_result):
        # 组装host_id和要获取内容的文件列表 一一对应
        domain_result = {}
        host_id_with_config_file = {}
        for host in param.get("infos"):
            host_id_with_config_file[host.get("host_id")] = host.get("config_list")

        for host_id, file_list in host_id_with_config_file.items():
            host_info = host_infos_result.get(host_id)
            # 处理/etc/pam.d
            for file_path in DIRECTORY_FILE_PATH_LIST:
                if file_path in file_list:
                    file_list.remove(file_path)
                    object_file_paths = self.deal_pam_d_config(host_info, file_path)
                    if object_file_paths:
                        file_list.extend(object_file_paths)
            host_file_content_result = CollectConfig.get_file_content(
                host_info, file_list
            )
            # 处理结果
            self.deal_host_file_content(domain_result, host_file_content_result)
        return domain_result

    @staticmethod
    def make_database_engine():
        engine_url = make_mysql_engine_url(configuration)
        MysqlProxy.engine = create_database_engine(
            engine_url,
            configuration.mysql.get("POOL_SIZE"),
            configuration.mysql.get("POOL_RECYCLE"),
        )

    @staticmethod
    def get_domain_host_ids(domain_list_resp, host_sync_proxy):
        domain_host_id_dict = {}
        for domain in domain_list_resp:
            domain_name = domain["domainName"]
            status, host_sync_infos = host_sync_proxy.get_domain_host_sync_status(
                domain_name
            )
            if status != SUCCEED or not host_sync_infos:
                continue
            host_ids = [host_sync["host_id"] for host_sync in host_sync_infos]
            domain_host_id_dict[domain_name] = host_ids
        return domain_host_id_dict

    @staticmethod
    def get_all_host_infos():
        host_infos_result = {}
        proxy = HostProxy()
        proxy.connect()
        status, host_list = proxy.get_host_info(
            {"username": "admin", "host_list": list()}, True
        )
        if status != state.SUCCEED:
            return {}
        for host in host_list:
            host_infos_result[host["host_id"]] = host
        return host_infos_result

    @staticmethod
    def compare_conf(expected_confs_resp, domain_result):
        headers = {"Content-Type": "application/json"}
        # 获取所有的domain
        domain_conf_diff_url = ConfTools.load_url_by_conf().get("domain_conf_diff_url")
        # 调用ragdoll接口比对
        try:
            request_data = {
                "expectedConfsResp": expected_confs_resp,
                "domainResult": domain_result,
            }
            domain_diff_response = requests.post(
                domain_conf_diff_url, data=json.dumps(request_data), headers=headers
            )
            domain_diff_resp = json.loads(domain_diff_response.text)
            if domain_diff_resp:
                return domain_diff_resp
            return []
        except requests.exceptions.RequestException as connect_ex:
            LOGGER.error(f"Failed to get domain list, an error occurred: {connect_ex}")
            return []

    @staticmethod
    def update_sync_status_for_db(domain_diff_resp, host_sync_proxy):
        if domain_diff_resp:
            status, save_ids = host_sync_proxy.update_domain_host_sync_status(
                domain_diff_resp
            )
            update_result = sum(save_ids)
            if status != SUCCEED or update_result == 0:
                LOGGER.error("failed update host sync status data")
            if update_result > 0:
                LOGGER.info(
                    "update %s host sync status  basic info succeed", update_result
                )
        else:
            LOGGER.info("no host sync status data need to update")
            return

    def execute(self):
        headers = {"Content-Type": "application/json"}
        # 获取所有的domain
        domain_list_url = ConfTools.load_url_by_conf().get("domain_list_url")
        try:
            domain_list_response = requests.post(domain_list_url, headers=headers)
            domain_list_resp = json.loads(domain_list_response.text)
        except requests.exceptions.RequestException as connect_ex:
            LOGGER.error(f"Failed to get domain list, an error occurred: {connect_ex}")
            return
        # 处理响应
        if not domain_list_resp:
            LOGGER.error(
                "Failed to get all domain, please check interface /domain/queryDomain"
            )
            return

        # 调用ragdoll query_excepted_confs接口获取所有业务域的基线配置内容
        domain_list_url = ConfTools.load_url_by_conf().get("expected_confs_url")
        domain_names = {"domainNames": domain_list_resp}
        try:
            expected_confs_response = requests.post(
                domain_list_url, data=json.dumps(domain_names), headers=headers
            )
            expected_confs_resp = json.loads(expected_confs_response.text)
        except requests.exceptions.RequestException as connect_ex:
            LOGGER.error(
                f"Failed to get all domain expected conf list, an error occurred: {connect_ex}"
            )
            return
        if not expected_confs_resp:
            LOGGER.error(
                "Failed to get all domain confs, please check interface /confs/queryExpectedConfs"
            )
            return

        # 方式一 创建数据引擎
        self.make_database_engine()
        # 方式一 根据domain获取所有的id，从host_conf_sync_status表中读取
        host_sync_proxy = HostSyncProxy()
        host_sync_proxy.connect()
        domain_host_id_dict = SyncStatus.get_domain_host_ids(
            domain_list_resp, host_sync_proxy
        )
        if not domain_host_id_dict:
            LOGGER.info("no host sync status data need to update")
            return
        # 获取所有admin下面的ip的信息
        host_infos_result = self.get_all_host_infos()
        if not host_infos_result:
            LOGGER.info("no host sync status data need to update")
            return

        # 方式一 组装参数并调用CollectConfig接口get_file_content获取文件真实内容
        domain_paths = {}
        self.get_domain_files(domain_paths, expected_confs_resp)

        domain_result = {}
        for domain_name, host_id_list in domain_host_id_dict.items():
            data = {"infos": []}
            file_paths = domain_paths.get(domain_name)
            if file_paths:
                for host_id in host_id_list:
                    data_info = {"host_id": host_id, "config_list": file_paths}
                    data["infos"].append(data_info)
            if data["infos"]:
                result = self.collect_file_infos(data, host_infos_result)
                domain_result[domain_name] = result
        # 调用ragdoll接口进行对比
        domain_diff_resp = self.compare_conf(expected_confs_resp, domain_result)
        # 根据结果更新数据库
        self.update_sync_status_for_db(domain_diff_resp, host_sync_proxy)
