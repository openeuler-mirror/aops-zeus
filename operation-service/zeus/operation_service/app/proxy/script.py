import os
from requests import delete
import sqlalchemy
import uuid
import shutil

from datetime import datetime
from sqlalchemy import func
from vulcanus.database.proxy import MysqlProxy
from vulcanus.database.helper import sort_and_page
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp.state import (
    DATA_EXIST,
    OPERATION_WRONG_SUPPORT_CONFIG,
    DATABASE_UPDATE_ERROR,
    DATABASE_DELETE_ERROR,
    DATABASE_INSERT_ERROR,
    DATABASE_QUERY_ERROR,
    NO_DATA,
    PARAM_ERROR,
    SUCCEED,
    TASK_DEPENDENCY_ERROR
)
from zeus.operation_service.app.serialize.script import GetScriptPage_ResponseSchema
from zeus.operation_service.database import Script, TaskOperate, OperateScript, Operate
from zeus.operation_service.app.constant import SCRIPTS_DIR
from zeus.operation_service.app.settings import configuration
from zeus.operation_service.app.core.file_util import U_RW
from flask import request

class ScriptProxy(MysqlProxy):

    def __init__(self):
        super().__init__()
        if not self.session:
            self.connect()

    def get_scripts(self, script_page_filter):
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
            result = self._query_scripts_page(script_page_filter)
            LOGGER.debug("Query scripts succeed")
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("Query scripts fail")
            return DATABASE_QUERY_ERROR, result
    
    def add_script(self, data):
        try:
            script_id = str(uuid.uuid1())
            # 如果选择的操作名，则设置相关关联
            if "operate_id" in data.keys():
                operate_id = data.pop("operate_id")
                # 如果该操作名下已有对应arch，os_name脚本，失败
                operate_scripte_associations = self.session.query(OperateScript).filter(OperateScript.operate_id == operate_id).all()
                for osa in operate_scripte_associations:
                    script_nums = self.session.query(Script).filter(Script.script_id==osa.script_id,
                                                               Script.arch==data['arch'],
                                                               Script.os_name==data['os_name']).count()
                    if script_nums>0:
                        return DATA_EXIST, operate_id
                self.session.add(OperateScript(operate_id=operate_id, script_id=script_id))
            self.session.add(Script(**data, script_id=script_id, create_time=datetime.now()))
            self.session.commit()
            LOGGER.info("add script [%s] succeed", data['script_name'])
            return SUCCEED, script_id
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            self.session.rollback()
            LOGGER.error("add script [%s] fail", data['script_name'])
            return DATABASE_INSERT_ERROR, None

    def upload_file(self, script_id, data):
        script = self.session.query(Script).filter_by(script_id = script_id)
        if not script:
            return PARAM_ERROR
        return self._save_file(script_id)
        

    def batch_delete_script(self, script_ids):
        delete_success_script_ids = list()
        delete_failed_script_ids = list()
        for script_id in script_ids:
            try:
                script = self.session.query(Script).filter(Script.script_id == script_id).first()
                if not script:
                    delete_success_script_ids.append(script_id)
                    continue

                operate_script_associations = self.session.query(OperateScript).filter(OperateScript.script_id == script_id).all()
                for osa in operate_script_associations:
                    self.session.delete(osa)
                self.session.delete(script)
                self.session.commit()

                save_file_dir = os.path.join(SCRIPTS_DIR, script_id)
                if os.path.exists(save_file_dir):
                    shutil.rmtree(save_file_dir)
                LOGGER.info(f"Script {script_id} delete succeed ")
            except sqlalchemy.exc.SQLAlchemyError as error:
                LOGGER.error(error)
                LOGGER.error(f"delete script {script_id} fail")
                self.session.rollback()
                delete_failed_script_ids.append(script_id)
                continue
            delete_success_script_ids.append(script_id)

        if len(delete_success_script_ids) == len(script_ids):
            return SUCCEED, {}
        else:
            return DATABASE_DELETE_ERROR, delete_failed_script_ids

    def get_script_info(self, script_id):
        try:
            script = self.session.query(Script).filter(Script.script_id == script_id).first()
            operate_script_association = self.session.query(OperateScript).filter(Script.script_id == script_id).first()
            if not script:
                return NO_DATA, None, None
            return SUCCEED, script, operate_script_association.operate_id
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR, None, None

    def modify_script_info(self, script_id, data):
        try:
            if "operate_id" in data.keys():
                operate_id = data.pop("operate_id")
                self.session.query(OperateScript).filter_by(script_id = script_id).update({"operate_id": operate_id})
            modified_rows = self.session.query(Script).filter_by(script_id = script_id).update(data)
            self.session.commit()
            if modified_rows != 1:
                LOGGER.info("update script [%s] failed", data['script_name'])
                return DATABASE_UPDATE_ERROR, None
            script = self.session.query(Script).filter_by(script_id = script_id).first()
            if not script:
                return NO_DATA, None
            LOGGER.info("update script [%s] succeed", data['script_name'])
            return SUCCEED, script
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            self.session.rollback()
            return DATABASE_UPDATE_ERROR, None

    def get_script_by_operate_id(self, operate_id):
        operate_script_associations = self.session.query(OperateScript).filter_by(operate_id = operate_id).all()
        scripts = list()
        for osa in operate_script_associations:
            scripts.append(self.session.query(Script).get(osa.script_id))
        return scripts

    @staticmethod
    def _get_script_column(column_name):
        if not column_name:
            return None
        return getattr(Script, column_name)
    
    def _query_scripts_page(self, page_filter):
        result = {"total_count": 0, "total_page": 0, "script_infos": []}
        # groups = cache.get_user_group_hosts()
        # filters = {HostGroup.host_group_id.in_(list(groups.keys()))}
        # if page_filter["cluster_ids"]:
        #     filters.add(HostGroup.cluster_id.in_(page_filter["cluster_ids"]))
        scripts_query = self.session.query(Script)
        
        result["total_count"] = scripts_query.count()
        if not result["total_count"]:
            return result
        sort_column = self._get_script_column(page_filter["sort"])
        processed_query, total_page = sort_and_page(
            scripts_query, sort_column, page_filter["direction"], page_filter["per_page"], page_filter["page"]
        )
        result['total_page'] = total_page
        script_infos = GetScriptPage_ResponseSchema(many=True).dump(processed_query.all())
        for script in script_infos:
            operate_script = self.session.query(OperateScript).filter_by(script_id=script['script_id']).first()
            if operate_script:
                script['operate_id'] = operate_script.operate_id
                script['operate_name'] = self.session.query(Operate).filter_by(operate_id=script['operate_id']).first().operate_name
            else:
                script['operate_id'] = ""
                script['operate_name'] = ""
        result['script_infos'] = script_infos
        return result


    def _save_file(self, script_id):
        file_list = request.files.getlist('files')

        try:
            save_file_dir = os.path.join(SCRIPTS_DIR, script_id)
            if not os.path.exists(save_file_dir):
                os.makedirs(save_file_dir, exist_ok=True)
            # 当前上传不包含目录结构
            for file in file_list:
                file_full = os.path.join(save_file_dir, str(file.filename))
                file.save(file_full)

        except Exception as e:
            LOGGER.error(f'Upload script error.{e}')
            shutil.rmtree(save_file_dir)
            return NO_DATA

        return SUCCEED
    
    def get_support_os_info(self):
        info = {}
        try:
            arch = configuration.support.os_arch
            name = configuration.support.os_name
        except AttributeError:
            LOGGER.error("config file not find supprot.os_arch or support.os_name")
            return OPERATION_WRONG_SUPPORT_CONFIG, info
        info = {'os_aarch': arch, 'os_name': name}
        return SUCCEED, info
        
