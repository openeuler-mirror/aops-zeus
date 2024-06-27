#!/usr/bin/python3
# ******************************************************************************
# Copyright (C) 2023 isoftstone Technologies Co., Ltd. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
"""
@FileName: conf_trace.py
@Time: 2024/4/19 10:23
@Author: JiaoSiMao
Description:
"""
from marshmallow import Schema, fields, validate


class ConfTraceMgmtSchema(Schema):
    """
    validators for parameter of /conftrace/mgmt
    """
    host_ids = fields.List(fields.Integer(), required=True)
    action = fields.Str(required=True, validate=validate.OneOf(['stop', 'start', 'update']))
    conf_files = fields.List(fields.String(), required=False)
    domain_name = fields.String(required=True, validate=lambda s: len(s) > 0)


class PtraceSchema(Schema):
    cmd = fields.String(required=True, validate=lambda s: len(s) > 0)
    pid = fields.Integer(required=True)


class ConfTraceDataSchema(Schema):
    """
    validators for parameter of /conftrace/data
    """
    host_id = fields.Integer(required=True, validate=lambda s: s > 0)
    domain_name = fields.String(required=True, validate=lambda s: len(s) > 0)
    file = fields.String(required=True, validate=lambda s: len(s) > 0)
    syscall = fields.String(required=True)
    pid = fields.Integer(required=True, validate=lambda s: s > 0)
    inode = fields.Integer(required=True)
    cmd = fields.String(required=True, validate=lambda s: len(s) > 0)
    ptrace = fields.List(fields.Nested(PtraceSchema()), required=True)
    flag = fields.Integer(required=True)


class ConfTraceQuerySchema(Schema):
    """
    validators for parameter of /conftrace/query
    """
    domain_name = fields.String(required=True, validate=lambda s: len(s) > 0)
    host_id = fields.Integer(required=True, validate=lambda s: s > 0)
    conf_name = fields.String(required=True, validate=lambda s: len(s) > 0)
    sort = fields.String(required=False, validate=validate.OneOf(["create_time", "host_id", ""]))
    direction = fields.String(required=False, validate=validate.OneOf(["desc", "asc"]))
    page = fields.Integer(required=False, validate=lambda s: s > 0)
    per_page = fields.Integer(required=False, validate=lambda s: 50 > s > 0)


class ConfTraceDataDeleteSchema(Schema):
    """
        validators for parameter of /conftrace/delete
        """
    domain_name = fields.String(required=True, validate=lambda s: len(s) > 0)
    host_ids = fields.List(fields.Integer(), required=False)
