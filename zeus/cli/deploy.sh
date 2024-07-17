#!/bin/bash
ELASTICSEARCH_REPO="/etc/yum.repos.d/aops_elascticsearch.repo"

function check_es_status() {
    visit_es_response=$(curl -s -XGET http://127.0.0.1:9200)
    if [[ "${visit_es_response}" =~ "You Know, for Search" ]]; then
        echo "[ERROR] The service is running, please close it manually and try again."
        exit 1
    fi
}

function create_es_repo() {
    echo "[INFO] Start to create ES official installation repo"

    if [ ! -f ${ELASTICSEARCH_REPO} ]; then
        touch ${ELASTICSEARCH_REPO}
    fi
    echo "[aops_elasticsearch]
name=Elasticsearch repository for 7.x packages
baseurl=https://artifacts.elastic.co/packages/7.x/yum
gpgcheck=1
gpgkey=https://artifacts.elastic.co/GPG-KEY-elasticsearch
enabled=1
autorefresh=1
type=rpm-md" >${ELASTICSEARCH_REPO}
  # create repo file failed
    if [ ! -f ${ELASTICSEARCH_REPO} ]; then
        echo "[ERROR] aops_elasticsearch.repo file creation failed!"
        echo "[INFO] Please confirm whether you have permission!"
        exit 1
    fi

    echo "[INFO] Create ES repo success"
}

function install_elasticsearch() {
    check_es_status
    create_es_repo
    echo "[INFO] Start to download and install elasticsearch"
    if rpm -q "elasticsearch" >/dev/null 2>&1; then
        echo "[INFO] Package elasticsearch is already installed"
    else
        # check repo
        es_repo=$(yum repolist | grep "aops_elasticsearch")
        if [ -z "${es_repo}" ]; then
        echo "[ERROR] Not found elasticsearch repo,please check config file in /etc/yum.repos.d"
        exit 1
        fi

        if yum install elasticsearch-7.14.0-1 -y; then
        echo "[INFO] Download and install elasticsearch successful"
        else
        echo "[ERROR] Install elasticsearch failed"
        exit 1
        fi
    fi
}

function install_mysql() {
    echo "[INFO] Start to download and install mysql"
    if rpm -q "mysql" >/dev/null 2>&1; then
        echo "[INFO] Package mysql-server is already installed"
    else
        if yum install mysql-server -y; then
        echo "[INFO] Download and install mysql successful"
        else
        echo "[ERROR] Install mysql failed"
        echo "[ERROR] Please check the files under the /etc/yum.repos.d/ is config correct"
        exit 1
        fi
    fi
}

function install_redis() {
    echo "[INFO] Start to download and install redis"
    if rpm -q "redis" >/dev/null 2>&1; then
        echo "[INFO] Package redis is already installed"
    else
        if yum install redis -y; then
        echo "[INFO] Download and install redis successful"
        else
        echo "[ERROR] Install redis failed"
        echo "[ERROR] Please check the files under the /etc/yum.repos.d/ is config correct"
        exit 1
        fi
    fi
}

function install_zookeeper() {
    echo "[INFO] Start to download and install zookeeper"
    if rpm -q "zookeeper" >/dev/null 2>&1; then
    echo "[INFO] Package zookeeper is already installed"
    else
      yum install zookeeper -y

      if [ $? -ne 0 ]; then
          echo "[ERROR] Install zookeeper failed"
          exit 1
      fi
    fi
}

function install_microservice(){
    echo "[INFO] Start to download and install aops service"

    yum install $@ -y

    if [ $? -ne 0 ]; then
        echo "[ERROR] An error occurred installing the $@"
        exit 1
    fi
    echo "[INFO] Microservice installation is complete"
}

function install_nginx() {
    echo "[INFO] Start to download and install nginx"
    if rpm -q "nginx" >/dev/null 2>&1; then
    echo "[INFO] Package nginx is already installed"
    else
      yum install nginx -y

      if [ $? -ne 0 ]; then
          echo "[ERROR] Install nginx failed"
          exit 1
      fi
    fi
}

function start_service(){
    echo "[INFO] Start $@"
    systemctl start $@
    echo "==========Service enabled state=========="
    systemctl show  --property ActiveState --property SubState  $@
    echo "==========End=========="
}

function init_service_database() {
    echo "[INFO] Start to init database $@"
    aops-cli database --init $@
}