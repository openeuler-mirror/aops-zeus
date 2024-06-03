#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2023. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
import os
import inspect
import logging
import yaml


MICROSERVICE_CONFIG_DIR = os.path.join("/etc/aops/", "conf.d")
AOPS_GOLBAL_CONFIG = os.path.join("/etc/aops/", 'aops-config.yml')


class JsonObject:
    def __init__(self, data):
        """
        Initialize the JsonObject object.

        Args:
            data (dict): Data to be converted to a JsonObject.
        """
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, JsonObject(value))
            elif isinstance(value, list):
                setattr(self, key, [JsonObject(v) if isinstance(v, dict) else v for v in value])
            else:
                setattr(self, key, value)

    def __getattr__(self, attr):
        return self.__dict__.get(attr)

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return self.__str__()


class ConfigHandle:
    """Handles configuration parsing and management."""

    def __init__(self, config_name: str = None, default=None):
        """
        Initialize the Config object.

        Args:
            config_file (str): Path to the YAML configuration file.
            default (module): The default configuration module (optional).
        """
        self.config_obj = None
        self.config_center = None
        self.global_config_data = {}
        self.custom_config_data = {}
        self.custom_config_file_name = config_name

        self.json_config_data = self.get_default_config_to_dict(default) if default else {}
        self.parser = JsonObject(self.json_config_data)
        self.handle()

    @staticmethod
    def parse_yaml_from_yaml_file(config_file: str):
        """
        Parse the YAML configuration file and return the parsed data.

        Args:
            config_file (str): Path to the YAML configuration file.

        Returns:
            Any: Parsed data from the YAML configuration file.

        Raises:
            RuntimeError: If the configuration file does not exist or fails to load.
        """
        if not os.path.exists(config_file):
            raise RuntimeError(f"Configuration file does not exist: {config_file}")
        try:
            with open(config_file, 'r') as file:
                return yaml.safe_load(file) or dict()

        except IOError:
            raise RuntimeError(f"Failed to load the configuration file: {config_file}")

        except yaml.YAMLError:
            raise RuntimeError(f"Failed to parse the configuration file: {config_file}")

    @staticmethod
    def get_default_config_to_dict(default_config_module):
        """
        Convert variables defined in a default configuration module to a dictionary.

        Args:
            default_config_module (module): The default configuration module.

        Returns:
            dict: Dictionary containing the variables and their values defined in the default configuration module.
        """
        default_config_dict = {}

        if default_config_module is None:
            return default_config_dict

        for name, value in inspect.getmembers(default_config_module):
            if not name.startswith("__") and not inspect.ismodule(value):
                default_config_dict[name] = value
        return default_config_dict

    def _parse_global_config_data(self, data: dict):

        if data:
            data.update(
                {
                    **data.pop("infrastructure", {}),
                    **data.pop("services", {}),
                }
            )
            return data
        return {"include": MICROSERVICE_CONFIG_DIR}

    def handle(self):
        """
        Handle configuration loading and parsing.

        Raises:
            RuntimeError: If there's an error parsing or loading configuration files.
        """

        # Parse global configuration
        global_config_data = self.parse_yaml_from_yaml_file(AOPS_GOLBAL_CONFIG)
        self.json_config_data.update(self._parse_global_config_data(global_config_data))
        if not self.custom_config_file_name:
            self.parser = JsonObject(self.json_config_data)
            return
        custom_config_path = f"{self.json_config_data.get('include')}/{self.custom_config_file_name}.yml"
        if not os.path.exists(custom_config_path):
            self.parser = JsonObject(self.json_config_data)
            return

        self.custom_config_data = self.parse_yaml_from_yaml_file(custom_config_path)
        for field, value in self.custom_config_data.items():
            if field in self.json_config_data and value is not None:
                self.json_config_data[field] = value
            elif field not in self.json_config_data:
                self.json_config_data[field] = value

        self.parser = JsonObject(self.json_config_data)

    def reload(self):
        """Reload configuration."""
        self.parser = JsonObject(self.json_config_data)

    def is_valid_yaml(self, yaml_str: str) -> bool:
        """
        Check the correctness of yaml format.

        Args:
            yaml_str (str): yaml string

        Returns:
            bool: Returns true if the yaml format is correct, otherwise returns false.
        """
        try:
            yaml.safe_load(yaml_str)
            return True
        except yaml.YAMLError as e:
            logging.warning(f"Wrong yaml data: {e}")
            return False

    def __str__(self) -> str:
        """
        Return a string representation of the parsed configuration.

        Returns:
            str: String representation of the parsed configuration.
        """
        return str(JsonObject(self.json_config_data))
