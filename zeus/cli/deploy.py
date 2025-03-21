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
import random
import subprocess
import sys

import click
import pymysql
import yaml
from pymysql.constants import CLIENT

from zeus.cli.settings import AOPS_GOLBAL_CONFIG, MICROSERVICE_CONFIG_DIR, ConfigHandle

MYSQL = "mysql-server"
# base environment dependency package
ENV_RPMS = ["elasticsearch", MYSQL, "redis", "zookeeper", "nginx"]
# microservice rpms
MICROSERVICES_RPMS = [
    "zeus-host-information",
    "aops-apollo",
    "zeus-user-access",
    "zeus-distribute",
    "async-task",
    "aops-hermes",
    "authhub",
    "authhub-web",
]
# method mapping for shell scripts
SHELL_FUNC = {
    "elasticsearch": "install_elasticsearch",
    MYSQL: "install_mysql",
    "redis": "install_redis",
    "zookeeper": "install_zookeeper",
    "nginx": "install_nginx",
    "service": "install_microservice",
}
ELASTICSEARCH_CONFIG = "/etc/elasticsearch/elasticsearch.yml"
MYSQL_CONFIG = "/etc/my.cnf"
MYSQL_CONFIG_CONTENT = """
[mysqld]
log-bin=mysql-bin
server-id={server_id}
bind-address=0.0.0.0
default-storage-engine=INNODB
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
"""
REDIS_CONFIG = "/etc/redis.conf"
NGINX_CONFIG = "/etc/nginx/nginx.conf"
# placeholder for the upstream block of the nginx configuration file
NGINX_PROXY_SERVER_CONFIG = {
    "zeus-host-information": {
        "type": "dynamic",
        "upstream": "host",
        "location": "/hosts",
        "proxy_pass": "http://host;",
    },
    "aops-apollo": {
        "type": "dynamic",
        "upstream": "apollo",
        "location": "/vulnerabilities",
        "proxy_pass": "http://apollo;",
    },
    "zeus-user-access": {
        "type": "dynamic",
        "upstream": "accounts",
        "location": "/accounts",
        "proxy_pass": "http://accounts;",
    },
    "zeus-distribute": {
        "type": "dynamic",
        "upstream": "distribute",
        "location": "/distribute",
        "proxy_pass": "http://distribute;",
        "rewrite": "^/distribute(.*)$ /distribute break;",
    },
    "authhub": {
        "type": "dynamic",
        "upstream": "oauth2server",
        "location": "/oauth2",
        "proxy_pass": "http://oauth2server;",
    },
    "aops-hermes": {"type": "static", "dir": "root /opt/aops/web/dist;", "location": "/"},
    "authhub-web": {"type": "static", "dir": "alias /opt/authhub/web/dist;", "location": "/authhub"},
}
NGINX_HTTP_SERVER = """
location %s {
      %s
      proxy_pass %s
      proxy_set_header Host $host;
      proxy_set_header X-Real-URL $request_uri;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header Request-Header $http_request_header;
}
"""

NGINX_HTTP_UPSTREAM = """
upstream %s { 
server %s;
}
"""


NGINX_HTTP_SERVER_STATIC = """
location %s {
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods 'GET, POST, DELETE, PUT, OPTIONS';
        %s
        index index.html;
        try_files $uri $uri/ /index.html last;
    }
"""

NGINX_CONFIG_TEMPLATE = """
user root;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /var/run/nginx.pid;
# Load dynamic modules. See /usr/share/doc/nginx/README.dynamic.
include /usr/share/nginx/modules/*.conf;
events {
    worker_connections 1024;
}
http {
  log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';
    access_log  /var/log/nginx/access.log  main;
    sendfile            on;
    tcp_nopush          on;
    tcp_nodelay         on;
    keepalive_timeout   65;
    types_hash_max_size 2048;
    include             /etc/nginx/mime.types;
    default_type        application/octet-stream;
    client_max_body_size 25M;
    include /etc/nginx/conf.d/*.conf;
    %s
    underscores_in_headers on;
    server {
    listen       80;
    listen       [::]:80 default_server;
    server_name  localhost;
    gzip on;
    gzip_min_length 1k;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/javascript application/json application/javascript application/x-javascript application/xml;
    gzip_vary on;
    gzip_disable "MSIE [1-6]\.";
    %s
    %s
  }
}
"""


class SetConfig:
    def __init__(self, ip, service):
        self.ip = ip
        self._service = service

    def elasticsearch(self):
        if not os.path.exists(ELASTICSEARCH_CONFIG):
            click.echo(f"{ELASTICSEARCH_CONFIG} not exists")
            sys.exit(-1)

        click.echo("[INFO] Start doing to set elasticsearch config")
        try:
            with open(ELASTICSEARCH_CONFIG, "r") as file:
                config = yaml.safe_load(file.read())
                if not config:
                    config = dict()
                config["network.host"] = self.ip
                config["node.name"] = "node-1"
                config["http.port"] = 9200
                config["cluster.initial_master_nodes"] = ["node-1"]
            with open(ELASTICSEARCH_CONFIG, "w") as file:
                file.write(yaml.dump(config, default_flow_style=False))
            click.echo("[INFO] The elasticsearch config is set successful")
        except (IOError, yaml.YAMLError):
            click.echo("[ERROR] The elasticsearch config is set failed")
            sys.exit(-1)

    def mysql(self):
        if not os.path.exists(MYSQL_CONFIG):
            click.echo(f"{MYSQL_CONFIG} not exists")
            sys.exit(-1)
        click.echo("[INFO] Start doing to set mysql config")
        try:
            with open(MYSQL_CONFIG, "w") as file:
                config = MYSQL_CONFIG_CONTENT.format(server_id=random.randint(1, 10000))
                file.write(config)
            click.echo("[INFO] The mysql config is set successful")
        except IOError:
            click.echo("[ERROR] The mysql config is set failed")
            sys.exit(-1)

    def redis(self):
        if not os.path.exists(REDIS_CONFIG):
            click.echo(f"{REDIS_CONFIG} not exists")
            sys.exit(-1)
        click.echo("[INFO] Start doing to set redis config")
        try:
            with open(REDIS_CONFIG, "r") as file:
                config = file.read()
            if not config:
                config = ""
            with open(REDIS_CONFIG, "w") as file:
                config = config.replace("bind 127.0.0.1", f"bind {self.ip}").replace(
                    "protected-mode yes", "protected-mode no")
                file.write(config)
            click.echo("[INFO] The redis config is set successful")
        except IOError:
            click.echo("[ERROR] The redis config is set failed")
            sys.exit(-1)

    def zookeeper(self):
        pass

    def _read_service_port(self, service):
        service_config = os.path.join(MICROSERVICE_CONFIG_DIR, f"{service}.yml")
        if not os.path.exists(service_config):
            return None
        try:
            with open(service_config, "r") as file:
                config = yaml.safe_load(file.read())
                if not config:
                    return None
            return config["uwsgi"]["port"]
        except (IOError, yaml.YAMLError, KeyError):
            return None

    def nginx(self):
        click.echo("[INFO] Start doing to set nginx config")
        try:
            upstream, proxys, statics = list(), list(), list()
            for service in self._service:
                if service not in NGINX_PROXY_SERVER_CONFIG:
                    continue
                if NGINX_PROXY_SERVER_CONFIG[service]["type"] == "static":
                    statics.append(
                        NGINX_HTTP_SERVER_STATIC
                        % (NGINX_PROXY_SERVER_CONFIG[service]['location'], NGINX_PROXY_SERVER_CONFIG[service]['dir'])
                    )
                    continue
                port = self._read_service_port(service)
                if not port:
                    click.echo(f"[WARNING] The {service} service port is not exists, please check the config file")
                    continue

                upstream.append(
                    NGINX_HTTP_UPSTREAM % (NGINX_PROXY_SERVER_CONFIG[service]['upstream'], f"{self.ip}:{port}")
                )
                rewrite = ""
                if "rewrite" in NGINX_PROXY_SERVER_CONFIG[service]:
                    rewrite = "rewrite " + NGINX_PROXY_SERVER_CONFIG[service]["rewrite"]

                proxys.append(
                    NGINX_HTTP_SERVER
                    % (
                        NGINX_PROXY_SERVER_CONFIG[service]['location'],
                        rewrite,
                        NGINX_PROXY_SERVER_CONFIG[service]['proxy_pass'],
                    )
                )
            if any([upstream, proxys, statics]):
                nginx_config = NGINX_CONFIG_TEMPLATE % ("\n".join(upstream), "\n".join(statics), "\n".join(proxys))
                with os.fdopen(
                    os.open(NGINX_CONFIG, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644), "w", encoding="utf-8"
                ) as file:
                    file.write(nginx_config)

            click.echo("[INFO] The nginx config is set successful")
        except (IOError, RuntimeError):
            click.echo("[ERROR] The nginx config is set failed")
            sys.exit(-1)


def call_shell_scripts(func, param=None, shell=None):
    """
    call shell scripts

    Args:
        func: shell function
        param: shell function param
        shell: shell file path

    Returns: success or fail
    """
    if not shell:
        shell = os.path.join(os.path.dirname(__file__), "deploy.sh")

    if param:
        command = ["bash", "-c", f"source {shell} && {func} {param}"]
    else:
        command = ["bash", "-c", f"source {shell} && {func}"]

    status_code = subprocess.call(command)
    return False if status_code else True


def install(env, service):
    """
    install service or install base environment package

    Args:
        env: environment package
        service: microservice package
    """

    for rpm, func in SHELL_FUNC.items():
        if rpm in env:
            if not call_shell_scripts(func=func):
                click.echo(f"[ERROR] Failed to install {rpm}")
                sys.exit(-1)
        if rpm == "service":
            if not call_shell_scripts(func=func, param=" ".join(service)):
                click.echo(f"[ERROR] Failed to install {' '.join(service)}")
                sys.exit(-1)


def set_config(env, service, ip):
    """
    set service config

    Args:
        env: environment package
        service: microservice package
        ip: ip address
    """
    _set_config = SetConfig(ip=ip, service=service)
    for base_service in env:
        if base_service == MYSQL:
            base_service = "mysql"

        set_func = getattr(_set_config, base_service)
        if set_func and callable(set_func):
            set_func()

    if not service:
        return
    # Set up the microservice configuration
    if not os.path.exists(AOPS_GOLBAL_CONFIG):
        click.echo(f"[ERROR] {AOPS_GOLBAL_CONFIG} does not exist")
        sys.exit(-1)

    click.echo("[INFO] Start doing to set aops global config")
    try:
        with open(AOPS_GOLBAL_CONFIG, "r") as file:
            config = yaml.safe_load(file.read())
            if not config:
                return
        config["infrastructure"]["mysql"]["host"] = ip
        config["infrastructure"]["redis"]["host"] = ip
        config["infrastructure"]["elasticsearch"]["host"] = ip
        config["infrastructure"]["zookeeper"]["host"] = ip
        config["domain"] = ip

        with open(AOPS_GOLBAL_CONFIG, "w") as file:
            config = yaml.dump(config, file)

        click.echo("[INFO] The aops global config is set successful")
    except (IOError, yaml.YAMLError):
        click.echo("[ERROR] The aops global config is set failed")
        sys.exit(-1)


def init_serivce_database(services):
    """
    init service database

    Args:
        services: microservice package
    """
    for service in services:
        if service not in ("zeus-host-information", "aops-apollo", "zeus-user-access", "authhub"):
            continue
        call_shell_scripts(func="init_service_database", param=service)


def start_service(services):
    """
    start service

    Args:
        services: microservice package
    """
    exclude_service = []
    for service in services:
        if service in exclude_service:
            continue
        if service == MYSQL:
            service = "mysqld"
        call_shell_scripts(func="start_service", param=service)


def set_database():
    """
    set mysql database permissions and generate user
    """
    try:
        config = ConfigHandle().parser
    except RuntimeError as error:
        click.echo(error, err=True)
        sys.exit(-1)

    database = None
    try:
        connection_options = dict(host="127.0.0.1", port=config.mysql.port)
        if config.mysql.username and config.mysql.password:
            connection_options.update(user=config.mysql.username, password=config.mysql.password)
        database = pymysql.connect(
            **connection_options, database='mysql', autocommit=True, client_flag=CLIENT.MULTI_STATEMENTS
        )
        cursor = database.cursor()
        cursor.execute("update user set host = '%' where user='root';")
        cursor.execute("flush privileges;")
        cursor.execute("grant system_user on *.*  to 'root';")
        cursor.execute("flush privileges;")
        cursor.execute("DELETE FROM mysql.user WHERE user='canal';")
        cursor.execute("flush privileges;")
        cursor.execute("CREATE USER canal IDENTIFIED BY 'canal';")
        cursor.execute("flush privileges;")
        cursor.execute("GRANT ALL PRIVILEGES ON *.* TO 'canal'@'%';")
        cursor.execute("flush privileges;")
        click.echo("[INFO] Mysql database root permissions and canal user generation were successful")
    except (IOError, pymysql.err.OperationalError, pymysql.err.InternalError):
        click.echo("[ERROR] Failed to root mysql database and generate canal user")
        sys.exit(-1)
    finally:
        if database:
            database.close()


@click.command("deploy", help="deploy microservices in one click")
@click.option("--ip", help="service ip")
@click.option('--env', multiple=True, type=str, help='env rpms', default=ENV_RPMS)
@click.option('--exclude-env', multiple=True, type=str, help="It doesn't need to be installed env rpms")
@click.option('--service', multiple=True, type=str, help='installed microservices', default=MICROSERVICES_RPMS)
@click.option('--exclude-service', multiple=True, type=str, help="It doesn't need to be installed microservices")
@click.option("-a", "--all-install", help="Install full service", default=False, is_flag=True, flag_value=True)
def deploy(ip, env, exclude_env, service, exclude_service, all_install):
    """
    deploy microservices in one click
    """
    install_env = env
    install_service = service
    if not all_install:
        install_env = set(env) - set(exclude_env)
        install_service = set(service) - set(exclude_service)
    install(install_env, install_service)
    set_config(install_env, install_service, ip)
    start_service(list(install_env))
    # set database
    if MYSQL in install_env:
        set_database()
    if install_service:
        init_serivce_database(install_service)

    start_service(list(install_service))


__all__ = ("deploy",)
