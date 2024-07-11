#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
import ipaddress

import click
from kazoo.client import KazooClient
from kazoo.exceptions import KazooException

ROOT_CONFIG_PATH = "/config"


def is_valid_port(port: int) -> bool:
    """Check if the port number is valid.

    Args:
        port (int): The port number to check.

    Returns:
        bool: True if the port number is valid, False otherwise.
    """
    if not isinstance(port, int):
        return False

    if not (0 <= port <= 65535):
        return False

    return True


def is_valid_host(ip: str) -> bool:
    """Check if the IP address is valid.

    Args:
        ip (str): The IP address to check.

    Returns:
        bool: True if the IP address is valid, False otherwise.
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def set_zookeeper_config_node(zookeeper_client: KazooClient, node: str, data: bytes):
    """Set the ZooKeeper configuration node information.

    Args:
        zookeeper_client (KazooClient): The Kazoo client instance.
        node (str): The path of the node to set.
        data (bytes): The data to set for the node.
    """
    if zookeeper_client.exists(node):
        zookeeper_client.set(node, data)
    else:
        zookeeper_client.create(node, data, makepath=True)


def read_config_data(file_name: str):
    """Read data from the configuration file.

    Args:
        file_name (str): The path to the configuration file.

    Returns:
        bytes: The data read from the file
    """
    try:
        with open(file_name, "rb") as file:
            data = file.read()
        return data
    except OSError as error:
        click.echo(error, err=True)
        return None


@click.command("config", help="zookeeper configuration center management script")
@click.option("-i", "--init", help="init configuration", default=False, is_flag=True, flag_value=True)
@click.option("-u", "--update", help="update configuration node data", flag_value=True, is_flag=True, default=False)
@click.option("--host", help="zookeeper host address, such as 127.0.0.1", required=True)
@click.option("--port", help="zookeeper port, default 2181", default=2181, type=int)
@click.option("--node", help="zookeeper node path, default global_config", default="global_config")
@click.option(
    "--file", help="config file path which needs to sync", default="/etc/aops/aops-config", type=click.Path()
)
def config(init, host, port, update, node, file):
    """ZooKeeper configuration center management script.

    Args:
        init (bool): Flag indicating whether to initialize the configuration.
        host (str): The ZooKeeper host address.
        port (int): The ZooKeeper port number.
        update (bool): Flag indicating whether to update the configuration node data.
        node (str): The ZooKeeper node path.
        file (str): The path to the config file that needs to be synchronized.
    """
    if not (init or update):
        click.echo("No action specified. Use --init or --update.", err=True)
        exit(1)

    if init and update:
        click.echo("Cannot use --init and --update together.", err=True)
        exit(1)

    if not is_valid_host(host):
        click.echo("The host information is not a valid ip address.", err=True)
        exit(1)

    if not is_valid_port(port):
        click.echo("The port information is not a valid port.", err=True)
        exit(1)

    data = read_config_data(file)
    if not data:
        click.echo("Failed to load config file!", err=True)
        exit(1)

    zk = KazooClient(hosts=f"{host}:{port}")
    node_path = f"{ROOT_CONFIG_PATH}/{node}"
    try:
        zk.start()
        set_zookeeper_config_node(zk, node_path, data)
    except KazooException:
        click.echo(
            f"Failed to set data in a configuration node in zookeeper. address:{host}:{port}, node path: {node_path}.",
            err=True,
        )
        exit(1)
    finally:
        zk.stop()


__all__ = ("config",)
