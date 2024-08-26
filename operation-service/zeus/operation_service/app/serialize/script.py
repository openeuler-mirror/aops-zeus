from marshmallow import Schema, fields, validate

from zeus.operation_service.database import Script

class GetScriptSchema(Schema):
    """
    Get Script response schema
    """

    sort = fields.String(required=False, missing=None, validate=validate.OneOf(["script_name", ""]))
    direction = fields.String(required=False, missing="desc", validate=validate.OneOf(["desc", "asc"]))
    page = fields.Integer(required=False, missing=None, validate=lambda s: s > 0)
    per_page = fields.Integer(required=False, missing=None, validate=lambda s: 50 > s > 0)


class AddScriptSchema(Schema):
    """
    Add Script request schema
    """

    script_name = fields.String(required=True, validate=lambda s: 0 < len(s) <= 128)
    command = fields.String(required=True)
    timeout = fields.Integer(required=False)
    execution_user = fields.String(required=False, validate=lambda s: 0 < len(s) <= 128)
    arch = fields.String(required=False, validate=lambda s: 0 < len(s) <= 128)
    os_name = fields.String(required=False, validate=lambda s: 0 < len(s) <= 128)
    
    operate_id = fields.String(validate=lambda s: 0 < len(s) <= 36)

ModifyScriptSchema = AddScriptSchema

class ScriptSchema(Schema):
    script_id = fields.String(required=True, validate=lambda s: 0 < len(s) <= 36)
    script_name = fields.String(required=True, validate=lambda s: 0 < len(s) <= 128)
    command = fields.String(required=True)
    timeout = fields.Integer(required=False)
    execution_user = fields.String(required=False, validate=lambda s: 0 < len(s) <= 128)


    class Meta:
        model = Script
        fields = ["script_id", "script_name", "command", "create_time", "timeout", "execution_user", "arch", "os_name"]



class GetScriptPage_ResponseSchema(Schema):
    """
    Get Script page response schema
    """
    script_id = fields.String(required=True, validate=lambda s: 0 < len(s) <= 36)
    script_name = fields.String(required=True, validate=lambda s: 0 < len(s) <= 128)
    command = fields.String(required=True)
    timeout = fields.Integer(required=False)
    execution_user = fields.String(required=False, validate=lambda s: 0 < len(s) <= 128)

    class Meta:
        model = Script
        fields = ["script_id", "script_name", "command", "create_time", "timeout", "execution_user", "arch", "os_name"]