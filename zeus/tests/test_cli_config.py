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
Unit tests for zeus.cli.config.

The module provides the ``config`` click command and a few pure helpers
(``is_valid_port``, ``is_valid_host``, ``set_zookeeper_config_node``,
``read_config_data``). The kazoo dependency is stubbed so the module can be
imported without the full runtime stack, and the command itself is exercised
through the click CLI runner with the ZooKeeper client mocked.
"""
import importlib.util
import os
import sys
import types
import unittest
from unittest import mock

from click.testing import CliRunner

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
TARGET_FILE = os.path.join(REPO_ROOT, "zeus", "cli", "config.py")
MODULE_NAME = "aops_zeus_test_cli_config"


def _install_stub(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_module(name, file_path):
    spec = importlib.util.spec_from_file_location(name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _stub_external_dependencies():
    # kazoo is not required for the tests; provide a minimal stand-in.
    kazoo_client = _install_stub("kazoo.client", KazooClient=mock.MagicMock())
    kazoo_exceptions = _install_stub("kazoo.exceptions", KazooException=type("KazooException", (Exception,), {}))
    kazoo = _install_stub("kazoo")
    kazoo.client = kazoo_client
    kazoo.exceptions = kazoo_exceptions


_stub_external_dependencies()
config_module = _load_module(MODULE_NAME, TARGET_FILE)


class IsValidPortTestCase(unittest.TestCase):
    def test_valid_boundary_ports(self):
        self.assertTrue(config_module.is_valid_port(0))
        self.assertTrue(config_module.is_valid_port(1))
        self.assertTrue(config_module.is_valid_port(65535))

    def test_out_of_range_ports(self):
        self.assertFalse(config_module.is_valid_port(-1))
        self.assertFalse(config_module.is_valid_port(65536))

    def test_non_integer_rejected(self):
        self.assertFalse(config_module.is_valid_port("2181"))
        self.assertFalse(config_module.is_valid_port(2181.5))
        self.assertFalse(config_module.is_valid_port(None))


class IsValidHostTestCase(unittest.TestCase):
    def test_valid_ipv4(self):
        for ip in ("127.0.0.1", "192.168.0.100", "10.0.0.1", "255.255.255.255", "0.0.0.0"):
            self.assertTrue(config_module.is_valid_host(ip))

    def test_valid_ipv6(self):
        self.assertTrue(config_module.is_valid_host("::1"))

    def test_invalid_hosts(self):
        for ip in ("192.168.0.256", "192.168.0", "abc", "", "1.2.3.4.5"):
            self.assertFalse(config_module.is_valid_host(ip))


class SetZookeeperConfigNodeTestCase(unittest.TestCase):
    def _client(self, exists):
        client = mock.MagicMock()
        client.exists.return_value = exists
        return client

    def test_existing_node_is_updated(self):
        client = self._client(exists=True)
        config_module.set_zookeeper_config_node(client, "/config/node", b"data")
        client.set.assert_called_once_with("/config/node", b"data")
        client.create.assert_not_called()

    def test_missing_node_is_created_with_makepath(self):
        client = self._client(exists=False)
        config_module.set_zookeeper_config_node(client, "/config/node", b"data")
        client.create.assert_called_once_with("/config/node", b"data", makepath=True)
        client.set.assert_not_called()


class ReadConfigDataTestCase(unittest.TestCase):
    def test_reads_file_content(self):
        with mock.patch("builtins.open", mock.mock_open(read_data=b"config-content")):
            self.assertEqual(config_module.read_config_data("/some/path"), b"config-content")

    def test_returns_none_on_oserror(self):
        with mock.patch("builtins.open", side_effect=OSError("no such file")):
            self.assertIsNone(config_module.read_config_data("/missing/path"))


class ConfigCommandTestCase(unittest.TestCase):
    """Exercise the ``config`` click command through the CLI runner."""

    def setUp(self):
        self.runner = CliRunner()
        self.config_file = os.path.join(REPO_ROOT, "README.md")

    def _invoke(self, *args, zk_start_side_effect=None, zk_stop_side_effect=None):
        with mock.patch.object(config_module, "KazooClient") as zk_class:
            instance = zk_class.return_value
            if zk_start_side_effect is not None:
                instance.start.side_effect = zk_start_side_effect
            if zk_stop_side_effect is not None:
                instance.stop.side_effect = zk_stop_side_effect
            result = self.runner.invoke(config_module.config, list(args))
        return result, zk_class

    def test_no_action_specified_exits_with_error(self):
        result, zk_class = self._invoke("--host", "127.0.0.1", "--file", self.config_file)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("No action specified", result.output)
        zk_class.assert_not_called()

    def test_init_and_update_together_exits_with_error(self):
        result, _ = self._invoke("--init", "--update", "--host", "127.0.0.1", "--file", self.config_file)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Cannot use --init and --update together", result.output)

    def test_invalid_host_exits_with_error(self):
        result, zk_class = self._invoke("--init", "--host", "not-a-host", "--file", self.config_file)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("not a valid ip address", result.output)
        zk_class.assert_not_called()

    def test_invalid_port_exits_with_error(self):
        result, zk_class = self._invoke("--init", "--host", "127.0.0.1", "--port", "99999", "--file", self.config_file)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("not a valid port", result.output)
        zk_class.assert_not_called()

    def test_missing_config_file_exits_with_error(self):
        result, zk_class = self._invoke(
            "--init", "--host", "127.0.0.1", "--file", os.path.join(REPO_ROOT, "no-such-file.yml")
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Failed to load config file", result.output)
        zk_class.assert_not_called()

    def test_init_creates_new_node(self):
        with mock.patch.object(config_module, "KazooClient") as zk_class:
            zk_class.return_value.exists.return_value = False
            result = self.runner.invoke(
                config_module.config, ["--init", "--host", "127.0.0.1", "--file", self.config_file]
            )
        self.assertEqual(result.exit_code, 0, msg=result.output)
        instance = zk_class.return_value
        instance.start.assert_called_once()
        instance.stop.assert_called_once()
        # node does not exist -> create is used with makepath
        instance.create.assert_called_once()
        args, kwargs = instance.create.call_args
        self.assertEqual(args[0], "/config/global_config")
        self.assertTrue(kwargs.get("makepath"))

    def test_update_sets_existing_node(self):
        result, zk_class = self._invoke("--update", "--host", "127.0.0.1", "--file", self.config_file)
        self.assertEqual(result.exit_code, 0, msg=result.output)
        instance = zk_class.return_value
        instance.exists.return_value = True
        instance.set.assert_called_once()
        args, _ = instance.set.call_args
        self.assertEqual(args[0], "/config/global_config")

    def test_custom_node_path_is_respected(self):
        with mock.patch.object(config_module, "KazooClient") as zk_class:
            zk_class.return_value.exists.return_value = False
            result = self.runner.invoke(
                config_module.config,
                ["--init", "--host", "127.0.0.1", "--node", "my_node", "--file", self.config_file],
            )
        self.assertEqual(result.exit_code, 0, msg=result.output)
        instance = zk_class.return_value
        args, _ = instance.create.call_args
        self.assertEqual(args[0], "/config/my_node")

    def test_zookeeper_error_exits_with_error(self):
        from kazoo.exceptions import KazooException

        result, _ = self._invoke(
            "--init",
            "--host",
            "127.0.0.1",
            "--file",
            self.config_file,
            zk_start_side_effect=KazooException("connection refused"),
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Failed to set data in a configuration node", result.output)


if __name__ == "__main__":
    unittest.main()
