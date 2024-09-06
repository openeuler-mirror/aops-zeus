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
import json
import socket
import uuid
from dataclasses import dataclass
from io import BytesIO, StringIO
from typing import Tuple

import gevent
import paramiko
from flask import request, send_file
from gevent.pool import Pool
from paramiko.ssh_exception import SSHException
from vulcanus.conf.constant import CERES_HOST_INFO, UserRoleType
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse
from vulcanus.restful.serialize.validate import validate

from zeus.host_information_service.app import cache
from zeus.host_information_service.app.constant import HostTemplate, HostStatus
from zeus.host_information_service.app.core.ssh import SSH, generate_key
from zeus.host_information_service.app.proxy.host import HostProxy
from zeus.host_information_service.app.serialize.host import (
    AddHostBatchSchema,
    AddHostSchema,
    BatchHostsSchema,
    GetHostsPage_RequestSchema,
    HostFilterSchema,
    HostInfoSchema,
    HostsInfo_ResponseSchema,
    TemplateLangSchema,
    UpdateHostSchema,
    UpdateHostStatusSchema,
    HostIpsFilterSchema,
)
from zeus.host_information_service.database import Host


@dataclass
class ClientConnect:
    """
    ClientConnectModel - model defined

    Args:
        host_ip: host public ip
        ssh_port: ssh remote login port
        ssh_user: ssh remote login user
        pkey: RSA-KEY string used for authentication
        timeout: timeout opening a channel, default 10s

    """

    host_ip: str
    ssh_port: int
    ssh_user: str
    pkey: str
    timeout: int = 10


class SSH_Verify:
    def _verify_ssh_identity(self, ssh_login_info: ClientConnect) -> str:
        """
        Verify that the ssh login information is correct

        Args:
            ssh_login_info(ClientConnect): e.g
                ClientConnect(host_ip='127.0.0.1', ssh_port=22, ssh_user='root', pkey=RSAKey string)

        Returns:
            status code
        """
        try:
            client = SSH(
                ip=ssh_login_info.host_ip,
                username=ssh_login_info.ssh_user,
                port=ssh_login_info.ssh_port,
                pkey=paramiko.RSAKey.from_private_key(StringIO(ssh_login_info.pkey)),
            )
            client.close()
        except socket.error as error:
            LOGGER.info(f"Failed to connect to host %s: %s", ssh_login_info.host_ip, error)
            return state.SSH_CONNECTION_ERROR
        except SSHException as error:
            LOGGER.info(f"Failed to connect to host %s: %s", ssh_login_info.host_ip, error)
            return state.SSH_AUTHENTICATION_ERROR
        except IndexError:
            LOGGER.error(
                f"Failed to connect to host %s because the pkey of the host are missing", ssh_login_info.host_ip
            )
            return state.SSH_AUTHENTICATION_ERROR
        except Exception as error:
            LOGGER.error(f"Failed to connect to host %s: %s", ssh_login_info.host_ip, error)
            return state.SSH_CONNECTION_ERROR

        return state.SUCCEED

    @staticmethod
    def _verify_ssh_identity_and_get_os_info(ssh_login_info) -> Tuple[str, str]:
        """
        Verify that the ssh login information is correct

        Args:
            ssh_login_info(ClientConnectArgs): e.g
                ClientConnectArgs(host_ip='127.0.0.1', ssh_port=22, ssh_user='root', pkey=RSAKey string)

        Returns:
            status code, os_info
        """
        client, stdout = None, ","
        try:
            client = SSH(
                ip=ssh_login_info.host_ip,
                username=ssh_login_info.ssh_user,
                port=ssh_login_info.ssh_port,
                pkey=paramiko.RSAKey.from_private_key(StringIO(ssh_login_info.pkey)),
            )
            _, stdout, _ = client.execute_command("source /etc/os-release && echo -n $(arch),$NAME")
        except socket.error as error:
            LOGGER.error(f"Failed to connect to host %s: %s", ssh_login_info.host_ip, error)
            return state.SSH_CONNECTION_ERROR, stdout
        except SSHException as error:
            LOGGER.error(f"Failed to connect to host %s: %s", ssh_login_info.host_ip, error)
            return state.SSH_AUTHENTICATION_ERROR, stdout
        except IndexError:
            LOGGER.error(
                f"Failed to connect to host %s because the pkey of the host are missing", ssh_login_info.host_ip
            )
            return state.SSH_AUTHENTICATION_ERROR, stdout
        except Exception as error:
            LOGGER.error(f"Failed to connect to host %s: %s", ssh_login_info.host_ip, error)
            return state.SSH_CONNECTION_ERROR, stdout
        finally:
            if client:
                client.close()
        return state.SUCCEED, stdout

    def _create_ssh_public_key(self, ip: str, port: int, username: str, password: str) -> tuple:
        """
        generate RSA key pair,save public key to the target host machine

        Args:
            ip(str):   host ip address
            username(str):   remote login user
            port(int):   remote login port
            password(str)

        Returns:
            tuple:
                status code(int), private key string
        """
        private_key, public_key = generate_key()
        command = (
            f"mkdir -p -m 700 ~/.ssh "
            f"&& echo {public_key!r} >> ~/.ssh/authorized_keys"
            f"&& chmod 600 ~/.ssh/authorized_keys"
            f"&& source /etc/os-release"
            f"&& echo -n $(arch),$NAME"
        )
        client, stdout = None, ","
        try:
            client = SSH(ip=ip, username=username, port=port, password=password)
            status, stdout, stderr = client.execute_command(command)
        except socket.error as error:
            LOGGER.error(error)
            return state.SSH_CONNECTION_ERROR, None, stdout
        except paramiko.ssh_exception.SSHException as error:
            LOGGER.error(error)
            return state.SSH_AUTHENTICATION_ERROR, None, stdout
        finally:
            if client:
                client.close()

        if status:
            LOGGER.error(stderr)
            LOGGER.error(f"Save public key on host failed, host ip is {ip}!")
            return state.EXECUTE_COMMAND_ERROR, None, stdout

        return state.SUCCEED, private_key, stdout


class HostManageAPI(BaseResponse, SSH_Verify):

    @BaseResponse.handle(schema=AddHostSchema, proxy=HostProxy)
    def post(self, callback: HostProxy, **params):
        """
        Add host info

        Args:
            args (dict): e.g
            {
                "host_name":"host name",
                "ssh_user":"root",
                "password":"password",
                "host_group_id":"uuid",
                "host_ip":"127.0.0.1",
                "ssh_port":"22",
                "management":false,
                "ssh_pkey": "RSA key"
            }
        """
        if cache.user_role != UserRoleType.ADMINISTRATOR:
            return self.response(code=state.PERMESSION_ERROR)

        private_key = params.pop("ssh_pkey")
        if private_key:
            status, stdout = self._verify_ssh_identity_and_get_os_info(
                ClientConnect(params["host_ip"], params["ssh_port"], params["ssh_user"], private_key)
            )
        else:
            status, private_key, stdout = self._create_ssh_public_key(
                params["host_ip"], params["ssh_port"], params["ssh_user"], params.pop("password")
            )
        host_status = HostStatus.ONLINE if status == state.SUCCEED else HostStatus.UNESTABLISHED

        os_arch, os_name = stdout.split(",")
        params["ext_props"] = json.dumps({"os": {"os_arch": os_arch, "os_name": os_name}})

        add_host_status = callback.add_host(host_info=params, status=host_status, private_key=private_key)

        return self.response(code=add_host_status)

    @BaseResponse.handle(schema=GetHostsPage_RequestSchema, proxy=HostProxy)
    def get(self, callback: HostProxy, **params):
        """
        Get hosts by page

        Args:
            host_group_list (list): host group name list
            cluster_list (list): cluster id list
            management (bool): whether it's a manage node
            sort (str): sort according to specified field
            direction (str): sort direction
            page (int): current page
            per_page (int): count per page

        Returns:
            dict: response body
        """
        status_code, result = callback.get_hosts(params)
        return self.response(code=status_code, data=result)

    @BaseResponse.handle(schema=BatchHostsSchema, proxy=HostProxy)
    def delete(self, callback: HostProxy, *params):
        """
        Delete hosts in batches based on host ids

        Returns:
            dict: response body
        """
        if cache.user_role != UserRoleType.ADMINISTRATOR:
            return self.response(code=state.PERMESSION_ERROR)

        status_code = callback.delete_host(host_ids=params["host_ids"])
        return self.response(code=status_code)


class BatchAddHostAPI(BaseResponse, SSH_Verify):
    """
    Interface for batch add hosts
    """

    def _create_rsa_key(self, hosts: list) -> list:
        """
        save key to client

        Args:
            hosts (list): host info

        Returns:
            host object list
        """
        # 100 connections are created at a time.
        gevent_pool = Pool(100)
        jobs = [gevent_pool.spawn(self._update_rsa_key_to_host, host) for host in hosts]
        gevent.joinall(jobs)
        return [job.value for job in jobs]

    def _update_rsa_key_to_host(self, host: dict) -> Host:
        """
        save ssh public key to client and update its private key in host

        Args:
            host(Host): host object

        Returns:
            host object
        """
        password = host.pop("password", None)
        pkey = host.pop("ssh_pkey", None)
        if pkey:
            status, stdout = self._verify_ssh_identity_and_get_os_info(
                ClientConnect(host["host_ip"], host["ssh_port"], host["ssh_user"], pkey)
            )
        else:
            status, pkey, stdout = self._create_ssh_public_key(
                host["host_ip"], host["ssh_port"], host["ssh_user"], password
            )
        _insert_host = Host(**host, status=HostStatus.OFFLINE, pkey=pkey, host_id=str(uuid.uuid4()))
        if status == state.SUCCEED:
            _insert_host.status = HostStatus.ONLINE

        os_arch, os_name = stdout.split(",")
        _insert_host.ext_props = json.dumps({"os": {"os_arch": os_arch, "os_name": os_name}})
        return _insert_host

    def _verify_request(self, request_param) -> tuple:
        """
        Verify args

        Args:
            schema(object): the class of the validator

        Returns:
            tuple:
                status code, dict
        """
        verify_params, errors = validate(AddHostBatchSchema, request_param)
        if not errors:
            return state.SUCCEED

        if not verify_params["host_list"]:
            return state.PARAM_ERROR
        validate_errors = errors["host_list"]
        for index, host in enumerate(verify_params["host_list"]):
            if index not in validate_errors.keys():
                continue
            host["result"] = "failed"
            host["reason"] = validate_errors[index].__str__()
            self.validate_failed.append(host)

        return state.PARAM_ERROR

    @BaseResponse.handle(proxy=HostProxy)
    def post(self, callback: HostProxy, **params):
        """
        Batch add hosts

        Returns:
            response body
        """
        if cache.user_role != UserRoleType.ADMINISTRATOR:
            return self.response(code=state.PERMESSION_ERROR)

        self.add_result = []

        self.validate_failed = []
        # Validate request
        verfify_status = self._verify_request(request.get_json())
        if verfify_status != state.SUCCEED:
            return self.response(code=verfify_status, data=self.validate_failed)

        # Query hosts with groups, validate hostname or host address
        batch_hosts = request.get_json()["host_list"]
        status, hosts = callback._validate_host_info(batch_hosts)
        if status != state.SUCCEED:
            return self.response(code=status, data=hosts)

        # save public_key on host and add host to database
        status = callback.add_host_batch(self._create_rsa_key(hosts))

        return self.response(code=status)


class HostInfoManageAPI(BaseResponse, SSH_Verify):

    @staticmethod
    def _is_valid_detail_info(host_info: str):
        try:
            info = json.loads(host_info)
        except ValueError:
            LOGGER.warning("Failed to loads host detail info!")
            info = {}

        if len(info.keys()) < 2:
            return False
        return True

    def _update_host_external_info(self, host_id: str, update_info: dict) -> None:
        """Update host external info

        Args:
            host_id(str): host id
            update_info(dict): host external info which needs to update

        """
        self.proxy.update_host_association_information(host_id, update_info)

    def _query_detail_info_from_client(self, host: ClientConnect):
        """Query host details

        Args:
            host(ClientConnect): host info, which contains its host_ip, ssh_port, ssh_user, pkey

        Returns:
            tuple: status code and query result
        """
        try:
            client = None
            client = SSH(
                ip=host.host_ip,
                username=host.ssh_user,
                port=host.ssh_port,
                pkey=paramiko.RSAKey.from_private_key(StringIO(host.pkey)),
            )

            status, stdout, _ = client.execute_command(CERES_HOST_INFO % json.dumps([]))

        except Exception as error:
            LOGGER.debug(error)
            LOGGER.warning(f"Failed to query host_info with host {host.host_ip}:{host.ssh_port}")
            return state.SSH_CONNECTION_ERROR, {}
        finally:
            if client:
                client.close()

        if status:
            LOGGER.debug("Failed to query host detail info!")
            return state.EXECUTE_COMMAND_ERROR, {}
        return state.SUCCEED, stdout

    def _handle(self, host_id: str, basic: bool, refresh: bool):
        """
        Get host info handle
        """
        result = {}
        host_status, host_info = self.proxy.get_host_info(host_id)
        if host_status != state.SUCCEED:
            return host_status, result

        result = HostsInfo_ResponseSchema().dump(host_info)
        result.pop("pkey", None)
        if basic:
            return state.SUCCEED, result

        if host_info.ext_props:
            result.update(json.loads(host_info.ext_props))

        if refresh or not self._is_valid_detail_info(host_info.ext_props):
            host_status, host_info = self._query_detail_info_from_client(host_info)
            if host_status == state.SUCCEED:
                self._update_host_external_info(host_id, {"ext_props": host_info})
                result.update(json.loads(host_info))

        return state.SUCCEED, result

    @BaseResponse.handle(proxy=HostProxy, schema=HostInfoSchema)
    @BaseResponse.permession()
    def get(self, callback: HostProxy, host_id: str, basic: bool, refresh: bool, **kwargs):
        """
        Get host info

        Args:
            host_id (str): The id of the host for which information is being retrieved.
            base (bool): A flag indicating whether to return only the basic information of the host.
                      If True, only basic info is returned. If False, detailed info is returned
            refresh (bool): A flag indicating whether to refresh the host information from the client.
                            If True, it will query the host detail info from the client directly.
                            If False, it will return the host detail info from MySQL database.

        Returns:
            dict: response body
        """
        self.proxy = callback
        status, host_info = self._handle(host_id, basic, refresh)

        return self.response(code=status, data=host_info)

    @BaseResponse.handle(proxy=HostProxy)
    @BaseResponse.permession()
    def delete(self, callback: HostProxy, host_id, **kwargs):
        """
        Delete host by host id

        Args:
            host_id: host id

        Returns:
            dict: response body
        """
        if cache.user_role != UserRoleType.ADMINISTRATOR:
            return self.response(code=state.PERMESSION_ERROR)

        status_code = callback.delete_host(host_ids=[host_id])
        return self.response(code=status_code)

    @BaseResponse.handle(schema=UpdateHostSchema, proxy=HostProxy)
    @BaseResponse.permession()
    def put(self, callback: HostProxy, host_id, **params):
        """
        Update host info

        Args:
            callback(MysqlProxy): HostProxy
            **params(dict): host info which needs to update, e.g
                {
                    host_id: host_id,
                    host_name: host_name,
                    host_group_id: uuid,
                    ssh_user: root,
                    ssh_port: 22,
                    password: pwd,
                    management: True,
                    reboot: True,
                }
        """
        if cache.user_role != UserRoleType.ADMINISTRATOR:
            return self.response(code=state.PERMESSION_ERROR)

        host_status, host_info = callback.get_host_info(host_id)
        if host_status != state.SUCCEED:
            return self.response(code=host_status)

        host_ip = params["host_ip"] or host_info.host_ip
        ssh_port = params["ssh_port"] or host_info.ssh_port
        ssh_user = params["ssh_user"] or host_info.ssh_user
        status = None

        if params["password"]:
            status, private_key, stdout = self._create_ssh_public_key(
                host_ip, ssh_port, ssh_user, params.pop("password")
            )
            params["pkey"] = private_key

        if params["ssh_pkey"]:
            params["pkey"] = params.pop("ssh_pkey")
            status, stdout = self._verify_ssh_identity_and_get_os_info(
                ClientConnect(host_ip, ssh_port, ssh_user, params["pkey"])
            )

        if status:
            params["status"] = HostStatus.ONLINE if status == state.SUCCEED else HostStatus.UNESTABLISHED

        os_arch, os_name = stdout.split(",")
        params["ext_props"] = json.dumps({"os": {"os_arch": os_arch, "os_name": os_name}})
        update_status = callback.update_host_info(host_id, params)

        return self.response(code=update_status)


class HostTemplateAPI(BaseResponse):
    """
    Interface for download host template file.
    Restful API: Get
    """

    @BaseResponse.handle(schema=TemplateLangSchema)
    def get(self, **params):
        """
        Download host template file

        Args:
            lang (str): The language code for the desired template file content.
                If not provided or if the specified language is not supported, defaults to English ("en").

        Returns:
            BytesIO
        """
        file_content = HostTemplate.get_file_content(params.get("lang"))

        file = BytesIO()
        file.write(file_content.encode('utf-8'))
        file.seek(0)
        response = send_file(file, mimetype="application/octet-stream")
        response.headers['Content-Disposition'] = 'attachment; filename=template.csv'
        return response


class HostCountAPI(BaseResponse):
    """
    Interface for get host count
    """

    @BaseResponse.handle(schema=HostFilterSchema, proxy=HostProxy)
    def get(self, callback: HostProxy, **param):
        """
        Get host count

        Args:

        Returns:
            dict: response body
        """
        status_code, result = callback.get_host_count(filter_param=param)
        return self.response(code=status_code, data=result)


class HostStatusAPI(BaseResponse, SSH_Verify):
    """
    Interface for batch get host status.
    """

    def _get_host_status(self, host: Host):
        status = self._verify_ssh_identity(ClientConnect(host.host_ip, host.ssh_port, host.ssh_user, host.pkey))
        if status == state.SSH_AUTHENTICATION_ERROR:
            status = HostStatus.UNESTABLISHED
        elif status == state.SUCCEED:
            status = HostStatus.ONLINE
        else:
            status = HostStatus.OFFLINE

        return dict(host_id=host.host_id, status=status)

    @BaseResponse.handle(schema=BatchHostsSchema, proxy=HostProxy)
    def get(self, callback: HostProxy, **param):
        """
        Batch get host status
        """
        filter_param = HostFilterSchema().load(param)
        status_code, hosts = callback.get_filter_hosts(filter_param=filter_param)
        if status_code != state.SUCCEED:
            return self.response(code=status_code)

        gevent_pool = Pool(100)
        jobs = [gevent_pool.spawn(self._get_host_status, Host(**host)) for host in hosts]
        gevent.joinall(jobs)
        response_data = [job.value for job in jobs]
        return self.response(code=state.SUCCEED, data=response_data)


class SingleHostStatusAPI(BaseResponse, SSH_Verify):
    """
    Interface for get single host status.
    """

    @BaseResponse.handle(proxy=HostProxy)
    @BaseResponse.permession()
    def get(self, host_id, callback: HostProxy, **kwargs):
        """
        get host status

        Args:
            host_id (str): host id

        Returns:
            response body
        """
        status_code, host = callback.get_host_info(host_id=host_id)
        if status_code != state.SUCCEED:
            return self.response(code=status_code)
        status = self._verify_ssh_identity(ClientConnect(host.host_ip, host.ssh_port, host.ssh_user, host.pkey))
        if status == state.SSH_AUTHENTICATION_ERROR:
            status = HostStatus.UNESTABLISHED
        elif status == state.SUCCEED:
            status = HostStatus.ONLINE
        else:
            status = HostStatus.OFFLINE
        return self.response(code=status_code, data=dict(host_id=host_id, status=status))

    @BaseResponse.handle(schema=UpdateHostStatusSchema, proxy=HostProxy)
    @BaseResponse.permession()
    def put(self, host_id, callback: HostProxy, **param):
        """
        modify host status

        Args:
            host_id (str): host id

        Returns:
            response body
        """

        host_info = UpdateHostSchema().load(data=param)
        status_code = callback.update_host_info(host_id=host_id, host_info=host_info)

        return self.response(code=status_code)


class HostFilterAPI(BaseResponse):
    """
    Interface for host filter
    """

    @BaseResponse.handle(schema=HostFilterSchema, proxy=HostProxy)
    def get(self, callback: HostProxy, **param):
        """
        Get the host that meets the filter

        Args:
            param: e.g
                {
                    "status": "online",
                    "host_ids": [],
                    "host_group_ids": [],
                    "reboot": True/False,
                    "cluster_list": [],
                    "fields": []
                }
        """
        status_code, host_list = callback.get_filter_hosts(param)
        return self.response(code=status_code, data=host_list)


class HostIpFilterAPI(BaseResponse):
    """
    Interface for host filter by ips
    """

    @BaseResponse.handle(schema=HostIpsFilterSchema, proxy=HostProxy)
    def get(self, callback: HostProxy, **param):
        """
        Get the host that meets the filter

        Args:
            param: e.g
                {
                    "host_ips": []
                }
        """
        status_code, host_list = callback.get_ips_hosts(param)
        return self.response(code=status_code, data=host_list)
