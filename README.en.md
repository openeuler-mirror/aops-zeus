# aops-zeus

### Introduce

The basic services of the intelligent O&M platform AOPS provide basic  host management and user management functions, and are responsible for  interacting with other service modules. 

### Environmental needs

- Python 3.9.9+
- MySql 8.0
- Redis

### Installation tutorial

1. Clone this repository and development kit, using openeuler22.03-LTS-SP1 as an example

   ```
   git clone https://gitee.com/openeuler/aops-zeus.git
   git clone https://gitee.com/openeuler/aops-vulcanus.git
   ```

2. Go to the project directory 

   ```
   cd aops-zeus
   ```

3. Install the dependencies required for the project to run 

   `dnf install <dependency-name>` Install the following dependencies by .

   ```
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

4. Service configuration 

   Install MySQL and Redis and create AOPS databases in MySQL. 

   ```
   create database aops default character set utf8mb4 collate utf8mb4_bin;
   ```

   After the installation is complete, follow the following steps to configure MySQL and Redis. 

   (1) Create a profile directory 

   ```
   mkdir -p /etc/aops
   ```

   (2) Copy the configuration file to this directory 

   ```
   cp -r conf/* /etc/aops/
   ```

   (3) Modify the configuration information 

   ```
   vim /etc/aops/zeus.ini
   ```

   ```
   [zeus]
   ip=127.0.0.1
   port=11111
   
   [uwsgi]
   wsgi-file=manage.py
   daemonize=/var/log/aops/uwsgi/zeus.log
   http-timeout=600
   harakiri=600
   processes=2
   gevent=100
   
   [mysql]
   ip=127.0.0.1
   port=3306
   database_name=aops
   mysql+pymysql://root:123456@%s:%s/%s
   engine_format=mysql+pymysql://@%s:%s/%s
   pool_size=100
   pool_recycle=7200
   
   [prometheus]
   ip=127.0.0.1
   port=9090
   query_range_step=15s
   
   [agent]
   default_instance_port=8888
   
   [redis]
   ip=127.0.0.1
   port=6379
   ```

5. Add the project directory to the environment variables, such as /work/aops-zeus and /work/aops-vulcanus 

   ```
   export PYTHONPATH=$PYTHONPATH:/work/aops-zeus
   export PYTHONPATH=$PYTHONPATH:/work/aops-vulcanus
   ```

6. Start the development server 

   ```
   python3 manage.py
   ```

   You can now `http://127.0.0.1:11111` access the project

### Directions for use

1. API interface documentation
2. For more information, please refer to the Asset Management section of the AOPS User Manual

### Get involved

1. Fork this repository 
2. Create a new Feat_xxx branch 
3. Submit the code 
4. Create a new pull request 

