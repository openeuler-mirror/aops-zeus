from zeus.operation_service.app.core.framework.common.common_init import init_host_map, init_dependency


class Step:
    def __init__(self, job_name, step_json, host_map):
        self.job_name = job_name
        self.name = step_json.get("name")
        self._hosts_map = init_host_map(step_json, host_map)
        self._module = step_json.get("module")
        self._dependency = init_dependency(step_json)
        self.essential = step_json.get('essential', "False")
        self.ignore_result = step_json.get('ignore_result', "False")
        self.is_depend_self_task = self.is_depend_self_task_other_step()

    def get_module(self):
        return self._module

    def get_hosts_map(self):
        return self._hosts_map

    def get_dependency(self):
        return self._dependency

    def have_dependency(self):
        if len(self._dependency) > 0:
            return True
        return False

    def is_depend_self_task_other_step(self):
        for depend_step in self._dependency:
            depend_step_name = depend_step.split(":")
            depend_step_name_len = len(depend_step_name)
            if depend_step_name_len == 1:
                return True
        return False
