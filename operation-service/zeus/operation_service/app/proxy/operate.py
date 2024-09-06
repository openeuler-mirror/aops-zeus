from datetime import datetime
import re
import sqlalchemy
import uuid
from sqlalchemy import func
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
from zeus.operation_service.app.serialize.operate import GetOperatePage_ResponseSchema
from zeus.operation_service.database import Operate, OperateScript

class OperateProxy(MysqlProxy):

    def __init__(self):
        super().__init__()
        if not self.session:
            self.connect()

    def get_operates(self, operate_page_filter):
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
            result = self._query_operates_page(operate_page_filter)
            LOGGER.debug("Query operates succeed")
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("Query operates fail")
            return DATABASE_QUERY_ERROR, result
    
    def add_operate(self, data):
        try:
            self.session.add(Operate(**data, operate_id=str(uuid.uuid1()), create_time=datetime.now()))
            self.session.commit()
            LOGGER.info("add operate [%s] succeed", data['operate_name'])
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            self.session.rollback()
            LOGGER.error("add operate [%s] fail", data['operate_name'])
            return DATABASE_INSERT_ERROR

    def batch_delete_operate(self, operate_ids):
        delete_success_operate_ids = list()
        delete_failed_operate_ids = list()
        for operate_id in operate_ids:
            try:
                operate = self.session.query(Operate).filter(Operate.operate_id == operate_id).first()
                if not operate:
                    delete_success_operate_ids.append(operate_id)
                    continue
                operate_script_associations = self.session.query(OperateScript).filter(OperateScript.operate_id == operate_id).all()
                for osa in operate_script_associations:
                    self.session.delete(osa)
                self.session.delete(operate)
                self.session.commit()
                LOGGER.info(f"Operate {operate_id} delete succeed ")
            except sqlalchemy.exc.SQLAlchemyError as error:
                LOGGER.error(error)
                LOGGER.error(f"delete operate {operate_id} fail")
                self.session.rollback()
                delete_failed_operate_ids.append(operate_id)
                continue
            delete_success_operate_ids.append(operate_id)

        if len(delete_success_operate_ids) == len(operate_ids):
            return SUCCEED, {}
        else:
            return DATABASE_DELETE_ERROR, delete_failed_operate_ids

    def get_operate_info(self, operate_id):
        try:
            operate = self.session.query(Operate).filter(Operate.operate_id == operate_id).first()
            if not operate:
                return NO_DATA, None
            return SUCCEED, operate
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR, None

    def modify_operate_info(self, operate_id, data):
        try:
            modified_rows = self.session.query(Operate).filter_by(operate_id = operate_id).update(data)
            self.session.commit()
            if modified_rows != 1:
                LOGGER.info("update operate [%s] failed", data['operate_name'])
                return DATABASE_UPDATE_ERROR, None
            operate = self.session.query(Operate).filter_by(operate_id = operate_id).first()
            if not operate:
                return NO_DATA, None
            LOGGER.info("update operate [%s] succeed", data['operate_name'])
            return SUCCEED, operate
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_UPDATE_ERROR, None



    @staticmethod
    def _get_operate_column(column_name):
        if not column_name:
            return None
        return getattr(Operate, column_name)
    
    def _query_operates_page(self, page_filter):
        result = {"total_count": 0, "total_page": 0, "operate_infos": []}
        # groups = cache.get_user_group_hosts()
        # filters = {HostGroup.host_group_id.in_(list(groups.keys()))}
        # if page_filter["cluster_ids"]:
        #     filters.add(HostGroup.cluster_id.in_(page_filter["cluster_ids"]))
        operates_query = self.session.query(Operate)
        
        result["total_count"] = operates_query.count()
        if not result["total_count"]:
            return result
        sort_column = self._get_operate_column(page_filter["sort"])
        processed_query, total_page = sort_and_page(
            operates_query, sort_column, page_filter["direction"], page_filter["per_page"], page_filter["page"]
        )
        result['total_page'] = total_page
        result['operate_infos'] = GetOperatePage_ResponseSchema(many=True).dump(processed_query.all())
        return result