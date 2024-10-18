# -*- coding: utf-8 -*-
"""
功 能：SSH模块
版权信息：华为技术有限公司，版本所有(C) 2010-2019

"""

from io import StringIO
import socket
import string
import time
import warnings
from collections import OrderedDict
from secrets import SystemRandom

import paramiko
from paramiko import AuthenticationException
from paramiko import SSHException

from paramiko.ssh_exception import NoValidConnectionsError
# from wtforms.validators import IPAddress

from zeus.operation_service.app.core.framework.common.constant import DEFAULT_SSH_PORT
from vulcanus.log.log import LOGGER

warnings.filterwarnings("ignore")


# class SshConnectionLruCache:
#     def __init__(self, capacity):
#         self.capacity = capacity
#         self.cache = OrderedDict()

#     def cached(self, key):
#         return key in self.cache

#     def get(self, key):
#         if not self.cached(key):
#             return -1
#         entity = self.cache.pop(key)
#         self.cache[key] = entity
#         return entity

#     def set(self, key, entity):
#         if key in self.cache:
#             self.cache.pop(key)
#         elif len(self.cache) == self.capacity:
#             _, entity = self.cache.popitem(last=False)
#             entity.close()
#         self.cache[key] = entity


# SSH_CONNECTION_CACHE = SshConnectionLruCache(capacity=15)


class RemoteControl(object):
    """
    该功能模块同时SSH/SFTP能力，SSH和SFTP通道共用连接，支持长连接。
    SSH和SFTP通道相互独立，SSH和SFTP上下文的操作互不干扰。
    """

    # def _cached_key(self):
    #     return f"@{self.__host_ip}@_@{self.__user}@"

    def _new_ssh_connection(self):
        self.m_client = paramiko.client.SSHClient()
        policy = paramiko.client.AutoAddPolicy()
        self.m_client.set_missing_host_key_policy(policy)
        if self.__passwordless:
            self.m_client.load_system_host_keys()
            self.m_client.connect(hostname=self.__host_ip, port=self.__port, username=self.__user, timeout=self.timeout,
                                  banner_timeout=300, allow_agent=False, look_for_keys=True)
        else:
            private_key = paramiko.RSAKey.from_private_key(StringIO(self.__password))
            self.m_client.connect(self.__host_ip, self.__port, self.__user, pkey=private_key, timeout=self.timeout,
                                  banner_timeout=300, allow_agent=False)
        self.m_sftp = self.m_client.open_sftp()

    # def _connect(self):
    #     cache_key = self._cached_key()
    #     if SSH_CONNECTION_CACHE.cached(cache_key):
    #         self.m_client = SSH_CONNECTION_CACHE.get(cache_key)
    #         self.m_sftp = self.m_client.open_sftp()
    #         self._cached = True
    #         return

    #     self._new_ssh_connection()
    #     SSH_CONNECTION_CACHE.set(cache_key, self.m_client)

    def __init__(self, host_ip, user, password, passwordless=False, port=DEFAULT_SSH_PORT, **args):
        """
        @OPEN_API_FUNCTION
        @DESCRIPTION SSH/SFTP初始化操作
        IP          :   服务器的IP,ipv4或者ipv6地址：比如：host_ip = "192.0.0.1" host_ip = "fe20::1"
        user        :   用户名
        password    :   密码
        passwordless:   免密登录，默认False
        port        :   端口，可选，默认为22
        shell       ：  用户的shell类型，可选，默认为bash
        supassword  ：  su切换root的密码，可选，如果指定，在登陆时会切换为root，仅适用于SSH通道
        timeout     ：  超时时间，可选，默认为4秒
        """

        self.timeout = 4
        if args.get("timeout") is not None:
            self.timeout = args.get("timeout")
        self.prompt = "%s: >" % self.get_prompt()
        self.waitstr = self.prompt
        if args.get("waitstr") is not None:
            self.waitstr = args.get("waitstr")
        self.interval = 0.2
        # 内部适配：Gkit目前支持双栈ip，其中使用ssh连接可能传入双栈ip（以英文逗号分隔），在这里进行host ip 的统一适配，加强检查，支持传入双IP，仅取第一个有效ip进行连接
        host_ip = self.check_host_ip(host_ip)
        LOGGER.info("[ssh]: Start to connect %s:%s", host_ip, port)
        if not password and not passwordless:
            LOGGER.exception(f"[ssh]: host : {host_ip}, do not have paaspwd")
            raise AuthenticationException()
        self.__host_ip = host_ip
        self.__port = port
        self.__user = user
        self.__password = password
        self.__passwordless = passwordless
        self.__supassword = args.get("supassword")
        self.__admin_pwd = args.get("admin_pwd")
        self.__shell = "bash" if not args.get("shell") else args.get("shell")
        self.__sftpflag = args.get("sftpflag")
        self.m_sftp = None
        self.__retry_time = args.get("retry_time", 5)
        self.__backoff_time = args.get("backoff_time", 1)
        self.__last_exception = None
        self._cached = False
        try:
            self._new_ssh_connection()
        except AuthenticationException as ex:
            LOGGER.error("[ssh]: Catch AuthenticationException [%s] %s", ex, host_ip)
            raise ex
        except (socket.timeout, SSHException, NoValidConnectionsError) as ex:
            LOGGER.info("[ssh]: Catch exception [%s],connect again! %s", ex, host_ip)
            self.__last_exception = ex
            begin_time = time.time()
            self.__backoff_reconnect(host_ip, port, user, password, begin_time, self.__retry_time)
        if not self._cached:
            self.check_ssh(args)

    def __backoff_reconnect(self, host_ip, port, user, password, begin_time, retry_time):
        """
        退避重试
        :param host_ip:
        :param port:
        :param user:
        :param password:
        :return:
        """
        if retry_time <= 0:
            raise self.__last_exception
        time.sleep(self.__backoff_time)
        try:
            if self.__passwordless:
                self.m_client.load_system_host_keys()
                self.m_client.connect(hostname=self.__host_ip, port=self.__port, username=self.__user, timeout=self.timeout,
                                    banner_timeout=300, allow_agent=False, look_for_keys=True)
            else:
                private_key = paramiko.RSAKey.from_private_key(StringIO(self.__password))
                self.m_client.connect(self.__host_ip, self.__port, self.__user, pkey=private_key, timeout=self.timeout,
                                    banner_timeout=300, allow_agent=False)
        except (socket.timeout, SSHException) as ex:
            self.__last_exception = ex
            LOGGER.info("[ssh]: Catch exception [%s],connect again!", ex)
            self.__backoff_reconnect(host_ip, port, user, password, begin_time, retry_time - (time.time() - begin_time))

    def check_host_ip(self, host_ip):
        """
        适配Gkit 管理面双栈部署模下，host_ip 可能传入双ip，导致ssh连接不适配，此接口对host ip进行加强检查
        取第一个有效ip进行ssh连接。
        若不能完成有效校验，能返回原host ip值，不做任何校验。
        :param host_ip:
        :return:
        """
        if not host_ip or not isinstance(host_ip, str):
            return host_ip
        split = host_ip.split(",")
        if not split:
            return host_ip
        # if IPAddress.check_ipv4(split[0]) or IPAddress.check_ipv6(split[0]):
        #     return split[0]
        else:
            return host_ip

    def check_ssh(self, args):
        # ssh链接后检查
        self.m_channel = self.m_client.invoke_shell(term="vt100", width=256)
        self.m_channel.setblocking(0)
        # 保持心跳没有任何交互下30s发送一次keepalive
        self.m_client.get_transport().set_keepalive(30)

        if self.waitstr != 'iBMC:/->':
            self.set_prompt("bash" if not args.get("shell") else args.get("shell"))

    @staticmethod
    def get_prompt():
        """
        生成一个随机的命令提示符
        :return:
        """
        characters = string.ascii_lowercase + string.digits + "_"
        sys_rand = SystemRandom()
        prompt = "".join([sys_rand.choice(characters) for _ in range(8)])
        return prompt

    def set_prompt(self, shell):
        """
        :return:
        """
        promptset = b""
        if shell.find("bash") != -1:
            if shell == "bash":
                # 切换到bash
                self.m_channel.send(b"PS1=\"" + self.waitstr.encode("utf-8") + b"\"\n")
                ret, _ = self.read_until(">", self.timeout * 4, wait_list=["$", "#"])
                LOGGER.info(f"[ssh]: {repr(ret)}")
                # bash命令返回较慢 等待第二次返回，用于清空 channel
                if ret.count("$".encode("utf-8")) != 2 and ret.count("#".encode("utf-8")) != 2 and ret.count(
                        ">".encode("utf-8")) != 2:
                    ret, _ = self.read_until(">", 1, wait_list=["$", "#"], ignore_log=True)
                    LOGGER.info(f"[ssh]: {repr(ret)}")
            # 设置命令提示符
            self.m_channel.send(b"PS1=\"" + self.waitstr.encode("utf-8") + b"\"\n")
            promptset = b"PS1=\""
        else:
            LOGGER.info("[ssh]: catch unknown shell %s,skip set prompt", shell)
            return

        first, _ = self.read_until(self.prompt, self.timeout)
        LOGGER.info(f"[ssh]: {repr(first[:80])}")
        if first.count(self.prompt.encode("utf-8")) < 2:
            second, _ = self.read_until(self.prompt, self.timeout)
            LOGGER.info(f"[ssh]: {repr(second)}")
            if second.count(promptset) > 0:
                third, _ = self.read_until(self.prompt, self.timeout)
                LOGGER.info(f"[ssh]: {repr(third)}")
        elif first.count(promptset) > 1:
            second, _ = self.read_until(self.prompt, self.timeout)
            LOGGER.info(f"[ssh]: {repr(second)}")

    # 仅适用于SSH通道
    def su(self, user="root", password=None, shell="/bin/bash"):
        """
        切换当前命令执行用户，等同于linux中执行 su 命令
        :param user:
        :param password:
        :param shell:
        :return:
        """
        cmd = "su - %s --shell=%s\n" % (user, shell)
        self.m_channel.send(cmd.encode("utf-8"))
        if password:
            ret, _ = self.read_until("assword:", self.timeout, wait_list=[self.prompt])
            LOGGER.info(f"[ssh]: {repr(ret)}")
            if ret.find(b"assword:") != -1:
                cmd = "%s\n" % password
                self.m_channel.send(cmd.encode("utf-8"))

        ret, _ = self.read_until(">", self.timeout * 2, wait_list=["$", "#", self.prompt])
        LOGGER.info(f"[ssh]: {repr(ret)}")

        if ret.find(b"not exist") != -1:
            LOGGER.error("[ssh]: user %s does not exist!", user)
            return False

        if ret.find(b"Authentication failure") != -1:
            LOGGER.error("[ssh]: su %s failed!", user)
            return False

        if ret.find(b"denied") != -1:
            LOGGER.error("[ssh]: su %s failed!", user)
            return False

        self.set_prompt(shell)
        self.cmd("whoami")
        return True

    def auto_save_key(self, sshserver, port=DEFAULT_SSH_PORT, retry_flag=False):
        """
        实现自动保存远程机器的证书
        :param retry_flag:
        :param sshserver: 远端服务器地址
        :param port:
        :return:
        """
        tmp_timeout = self.timeout
        self.timeout = 30
        for _ in range(3):
            cmd = "ssh %s -p %s\n" % (str(sshserver), str(port))
            self.m_channel.send(cmd.encode("utf-8"))
            result, _ = self.read_until("yes/no", self.timeout, wait_list=["assword:", "$", ">", "#"])
            if result.find(b"reset by peer") != -1 or result.find(b"ssh_exchange_identification") != -1:
                time.sleep(SystemRandom().random() * 10)
                continue
            break
        LOGGER.info(f"[ssh]: {repr(result)}")
        if result.find(b"yes/no") != -1:
            cmd = "yes\n"
            self.m_channel.send(cmd.encode("utf-8"))
            ret, _ = self.read_until("assword:", self.timeout, wait_list=["$", ">", "#"])
            time.sleep(0.5)
            LOGGER.info(f"[ssh]: {repr(ret)}")
            if ret.find(b"assword:") == -1:
                self.cmd("exit")
                return False
            self.cmd("\x03")
            self.timeout = tmp_timeout
            return True
        elif result.find(b"assword:") != -1:
            self.cmd("\x03")
            self.timeout = tmp_timeout
            return True
        elif result.find(b"ost key verification failed") != -1:
            # 解决已经在known_hosts中添加了公钥，但后来机器重构的情况，自动删除之前的公钥后重试
            if not retry_flag:
                self.cmd("sed -i \"/%s /d\"  ~/.ssh/known_hosts" % sshserver)
                return self.auto_save_key(sshserver, port, True)
            self.timeout = tmp_timeout
            return False
        elif result.find(b"has expired") != -1:
            self.timeout = tmp_timeout
            return True
        else:
            self.cmd("exit")
            self.set_prompt(self.__shell)
            self.timeout = tmp_timeout
            return False

    @staticmethod
    def check_return(result, waitlist):
        """确认是否出现预期字符"""
        for wait in waitlist:
            if result.find(wait.encode("utf-8")) != -1:
                return True
        return False

    def read_until(self, wait_str, timeout, ignore_log=False, wait_list=None):
        """ 通过分析输出流中是否出现预期的字符串，确认是否可以返回已经读到的字符串 """
        # 通过分析输出流中是否出现预期的字符串，确认是否可以返回已经读到的字符串
        if wait_list is None:
            wait_list = []
        result = b""

        self.m_channel.settimeout(timeout)
        self.timeout_flag = False
        begin = time.time()
        exec_timeout = False
        recv_number = 1024

        while True:
            time.sleep(self.interval)
            try:
                while self.m_channel.recv_ready():
                    result = result + self.m_channel.recv(recv_number)
            except socket.timeout:
                if not ignore_log:
                    LOGGER.warning("[ssh]: recv timeout(%s)", timeout)
                continue
            except Exception as ex:
                raise ex

            # 检查是否超时
            now = time.time()
            diff = now - begin
            if diff >= timeout:
                self.timeout_flag = True
                if not ignore_log:
                    LOGGER.warning('[ssh]: Wait "%s" time out!', wait_str)
                exec_timeout = True
                break

            waitlist = []
            waitlist.append(wait_str)
            waitlist.extend(wait_list)
            if self.check_return(result, waitlist):
                break

        return result, exec_timeout

    def set_timeout(self, timeout):
        """
        设置命令执行超时时间
        :param timeout:
        :return:
        """
        self.timeout = timeout

    def relogin(self):
        """重新登录"""
        self.m_client = paramiko.client.SSHClient()
        policy = paramiko.client.AutoAddPolicy()
        self.m_client.set_missing_host_key_policy(policy)
        relogin_timeout = self.timeout * 4 if self.timeout * 4 <= 60 else 60
        for i in range(1, 4):
            try:
                self.m_client.connect(self.__host_ip,
                                      self.__port,
                                      self.__user,
                                      self.__password,
                                      timeout=relogin_timeout,
                                      banner_timeout=300,
                                      allow_agent=False,
                                      look_for_keys=True)

                self.m_channel = self.m_client.invoke_shell(term="vt100", width=256)
                self.m_channel.setblocking(0)
                if self.__user == "root" or not self.__supassword:
                    self.set_prompt("bash" if not self.__shell else self.__shell)
                    break

                # 切换到root
                self.m_channel.send(b"su -\n")
                ret, _ = self.read_until("assword:", relogin_timeout)
                LOGGER.info(f"[ssh]: {repr(ret)}")
                if ret.find(b"assword:") != -1:
                    self.m_channel.send(b"%s\n" % self.__supassword.encode("utf-8"))
                    ret, _ = self.read_until("#", relogin_timeout, wait_list=["$", ">"])
                    LOGGER.info(f"[ssh]: {repr(ret)}")

                self.set_prompt("bash" if not self.__shell else self.__shell)
                break
            except SSHException as err:
                LOGGER.info("[ssh]: Catch SSHException [%s],connect again!", err)
                LOGGER.info("[ssh]: try to connect again ,%s times", i)
                time.sleep(5)
                continue
            except OSError as err:
                LOGGER.info("[ssh]: Catch OSError [%s],connect again!", err)
                LOGGER.info("[ssh]: try to connect again ,%s times", i)
                time.sleep(5)
                continue

    def cmd(self, command, waitstr=None, retflag=False, ignorelog=False, reset_prompt=False):
        """
        SSH通道中执行命令
        对于返回值有着色配置的系统，ls或grep命令结果可能有乱码
        可以在ls/grep命令中加参数--color=never防止乱码出现
        reset_prompt=True时，因为需要去设置命令提示符，所以不能通过get_last_result去查该调命令的结果
        """
        info, _ = self.cmd_with_timeout_flag(command, waitstr, retflag, ignorelog, reset_prompt=reset_prompt)
        return info

    def cmd_with_timeout_flag(self, command, waitstr=None, retflag=False, ignorelog=False, reset_prompt=False):
        """
        SSH通道中执行命令, 同时返回命令是否执行超时标识
        对于返回值有着色配置的系统，ls或grep命令结果可能有乱码
        可以在ls/grep命令中加参数--color=never防止乱码出现
        reset_prompt=True时，因为需要去设置命令提示符，所以不能通过get_last_result去查该调命令的结果
        """
        # 禁止使用su命令在这里切换用户
        try:
            self.m_channel.send(command + "\n")
        except Exception as e:
            # 如果socket关闭则重连
            self.relogin()
            self.m_channel.send(command + "\n")
        beginline = 1
        if retflag:
            beginline = 0
        if waitstr:
            if reset_prompt:
                result, exec_timeout = self.read_until(">", self.timeout, wait_list=["$", "#", self.prompt])
            else:
                result, exec_timeout = self.read_until(waitstr, self.timeout, wait_list=[self.waitstr])
            if not ignorelog:
                LOGGER.info(f"[ssh]: {result}")
            info = b"\n".join(result.split(b"\n")[beginline:])
        else:
            if reset_prompt:
                result, exec_timeout = self.read_until(">", self.timeout, wait_list=["$", "#", self.prompt])
            else:
                result, exec_timeout = self.read_until(self.waitstr, self.timeout)
            info = self.__remove_result_wrap(beginline, ignorelog, result)

        if reset_prompt:
            self.set_prompt(self.__shell)
            self.cmd("whoami")
        return info.decode("utf-8", "replace"), exec_timeout

    def cmd_with_backoff_retry(self, command, waitstr=None, retflag=False, ignorelog=False, retry_time=None,
                               backoff_time=None, reset_prompt=False):
        """
        SSH通道中执行命令,带有退避重试功能，如果退避重试失败最终会抛出异常
        对于返回值有着色配置的系统，ls或grep命令结果可能有乱码
        可以在ls/grep命令中加参数--color=never防止乱码出现
        :param command: 执行的命令字符串
        :param waitstr: 等待字符串，命令返回中有该字符串时认为命令已经执行结束
        :param retflag:
        :param ignorelog: 不打印日志
        :param retry_time:  退避重试时长，在多长时间内会进行退避
        :param backoff_time: 退避时长，每次失败后退避多长时间后再次重试
        :param reset_prompt: 是否需要重新设置命令提示符，reset_prompt=True时，因为需要去设置命令提示符，所以不能通过get_last_result去查该调命令的结果
        :return:
        """
        # 禁止使用su命令在这里切换用户
        beginline = 1
        if retflag:
            beginline = 0
        try:
            result = self.__wait_exec_cmd_result(command, waitstr, reset_prompt=reset_prompt)
        except Exception as ex:
            # 如果socket关闭则重连
            self.__last_exception = ex
            begin_time = time.time()
            retry_time = retry_time if retry_time else self.__retry_time
            backoff_time = backoff_time if backoff_time else self.__backoff_time
            result = self.__backoff_recmd(command, waitstr, begin_time, retry_time, backoff_time,
                                          reset_prompt=reset_prompt)

        info = self.__remove_result_wrap(beginline, ignorelog, result)
        if reset_prompt:
            self.set_prompt(self.__shell)
            self.cmd("whoami")

        return info.decode("utf-8", "replace")

    @staticmethod
    def __remove_result_wrap(beginline, ignorelog, result):
        if not ignorelog:
            LOGGER.info(f"[ssh]: {result[:80]}")
        info = b"\n".join(result.split(b"\n")[beginline:-1])
        if len(info) > 0 and info[-1] == ord("\r"):
            info = info[:-1]
        return info

    def __wait_exec_cmd_result(self, command, waitstr, reset_prompt=False):
        self.m_channel.send(command + "\n")
        if waitstr:
            if reset_prompt:
                result, exec_timeout = self.read_until(">", self.timeout, wait_list=["$", "#", self.prompt])
            else:
                result, exec_timeout = self.read_until(waitstr, self.timeout, wait_list=[self.waitstr])
        else:
            if reset_prompt:
                result, exec_timeout = self.read_until(">", self.timeout, wait_list=["$", "#", self.prompt])
            else:
                result, exec_timeout = self.read_until(self.waitstr, self.timeout)
        if exec_timeout:
            raise socket.timeout("Wait cmd result time out!")
        return result

    def __backoff_recmd(self, command, waitstr, begin_time, retry_time, backoff_time, reset_prompt=False):
        """
        退避重试
        :param host_ip:
        :param port:
        :param user:
        :param password:
        :return:
        """
        if retry_time <= 0:
            raise self.__last_exception
        time.sleep(backoff_time)
        try:
            LOGGER.info("[ssh]: Catch exception [%s],execute cmd again!", self.__last_exception)
            self.relogin()
            result = self.__wait_exec_cmd_result(command, waitstr, reset_prompt=reset_prompt)
        except Exception as ex:
            self.__last_exception = ex
            result = self.__backoff_recmd(command, waitstr, begin_time, retry_time - (time.time() - begin_time),
                                          backoff_time, reset_prompt=reset_prompt)
        return result

    def close(self):
        """
        关闭通道连接
        :return:
        """
        # 关闭通道连接
        if hasattr(self, "m_sftp") and self.m_sftp:
            self.m_sftp.close()

    @property
    def login_ip(self):
        """get login ip"""
        return self.__host_ip

    @property
    def login_port(self):
        """getter"""
        return self.__port

    def get_last_result(self, waitstr=None, process_method=None):
        """用于获取上个命令的执行情况"""
        result_code = self.cmd("echo $?").split()
        for spec in result_code:
            try:
                int(spec)
            except ValueError:
                pass
            else:
                result_code = spec
        if waitstr is None:
            waitstr = self.waitstr
        if len(result_code) == 0:
            result_code, _ = self.read_until(waitstr, self.timeout, wait_list=[self.waitstr])
        try:
            if result_code == "0":
                return True
            elif result_code == "1":
                return False
            elif result_code == "99":
                LOGGER.info("[ssh]: Script is running!Don't run repeatedly")
                return False
            else:
                LOGGER.info("[ssh]: Unknow return value [%s]", result_code)
                return False
        finally:
            if process_method:
                process_method(result_code)

    def cmd1(self, command, waitstr=None, retflag=False, ignorelog=False):
        """
        SSH通道中执行命令
        对于返回值有着色配置的系统，ls或grep命令结果可能有乱码
        可以在ls/grep命令中加参数--color=never防止乱码出现
        """
        info = b""
        # 禁止使用su命令在这里切换用户
        try:
            self.m_channel.send(command + "\n")
        except Exception as e:
            # 如果socket关闭则重连
            self.relogin()
            self.m_channel.send(command + "\n")
        beginline = 1
        if retflag:
            beginline = 0
        if waitstr:
            result, _ = self.read_until(waitstr, self.timeout, wait_list=[self.waitstr])
            if not ignorelog:
                LOGGER.info("[ssh]: %s%s%s", str.encode(command), b" ", result)
            info = b"\n".join(result.split(b"\n")[beginline:])
        else:
            result, _ = self.read_until(self.waitstr, self.timeout)
            info = self.__remove_result_wrap(beginline, ignorelog, result)

        return info.decode("utf-8", "replace")

    def __del__(self):
        '''对象销毁时候调用close'''
        self.close()

    def __enter__(self):
        """
        with statement entrance
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        with statement exit
        """
        self.close()
