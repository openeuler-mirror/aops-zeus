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
from zeus.operation_service.app.serialize.command import GetCommandPage_ResponseSchema
from zeus.operation_service.database import Command

class CommandProxy(MysqlProxy):

    def get_commands(self, command_page_filter):
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
            result = self._query_commands_page(command_page_filter)
            LOGGER.debug("Query commands succeed")
            return SUCCEED, result
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            LOGGER.error("Query commands fail")
            return DATABASE_QUERY_ERROR, result
    
    def add_command(self, data):
        try:
            command = self.session.query(Command).filter(Command.command_name == data['command_name']).first()
            if command:
                return DATA_EXIST
            self.session.add(Command(**data, command_id=str(uuid.uuid1()), create_time=datetime.now()))
            self.session.commit()
            LOGGER.info("add command [%s] succeed", data['command_name'])
            return SUCCEED
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            self.session.rollback()
            LOGGER.error("add command [%s] fail", data['command_name'])
            return DATABASE_INSERT_ERROR

    def batch_delete_command(self, command_ids):
        delete_success_command_ids = list()
        delete_failed_command_ids = list()
        for command_id in command_ids:
            try:
                command = self.session.query(Command).filter(Command.command_id == command_id).first()
                if not command:
                    delete_success_command_ids.append(command_id)
                    continue
                self.session.delete(command)
                self.session.commit()
                LOGGER.info(f"Command {command_id} delete succeed ")
            except sqlalchemy.exc.SQLAlchemyError as error:
                LOGGER.error(error)
                LOGGER.error(f"delete command {command_id} fail")
                self.session.rollback()
                delete_failed_command_ids.append(command_id)
                continue
            delete_success_command_ids.append(command_id)

        if len(delete_success_command_ids) == len(command_ids):
            return SUCCEED, {}
        else:
            return DATABASE_DELETE_ERROR, delete_failed_command_ids

    def get_command_info(self, command_id):
        try:
            command = self.session.query(Command).filter(Command.command_id == command_id).first()
            if not command:
                return NO_DATA, None
            return SUCCEED, command
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_QUERY_ERROR, None

    def modify_command_info(self, command_id, data):
        try:
            modified_rows = self.session.query(Command).filter_by(command_id = command_id).update(data)
            self.session.commit()
            if modified_rows != 1:
                LOGGER.info("update command [%s] failed", data['command_name'])
                return DATABASE_UPDATE_ERROR, None
            command = self.session.query(Command).filter_by(command_id = command_id).first()
            if not command:
                return NO_DATA, None
            LOGGER.info("update command [%s] succeed", data['command_name'])
            return SUCCEED, command
        except sqlalchemy.exc.SQLAlchemyError as error:
            LOGGER.error(error)
            return DATABASE_UPDATE_ERROR, None



    @staticmethod
    def _get_command_column(column_name):
        if not column_name:
            return None
        return getattr(Command, column_name)
    
    def _query_commands_page(self, page_filter):
        result = {"total_count": 0, "total_page": 0, "command_infos": []}
        # groups = cache.get_user_group_hosts()
        # filters = {HostGroup.host_group_id.in_(list(groups.keys()))}
        # if page_filter["cluster_ids"]:
        #     filters.add(HostGroup.cluster_id.in_(page_filter["cluster_ids"]))
        commands_query = self.session.query(Command)
        
        result["total_count"] = commands_query.count()
        if not result["total_count"]:
            return result
        sort_column = self._get_command_column(page_filter["sort"])
        processed_query, total_page = sort_and_page(
            commands_query, sort_column, page_filter["direction"], page_filter["per_page"], page_filter["page"]
        )
        result['total_page'] = total_page
        result['command_infos'] = GetCommandPage_ResponseSchema(many=True).dump(processed_query.all())
        return result