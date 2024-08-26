from zeus.operation_service.app.core.framework.common.common_init import init_host_map, init_dependency
from zeus.operation_service.app.core.framework.workflow.step import Step


class Job:
    """"job结构"""

    def __init__(self, job_json, hosts_map):
        self.name = job_json.get("name")
        self._hosts_map = init_host_map(job_json, hosts_map)
        self._dependency = init_dependency(job_json)
        self._steps_map = Job._init_steps(job_json, self.name, self._hosts_map)

    def get_steps(self):
        return self._steps_map

    def have_dependency(self):
        if len(self._dependency) > 0:
            return True
        return False

    def get_dependency(self):
        return self._dependency


    @staticmethod
    def _init_steps(job_json, job_name, host_map):
        steps = {}
        steps_list = job_json.get("steps")
        for step_json in steps_list:
            step = Step(job_name, step_json, host_map)
            steps[step.name] = step
        return steps

