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
import threading
from flask_socketio import SocketIO
from vulcanus.log.log import LOGGER
from zeus.host_manager.ssh import InteroperableSSH


class XtermRoom:
    """
    This class represents a collection of Xterm rooms.
    Each room is a unique SSH connection.
    """

    # The rooms dictionary stores all the active rooms.
    # Note: This implementation is only suitable for a single-process server.
    # If you need to deploy a multi-process server, consider using a database,
    # middleware, or a separate service to manage the rooms.
    rooms = {}

    def __init__(self, sio: SocketIO) -> None:
        """
        Initialize the XtermRooms instance.

        sio: The SocketIO instance used for communication.
        """
        self.sio = sio
        self.stop_event = threading.Event()

    def has(self, room_id: str) -> bool:
        """
        Check if a room with the given ID exists and is active.

        room_id: The ID of the room to check.

        Returns: True if the room exists and is active, False otherwise.
        """

        room_info = self.rooms.get(room_id)

        if (
            not room_info
            or not room_info["socket"].is_active
            or room_info["conns"] < 1
            or not room_info["thread"].is_alive()
        ):
            self._del(room_id)
            return False

        return True

    def send(self, room_id: str, data: str) -> bool:
        """
        Sends data to the room with the given ID.

        room_id: The ID of the room to send data to.
        data: The data to send.

        Returns: True if the operation is successful, False otherwise.
        """

        if not self.rooms.get(room_id):
            return False

        self.rooms[room_id]["socket"].send(data)
        return True

    def join(self, room_id: str, namespace: str = None, room_sock=None) -> bool:
        """
        Join a room with the given ID. If the room does not exist,
        create it.

        room_id: The ID of the room to join.
        room_sock: The socket of the room to join.
            If None, a new socket will be created.

        Returns: True if the operation is successful, False otherwise.
        """
        if not self.rooms.get(room_id):
            return self._add(room_id, namespace, room_sock)

        self.rooms[room_id]["conns"] += 1
        self.rooms[room_id]["socket"].send("")
        return True

    def leave(self, room_id: str) -> bool:
        """
        Leave a room with the given ID. If the room is empty after leaving,
        delete it.

        room_id: The ID of the room to leave.

        Returns: True if the operation is successful, False otherwise.
        """
        if not self.rooms.get(room_id) or self.rooms[room_id]["conns"] < 1:
            return False

        self.rooms[room_id]["conns"] -= 1
        if self.rooms[room_id]["conns"] == 0:
            return self._del(room_id)

        return True

    def resize(self, room_id: str, cols: int, rows: int) -> bool:
        """
        Resizes the terminal size of the room with the given ID.

        room_id: The ID of the room to resize.
        cols: The number of columns for the terminal.
        rows: The number of rows for the terminal.

        Returns: True if the operation is successful, False otherwise.
        """
        if not self.rooms.get(room_id):
            return False

        self.rooms[room_id]["socket"].resize(cols, rows)
        return True

    def _add(self, room_id: str, namespace: str, room_sock=None) -> bool:
        """
        Add a new room with the given ID and socket.

        room_id: The ID of the room to add.
        namespace: The namespace of the room to add.
        room_sock: The socket of the room to add.

        Returns: True if the operation is successful, False otherwise.
        """

        if self.rooms.get(room_id):
            return False

        if not isinstance(room_sock, InteroperableSSH) or not room_sock.is_active:
            return False

        self.rooms[room_id] = {
            "socket": room_sock,
            "conns": 1,
            "thread": threading.Thread(target=self._bg_recv, args=(room_id, namespace)),
        }

        self.rooms[room_id]["thread"].start()

        return True

    def _del(self, room_id: str) -> bool:
        """
        Delete a room with the given ID.

        room_id: The ID of the room to delete.

        Returns: True if the operation is successful, False otherwise.
        """
        room_info = self.rooms.get(room_id)
        if not room_info:
            return False

        try:
            if room_info["socket"].is_active:
                room_info["socket"].close()
        except Exception as error:
            LOGGER.error("Error while closing socket: %s", error)
        # self.stop_event.set()  # Set the event to signal thread termination
        # self.rooms[room_id]["thread"].join()  # Wait for the thread to finish
        self.rooms.pop(room_id)
        return True

    def _bg_recv(self, room_id: str, namespace: str):
        """
        Continuously receive data from the room's socket in the background and
        emit it to the room.

        room_id: The ID of the room to receive data from.
        """
        while True:
            if len(self.rooms) == 0:
                break
            is_active = self.rooms[room_id]["socket"].is_active

            if not is_active:
                break
            self.sio.emit(
                "message",
                self.rooms[room_id]["socket"].recv(),
                namespace=namespace,
                to=room_id,  # Emit the received data to the room
            )
