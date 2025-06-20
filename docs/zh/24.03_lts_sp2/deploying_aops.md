# 一、A-Ops服务介绍

A-Ops是用于提升主机整体安全性的服务，通过资产管理、漏洞管理、配置溯源等功能，识别并管理主机中的信息资产，监测主机中的软件漏洞、排查主机中遇到的系统故障，使得目标主机能够更加稳定和安全的运行。

下表是A-Ops服务涉及模块的说明：

| 模块 | 说明  |
| ---------- | ---------------------------------------------------- |
| aops-ceres | A-Ops服务的客户端。<br />提供采集主机数据与管理其他数据采集器（如gala-gopher）的功能。<br />响应管理中心下发的命令，处理管理中心的需求与操作。 |
| aops-zeus  | A-Ops基础应用管理中心，主要负责与其他模块的中转站，默认端口：11111<br />对外提供基本主机管理服务，主机与主机组的添加、删除等功能依赖此模块实现。 |
| aops-hermes | A-Ops可视化操作界面，展示数据信息，提升服务易用性。 |
| aops-apollo | A-Ops漏洞管理模块相关功能依赖此服务实现，默认端口：11116<br />识别客户机周期性获取openEuler社区发布的安全公告，并更新到漏洞库中。<br />通过与漏洞库比对，检测出系统和软件存在的漏洞。 |
| aops-vulcanus | A-Ops工具库，**除aops-ceres与aops-hermes模块外，其余模块须与此模块共同安装使用**。 |
| aops-tools | 提供基础环境一键部署脚本、数据库表初始化，安装后在/opt/aops/scripts目录下可见。<br /> |
| gala-ragdoll | A-Ops配置溯源模块，通过git监测并记录配置文件的改动，默认端口：11114 |
| dnf-hotpatch-plugin | dnf插件，使得dnf工具可识别热补丁信息，提供热补丁扫描及热补丁修复功能。 |

# 二、部署环境要求

建议采用4台 openEuler 24.03-LTS 机器部署，其中3台用于配置服务端，1台用于纳管（aops服务纳管的主机），**且repo中需要配置update源**（[FAQ：配置update源](#Q6、配置update源)），具体用途以及部署方案如下：

+ 机器A：部署mysql、redis、elasticsearch等，主要提供数据服务支持，建议内存8G+。
+ 机器B：部署A-Ops的资产管理zeus服务+前端展示服务，提供完整的业务功能支持，建议内存6G+。
+ 机器C：部署A-Ops的漏洞管理配置溯源（gala-ragdoll），提供漏洞管理服务，建议内存4G+。
+ 机器D：部署A-Ops的客户端，用作一个被AOps服务纳管监控的主机（需要监管的机器中都可以安装aops-ceres）。

| 机器编号 | 配置IP      | 部署模块                              |
| -------- | ----------- | ------------------------------------- |
| 机器A    | 192.168.1.1 | mysql，elasticsearch， redis          |
| 机器B    | 192.168.1.2 | aops-zeus，aops-hermes，aops-diana    |
| 机器C    | 192.168.1.3 | aops-apollo，gala-ragdoll，aops-diana |
| 机器D    | 192.168.1.4 | aops-ceres，dnf-hotpatch-plugin       |

> 每台机器在部署前，请先**关闭防火墙和SELinux**。

- 关闭防火墙

```shell
systemctl stop firewalld
systemctl disable firewalld
systemctl status firewalld
setenforce 0

```

- 禁用SELinux

```shell
# 修改/etc/selinux/config文件中SELINUX状态为disabled

vi /etc/selinux/config
SELINUX=disabled

# 更改之后，按下ESC键，键盘中输入 :wq 保存修改的内容
```

注：此SELINUX状态配置在系统重启后生效。

# 三、服务端部署

## 3.1、 资产管理

使用资产管理功能需部署aops-zeus、aops-hermes、mysql、redis服务。

### 3.1.1、节点信息

| 机器编号 |  配置IP|部署模块|
| -------- | -------- | -------- |
| 机器A | 192.168.1.1 |mysql，redis|
| 机器B | 192.168.1.2 |aops-zeus，aops-hermes|

### 3.1.2、部署步骤

#### 3.1.2.1、 部署mysql

- 安装mysql

```shell
yum install mysql-server -y
```

- 修改mysql配置文件

```bash
vim /etc/my.cnf
```

- 在mysqld配置节下新增bind-address，值为本机ip

```ini
[mysqld]
bind-address=192.168.1.1
```

- 重启mysql服务

```bash
systemctl restart mysqld
```

- 设置mysql数据库的root用户访问权限

```mysql
[root@localhost ~] mysql

mysql> show databases;
mysql> use mysql;
mysql> select user,host from user; -- 此处出现host为localhost时，说明mysql只允许本机连接，外网和本地软件客户端则无法连接。

+---------------+-----------+
| user          | host      |
+---------------+-----------+
| root          | localhost |
| mysql.session | localhost |
| mysql.sys     | localhost |
+---------------+-----------+
3 rows in set (0.00 sec)
```

```mysql
mysql> update user set host = '%' where user='root'; -- 设置允许root用户任意IP访问。
mysql> flush privileges; -- 刷新权限
mysql> exit
```

#### 3.1.2.2、 部署redis

- 安装redis

```shell
yum install redis -y
```

- 修改配置文件

```shell
vim /etc/redis.conf
```

- 绑定IP

```ini
# It is possible to listen to just one or multiple selected interfaces using
# the "bind" configuration directive, followed by one or more IP addresses.
#
# Examples:
#
# bind 192.168.1.100 10.0.0.1
# bind 127.0.0.1 ::1
#
# ~~~ WARNING ~~~ If the computer running Redis is directly exposed to the
# internet, binding to all the interfaces is dangerous and will expose the
# instance to everybody on the internet. So by default we uncomment the
# following bind directive, that will force Redis to listen only into
# the IPv4 lookback interface address (this means Redis will be able to
# accept connections only from clients running into the same computer it
# is running).
#
# IF YOU ARE SURE YOU WANT YOUR INSTANCE TO LISTEN TO ALL THE INTERFACES
# JUST COMMENT THE FOLLOWING LINE.
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
bind 127.0.0.1 192.168.1.1 # 此处添加机器A的真实IP
```

- 启动redis服务

```shell
systemctl start redis
```

#### 3.1.2.3、 部署prometheus

- 安装prometheus

```shell
yum install prometheus2 -y
```

- 修改配置文件

```shell
vim /etc/prometheus/prometheus.yml
```

- 被纳管的客户端**gala-gopher**地址添加至prometheus监控节点

  > 本指南中机器D用于部署客户端，故添加机器D的gala-gopher地址
  >
  > 修改**targets**配置项

```yml
# A scrape configuration containing exactly one endpoint to scrape:
# Here it's Prometheus itself.
scrape_configs:
  # The job name is added as a label `job=<job_name>` to any timeseries scraped from this config.
  - job_name: 'prometheus'

    # metrics_path defaults to '/metrics'
    # scheme defaults to 'http'.

    static_configs:
    - targets: ['localhost:9090', '192.168.1.4:8888']
```

- 启动prometheus服务

```shell
systemctl start prometheus
```

#### 3.1.2.4、 部署aops-zeus

- 安装aops-zeus

```bash
yum install aops-zeus -y
```

- 修改配置文件

```bash
vim /etc/aops/zeus.ini
```

- 将配置文件中各服务的地址修改为真实地址，本指南中aops-zeus部署于机器B，故需把IP地址配为机器B的ip地址

```ini
[zeus]
ip=192.168.1.2  // 此处ip修改为机器B真实ip
port=11111

[uwsgi]
wsgi-file=manage.py
daemonize=/var/log/aops/uwsgi/zeus.log
http-timeout=600
harakiri=600
processes=2   // 生成指定数目的worker/进程
gevent=100    // gevent异步核数

[mysql]
ip=192.168.1.1  // 此处ip修改为机器A真实ip
port=3306
database_name=aops
engine_format=mysql+pymysql://@%s:%s/%s
pool_size=100
pool_recycle=7200

[agent]
default_instance_port=8888

[redis]
ip=192.168.1.1  // 此处ip修改为机器A真实ip
port=6379

[apollo]
ip=192.168.1.3  // 此处ip修改为部署apollo服务的真实ip（建议apollo与zeus分开部署）。若不使用apollo的漏洞管理功能则可以不配置
port=11116
```

> **mysql数据库设置为密码模式**，请参阅[FAQ：密码模式下mysql服务配置链接字符串](#Q5、mysql设置为密码模式)

- 启动aops-zeus服务

```shell
systemctl start aops-zeus
```

**注意：服务启动前请确保已 [初始化aops-zeus数据库](#3125-初始化aops-zeus数据库)**

> zeus服务启动失败，且报错内容包含mysql数据库连接失败，请排查是否设置mysql密码，如果是请参阅[FAQ：密码模式下mysql服务启动失败](#Q5、mysql设置为密码模式)

#### 3.1.2.5、 初始化aops-zeus数据库

- 执行数据库初始化

```shell
cd /opt/aops/scripts/deploy
bash aops-basedatabase.sh init zeus
```

**注意：在未安装aops-tools工具包时，也可获取sql脚本通过mysql加载的方式初始化（sql脚本路径：/opt/aops/database/zeus.sql）**

[FAQ：密码模式下mysql数据库初始化](#Q5、mysql设置为密码模式)

[FAQ：/opt/aops/scripts/deploy目录不存在](#Q7、/opt/aops/scripts/deploy目录不存在)

#### 3.1.2.6、 部署aops-hermes

- 安装aops-hermes

```shell
yum install aops-hermes -y
```

- 修改配置文件

```shell
vim /etc/nginx/aops-nginx.conf
```

- 服务配置展示

> 服务都部署在机器B，需将ngxin代理访问的各服务地址配置为机器B的真实ip

```ini
# 保证前端路由变动时nginx仍以index.html作为入口
location / {
    try_files $uri $uri/ /index.html;
    if (!-e $request_filename){
        rewrite ^(.*)$ /index.html last;
    }
}
# 此处修改为aops-zeus部署机器真实IP
location /api/ {
    proxy_pass http://192.168.1.2:11111/;
}
# 此处IP对应gala-ragdoll的IP地址,涉及到端口为11114的IP地址都需要进行调整
location /api/domain {
    proxy_pass http://192.168.1.3:11114/;
    rewrite ^/api/(.*) /$1 break;
}
# 此处IP对应aops-apollo的IP地址
location /api/vulnerability {
    proxy_pass http://192.168.1.3:11116/;
    rewrite ^/api/(.*) /$1 break;
}
```

- 开启aops-hermes服务

```shell
systemctl start aops-hermes
```

## 3.2、 漏洞管理

CVE管理模块在[资产管理](#31-资产管理)模块的基础上实现，在部署CVE管理模块前须完成[资产管理](#31-资产管理)模块的部署，然后再部署aops-apollo。

数据服务部分aops-apollo服务的运行需要**mysql、elasticsearch、redis**数据库的支持。

### 3.2.1、 节点信息

| 机器编号 | 配置IP      | 部署模块      |
| -------- | ----------- | ------------- |
| 机器A    | 192.168.1.1 | elasticsearch |
| 机器C    | 192.168.1.3 | aops-apollo   |

### 3.2.2、 部署步骤

[部署步骤](#312部署步骤)

#### 3.2.2.1、 部署elasticsearch

- 生成elasticsearch的repo源

```shell
echo "[aops_elasticsearch]
name=Elasticsearch repository for 7.x packages
baseurl=https://artifacts.elastic.co/packages/7.x/yum
gpgcheck=1
gpgkey=https://artifacts.elastic.co/GPG-KEY-elasticsearch
enabled=1
autorefresh=1
type=rpm-md" > "/etc/yum.repos.d/aops_elascticsearch.repo"
```

- 安装elasticsearch

```shell
yum install elasticsearch-7.14.0-1 -y
```

- 修改elasticsearch配置文件

```shell
vim /etc/elasticsearch/elasticsearch.yml
```

```yml
# ------------------------------------ Node ------------------------------------
#
# Use a descriptive name for the node:
#
node.name: node-1
```

```yml
# ---------------------------------- Network -----------------------------------
#
# By default Elasticsearch is only accessible on localhost. Set a different
# address here to expose this node on the network:
#
# 此处修改为机器A真实ip
network.host: 192.168.1.1
#
# By default Elasticsearch listens for HTTP traffic on the first free port it
# finds starting at 9200. Set a specific HTTP port here:
#
http.port: 9200
#
# For more information, consult the network module documentation.
#
```

```yml
# --------------------------------- Discovery ----------------------------------
#
# Pass an initial list of hosts to perform discovery when this node is started:
# The default list of hosts is ["127.0.0.1", "[::1]"]
#
#discovery.seed_hosts: ["host1", "host2"]
#
# Bootstrap the cluster using an initial set of master-eligible nodes:
#
cluster.initial_master_nodes: ["node-1"]
# 跨域配置
http.cors.enabled: true
http.cors.allow-origin: "*"
```

- 重启elasticsearch服务

```shell
systemctl restart elasticsearch
```

#### 3.2.2.2、 部署aops-apollo

- 安装aops-apollo

```shell
yum install aops-apollo -y
```

- 修改配置文件

```bash
vim /etc/aops/apollo.ini
```

- 将apollo.ini配置文件中各服务的地址修改为真实地址

```ini
[apollo]
ip=192.168.1.3//此处修改为机器C的真实IP
port=11116
host_vault_dir=/opt/aops
host_vars=/opt/aops/host_vars

[zeus]
ip=192.168.1.2  //此处修改为机器B的真实IP
port=11111

# hermes info is used to send mail.
[hermes]
ip=192.168.1.2  //此处修改为部署aops-hermes的真实IP,以机器B的IP地址为例
port=80   //此处改为hermes服务实际使用端口

[cve]
cve_fix_function=yum
# value between 0-23, for example, 2 means 2:00 in a day.
cve_scan_time=2

[mysql]
ip=192.168.1.1 //此处修改为机器A的真实IP
port=3306
database_name=aops
engine_format=mysql+pymysql://@%s:%s/%s
pool_size=100
pool_recycle=7200

[elasticsearch]
ip=192.168.1.1 //此处修改为机器A的真实IP
port=9200
max_es_query_num=10000000

[redis]
ip=192.168.1.1 //此处修改为机器A的真实IP
port=6379

[uwsgi]
wsgi-file=manage.py
daemonize=/var/log/aops/uwsgi/apollo.log
http-timeout=600
harakiri=600
processes=2
gevent=100

```

> **mysql数据库设置为密码模式**，请参阅[密码模式下mysql服务配置链接字符串](#Q5、mysql设置为密码模式)

- 启动aops-apollo服务

```shell
systemctl start aops-apollo
```

**注意：服务启动前请确保已 [初始化aops-apollo数据库](#3223初始化aops-apollo数据库)**

> apollo服务启动失败，且报错内容包含mysql数据库连接失败，请排查是否设置mysql密码，如果是请参阅[密码模式下mysql服务启动失败](#Q5、mysql设置为密码模式)

#### 3.2.2.3、初始化aops-apollo数据库

- apollo数据库初始化

```shell
cd /opt/aops/scripts/deploy
bash aops-basedatabase.sh init apollo
```

**注意：在未安装aops-tools工具包时，也可获取sql脚本通过mysql加载的方式初始化（sql脚本路径：/opt/aops/database/apollo.sql）**

[FAQ：密码模式下mysql数据库初始化](#Q5、mysql设置为密码模式)

[FAQ：/opt/aops/scripts/deploy目录不存在](#Q7、/opt/aops/scripts/deploy目录不存在)

## 3.3、 配置溯源

A-Ops配置溯源在机器管理的基础上依赖gala-ragdoll实现，同样在部署gala-ragdoll服务之前，须完成[资产管理](#31-资产管理)部分的部署。

### 3.3.1、 节点信息

| 机器编号 | 配置IP      | 部署模块     |
| -------- | ----------- | ------------ |
| 机器C    | 192.168.1.3 | gala-ragdoll |

### 3.3.2、 部署步骤

[部署步骤](#312部署步骤)

#### 3.3.2.1、 部署gala-ragdoll

- 安装gala-ragdoll

```shell
yum install gala-ragdoll python3-gala-ragdoll -y
```

- 修改配置文件

```shell
vim /etc/ragdoll/gala-ragdoll.conf
```

> **将collect节点collect_address中IP地址修改为机器B的地址，collect_api与collect_port修改为实际接口地址**

```ini
[git]
git_dir = "/home/confTraceTest"
user_name = "user_name"
user_email = "user_email"

[collect]
collect_address = "http://192.168.1.2"    //此处修改为机器B的真实IP
collect_api = "/manage/config/collect"    //此处接口原为示例值，需修改为实际接口值/manage/config/collect
collect_port = 11111                      //此处修改为aops-zeus服务的实际端口

[sync]
sync_address = "http://192.168.1.2"
sync_api = "/manage/config/sync"          //此处接口原为示例值，需修改为实际接口值/manage/config/sync
sync_port = 11111

[objectFile]
object_file_address = "http://192.168.1.2"
object_file_api = "/manage/config/objectfile"   //此处接口原为示例值，需修改为实际接口值/manage/config/objectfile
object_file_port = 11111

[ragdoll]
port = 11114
```

- 启动gala-ragdoll服务

```shell
systemctl start gala-ragdoll
```

## 3.4、 异常检测

异常检测模块依赖[机器管理](#31-资产管理)服务，故在部署异常检测功能前须完成[机器管理](#31-资产管理)模块部署，然后再部署aops-diana。

基于分布式部署考虑，aops-diana服务需在机器B与机器C同时部署，分别扮演消息队列中的生产者与消费者角色。

数据服务部分aops-diana服务的运行需要**mysql、elasticsearch、kafka**以及**prometheus**的支持。

### 3.4.1、 节点信息

| 机器编号 | 配置IP      | 部署模块   |
| -------- | ----------- | ---------- |
| 机器A    | 192.168.1.1 | kafka      |
| 机器B    | 192.168.1.2 | aops-diana |
| 机器C    | 192.168.1.3 | aops-diana |

### 3.4.2、 部署步骤

[部署步骤](#312部署步骤)

[部署elasticsearch](#3221-部署elasticsearch)

#### 3.4.2.1、 部署kafka

kafka使用zooKeeper用于管理、协调代理，在应用**kafka**服务时需要同步部署**zookeeper**服务。

- 安装zookeeper

```shell
yum install zookeeper -y
```

- 启动zookeeper服务

```shell
systemctl start zookeeper
```

- 安装kafka

```shell
yum install kafka -y
```

- 修改kafka配置文件

```shell
vim /opt/kafka/config/server.properties
```

- 修改**listeners**为本机ip

```yaml
############################# Socket Server Settings #############################

# The address the socket server listens on. It will get the value returned from
# java.net.InetAddress.getCanonicalHostName() if not configured.
#   FORMAT:
#     listeners = listener_name://host_name:port
#   EXAMPLE:
#     listeners = PLAINTEXT://your.host.name:9092
listeners=PLAINTEXT://192.168.1.1:9092
```

- 后台运行kafka服务

```shell
cd /opt/kafka/bin
nohup ./kafka-server-start.sh ../config/server.properties &

# 查看nohup所有的输出出现A本机ip 以及kafka启动成功INFO
tail -f ./nohup.out
```

#### 3.4.2.2、 部署diana

- 安装aops-diana

```shell
yum install aops-diana -y
```

- 修改配置文件

  > 机器B与机器C中aops-diana分别扮演不同的角色，通过**配置文件的差异来区分两者扮演角色的不同**

```shell
vim /etc/aops/diana.ini
```

（1）机器C中aops-diana以**executor**模式启动，**扮演kafka消息队列中的消费者角色**，配置文件需修改部分如下所示

```ini
[diana]
ip=192.168.1.3  // 此处ip修改为机器C真实ip
port=11112
mode=executor  // 该模式为executor模式，用于常规诊断模式下的执行器，扮演kafka中消费者角色。
timing_check=on

[default_mode]
period=60
step=60

[elasticsearch]
ip=192.168.1.1  // 此处ip修改为机器A真实ip
port=9200
max_es_query_num=10000000

[mysql]
ip=192.168.1.1  // 此处ip修改为机器A真实ip
port=3306
database_name=aops
engine_format=mysql+pymysql://@%s:%s/%s
pool_size=100
pool_recycle=7200

[redis]
ip=192.168.1.1  // 此处ip修改为机器A真实ip
port=6379

[prometheus]
ip=192.168.1.1  // 此处ip修改为机器A真实ip
port=9090
query_range_step=15s

[agent]
default_instance_port=8888

[zeus]
ip=192.168.1.2  // 此处ip修改为机器B真实ip
port=11111

[consumer]
kafka_server_list=192.168.1.1:9092  // 此处ip修改为机器A真实ip
enable_auto_commit=False
auto_offset_reset=earliest
timeout_ms=5
max_records=3
task_name=CHECK_TASK
task_group_id=CHECK_TASK_GROUP_ID
result_name=CHECK_RESULT

[producer]
kafka_server_list = 192.168.1.1:9092  // 此处ip修改为机器A真实ip
api_version = 0.11.5
acks = 1
retries = 3
retry_backoff_ms = 100
task_name=CHECK_TASK
task_group_id=CHECK_TASK_GROUP_ID

[uwsgi]
wsgi-file=manage.py
daemonize=/var/log/aops/uwsgi/diana.log
http-timeout=600
harakiri=600
processes=2
threads=2
```

> **mysql数据库设置为密码模式**，请参阅[FAQ：密码模式下mysql服务配置链接字符串](#Q5、mysql设置为密码模式)

（2）机器B中diana以**configurable**模式启动，**扮演kafka消息队列中的生产者角色**，aops-hermes中关于aops-diana的端口配置以该机器ip与端口为准，配置文件需修改部分如下所示

```ini
[diana]
ip=192.168.1.2  // 此处ip修改为机器B真实ip
port=11112
mode=configurable  // 该模式为configurable模式，用于常规诊断模式下的调度器，充当生产者角色。
timing_check=on

[default_mode]
period=60
step=60

[elasticsearch]
ip=192.168.1.1  // 此处ip修改为机器A真实ip
port=9200
max_es_query_num=10000000

[mysql]
ip=192.168.1.1  // 此处ip修改为机器A真实ip
port=3306
database_name=aops
engine_format=mysql+pymysql://@%s:%s/%s
pool_size=100
pool_recycle=7200

[redis]
ip=192.168.1.1  // 此处ip修改为机器A真实ip
port=6379

[prometheus]
ip=192.168.1.1  // 此处ip修改为机器A真实ip
port=9090
query_range_step=15s

[agent]
default_instance_port=8888

[zeus]
ip=192.168.1.2  // 此处ip修改为机器B真实ip
port=11111

[consumer]
kafka_server_list=192.168.1.1:9092  // 此处ip修改为机器A真实ip
enable_auto_commit=False
auto_offset_reset=earliest
timeout_ms=5
max_records=3
task_name=CHECK_TASK
task_group_id=CHECK_TASK_GROUP_ID
result_name=CHECK_RESULT

[producer]
kafka_server_list = 192.168.1.1:9092  // 此处ip修改为机器A真实ip
api_version = 0.11.5
acks = 1
retries = 3
retry_backoff_ms = 100
task_name=CHECK_TASK
task_group_id=CHECK_TASK_GROUP_ID

[uwsgi]
wsgi-file=manage.py
daemonize=/var/log/aops/uwsgi/diana.log
http-timeout=600
harakiri=600
processes=2
threads=2
```

> **mysql数据库设置为密码模式**，请参阅[FAQ：密码模式下mysql服务配置链接字符串](#Q5、mysql设置为密码模式)

- 启动aops-diana服务

```shell
systemctl start aops-diana
```

**注意：服务启动前请确保已 [初始化aops-diana数据库](#3423初始化aops-diana数据库)**

> diana服务启动失败，且报错内容包含mysql数据库连接失败，请排查是否设置mysql密码，如果是请参阅[FAQ：密码模式下mysql服务启动失败](#Q5、mysql设置为密码模式)

#### 3.4.2.3、初始化aops-diana数据库

- diana数据库初始化

```shell
cd /opt/aops/scripts/deploy
bash aops-basedatabase.sh init diana
```

**注意：在未安装aops-tools工具包时，也可获取sql脚本通过mysql加载的方式初始化（sql脚本路径：/opt/aops/database/diana.sql）**

[FAQ：密码模式下mysql数据库初始化](#Q5、mysql设置为密码模式)

[FAQ：/opt/aops/scripts/deploy目录不存在](#Q7、/opt/aops/scripts/deploy目录不存在)

## 3.5、客户端安装

aops-ceres作为A-Ops模块的客户端，通过ssh协议与AOps管理中心进行数据交互，提供采集主机信息、响应并处理中心命令等功能。

### 3.5.1、 节点信息

| 机器编号 | 配置IP      | 部署模块   |
| -------- | ----------- | ---------- |
| 机器D    | 192.168.1.4 | aops-ceres |

### 3.5.2、 部署客户端

```shell
yum install aops-ceres dnf-hotpatch-plugin -y
```

## FAQ

### Q1、最大连接数（MaxStartups）

批量添加主机接口服务执行过程中会受到aops-zeus安装所在主机sshd服务配置中最大连接数（MaxStartups）的限制，会出现部分主机不能连接的情况，如有大量添加主机的需求，可考虑临时调增该数值。关于该配置项的修改可参考[ssh文档](https://www.man7.org/linux/man-pages/man5/sshd_config.5.html)。

### Q2、504网关超时

部分http访问接口执行时间较长，web端可能返回504错误，可向nginx配置中添加proxy_read_timeout配置项，并适当调大该数值，可降低504问题出现概率。

### Q3、防火墙

若防火墙不方便关闭，请设置放行服务部署过程涉及的所有接口，否则会造成服务不可访问，影响A-Ops的正常使用。

### Q4、elasticasearch访问拒绝

elasticsearch分布式部署多节点时，需调整配置跨域部分，允许各节点访问。

### Q5、mysql设置为密码模式

- **服务配置mysql链接字符串**

mysql数据库链接设置密码模式（例如用户名为**root**，密码为**123456**），则需要调整[mysql]配置节下engine_format配置项（apollo、zeus同步调整），数据格式如下：

```ini
[mysql]
egine_format=mysql+pymysql://root:123456@%s:%s/%s
```

- **初始化脚本aops-basedatabase.sh修改**

aops-basedatabase.sh脚本需要调整145行代码实现

> aops-basedatabase.sh调整前内容如下：

```shell
database = pymysql.connect(host='$mysql_ip', port=$port, database='mysql', autocommit=True,client_flag=CLIENT.MULTI_STAT    EMENTS)
```

> aops-basedatabase.sh调整后内容如下：

```shell
database = pymysql.connect(host='$mysql_ip', port=$port, database='mysql', password='密码', user='用户名', autocommit=True, client_flag=CLIENT.MULTI_STATEMENTS)
```

- **服务启动时数据库连接错误**

**/usr/bin/aops-vulcanus**脚本需要调整178行代码实现

> /usr/bin/aops-vulcanus调整前内容如下：

```shell
connect = pymysql.connect(host='$mysql_ip', port=$port, database='$aops_database')
```

> /usr/bin/aops-vulcanus调整后内容如下：

```shell
connect = pymysql.connect(host='$mysql_ip', port=$port, database='$aops_database', password='密码', user='用户名')
```

**注意：当服务器不是以root用户登录时，需添加user="root"或mysql允许链接的用户名**

### Q6、配置update源

```shell
echo "[update]
name=update
baseurl=http://repo.openeuler.org/openEuler-24.03-LTS/update/$basearch/
enabled=1
gpgcheck=0
[update-epol]
name=update-epol
baseurl=http://repo.openeuler.org/openEuler-24.03-LTS/EPOL/update/main/$basearch/
enabled=1
gpgcheck=0" > /etc/yum.repos.d/openEuler-update.repo
```

> 注意： 其中**openEuler-24.03-LTS** 根据部署的系统版本具体调整，或可直接参与openeuler官网中针对repo源配置介绍

### Q7、/opt/aops/scripts/deploy目录不存在

在执行数据库初始化时，提示不存在`/opt/aops/scripts/deploy`文件目录，执行安装aops-tools工具包

```shell
yum install aops-tools -y
```
