import copy
import queue
import timeit
from abc import ABCMeta, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from zeus.operation_service.app.core.framework.common.result_code import PluginResultCode, WorkFlowResultCode
from zeus.operation_service.app.core.framework.workflow.job import Job
from zeus.operation_service.app.core.framework.workflow.task_parser import TaskParser
from zeus.operation_service.app.core.framework.workflow.work_node import WorkNode
from zeus.operation_service.app.core.framework.workflow.workflow_exception import WorkFlowException
from vulcanus.log.log import LOGGER


class WorkFlow:
    __metaclass__ = ABCMeta

    def __init__(self, task_file, task_param):
        self._task_file = task_file
        self.task_name = task_param.get("task_name", task_file)
        self.task_id = task_param.get('task_id')
        self._params = dict()
        self._jobs_map = dict()
        self._hosts_map = dict()
        self.worknode_found = dict()
        self.worknode_map = dict()
        self._waiting_queue = queue.Queue()
        self.result = queue.Queue()
        self._get_jobs_number = 0
        self._jobs_number = 0
        self.max_work_jobs = task_param.get("max_work_jobs", 5)
        self.timeout = task_param.get("timeout", 900)
        self.status = WorkFlowResultCode.NORMAL.code

    def parse(self):
        task_parser = TaskParser(self._task_file)
        if not task_parser.parse():
            LOGGER.error("parse workflow failed")
            raise WorkFlowException(WorkFlowResultCode.ERR_WORKFLOW_PARSE)
        self._params = task_parser.params()

        hosts_json = task_parser.hosts()
        for host_json in hosts_json:
            host_name = host_json.get("hostname")
            if host_name is None or host_name == "":
                LOGGER.error(f"workflow host name: {host_name}")
                raise WorkFlowException(WorkFlowResultCode.ERR_WORKFLOW_HOST_NAME)
            self._hosts_map[host_name] = host_json

        jobs_json = task_parser.jobs()
        for job_json in jobs_json:
            job_name = job_json.get("name")
            if job_name is None or job_name == "":
                LOGGER.error(f"workflow job name: {job_name}")
                raise WorkFlowException(WorkFlowResultCode.ERR_WORKFLOW_JOB_NAME)
            self._jobs_map[job_name] = Job(job_json, self._hosts_map)

    # 根据Jobs_map生成任务之间的依赖关系，初始化workflow
    def init_workflow(self):
        for job_name, job in self._jobs_map.items():
            job_start_name = job_name + ":start"
            job_end_name = job_name + ":end"
            self.worknode_map[job_start_name] = WorkNode(job_start_name, self.task_id, None)
            self.worknode_map[job_end_name] = WorkNode(job_end_name, self.task_id, None)
            steps = job.get_steps()
            if len(steps) == 0:
                LOGGER.error("steps is null")
                raise WorkFlowException(WorkFlowResultCode.ERR_WORKFLOW_STEPS_NULL)
            for _, step in steps.items():
                job_step_name = job_name + ":" + step.name
                self.worknode_map[job_step_name] = WorkNode(job_step_name, self.task_id, step)

        for job_name, job in self._jobs_map.items():

            # 建立job之间的依赖
            self._generate_jobs_dependency(job_name, job.get_dependency())
            for _, step in job.get_steps().items():
                self._generate_step_dependency(job_name, step)

            # 建立task：end的依赖关系
            self._generate_job_end_dependency(job_name, job_name + ":start")
        self._jobs_number = len(self.worknode_map)
        for worknode_name, worknode in self.worknode_map.items():
            LOGGER.info(
                f"{worknode_name}, next worknodes: {worknode.next_nodes}, dependency count: {worknode.dependency_account.get_value()}")

    def _generate_jobs_dependency(self, job_name, depend_jobs):
        job_start_name = job_name + ":start"
        self.worknode_map[job_start_name].dependency_account.add(len(depend_jobs))
        for depend_job in depend_jobs:
            self.worknode_map[depend_job + ":end"].add_next_node(self.worknode_map[job_start_name])

    def _generate_step_dependency(self, job_name, step):
        job_step_name = job_name + ":" + step.name
        job_start_name = job_name + ":start"
        if step.have_dependency():

            # 是否依赖本身job的其他step
            depend_self_task_step = False
            step_depends = step.get_dependency()
            for step_depend in step_depends:
                self.worknode_map[job_step_name].dependency_account.increment()
                if len(step_depend.split(":")) == 1:
                    self.worknode_map[job_name + ":" + step_depend].add_next_node(
                        self.worknode_map[job_step_name])
                    depend_self_task_step = True
                else:
                    self.worknode_map[step_depend].add_next_node(self.worknode_map[job_step_name])

            # 如果不依赖自身的task的其他step，就与task：start建立依赖
            if not depend_self_task_step:
                self.worknode_map[job_step_name].dependency_account.increment()
                self.worknode_map[job_start_name].add_next_node(self.worknode_map[job_step_name])

        # 如果没有依赖，则直接与task：start建立依赖
        else:
            self.worknode_map[job_step_name].dependency_account.increment()
            self.worknode_map[job_start_name].add_next_node(self.worknode_map[job_step_name])

    def _generate_job_end_dependency(self, job_name, worknode_name):
        job_end_name = job_name + ":end"
        if worknode_name == job_end_name:
            return

        have_self_task_step = False
        for depend_worknode in self.worknode_map[worknode_name].next_nodes:
            if depend_worknode.name not in self.worknode_found.keys() and depend_worknode.name.split(":")[
                -2] == job_name:
                have_self_task_step = True
                self.worknode_found[depend_worknode.name] = 1
                self._generate_job_end_dependency(job_name, depend_worknode.name)

        if not have_self_task_step:
            self.worknode_map[job_end_name].dependency_account.increment()
            self.worknode_map[worknode_name].add_next_node(self.worknode_map[job_end_name])

    def validate_workflow(self):
        # 可能存在一开始就有依赖的情况
        if not self._waiting_queue:
            LOGGER.error(f"{self._waiting_queue} is null")
            return False
        work_node_back = queue.Queue()
        queue_size = self._waiting_queue.qsize()
        waitting_queue = queue.Queue()
        checked_node = dict()
        for i in range(0, queue_size):
            work_node = self._waiting_queue.get()
            waitting_queue.put(work_node)
            self._waiting_queue.put(work_node)
        while not waitting_queue.empty():
            work_node = waitting_queue.get()
            checked_node[work_node.name] = True
            for next_work_node in work_node.next_nodes:
                if checked_node.get(next_work_node.name):
                    LOGGER.error(f"{next_work_node.name} get circle")
                    return False
                work_node_back.put(next_work_node)
                next_work_node.dependency_account.decrease()
                if next_work_node.dependency_account.get_value() == 0:
                    waitting_queue.put(next_work_node)
        # 可能存在单独闭环的job，以搜索过的work_node节点判断，如果存在未搜索过的节点，则存在单独闭环的job
        for work_node_name in self.worknode_map.keys():
            if work_node_name not in checked_node.keys():
                LOGGER.error(f"{work_node_name} not in flow")
                return False
        self.rollback_dependency_count(work_node_back)
        return True

    @staticmethod
    def rollback_dependency_count(work_node_queue: queue.Queue):
        while not work_node_queue.empty():
            work_node = work_node_queue.get()
            work_node.dependency_account.increment()

    def init_queue(self):
        for _, worknode in self.worknode_map.items():
            if worknode.dependency_account.get_value() == 0:
                LOGGER.warning(f"queue_init: {worknode.name}")
                self._waiting_queue.put(worknode)

    def _start_before(self):
        """workflow开始执行前操作"""
        pass

    def _handle_error_result(self, result_msg):
        """处理work node错误"""
        pass

    def _handle_exception(self, exception):
        """处理workflow抛出的异常"""
        raise exception

    def _success_after(self):
        """任务完成后的操作，子类实现"""
        pass

    @abstractmethod
    def _clean_env(self):
        """清理workflow环境，子类必须实现"""
        pass

    def _handle_result(self, result_msg):
        work_node_name = result_msg["work_node_name"]
        work_node = self.worknode_map[work_node_name]
        if result_msg["result_code"] == PluginResultCode.PRE_DEPENDENCY_ERROR:
            work_node.set_status('failed')

            # 前置依赖报错，设置任务报错，且报错原因设置为前置依赖的报错原因
            for next_work_node in work_node.next_nodes:
                next_work_node.pre_status.set_value(-1)
                next_work_node.status_reason.set_value(work_node.status_reason.value)
        elif result_msg["result_code"] == PluginResultCode.SUCCESS or (result_msg["result_code"] != PluginResultCode.SUCCESS and work_node.step.ignore_result):
            work_node.set_status('success')
            work_node.status_reason.set_value('ok')
            LOGGER.warning(f"work node: {work_node_name} successfully")
        else:
            work_node.set_status('failed')
            work_node.status_reason.set_value(result_msg["errors_info"])
            self.status = WorkFlowResultCode.ERR_WORKFLOW_EXECUTE.code

            # 设置依赖项pre_status为-1
            for next_work_node in work_node.next_nodes:
                next_work_node.pre_status.set_value(-1)
                next_work_node.status_reason.set_value(work_node_name + ' ' + str(result_msg["errors_info"]))
            self._handle_error_result(result_msg)
            LOGGER.warning(f"{work_node_name} execute failed, error: {result_msg['errors_info']}")

        # 获取下一批可执行的work nodes
        next_free_work_nodes = work_node.get_next_free_nodes()
        if len(next_free_work_nodes) == 0:
            return result_msg
        for next_work_node in next_free_work_nodes:
            LOGGER.warning(f"put next work nodes: {next_work_node.name}")
            self._waiting_queue.put(next_work_node)
        return result_msg

    # 运行前的准备动作
    def init(self):
        self.parse()
        LOGGER.info(f"{self.task_name} parse successfully")
        self.init_workflow()
        LOGGER.info(f"{self.task_name} workflow init successfully")
        self.init_queue()
        LOGGER.info(f"{self.task_name} queue init successfully")
        if not self.validate_workflow():
            raise WorkFlowException(WorkFlowResultCode.ERR_WORKFLOW_CIRCLE)
        LOGGER.info("workflow check successfully")

    def start(self):
        work_pool = ThreadPoolExecutor(max_workers=self.max_work_jobs)
        start_time = timeit.default_timer()
        all_tasks = list()
        try:
            while True:
                timeout_time = self.timeout - (timeit.default_timer() - start_time)
                if timeout_time < 0:
                    LOGGER.error(f"{self.task_name} execute timeout, begin to shutdown pool")
                    raise WorkFlowException(WorkFlowResultCode.ERR_WORKFLOW_TIMEOUT)
                work_node = self._waiting_queue.get(timeout=timeout_time)
                self._get_jobs_number += 1
                LOGGER.warning(
                    f"get work_node: {work_node.name}, get jobs number: {self._get_jobs_number}, all jobs number: {self._jobs_number}")
                all_tasks.append(work_pool.submit(work_node.work, self._handle_result))
                if self._get_jobs_number == self._jobs_number:
                    LOGGER.warning("get all jobs, wait for all jobs result")
                    timeout_time = self.timeout - (timeit.default_timer() - start_time)
                    for task in as_completed(all_tasks, timeout=timeout_time):
                        self.result.put(task.result(timeout=timeout_time))
                    LOGGER.warning(f"{self.task_name} execute successfully")
                    break
        finally:
            LOGGER.warning(f"{self.task_name} shutdown pool:{id(work_pool)}")
            work_pool.shutdown(wait=False)

    def get_result_from_queue(self, worknode_name):
        my_list = list(self.result.queue)
        for worknode in my_list:
            if worknode['work_node_name'] == worknode_name:
                return worknode
        return None
