#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2020-2020. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
import click


class CiGroup(click.Group):
    """
    Command line parameter group to simplify common parameters
    """

    version_option = click.Option(
        ["--version", "-V"],
        help="Show version information",
        expose_value=False,
        is_flag=True,
        is_eager=True,
    )
    help_option = click.Option(
        ["--help", "-h"], help="Show this help message and exit", expose_value=False, is_flag=True, is_eager=True
    )

    def __init__(self, **extra) -> None:
        params = list(extra.pop("params", None) or ())
        params.append(CiGroup.version_option)
        params.append(CiGroup.help_option)

        super().__init__(params=params, **extra)

    def format_usage(self, ctx, formatter):
        formatter.write_usage(ctx.command_path)

    def main(self, *args, **kwargs):
        """
        Command invocation entry,Contains commands and parameters
        """
        return super(CiGroup, self).main(*args, **kwargs)
