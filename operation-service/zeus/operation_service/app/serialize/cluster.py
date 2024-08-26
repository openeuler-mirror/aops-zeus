#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
from marshmallow import Schema, fields, validate
from vulcanus.restful.serialize.validate import ValidateRules
from zeus.host_information_service.database import Cluster


class GetClusterInfo_ResponseSchema(Schema):
    """
    Get cluster info response schema
    """

    cluster_ip = fields.String(attribute="backend_ip")

    class Meta:
        model = Cluster
        fields = ["cluster_id", "cluster_ip", "subcluster", "cluster_name", "synchronous_state", "description"]


class GetLocalClusterInfo_ResponseSchema(Schema):
    """
    Get local cluster info response schema
    """

    cluster_ip = fields.String(attribute="backend_ip")

    class Meta:
        model = Cluster
        fields = ["cluster_id", "cluster_name", "cluster_ip", "private_key", "public_key"]


class QueryClusterSchema(Schema):
    """
    Query cluster info.
    """

    cluster_ids = fields.List(
        fields.String(required=True, validate=validate.Length(min=1, max=36)),
        required=False,
        missing=[],
    )


class AddClusterSchema(Schema):
    """
    Add a single cluster.
    """

    cluster_id = fields.String(required=True, validate=validate.Length(min=1, max=36))
    cluster_name = fields.String(required=True, validate=validate.Length(min=1, max=20))
    description = fields.String(required=True, validate=validate.Length(min=1, max=60))
    cluster_ip = fields.String(required=True, validate=ValidateRules.ipv4_address_check)
    synchronous_state = fields.String(required=True, validate=validate.Length(min=1, max=20))


class DeleteClusterSchema(Schema):
    """
    Delete cluster.
    """

    cluster_list = fields.List(
        fields.String(required=True, validate=validate.Length(min=1, max=36)),
        required=False,
        missing=None,
    )


class UpdateClusterSchema(Schema):
    """
    Update cluster.
    """

    cluster_id = fields.String(required=True, validate=validate.Length(min=1, max=36))
    cluster_name = fields.String(required=True, validate=validate.Length(min=1, max=20))
    description = fields.String(required=True, validate=validate.Length(min=1, max=60))
    cluster_ip = fields.String(required=True, validate=ValidateRules.ipv4_address_check)
    synchronous_state = fields.String(required=False, validate=validate.Length(min=1, max=20))
