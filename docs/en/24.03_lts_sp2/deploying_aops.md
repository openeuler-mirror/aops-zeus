# Deploying A-Ops

## 1 Introduction to A-Ops

A-Ops is a service used to improve the overall security of hosts. It provides functions such as asset management, vulnerability management, and configuration source tracing to identify and manage information assets, monitor software vulnerabilities, and rectify system faults on hosts, ensuring stable and secure running of hosts.

The following table describes the modules related to the A-Ops service.

| Module              | Description                                                                                                                                                                                                                                                                                                                                                       |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| aops-ceres          | Client of the A-Ops service.<br>Collects host data and manages other data collectors (such as gala-gopher).<br>Responds to the commands delivered by the management center and processes the requirements and operations of the management center.                                                                                                                |
| aops-zeus           | A-Ops basic application management center, which interacts with other modules. The default port number is 11111.<br>Provides the basic host management service externally, such as adding and deleting hosts and host groups.                                                                                                                                                                    |
| aops-hermes         | Provides a visualized operation interface for A-Ops to display data information to users, improving service usability.                                                                                                                                                                                                                                                                         |
| aops-apollo         | Vulnerability management module of A-Ops. The default port number is 11116.<br>Identifies clients, and periodically obtains security notices released by the openEuler community and updates them to the vulnerability database.<br>Detects vulnerabilities in the system and software by comparing the vulnerabilities with those in the vulnerability database. |
| aops-vulcanus       | Basic tool library of A-Ops. **Except aops-ceres and aops-hermes, modules must be installed and used together with this module.**                                                                                                                                                                                                                   |
| aops-tools          | Provides the basic environment deployment script and database table initialization. The script is available in the **/opt/aops/scripts** directory after A-Ops is installed.                                                                                                                                                                                                                                     |
| gala-ragdoll        | Configuration source tracing module of A-Ops.<br>Uses Git to monitor and record configuration file changes. The default port number is 11114.                                                                                                                                                                                                                     |
| dnf-hotpatch-plugin | DNF plug-in, which allows DNF to recognize hot patch information and provides hot patch scanning and application.                                                                                                                                                                                                                                                 |

## 2 Environment Requirements

You are advised to use four hosts running openEuler 24.03 LTS for deployment. Use three as the server and one as the managed host managed by A-Ops. **Configure the update repository** ([Q6: update Repository Configuration](#q6-update-repository-configuration)). The deployment scheme is as follows:

- Host A: For MySQL, Redis, and Elasticsearch deployment. It provides data service support. The recommended memory is more than 8 GB.
- Host B: For the A-Ops asset management service (zeus),  frontend display, and complete service function support. The recommended memory is more than 6 GB.
- Host C: For the A-Ops configuration source tracing service (gala-ragdoll) and vulnerability management. The recommended memory is 4 GB or more.
- Host D: As an A-Ops client and is used as a host managed and monitored by A-Ops. (aops-ceres can be deployed on hosts that need to be managed.)

| Host   | IP Address  | Module                                |
| ------ | ----------- | ------------------------------------- |
| Host A | 192.168.1.1 | MySQL, Elasticsearch, Redis           |
| Host B | 192.168.1.2 | aops-zeus, aops-hermes, aops-diana    |
| Host C | 192.168.1.3 | aops-apollo, gala-ragdoll, aops-diana |
| Host D | 192.168.1.4 | aops-ceres, dnf-hotpatch-plugin       |

>Before deployment, disable the **firewall and SELinux** on each host.

- Disable the firewall.

```shell
systemctl stop firewalld
systemctl disable firewalld
systemctl status firewalld
setenforce 0

```

- Disable SELinux.

```shell
# Change the status of SELinux to disabled in /etc/selinux/config.

vi /etc/selinux/config
SELINUX=disabled

# After changing the value, press ESC and enter :wq to save the modification.
```

Note: SELinux will be disabled after a reboot.

## 3. Server Deployment

### 3.1 Asset Management

To use the asset management function, you need to deploy the aops-zeus, aops-hermes, MySQL, and Redis services.

#### 3.1.1 Node Information

| Host   | IP Address  | Module                                |
| ------ | ----------- | ------------------------------------- |
| Host A | 192.168.1.1 | MySQL, Redis  |
| Host B | 192.168.1.2 | aops-zeus, aops-hermes              |

#### 3.1.2 Deployment Procedure

##### 3.1.2.1 Deploying MySQL

- Install MySQL.

```shell
yum install mysql-server
```

- Modify the MySQL configuration file.

```bash
vim /etc/my.cnf
```

- Add **bind-address** and set it to the IP address of the local host in the **mysqld** section.

```ini
[mysqld]
bind-address=192.168.1.1
```

- Restart the MySQL service.

```bash
systemctl restart mysqld
```

- Set the MySQL database access permission for the **root** user.

```mysql
$ mysql

mysql> show databases;
mysql> use mysql;
mysql> select user,host from user; -- If the value of host is localhost, only the local host can connect to the MySQL database. The external network and local software client cannot connect to the MySQL database.

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
mysql> update user set host = '%' where user='root'; -- Allow the access of the root user using any IP address.
mysql> flush privileges; -- Refresh the permissions.
mysql> exit
```

##### 3.1.2.2 Deploying Redis

- Install Redis.

```shell
yum install redis -y
```

- Modify the Redis configuration file.

```shell
vim /etc/redis.conf
```

Bind IP addresses.

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
bind 127.0.0.1 192.168.1.1# Add the actual IP address of host A.
```

- Start the Redis service.

```shell
systemctl start redis
```

##### 3.1.2.3 Deploying Prometheus

- Install Prometheus.

```shell
yum install prometheus2 -y
```

- Modify the Prometheus configuration file.

```shell
vim /etc/prometheus/prometheus.yml
```

- Add the gala-gopher IP addresses of the managed client to the monitored targets of Prometheus.

> In this document, host D is the client. Add the gala-gopher address of host D.

- Modify the **targets** configuration item.

```yaml
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

Start the Prometheus service.

```shell
systemctl start prometheus
```

##### 3.1.2.4 Deploying aops-zeus

- Install aops-zeus.

```shell
yum install aops-zeus -y
```

- Modify the configuration file.

```shell
vim /etc/aops/zeus.ini
```

- Change the IP address of each service in the configuration file to the actual IP address. In this document, aops-zeus is deployed on host B. Therefore, you need to set the IP address to the IP address of host B.

```ini
[zeus]
ip=192.168.1.2  // Change the IP address to the actual IP address of host B.
port=11111

[uwsgi]
wsgi-file=manage.py
daemonize=/var/log/aops/uwsgi/zeus.log
http-timeout=600
harakiri=600
processes=2     // Generate a specified number of workers or processes.
gevent=100      // Number of gevent asynchronous cores

[mysql]
ip=192.168.1.1  // Change the IP address to the actual IP address of host A.
port=3306
database_name=aops
engine_format=mysql+pymysql://@%s:%s/%s
pool_size=100
pool_recycle=7200

[agent]
default_instance_port=8888

[redis]
ip=192.168.1.1  // Change the IP address to the actual IP address of host A.
port=6379

[apollo]
ip=192.168.1.3  // Change the IP address to the actual IP address of the apollo service deployment. It is recommended that apollo and zeus be deployed separately. This section is not required if apollo is not used.
port=11116
```

> **Set the MySQL database mode to password mode**. For details, see [Q5: MySQL Password Mode](#q5-mysql-password-mode)
 
- Start the aops-zeus service.

```shell
systemctl start aops-zeus
```

**Note: [Initialize the aops-zeus database](#3125-initializing-the-aops-zeus-database) before starting the service.**

> If the zeus service fails to be started and the error message indicates that the MySQL database cannot be connected, check if a MySQL password is set. If yes, see [Q5: MySQL Password Mode](#q5-mysql-password-mode).

#### 3.1.2.5 Initializing the aops-zeus Database

- Initialize the database.

```shell
cd /opt/aops/scripts/deploy
bash aops-basedatabase.sh init zeus
```

**Note: If aops-tools is not installed, run the SQL script to initialize. The script path is /opt/aops/database/zeus.sql**

[Q5: MySQL Password Mode](#q5-mysql-password-mode)

[Q7: Nonexisting /opt/aops/scripts/deploy](#q7-nonexisting-optaopsscriptsdeploy)

##### 3.1.2.6 Deploying aops-hermes

- Install aops-hermes.

```shell
yum install aops-hermes -y
```

- Modify the configuration file.

```shell
vim /etc/nginx/aops-nginx.conf
```

- Some service configurations:

  > As the services are deployed on host B, configure the Nginx proxy to set the services addresses to the actual IP address of host B.

```ini
 # Ensure that Nginx still uses index.html as the entry when the front-end route changes.
  location / {
      try_files $uri $uri/ /index.html;
      if (!-e $request_filename){
          rewrite ^(.*)$ /index.html last;
      }
  }
    # Change it to the actual IP address of the host where aops-zeus is deployed.
  location /api/ {
      proxy_pass http://192.168.1.2:11111/;
  }
  # Enter the IP address of gala-ragdoll. IP addresses that involve port 11114 need to be configured.
  location /api/domain {
      proxy_pass http://192.168.1.3:11114/;
      rewrite ^/api/(.*) /$1 break;
  }
    # Enter the IP address of gala-apollo.
  location /api/vulnerability {
      proxy_pass http://192.168.1.3:11116/;
      rewrite ^/api/(.*) /$1 break;
  }
```

- Enable the aops-hermes service.

```shell
systemctl start aops-hermes
```

### 3.2 Vulnerability Management

The CVE management module is implemented based on the [asset management](#31-asset-management) module. Therefore, you need to [deploy the module](#312-deployment-procedure) before deploying aops-apollo.

The running of the aops-apollo service requires the support of the **MySQL, Elasticsearch, and Redis** databases.

#### 3.2.1 Node Information

| Host   | IP Address  | Module        |
| ------ | ----------- | ------------- |
| Host A | 192.168.1.1 | Elasticsearch |
| Host C | 192.168.1.3 | aops-apollo   |

#### 3.2.2 Deployment Procedure

See [Asset Management](#312-deployment-procedure).

##### 3.2.2.1 Deploying Elasticsearch

- Configure the repository for Elasticsearch.

```shell
echo "[aops_elasticsearch]
name=Elasticsearch repository for 7.x packages
baseurl=https://artifacts.elastic.co/packages/7.x/yum
gpgcheck=1
gpgkey=https://artifacts.elastic.co/GPG-KEY-elasticsearch
enabled=1
autorefresh=1
type=rpm-md" > "/etc/yum.repos.d/aops_elasticsearch.repo"
```

- Install Elasticsearch.

```shell
yum install elasticsearch-7.14.0-1 -y
```

- Modify the Elasticsearch configuration file.

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
# Change the value to the actual IP address of host A.
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
# Cross-domain configurations
http.cors.enabled: true
http.cors.allow-origin: "*"
#
```

- Restart the Elasticsearch service.

```shell
systemctl restart elasticsearch
```

##### 3.2.2.2 Deploying aops-apollo

- Install aops-apollo.

```shell
yum install aops-apollo
```

- Modify the configuration file.

```shell
vim /etc/aops/apollo.ini
```

- Change the IP address of each service in the **apollo.ini** to the actual IP address.

```ini
[apollo]
ip=192.168.1.3// Change it to the actual IP address of host C.
port=11116
host_vault_dir=/opt/aops
host_vars=/opt/aops/host_vars

[zeus]
ip=192.168.1.2 // Change it to the actual IP address of host B.
port=11111

# hermes info is used to send mail.
[hermes]
ip=192.168.1.2  // Change it to the actual IP address of aops-hermes, for example, the IP address of host B.
port=80         // Change it to the actual port of the hermes service.

[cve]
cve_fix_function=yum
# value between 0-23, for example, 2 means 2:00 in a day.
cve_scan_time=2

[mysql]
ip=192.168.1.1 // Change it to the actual IP address of host A.
port=3306
database_name=aops
engine_format=mysql+pymysql://@%s:%s/%s
pool_size=100
pool_recycle=7200

[elasticsearch]
ip=192.168.1.1 // Change it to the actual IP address of host A.
port=9200
max_es_query_num=10000000

[redis]
ip=192.168.1.1 // Change it to the actual IP address of host A.
port=6379

[uwsgi]
wsgi-file=manage.py
daemonize=/var/log/aops/uwsgi/apollo.log
http-timeout=600
harakiri=600
processes=2
gevent=100
```

> **Set the MySQL database to the password mode**. For details, see [Q5: MySQL Password Mode](#q5-mysql-password-mode).

- Start the aops-apollo service.

```shell
systemctl start aops-apollo
```

**Note: [Initialize the aops-apollo database](#3223-initializing-the-aops-apollo-database) before starting the service.**

> If the apollo service fails to be started and the error message indicates that the MySQL database cannot be connected, check if a MySQL password is set. If yes, see [Q5: MySQL Password Mode](#q5-mysql-password-mode).

#### 3.2.2.3 Initializing the aops-apollo Database

- Initialize the apollo database.

```shell
cd /opt/aops/scripts/deploy
bash aops-basedatabase.sh init apollo
```

**Note: If aops-tools is not installed, run the SQL script to initialize. The script path is /opt/aops/database/apollo.sql**

[Q5: MySQL Password Mode](#q5-mysql-password-mode)

[FAQs: Nonexisting /opt/aops/scripts/deploy](#q7-nonexisting-optaopsscriptsdeploy)

### 3.3 Configuring Source Tracing

A-Ops configuration source tracing depends on gala-ragdoll. Therefore, you need to complete the deployment of [Asset Management](#31-asset-management) and then deploy gala-ragdoll.

#### 3.3.1 Node Information

| Host   | IP Address  | Module       |
| ------ | ----------- | ------------ |
| Host C | 192.168.1.3 | aops-ragdoll |

#### 3.3.2 Deployment Procedure

See [Asset Management](#31-asset-management).

##### 3.3.2.1 Deploying gala-ragdoll

- Install gala-ragdoll.

```shell
yum install gala-ragdoll python3-gala-ragdoll -y
```

- Modify the configuration file.

```shell
vim /etc/ragdoll/gala-ragdoll.conf
```

> **Change the IP address in collect_address of the collect section to the IP address of host B, and change the values of collect_api and collect_port to the actual API and port number.**

```ini
[git]
git_dir = "/home/confTraceTest"
user_name = "user_name"
user_email = "user_email"

[collect]
collect_address = "http://192.168.1.2"    // Change it to the actual IP address of host B.
collect_api = "/manage/config/collect"    // The value is an example. Change it to the actual value.
collect_port = 11111                      // Change it to the actual port number of the aops-zeus service.

[sync]
sync_address = "http://192.168.1.2"
sync_api = "/manage/config/sync"          // The value is an example. Change it to the actual value.
sync_port = 11111

[objectFile]
object_file_address = "http://192.168.1.2"
object_file_api = "/manage/config/objectfile"   // The value is an example. Change it to the actual value.
object_file_port = 11111

[ragdoll]
port = 11114
```

- Start the gala-ragdoll service.

```shell
systemctl start gala-ragdoll
```

## 3.4 Exception Detection

The exception detection function is implemented based on the aops-zeus service. Therefore, you need to deploy aops-zeus and then aops-diana.

Considering distributed deployment, the aops-diana service must be deployed on both host B and host C to act as the producer and consumer in the message queue, respectively.

The running of the aops-diana service requires the support of MySQL, Elasticsearch, Kafka, and Prometheus.

### 3.4.1 Node Information

| Host   | IP Address  | Module     |
| ------ | ----------- | ---------- |
| Host A | 192.168.1.1 | Kafka      |
| Host B | 192.168.1.2 | aops-diana |
| Host C | 192.168.1.3 | aops-diana |

### 3.4.2 Deployment Procedure

[Asset Management](#312-deployment-procedure)

[Deploying Elasticsearch](#3221-deploying-elasticsearch)

#### 3.4.2.1 Deploying Kafka

Kafka uses ZooKeeper to manage and coordinate agents. Therefore, you need to deploy ZooKeeper when deploying Kafka.

- Install ZooKeeper.

```shell
yum install zookeeper -y
```

- Start the ZooKeeper service.

```shell
systemctl start zookeeper
```

- Install Kafka.

```shell
yum install kafka -y
```

- Modify the Kafka configuration file.

```shell
vim /opt/kafka/config/server.properties
```

Change the value of **listeners** to the IP address of the local host.

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

- Start the Kafka service.

```shell
cd /opt/kafka/bin
nohup ./kafka-server-start.sh ../config/server.properties &

# Check all the outputs of nohup. If the IP address of host A and the Kafka startup success INFO are displayed, Kafka is started successfully.
tail -f ./nohup.out
```

#### 3.4.2.2 Deploying diana

- Install aops-diana.

```shell
yum install aops-diana
```

Modify the configuration file. 
> The aops-dianas on host B and host C play different roles, which are **distinguished based on the differences in the configuration file**.

```shell
vim /etc/aops/diana.ini
```

(1) Start aops-diana on host C in executor mode. It functions as the consumer in the Kafka message queue. The configuration file to be modified is as follows:

```ini
[diana]
ip=192.168.1.3  // Change the IP address to the actual IP address of host C.
port=11112
mode=executor  // This mode is the executor mode. It is used as the executor in common diagnosis mode and functions as the consumer in Kafka.
timing_check=on

[default_mode]
period=60
step=60

[elasticsearch]
ip=192.168.1.1  // Change the IP address to the actual IP address of host A.
port=9200
max_es_query_num=10000000


[mysql]
ip=192.168.1.1  // Change the IP address to the actual IP address of host A.
port=3306
database_name=aops
engine_format=mysql+pymysql://@%s:%s/%s
pool_size=10000
pool_recycle=7200

[redis]
ip=192.168.1.1  // Change the IP address to the actual IP address of host A.
port=6379


[prometheus]
ip=192.168.1.1  // Change the IP address to the actual IP address of host A.
port=9090
query_range_step=15s

[agent]
default_instance_port=8888

[zeus]
ip=192.168.1.2  // Change the IP address to the actual IP address of host B.
port=11111

[consumer]
kafka_server_list=192.168.1.1:9092  // Change the IP address to the actual IP address of host C.
enable_auto_commit=False
auto_offset_reset=earliest
timeout_ms=5
max_records=3
task_name=CHECK_TASK
task_group_id=CHECK_TASK_GROUP_ID
result_name=CHECK_RESULT

[producer]
kafka_server_list = 192.168.1.1:9092  // Change the IP address to the actual IP address of host C.
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

> **Set the MySQL database to the password mode**. For details, see [Q5: MySQL Password Mode](#q5-mysql-password-mode).

(2) Start aops-diana on host B in configurable mode. It functions as the producer in the Kafka message queue. The aops-diana port configuration in the aops-hermes file is subject to the IP address and port number of this host. The configuration file to be modified is as follows:

```ini
[diana]
ip=192.168.1.2  // Change the IP address to the actual IP address of host B.
port=11112
mode=configurable  // This mode is the configurable mode. It is used as a scheduler in common diagnosis mode and functions as the producer.
timing_check=on

[default_mode]
period=60
step=60

[elasticsearch]
ip=192.168.1.1  // Change the IP address to the actual IP address of host A.
port=9200
max_es_query_num=10000000

[mysql]
ip=192.168.1.1  // Change the IP address to the actual IP address of host A.
port=3306
database_name=aops
engine_format=mysql+pymysql://@%s:%s/%s
pool_size=100
pool_recycle=7200

[redis]
ip=192.168.1.1  // Change the IP address to the actual IP address of host A.
port=6379

[prometheus]
ip=192.168.1.1  // Change the IP address to the actual IP address of host A.
port=9090
query_range_step=15s

[agent]
default_instance_port=8888

[zeus]
ip=192.168.1.2  // Change the IP address to the actual IP address of host B.
port=11111

[consumer]
kafka_server_list=192.168.1.1:9092  // Change the IP address to the actual IP address of host A.
enable_auto_commit=False
auto_offset_reset=earliest
timeout_ms=5
max_records=3
task_name=CHECK_TASK
task_group_id=CHECK_TASK_GROUP_ID
result_name=CHECK_RESULT

[producer]
kafka_server_list = 192.168.1.1:9092  // Change the IP address to the actual IP address of host A.
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

> **Set the MySQL database to the password mode**. For details, see [Q5: MySQL Password Mode](#q5-mysql-password-mode).

Start the aops-diana service.

```shell
systemctl start aops-diana
```

**Note: [Initialize the aops-diana database](#3423-initializing-the-aops-diana-database) before starting the service.**

> If the diana service fails to be started and the error message indicates that the MySQL database cannot be connected, check if a MySQL password is set. If yes, see [Q5: MySQL Password Mode](#q5-mysql-password-mode).

#### 3.4.2.3 Initializing the aops-diana Database

- Initialize the diana database.

```shell
cd /opt/aops/scripts/deploy
bash aops-basedatabase.sh init diana
```

**Note:If aops-tools is not installed, run the SQL script to initialize. The script path is /opt/aops/database/diana.sql**

[Q5: MySQL Password Mode](#q5-mysql-password-mode)

[FAQs: Nonexisting /opt/aops/scripts/deploy](#q7-nonexisting-optaopsscriptsdeploy)

## 3.5 Client Installation

aops-ceres functions as the client of A-Ops. It communicates with the A-Ops management center through SSH and provides functions such as host information collection and command response.

### 3.5.1 Node Information

| Host   | IP Address  | Module     |
| ------ | ----------- | ---------- |
| Host D | 192.168.1.4 | aops-ceres |

### 3.5.2  Client Deployment

```shell
yum install aops-ceres dnf-hotpatch-plugin -y
```

## FAQs

### Q1: Max Number of Connections

When host interfaces are added in batches, due to the max number of SSH connections (**MaxStartups**) of the host where aops-zeus is installed, some hosts may fail to be connected. You can temporarily increase **MaxStartups** as required. For details, see the [SSH documentation](https://www.man7.org/linux/man-pages/man5/sshd_config.5.html).

### Q2: 504 Gateway Timeout

Some HTTP interfaces may take a long time to execute, resulting in error 504 on the web client. You can reduce the probability of error 504 by adding **proxy_read_timeout** to the Nginx configuration or increase its value.

### Q3: Firewall

If firewall cannot be disabled, open the ports involved in service deployment on the firewall. Otherwise, services may be inaccessible and A-Ops cannot be used properly.

### Q4: Elasticsearch Access Denied

If Elasticsearch is deployed on multiple nodes in a distributed manner, set the cross-domain access configurations properly to enable the access of the nodes.

### Q5: MySQL Password Mode

- **Configure the mysql section in the service configuration.**

To set the password mode for the MySQL database connection (for example, the user is **root**, and the password is **123456**), change the value of **engine_format** in the **\[mysql]** section in apollo and zeus configurations.

```ini
[mysql]
engine_format=mysql+pymysql://root:123456@%s:%s/%s
```

- **Modify the aops-basedatabase.sh initialization script.**

Modify the 145th line of **aops-basedatabase.sh**.

> Before modification:

```shell
database = pymysql.connect(host='$mysql_ip', port=$port, database='mysql', autocommit=True,client_flag=CLIENT.MULTI_STAT    EMENTS)
```

> After modification:

```shell
database = pymysql.connect(host='$mysql_ip', port=$port, database='mysql', password='password', user='user', autocommit=True, client_flag=CLIENT.MULTI_STATEMENTS)
```

- **Database connection error upon service startup**

Modify the 178th line in **/usr/bin/aops-vulcanus**.

> Before modification:

```shell
connect = pymysql.connect(host='$mysql_ip', port=$port, database='$aops_database')
```

> After modification:

```shell
connect = pymysql.connect(host='$mysql_ip', port=$port, database='$aops_database', password='password', user='user')
```

**Note: If a non-root user is used for logging in to the server, add user ="root" or a user allowed by MySQL.**

### Q6: update Repository Configuration

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

> Note: Change **openEuler-24.03-LTS** to the actual OS version. You can also refer to the repository description in the openEuler official documentation.

### Q7: Nonexisting /opt/aops/scripts/deploy

During database initialization, if **/opt/aops/scripts/deploy** does not exits, install the aops-tools package.

```shell
yum install aops-tools -y
```
