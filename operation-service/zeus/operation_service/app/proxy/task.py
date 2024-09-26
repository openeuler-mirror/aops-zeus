from datetime import datetime
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from requests import session
import sqlalchemy
import uuid
import json
from vulcanus.database.proxy import MysqlProxy
from vulcanus.database.helper import sort_and_page
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp.state import (
    DATA_DEPENDENCY_ERROR,
    DATA_EXIST,
    DATABASE_UPDATE_ERROR,
    DATABASE_DELETE_ERROR,
    DATABASE_INSERT_ERROR,
    DATABASE_QUERY_ERROR,
    NO_DATA,
    PARAM_ERROR,
    SUCCEED,
)
from zeus.operation_service.app.serialize.task import GetTaskPage_ResponseSchema
from zeus.operation_service.database import Task, TaskOperate, TaskHost, TaskCommand
from zeus.operation_service.app.core.framework.common.constant import TaskType
from zeus.operation_service.app.constant import Shcheduler

from zeus.operation_service.app.core.framework.common.result_code import TaskResultCode
from zeus.operation_service.app.core.framework.task.task_detail.task_detail_context import TaskDetailContext


def sche_job(task_id, action):
    from zeus.operation_service.app.core.task_manager import TaskManager
    tmng = TaskManager()
    tmng.do_action(task_id, action)

class TaskProxy(MysqlProxy):

    def __init__(self):
        super().__init__()
        if not self.session:
            self.connect()
        self.scheduler = Shcheduler(self.engine).scheduler
        if not self.scheduler.running:
            self.scheduler.start()

    @staticmethod
    def _get_task_column(column_name):
        if not column_name:
            return None
        return getattr(Task, column_name)
    
    def _query_tasks_page(self, page_filter):
        result = {"total_count": 0, "total_page": 0, "task_infos": []}
        # groups = cache.get_user_group_hosts()
        # filters = {HostGroup.host_group_id.in_(list(groups.keys()))}
        # if page_filter["cluster_ids"]:
        #     filters.add(HostGroup.cluster_id.in_(page_filter["cluster_ids"]))
        tasks_query = self.session.query(Task).filter(Task.task_type == page_filter["task_type"])
        result["total_count"] = tasks_query.count()
        if not result["total_count"]:
            return result
        sort_column = self._get_task_column(page_filter["sort"])
        processed_query, total_page = sort_and_page(
            tasks_query, sort_column, page_filter["direction"], page_filter["per_page"], page_filter["page"]
        )
        result['total_page'] = total_page
        result['task_infos'] = GetTaskPage_ResponseSchema(many=True).dump(processed_query.all())
        return result

    def get_tasks(self, task_page_filter):
        """
        Get host according to host group from table

        Args:
            host_page_filter (dict): parameter, e.g.
                {
                    "host_group_list": ["group1", "group2"]
                    "management": False
                }

        Returns:
            int: status code
            dict: query result
        """
        result = {}
        try:
            result = self._query_tasks_page(task_page_filter)
            LOGGER.debug("Query tasks succeed")
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("Query tasks fail")
            return DATABASE_QUERY_ERROR, result

    def set_trigger(self, trigger_type: str, trigger_params: dict):
        trigger_map = {
            "cron": CronTrigger,
            "interval": IntervalTrigger,
            "single": DateTrigger,
        }
        return trigger_map[trigger_type](**trigger_params)

    # 根据参数设置定时任务
    def add_task_sheduler(self, scheduler_info: dict, task_id: str):
        trigger_type = scheduler_info.get("type")
        trigger_params = scheduler_info.get("params")
        if isinstance(trigger_type, str) and isinstance(trigger_params, dict):        
            self.scheduler.add_job(
                trigger = self.set_trigger(trigger_type, trigger_params), 
                id=f"scheduler_{task_id}",
                func=sche_job,
                args=(task_id, 'start')
            )
            LOGGER.info("add scheduler job for task [%s] successfully", task_id)

    # 将对应task_id的定时任务一并清除
    def del_task_sheduler(self, task_id):
        job = self.scheduler.get_job(f"scheduler_{task_id}")
        if job:
            self.scheduler.remove_job(job.id)
    
    def add_task(self, data):
        try:
            task = self.session.query(Task).filter(Task.task_name == data['task_name']).first()
            if task:
                return DATA_EXIST
            if len(data['host_ids']) == 0:
                return NO_DATA
            task_id = str(uuid.uuid1())
            if data['task_type'] == TaskType.SCRIPT_EXECUTION:
                self.session.add(TaskOperate(task_id=task_id, operate_id=data['action_ids'][0]))
            if data['task_type'] == TaskType.COMMAND_EXECUTION:
                data['only_push'] = False
                self.session.add(TaskCommand(task_id=task_id, command_id=data['action_ids'][0]))
            for host_id in data['host_ids']:
                self.session.add(TaskHost(task_id=task_id, host_id=host_id))
            
            task_detail, task_total = TaskDetailContext(data).get_task_detail()
            data.pop('host_ids')
            data.pop('action_ids')
            scheduler_info = None
            if data.get("scheduler_info"):
                scheduler_info = data.pop("scheduler_info")
            if data.get("remote_path"):
                data.pop("remote_path")
            self.session.add(Task(task_name=data['task_name'], 
                                  task_type=data['task_type'],
                                  task_id=task_id, 
                                  task_detail=task_detail, 
                                  task_total=task_total))
            if scheduler_info:
                self.add_task_sheduler(scheduler_info, task_id)
            self.session.commit()
            LOGGER.info("add task [%s] succeed", data['task_name'])
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            self.session.rollback()
            LOGGER.error("add task [%s] fail", data['task_name'])
            return DATABASE_INSERT_ERROR

    def modify_task_scheduler(self, data):
        task_id = data.get("task_id", None)
        if not task_id:
            LOGGER.error("Not give param[task_id]")
            return PARAM_ERROR
        try:
            _ = self.session.query(Task).filter(Task.task_id == task_id).first()
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error(f"Not find task[{task_id}].")
            return NO_DATA
        scheduler_info = data.get("scheduler_info", None)

        task_detail_str = self.get_task_by_id(task_id=task_id).task_detail
        task_detail = json.loads(task_detail_str)
        task_detail['ext_props']['scheduler_info'] = scheduler_info
        self.update_task(task_id, task_detail=json.dumps(task_detail))
        self.del_task_sheduler(task_id)

        if not scheduler_info:
            LOGGER.error("cancel scheduler_info")
            return SUCCEED
        self.add_task_sheduler(scheduler_info, task_id)

        return SUCCEED
    
    def batch_delete_task(self, task_ids):
        delete_success_task_ids = list()
        delete_failed_task_ids = list()
        for task_id in task_ids:
            try:
                task = self.session.query(Task).filter(Task.task_id == task_id).first()
                if not task:
                    delete_success_task_ids.append(task_id)
                    continue
                self.del_task_sheduler(task_id)
                self.delete_task_associations(task_id)
                self.session.delete(task)
                self.session.commit()
                LOGGER.info(f"Task {task_id} delete succeed ")
            except sqlalchemy.exc.SQLAlchemyError as error:
                LOGGER.error(error)
                LOGGER.error(f"delete task {task_id} fail")
                self.session.rollback()
                delete_failed_task_ids.append(task_id)
                continue
            delete_success_task_ids.append(task_id)

        if len(delete_success_task_ids) == len(task_ids):
            return SUCCEED, {}
        else:
            return DATABASE_DELETE_ERROR, delete_failed_task_ids
    
    def delete_task_associations(self, task_id):
        task_operate_associations = self.session.query(TaskOperate).filter(TaskOperate.task_id == task_id).all()
        for toa in task_operate_associations:
            self.session.delete(toa)
        task_command_associations = self.session.query(TaskCommand).filter(TaskCommand.task_id == task_id).all()
        for tca in task_command_associations:
            self.session.delete(tca)
        task_host_associations = self.session.query(TaskHost).filter(TaskHost.task_id == task_id).all()
        for tha in task_host_associations:
            self.session.delete(tha)

    def get_task_info(self, task_id):
        try:
            task = self.session.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                return NO_DATA, None, None
            task_host_association = self.session.query(TaskHost).filter(TaskHost.task_id == task_id).all()
            host_ids = list()
            for tha in task_host_association:
                host_ids.append(tha.host_id)
            return SUCCEED, task, host_ids
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR, None, None

    def get_task_by_id(self, task_id):
        return self.session.query(Task).get(task_id)
    
    def get_commands(self, task_id):
        commands = self.session.query(TaskCommand).filter(TaskCommand.task_id == task_id).all()
        return commands

    def set_wait_status(self, task_id):
        self.session.query(Task).filter(Task.task_id == task_id).update(
            {'status': TaskResultCode.WAITING.code, 'progress': 0.0, 'end_time': None})
        self.session.commit()

    def set_running_status(self, task_id):
        self.session.query(Task).filter(Task.task_id == task_id).update(
            {'status': TaskResultCode.RUNNING.code, 'start_time': datetime.now()})
        self.session.commit()

    def set_failed_status(self, task_id, error_code):
        self.session.query(Task).filter(Task.task_id == task_id).update(
            {'status': error_code, 'end_time': datetime.now()})
        self.session.commit()

    def update_progress(self, task_id, progress):
        task = self.session.query(Task).filter(Task.task_id == task_id).first()
        if task.status == TaskResultCode.RUNNING.code:
            task.progtess = progress
            self.session.commit()

    def reset_task_status(self, task_id):
        self.session.query(Task).filter(Task.task_id == task_id).update(
            {'status': TaskResultCode.RUNNABLE.code, 'progress': 0.0, 'end_time': None})
        self.session.commit()

    def update_task(self, task_id, **params):
        self.session.query(Task).filter(Task.task_id == task_id).update(params)
        self.session.commit()

    def cancel_task(self, task_id):
        self.session.query(Task).filter(Task.task_id == task_id).update(
            {'status': TaskResultCode.CANCELED.code, 'progress': 0.0, 'end_time': None})
        self.session.commit()