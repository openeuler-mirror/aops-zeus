from marshmallow import Schema, fields, validate

from zeus.operation_service.database import Command

class GetCommandSchema(Schema):
    """
    Get Command response schema
    """

    sort = fields.String(required=False, missing=None, validate=validate.OneOf(["command_name", ""]))
    direction = fields.String(required=False, missing="desc", validate=validate.OneOf(["desc", "asc"]))
    page = fields.Integer(required=False, missing=None, validate=lambda s: s > 0)
    per_page = fields.Integer(required=False, missing=None, validate=lambda s: 50 > s > 0)


class AddCommandSchema(Schema):
    """
    Add Command request schema
    """

    command_name = fields.String(required=True, validate=lambda s: 0 < len(s) <= 128)
    lang = fields.String(required=False, validate=lambda s: 0 < len(s) <= 64)
    content = fields.String(required=True)
    timeout = fields.Integer(required=False)
    execution_user = fields.String(required=False, validate=lambda s: 0 < len(s) <= 128)

ModifyCommandSchema = AddCommandSchema

class CommandSchema(Schema):
    """
    HostGroup info response schema
    """
    command_id = fields.String(required=True, validate=lambda s: 0 < len(s) <= 36)
    command_name = fields.String(required=True, validate=lambda s: 0 < len(s) <= 128)
    lang = fields.String(required=False, validate=lambda s: 0 < len(s) <= 64)
    content = fields.String(required=True)
    timeout = fields.Integer(required=False)
    execution_user = fields.String(required=False, validate=lambda s: 0 < len(s) <= 128)

    class Meta:
        model = Command
        fields = ["command_id", "command_name", "lang", "content", "create_time", "timeout", "execution_user"]



class GetCommandPage_ResponseSchema(Schema):
    """
    Get Command page response schema
    """
    command_id = fields.String(required=True, validate=lambda s: 0 < len(s) <= 36)
    command_name = fields.String(required=True, validate=lambda s: 0 < len(s) <= 128)
    lang = fields.String(required=False, validate=lambda s: 0 < len(s) <= 64)
    content = fields.String(required=True)
    timeout = fields.Integer(required=False)
    execution_user = fields.String(required=False, validate=lambda s: 0 < len(s) <= 128)

    class Meta:
        model = Command
        fields = ["command_id", "command_name", "lang", "content", "create_time", "timeout", "execution_user"]