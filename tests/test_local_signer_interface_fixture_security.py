# SPDX-License-Identifier: Apache-2.0
"""Foundation121 static security, authority, and public-data tests."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

import local_signer_interface_fixture_test_support as support

FOUNDATION121_FILES = (
    "local_signer_interface_fixture_test_support.py",
    "test_local_signer_interface_fixture_profiles.py",
    "test_local_signer_interface_fixture_schema.py",
    "test_local_signer_interface_fixture_security.py",
)
ALLOWED_IMPORT_ROOTS = frozenset(
    {"__future__", "ast", "copy", "hashlib", "json", "re", "unittest", "collections", "pathlib", "typing", "local_signer_interface_fixture_test_support"}
)
FORBIDDEN_IMPORT_ROOTS = frozenset(
    {"socket", "requests", "urllib", "http", "httpx", "aiohttp", "websocket", "websockets", "bitcoinrpc", "subprocess", "nacl", "cryptography", "secrets", "os", "time", "datetime", "random", "uuid", "platform", "coin", "contracts", "wallet", "wallets", "web3", "bitcoin", "bitcoinlib"}
)
FORBIDDEN_CALL_NAMES = frozenset(
    {"__import__", "eval", "exec", "validate_transaction", "sign", "broadcast", "submit_transaction", "create_wallet", "import_key", "generate_key", "mine", "deploy", "getenv"}
)
FORBIDDEN_CALL_ATTRS = frozenset(
    {"write_text", "write_bytes", "unlink", "rmdir", "rename", "replace", "connect", "send", "sendall", "request", "urlopen", "Popen", "run", "system", "popen", "getenv", "time", "monotonic", "now", "utcnow", "today", "uuid4", "token_bytes", "sign", "broadcast", "submit_transaction", "create_wallet", "import_key", "generate_key", "mine", "deploy"}
)
FORBIDDEN_FIXTURE_KEYS = frozenset(
    {"private_key", "seed", "seed_phrase", "mnemonic", "xprv", "keystore", "wallet_secret", "wallet_password", "rpc_user", "rpc_password", "rpc_cookie", "credential", "credentials"}
)


def import_roots(source: str) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def forbidden_calls(source: str) -> list[str]:
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALL_NAMES:
            found.append(node.func.id)
        elif isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_CALL_ATTRS:
            found.append(node.func.attr)
    return found


def collect_forbidden_keys(value: object, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in FORBIDDEN_FIXTURE_KEYS:
                found.append(child_path)
            found.extend(collect_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(collect_forbidden_keys(child, f"{path}[{index}]"))
    return found


class TestLocalSignerInterfaceFixtureSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = support.load_fixtures()
        cls.test_dir = Path(__file__).resolve().parent

    def test_protected_economic_facts_are_exact_and_immutable(self) -> None:
        for fixture in self.fixtures:
            self.assertEqual(fixture["protected_economic_facts"], support.PROTECTED_ECONOMICS)
            self.assertEqual(tuple(fixture["protected_economic_facts"]), support.ORDERS["protected_economic_facts"])
            self.assertEqual(fixture["protected_economic_facts"]["issuance_mechanism"], "coinbase_only")
            self.assertEqual(fixture["protected_economic_facts"]["canonical_height_authority"], "consensus_derived")
            self.assertIs(fixture["protected_economic_facts"]["historical_evidence_mutable"], False)

    def test_authority_assertions_are_exact_in_fixture_request_and_response(self) -> None:
        for fixture in self.fixtures:
            request = fixture["input"]["request"]
            response = fixture["expected"]["response"]
            self.assertEqual(fixture["authority_assertions"], support.AUTHORITY_ASSERTIONS)
            self.assertEqual(request["authority_assertions"], support.AUTHORITY_ASSERTIONS)
            self.assertEqual(response["authority_assertions"], support.AUTHORITY_ASSERTIONS)

    def test_every_authority_override_flag_is_false(self) -> None:
        self.assertEqual(set(support.OVERRIDE_FLAGS), {"issuance_override_allowed", "supply_override_allowed", "height_override_allowed", "validation_override_allowed", "consensus_override_allowed", "history_override_allowed", "settlement_override_allowed"})
        for fixture in self.fixtures:
            for authority in (fixture["authority_assertions"], fixture["input"]["request"]["authority_assertions"], fixture["expected"]["response"]["authority_assertions"]):
                self.assertTrue(all(authority[name] is False for name in support.OVERRIDE_FLAGS))
                self.assertIs(authority["authorization_equals_validation"], False)
                self.assertIs(authority["eligibility_equals_invocation"], False)
                self.assertIs(authority["signer_may_override_protocol"], False)

    def test_all_17_request_and_response_non_execution_flags_are_false(self) -> None:
        self.assertEqual(len(support.NON_EXECUTION), 17)
        for fixture in self.fixtures:
            request_flags = fixture["input"]["request"]["non_execution"]
            response_flags = fixture["expected"]["response"]["non_execution"]
            self.assertEqual(request_flags, support.NON_EXECUTION)
            self.assertEqual(response_flags, support.NON_EXECUTION)
            self.assertTrue(all(value is False for value in request_flags.values()))
            self.assertTrue(all(value is False for value in response_flags.values()))

    def test_safety_assertions_are_exact_and_non_activating(self) -> None:
        for fixture in self.fixtures:
            self.assertEqual(fixture["safety_assertions"], support.SAFETY_ASSERTIONS)
            self.assertIs(fixture["safety_assertions"]["public_fictional_data_only"], True)
            self.assertTrue(all(value is False for key, value in fixture["safety_assertions"].items() if key != "public_fictional_data_only"))

    def test_fixtures_contain_no_secret_or_credential_properties(self) -> None:
        secret_probe_cases: list[str] = []
        for fixture in self.fixtures:
            self.assertEqual(collect_forbidden_keys(fixture), [])
            probe = fixture["input"]["case_probe"]
            if probe["public_marker"]:
                secret_probe_cases.append(fixture["case_id"])
                self.assertEqual(probe["public_marker"], support.DISPOSABLE_MARKER)
                if isinstance(probe["public_value"], dict):
                    self.assertEqual(probe["public_value"]["secret_marker"], support.DISPOSABLE_MARKER)
                else:
                    self.assertEqual(probe["public_value"], support.DISPOSABLE_MARKER)
        self.assertEqual(
            set(secret_probe_cases),
            {"LSI-CONF-v0.1-PRE-BND-001", "LSI-CONF-v0.1-IDN-NEG-001"},
        )

    def test_fixture_values_exclude_actual_key_material_and_host_paths(self) -> None:
        for fixture in self.fixtures:
            for value in support.walk(fixture):
                if isinstance(value, str):
                    self.assertFalse(value.startswith("xprv"))
                    self.assertNotIn("BEGIN PRIVATE KEY", value)
                    self.assertNotIn("BEGIN OPENSSH PRIVATE KEY", value)
            target = fixture["input"]["case_probe"]["target_path"]
            self.assertNotIn("/", target)
            self.assertNotIn("\\", target)

    def test_public_identity_labels_are_fixed_and_disposable(self) -> None:
        for fixture in self.fixtures:
            identities = fixture["public_identities"]
            self.assertEqual(identities, support.PUBLIC_IDENTITIES)
            self.assertTrue(all("public" in value for key, value in identities.items() if key != "approver_ids"))
            self.assertTrue(all("public" in value for value in identities["approver_ids"]))

    def test_foundation121_sources_are_stdlib_only_and_offline(self) -> None:
        for filename in FOUNDATION121_FILES:
            source = (self.test_dir / filename).read_text(encoding="utf-8")
            roots = import_roots(source)
            self.assertTrue(roots <= ALLOWED_IMPORT_ROOTS, (filename, roots))
            self.assertTrue(roots.isdisjoint(FORBIDDEN_IMPORT_ROOTS), filename)
            self.assertEqual(forbidden_calls(source), [], filename)

    def test_no_production_validation_signer_wallet_network_or_runtime_import(self) -> None:
        combined = "\n".join((self.test_dir / filename).read_text(encoding="utf-8") for filename in FOUNDATION121_FILES)
        roots = import_roots(combined)
        self.assertTrue(roots.isdisjoint(FORBIDDEN_IMPORT_ROOTS))
        called_names = {
            node.func.id for node in ast.walk(ast.parse(combined))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue(called_names.isdisjoint(FORBIDDEN_CALL_NAMES))

    def test_no_environment_system_clock_or_nondeterministic_source(self) -> None:
        for filename in FOUNDATION121_FILES:
            source = (self.test_dir / filename).read_text(encoding="utf-8")
            roots = import_roots(source)
            self.assertTrue(roots.isdisjoint({"os", "time", "datetime", "platform", "random", "secrets", "uuid"}), filename)

    def test_test_sources_have_no_file_mutation_calls(self) -> None:
        for filename in FOUNDATION121_FILES:
            source = (self.test_dir / filename).read_text(encoding="utf-8")
            attrs = {
                node.func.attr for node in ast.walk(ast.parse(source))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            }
            self.assertTrue(attrs.isdisjoint({"write_text", "write_bytes", "unlink", "rmdir", "rename", "replace"}), filename)

    def test_fixture_directory_contains_json_data_only(self) -> None:
        entries = sorted(support.FIXTURE_DIR.iterdir())
        self.assertEqual(len(entries), 100)
        self.assertTrue(all(path.is_file() and path.suffix == ".json" for path in entries))

    def test_transaction_projection_never_creates_issuance(self) -> None:
        for fixture in self.fixtures:
            transaction = fixture["input"]["request"]["proposed_transaction"]
            self.assertEqual(transaction["type"], "transfer")
            self.assertIs(transaction["coinbase"], False)
            self.assertNotEqual(transaction["sender"], "COINBASE")

    def test_fixture_values_have_no_floats_and_declared_hashes_are_lower_hex(self) -> None:
        for fixture in self.fixtures:
            for value in support.walk(fixture):
                self.assertNotIsInstance(value, float)
            for name in support.ORDERS["canonical"][2:]:
                self.assertRegex(fixture["canonical"][name], support.HEX64)


if __name__ == "__main__":
    unittest.main()
