# 一、一键化部署介绍

Aops服务一键化部署采用docker容器技术，搭配docker-compose容器编排，简化部署难度，实现一键启动和暂停。

# 二、环境要求

建议使用2台openEuler 24.03-LTS及以上机器完成部署（单台机器内存8G+），具体用途及部署方案如下：

- 机器A用于部署mysql、elasticsearch、kafka、redis、prometheus等，主要提供数据服务支持；
- 机器B用于部署A-Ops服务端，提供业务功能支持。部署A-Ops前端服务，提供展示、操作；

| 机器编号 | 配置IP      | 部署服务                                     |
| -------- | ----------- | -------------------------------------------- |
| 机器A    | 192.168.1.1 | mysql elasticsearch redis kafka prometheus   |
| 机器B    | 192.168.1.2 | aops-zeus aops-diana aops-apollo aops-hermes |

# 三、配置环境部署

## 1. 关闭机器A防火墙

```shell
systemctl stop firewalld
systemctl disable firewalld
systemctl status firewalld
```

## 2. 安装docker docker-compose

```shell
dnf install docker docker-compose
# 设置docker开机启动
systemctl enable docker
```

## 3. 安装aops-vulcanus aops-tools

```shell
dnf install aops-vulcanus aops-tools
```

> **说明：安装aops相关组件需要配置[EPOL源](https://dl-cdn.openeuler.openatom.cn/openEuler-24.03-LTS-SP1/EPOL/)。**

## 4. 执行一键化部署

- 执行部署脚本

```shell
cd /opt/aops/scripts/deploy/container
# 执行run.sh部署脚本
bash run.sh
```

> 进入交互式命令行
>
> ```shell
> 1. Build the docker container (build).
> 2. Start the container orchestration service (start-service/start-env).
> 3. Stop all container services (stop-service/stop-env).
> run.sh: line 74: read: `Enter to exit the operation (Q/q).': not a valid identifier
> Select an operation procedure to continue:
> 
> ```
>
> **build**: 部署基础服务（mysql、kafka等）不需要执行build操作
>
> **start-service**: 启动A-Ops服务及前端应用
>
> **start-env**: 启动基础服务，包括mysql、redis、kafka等
>
> **stop-service**: 停止A-Ops服务及前端应用
>
> **stop-env**: 停止基础服务（数据会依然保留）
>
> **Q/q**: 退出命令交互模式

- 部署A-Ops服务端

```shell
# 切换在机器B上执行部署脚本
cd /opt/aops/scripts/deploy/container
bash run.sh
# 交互式命令中执行start-service
```

- 更改服务配置文件

> **注意：当A-Ops服务和基础服务在同一台机器上部署时，则无需调整配置文件即可使用。若部署方案与本文档中类似（机器A、B），则需要将所有的配置文件中连接基础服务的配置项更改为机器A的ip**
>
> **默认的mysql连接字符串中使用无密码模式，基础服务的mysql配置了默认密码“123456”，视具体情况调整**

```shell
# 调整 apollo.ini diana.ini zeus.ini配置文件中连接mysql、elasticsearch、kafka、redis的ip地址
cd /etc/aops/
```

- **FAQ**

​    **1. elasticsearch基础服务无法正常启动**

查看/opt/es文件夹的权限，默认权限需要调整为777，可执行 "chmod -R 777 /opt/es" 。

​    **2. prometheus 基础服务无法正常启动**

查看/etc/prometheus目录下是否存在prometheus.yml配置文件，如果不存在，请添加配置文件。
