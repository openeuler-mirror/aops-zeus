#!/usr/bin/python3
# ******************************************************************************
# Copyright (C) 2023 isoftstone Technologies Co., Ltd. All rights reserved.
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
Description: Restful APIs for conf trace
"""
import glob
import json
import os
import queue
import subprocess
import threading
import time

import yaml
from vulcanus import LOGGER
from vulcanus.restful.resp import state
from vulcanus.restful.resp.state import SUCCEED, SERVER_ERROR
from vulcanus.restful.response import BaseResponse

from zeus.conf import configuration
from zeus.conf.constant import KEY_FILE_PREFIX, KEY_FILE_SUFFIX, HOST_PATH_FILE, CONF_TRACE_LOG_PATH, \
    PARENT_DIRECTORY, CONF_TRACE_YML
from zeus.database.proxy.conf_trace import ConfTraceProxy
from zeus.database.proxy.host import HostProxy
from zeus.function.verify.conf_trace import ConfTraceMgmtSchema, ConfTraceDataSchema, ConfTraceQuerySchema, \
    ConfTraceDataDeleteSchema


class ConfTraceMgmt(BaseResponse):
    """
    Interface for register user.
    Restful API: post
    """

    @staticmethod
    def parse_result(action, result, host_ip_trace_result, HOST_FILE):
        code_num = SUCCEED
        code_string = f"{action} ragdoll-filetrace succeed"
        processor_result = result.splitlines()
        char_to_filter = 'unreachable='
        filtered_list = [item for item in processor_result if char_to_filter in item]
        if not filtered_list:
            code_num = SERVER_ERROR
            code_string = f"{action} ragdoll-filetrace error, no result"
        for line in filtered_list:
            result_start_index = line.find(":")
            ip_port = line[0:result_start_index]
            trace_result = host_ip_trace_result.get(ip_port.strip())
            print(trace_result)
            result_str = line[result_start_index:]
            if "unreachable=0" in result_str and "failed=0" in result_str:
                host_ip_trace_result[ip_port.strip()] = True
            else:
                host_ip_trace_result[ip_port.strip()] = False

        # 删除中间文件
        try:
            # 删除/tmp下面以id_dsa结尾的文件
            dsa_file_pattern = "*id_dsa"
            dsa_tmp_files_to_delete = glob.glob(os.path.join(KEY_FILE_PREFIX, dsa_file_pattern))
            for dsa_tmp_file_path in dsa_tmp_files_to_delete:
                os.remove(dsa_tmp_file_path)

            # 删除临时的HOST_PATH_FILE的临时inventory文件
            os.remove(HOST_FILE)
        except OSError as ex:
            LOGGER.error("remove file error: %s", ex)
        return code_num, code_string

    @staticmethod
    def run_subprocess(cmd, result_queue):
        try:
            completed_process = subprocess.run(cmd, cwd=PARENT_DIRECTORY, shell=True, capture_output=True, text=True)
            result_queue.put(completed_process)
        except subprocess.CalledProcessError as ex:
            result_queue.put(ex)

    @staticmethod
    def ansible_handler(now_time, ansible_forks, extra_vars, HOST_FILE):
        if not os.path.exists(CONF_TRACE_LOG_PATH):
            os.makedirs(CONF_TRACE_LOG_PATH)

        CONF_TRACE_LOG = CONF_TRACE_LOG_PATH + "conf_trace_" + now_time + ".log"

        cmd = f"ansible-playbook -f {ansible_forks} -e '{extra_vars}' " \
              f"-i {HOST_FILE} {CONF_TRACE_YML} |tee {CONF_TRACE_LOG} "
        result_queue = queue.Queue()
        thread = threading.Thread(target=ConfTraceMgmt.run_subprocess, args=(cmd, result_queue))
        thread.start()

        thread.join()
        try:
            completed_process = result_queue.get(block=False)
            if isinstance(completed_process, subprocess.CalledProcessError):
                LOGGER.error("ansible subprocess error:", completed_process)
            else:
                if completed_process.returncode == 0:
                    return completed_process.stdout
                else:
                    LOGGER.error("ansible subprocess error:", completed_process)
        except queue.Empty:
            LOGGER.error("ansible subprocess nothing result")

    @staticmethod
    def generate_config(host_list, now_time, conf_files, host_ip_trace_result, domain_name):
        # 取出host_ip,并传入ansible的hosts中
        hosts = {
            "all": {
                "children": {
                    "sync": {
                        "hosts": {

                        }
                    }
                }
            }
        }

        for host in host_list:
            # 生成临时的密钥key文件用于ansible访问远端主机
            key_file_path = KEY_FILE_PREFIX + host['host_ip'] + KEY_FILE_SUFFIX
            with open(key_file_path, 'w', encoding="UTF-8") as keyfile:
                os.chmod(key_file_path, 0o600)
                keyfile.write(host['pkey'])
            host_ip = host['host_ip']
            host_vars = {
                "ansible_host": host_ip,
                "ansible_ssh_user": "root",
                "ansible_ssh_private_key_file": key_file_path,
                "ansible_ssh_port": host['ssh_port'],
                "ansible_python_interpreter": "/usr/bin/python3",
                "host_key_checking": False,
                "interpreter_python": "auto_legacy_silent",
                "become": True,
                "become_method": "sudo",
                "become_user": "root",
                "become_ask_pass": False,
                "ssh_args": "-C -o ControlMaster=auto -o ControlPersist=60s StrictHostKeyChecking=no",
                "host_id": host['host_id']
            }

            hosts['all']['children']['sync']['hosts'][host_ip + "_" + str(host['ssh_port'])] = host_vars
            # 初始化结果
            host_ip_trace_result[host['host_ip'] + "_" + str(host['ssh_port'])] = True

        HOST_FILE = HOST_PATH_FILE + "hosts_" + now_time + ".yml"
        with open(HOST_FILE, 'w') as outfile:
            yaml.dump(hosts, outfile, default_flow_style=False)

    @staticmethod
    def ansible_conf_trace_mgmt(host_list: list, action: str, conf_files: list, domain_name: str):
        now_time = str(int(time.time()))
        host_ip_trace_result = {}
        ConfTraceMgmt.generate_config(host_list, now_time, conf_files, host_ip_trace_result, domain_name)
        ansible_forks = len(host_list)
        # 配置文件中读取并发数量
        # 从内存中获取serial_count
        # serial_count = configuration.serial.get("SERIAL_COUNT")
        # 组装ansible执行的extra参数
        ip = configuration.zeus.get('IP')
        port = configuration.zeus.get("PORT")
        if conf_files:
            conf_list_str = ",".join(conf_files)
        else:
            conf_list_str = ""
        extra_vars = f"action={action} ip={ip} port={port} conf_list_str={conf_list_str} " \
                     f"domain_name={domain_name} "
        # 调用ansible
        try:
            HOST_FILE = HOST_PATH_FILE + "hosts_" + now_time + ".yml"
            result = ConfTraceMgmt.ansible_handler(now_time, ansible_forks, extra_vars, HOST_FILE)
        except Exception as ex:
            LOGGER.error("ansible playbook execute error:", ex)
            conf_trace_mgmt_result = "ragdoll-filetrace ansible playbook execute error"
            return SERVER_ERROR, conf_trace_mgmt_result, host_ip_trace_result
        # 根据action解析每个result
        code_num, code_string = ConfTraceMgmt.parse_result(action, result, host_ip_trace_result, HOST_FILE)
        return code_num, code_string, host_ip_trace_result

    @BaseResponse.handle(schema=ConfTraceMgmtSchema, proxy=HostProxy, token=True)
    def put(self, callback: HostProxy, **params):
        host_ids = params.get("host_ids")
        action = params.get("action")
        conf_files = params.get("conf_files")
        domain_name = params.get("domain_name")

        # 根据id获取host信息
        # Query host address from database
        if not callback.connect():
            return self.response(code=state.DATABASE_CONNECT_ERROR, message="database connect error")

        # 校验token
        status, host_list = callback.get_host_info(
            # 校验token 拿到用户
            {"username": params.get("username"), "host_list": host_ids}, True)
        if status != state.SUCCEED:
            return self.response(code=status, message="get host info error")

        # 组装ansible外部数据
        code_num, code_string, host_ip_trace_result = self.ansible_conf_trace_mgmt(host_list, action, conf_files,
                                                                                   domain_name)
        return self.response(code=code_num, message=code_string, data=host_ip_trace_result)


class ConfTraceData(BaseResponse):
    @staticmethod
    def validate_conf_trace_info(params: dict):
        """
        query conf trace info, validate that the host sync status info is valid
        return host object

        Args:
            params (dict): e.g
            {
                "domain_name": "aops",
                "host_id": 1,
                "conf_name": "/etc/hostname",
                "info": ""
            }

        Returns:
            tuple:
                status code, host sync status object
        """
        # 检查host 是否存在
        host_proxy = HostProxy()
        if not host_proxy.connect():
            LOGGER.error("Connect to database error")
            return state.DATABASE_CONNECT_ERROR, {}
        data = {"host_list": [params.get("host_id")]}
        code_num, result_list = host_proxy.get_host_info_by_host_id(data)
        if code_num != SUCCEED:
            LOGGER.error("query host info error")
            return state.DATABASE_QUERY_ERROR, {}
        if len(result_list) == 0:
            return state.NO_DATA, []
        return code_num, result_list

    @BaseResponse.handle(schema=ConfTraceDataSchema, proxy=ConfTraceProxy, token=False)
    def post(self, callback: ConfTraceProxy, **params):
        # 校验hostId是否存在
        code_num, result_list = self.validate_conf_trace_info(params)
        if code_num != SUCCEED or len(result_list) == 0:
            return self.response(code=SERVER_ERROR, message="request param host id does not exist")

        status_code = callback.add_conf_trace_info(params)
        if status_code != state.SUCCEED:
            return self.response(code=SERVER_ERROR, message="Failed to upload data, service error")
        return self.response(code=SUCCEED, message="Succeed to upload conf trace info data")


class ConfTraceQuery(BaseResponse):
    @BaseResponse.handle(schema=ConfTraceQuerySchema, proxy=ConfTraceProxy, token=True)
    def post(self, callback: ConfTraceProxy, **params):
        status_code, result = callback.query_conf_trace_info(params)
        if status_code != SUCCEED:
            return self.response(code=SERVER_ERROR, message="Failed to query data, service error")
        return self.response(code=SUCCEED, message="Succeed to query conf trace info data", data=result)


class ConfTraceDataDelete(BaseResponse):
    @BaseResponse.handle(schema=ConfTraceDataDeleteSchema, proxy=ConfTraceProxy, token=True)
    def post(self, callback: ConfTraceProxy, **params):
        status_code = callback.delete_conf_trace_info(params)
        if status_code != state.SUCCEED:
            return self.response(code=SERVER_ERROR, message="Failed to delete data, service error")
        return self.response(code=SUCCEED, message="Succeed to delete conf trace info data")
