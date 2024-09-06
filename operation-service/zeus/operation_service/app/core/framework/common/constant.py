# -*- encoding: utf-8 -*-
"""
功 能：工具的常量
版权信息：华为技术有限公司，版本所有(C) 2023-2032
"""

# ssh 默认通信端口
DEFAULT_SSH_PORT = 22


class TaskType:
    COMMAND_EXECUTION = "COMMAND_EXECUTION"
    SCRIPT_EXECUTION = "SCRIPT_EXECUTION"

class FileSize:
    # 读取的默认文件大小为10k
    READ_SIZE = 10 * 1024
