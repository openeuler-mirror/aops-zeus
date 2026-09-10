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
Unit tests for zeus.user_access_service.app.constant.

The module derives the celery ``BACKEND`` and ``BROKER`` redis URLs from the
service configuration. The configuration module is stubbed so the constants
can be exercised without the vulcanus runtime stack, and the module is
loaded directly from its file path.
"""
import importlib.util
import os
import sys
import types
import unittest

SERVICE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
TARGET_FILE = os.path.join(SERVICE_DIR, "zeus", "user_access_service", "app", "constant.py")
MODULE_NAME = "aops_zeus_test_uaz_app_constant"
SETTINGS_MODULE_NAME = "zeus.user_access_service.app.settings"

REDIS_HOST = "10.0.0.1"
REDIS_PORT = 6379


def _load_module(name, file_path):
    spec = importlib.util.spec_from_file_location(name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _stub_settings():
    redis = types.SimpleNamespace(host=REDIS_HOST, port=REDIS_PORT)
    configuration = types.SimpleNamespace(redis=redis)
    module = types.ModuleType(SETTINGS_MODULE_NAME)
    module.configuration = configuration
    sys.modules[SETTINGS_MODULE_NAME] = module


class ConstantTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _stub_settings()
        cls.module = _load_module(MODULE_NAME, TARGET_FILE)

    def test_backend_url_uses_redis_database_1(self):
        self.assertEqual(self.module.BACKEND, f"redis://{REDIS_HOST}:{REDIS_PORT}/1")

    def test_broker_url_uses_redis_database_0(self):
        self.assertEqual(self.module.BROKER, f"redis://{REDIS_HOST}:{REDIS_PORT}/0")

    def test_backend_and_broker_use_same_host_and_port(self):
        backend_parts = self.module.BACKEND.split("redis://")
        broker_parts = self.module.BROKER.split("redis://")
        self.assertEqual(
            backend_parts[1].rsplit("/", 1)[0], broker_parts[1].rsplit("/", 1)[0]
        )

    def test_backend_and_broker_are_distinct_databases(self):
        self.assertTrue(self.module.BACKEND.endswith("/1"))
        self.assertTrue(self.module.BROKER.endswith("/0"))
        self.assertNotEqual(self.module.BACKEND, self.module.BROKER)


if __name__ == "__main__":
    unittest.main()
