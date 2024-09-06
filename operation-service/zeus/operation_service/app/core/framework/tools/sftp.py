# -*- encoding: utf-8 -*-
"""
功 能：ftp操作工具类
版权信息：华为技术有限公司，版本所有(C) 2010-2019
"""
import os.path
import stat
import traceback
import warnings

import paramiko

from vulcanus.log.log import LOGGER


warnings.filterwarnings("ignore")


class FileMgr(object):
    """
    ftp操作工具类
    """

    def __init__(self, ssh_con):
        self.m_sftp = ssh_con.m_sftp

    def close(self):
        """
        关闭连接
        :return:
        """
        self.m_sftp.close()

    def cd(self, directory):
        """
        切换目录接口，用于切换SFTP服务器上的工作目录
        """
        try:
            self.m_sftp.chdir(directory)
            return True
        except IOError:
            LOGGER.exception("Catch an exception: %s", traceback.format_exc())
            return False

    def pwd(self):
        """
        获取SFTP服务器上的当前工作目录
        """
        try:
            return self.m_sftp.getcwd()
        except paramiko.SSHException:
            return None

    def mkdir(self, directory):
        """
        用于在SFTP服务器上新建一个目录
        """
        try:
            self.m_sftp.mkdir(directory)
        except paramiko.SSHException:
            LOGGER.exception("Catch an exception: %s", traceback.format_exc())
            return False
        except Exception as e:
            LOGGER.exception("Catch an exception: %s", traceback.format_exc())
            return False
        return True

    def rename(self, fromname, toname):
        """
        修改SFTP服务器上文件和目录的名称
        fromname    : 文件和目录名称
        toname      : 需要改成的名称
        """
        try:
            self.m_sftp.rename(fromname, toname)
        except (OSError, IOError, paramiko.SSHException):
            LOGGER.exception("Catch an exception: %s", traceback.format_exc())
            return False
        except Exception as e:
            LOGGER.exception("Catch an exception: %s", traceback.format_exc())
            return False
        return True

    def GetBinFile(self, remotefile, localfile=None, callback=None):
        """
        用于二进制方式下载文件，会覆盖掉本地文件
        remotefile  : 服务器上的文件路径
        localfile   : 下载到本地的文件路径。可选参数，如果没有指定，默认下载到当前工作目录
        """
        try:
            if localfile is None:
                localfile = os.path.basename(remotefile)
            self.m_sftp.get(remotefile, localfile, callback)
            return True
        except Exception as e:
            LOGGER.error(
                "remotefile: [%s], localfile: [%s]", remotefile, localfile)
            LOGGER.exception("Catch an exception: %s", traceback.format_exc())
            return False

    def PutBinFile(self, localfile, remotefile=None, callback=None):
        """
        用于二进制方式上传文件，会覆盖服务器上的文件
        localfile   : 需要上传的本地文件名称
        remotefile  : 上传到远程服务器的文件路径。可选参数，如果没有指定，默认上传到FTP工作目录
        """
        try:
            if remotefile is None:
                remotefile = os.path.basename(localfile)
            self.m_sftp.put(localfile, remotefile, callback)
            return True
        except Exception as e:
            LOGGER.error(
                "remotefile: [%s], localfile: [%s]", remotefile, localfile)
            LOGGER.exception("Catch an exception: %s", traceback.format_exc())
            return False

    def ls(self, directory="."):
        """
        用于列出SFTP服务上的文件和目录名称，如果没有指定参数，则列出当FTP工作目录上的文件和目录名称
        """
        alllist = []
        try:
            alllist = self.m_sftp.listdir(directory)
        except Exception as e:
            LOGGER.exception("Catch an exception: %s", traceback.format_exc())
        return alllist

    def exists(self, filename):
        """
        用于判断文件或目录是否存在，支持绝对路径和相对路径
        """
        filelist = self.ls(os.path.dirname(filename))
        if os.path.basename(filename) in filelist:
            return True
        else:
            return False

    def delete(self, filename):
        """
        用于删除SFTP服务其上的文件，不能用来删除目录，支持绝对路径和相对路径
        """
        try:
            self.m_sftp.remove(filename)
            return True
        except Exception as e:
            LOGGER.exception("Catch an exception: %s", traceback.format_exc())
            return False

    def size(self, filename):
        """
        获取文件大小
        :param filename: 文件名
        :return: 文件大小
        """
        try:
            att = self.m_sftp.stat(filename)
            return int(att.st_size)
        except Exception as e:
            LOGGER.exception("Catch an exception: %s", traceback.format_exc())
            return None

    def rmdir(self, directory):
        """
        删除远程服务器目录
        """
        try:
            self.m_sftp.rmdir(directory)
            return True
        except Exception as e:
            LOGGER.exception("Catch an exception: %s", traceback.format_exc())
            return False

    def stat(self, filename):
        """
        获取文件信息
        :param filename: 文件名
        :return: 文件统计信息对象
        """
        try:
            return self.m_sftp.stat(filename)
        except Exception as e:
            LOGGER.exception("Catch an exception: %s", traceback.format_exc())
            return None

    def is_file(self, path):
        """
        判断 remote path 是否是一个文件
        :param path:
        :return:
        """
        try:
            file_attr = self.m_sftp.lstat(path)
            return stat.S_ISREG(file_attr.st_mode)
        except Exception as e:
            LOGGER.exception("Catch an exception: %s", traceback.format_exc())
            return None

    def chown(self, path, uid, gid):
        """
        更改文件属主
        """
        try:
            return self.m_sftp.chown(path, uid, gid)
        except Exception as e:
            LOGGER.exception("Catch an exception: %s", traceback.format_exc())
            return None

    def chmod(self, path, mode):
        """
        更改文件权限
        """
        try:
            return self.m_sftp.chmod(path, mode)
        except Exception as e:
            LOGGER.exception("Catch an exception: %s", traceback.format_exc())
            return None
