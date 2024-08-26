import hashlib
import os.path
import re


class NotFileException(Exception):
    def __init__(self):
        pass

    def __str__(self):
        print("Need a file, but a directory offered")


def sha256sum(path):
    if not os.path.isfile(path):
        raise NotFileException()
    with open(path, "rb") as f:
        sha256res = hashlib.sha256(f.read()).hexdigest()
    return sha256res


def remove_color_and_format(string):
    """
    去除服务器回显中的颜色样式信息
    """
    return re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]').sub('', string).replace('\b', '').replace('\r', '')


def compare_remote_and_local_file(ssh_con, remote_path, local_path):
    cmd = "sha256sum {}".format(remote_path)
    echo = ssh_con.cmd(cmd)
    echo = remove_color_and_format(echo)
    remote_file_sha256sum = echo.split(" ")[0]
    local_file_sha256sum = sha256sum(local_path)
    return remote_file_sha256sum == local_file_sha256sum
