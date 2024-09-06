from marshmallow import Schema, fields, validate

from zeus.operation_service.database import Operate

class GetOperateSchema(Schema):
    """
    Get Operate response schema
    """

    sort = fields.String(required=False, missing=None, validate=validate.OneOf(["operate_name", ""]))
    direction = fields.String(required=False, missing="desc", validate=validate.OneOf(["desc", "asc"]))
    page = fields.Integer(required=False, missing=None, validate=lambda s: s > 0)
    per_page = fields.Integer(required=False, missing=None, validate=lambda s: 50 > s > 0)


class AddOperateSchema(Schema):
    """
    Add Operate request schema
    """

    operate_name = fields.String(required=True, validate=lambda s: 0 < len(s) <= 128)


ModifyOperateSchema = AddOperateSchema

class OperateSchema(Schema):
    operate_id = fields.String(required=True, validate=lambda s: 0 < len(s) <= 36)
    operate_name = fields.String(required=True, validate=lambda s: 0 < len(s) <= 128)


    class Meta:
        model = Operate
        fields = ["operate_id", "operate_name", "create_time"]



class GetOperatePage_ResponseSchema(Schema):
    """
    Get Operate page response schema
    """
    operate_id = fields.String(required=True, validate=lambda s: 0 < len(s) <= 36)
    operate_name = fields.String(required=True, validate=lambda s: 0 < len(s) <= 128)

    class Meta:
        model = Operate
        fields = ["operate_id", "operate_name", "create_time"]