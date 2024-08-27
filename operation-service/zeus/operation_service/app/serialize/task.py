from marshmallow import Schema, fields, validate

from zeus.operation_service.database import Task

class GetTaskSchema(Schema):
    """
    Get Task response schema
    """

    sort = fields.String(required=False, missing=None, validate=validate.OneOf(["task_name", ""]))
    direction = fields.String(required=False, missing="desc", validate=validate.OneOf(["desc", "asc"]))
    page = fields.Integer(required=False, missing=None, validate=lambda s: s > 0)
    per_page = fields.Integer(required=False, missing=None, validate=lambda s: 50 > s > 0)
    task_type = fields.String(required=True)

class AddTaskSchema(Schema):

    task_name = fields.String(required=True, validate=lambda s: len(s) <= 255)
    task_type = fields.String(required=True)
    host_ids = fields.List(fields.String(required=True, validate=lambda s: 0 < len(s) <= 36))
    action_ids = fields.List(fields.String(required=True, validate=lambda s: 0 < len(s) <= 36))
    scheduler_info = fields.Dict()
    only_push = fields.Bool(required=False)

class ModifyTaskSchedulerSchema(Schema):
    task_id = fields.String(required=True, validate=lambda s: len(s) <= 255)
    scheduler_info = fields.Dict()

class TaskSchema(Schema):

    task_id = fields.String(required=True, validate=lambda s: 0 < len(s) <= 36)
    task_name = fields.String(required=True, validate=lambda s: len(s) <= 255)
    command = fields.String(required=True)
    timeout = fields.Integer(required=False)
    execution_user = fields.String(required=False, validate=lambda s: 0 < len(s) <= 128)


    class Meta:
        model = Task
        fields = ["task_id", "task_name", "status", "progress", "start_time", "end_time", "task_detail", "task_type"]


class GetTaskPage_ResponseSchema(Schema):
    """
    Get Task page response schema
    """
    task_id = fields.String(required=True, validate=lambda s: 0 < len(s) <= 36)
    task_name = fields.String(required=True, validate=lambda s: len(s) <= 255)
    status = fields.String(required=True, validate=lambda s: s <= 64)
    # progress = fields.Float(required=True, missing=0.0, validate=lambda s: 100.0 >= s >= 0.0)
    task_type = fields.String(required=True)

    class Meta:
        model = Task
        fields = ["task_id", "task_name", "status", "progress", "start_time", "end_time", "task_detail", "task_type"]
