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
Unit tests for zeus.host_information_service.app.constant.

The module holds the host import template file contents (Chinese/English),
the ``HostTemplate`` helper and the ``HostStatus`` constants. It has no
external dependencies, so it is loaded directly from its file path.
"""
import importlib.util
import os
import sys
import types
import unittest

SERVICE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
TARGET_FILE = os.path.join(SERVICE_DIR, "zeus", "host_information_service", "app", "constant.py")
MODULE_NAME = "aops_zeus_test_hiz_app_constant"


def _load_module(name, file_path):
    spec = importlib.util.spec_from_file_location(name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


constant = _load_module(MODULE_NAME, TARGET_FILE)


class HostTemplateTestCase(unittest.TestCase):
    def test_support_lang_returns_supported_codes(self):
        self.assertEqual(sorted(constant.HostTemplate.support_lang()), ["en", "zh"])

    def test_get_file_content_zh(self):
        content = constant.HostTemplate.get_file_content("zh")
        self.assertIsInstance(content, str)
        self.assertIn("提示", content)
        self.assertIn("127.0.0.1", content)

    def test_get_file_content_en(self):
        content = constant.HostTemplate.get_file_content("en")
        self.assertIsInstance(content, str)
        self.assertIn("Note:", content)
        self.assertIn("127.0.0.1", content)

    def test_get_file_content_defaults_to_en_when_none(self):
        self.assertEqual(constant.HostTemplate.get_file_content(None), constant.HostTemplate.get_file_content("en"))

    def test_get_file_content_defaults_to_en_for_unsupported_lang(self):
        self.assertEqual(
            constant.HostTemplate.get_file_content("fr"), constant.HostTemplate.get_file_content("en")
        )

    def test_template_content_is_stable_per_language(self):
        """Repeated calls return the same stored content object for a language."""
        first = constant.HostTemplate.get_file_content("zh")
        second = constant.HostTemplate.get_file_content("zh")
        self.assertEqual(first, second)

    def test_template_has_expected_csv_header(self):
        expected_header = "host_ip,ssh_port,ssh_user,password,ssh_pkey,host_name,host_group_name,management"
        for lang in ("zh", "en"):
            lines = constant.HostTemplate.get_file_content(lang).strip().splitlines()
            self.assertEqual(lines[0], expected_header)

    def test_template_contains_sample_rows(self):
        for lang in ("zh", "en"):
            lines = constant.HostTemplate.get_file_content(lang).strip().splitlines()
            self.assertIn(
                "127.0.0.1,22,root,password,private key,test_host,test_host_group,FALSE", lines
            )


class HostStatusTestCase(unittest.TestCase):
    def test_status_constants(self):
        self.assertEqual(constant.HostStatus.ONLINE, 0)
        self.assertEqual(constant.HostStatus.OFFLINE, 1)
        self.assertEqual(constant.HostStatus.UNESTABLISHED, 2)
        self.assertEqual(constant.HostStatus.SCANNING, 3)

    def test_status_constants_are_distinct(self):
        values = [
            constant.HostStatus.ONLINE,
            constant.HostStatus.OFFLINE,
            constant.HostStatus.UNESTABLISHED,
            constant.HostStatus.SCANNING,
        ]
        self.assertEqual(len(values), len(set(values)))


class TemplateContentConstantTestCase(unittest.TestCase):
    def test_zh_content_constant_matches_template(self):
        self.assertEqual(
            constant.HOST_TEMPLATE_FILE_CONTENT_FOR_ZH, constant.HostTemplate.get_file_content("zh")
        )

    def test_en_content_constant_matches_template(self):
        self.assertEqual(
            constant.HOST_TEMPLATE_FILE_CONTENT_FOR_EN, constant.HostTemplate.get_file_content("en")
        )


if __name__ == "__main__":
    unittest.main()
