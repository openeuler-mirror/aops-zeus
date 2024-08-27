from vulcanus.log.log import LOGGER
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse
from vulcanus.conf.constant import HOSTS_FILTER

from zeus.operation_service.app.settings import configuration
from zeus.operation_service.app.serialize.task import GetTaskSchema, AddTaskSchema, TaskSchema, ModifyTaskSchedulerSchema
from zeus.operation_service.app.proxy.task import TaskProxy
from zeus.operation_service.app.core.task_manager import TaskManager
from zeus.operation_service.app.core.framework.task.task_result.task_result_context import TaskResultContext
from flask import request,g

class TaskManageAPI(BaseResponse):
    @BaseResponse.handle(schema=GetTaskSchema, proxy=TaskProxy)
    def get(self, callback: TaskProxy, **params):
        """
        Get tasks

        Args:
            sort (str): sort according to specified field
            direction (str): sort direction
            page (int): current page
            per_page (int): count per page

        Returns:
            dict: response body
        """
        status_code, result = callback.get_tasks(params)
        return self.response(code=status_code, data=result)

    @BaseResponse.handle(schema=AddTaskSchema, proxy=TaskProxy)
    def post(self, callback: TaskProxy, **params):
        status_code = callback.add_task(params)
        return self.response(code=status_code)

    @BaseResponse.handle(schema=ModifyTaskSchedulerSchema, proxy=TaskProxy)
    def patch(self, callback: TaskProxy, **params):
        status_code = callback.modify_task_scheduler(params)
        return self.response(code=status_code)

    
    @BaseResponse.handle(proxy=TaskProxy)
    def delete(self, callback: TaskProxy, **params):
        status_code, result = callback.batch_delete_task(params['task_ids'])
        return self.response(code=status_code, data=result)


class TaskInfoManageAPI(BaseResponse):
    
    @BaseResponse.handle(proxy=TaskProxy)
    def get(self, callback: TaskProxy, task_id, **params):
        status_code, task, host_ids = callback.get_task_info(task_id)
        if task:
            task =  TaskSchema().dump(task)
            task['host_ids'] = host_ids
        return self.response(code=status_code, data=task)
    
    @BaseResponse.handle()
    def post(self, task_id):
        action = request.args.get('action')
        task_mng = TaskManager()
        code, result = task_mng.do_action(task_id, action)
        return self.response(code=code, data=result)

class TaskResultAPI(BaseResponse):

    @BaseResponse.handle(proxy=TaskProxy)
    def post(self, callback: TaskProxy, **params):
        task = callback.get_task_by_id(params["task_id"])
        task_result = TaskResultContext(task)
        code, result = task_result.get_items_detail(params)
        return self.response(code=code, data=result)
