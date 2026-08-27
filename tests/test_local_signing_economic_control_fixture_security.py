# SPDX-License-Identifier: Apache-2.0
"""Foundation115 static security and public-data conformance tests."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

import local_signing_fixture_test_support as support

FOUNDATION115_FILES = (
    "local_signing_fixture_test_support.py",
    "test_local_signing_economic_control_fixture_schema.py",
    "test_local_signing_economic_control_fixture_profiles.py",
    "test_local_signing_economic_control_fixture_security.py",
)
ALLOWED_IMPORT_ROOTS = frozenset(
    {
        "__future__",
        "ast",
        "copy",
        "hashlib",
        "json",
        "re",
        "unittest",
        "collections",
        "pathlib",
        "typing",
        "local_signing_fixture_test_support",
    }
)
FORBIDDEN_IMPORT_ROOTS = frozenset(
    {
        "socket",
        "requests",
        "urllib",
        "httpx",
        "aiohttp",
        "websocket",
        "websockets",
        "bitcoinrpc",
        "subprocess",
        "nacl",
        "cryptography",
        "secrets",
        "os",
        "time",
        "datetime",
        "random",
        "uuid",
        "platform",
        "coin",
        "contracts",
        "wallet",
        "wallets",
        "web3",
        "bitcoin",
        "bitcoinlib",
    }
)
FORBIDDEN_CALL_NAMES = frozenset(
    {
        "__import__",
        "eval",
        "exec",
        "validate_transaction",
        "sign",
        "broadcast",
        "submit_transaction",
        "create_wallet",
        "import_key",
        "generate_key",
        "mine",
        "deploy",
        "getenv",
    }
)
FORBIDDEN_CALL_ATTRS = frozenset(
    {
        "write_text",
        "write_bytes",
        "unlink",
        "rmdir",
        "rename",
        "replace",
        "connect",
        "send",
        "sendall",
        "request",
        "urlopen",
        "Popen",
        "run",
        "system",
        "popen",
        "getenv",
        "time",
        "monotonic",
        "now",
        "utcnow",
        "today",
        "uuid4",
        "token_bytes",
        "sign",
        "broadcast",
        "submit_transaction",
        "create_wallet",
        "import_key",
        "generate_key",
        "mine",
        "deploy",
    }
)
FORBIDDEN_FIXTURE_KEYS = frozenset(
    {
        "private_key",
        "seed",
        "seed_phrase",
        "mnemonic",
        "xprv",
        "wallet_secret",
        "wallet_password",
        "rpc_user",
        "rpc_password",
        "rpc_cookie",
        "credential",
        "credentials",
    }
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


def collect_forbidden_fixture_keys(value, path=""):
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in FORBIDDEN_FIXTURE_KEYS:
                found.append(child_path)
            found.extend(collect_forbidden_fixture_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(collect_forbidden_fixture_keys(child, f"{path}[{index}]"))
    return found


class TestLocalSigningEconomicControlFixtureSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = support.load_fixtures()
        cls.test_dir = Path(__file__).resolve().parent

    def test_foundation115_sources_are_stdlib_only_and_offline(self) -> None:
        for filename in FOUNDATION115_FILES:
            path = self.test_dir / filename
            self.assertTrue(path.is_file(), filename)
            source = path.read_text(encoding="utf-8")
            roots = import_roots(source)
            self.assertTrue(roots <= ALLOWED_IMPORT_ROOTS, (filename, roots))
            self.assertTrue(roots.isdisjoint(FORBIDDEN_IMPORT_ROOTS), filename)
            self.assertEqual(forbidden_calls(source), [], filename)

    def test_no_production_validation_signer_wallet_network_or_runtime_import(self) -> None:
        combined = "\n".join(
            (self.test_dir / filename).read_text(encoding="utf-8")
            for filename in FOUNDATION115_FILES
        )
        roots = import_roots(combined)
        for name in FORBIDDEN_IMPORT_ROOTS:
            self.assertNotIn(name, roots)
        tree = ast.parse(combined)
        called_names = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertNotIn("validate_transaction", called_names)
        self.assertNotIn("sign", called_names)
        self.assertNotIn("broadcast", called_names)
        self.assertNotIn("submit_transaction", called_names)

    def test_no_environment_or_system_clock_authority(self) -> None:
        for filename in FOUNDATION115_FILES:
            source = (self.test_dir / filename).read_text(encoding="utf-8")
            roots = import_roots(source)
            self.assertNotIn("os", roots)
            self.assertNotIn("time", roots)
            self.assertNotIn("datetime", roots)
            self.assertNotIn("platform", roots)
            self.assertNotIn("random", roots)
            self.assertNotIn("secrets", roots)
            self.assertNotIn("uuid", roots)

    def test_test_sources_have_no_file_mutation_calls(self) -> None:
        for filename in FOUNDATION115_FILES:
            source = (self.test_dir / filename).read_text(encoding="utf-8")
            attrs = {
                node.func.attr
                for node in ast.walk(ast.parse(source))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            }
            self.assertTrue(
                attrs.isdisjoint({"write_text", "write_bytes", "unlink", "rmdir", "rename", "replace"}),
                filename,
            )

    def test_fixtures_contain_no_secret_or_credential_properties(self) -> None:
        for fixture in self.fixtures:
            self.assertEqual(collect_forbidden_fixture_keys(fixture), [])
            probe = fixture["input"]["case_probe"]
            self.assertIn(probe["public_marker"], {"", support.DISPOSABLE_MARKER})
            if probe["public_marker"]:
                self.assertEqual(fixture["case_id"], "LSEC-CONF-v0.1-KEY-NEG-001")
                self.assertEqual(probe["public_value"], support.DISPOSABLE_MARKER)

    def test_fixture_strings_exclude_key_material_and_host_paths(self) -> None:
        for fixture in self.fixtures:
            for value in support.walk(fixture):
                if not isinstance(value, str):
                    continue
                self.assertFalse(value.startswith("xprv"))
                self.assertNotIn("BEGIN PRIVATE KEY", value)
                self.assertNotIn("BEGIN OPENSSH PRIVATE KEY", value)
            target = fixture["input"]["case_probe"]["target_path"]
            self.assertNotIn("/", target)
            self.assertNotIn("\\", target)

    def test_all_public_identities_are_fictional_and_non_address_metadata(self) -> None:
        for fixture in self.fixtures:
            identities = fixture["public_identities"]
            self.assertTrue(identities["payer_id"].startswith("fictional-"))
            self.assertTrue(identities["payee_id"].startswith("fictional-"))
            self.assertTrue(identities["operator_id"].startswith("fictional-"))
            self.assertTrue(all(value.startswith("fictional-") for value in identities["approver_ids"]))
            self.assertTrue(identities["signer_public_key_id"].startswith("fictional-public-key-id-"))
            self.assertEqual(fixture["input"]["intent"]["payer_id"], identities["payer_id"])
            self.assertEqual(fixture["input"]["intent"]["payee_id"], identities["payee_id"])

    def test_every_fixture_asserts_no_runtime_or_state_mutation(self) -> None:
        for fixture in self.fixtures:
            expected = fixture["expected"]["non_execution"]
            self.assertEqual(expected, support.NON_EXECUTION)
            safety = fixture["safety_assertions"]
            self.assertEqual(safety, support.SAFETY_ASSERTIONS)
            for flag in (
                "generates_or_imports_keys",
                "creates_or_imports_wallets",
                "signs",
                "broadcasts",
                "connects_network",
                "mutates_replay_state",
                "mutates_ledger",
                "activates_settlement",
                "changes_protocol_or_economics",
            ):
                self.assertIs(safety[flag], False)

    def test_authority_boundaries_remain_fixed_in_every_fixture(self) -> None:
        for fixture in self.fixtures:
            authority = fixture["authority_assertions"]
            self.assertEqual(authority, support.AUTHORITY_ASSERTIONS)
            self.assertIs(authority["l28_consensus_authority"], True)
            self.assertIs(authority["l28_settlement_authority"], True)
            self.assertIs(authority["validate_transaction_mandatory"], True)
            self.assertIs(authority["harness_evals_advisory_only"], True)
            self.assertIs(authority["bitcoin_external_evidence_only"], True)
            self.assertTrue(all(authority[flag] is False for flag in support.OVERRIDE_FLAGS))


if __name__ == "__main__":
    unittest.main()
