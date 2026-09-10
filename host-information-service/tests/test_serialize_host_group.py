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
Unit tests for zeus.host_information_service.app.serialize.host_group.

The schema module depends on marshmallow and the SQLAlchemy ``HostGroup``
model. The database model is replaced with a lightweight stand-in and the
schema module is loaded directly from its file path so the tests can run
without the full runtime stack.
"""
import importlib.util
import os
import sys
import types
import unittest

from marshmallow import ValidationError

SERVICE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
TARGET_FILE = os.path.join(
    SERVICE_DIR, "zeus", "host_information_service", "app", "serialize", "host_group.py"
)


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


def _valid_host_group():
    return {
        "host_group_name": "test_host_group",
        "description": "description",
        "cluster_id": "cluster-id-0001",
    }


_stub_external_dependencies()
host_group_schemas = _load_module("aops_zeus_test_hiz_serialize_host_group", TARGET_FILE)


class AddHostGroupSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = host_group_schemas.AddHostGroupSchema()

    def test_valid_add(self):
        data = _valid_host_group()
        self.assertEqual(self.schema.load(data), data)

    def test_all_fields_required(self):
        for field in ("host_group_name", "description", "cluster_id"):
            data = _valid_host_group()
            del data[field]
            _assert_load_errors(self.schema, data, field)

    def test_host_group_name_boundary_accepted(self):
        data = _valid_host_group()
        data["host_group_name"] = "x" * 20
        self.schema.load(data)

    def test_host_group_name_too_long_rejected(self):
        data = _valid_host_group()
        data["host_group_name"] = "x" * 21
        _assert_load_errors(self.schema, data, "host_group_name")

    def test_description_boundary_accepted(self):
        data = _valid_host_group()
        data["description"] = "x" * 60
        self.schema.load(data)

    def test_description_too_long_rejected(self):
        data = _valid_host_group()
        data["description"] = "x" * 61
        _assert_load_errors(self.schema, data, "description")

    def test_cluster_id_boundary_accepted(self):
        data = _valid_host_group()
        data["cluster_id"] = "x" * 36
        self.schema.load(data)

    def test_cluster_id_too_long_rejected(self):
        data = _valid_host_group()
        data["cluster_id"] = "x" * 37
        _assert_load_errors(self.schema, data, "cluster_id")

    def test_empty_cluster_id_rejected(self):
        data = _valid_host_group()
        data["cluster_id"] = ""
        _assert_load_errors(self.schema, data, "cluster_id")


class HostGroupSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = host_group_schemas.HostGroupSchema()

    def _sample_object(self):
        return types.SimpleNamespace(
            host_group_id="hg-0001",
            host_group_name="test_host_group",
            description="description",
            cluster_name="test_cluster",
            cluster_id="cluster-id-0001",
        )

    def test_cluster_id_required_on_load(self):
        _assert_load_errors(self.schema, {"cluster_name": "test_cluster"}, "cluster_id")

    def test_cluster_name_optional_on_load(self):
        data = self.schema.load({"cluster_id": "cluster-id-0001"})
        self.assertIsNone(data["cluster_name"])

    def test_dump_contains_all_declared_fields(self):
        result = self.schema.dump(self._sample_object())
        self.assertEqual(
            set(result),
            {"host_group_id", "host_group_name", "description", "cluster_name", "cluster_id"},
        )


class GetHostGroupPageRequestSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = host_group_schemas.GetHostGroupPage_RequestSchema()

    def test_all_fields_optional(self):
        self.assertEqual(
            self.schema.load({}),
            {"cluster_ids": None, "sort": None, "direction": "desc", "page": None, "per_page": None},
        )

    def test_direction_defaults_to_desc(self):
        self.assertEqual(self.schema.load({})["direction"], "desc")

    def test_valid_page_params(self):
        data = self.schema.load(
            {"cluster_ids": ["c1"], "sort": "host_count", "direction": "asc", "page": 1, "per_page": 10}
        )
        self.assertEqual(data, {"cluster_ids": ["c1"], "sort": "host_count", "direction": "asc", "page": 1, "per_page": 10})

    def test_sort_valid_values_accepted(self):
        for value in ("host_count", "host_group_name", ""):
            self.schema.load({"sort": value})

    def test_sort_invalid_value_rejected(self):
        _assert_load_errors(self.schema, {"sort": "unknown"}, "sort")

    def test_direction_valid_values_accepted(self):
        for value in ("desc", "asc"):
            self.schema.load({"direction": value})

    def test_direction_invalid_value_rejected(self):
        _assert_load_errors(self.schema, {"direction": "left"}, "direction")

    def test_page_boundary_values(self):
        self.schema.load({"page": 1})
        _assert_load_errors(self.schema, {"page": 0}, "page")
        _assert_load_errors(self.schema, {"page": -1}, "page")

    def test_per_page_boundary_values(self):
        self.schema.load({"per_page": 1})
        self.schema.load({"per_page": 49})
        _assert_load_errors(self.schema, {"per_page": 50}, "per_page")
        _assert_load_errors(self.schema, {"per_page": 0}, "per_page")


class GetHostGroupPageResponseSchemaTestCase(unittest.TestCase):
    def _sample_object(self):
        return types.SimpleNamespace(
            host_group_id="hg-0001",
            host_group_name="test_host_group",
            description="description",
            host_count=5,
            cluster_name="test_cluster",
            cluster_id="cluster-id-0001",
        )

    def test_dump_contains_all_declared_fields(self):
        result = host_group_schemas.GetHostGroupPage_ResponseSchema().dump(self._sample_object())
        self.assertEqual(
            set(result),
            {"host_group_id", "host_group_name", "description", "host_count", "cluster_name", "cluster_id"},
        )

    def test_dump_with_none_cluster_name(self):
        obj = self._sample_object()
        obj.cluster_name = None
        result = host_group_schemas.GetHostGroupPage_ResponseSchema().dump(obj)
        self.assertIsNone(result["cluster_name"])


if __name__ == "__main__":
    unittest.main()
