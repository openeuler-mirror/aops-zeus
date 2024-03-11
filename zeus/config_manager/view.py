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
Description: Restful APIs for host
"""
import glob
import json
import os
import queue
import subprocess
import threading
import time
from configparser import RawConfigParser
from typing import List, Dict

import yaml
from vulcanus import LOGGER
from vulcanus.multi_thread_handler import MultiThreadHandler
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse

from zeus.conf import configuration
from zeus.conf.constant import CERES_COLLECT_FILE, CERES_SYNC_CONF, CERES_OBJECT_FILE_CONF, SYNC_LOG_PATH, \
    HOST_PATH_FILE, SYNC_CONFIG_YML, PARENT_DIRECTORY, IP_START_PATTERN, KEY_FILE_PREFIX, KEY_FILE_SUFFIX
from zeus.database.proxy.host import HostProxy
from zeus.function.model import ClientConnectArgs
from zeus.function.verify.config import CollectConfigSchema, SyncConfigSchema, ObjectFileConfigSchema, \
    BatchSyncConfigSchema
from zeus.host_manager.ssh import execute_command_and_parse_its_result, execute_command_sftp_result


class CollectConfig(BaseResponse):
    """
    Interface for collect config.
    Restful API: POST
    """

    @staticmethod
    def get_file_content(host_info: Dict, file_list: list) -> Dict:
        """
            Get target file content from ceres.

        Args:
            host_info (dict): e.g
                {
                    host_id : xx,
                    address : xx,
                    header  : xx
                }
            file_list (list): e.g
                ["/etc/test.txt", "/tmp/test.csv"]
        Returns:
            dict: e.g
            {
                'fail_files': [],
                'infos': [{
                    'content': 'string',
                    'file_attr': {
                    'group': 'root',
                    'mode': '0644',
                    'owner': 'root'},
                    'path': 'file_path'
                    }],
                'success_files': ['file_path'],
                'host_id': 'host_id'
            }

        """
        command = CERES_COLLECT_FILE % json.dumps(file_list)
        status, content = execute_command_and_parse_its_result(
            ClientConnectArgs(
                host_info.get("host_ip"), host_info.get("ssh_port"), host_info.get("ssh_user"), host_info.get("pkey")
            ),
            command,
        )
        if status == state.SUCCEED:
            data = json.loads(content)
            data.update({"host_id": host_info["host_id"]})
            return data
        return {"host_id": host_info["host_id"], "config_file_list": file_list}

    @staticmethod
    def convert_host_id_to_failed_data_format(host_id_list: list, host_id_with_file: dict) -> list:
        """
        convert host id which can't visit to target data format

        Args:
            host_id_list (list)
            host_id_with_file: host id and all requested file path. e.g
                {
                    host_id_1: [config_path_1, config_path_2, ...],
                    host_id_2: [config_path_1, config_path_2, ...]
                }

        Returns:
            List[Dict]:  e.g
                [{
                    host_id: host_id,
                    success_files: [],
                    fail_files: [all file path],
                    infos: []
               }]
        """
        return [
            {'host_id': host_id, 'success_files': [], 'fail_files': host_id_with_file.get(host_id), 'infos': []}
            for host_id in host_id_list
        ]

    def generate_target_data_format(self, collect_result_list: List[Dict], host_id_with_file: Dict[str, List]) -> List:
        """
        Generate target data format


        Args:
            collect_result_list: file content list
            host_id_with_file:  host id and all requested file path

        Returns:
            target data format: e.g
                [
                    {
                        host_id: host_id,
                        infos: [
                            path: file_path,
                            content: string,
                            file_attr: {
                                owner: root,
                                mode: 0644,
                                group: root
                            }
                        ],
                        success_files:[ file_path ],
                        fail_files:[ file_path ]
                    }
                ]
        """
        file_content = []
        valid_host_id = set()
        for collect_result in collect_result_list:
            if collect_result.get('infos') is not None:
                file_content.append(collect_result)
                valid_host_id.add(collect_result.get('host_id'))

        invalid_host_id = set(host_id_with_file.keys()) - valid_host_id
        read_failed_data = self.convert_host_id_to_failed_data_format(list(invalid_host_id), host_id_with_file)
        file_content.extend(read_failed_data)

        return file_content

    @BaseResponse.handle(schema=CollectConfigSchema, token=True)
    def post(self, **param):
        """
        Get config
        Args:
            request(json): {
                "infos": [{
                    "host_id": "f",
                    "config_list": ["/xx", "/exxxo"]
                }]
            }
        Returns:
            dict: e.g
            {
                code: int,
                msg: string,
                resp:[
                    {
                        host_id: host_id,
                        infos: [
                            path: file_path1,
                            content: string,
                            file_attr: {
                                owner: root,
                                mode: 0644,
                                group: root
                            }
                            ...
                        ],
                        success_files:[
                            file_path1,
                            file_path2,
                            ...
                        ]
                        fail_files:[
                            file_path3,
                            ...
                        ]
                    }
                    ...
                ]
            }
        """
        # Get host id list
        host_id_with_config_file = {}
        for host in param.get('infos'):
            host_id_with_config_file[host.get('host_id')] = host.get('config_list')

        # Query host address from database
        proxy = HostProxy()
        if not proxy.connect():
            file_content = self.convert_host_id_to_failed_data_format(
                list(host_id_with_config_file.keys()), host_id_with_config_file
            )
            return self.response(code=state.DATABASE_CONNECT_ERROR, data=file_content)

        status, host_list = proxy.get_host_info(
            {"username": param.get("username"), "host_list": list(host_id_with_config_file.keys())}, True
        )
        if status != state.SUCCEED:
            file_content = self.convert_host_id_to_failed_data_format(
                list(host_id_with_config_file.keys()), host_id_with_config_file
            )
            return self.response(code=status, data=file_content)
        # Get file content
        tasks = [(host, host_id_with_config_file[host["host_id"]]) for host in host_list]
        multi_thread = MultiThreadHandler(lambda data: self.get_file_content(*data), tasks, None)
        multi_thread.create_thread()

        return self.response(
            state.SUCCEED, None, self.generate_target_data_format(multi_thread.get_result(), host_id_with_config_file)
        )


class SyncConfig(BaseResponse):
    @staticmethod
    def sync_config_by_execute_command_sftp(host_info: Dict, sync_config_info: Dict, local_path: str,
                                            remote_path: str):
        content = sync_config_info.get("content")
        with open(local_path, "w", encoding="UTF-8") as f:
            f.write(content)
        status = execute_command_sftp_result(
            ClientConnectArgs(host_info.get("host_ip"), host_info.get("ssh_port"),
                              host_info.get("ssh_user"), host_info.get("pkey")), local_path, remote_path)
        return status

    @staticmethod
    def sync_config_content(host_info: Dict, sync_config_info: Dict):
        join_path = "/tmp"
        if sync_config_info.get("file_path") == "/etc/profile":
            local_path = os.path.join(join_path, "profile")
            remote_path = "/etc/profile"
            status = SyncConfig.sync_config_by_execute_command_sftp(host_info, sync_config_info, local_path,
                                                                    remote_path)
            return status
        elif sync_config_info.get("file_path") == "/etc/rc.local":
            local_path = os.path.join(join_path, "rc.local")
            remote_path = "/etc/rc.local"
            status = SyncConfig.sync_config_by_execute_command_sftp(host_info, sync_config_info, local_path,
                                                                    remote_path)
            return status
        elif sync_config_info.get("file_path") == "/etc/bashrc":
            local_path = os.path.join(join_path, "bashrc")
            remote_path = "/etc/bashrc"
            status = SyncConfig.sync_config_by_execute_command_sftp(host_info, sync_config_info, local_path,
                                                                    remote_path)
            return status
        else:
            command = CERES_SYNC_CONF % json.dumps(sync_config_info)

            status, content = execute_command_and_parse_its_result(
                ClientConnectArgs(host_info.get("host_ip"), host_info.get("ssh_port"),
                                  host_info.get("ssh_user"), host_info.get("pkey")), command)
            return status

    @BaseResponse.handle(schema=SyncConfigSchema, token=True)
    def put(self, **params):

        sync_config_info = dict()
        sync_config_info['file_path'] = params.get('file_path')
        sync_config_info['content'] = params.get('content')

        sync_result = {
            "file_path": sync_config_info['file_path'],
            "sync_result": False
        }

        # Query host address from database
        proxy = HostProxy()
        if not proxy.connect():
            return self.response(code=state.DATABASE_CONNECT_ERROR, data=sync_result)

        status, host_list = proxy.get_host_info(
            {"username": params.get("username"), "host_list": [params.get('host_id')]}, True)
        if status != state.SUCCEED:
            return self.response(code=status, data=sync_result)

        host_info = host_list[0]
        status = self.sync_config_content(host_info, sync_config_info)
        if status == state.SUCCEED:
            sync_result['sync_result'] = True
            return self.response(code=state.SUCCEED, data=sync_result)
        return self.response(code=state.UNKNOWN_ERROR, data=sync_result)


class ObjectFileConfig(BaseResponse):

    @staticmethod
    def object_file_config_content(host_info: Dict, file_directory: str):
        command = CERES_OBJECT_FILE_CONF % file_directory
        status, content = execute_command_and_parse_its_result(
            ClientConnectArgs(host_info.get("host_ip"), host_info.get("ssh_port"),
                              host_info.get("ssh_user"), host_info.get("pkey")), command)
        return status, content

    @BaseResponse.handle(schema=ObjectFileConfigSchema, token=True)
    def post(self, **params):
        object_file_result = {
            "object_file_paths": list(),
            "object_file_result": False
        }
        # Query host address from database
        proxy = HostProxy()
        if not proxy.connect():
            return self.response(code=state.DATABASE_CONNECT_ERROR, data=object_file_result)

        status, host_list = proxy.get_host_info(
            {"username": params.get("username"), "host_list": [params.get('host_id')]}, True)
        if status != state.SUCCEED:
            return self.response(code=status, data=object_file_result)

        host_info = host_list[0]
        status, content = self.object_file_config_content(host_info, params.get('file_directory'))
        if status == state.SUCCEED:
            object_file_result['object_file_result'] = True
            content_res = json.loads(content)
            if content_res.get("resp"):
                resp = content_res.get("resp")
                object_file_result['object_file_paths'] = resp
            return self.response(code=state.SUCCEED, data=object_file_result)
        return self.response(code=state.UNKNOWN_ERROR, data=object_file_result)


class BatchSyncConfig(BaseResponse):
    @staticmethod
    def run_subprocess(cmd, result_queue):
        try:
            completed_process = subprocess.run(cmd, cwd=PARENT_DIRECTORY, shell=True, capture_output=True, text=True)
            result_queue.put(completed_process)
        except subprocess.CalledProcessError as ex:
            result_queue.put(ex)

    @staticmethod
    def ansible_handler(now_time, ansible_forks, extra_vars, HOST_FILE):
        if not os.path.exists(SYNC_LOG_PATH):
            os.makedirs(SYNC_LOG_PATH)

        SYNC_LOG = SYNC_LOG_PATH + "sync_config_" + now_time + ".log"
        cmd = f"ansible-playbook -f {ansible_forks} -e '{extra_vars}' " \
              f"-i {HOST_FILE} {SYNC_CONFIG_YML} |tee {SYNC_LOG} "
        result_queue = queue.Queue()
        thread = threading.Thread(target=BatchSyncConfig.run_subprocess, args=(cmd, result_queue))
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
    def ansible_sync_domain_config_content(host_list: list, file_path_infos: list):
        # 初始化参数和响应
        now_time = str(int(time.time()))
        host_ip_sync_result = {}
        BatchSyncConfig.generate_config(host_list, host_ip_sync_result, now_time)

        ansible_forks = len(host_list)
        # 配置文件中读取并发数量
        # 从内存中获取serial_count
        serial_count = configuration.serial.get("SERIAL_COUNT")
        # 换种方式
        path_infos = {}
        for file_info in file_path_infos:
            file_path = file_info.get("file_path")
            file_content = file_info.get("content")
            # 写临时文件
            src_file_path = "/tmp/" + os.path.basename(file_path)
            with open(src_file_path, "w", encoding="UTF-8") as f:
                f.write(file_content)
            path_infos[src_file_path] = file_path

        # 调用ansible
        extra_vars = json.dumps({"serial_count": serial_count, "file_path_infos": path_infos})
        try:
            HOST_FILE = HOST_PATH_FILE + "hosts_" + now_time + ".yml"
            result = BatchSyncConfig.ansible_handler(now_time, ansible_forks, extra_vars, HOST_FILE)
        except Exception as ex:
            LOGGER.error("ansible playbook execute error:", ex)
            return host_ip_sync_result

        processor_result = result.splitlines()
        char_to_filter = 'item='
        filtered_list = [item for item in processor_result if char_to_filter in item]
        if not filtered_list:
            return host_ip_sync_result
        for line in filtered_list:
            start_index = line.find("[") + 1
            end_index = line.find("]", start_index)
            ip_port = line[start_index:end_index]
            sync_results = host_ip_sync_result.get(ip_port)

            start_index1 = line.find("{")
            end_index1 = line.find(")", start_index1)
            path_str = line[start_index1:end_index1]
            file_path = json.loads(path_str.replace("'", "\"")).get("value")
            if line.startswith("ok:") or line.startswith("changed:"):
                signal_file_sync = {
                    "filePath": file_path,
                    "result": "SUCCESS"
                }
            else:
                signal_file_sync = {
                    "filePath": file_path,
                    "result": "FAIL"
                }
            sync_results.append(signal_file_sync)
        # 删除中间文件
        try:
            # 删除/tmp下面以id_dsa结尾的文件
            file_pattern = "*id_dsa"
            tmp_files_to_delete = glob.glob(os.path.join(KEY_FILE_PREFIX, file_pattern))
            for tmp_file_path in tmp_files_to_delete:
                os.remove(tmp_file_path)

            # 删除/tmp下面临时写的path_infos的key值文件
            for path in path_infos.keys():
                os.remove(path)

            # 删除临时的HOST_PATH_FILE的临时inventory文件
            os.remove(HOST_FILE)
        except OSError as ex:
            LOGGER.error("remove file error: %s", ex)
        return host_ip_sync_result

    @staticmethod
    def generate_config(host_list, host_ip_sync_result, now_time):
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
                "ssh_args": "-C -o ControlMaster=auto -o ControlPersist=60s StrictHostKeyChecking=no"
            }

            hosts['all']['children']['sync']['hosts'][host_ip + "_" + str(host['ssh_port'])] = host_vars
            # 初始化结果
            host_ip_sync_result[host['host_ip'] + "_" + str(host['ssh_port'])] = list()
        HOST_FILE = HOST_PATH_FILE + "hosts_" + now_time + ".yml"
        with open(HOST_FILE, 'w') as outfile:
            yaml.dump(hosts, outfile, default_flow_style=False)

    @staticmethod
    def ini2json(ini_path):
        json_data = {}
        cfg = RawConfigParser()
        cfg.read(ini_path)
        for s in cfg.sections():
            json_data[s] = dict(cfg.items(s))
        return json_data

    @BaseResponse.handle(schema=BatchSyncConfigSchema, proxy=HostProxy, token=True)
    def put(self, callback: HostProxy, **params):
        # 初始化响应
        file_path_infos = params.get('file_path_infos')
        host_ids = params.get('host_ids')
        sync_result = list()
        # Query host address from database
        if not callback.connect():
            return self.response(code=state.DATABASE_CONNECT_ERROR, data=sync_result)

        # 校验token
        status, host_list = callback.get_host_info(
            # 校验token 拿到用户
            {"username": params.get("username"), "host_list": host_ids}, True)
        if status != state.SUCCEED:
            return self.response(code=status, data=sync_result)

        # 将ip和id对应起来
        host_id_ip_dict = dict()
        if host_list:
            for host in host_list:
                key = host['host_ip'] + str(host['ssh_port'])
                host_id_ip_dict[key] = host['host_id']

        host_ip_sync_result = self.ansible_sync_domain_config_content(host_list, file_path_infos)

        if not host_ip_sync_result:
            return self.response(code=state.EXECUTE_COMMAND_ERROR, data=sync_result)
        # 处理成id对应结果
        for key, value in host_ip_sync_result.items():
            host_id = host_id_ip_dict.get(key)
            single_result = {
                "host_id": host_id,
                "syncResult": value
            }
            sync_result.append(single_result)
        return self.response(code=state.SUCCEED, data=sync_result)
