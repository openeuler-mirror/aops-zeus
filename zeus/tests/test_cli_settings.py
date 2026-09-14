#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
"""
Unit tests for zeus.cli.settings (configuration parsing logic).

The module provides the ``JsonObject`` attribute-style view of parsed YAML
data and the ``ConfigHandle`` which loads the global A-Ops configuration and
optionally merges a per-service custom configuration. File-based behaviour
is exercised against temporary YAML files with the module-level path
constants patched.
"""
import importlib.util
import os
import tempfile
import types
import unittest
from unittest import mock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
TARGET_FILE = os.path.join(REPO_ROOT, "zeus", "cli", "settings.py")
MODULE_NAME = "aops_zeus_test_cli_settings"


def _load_module(name, file_path):
    spec = importlib.util.spec_from_file_location(name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys_modules[name] = module
    spec.loader.exec_module(module)
    return module


import sys  # noqa: E402

sys_modules = sys.modules
settings = _load_module(MODULE_NAME, TARGET_FILE)


def _write_yaml(directory, file_name, content):
    path = os.path.join(directory, file_name)
    with open(path, "w") as handle:
        handle.write(content)
    return path


class JsonObjectTestCase(unittest.TestCase):
    def test_scalar_values(self):
        obj = settings.JsonObject({"host": "127.0.0.1", "port": 2181, "debug": True})
        self.assertEqual(obj.host, "127.0.0.1")
        self.assertEqual(obj.port, 2181)
        self.assertIs(obj.debug, True)

    def test_nested_dict_becomes_json_object(self):
        obj = settings.JsonObject({"redis": {"host": "10.0.0.1", "port": 6379}})
        self.assertIsInstance(obj.redis, settings.JsonObject)
        self.assertEqual(obj.redis.host, "10.0.0.1")
        self.assertEqual(obj.redis.port, 6379)

    def test_dash_in_key_converted_to_underscore(self):
        obj = settings.JsonObject({"max-retries": 3, "db-name": "aops"})
        self.assertEqual(obj.max_retries, 3)
        self.assertEqual(obj.db_name, "aops")

    def test_list_of_dicts_becomes_list_of_json_objects(self):
        obj = settings.JsonObject(
            {"services": [{"name": "host-information"}, {"name": "user-access"}]}
        )
        self.assertIsInstance(obj.services, list)
        self.assertEqual(len(obj.services), 2)
        self.assertIsInstance(obj.services[0], settings.JsonObject)
        self.assertEqual(obj.services[0].name, "host-information")
        self.assertEqual(obj.services[1].name, "user-access")

    def test_list_of_scalars_kept_as_is(self):
        obj = settings.JsonObject({"ports": [2181, 2182]})
        self.assertEqual(obj.ports, [2181, 2182])

    def test_mixed_list(self):
        obj = settings.JsonObject({"items": [{"a": 1}, "plain", 7]})
        self.assertIsInstance(obj.items[0], settings.JsonObject)
        self.assertEqual(obj.items[0].a, 1)
        self.assertEqual(obj.items[1], "plain")
        self.assertEqual(obj.items[2], 7)

    def test_missing_attribute_returns_none(self):
        obj = settings.JsonObject({"known": 1})
        self.assertIsNone(obj.unknown)

    def test_deeply_nested_structure(self):
        obj = settings.JsonObject({"a": {"b": {"c": [1, 2, 3]}}})
        self.assertEqual(obj.a.b.c, [1, 2, 3])

    def test_str_and_repr_show_dict_content(self):
        obj = settings.JsonObject({"host": "127.0.0.1"})
        self.assertIn("host", str(obj))
        self.assertIn("host", repr(obj))


class ParseYamlFromFileTestCase(unittest.TestCase):
    def test_missing_file_raises_runtime_error(self):
        with self.assertRaises(RuntimeError):
            settings.ConfigHandle.parse_yaml_from_yaml_file("/nonexistent/aops-config.yml")

    def test_valid_yaml_file_parsed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_yaml(tmpdir, "config.yml", "host: 127.0.0.1\nport: 2181\n")
            data = settings.ConfigHandle.parse_yaml_from_yaml_file(path)
            self.assertEqual(data, {"host": "127.0.0.1", "port": 2181})

    def test_empty_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_yaml(tmpdir, "empty.yml", "")
            self.assertEqual(settings.ConfigHandle.parse_yaml_from_yaml_file(path), {})

    def test_invalid_yaml_raises_runtime_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_yaml(tmpdir, "broken.yml", "key: [unclosed\n  bad indent: {")
            with self.assertRaises(RuntimeError):
                settings.ConfigHandle.parse_yaml_from_yaml_file(path)


class GetDefaultConfigToDictTestCase(unittest.TestCase):
    def test_none_returns_empty_dict(self):
        self.assertEqual(settings.ConfigHandle.get_default_config_to_dict(None), {})

    def test_public_members_extracted(self):
        module = types.ModuleType("fake_settings_module")
        module.HOST = "127.0.0.1"
        module.PORT = 2181

        class InnerClass:
            pass

        module.InnerClass = InnerClass
        setattr(module, "__secret", "hidden")

        result = settings.ConfigHandle.get_default_config_to_dict(module)
        self.assertEqual(result["HOST"], "127.0.0.1")
        self.assertEqual(result["PORT"], 2181)
        # classes are not modules, so they are included
        self.assertIs(result["InnerClass"], InnerClass)
        # dunders are excluded
        self.assertNotIn("__secret", result)

    def test_submodules_excluded(self):
        import yaml  # a real module to be excluded

        module = types.ModuleType("fake_settings_module")
        module.yaml = yaml
        module.VALUE = 1
        result = settings.ConfigHandle.get_default_config_to_dict(module)
        self.assertNotIn("yaml", result)
        self.assertEqual(result["VALUE"], 1)


class ParseGlobalConfigDataTestCase(unittest.TestCase):
    def setUp(self):
        # construct without touching the filesystem: bypass __init__
        self.handle = object.__new__(settings.ConfigHandle)
        # resolve the private helper by name to keep the source lint-clean
        self.parse_global = getattr(settings.ConfigHandle, "_parse_global_config_data")

    def test_empty_data_defaults_to_microservice_dir(self):
        result = self.parse_global(self.handle, None)
        self.assertEqual(result, {"include": settings.MICROSERVICE_CONFIG_DIR})

    def test_infrastructure_and_services_flattened(self):
        data = {
            "infrastructure": {"zookeeper": "127.0.0.1:2181"},
            "services": {"user_access": {"enabled": True}},
            "custom": "kept",
        }
        result = self.parse_global(self.handle, data)
        self.assertEqual(result["zookeeper"], "127.0.0.1:2181")
        self.assertTrue(result["user_access"]["enabled"])
        self.assertEqual(result["custom"], "kept")
        self.assertNotIn("infrastructure", result)
        self.assertNotIn("services", result)


class IsValidYamlTestCase(unittest.TestCase):
    def setUp(self):
        self.handle = object.__new__(settings.ConfigHandle)

    def test_valid_yaml(self):
        self.assertTrue(self.handle.is_valid_yaml("key: value"))
        self.assertTrue(self.handle.is_valid_yaml("a: 1\nb: 2"))

    def test_invalid_yaml(self):
        self.assertFalse(self.handle.is_valid_yaml("key: [unclosed"))


class ConfigHandleHandleTestCase(unittest.TestCase):
    """End-to-end parsing through ``handle()`` using temporary config files."""

    def _build_handle(self, tmpdir, global_content, config_name=None, custom_content=None):
        global_path = _write_yaml(tmpdir, "aops-config.yml", global_content)
        include_dir = os.path.join(tmpdir, "conf.d")
        os.makedirs(include_dir, exist_ok=True)
        if custom_content is not None and config_name:
            _write_yaml(include_dir, config_name + ".yml", custom_content)

        with mock.patch.object(settings, "AOPS_GOLBAL_CONFIG", global_path):
            handle = settings.ConfigHandle(config_name=config_name, default=None)
        return handle

    def test_global_config_flattened_into_parser(self):
        global_content = (
            "include: /etc/aops/conf.d\n"
            "infrastructure:\n"
            "  zookeeper: 127.0.0.1:2181\n"
            "services:\n"
            "  redis: 10.0.0.1:6379\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            handle = self._build_handle(tmpdir, global_content)
        self.assertEqual(handle.parser.zookeeper, "127.0.0.1:2181")
        self.assertEqual(handle.parser.redis, "10.0.0.1:6379")
        self.assertEqual(handle.parser.include, "/etc/aops/conf.d")
        self.assertIsNone(handle.parser.infrastructure)

    def test_custom_config_overrides_global_value(self):
        global_content = (
            "include: {}\n"
            "database: mysql-global\n"
            "zookeeper: 127.0.0.1:2181\n"
        ).format(os.path.join("{}", "conf.d"))
        with tempfile.TemporaryDirectory() as tmpdir:
            include_dir = os.path.join(tmpdir, "conf.d")
            os.makedirs(include_dir, exist_ok=True)
            global_content = global_content.format(tmpdir)
            handle = self._build_handle(
                tmpdir,
                global_content,
                config_name="zeus-user-access",
                custom_content="database: mysql-custom\nextra_field: added\n",
            )
        self.assertEqual(handle.parser.database, "mysql-custom")
        self.assertEqual(handle.parser.extra_field, "added")
        self.assertEqual(handle.parser.zookeeper, "127.0.0.1:2181")

    def test_custom_config_none_value_keeps_global(self):
        global_content = "include: {include_dir}\ndatabase: mysql-global\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            include_dir = os.path.join(tmpdir, "conf.d")
            os.makedirs(include_dir, exist_ok=True)
            handle = self._build_handle(
                tmpdir,
                global_content.format(include_dir=include_dir),
                config_name="zeus-user-access",
                custom_content="database: null\n",
            )
        self.assertEqual(handle.parser.database, "mysql-global")

    def test_missing_custom_config_file_keeps_global(self):
        global_content = "include: {include_dir}\ndatabase: mysql-global\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            include_dir = os.path.join(tmpdir, "conf.d")
            os.makedirs(include_dir, exist_ok=True)
            handle = self._build_handle(
                tmpdir,
                global_content.format(include_dir=include_dir),
                config_name="does-not-exist",
            )
        self.assertEqual(handle.parser.database, "mysql-global")

    def test_reload_rebuilds_parser(self):
        global_content = "zookeeper: 127.0.0.1:2181\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            handle = self._build_handle(tmpdir, global_content)
            original = handle.parser
            handle.reload()
        self.assertIsNot(handle.parser, original)
        self.assertEqual(handle.parser.zookeeper, "127.0.0.1:2181")


if __name__ == "__main__":
    unittest.main()
