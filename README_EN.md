English | [简体中文](./README.md)

# aops-zeus

## Overview

Core service of the A-Ops platform, providing host and user management while orchestrating interactions between service modules

## Environment Requirements

+ Python 3.9.9 or later
+ MySQL 8.0
+ Redis

## Installation

1. Clone this repository and development kits. openEuler 22.03 LTS SP1 is used as an example.

   ```shell
   git clone https://atomgit.com/openeuler/aops-zeus.git
   git clone https://atomgit.com/openeuler/aops-vulcanus.git
   ```

2. Go to the project directory.

   ```shell
   cd aops-zeus
   ```

3. Install project dependencies.

   Run `dnf install <dependency-name>` to install the following dependencies:

   ```shell
   python3-PyMySQL
   python3-concurrent-log-handler
   python3-elasticsearch >= 7    
   python3-flask
   python3-flask-restful
   python3-gevent
   python3-jwt
   python3-kafka-python
   python3-marshmallow >= 3.13.0
   python3-paramiko >= 2.11.0
   python3-prettytable
   python3-prometheus-api-client
   python3-pygments
   python3-pyyaml
   python3-redis
   python3-requests
   python3-sqlalchemy
   python3-uWSGI
   python3-urllib3
   python3-werkzeug
   python3-xlrd
   python3-xmltodict
   ```

4. Configure the service.

   Install MySQL and Redis, and create the `aops` database in MySQL.

   ```sql
   create database aops default character set utf8mb4 collate utf8mb4_bin;
   ```

   After the installation is complete, configure MySQL and Redis as follows:

   (1) Create a configuration file directory.

   ```shell
   mkdir -p /etc/aops
   ```

   (2) Copy configuration files to the directory.

   ```shell
   cp -r conf/* /etc/aops/
   ```

   (3) Update configuration settings.

   ```shell
   vim /etc/aops/zeus.ini
   ```

   ```ini
   [zeus]
   # Configure the IP address and port for starting the zeus service.
   ip=127.0.0.1
   port=11111
   
   [uwsgi]
   wsgi-file=manage.py
   daemonize=/var/log/aops/uwsgi/zeus.log
   http-timeout=600
   harakiri=600
   processes=2
   # The aops-zeus service uses the gevent module. When starting the service via uWSGI, configure the number of concurrent gevent processes.
   gevent=100
   
   [mysql]
   # Configure the database IP address and port.
   ip=127.0.0.1
   port=3306
   database_name=aops
   # The default database connection does not require authentication.
   # If a password is configured for MySQL, for example, the user name is root and the password is 123456, the connection string is mysql+pymysql://root:123456@%s:%s/%s.
   engine_format=mysql+pymysql://@%s:%s/%s
   pool_size=100
   pool_recycle=7200
   
   [prometheus]
   # The metric visualization on the host page depends on Prometheus. If necessary, install Prometheus and configure it here.
   ip=127.0.0.1
   port=9090
   query_range_step=15s
   
   [agent]
   default_instance_port=8888
   
   [redis]
   ip=127.0.0.1
   port=6379
   ```

5. Go to the `aops-vulcanus` directory, for example, `/work/aops-vulcanus`. Copy configuration files to the `/etc/aops` directory.

   ```shell
   cd /work/aops-vulcanus/ 
   cp conf/.aops-private-config.ini /etc/aops/
   cp conf/system.ini /etc/aops/
   ```

6. Add the project directories to the environment variables. For example, add `/work/aops-zeus` and `/work/aops-vulcanus`.

   ```shell
   export PYTHONPATH=$PYTHONPATH:/work/aops-zeus
   export PYTHONPATH=$PYTHONPATH:/work/aops-vulcanus
   ```

7. Start the development server.

   ```shell
   python3 manage.py
   ```

   Access the project at `http://127.0.0.1:11111`.

## Instructions

1. [API Reference](https://gitcode.com/openeuler/aops-zeus/blob/master/docs/design/aops-zeus%E6%8E%A5%E5%8F%A3%E6%96%87%E6%A1%A3.yaml)
2. For details, see the [A-Ops Asset Management User Guide](https://gitcode.com/openeuler/aops-zeus/blob/master/docs/en/24.03_lts_sp2/aops_asset_management_user_manual.md).

## Contribution

1. Fork this repository.
2. Create a Feat_*xxx* branch.
3. Commit code.
4. Create a pull request (PR).
