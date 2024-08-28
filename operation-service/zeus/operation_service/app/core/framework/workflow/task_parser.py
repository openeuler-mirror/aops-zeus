import os.path
import yaml
from yaml.parser import ParserError
from vulcanus.log.log import LOGGER


class TaskParser:
    def __init__(self, task_file):
        self._task_file = task_file
        self._task_json = dict()
        self._jobs_json = dict()
        self._task_name = ""
        self._params = dict()
        self._hosts = dict()

    def parse(self):
        try:
            if os.path.isfile(self._task_file):
                with open(self._task_file, "r", encoding="utf-8") as yml_file:
                    self._task_json = yaml.safe_load(yml_file)
            else:
                self._task_json = yaml.safe_load(self._task_file)
        except ParserError as err:
            LOGGER.error(f"Not well-formed {self._task_json}: {str(err)}!")
            return False
        except Exception as err:
            LOGGER.error(f"Failed to read {self._task_json}: {str(err)}!")
            return False
        if self._task_json is None:
            LOGGER.error(f"No content in {self._task_json}!")
            return False
        # LOGGER.info(f"TaskParser--parse: {self._task_json}")
        self._jobs_json = self._task_json.get("jobs")
        self._task_name = self._task_json.get("name")
        self._params = self._task_json.get("params")
        self._hosts = self._task_json.get("hosts")
        return True

    def jobs(self):
        """返回jobs的json"""
        return self._jobs_json

    def task_name(self):
        """返回task名字"""
        return self._task_name

    def params(self):
        """返回task的全局参数"""
        return self._params

    def hosts(self):
        """返回hosts的json"""
        return self._hosts
