# aops-zeus

### 介绍
智能运维平台aops的基础服务，提供基本主机管理与用户管理功能，负责与其他服务模块的交互。

### 环境需求
+ Python 3.9.9+
+ MySql 8.0
+ Redis


### 安装教程

1. 克隆此仓库与开发工具包，**以openeuler22.03-LTS-SP1为例**

   ```shell
   git clone https://gitee.com/openeuler/aops-zeus.git
   git clone https://gitee.com/openeuler/aops-vulcanus.git
   ```

2. 进入项目目录

   ```shell
   cd aops-zeus
   ```

3. 安装项目运行所需依赖库

   通过`dnf install <dependency-name>`安装下述依赖包。

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

4. 服务配置

   安装mysql与redis，并在mysql中建立aops数据库。

   ```sql
   create database aops default character set utf8mb4 collate utf8mb4_bin;
   ```

   安装完成后按照下述流程进行mysql与redis的配置。

   (1) 创建配置文件目录

   ```
   mkdir -p /etc/aops
   ```

   (2) 复制配置文件至该目录下

   ```
   cp -r conf/* /etc/aops/
   ```

   (3) 修改相关配置信息

   ```
   vim /etc/aops/zeus.ini
   ```

   ```ini
   [zeus]
   # zeus服务启动IP与端口配置
   ip=127.0.0.1
   port=11111
   
   [uwsgi]
   wsgi-file=manage.py
   daemonize=/var/log/aops/uwsgi/zeus.log
   http-timeout=600
   harakiri=600
   processes=2
   # aops-zeus服务中采用gevent模块，通过uwsgi启动时，需要设置gevent并发数。
   gevent=100
   
   [mysql]
   # 数据库IP与端口配置
   ip=127.0.0.1
   port=3306
   database_name=aops
   # 默认数据库无密码链接
   # 如mysql配置密码，以用户名root，密码为123456为例，则链接应为mysql+pymysql://root:123456@%s:%s/%s
   engine_format=mysql+pymysql://@%s:%s/%s
   pool_size=100
   pool_recycle=7200
   
   [prometheus]
   # 主机界面指标统计图例依赖prometheus实现，如有需求，请自行安装在此处配置。
   ip=127.0.0.1
   port=9090
   query_range_step=15s
   
   [agent]
   default_instance_port=8888
   
   [redis]
   ip=127.0.0.1
   port=6379
   ```

5. 将项目目录添加至环境变量，以/work/aops-zeus、/work/aops-vulcanus为例

   ```
   export PYTHONPATH=$PYTHONPATH:/work/aops-zeus
   export PYTHONPATH=$PYTHONPATH:/work/aops-vulcanus
   ```

6. 启动开发服务器

   ```
   python3 manage.py
   ```

   现在可访问`http://127.0.0.1:11111`访问项目

### 使用说明

1. [api接口文档](https://gitee.com/openeuler/aops-zeus/blob/master/doc/design/aops-zeus%E6%8E%A5%E5%8F%A3%E6%96%87%E6%A1%A3.yaml)
2. 使用手册可参考[aops使用手册](https://gitee.com/openeuler/docs/blob/stable2-22.03_LTS_SP2/docs/zh/docs/A-Ops/AOps%E6%99%BA%E8%83%BD%E5%AE%9A%E4%BD%8D%E6%A1%86%E6%9E%B6%E4%BD%BF%E7%94%A8%E6%89%8B%E5%86%8C.md)资产管理部分

### 参与贡献

1.  Fork 本仓库
2.  新建 Feat_xxx 分支
3.  提交代码
4.  新建 Pull Request