import json
import logging
import os.path
import sys
sys.path.append(os.getcwd())

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(filename='/opt/.agent/agent.log', level=logging.DEBUG, format=LOG_FORMAT)
logger = logging.getLogger()


def main():
    real_path = os.path.realpath(sys.argv[1])
    if real_path.startswith("/opt/.agent"):
        with open(real_path, 'r') as config_f:
            config_json = json.load(config_f)
        task_type = config_json['task_type']
        execute_task(task_type, config_json)


def get_task_executor():
    from task_executor_factory.health_check_executor import HealthCheckExecutor
    from task_executor_factory.data_collect_executor import DataCollectExecutor
    from task_executor_factory.security_manage_executor import SecurityManageExecutor
    return {
        "HEALTH_CHECK": HealthCheckExecutor,
        "DATA_COLLECT": DataCollectExecutor,
        "SECURITY_MANAGE": SecurityManageExecutor
    }


def execute_task(task_type, config_json):
    return get_task_executor().get(task_type)(config_json).start()


if __name__ == '__main__':
    main()
