import subprocess

from zeus.operation_service.app.core.framework.common.result_code import PluginResultCode
from zeus.operation_service.app.core.framework.plugins.base_plugin import BasePlugin


class Ping(BasePlugin):

    def run(self):
        task_vars = self._task_vars
        command = ['ping']
        if 'count' in task_vars:
            command.append('-c {}'.format(task_vars['count']))
        else:
            command.append('-c 4')
        if 'timeout' in task_vars:
            command.append('-w {}'.format(task_vars['timeout']))
        command.append(self._host['ip'])

        p = subprocess.Popen(command,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             shell=False
                             )

        p_result = p.stdout.read()
        result = dict()
        if "100% packet loss" in str(p_result):
            result["error_code"] = PluginResultCode.ERROR
            result["error_msg"] = "{} DOWN".format(self._host['ip'])
        else:
            result["error_code"] = PluginResultCode.SUCCESS
            result["error_msg"] = "{} UP".format(self._host['ip'])
        return result
