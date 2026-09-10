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
Unit tests for zeus.user_access_service.app.serialize.account.

The schema module depends on marshmallow and the vulcanus ``ValidateRules``
helper. The helper is replaced with a behavioural stand-in (matching the
real vulcanus implementation) and the schema module is loaded directly from
its file path so the tests can run without the full runtime stack.
"""
import importlib.util
import os
import re
import sys
import types
import unittest

from marshmallow import ValidationError

SERVICE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
TARGET_FILE = os.path.join(SERVICE_DIR, "zeus", "user_access_service", "app", "serialize", "account.py")


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
account_schemas = _load_module("aops_zeus_test_uaz_serialize_account", TARGET_FILE)


class Oauth2AuthorizeLoginSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = account_schemas.Oauth2AuthorizeLoginSchema()

    def test_valid_code(self):
        data = self.schema.load({"code": "authorization-code"})
        self.assertEqual(data["code"], "authorization-code")

    def test_code_required(self):
        _assert_load_errors(self.schema, {}, "code")

    def test_code_boundary_accepted(self):
        self.schema.load({"code": "x" * 200})

    def test_code_too_long_rejected(self):
        _assert_load_errors(self.schema, {"code": "x" * 201}, "code")

    def test_code_empty_rejected(self):
        _assert_load_errors(self.schema, {"code": ""}, "code")


class Oauth2AuthorizedLogoutSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = account_schemas.Oauth2AuthorizedLogoutSchema()

    def test_valid_logout(self):
        data = self.schema.load({"username": "user00001", "encrypted_string": "encrypted"})
        self.assertEqual(data["username"], "user00001")
        self.assertEqual(data["encrypted_string"], "encrypted")

    def test_username_boundary_accepted(self):
        self.schema.load({"username": "x" * 5, "encrypted_string": "enc"})
        self.schema.load({"username": "x" * 20, "encrypted_string": "enc"})

    def test_username_too_short_rejected(self):
        _assert_load_errors(self.schema, {"username": "x" * 4, "encrypted_string": "enc"}, "username")

    def test_username_too_long_rejected(self):
        _assert_load_errors(self.schema, {"username": "x" * 21, "encrypted_string": "enc"}, "username")

    def test_encrypted_string_required(self):
        _assert_load_errors(self.schema, {"username": "user00001"}, "encrypted_string")


class Oauth2AuthorizeAddUserSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = account_schemas.Oauth2AuthorizeAddUserSchema()

    def test_valid_register(self):
        data = self.schema.load({"username": "user00001", "email": "user@example.com"})
        self.assertEqual(data["username"], "user00001")
        self.assertEqual(data["email"], "user@example.com")

    def test_account_name_check_valid(self):
        for name in ("user00001", "a1b2c", "User01234567890123"):
            self.schema.load({"username": name, "email": "user@example.com"})

    def test_account_name_check_min_length_boundary(self):
        # exactly 5 alphanumeric characters is the minimum accepted length
        self.schema.load({"username": "user0", "email": "user@example.com"})
        _assert_load_errors(self.schema, {"username": "user", "email": "user@example.com"}, "username")

    def test_account_name_check_rejects_long(self):
        _assert_load_errors(
            self.schema, {"username": "x" * 21, "email": "user@example.com"}, "username"
        )

    def test_account_name_check_rejects_special_chars(self):
        _assert_load_errors(self.schema, {"username": "user@0001", "email": "user@example.com"}, "username")

    def test_email_invalid_rejected(self):
        _assert_load_errors(self.schema, {"username": "user00001", "email": "not-an-email"}, "email")


class ChangePasswordSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = account_schemas.ChangePasswordSchema()

    def test_valid_change(self):
        data = self.schema.load(
            {"username": "user00001", "password": "newpass123", "old_password": "oldpass1"}
        )
        self.assertEqual(data["username"], "user00001")

    def test_password_rule_valid(self):
        self.schema.load({"username": "user00001", "password": "a1b2c3", "old_password": "oldpass1"})
        self.schema.load({"username": "user00001", "password": "a1b2c3d4e5f6g7h8i9j0", "old_password": "oldpass1"})

    def test_password_rule_rejects_short(self):
        _assert_load_errors(
            self.schema, {"username": "user00001", "password": "a1b2c", "old_password": "oldpass1"}, "password"
        )

    def test_password_rule_rejects_long(self):
        _assert_load_errors(
            self.schema,
            {"username": "user00001", "password": "x" * 21, "old_password": "oldpass1"},
            "password",
        )

    def test_password_rule_rejects_special_chars(self):
        _assert_load_errors(
            self.schema, {"username": "user00001", "password": "pass@word1", "old_password": "oldpass1"}, "password"
        )

    def test_old_password_boundary(self):
        self.schema.load({"username": "user00001", "password": "newpass123", "old_password": "oldpas"})
        self.schema.load({"username": "user00001", "password": "newpass123", "old_password": "old" * 6})
        _assert_load_errors(
            self.schema, {"username": "user00001", "password": "newpass123", "old_password": "oldp"}, "old_password"
        )
        _assert_load_errors(
            self.schema,
            {"username": "user00001", "password": "newpass123", "old_password": "x" * 21},
            "old_password",
        )


class ResetPasswordSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = account_schemas.ResetPasswordSchema()

    def test_valid_reset(self):
        data = self.schema.load({"username": "user00001"})
        self.assertEqual(data["username"], "user00001")

    def test_username_boundary(self):
        self.schema.load({"username": "x" * 5})
        self.schema.load({"username": "x" * 20})
        _assert_load_errors(self.schema, {"username": "x" * 4}, "username")
        _assert_load_errors(self.schema, {"username": "x" * 21}, "username")


class CertificateSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = account_schemas.CertificateSchema()

    def test_valid_key(self):
        data = self.schema.load({"key": "certificate-key"})
        self.assertEqual(data["key"], "certificate-key")

    def test_empty_key_rejected(self):
        _assert_load_errors(self.schema, {"key": ""}, "key")


class BindManagerUserSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = account_schemas.BindManagerUserSchema()

    def _sample(self):
        return {
            "username": "user00001",
            "password": "password123",
            "manager_username": "manager00001",
            "manager_cluster_id": "cluster-id-0001",
            "public_key": "public-key",
        }

    def test_valid_bind(self):
        data = self._sample()
        self.assertEqual(self.schema.load(data), data)

    def test_all_fields_required(self):
        for field in (
            "username",
            "password",
            "manager_username",
            "manager_cluster_id",
            "public_key",
        ):
            data = self._sample()
            del data[field]
            _assert_load_errors(self.schema, data, field)

    def test_username_boundary(self):
        data = self._sample()
        data["username"] = "x" * 36
        self.schema.load(data)
        data["username"] = "x" * 37
        _assert_load_errors(self.schema, data, "username")

    def test_public_key_boundary(self):
        data = self._sample()
        data["public_key"] = "x" * 4096
        self.schema.load(data)
        data["public_key"] = "x" * 4097
        _assert_load_errors(self.schema, data, "public_key")


class RegisterClusterSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = account_schemas.RegisterClusterSchema()

    def _sample(self):
        return {
            "cluster_name": "test_cluster",
            "description": "description",
            "cluster_ip": "192.168.0.100",
            "cluster_username": "clusteruser",
            "cluster_password": "password123",
        }

    def test_valid_register(self):
        data = self._sample()
        self.assertEqual(self.schema.load(data), data)

    def test_all_fields_required(self):
        for field in (
            "cluster_name",
            "description",
            "cluster_ip",
            "cluster_username",
            "cluster_password",
        ):
            data = self._sample()
            del data[field]
            _assert_load_errors(self.schema, data, field)

    def test_cluster_name_boundary(self):
        data = self._sample()
        data["cluster_name"] = "x" * 20
        self.schema.load(data)
        data["cluster_name"] = "x" * 21
        _assert_load_errors(self.schema, data, "cluster_name")

    def test_description_boundary(self):
        data = self._sample()
        data["description"] = "x" * 60
        self.schema.load(data)
        data["description"] = "x" * 61
        _assert_load_errors(self.schema, data, "description")

    def test_invalid_ipv4_rejected(self):
        for ip in ("192.168.0.256", "192.168.0", "abc", "300.1.1.1"):
            data = self._sample()
            data["cluster_ip"] = ip
            _assert_load_errors(self.schema, data, "cluster_ip")

    def test_valid_ipv4_accepted(self):
        for ip in ("192.168.0.100", "10.0.0.1", "255.255.255.255", "0.0.0.0"):
            data = self._sample()
            data["cluster_ip"] = ip
            self.schema.load(data)


class DeleteClusterSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = account_schemas.DeleteClusterSchema()

    def test_valid_delete(self):
        data = self.schema.load({"cluster_id": "cluster-id-0001"})
        self.assertEqual(data["cluster_id"], "cluster-id-0001")

    def test_cluster_id_required(self):
        _assert_load_errors(self.schema, {}, "cluster_id")

    def test_cluster_id_boundary(self):
        self.schema.load({"cluster_id": "x" * 36})
        _assert_load_errors(self.schema, {"cluster_id": "x" * 37}, "cluster_id")


class BatchRegisterClusterSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = account_schemas.BatchRegisterClusterSchema()

    def _cluster(self):
        return {
            "cluster_name": "test_cluster",
            "description": "description",
            "cluster_ip": "192.168.0.100",
            "cluster_username": "clusteruser",
            "cluster_password": "password123",
        }

    def test_valid_batch(self):
        data = self.schema.load({"cluster_info": [self._cluster()]})
        self.assertEqual(len(data["cluster_info"]), 1)

    def test_cluster_info_required(self):
        _assert_load_errors(self.schema, {}, "cluster_info")

    def test_empty_cluster_info_rejected(self):
        _assert_load_errors(self.schema, {"cluster_info": []}, "cluster_info")

    def test_invalid_nested_cluster_rejected(self):
        cluster = self._cluster()
        cluster["cluster_ip"] = "not-an-ip"
        _assert_load_errors(self.schema, {"cluster_info": [cluster]}, "cluster_info")


class ClusterKeySchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = account_schemas.ClusterKeySchema()

    def test_cluster_ids_optional(self):
        self.assertEqual(self.schema.load({}), {"cluster_ids": None})

    def test_valid_cluster_ids(self):
        data = self.schema.load({"cluster_ids": ["id-1", "id-2"]})
        self.assertEqual(data["cluster_ids"], ["id-1", "id-2"])

    def test_empty_list_accepted(self):
        self.assertEqual(self.schema.load({"cluster_ids": []})["cluster_ids"], [])

    def test_too_long_id_rejected(self):
        _assert_load_errors(self.schema, {"cluster_ids": ["x" * 37]}, "cluster_ids")


class UnbindManagerUserSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = account_schemas.UnbindManagerUserSchema()

    def _sample(self):
        return {
            "cluster_id": "cluster-id-0001",
            "cluster_username": "clusteruser",
            "signature": "signature",
        }

    def test_valid_unbind(self):
        data = self._sample()
        self.assertEqual(self.schema.load(data), data)

    def test_all_fields_required(self):
        for field in ("cluster_id", "cluster_username", "signature"):
            data = self._sample()
            del data[field]
            _assert_load_errors(self.schema, data, field)

    def test_empty_cluster_username_rejected(self):
        data = self._sample()
        data["cluster_username"] = ""
        _assert_load_errors(self.schema, data, "cluster_username")


class ClusterSyncSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = account_schemas.ClusterSyncSchema()

    def test_valid_sync(self):
        data = self.schema.load({"cluster_id": "cluster-id-0001", "cluster_ip": "192.168.0.100"})
        self.assertEqual(data["cluster_id"], "cluster-id-0001")

    def test_all_fields_required(self):
        _assert_load_errors(self.schema, {"cluster_id": "cluster-id-0001"}, "cluster_ip")
        _assert_load_errors(self.schema, {"cluster_ip": "192.168.0.100"}, "cluster_id")

    def test_cluster_ip_max_length(self):
        self.schema.load({"cluster_id": "cluster-id-0001", "cluster_ip": "x" * 16})
        _assert_load_errors(
            self.schema, {"cluster_id": "cluster-id-0001", "cluster_ip": "x" * 17}, "cluster_ip"
        )


class GenerateTokenSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = account_schemas.GenerateTokenSchema()

    def test_valid_token(self):
        data = self.schema.load({"client_id": "client-0001", "access_token": "token-0001"})
        self.assertEqual(data["client_id"], "client-0001")

    def test_client_id_boundary(self):
        self.schema.load({"client_id": "x" * 48, "access_token": "t"})
        _assert_load_errors(self.schema, {"client_id": "x" * 49, "access_token": "t"}, "client_id")

    def test_access_token_boundary(self):
        self.schema.load({"client_id": "c", "access_token": "x" * 255})
        _assert_load_errors(self.schema, {"client_id": "c", "access_token": "x" * 256}, "access_token")


if __name__ == "__main__":
    unittest.main()
