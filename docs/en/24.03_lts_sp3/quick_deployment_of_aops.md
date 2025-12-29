# One-Click Deployment of A-Ops

One-click deployment of A-Ops is based on Docker and docker-compose to simply deployment and implement one-click start and stop.

## Environment Requirements

You are advised to use two or more machines with 8 GB or more memory running openEuler 22.03 LTS SP1 or later. Assume that the machines are host A and B.

- MySQL, Elasticsearch, Kafka, Redis, and Prometheus are deployed on host A, which provides data services.
- The A-Ops server and A-Ops frontend are deployed on host B to provide service functions as well as display and operations.

| Host | IP Address      | Services                                     |
| -------- | ----------- | -------------------------------------------- |
| Host A    | 192.168.1.1 | MySQL, Elasticsearch, Redis, Kafka, Prometheus   |
| Host B    | 192.168.1.2 | aops-zeus, aops-diana, aops-apollo, aops-hermes |

## Environment Configuration

### Disabling the Firewall on Host A

```shell
systemctl stop firewalld
systemctl disable firewalld
systemctl status firewalld
```

### Installing Docker and docker-compose

```shell
dnf install docker docker-compose
# Set Docker to start upon system startup.
systemctl enable docker
```

### Installing aops-vulcanus and aops-tools

```shell
dnf install aops-vulcanus aops-tools
```

### Perform One-Click Deployment

- Execute the deployment script.

```shell
cd /opt/aops/scripts/deploy/container
# Execute run.sh.
bash run.sh
```

> Enter the interactive CLI.
>
> ```console
> 1. Build the docker container (build).
> 2. Start the container orchestration service (start-service/start-env).
> 3. Stop all container services (stop-service/stop-env).
> run.sh: line 74: read: `Enter to exit the operation (Q/q).': not a valid identifier
> Select an operation procedure to continue:
> 
> ```
>
> **build**: Deployment of basic services (such as MySQL and Kafka) does not need the build operation.
>
> **start-service**: Start the service and frontend of A-Ops.
>
> **start-env**: Start basic service including MySQL, Redis, and Kafka.
>
> **stop-service**: Stop the service and frontend of A-Ops.
>
> **stop-env**: Stop basic services. The data is retained.
>
> **Q/q**: Exit the interactive CLI.

- Deploy the A-Ops server.

```shell
# Execute the deployment script on host B.
cd /opt/aops/scripts/deploy/container
bash run.sh
# Run start-service in the interactive CLI.
```

- Modify service configuration files.

> **Note: If the A-Ops service and basic services are deployed on the same host, you do not need to modify the configuration files. In this example, set the IP addresses for connecting to basic services to the IP address of host A in all configuration files.**
>
> **Password-free mode is used in the default MySQL connection string. The MySQL basic service is configured with the default password "123456". Change the configurations as required.**

```shell
# Modify the IP addresses for connecting to mysql, elasticsearch, kafka, and redis in apollo.ini, diana.ini, and zeus.ini.
cd /etc/aops/
```

- **FAQ**

**1. The Elasticsearch basic service cannot be started normally.**

Check whether the permission on the **/opt/es** directory is **777**. You can run `chmod -R 777 /opt/es` to modify the permission.

**2. The Prometheus basic service cannot be started normally.**

Check whether the configuration file **prometheus.yml** exists in **/etc/prometheus**. If not, create it.
