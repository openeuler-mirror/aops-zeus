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
Unit tests for zeus.host_information_service.app.serialize.host.

The schema module depends on marshmallow, the vulcanus ``ValidateRules``
helper, the SQLAlchemy ``Host`` model and the local ``HostTemplate``
constants. The external pieces are replaced with lightweight stand-ins
(the validator behaviour matches the real vulcanus implementation) and the
schema module is loaded directly from its file path.
"""
import importlib.util
import os
import re
import sys
import types
import unittest

from marshmallow import ValidationError

SERVICE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
TARGET_FILE = os.path.join(SERVICE_DIR, "zeus", "host_information_service", "app", "serialize", "host.py")
CONSTANT_FILE = os.path.join(SERVICE_DIR, "zeus", "host_information_service", "app", "constant.py")


class _StubValidateRules:
    """Behavioural stand-in for ``vulcanus.restful.serialize.validate.ValidateRules``."""

    @staticmethod
    def space_character_check(string):
        if len(string.strip()) != len(string):
            raise ValidationError("there may be space character exists at the beginning or end!")

    @staticmethod
    def ipv4_address_check(string):
        pattern = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        if not re.findall(pattern, string):
            raise ValidationError("Not a valid IPV4 address.")


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
    _install_stub("vulcanus")
    _install_stub("vulcanus.restful")
    _install_stub("vulcanus.restful.serialize")
    _install_stub("vulcanus.restful.serialize.validate", ValidateRules=_StubValidateRules)
    _install_stub("zeus")
    _install_stub("zeus.host_information_service")
    _install_stub(
        "zeus.host_information_service.database",
        Cluster=type("Cluster", (), {}),
        Host=type("Host", (), {}),
        HostGroup=type("HostGroup", (), {}),
        __all__=["Cluster", "Host", "HostGroup"],
    )
    # constant.py has no external dependencies, load it for real.
    _load_module("zeus.host_information_service.app.constant", CONSTANT_FILE)


def _assert_load_errors(schema, data, *fields):
    """Load ``data`` and assert a validation error on every field in ``fields``."""
    try:
        schema.load(data)
    except ValidationError as error:
        for field in fields:
            assert field in error.messages, "expected error on %r, got %r" % (field, error.messages)
        return error
    raise AssertionError("expected ValidationError for %r, but load succeeded" % (data,))


def _valid_add_host():
    return {
        "ssh_user": "root",
        "password": "password",
        "host_name": "test_host",
        "host_ip": "192.168.0.100",
        "ssh_port": 22,
        "management": False,
    }


_stub_external_dependencies()
host_schemas = _load_module("aops_zeus_test_hiz_serialize_host", TARGET_FILE)


class AddHostSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = host_schemas.AddHostSchema()

    def test_valid_add_with_password(self):
        data = _valid_add_host()
        data["host_group_id"] = "hg-0001"
        loaded = self.schema.load(data)
        for field, value in data.items():
            self.assertEqual(loaded[field], value)

    def test_valid_add_with_ssh_pkey(self):
        data = _valid_add_host()
        del data["password"]
        data["ssh_pkey"] = "private-key"
        data["host_group_id"] = "hg-0001"
        self.schema.load(data)

    def test_authentication_info_required(self):
        """Neither password nor ssh_pkey provided must be rejected."""
        data = _valid_add_host()
        del data["password"]
        data["host_group_id"] = "hg-0001"
        _assert_load_errors(self.schema, data, "_schema")

    def test_ssh_pkey_takes_effect_without_password(self):
        data = _valid_add_host()
        data["ssh_pkey"] = "private-key"
        data["host_group_id"] = "hg-0001"
        self.schema.load(data)

    def test_host_group_id_required(self):
        data = _valid_add_host()
        _assert_load_errors(self.schema, data, "host_group_id")

    def test_required_fields_enforced(self):
        for field in ("ssh_user", "host_name", "host_ip", "ssh_port", "management"):
            data = _valid_add_host()
            data["host_group_id"] = "hg-0001"
            del data[field]
            _assert_load_errors(self.schema, data, field)

    def test_ssh_user_boundary_accepted(self):
        data = _valid_add_host()
        data["ssh_user"] = "x" * 32
        data["host_group_id"] = "hg-0001"
        self.schema.load(data)

    def test_ssh_user_too_long_rejected(self):
        data = _valid_add_host()
        data["ssh_user"] = "x" * 33
        data["host_group_id"] = "hg-0001"
        _assert_load_errors(self.schema, data, "ssh_user")

    def test_host_name_boundary_accepted(self):
        data = _valid_add_host()
        data["host_name"] = "x" * 50
        data["host_group_id"] = "hg-0001"
        self.schema.load(data)

    def test_host_name_too_long_rejected(self):
        data = _valid_add_host()
        data["host_name"] = "x" * 51
        data["host_group_id"] = "hg-0001"
        _assert_load_errors(self.schema, data, "host_name")

    def test_host_name_leading_space_rejected(self):
        data = _valid_add_host()
        data["host_name"] = " test_host"
        data["host_group_id"] = "hg-0001"
        _assert_load_errors(self.schema, data, "host_name")

    def test_host_name_trailing_space_rejected(self):
        data = _valid_add_host()
        data["host_name"] = "test_host "
        data["host_group_id"] = "hg-0001"
        _assert_load_errors(self.schema, data, "host_name")

    def test_valid_ipv4_accepted(self):
        for ip in ("192.168.0.100", "10.0.0.1", "255.255.255.255", "0.0.0.0"):
            data = _valid_add_host()
            data["host_ip"] = ip
            data["host_group_id"] = "hg-0001"
            self.schema.load(data)

    def test_invalid_ipv4_rejected(self):
        for ip in ("192.168.0.256", "192.168.0", "abc", "1.2.3.4.5"):
            data = _valid_add_host()
            data["host_ip"] = ip
            data["host_group_id"] = "hg-0001"
            _assert_load_errors(self.schema, data, "host_ip")

    def test_ssh_port_boundary_values(self):
        for port in (1, 65535):
            data = _valid_add_host()
            data["ssh_port"] = port
            data["host_group_id"] = "hg-0001"
            self.schema.load(data)

    def test_ssh_port_out_of_range_rejected(self):
        for port in (0, 65536, -1):
            data = _valid_add_host()
            data["ssh_port"] = port
            data["host_group_id"] = "hg-0001"
            _assert_load_errors(self.schema, data, "ssh_port")

    def test_ssh_pkey_boundary_accepted(self):
        data = _valid_add_host()
        data["ssh_pkey"] = "x" * 4096
        data["host_group_id"] = "hg-0001"
        self.schema.load(data)

    def test_ssh_pkey_too_long_rejected(self):
        data = _valid_add_host()
        data["ssh_pkey"] = "x" * 4097
        data["host_group_id"] = "hg-0001"
        _assert_load_errors(self.schema, data, "ssh_pkey")


class AddHostBatchSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = host_schemas.AddHostBatchSchema()

    def _entry(self, host_group_name="test_host_group"):
        return {
            "ssh_user": "root",
            "password": "password",
            "host_name": "test_host",
            "host_ip": "192.168.0.100",
            "ssh_port": 22,
            "management": False,
            "host_group_name": host_group_name,
        }

    def test_valid_batch(self):
        data = {"host_list": [self._entry()]}
        self.schema.load(data)

    def test_host_list_required(self):
        _assert_load_errors(self.schema, {}, "host_list")

    def test_empty_host_list_rejected(self):
        _assert_load_errors(self.schema, {"host_list": []}, "host_list")

    def test_host_group_name_too_long_rejected(self):
        data = {"host_list": [self._entry("x" * 21)]}
        _assert_load_errors(self.schema, data, "host_list")

    def test_entry_authentication_info_enforced(self):
        entry = self._entry()
        del entry["password"]
        data = {"host_list": [entry]}
        _assert_load_errors(self.schema, data, "host_list")


class GetHostsPageRequestSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = host_schemas.GetHostsPage_RequestSchema()

    def test_all_fields_optional(self):
        self.assertEqual(
            self.schema.load({}),
            {
                "host_group_list": None,
                "cluster_list": None,
                "search_key": None,
                "management": None,
                "status": None,
                "sort": None,
                "direction": None,
                "page": None,
                "per_page": None,
            },
        )

    def test_valid_page_params(self):
        data = self.schema.load(
            {
                "host_group_list": ["hg1"],
                "cluster_list": ["c1"],
                "search_key": "test",
                "management": True,
                "status": [0, 1],
                "sort": "host_name",
                "direction": "asc",
                "page": 1,
                "per_page": 10,
            }
        )
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["per_page"], 10)
        self.assertEqual(data["sort"], "host_name")

    def test_sort_valid_values_accepted(self):
        for value in ("host_name", "host_group_name", ""):
            self.schema.load({"sort": value})

    def test_sort_invalid_value_rejected(self):
        _assert_load_errors(self.schema, {"sort": "unknown"}, "sort")

    def test_direction_invalid_value_rejected(self):
        _assert_load_errors(self.schema, {"direction": "left"}, "direction")

    def test_status_negative_value_rejected(self):
        _assert_load_errors(self.schema, {"status": [-1]}, "status")

    def test_status_valid_values_accepted(self):
        self.schema.load({"status": [0, 1, 2, 3]})

    def test_search_key_boundary_accepted(self):
        self.schema.load({"search_key": "x" * 50})

    def test_search_key_too_long_rejected(self):
        _assert_load_errors(self.schema, {"search_key": "x" * 51}, "search_key")

    def test_page_boundary_values(self):
        self.schema.load({"page": 1})
        _assert_load_errors(self.schema, {"page": 0}, "page")

    def test_per_page_boundary_values(self):
        self.schema.load({"per_page": 1})
        self.schema.load({"per_page": 49})
        _assert_load_errors(self.schema, {"per_page": 50}, "per_page")
        _assert_load_errors(self.schema, {"per_page": 0}, "per_page")


class GetHostsPageResponseSchemaTestCase(unittest.TestCase):
    def _sample_object(self):
        return types.SimpleNamespace(
            host_id="host-0001",
            host_name="test_host",
            host_group_name="test_host_group",
            host_ip="192.168.0.100",
            management=False,
            scene="general",
            os_version="openEuler-22.03",
            ssh_port=22,
            cluster_id="cluster-id-0001",
            cluster_name="test_cluster",
        )

    def test_dump_contains_all_declared_fields(self):
        result = host_schemas.GetHostsPage_ResponseSchema().dump(self._sample_object())
        self.assertEqual(
            set(result),
            {
                "host_id",
                "host_name",
                "host_group_name",
                "host_ip",
                "management",
                "scene",
                "os_version",
                "ssh_port",
                "cluster_id",
                "cluster_name",
            },
        )


class UpdateHostSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = host_schemas.UpdateHostSchema()

    def _sample(self):
        return {
            "host_ip": "192.168.0.100",
            "ssh_user": "root",
            "password": "password",
            "ssh_port": 22,
            "host_name": "test_host",
            "host_group_id": "hg-0001",
            "management": False,
            "ssh_pkey": "private-key",
            "status": 0,
            "last_scan": 1000,
            "repo_id": "repo-0001",
            "reboot": False,
        }

    def test_valid_update(self):
        data = self._sample()
        self.assertEqual(self.schema.load(data), data)

    def test_host_group_id_required(self):
        data = self._sample()
        del data["host_group_id"]
        _assert_load_errors(self.schema, data, "host_group_id")

    def test_optional_fields_absent(self):
        loaded = self.schema.load({"host_group_id": "hg-0001"})
        self.assertEqual(loaded["host_group_id"], "hg-0001")
        for field in (
            "host_ip",
            "ssh_user",
            "password",
            "ssh_port",
            "host_name",
            "management",
            "ssh_pkey",
            "status",
            "last_scan",
            "repo_id",
            "reboot",
        ):
            self.assertIsNone(loaded[field])

    def test_status_valid_values_accepted(self):
        for value in (0, 1, 2, 3):
            data = {"host_group_id": "hg-0001", "status": value}
            self.schema.load(data)

    def test_status_invalid_value_rejected(self):
        _assert_load_errors(self.schema, {"host_group_id": "hg-0001", "status": 4}, "status")

    def test_last_scan_boundary_accepted(self):
        self.schema.load({"host_group_id": "hg-0001", "last_scan": 1})

    def test_last_scan_non_positive_rejected(self):
        _assert_load_errors(self.schema, {"host_group_id": "hg-0001", "last_scan": 0}, "last_scan")

    def test_repo_id_boundary_accepted(self):
        self.schema.load({"host_group_id": "hg-0001", "repo_id": "x" * 36})

    def test_repo_id_too_long_rejected(self):
        _assert_load_errors(self.schema, {"host_group_id": "hg-0001", "repo_id": "x" * 37}, "repo_id")

    def test_password_empty_rejected(self):
        _assert_load_errors(self.schema, {"host_group_id": "hg-0001", "password": ""}, "password")

    def test_invalid_ipv4_rejected(self):
        _assert_load_errors(self.schema, {"host_group_id": "hg-0001", "host_ip": "192.168.0.256"}, "host_ip")

    def test_ssh_port_out_of_range_rejected(self):
        _assert_load_errors(self.schema, {"host_group_id": "hg-0001", "ssh_port": 65536}, "ssh_port")

    def test_host_name_leading_space_rejected(self):
        _assert_load_errors(self.schema, {"host_group_id": "hg-0001", "host_name": " test_host"}, "host_name")


class HostsInfoResponseSchemaTestCase(unittest.TestCase):
    def _sample_object(self):
        return types.SimpleNamespace(
            host_id="host-0001",
            host_name="test_host",
            host_group_name="test_host_group",
            host_group_id="hg-0001",
            host_ip="192.168.0.100",
            management=False,
            scene="general",
            os_version="openEuler-22.03",
            ssh_port=22,
            last_scan=1000,
            repo_id="repo-0001",
            status=0,
            reboot=False,
            pkey="private-key",
            ssh_user="root",
            cluster_id="cluster-id-0001",
            cluster_name="test_cluster",
        )

    def test_dump_contains_all_declared_fields(self):
        result = host_schemas.HostsInfo_ResponseSchema().dump(self._sample_object())
        self.assertEqual(
            set(result),
            {
                "host_id",
                "host_name",
                "host_group_name",
                "host_group_id",
                "host_ip",
                "management",
                "scene",
                "os_version",
                "ssh_port",
                "last_scan",
                "repo_id",
                "status",
                "reboot",
                "pkey",
                "ssh_user",
                "cluster_id",
                "cluster_name",
            },
        )


class BatchHostsSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = host_schemas.BatchHostsSchema()

    def test_valid_host_ids(self):
        data = self.schema.load({"host_ids": ["host-1", "host-2"]})
        self.assertEqual(data["host_ids"], ["host-1", "host-2"])

    def test_empty_host_ids_rejected(self):
        _assert_load_errors(self.schema, {"host_ids": []}, "host_ids")

    def test_host_ids_required(self):
        _assert_load_errors(self.schema, {}, "host_ids")


class HostFilterSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = host_schemas.HostFilterSchema()

    def test_all_fields_optional(self):
        self.assertEqual(
            self.schema.load({}),
            {
                "status": None,
                "host_ids": None,
                "host_group_ids": None,
                "host_name": None,
                "reboot": None,
                "repo": None,
                "cluster_list": None,
                "fields": None,
            },
        )

    def test_host_group_ids_length_enforced(self):
        self.schema.load({"host_group_ids": ["x" * 36]})
        _assert_load_errors(self.schema, {"host_group_ids": ["x" * 37]}, "host_group_ids")

    def test_host_ids_empty_list_rejected(self):
        _assert_load_errors(self.schema, {"host_ids": []}, "host_ids")

    def test_host_name_boundary_values(self):
        self.schema.load({"host_name": "x" * 50})
        _assert_load_errors(self.schema, {"host_name": "x" * 51}, "host_name")

    def test_repo_ids_length_enforced(self):
        self.schema.load({"repo": ["x" * 36]})
        _assert_load_errors(self.schema, {"repo": ["x" * 37]}, "repo")

    def test_cluster_list_ids_length_enforced(self):
        self.schema.load({"cluster_list": ["x" * 36]})
        _assert_load_errors(self.schema, {"cluster_list": ["x" * 37]}, "cluster_list")

    def test_fields_only_accepts_declared_columns(self):
        self.schema.load({"fields": ["host_id", "host_name", "status"]})
        _assert_load_errors(self.schema, {"fields": ["not_a_column"]}, "fields")


class UpdateHostStatusSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = host_schemas.UpdateHostStatusSchema()

    def test_status_optional(self):
        self.assertEqual(self.schema.load({}), {"status": None})

    def test_status_valid_values_accepted(self):
        for value in (0, 1, 2, 3):
            self.schema.load({"status": value})

    def test_status_invalid_value_rejected(self):
        _assert_load_errors(self.schema, {"status": 4}, "status")


class HostInfoSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = host_schemas.HostInfoSchema()

    def test_defaults(self):
        self.assertEqual(self.schema.load({}), {"basic": True, "refresh": False})

    def test_valid_values_accepted(self):
        self.assertEqual(self.schema.load({"basic": False, "refresh": True}), {"basic": False, "refresh": True})


class TemplateLangSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = host_schemas.TemplateLangSchema()

    def test_lang_defaults_to_en(self):
        self.assertEqual(self.schema.load({})["lang"], "en")

    def test_valid_langs_accepted(self):
        for lang in ("zh", "en"):
            self.assertEqual(self.schema.load({"lang": lang})["lang"], lang)

    def test_invalid_lang_rejected(self):
        _assert_load_errors(self.schema, {"lang": "fr"}, "lang")


if __name__ == "__main__":
    unittest.main()
