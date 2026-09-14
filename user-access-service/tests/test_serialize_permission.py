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
Unit tests for zeus.user_access_service.app.serialize.permission.

The schema module depends on marshmallow and the SQLAlchemy ``UserInfo``
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
TARGET_FILE = os.path.join(SERVICE_DIR, "zeus", "user_access_service", "app", "serialize", "permission.py")


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
    _install_stub("zeus.user_access_service")
    _install_stub("zeus.user_access_service.database")
    _install_stub(
        "zeus.user_access_service.database.table",
        Permission=type("Permission", (), {}),
        Role=type("Role", (), {}),
        RolePermissionAssociation=type("RolePermissionAssociation", (), {}),
        Route=type("Route", (), {}),
        UserClusterAssociation=type("UserClusterAssociation", (), {}),
        UserInfo=type("UserInfo", (), {}),
        UserMap=type("UserMap", (), {}),
        UserRoleAssociation=type("UserRoleAssociation", (), {}),
        UserToken=type("UserToken", (), {}),
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


_stub_external_dependencies()
permission_schemas = _load_module("aops_zeus_test_uaz_serialize_permission", TARGET_FILE)


class GetAccountPageRequestSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = permission_schemas.GetAccountPage_RequestSchema()

    def test_all_fields_optional(self):
        self.assertEqual(self.schema.load({}), {"username": None, "page": None, "per_page": None})

    def test_valid_page_params(self):
        data = self.schema.load({"username": "user00001", "page": 1, "per_page": 10})
        self.assertEqual(data["username"], "user00001")
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["per_page"], 10)

    def test_page_boundary_values(self):
        self.schema.load({"page": 1})
        _assert_load_errors(self.schema, {"page": 0}, "page")
        _assert_load_errors(self.schema, {"page": -1}, "page")

    def test_per_page_boundary_values(self):
        self.schema.load({"per_page": 1})
        self.schema.load({"per_page": 49})
        _assert_load_errors(self.schema, {"per_page": 50}, "per_page")
        _assert_load_errors(self.schema, {"per_page": 0}, "per_page")


class GetAccountPageResponseSchemaTestCase(unittest.TestCase):
    def _sample_object(self):
        return types.SimpleNamespace(
            username="user00001",
            role_type="admin",
            clusters_num=3,
            email="user@example.com",
        )

    def test_dump_contains_all_declared_fields(self):
        result = permission_schemas.GetAccountPage_ResponseSchema().dump(self._sample_object())
        self.assertEqual(set(result), {"username", "role_type", "clusters_num", "email"})


class GetPermissionRequestSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = permission_schemas.GetPermission_RequestSchema()

    def test_all_fields_optional(self):
        self.assertEqual(self.schema.load({}), {"username": None, "cluster_id": None})

    def test_valid_params(self):
        data = self.schema.load({"username": "user00001", "cluster_id": "cluster-id-0001"})
        self.assertEqual(data["username"], "user00001")
        self.assertEqual(data["cluster_id"], "cluster-id-0001")


class DeletePermissionRequestSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = permission_schemas.DeletePermission_RequestSchema()

    def test_all_fields_optional(self):
        self.assertEqual(self.schema.load({}), {"manager_username": None, "cluster_id": None})

    def test_valid_params(self):
        data = self.schema.load({"manager_username": "manager00001", "cluster_id": "cluster-id-0001"})
        self.assertEqual(data["manager_username"], "manager00001")
        self.assertEqual(data["cluster_id"], "cluster-id-0001")


class PermissionSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = permission_schemas.PermissionSchema()

    def test_cluster_id_required(self):
        _assert_load_errors(self.schema, {"host_group": ["hg-1"]}, "cluster_id")

    def test_cluster_id_boundary(self):
        self.schema.load({"cluster_id": "x" * 36})
        _assert_load_errors(self.schema, {"cluster_id": "x" * 37}, "cluster_id")

    def test_empty_cluster_id_rejected(self):
        _assert_load_errors(self.schema, {"cluster_id": ""}, "cluster_id")

    def test_host_group_optional(self):
        loaded = self.schema.load({"cluster_id": "cluster-id-0001"})
        self.assertEqual(loaded["cluster_id"], "cluster-id-0001")
        self.assertIsNone(loaded["host_group"])

    def test_valid_host_group(self):
        data = self.schema.load({"cluster_id": "cluster-id-0001", "host_group": ["hg-1", "hg-2"]})
        self.assertEqual(data["host_group"], ["hg-1", "hg-2"])

    def test_host_group_length_enforced(self):
        self.schema.load({"cluster_id": "cluster-id-0001", "host_group": ["x" * 36]})
        _assert_load_errors(
            self.schema, {"cluster_id": "cluster-id-0001", "host_group": ["x" * 37]}, "host_group"
        )


class SetPermissionRequestSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = permission_schemas.SetPermission_RequestSchema()

    def test_username_required(self):
        _assert_load_errors(self.schema, {"permission": [{"cluster_id": "c-1"}]}, "username")

    def test_username_boundary(self):
        self.schema.load({"username": "x" * 36, "permission": [{"cluster_id": "c-1"}]})
        _assert_load_errors(
            self.schema, {"username": "x" * 37, "permission": [{"cluster_id": "c-1"}]}, "username"
        )

    def test_empty_username_rejected(self):
        _assert_load_errors(self.schema, {"username": "", "permission": [{"cluster_id": "c-1"}]}, "username")

    def test_permission_optional(self):
        loaded = self.schema.load({"username": "user00001"})
        self.assertEqual(loaded["username"], "user00001")
        self.assertIsNone(loaded["permission"])

    def test_valid_permission(self):
        data = self.schema.load(
            {"username": "user00001", "permission": [{"cluster_id": "c-1", "host_group": ["hg-1"]}]}
        )
        self.assertEqual(data["permission"][0]["cluster_id"], "c-1")

    def test_empty_permission_list_rejected(self):
        _assert_load_errors(self.schema, {"username": "user00001", "permission": []}, "permission")

    def test_invalid_nested_permission_rejected(self):
        payload = {"username": "user00001", "permission": [{"host_group": ["hg-1"]}]}
        _assert_load_errors(self.schema, payload, "permission")


class BindPermissionRequestSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = permission_schemas.BindPermission_RequestSchema()

    def _sample(self):
        return {
            "cluster_id": "cluster-id-0001",
            "manager_username": "manager00001",
            "public_key": "public-key",
            "host_group": ["hg-1", "hg-2"],
        }

    def test_valid_bind(self):
        data = self._sample()
        self.assertEqual(self.schema.load(data), data)

    def test_all_fields_required(self):
        for field in ("cluster_id", "manager_username", "public_key", "host_group"):
            data = self._sample()
            del data[field]
            _assert_load_errors(self.schema, data, field)

    def test_cluster_id_boundary(self):
        data = self._sample()
        data["cluster_id"] = "x" * 36
        self.schema.load(data)
        data["cluster_id"] = "x" * 37
        _assert_load_errors(self.schema, data, "cluster_id")

    def test_manager_username_boundary(self):
        data = self._sample()
        data["manager_username"] = "x" * 36
        self.schema.load(data)
        data["manager_username"] = "x" * 37
        _assert_load_errors(self.schema, data, "manager_username")

    def test_public_key_max_length(self):
        data = self._sample()
        data["public_key"] = "x" * 4096
        self.schema.load(data)
        data["public_key"] = "x" * 4097
        _assert_load_errors(self.schema, data, "public_key")

    def test_host_group_empty_list_accepted(self):
        # host_group is required (must be present) but has no length
        # constraint, so an empty list is accepted.
        data = self._sample()
        data["host_group"] = []
        loaded = self.schema.load(data)
        self.assertEqual(loaded["host_group"], [])

    def test_host_group_length_enforced(self):
        data = self._sample()
        data["host_group"] = ["x" * 36]
        self.schema.load(data)
        data["host_group"] = ["x" * 37]
        _assert_load_errors(self.schema, data, "host_group")


if __name__ == "__main__":
    unittest.main()
