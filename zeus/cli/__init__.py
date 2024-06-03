#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2021. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
import sys
from zeus.cli.base import CiGroup
from zeus.cli.service import service
from zeus.cli.database import database
from zeus.cli.config import config
from zeus.cli.deploy import deploy


aops_cli = CiGroup(help="""Aops command tool line""")
aops_cli.add_command(service)
aops_cli.add_command(database)
aops_cli.add_command(config)
aops_cli.add_command(deploy)


def main():
    """
    The starting method of a terminal command
    """

    aops_cli.main(args=sys.argv[1:])


__all__ = "main"
