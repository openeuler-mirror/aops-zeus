import copy
import timeit
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict

from zeus.operation_service.app.core.framework.Atomic.atomic_integer import AtomicInteger
from zeus.operation_service.app.core.framework.common.result_code import PluginResultCode
from zeus.operation_service.app.core.framework.process.task_executor import TaskExecutor
from vulcanus.log.log import LOGGER

class TaskDispatcher:
    def __init__(self, context: Dict):
        self._todo_hosts = copy.deepcopy(context["hosts"])
        self._todo_task = context["task"]
        self._task_id = context["task_id"]
        self._batch_size = context.get("batch_size", 5)
        self._timeout = context.get("timeout", 300)
        self._finished_count = 0
        self._host_num = len(self._todo_hosts)
        self._working_prc_count = AtomicInteger(0)
        self._callback = context["callback"]
        self._work_node_name = context["work_node_name"]
        self._stat = dict()
        self._stat['failed'] = list()
        self._stat['success'] = list()
        self._results = dict()

    def run(self):
        work_pool = ThreadPoolExecutor(max_workers=self._batch_size)
        start_time = timeit.default_timer()
        all_tasks = list()
        try:
            while True:
                if not self._todo_hosts:
                    timeout_time = self._timeout - (timeit.default_timer() - start_time)
                    for task in as_completed(all_tasks, timeout=timeout_time):
                        self.handle_result(task.result(timeout=timeout_time))
                    break

                if len(self._todo_hosts) > 0:
                    host = self._todo_hosts.pop()
                    # 适配，zeus不支持免密登录
                    host['passwordless'] = False
                    self._todo_task['task_metadata'] = dict()
                    self._todo_task['task_metadata']['task_id'] = self._task_id
                    task_executor = TaskExecutor(host, self._todo_task)
                    all_tasks.append(work_pool.submit(TaskExecutor.run, task_executor))
        except Exception as e:
            LOGGER.error(traceback.print_exc())
            self._results = {
                'work_node_name': self._work_node_name,
                'result_code': PluginResultCode.FAILED,
                'errors_info': e
            }
            self._callback(self._results)
        finally:
            LOGGER.warning(f"{self._task_id} shutdown pool:{id(work_pool)}")
            work_pool.shutdown(wait=False)
        return self._results

    def handle_result(self, exec_result):
        self._working_prc_count.decrease()
        LOGGER.info("========================")
        LOGGER.info(f"work_node: {self._work_node_name}")
        LOGGER.info(f"{exec_result.host['ip']}: {exec_result.task['name']}")
        LOGGER.info(exec_result.result)
        LOGGER.info("========================")
        self._finished_count += 1

        # 统计结果
        if exec_result.result['error_code'] == PluginResultCode.SUCCESS:
            self._stat['success'].append(
                {
                    'host': exec_result.host['ip'],
                    'msg': exec_result.result['error_msg'],
                    'code': exec_result.result['error_code']
                }
            )
        else:
            self._stat['failed'].append(
                {
                    'host': exec_result.host['ip'],
                    'msg': exec_result.result['error_msg'],
                    'code': exec_result.result['error_code']
                }
            )
        if self._finished_count == self._host_num:
            self._results = self._statistic_execution_result()
            self._callback(self._results)

    def _statistic_execution_result(self):
        LOGGER.info(f"start to collect statistics on execution results: wokr_node_name: {self._work_node_name}")
        result = dict()
        result['work_node_name'] = self._work_node_name
        result['errors_info'] = dict()
        if self._host_num == len(self._stat['success']):
            result['result_code'] = PluginResultCode.SUCCESS
        elif len(self._stat['success']) > 0:
            result['result_code'] = PluginResultCode.PARTIAL_PASSED
        else:
            result['result_code'] = PluginResultCode.FAILED

        for item in self._stat['failed']:
            result['errors_info'][item['host']] = item['msg']
        for item in self._stat['success']:
            result['errors_info'][item['host']] = item['msg']

        return result
