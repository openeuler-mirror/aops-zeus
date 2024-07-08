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


# host template file content
HOST_TEMPLATE_FILE_CONTENT = """host_ip,ssh_port,ssh_user,password,ssh_pkey,host_name,host_group_name,management
127.0.0.1,22,root,password,private key,test_host,test_host_group,FALSE
127.0.0.1,23,root,password,private key,test_host,test_host_group,FALSE
,,,,,,,
"提示:",,,,,,,
"1. 除登录密码与SSH登录秘钥外,其余信息都应提供有效值",,,,,,,
"2. 登录密码与SSH登录秘钥可选择一种填入,当两者都提供时,以SSH登录秘钥为准",,,,,,,
"3. 添加的主机信息不应存在重复信息(主机IP+端口重复)",,,,,,,
"4. 上传本文件前,请删除此部分提示内容",,,,,,,
"""


class HostStatus:
    ONLINE = 0
    OFFLINE = 1
    UNESTABLISHED = 2
    SCANNING = 3
