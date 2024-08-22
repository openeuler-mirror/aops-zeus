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
HOST_TEMPLATE_FILE_CONTENT_FOR_ZH = """host_ip,ssh_port,ssh_user,password,ssh_pkey,host_name,host_group_name,management
127.0.0.1,22,root,password,private key,test_host,test_host_group,FALSE
127.0.0.1,23,root,password,private key,test_host,test_host_group,FALSE
,,,,,,,
"提示:",,,,,,,
"1. 除登录密码与SSH登录秘钥外,其余信息都应提供有效值",,,,,,,
"2. 登录密码与SSH登录秘钥可选择一种填入,当两者都提供时,以SSH登录秘钥为准",,,,,,,
"3. 添加的主机信息不应存在重复信息(主机IP+端口重复)",,,,,,,
"4. 上传本文件前,请删除此部分提示内容",,,,,,,
"""

# host template file content
HOST_TEMPLATE_FILE_CONTENT_FOR_EN = """host_ip,ssh_port,ssh_user,password,ssh_pkey,host_name,host_group_name,management
127.0.0.1,22,root,password,private key,test_host,test_host_group,FALSE
127.0.0.1,23,root,password,private key,test_host,test_host_group,FALSE
,,,,,,,
"Note:",,,,,,,
"1. Except for the login password and SSH login key, other information should provide valid values",,,,,,,
"2. Choose to enter password or SSH key, the SSH key will be considered preferly when both are provided.",,,,,,,
"3. The combination of the host IP and port must be unique; no duplicate entries are allowed.",,,,,,,
"4. Please delete the note before uploading this file.",,,,,,,
"""


class HostTemplate:
    """A template class for managing host template file contents in different languages.

    Attributes:
        _content (dict): A dictionary containing the template file contents for
            different languages. The keys are language codes ("zh" for Chinese,
            "en" for English), and the values are the corresponding template file contents.

    Example:
        content = HostTemplate.get_file_content("zh")
        print(content)

        supported_languages = HostTemplate.support_lang
        print(supported_languages)
    """

    _content = {"zh": HOST_TEMPLATE_FILE_CONTENT_FOR_ZH, "en": HOST_TEMPLATE_FILE_CONTENT_FOR_EN}

    @classmethod
    def get_file_content(cls, lang: str = None) -> str:
        """Gets the template file content for the specified language.

        Args:
            lang (str, optional): The language code for the desired template file content.
                If not provided or if the specified language is not supported, defaults to English ("en").

        Returns:
            str: The template file content for the specified language, or the English content if
            the specified language is not supported.
        """
        if lang not in cls._content:
            lang = "en"
        return cls._content.get(lang)

    @staticmethod
    def support_lang():
        """Gets the list of supported languages.

        Returns:
            list: A list of language codes representing the supported languages (e.g., ["zh", "en"]).
        """
        return list(HostTemplate._content.keys())


class HostStatus:
    ONLINE = 0
    OFFLINE = 1
    UNESTABLISHED = 2
    SCANNING = 3
