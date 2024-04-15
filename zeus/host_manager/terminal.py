#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2022-2022. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
import sqlalchemy
from flask import request
from flask_socketio import SocketIO, Namespace, join_room, leave_room
from vulcanus.log.log import LOGGER
from vulcanus.exceptions import DatabaseConnectionFailed
from zeus.database.proxy.host import HostProxy
from zeus.host_manager.utils.sockets import XtermRoom
from zeus.database.table import Host
from zeus.host_manager.ssh import InteroperableSSH


socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode="gevent",
)

# init singleton xterm rooms in global properties
# to avoid duplicated initializing in different sessions.
socket_room = XtermRoom(sio=socketio)


class TerminalNamspace(Namespace):
    def on_open(self, event: dict):
        """
        Handle Terminal open event

        Args
            event:
                ssh_info:
                    type: object
                    example: {
                       host_id(int): 12
                    }
                room:
                    type: string
                    example: abc

        Returns: None
        """
        room_id = event.get("room")
        ssh_info = event.get("ssh_info")

        if not room_id or not ssh_info:
            self._handle_error(
                "lack of room or ssh information, \
                fail to establish ssh connection"
            )

        host_info = self._get_host_info(ssh_info.get('host_id'))

        try:
            joined = socket_room.join(
                room_id=room_id,
                namespace=self.namespace,
                room_sock=InteroperableSSH(
                    ip=host_info.get('host_ip', '0.0.0.0'),
                    port=host_info.get('ssh_port', 22),
                    username=host_info.get('ssh_user', 'root'),
                    pkey=host_info.get('pkey'),
                ),
            )
            if not joined:
                raise RuntimeError(f"could not create socket_room[{room_id}]")
            join_room(room=room_id)
        except Exception as error:
            LOGGER.error(error)
            socket_room.leave(room_id)
            leave_room(room_id)

    def on_join(self, event: dict):
        """
        Handle join event

        Args:
            event:
                room:
                    type: string
                    example: abc

        Returns: None
        """
        room = event.get("room")
        if not room:
            LOGGER.error("lack of room token, fail to join in.")

        try:
            socket_room.join(room)
            join_room(room)

        except Exception as error:
            LOGGER.error(error)
            socket_room.leave(room)
            leave_room(room)

    def on_stdin(self, event: dict):
        """
        Handle stdin event

        Args:
            event:
                room:
                    type: string
                    .e.g: abc
                data:
                    type: string
                    .e.g: 'ls -a'
        Returns: None
        """
        room = event.get("room")
        data = event.get("data")
        if not room or not data:
            return

        if not socket_room.has(room):
            self._handle_error(f"socket_room['{room}'] does not exist")
            leave_room(room=room)

        sent = socket_room.send(room_id=room, data=data)
        if not sent:
            self._handle_error(
                f"socket_room['{room}'] does not exist, \
                    could not send data to it."
            )

    def on_leave(self, event: dict):
        """
        Handle leave room event

        Args:
            event:
                room:
                    type: string
                    .e.g: abc

        Returns: None
        """
        room = event.get("room")
        if not room or not socket_room.has(room):
            return

        socket_room.leave(room_id=room)
        leave_room(room)

    def on_resize(self, event: dict):
        """
        Handle resize event

        Args:
            event:
                room:
                    type: string
                    .e.g: abc
                data:
                    type: dict
                        cols:
                            type: number
                            .e.g: 30
                        cows:
                            type: number
                            .e.g: 30

        Returns: None
        """
        room = event.get("room")
        data = event.get("data")
        if not room or not data:
            return

        if not socket_room.has(room):
            self._handle_error(f"socket_room[{room}] does not exist")
            leave_room(room)

        resized = socket_room.resize(room, data.get("cols"), data.get("rows"))
        if not resized:
            self._handle_error(
                f"socket_room[{room}] does not exist,\
                  could not send data to it."
            )

    def _get_host_info(self, host_id: int):
        """
        select host_ip, ssh_port, ssh_user, pkey from host table by host id

        Args:
            host_id: int e.g. 3

        Returns: host_info
            dict: e.g.
                {
                    "host_ip": "127.0.0.1",
                    "ssh_port": 22,
                    "ssh_user": "root",
                    "pkey": "xxxxxxxxxxxxxxxx"
                }
        """
        query_fields = [
            Host.host_ip,
            Host.ssh_port,
            Host.pkey,
            Host.ssh_user,
        ]
        host_info = {}

        try:
            with HostProxy() as db_proxy:
                host: Host = db_proxy.session.query(*query_fields).filter(Host.host_id == host_id).first()
                host_info = {
                    "host_ip": host.host_ip,
                    "ssh_port": host.ssh_port,
                    "pkey": host.pkey,
                    "ssh_user": host.ssh_user,
                }
                LOGGER.debug("query host info %s succeed", host_info)
                return host_info
        except DatabaseConnectionFailed as connect_error:
            LOGGER.error('connect database failed, %s', connect_error)
            return host_info
        except sqlalchemy.exc.SQLAlchemyError as query_error:
            LOGGER.error("query host info failed %s", query_error)
            return host_info

    def _handle_error(self, err: str):
        """
        unified handling of exceptions
        """
        LOGGER.error(
            "session[ %s ] connects testbox terminal, failed: { %s }",
            request.sid,
            str(err),
        )
        socketio.emit(
            "error",
            f"connect failed: {str(err)}",
            namespace=self.namespace,
        )


socketio.on_namespace(TerminalNamspace("/terminal"))
