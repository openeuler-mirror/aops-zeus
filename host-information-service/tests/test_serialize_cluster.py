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
Unit tests for zeus.host_information_service.app.serialize.cluster.

The schema module depends on marshmallow, the vulcanus ``ValidateRules``
helper and the SQLAlchemy ``Cluster`` model. To keep the tests runnable
without the full runtime stack, ``vulcanus`` and the database model are
replaced with lightweight stand-ins (the validator behaviour matches the
real vulcanus implementation) and the schema module is loaded directly
from its file path.
"""
import importlib.util
import os
import re
import sys
import types
import unittest

from marshmallow import ValidationError

SERVICE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
TARGET_FILE = os.path.join(
    SERVICE_DIR, "zeus", "host_information_service", "app", "serialize", "cluster.py"
)


class _StubValidateRules:
    """Behavioural stand-in for ``vulcanus.restful.serialize.validate.ValidateRules``."""

    @staticmethod
    def space_character_check(string):
        if len(string.strip()) != len(string):
            raise ValidationError("there may be space character exists at the beginning or end!")

    @staticmethod
    def account_name_check(string):
        if not re.findall("^[a-zA-Z0-9]{5,20}$", string):
            raise ValidationError("username should only contains string or number, between 5 and 20 characters!")

    @staticmethod
    def account_password_check(string):
        if not re.findall("^[a-zA-Z0-9]{6,20}$", string):
            raise ValidationError("password should only contains string or number, between 6 and 20 characters!!")

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


def _assert_load_errors(schema, data, *fields):
    """Load ``data`` and assert a validation error on every field in ``fields``."""
    try:
        schema.load(data)
    except ValidationError as error:
        for field in fields:
            assert field in error.messages, "expected error on %r, got %r" % (field, error.messages)
        return error
    raise AssertionError("expected ValidationError for %r, but load succeeded" % (data,))


def _valid_add_cluster():
    return {
        "cluster_id": "cluster-id-0001",
        "cluster_name": "test_cluster",
        "description": "description",
        "cluster_ip": "192.168.0.100",
        "synchronous_state": "sync",
    }


_stub_external_dependencies()
cluster_schemas = _load_module("aops_zeus_test_hiz_serialize_cluster", TARGET_FILE)


class QueryClusterSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = cluster_schemas.QueryClusterSchema()

    def test_missing_cluster_ids_defaults_to_empty_list(self):
        self.assertEqual(self.schema.load({}), {"cluster_ids": []})

    def test_valid_cluster_ids(self):
        data = self.schema.load({"cluster_ids": ["id-1", "id-2"]})
        self.assertEqual(data["cluster_ids"], ["id-1", "id-2"])

    def test_boundary_length_36_accepted(self):
        self.schema.load({"cluster_ids": ["x" * 36]})

    def test_length_37_rejected(self):
        _assert_load_errors(self.schema, {"cluster_ids": ["x" * 37]}, "cluster_ids")

    def test_empty_string_id_rejected(self):
        _assert_load_errors(self.schema, {"cluster_ids": [""]}, "cluster_ids")

    def test_non_list_rejected(self):
        _assert_load_errors(self.schema, {"cluster_ids": "not-a-list"}, "cluster_ids")


class AddClusterSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = cluster_schemas.AddClusterSchema()

    def test_valid_add(self):
        data = _valid_add_cluster()
        self.assertEqual(self.schema.load(data), data)

    def test_all_fields_required(self):
        for field in ("cluster_id", "cluster_name", "description", "cluster_ip", "synchronous_state"):
            data = _valid_add_cluster()
            del data[field]
            _assert_load_errors(self.schema, data, field)

    def test_cluster_id_boundary_accepted(self):
        data = _valid_add_cluster()
        data["cluster_id"] = "x" * 36
        self.schema.load(data)

    def test_cluster_id_too_long_rejected(self):
        data = _valid_add_cluster()
        data["cluster_id"] = "x" * 37
        _assert_load_errors(self.schema, data, "cluster_id")

    def test_cluster_name_boundary_accepted(self):
        data = _valid_add_cluster()
        data["cluster_name"] = "x" * 20
        self.schema.load(data)

    def test_cluster_name_too_long_rejected(self):
        data = _valid_add_cluster()
        data["cluster_name"] = "x" * 21
        _assert_load_errors(self.schema, data, "cluster_name")

    def test_description_boundary_accepted(self):
        data = _valid_add_cluster()
        data["description"] = "x" * 60
        self.schema.load(data)

    def test_description_too_long_rejected(self):
        data = _valid_add_cluster()
        data["description"] = "x" * 61
        _assert_load_errors(self.schema, data, "description")

    def test_synchronous_state_boundary_accepted(self):
        data = _valid_add_cluster()
        data["synchronous_state"] = "x" * 20
        self.schema.load(data)

    def test_synchronous_state_too_long_rejected(self):
        data = _valid_add_cluster()
        data["synchronous_state"] = "x" * 21
        _assert_load_errors(self.schema, data, "synchronous_state")

    def test_valid_ipv4_accepted(self):
        for ip in ("192.168.0.100", "10.0.0.1", "255.255.255.255", "0.0.0.0"):
            data = _valid_add_cluster()
            data["cluster_ip"] = ip
            self.schema.load(data)

    def test_invalid_ipv4_rejected(self):
        for ip in ("192.168.0.256", "192.168.0", "abc", "1.2.3.4.5", "300.1.1.1"):
            data = _valid_add_cluster()
            data["cluster_ip"] = ip
            _assert_load_errors(self.schema, data, "cluster_ip")


class DeleteClusterSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = cluster_schemas.DeleteClusterSchema()

    def test_missing_cluster_list_defaults_to_none(self):
        self.assertEqual(self.schema.load({}), {"cluster_list": None})

    def test_valid_cluster_list(self):
        data = self.schema.load({"cluster_list": ["id-1", "id-2"]})
        self.assertEqual(data["cluster_list"], ["id-1", "id-2"])

    def test_empty_cluster_list_accepted(self):
        self.assertEqual(self.schema.load({"cluster_list": []})["cluster_list"], [])

    def test_too_long_id_rejected(self):
        _assert_load_errors(self.schema, {"cluster_list": ["x" * 37]}, "cluster_list")

    def test_non_list_rejected(self):
        _assert_load_errors(self.schema, {"cluster_list": "not-a-list"}, "cluster_list")


class UpdateClusterSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = cluster_schemas.UpdateClusterSchema()

    def test_valid_update(self):
        data = _valid_add_cluster()
        self.assertEqual(self.schema.load(data), data)

    def test_synchronous_state_optional(self):
        data = _valid_add_cluster()
        del data["synchronous_state"]
        loaded = self.schema.load(data)
        self.assertNotIn("synchronous_state", loaded)

    def test_synchronous_state_too_long_rejected(self):
        data = _valid_add_cluster()
        data["synchronous_state"] = "x" * 21
        _assert_load_errors(self.schema, data, "synchronous_state")

    def test_required_fields_enforced(self):
        for field in ("cluster_id", "cluster_name", "description", "cluster_ip"):
            data = _valid_add_cluster()
            del data[field]
            _assert_load_errors(self.schema, data, field)

    def test_invalid_ipv4_rejected(self):
        data = _valid_add_cluster()
        data["cluster_ip"] = "192.168.0.256"
        _assert_load_errors(self.schema, data, "cluster_ip")


class GetClusterInfoResponseSchemaTestCase(unittest.TestCase):
    def _sample_object(self):
        return types.SimpleNamespace(
            cluster_id="cluster-id-0001",
            backend_ip="192.168.0.100",
            subcluster="sub-1",
            cluster_name="test_cluster",
            synchronous_state="sync",
            description="description",
        )

    def test_dump_maps_backend_ip_to_cluster_ip(self):
        result = cluster_schemas.GetClusterInfo_ResponseSchema().dump(self._sample_object())
        self.assertEqual(result["cluster_ip"], "192.168.0.100")

    def test_dump_contains_all_declared_fields(self):
        result = cluster_schemas.GetClusterInfo_ResponseSchema().dump(self._sample_object())
        self.assertEqual(
            set(result),
            {"cluster_id", "cluster_ip", "subcluster", "cluster_name", "synchronous_state", "description"},
        )


class GetLocalClusterInfoResponseSchemaTestCase(unittest.TestCase):
    def _sample_object(self):
        return types.SimpleNamespace(
            cluster_id="cluster-id-0001",
            cluster_name="test_cluster",
            backend_ip="192.168.0.100",
            private_key="private-key",
            public_key="public-key",
        )

    def test_dump_maps_backend_ip_to_cluster_ip(self):
        result = cluster_schemas.GetLocalClusterInfo_ResponseSchema().dump(self._sample_object())
        self.assertEqual(result["cluster_ip"], "192.168.0.100")

    def test_dump_contains_all_declared_fields(self):
        result = cluster_schemas.GetLocalClusterInfo_ResponseSchema().dump(self._sample_object())
        self.assertEqual(
            set(result),
            {"cluster_id", "cluster_name", "cluster_ip", "private_key", "public_key"},
        )


if __name__ == "__main__":
    unittest.main()
