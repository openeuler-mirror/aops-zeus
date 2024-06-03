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
import time
import sys
import click
from zeus.cli.settings import ConfigHandle


WSGI_FOLDER = "/opt/aops/uwsgi"
MODULES = {
    "zeus-host-information": "zeus.host_information_service",
    "zeus-user-access": "zeus.user_access_service",
    "zeus-distribute": "zeus.distribute_service",
}


def stop_service(service_name):
    pidfile = os.path.join(WSGI_FOLDER, service_name + ".pid")
    if not os.path.exists(pidfile):
        click.echo(f"[ERROR] {service_name} service is not running")
        sys.exit(0)

    os.system(f"uwsgi --stop {pidfile}")
    os.remove(pidfile)
    click.echo(f"[INFO] Stop {service_name} service is successful")


def start_service(service_name):
    pid = os.path.join(WSGI_FOLDER, service_name + ".pid")
    if os.path.exists(pid):
        os.remove(pid)

    ini = os.path.join(WSGI_FOLDER, service_name + ".ini")
    if not os.path.exists(ini):
        click.echo(f"[ERROR] {service_name} service config file does not exists")
        sys.exit(0)

    os.system(f"uwsgi --ini {ini} --enable-threads")
    time.sleep(3)
    if not os.path.exists(pid):
        click.echo(f"[ERROR] {service_name} service start failed")
        sys.exit(0)

    click.echo(f"[INFO] Start {service_name} service is successful")


def create_uwsgi_config(service_name: str, config):

    if not os.path.exists(WSGI_FOLDER):
        os.makedirs(WSGI_FOLDER)
    if service_name in MODULES:
        main, service = MODULES[service_name].split(".")
        chdir = os.path.join(sys.path[-1], main, service)
        module = MODULES[service_name] + ".manage"
    else:
        service = service_name
        if service_name.startswith("aops-"):
            service = service_name[5:]
        chdir = os.path.join(sys.path[-1], service)
        module = service + ".manage"

    pidfile = os.path.join(WSGI_FOLDER, service_name + ".pid")
    ini = os.path.join(WSGI_FOLDER, service_name + ".ini")
    if config.daemonize and not os.path.exists(config.daemonize):
        os.makedirs(os.path.dirname(config.daemonize), exist_ok=True)
        open(config.daemonize, "w").close()

    with open(ini, "w") as file:
        uwsgi_file = f"""
[uwsgi]
http=:{config.port}
chdir={chdir}
module={module}
pidfile={pidfile}
callable=app
http-timeout={config.http_timeout}
harakiri={config.harakiri}
processes={config.processes}
daemonize={config.daemonize}
"""
        if config.gevent:
            uwsgi_file += f"""
gevent={config.gevent}
gevent-monkey-patch=true
"""
        else:
            uwsgi_file += f"""
threads={config.threads}           
"""
        file.write(uwsgi_file)
    os.chmod(ini, 0o750)
    click.echo(f"[INFO] Create {service_name} uwsgi file ok,path is {os.path.join(WSGI_FOLDER, service_name + '.ini')}")


@click.command("service", help="")
@click.option("-name", help="service name", required=True)
@click.option("-stop", help="stop service", default=False, is_flag=True, flag_value=True)
def service(name, stop):
    """
    service start or stop

    :param name: service name
    :param stop: stop or start service
    """
    try:
        config = ConfigHandle(name).parser

    except RuntimeError as error:
        click.echo(error, err=True)
        sys.exit(0)

    if stop:
        stop_service(name)
        sys.exit(0)

    create_uwsgi_config(name, config.uwsgi)
    start_service(name)


__all__ = ("service",)
