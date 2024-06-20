#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2021. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
import os
import sys
import uuid

import click
import pymysql
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pymysql.constants import CLIENT

from zeus.cli.settings import ConfigHandle

ADMINISTRATOR_USER = "admin"


def database_cursor(config, database="mysql"):
    mysql_client = None
    try:
        connection_options = dict(host=config.host, port=config.port)
        if config.username and config.password:
            connection_options.update(user=config.username, password=config.password)
        mysql_client = pymysql.connect(
            **connection_options, database=database, autocommit=True, client_flag=CLIENT.MULTI_STATEMENTS
        )
    except pymysql.err.OperationalError:
        click.echo(f"[ERROR] Database {database} connect failed")
    return mysql_client


def init_database(sql_file, config):
    database = database_cursor(config=config)
    if not database:
        sys.exit(0)
    try:
        with open(sql_file, 'r', encoding='utf-8') as file:
            sql = file.read()
        if not sql:
            click.echo(f"[ERROR] Sql file is empty: {sql_file}")
            sys.exit(0)
        cursor = database.cursor()
        cursor.execute(sql)
        click.echo(f"[INFO] Sql {sql_file} initialization was successful")
    except (IOError, pymysql.err.OperationalError):
        click.echo(f"[ERROR] Sql file {sql_file} initialization failed")
    finally:
        database.close()


def generate_rsa_key():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    public_key = private_key.public_key()
    private_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode('utf-8')
    public_key = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    return private_key, public_key


def fix_cluster_data(cluster_ip, config):
    database = database_cursor(config=config, database=config.database)
    if not database:
        sys.exit(0)
    try:
        private_key, public_key = generate_rsa_key()
        cluster_id = str(uuid.uuid4())
        cursor = database.cursor()
        show_tables_sql = "show tables;"
        cursor.execute(show_tables_sql)
        if "user_cluster_association" in [table[0] for table in cursor.fetchall()]:
            user_cluster_association_sql = f"select cluster_id from user_cluster_association where username='{ADMINISTRATOR_USER}' and cluster_username='{ADMINISTRATOR_USER}';"
            cursor.execute(user_cluster_association_sql)
            user_cluster_association = cursor.fetchone()
            if user_cluster_association:
                cluster_id = user_cluster_association[0]

        sql = f"""INSERT INTO cluster(cluster_id, cluster_name, subcluster, private_key, public_key, backend_ip, synchronous_state) 
            SELECT '{cluster_id}' ,"local-cluster" , 0, '{private_key}', '{public_key}', '{cluster_ip}', ""
            FROM DUAL
            WHERE NOT EXISTS(SELECT 1 FROM cluster WHERE subcluster = 0);
        """

        cursor.execute(sql)
        click.echo("[INFO] Table cluster data fix successful")
    except pymysql.err.OperationalError:
        click.echo("[ERROR] Table cluster data fix failed")
    finally:
        database.close()


def fix_user_cluster_association_data(config):
    database = database_cursor(config=config, database=config.database)
    if not database:
        sys.exit(0)
    try:
        cursor = database.cursor()
        cluster_id = str(uuid.uuid4())
        show_tables_sql = "show tables;"
        cursor.execute(show_tables_sql)
        if "cluster" in [table[0] for table in cursor.fetchall()]:
            cluster_sql = "select cluster_id from cluster where subcluster = 0;"
            cursor.execute(cluster_sql)
            cluster = cursor.fetchone()
            if cluster:
                cluster_id = cluster[0]
        sql = f"""INSERT INTO user_cluster_association (id, username, cluster_id, cluster_username, private_key)
            SELECT '{str(uuid.uuid4())}' , '{ADMINISTRATOR_USER}' , '{cluster_id}' ,'{ADMINISTRATOR_USER}' , ""
            FROM DUAL
            WHERE NOT EXISTS(SELECT 1 FROM user_cluster_association WHERE username = '{ADMINISTRATOR_USER}');
        """
        cursor.execute(sql)
        click.echo("[INFO] Table user_cluster_association data fix successful")
    except pymysql.err.OperationalError:
        click.echo("[ERROR] Table user_cluster_association data fix failed")
    finally:
        database.close()


@click.command("database", help="database initialization")
@click.option("--init", help="init database name", required=True)
@click.option("--sql", help="init database sql file")
def database(init, sql):
    """
    init database
    """
    if not sql:
        sql = os.path.join("/opt/aops/database", init + ".sql")
    if not os.path.exists(sql):
        click.echo(f"[ERROR] Sql file does not exist, please check: {sql}")
        sys.exit(0)
    try:
        config = ConfigHandle(init).parser
    except RuntimeError as error:
        click.echo(error, err=True)
        sys.exit(0)

    init_database(sql_file=sql, config=config.mysql)
    if init == "zeus-host-information":
        fix_cluster_data(config.domain, config.mysql)

    if init == "zeus-user-access":
        fix_user_cluster_association_data(config.mysql)


__all__ = ("database",)
