#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2023. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/

import uuid
from sqlalchemy import Column
from sqlalchemy.sql.sqltypes import Integer, String, DateTime, Text, Float, Boolean
from sqlalchemy.orm import relationship, backref
from vulcanus.database import Base


class Command(Base):
    """
    Command table
    """
    
    __tablename__ = "command"

    command_id = Column(String(36), primary_key=True)
    command_name = Column(String(128), unique=True)
    lang = Column(String(64))
    content = Column(Text)
    create_time = Column(DateTime, nullable=True)
    timeout = Column(Integer)
    execution_user = Column(String(128))

class Script(Base):
    """
    Script table
    """
    
    __tablename__ = "script"
    script_id = Column(String(36), primary_key=True)
    script_name = Column(String(128), unique=True)
    command = Column(Text)
    create_time = Column(DateTime, nullable=True)
    timeout = Column(Integer)
    execution_user = Column(String(128))
    arch = Column(String(128))
    os_name = Column(String(128))

class Operate(Base):
    __tablename__ = "operate"
    operate_id = Column(String(36), primary_key=True)
    operate_name = Column(String(128), unique=True)
    create_time = Column(DateTime, nullable=True)


class Task(Base):
    """
    Task table
    """

    __tablename__ = "operation_task"
    task_id = Column(String(36), primary_key=True)
    status = Column(String(64))
    progress = Column(Float, nullable=True, default=0.0)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    task_detail = Column(Text)
    task_total = Column(Integer)
    task_name = Column(String(255))
    task_type = Column(String(64))

    only_push = Column(Boolean)
    # asset被删除且[task引用为空]时,删除该巡检项（行）

class OperateScript(Base):
    __tablename__ = "operate_script_association"
    operate_id = Column(String(36), primary_key=True)
    script_id = Column(String(36), primary_key=True)

class TaskOperate(Base):
    __tablename__ = "operation_task_operate_association"
    task_id = Column(String(36), primary_key=True)
    operate_id = Column(String(36), primary_key=True)

class TaskCommand(Base):
    __tablename__ = "operation_task_command_association"
    task_id = Column(String(36), primary_key=True)
    command_id = Column(String(36),primary_key=True)

class TaskHost(Base):
    __tablename__ = "operation_task_host_association"
    task_id = Column(String(36), primary_key=True)
    host_id = Column(String(36), primary_key=True)
