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


from enum import Enum

BASE_DIR = '/opt/aops/task'
# 存储脚本，目录为SCRIPTS_DIR/<script_id>
SCRIPTS_DIR = '/opt/aops/task/scripts'
# 存储任务执行信息，目录为WORK_DIR/<task_id>
WORK_DIR = '/opt/aops/task/work_dir'
# 存储任务执行结果信息，目录为RESULTS_DIR/<task_id>
RESULTS_DIR = '/opt/aops/task/results'


class ResultCodeEnum(Enum):
    @property
    def code(self):
        return self.value[0]

    @property
    def msg(self):
        return self.value[1]

"""
前端错误码规范：
共七位：AAABBBCDDD
AAA:  模块102
BBB:  应用
C：状态：成功 or 失败 or 其他
DDD： 错误码
例子：1020011001， 为os_manager(102)主机管理应用（001），测试ip连通性成功（1）的错误码（001）
备注：通用成功（后三位为0，AAABBBC000）前端不会弹窗提示
"""

class RemoteExecutionResultCode(ResultCodeEnum):
    """
    前端远程执行命令相关API错误码枚举类
    """

    SUCCESS_COMMON = (1020021000, 'OK')

    SUCCESS_ADD_COMMAND = (1020021001, 'Command added successfully')
    SUCCESS_DELETE_COMMAND = (1020021002, 'Command deleted successfully')
    SUCCESS_MODIFY_COMMAND = (1020021003, 'Command modified successfully')
    SUCCESS_BATCH_DELETE_COMMAND = (1020021004, 'Command batch deleted successfully')
    SUCCESS_ADD_SCRIPT = (1020021005, 'Script added successfully')
    SUCCESS_DELETE_SCRIPT = (1020021006, 'Script deleted successfully')
    SUCCESS_MODIFY_SCRIPT = (1020021007, 'Script modified successfully')
    SUCCESS_BATCH_DELETE_SCRIPT = (1020021008, 'Script batch deleted successfully')

    ERR_BATCH_DELETE_COMMAND = (1020022001, 'Command batch delete failed')
    ERR_UNCONFIRMED_COMMAND = (1020022002, 'unconfirmed high risk operations')
    ERR_UNKNOWN_COMMAND_TYPE = (1020022003, 'unknown command type')
    ERR_INVALID_DATA = (1020022004, 'Invalid data in request')
    ERR_EXECUTION_FAILED_SHORTCUT = (1020022005, "shortcut execution failed")
    ERR_COMMAND_EXIST = (1020022006, 'Command with this name already exists')
    ERR_SCRIPT_EXIST = (1020022007, 'Script with this name already exists')
    ERR_BATCH_DELETE_SCRIPT = (1020022008, 'Script batch delete failed')

    ERR_UNKNOWN = (1020022999, 'Unknown error in command operation')

    PARTIAL_SUCCESS_BATCH_DELETE_COMMAND = (1020023001, 'Partial Command deleted successfully')
    PARTIAL_SUCCESS_EXECUTION_SHORTCUT = (1020023002, 'Partial shortcut executed successfully')


class TaskOperationResultCode(ResultCodeEnum):
    """
    前端任务相关API错误码枚举类
    """
    SUCCESS_COMMON = (1020031000, 'OK')

    SUCCESS_ADD_TASK = (1020031001, 'Task added successfully')
    SUCCESS_DELETE_TASK = (1020031002, 'Task deleted successfully')
    SUCCESS_START_TASK = (1020031003, 'Tasks started')
    SUCCESS_UPDATE_TASK_DETAIL = (1020031004, 'Task updated successfully')
    SUCCESS_CANCEL_TASK = (1020031005, 'Task canceled successfully')
    SUCCESS_BATCH_DELETE_TASK = (1020031006, 'Task batch deleted successfully')

    PARTIAL_SUCCESS_BATCH_DELETE_TASK = (1020033001, 'Partial task deleted successfully')

    ERR_RETRY_RUNNING_TASK = (1020032001, 'Task is running')
    ERR_HOST_NOT_EXIST = (1020032002, 'Host not exist')
    ERR_ASSET_NOT_EXIST = (1020032003, 'Asset not exist')
    ERR_INVALID_DATA = (1020032004, 'Invalid data in request')
    ERR_GET_RESULT_ITEMS = (1020032005, 'Get host asset items result failed')
    ERR_TASK_FINISHED = (1020032006, 'Task finished, cant update')
    ERR_TASK_EXIST = (1020032007, 'Task with this name already exists')
    ERR_TASK_NOT_FOUND = (1020032008, 'Task not found')
    ERR_CANCEL_NOT_RUNNING_TASK = (1020032009, 'Task is not running, cant cancel')
    ERR_UPDATE_TASK_DETAIL = (1020032010, 'Task is not running, cant update')
    ERR_BATCH_DELETE_TASK = (1020032011, 'Task batch delete failed')
    ERR_CONFIG_TASKS_NUMBER = (1020032012, 'config error, MAX_RUNNING_TASKS type is not a number')
    ERR_CONFIG_TASK_TIMEOUT = (1020032013, 'config error, TASK_TIMEOUT type is not a number')
    ERR_CONFIG_TASK_POOL_TIMEOUT = (
        1020032014, 'config error, TASK_POOL_TIMEOUT type is not a number')
    ERR_TASK_UUID = (1020032015, 'task uuid error')
    ERR_TASK_RESULT_FILE_NOT_FOUND = (1020032016, 'task result file not found')
    ERR_TASK_RUNNING = (1020032017, 'Task is running')
    ERR_TASK_RESULT_NEED_DOWNLOAD = (1020032018, 'Task result dont support view,please download')

    ERR_UNKNOWN = (1020032999, 'Unknown error in health check')
