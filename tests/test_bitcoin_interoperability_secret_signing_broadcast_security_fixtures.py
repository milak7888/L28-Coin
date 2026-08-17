# SPDX-License-Identifier: Apache-2.0
"""Foundation 101 — isolated Bitcoin secret/signing/broadcast security checks.

Test-local evaluator only. This is not a wallet, key parser, BIP39 validator,
xprv decoder, RPC client, or signing implementation. Forbidden fields are
detected by exact documented field names. Disposable markers are never
treated as secrets, logged, printed, or echoed in evaluator results.
"""

from __future__ import annotations

import ast
import copy
import json
import re
import unittest
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = (
    REPO_ROOT / "conformance" / "bitcoin_interoperability" / "v0.1" / "fixtures"
)

PLAN_VERSION = "bitcoin-interoperability-conformance-plan/v0.1"
DESIGN_PROFILE = "bitcoin-interoperability-spec/v0.1"
FAMILY = "SEC"
BLOCKED = "BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION"

MARKER_KEY = "FORBIDDEN_FIELD_MARKER_NOT_A_KEY"
MARKER_MNEMONIC = "FORBIDDEN_FIELD_MARKER_NOT_A_MNEMONIC"
MARKER_XPRV = "FORBIDDEN_FIELD_MARKER_NOT_AN_XPRV"
MARKER_CREDENTIAL = "FORBIDDEN_FIELD_MARKER_NOT_A_CREDENTIAL"
ALLOWED_MARKERS = frozenset(
    {MARKER_KEY, MARKER_MNEMONIC, MARKER_XPRV, MARKER_CREDENTIAL}
)
FORBIDDEN_SECRET_FIELDS = frozenset(
    {
        "private_key",
        "seed_phrase",
        "mnemonic",
        "xprv",
        "rpc_user",
        "rpc_password",
        "rpc_cookie",
    }
)
MARKER_BY_FIELD = {
    "private_key": MARKER_KEY,
    "seed_phrase": MARKER_MNEMONIC,
    "mnemonic": MARKER_MNEMONIC,
    "xprv": MARKER_XPRV,
    "rpc_user": MARKER_CREDENTIAL,
    "rpc_password": MARKER_CREDENTIAL,
    "rpc_cookie": MARKER_CREDENTIAL,
}
SCAN_ROOTS = ("request", "bitcoin_evidence", "observer_views", "prior_accept_state")
SIGNING_OPERATION = "sign_bitcoin_transaction"
BROADCAST_OPERATION = "broadcast_bitcoin_transaction"

PLANNED = (
    ("fx-btc-v01-0030", "BTC-CONF-v0.1-SEC-NEG-001", "negative"),
    ("fx-btc-v01-0031", "BTC-CONF-v0.1-SEC-NEG-002", "negative"),
    ("fx-btc-v01-0032", "BTC-CONF-v0.1-SEC-NEG-003", "negative"),
    ("fx-btc-v01-0033", "BTC-CONF-v0.1-SEC-NEG-004", "negative"),
    ("fx-btc-v01-0034", "BTC-CONF-v0.1-SEC-NEG-005", "negative"),
    ("fx-btc-v01-0035", "BTC-CONF-v0.1-SEC-NEG-006", "negative"),
    ("fx-btc-v01-0036", "BTC-CONF-v0.1-SEC-NEG-007", "negative"),
    ("fx-btc-v01-0037", "BTC-CONF-v0.1-SEC-FCL-001", "fail_closed"),
)
PLANNED_FIXTURE_IDS = tuple(item[0] for item in PLANNED)
PLANNED_CASE_IDS = tuple(item[1] for item in PLANNED)

ROOT_KEYS = (
    "fixture_id",
    "plan_version",
    "design_profile",
    "case_id",
    "family",
    "polarity",
    "description",
    "fixed_clock",
    "test_policy",
    "bitcoin_evidence",
    "l28_invariants",
    "request",
    "expected",
    "safety",
)
ROOT_KEYS_WITH_OBSERVERS = (
    "fixture_id",
    "plan_version",
    "design_profile",
    "case_id",
    "family",
    "polarity",
    "description",
    "fixed_clock",
    "test_policy",
    "bitcoin_evidence",
    "observer_views",
    "l28_invariants",
    "request",
    "expected",
    "safety",
)
TEST_POLICY_KEYS = (
    "not_production_policy",
    "production_proof_architecture",
    "production_confirmation_count",
    "production_quorum",
    "test_min_confirmations",
    "test_observer_count",
    "test_require_merkle_path",
    "test_require_network_identity",
)
L28_INVARIANT_KEYS = (
    "protocol_version",
    "hard_cap_l28",
    "emission_ceiling_l28",
    "historically_mined_l28",
    "treasury_locked_l28",
    "circulating_snapshot_l28",
    "issuance_mechanism",
    "height_authority",
    "historical_evidence",
    "adapter_override_allowed",
)
L28_INVARIANTS = {
    "protocol_version": "1.0.0",
    "hard_cap_l28": 28000000,
    "emission_ceiling_l28": 11130000,
    "historically_mined_l28": 2824584,
    "treasury_locked_l28": 500000,
    "circulating_snapshot_l28": 2324584,
    "issuance_mechanism": "coinbase_only",
    "height_authority": "consensus_derived",
    "historical_evidence": "immutable",
    "adapter_override_allowed": False,
}
SAFETY_KEYS = (
    "contains_private_keys",
    "contains_credentials",
    "uses_real_wallet",
    "uses_real_balance",
    "uses_real_transaction",
    "network_call_performed",
    "signing_performed",
    "broadcast_performed",
    "ledger_mutated",
    "settlement_finalized",
    "spend_authorized",
    "execution_authorized",
    "adapter_override_allowed",
)
GRANT_FLAGS = (
    "execution_authorized",
    "spend_authorized",
    "signing_authorized",
    "broadcast_authorized",
    "ledger_mutated",
    "settlement_finalized",
    "transaction_submitted",
    "l28_issuance_authorized",
    "adapter_override_allowed",
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
        "coin",
        "contracts",
        "subprocess",
        "nacl",
        "cryptography",
        "importlib",
    }
)
ALLOWED_IMPORT_ROOTS = frozenset(
    {
        "__future__",
        "ast",
        "copy",
        "json",
        "re",
        "unittest",
        "collections",
        "pathlib",
        "typing",
    }
)
FORBIDDEN_DYNAMIC_ATTRS = frozenset(
    {
        ("os", "system"),
        ("os", "popen"),
        ("os", "exec"),
        ("subprocess", "run"),
        ("subprocess", "call"),
        ("subprocess", "Popen"),
        ("subprocess", "check_output"),
        ("subprocess", "check_call"),
        ("importlib", "import_module"),
        ("importlib", "__import__"),
    }
)
PROTECTED_JSON_FRAGMENTS = (
    '"hard_cap_l28": 28000000',
    '"emission_ceiling_l28": 11130000',
    '"historically_mined_l28": 2824584',
    '"treasury_locked_l28": 500000',
    '"circulating_snapshot_l28": 2324584',
    '"issuance_mechanism": "coinbase_only"',
    '"height_authority": "consensus_derived"',
    '"historical_evidence": "immutable"',
    '"adapter_override_allowed": false',
    '"protocol_version": "1.0.0"',
)
CASE_ID_RE = re.compile(r"^BTC-CONF-v0\.1-SEC-(NEG|FCL)-\d{3}$")
FIXTURE_ID_RE = re.compile(r"^fx-btc-v01-003[0-7]$")


class DuplicateKeyError(ValueError):
    pass


def _object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise DuplicateKeyError(key)
        out[key] = value
    return out


def strict_loads(text: str) -> Any:
    return json.loads(
        text,
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)),
        object_pairs_hook=_object_pairs_hook,
    )


def load_fixture_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if "\t" in text:
        raise AssertionError(f"tabs forbidden in {path}")
    obj = strict_loads(text)
    if not isinstance(obj, dict):
        raise AssertionError(f"fixture root must be object: {path}")
    return obj


def discover_sec_fixture_paths() -> list[Path]:
    by_id = {fid: FIXTURE_DIR / f"{fid}.json" for fid in PLANNED_FIXTURE_IDS}
    missing = [fid for fid, path in by_id.items() if not path.is_file()]
    if missing:
        raise AssertionError(f"missing fixtures: {missing}")
    extra = sorted(
        path.stem
        for path in FIXTURE_DIR.glob("fx-btc-v01-003[0-7].json")
        if path.stem not in by_id
    )
    if extra:
        raise AssertionError(f"unexpected Foundation101 fixtures: {extra}")
    return [by_id[fid] for fid in PLANNED_FIXTURE_IDS]


def imported_module_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def forbidden_executable_calls(source: str) -> list[str]:
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in {"__import__", "eval", "exec"}:
            found.append(func.id)
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            pair = (func.value.id, func.attr)
            if pair in FORBIDDEN_DYNAMIC_ATTRS:
                found.append(f"{func.value.id}.{func.attr}")
    return found


def find_forbidden_secret_field(node: Any, path: str) -> str | None:
    """Return the first forbidden field path. Does not copy or return values."""
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}" if path else key
            if key in FORBIDDEN_SECRET_FIELDS:
                return child
            found = find_forbidden_secret_field(value, child)
            if found is not None:
                return found
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found = find_forbidden_secret_field(item, f"{path}[{index}]")
            if found is not None:
                return found
    return None


def find_unauthorized_signing_grant(node: Any, path: str) -> str | None:
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}" if path else key
            if key == "signing_authorized" and value is True:
                return child
            found = find_unauthorized_signing_grant(value, child)
            if found is not None:
                return found
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found = find_unauthorized_signing_grant(item, f"{path}[{index}]")
            if found is not None:
                return found
    return None


def collect_secret_field_values(node: Any, found: list[tuple[str, Any]]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in FORBIDDEN_SECRET_FIELDS:
                found.append((key, value))
            collect_secret_field_values(value, found)
    elif isinstance(node, list):
        for item in node:
            collect_secret_field_values(item, found)


def _reject(code: str, category: str, field_path: str) -> dict[str, Any]:
    return {
        "outcome": "reject",
        "ok": False,
        "code": code,
        "execution_authorized": False,
        "spend_authorized": False,
        "signing_authorized": False,
        "broadcast_authorized": False,
        "ledger_mutated": False,
        "settlement_finalized": False,
        "transaction_submitted": False,
        "l28_issuance_authorized": False,
        "adapter_override_allowed": False,
        "result": None,
        "error": {
            "code": code,
            "category": category,
            "field_path": field_path,
        },
    }


def evaluate_security(fx: dict[str, Any]) -> dict[str, Any]:
    """Test-local SEC evaluator. Not a production adapter.

    Detects documented forbidden field names only. Never logs, prints, or
    echoes marker values. Never signs, broadcasts, or parses credentials.
    """
    invariants = fx.get("l28_invariants")
    if not isinstance(invariants, dict) or invariants != L28_INVARIANTS:
        return _reject("adapter_override_forbidden", "economic_override", "l28_invariants")

    policy = fx.get("test_policy")
    if not isinstance(policy, dict) or policy.get("not_production_policy") is not True:
        return _reject("schema_invalid", "policy", "test_policy")
    for key in (
        "production_proof_architecture",
        "production_confirmation_count",
        "production_quorum",
    ):
        if policy.get(key) != BLOCKED:
            return _reject("schema_invalid", "policy", f"test_policy.{key}")

    for root_name in SCAN_ROOTS:
        if root_name not in fx:
            continue
        secret_path = find_forbidden_secret_field(fx[root_name], root_name)
        if secret_path is not None:
            return _reject("secret_material_forbidden", "secret_field", secret_path)

    for root_name in SCAN_ROOTS:
        if root_name not in fx:
            continue
        grant_path = find_unauthorized_signing_grant(fx[root_name], root_name)
        if grant_path is not None:
            return _reject("authority_denied", "unauthorized_grant", grant_path)

    request = fx.get("request")
    if not isinstance(request, dict):
        return _reject("schema_invalid", "request", "request")
    operation = request.get("operation")
    if operation == SIGNING_OPERATION:
        return _reject("operation_unsupported", "signing", "request.operation")
    if operation == BROADCAST_OPERATION:
        return _reject("operation_unsupported", "broadcast", "request.operation")
    return _reject("schema_invalid", "request", "request")


class TestBitcoinInteroperabilitySecretSigningBroadcastSecurityFixtures(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_sec_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]
        cls.by_fixture_id = {fx["fixture_id"]: fx for fx in cls.fixtures}
        cls.by_case_id = {fx["case_id"]: fx for fx in cls.fixtures}

    def test_exactly_eight_foundation101_sec_fixtures(self) -> None:
        self.assertTrue(FIXTURE_DIR.is_dir())
        self.assertEqual(len(self.paths), 8)
        self.assertEqual([p.stem for p in self.paths], list(PLANNED_FIXTURE_IDS))

    def test_unique_fixture_and_case_ids(self) -> None:
        fixture_ids = [fx["fixture_id"] for fx in self.fixtures]
        case_ids = [fx["case_id"] for fx in self.fixtures]
        self.assertEqual(fixture_ids, list(PLANNED_FIXTURE_IDS))
        self.assertEqual(case_ids, list(PLANNED_CASE_IDS))
        self.assertEqual(len(set(fixture_ids)), 8)
        self.assertEqual(len(set(case_ids)), 8)

    def test_exact_case_fixture_mapping(self) -> None:
        for fixture_id, case_id, polarity in PLANNED:
            fx = self.by_fixture_id[fixture_id]
            self.assertEqual(fx["case_id"], case_id)
            self.assertEqual(fx["polarity"], polarity)
            self.assertEqual(fx["family"], FAMILY)
            self.assertRegex(fx["fixture_id"], FIXTURE_ID_RE)
            self.assertRegex(fx["case_id"], CASE_ID_RE)

    def test_polarity_counts(self) -> None:
        counts = Counter(fx["polarity"] for fx in self.fixtures)
        self.assertEqual(counts["negative"], 7)
        self.assertEqual(counts["fail_closed"], 1)
        self.assertEqual(counts["positive"], 0)

    def test_conceptual_fields_and_blocked_production_policy(self) -> None:
        for fx in self.fixtures:
            expected_keys = (
                ROOT_KEYS_WITH_OBSERVERS if "observer_views" in fx else ROOT_KEYS
            )
            self.assertEqual(tuple(fx.keys()), expected_keys)
            self.assertEqual(fx["plan_version"], PLAN_VERSION)
            self.assertEqual(fx["design_profile"], DESIGN_PROFILE)
            self.assertEqual(fx["family"], FAMILY)
            self.assertEqual(tuple(fx["test_policy"].keys()), TEST_POLICY_KEYS)
            self.assertIs(fx["test_policy"]["not_production_policy"], True)
            self.assertEqual(fx["test_policy"]["production_proof_architecture"], BLOCKED)
            self.assertEqual(fx["test_policy"]["production_confirmation_count"], BLOCKED)
            self.assertEqual(fx["test_policy"]["production_quorum"], BLOCKED)

    def test_exact_protected_l28_invariants(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(tuple(fx["l28_invariants"].keys()), L28_INVARIANT_KEYS)
            self.assertEqual(fx["l28_invariants"], L28_INVARIANTS)

    def test_protected_values_byte_for_byte_in_fixture_text(self) -> None:
        for path in self.paths:
            text = path.read_text(encoding="utf-8")
            for fragment in PROTECTED_JSON_FRAGMENTS:
                self.assertIn(fragment, text)

    def test_all_safety_flags_false_including_marker_fixtures(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(tuple(fx["safety"].keys()), SAFETY_KEYS)
            for key in SAFETY_KEYS:
                self.assertIs(fx["safety"][key], False)
            for key in GRANT_FLAGS:
                self.assertIs(fx["expected"][key], False)

    def test_only_documented_disposable_markers(self) -> None:
        for fx in self.fixtures:
            found: list[tuple[str, Any]] = []
            for root_name in SCAN_ROOTS:
                if root_name in fx:
                    collect_secret_field_values(fx[root_name], found)
            for field_name, value in found:
                self.assertEqual(value, MARKER_BY_FIELD[field_name])
                self.assertIn(value, ALLOWED_MARKERS)

    def test_neg_001_private_key_field(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-SEC-NEG-001"]
        self.assertIn("private_key", fx["request"])
        result = evaluate_security(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "secret_material_forbidden")
        self.assertEqual(result["error"]["field_path"], "request.private_key")

    def test_neg_002_seed_phrase_and_mnemonic(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-SEC-NEG-002"]
        self.assertIn("seed_phrase", fx["request"])
        self.assertIn("mnemonic", fx["request"])
        result = evaluate_security(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "secret_material_forbidden")
        self.assertEqual(result["error"]["field_path"], "request.seed_phrase")

    def test_neg_003_xprv_field(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-SEC-NEG-003"]
        self.assertIn("xprv", fx["request"])
        result = evaluate_security(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "secret_material_forbidden")
        self.assertEqual(result["error"]["field_path"], "request.xprv")

    def test_neg_004_rpc_credential_fields(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-SEC-NEG-004"]
        request = fx["request"]
        self.assertIn("rpc_user", request)
        self.assertIn("rpc_password", request)
        self.assertIn("rpc_cookie", request)
        result = evaluate_security(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "secret_material_forbidden")
        self.assertEqual(result["error"]["field_path"], "request.rpc_user")

    def test_neg_005_signing_attempt_unsupported(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-SEC-NEG-005"]
        self.assertEqual(fx["request"]["operation"], SIGNING_OPERATION)
        result = evaluate_security(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "operation_unsupported")
        self.assertIs(result["signing_authorized"], False)
        self.assertIs(fx["safety"]["signing_performed"], False)

    def test_neg_006_broadcast_attempt_unsupported(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-SEC-NEG-006"]
        self.assertEqual(fx["request"]["operation"], BROADCAST_OPERATION)
        result = evaluate_security(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "operation_unsupported")
        self.assertIs(result["broadcast_authorized"], False)
        self.assertIs(result["transaction_submitted"], False)
        self.assertIs(fx["safety"]["broadcast_performed"], False)

    def test_neg_007_signing_authorized_claim_denied(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-SEC-NEG-007"]
        self.assertIs(fx["observer_views"][0]["signing_authorized"], True)
        result = evaluate_security(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "authority_denied")
        self.assertIs(result["signing_authorized"], False)

    def test_fcl_001_nested_secret_field(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-SEC-FCL-001"]
        nested = fx["request"]["adapter_output"]["nested"]["witness"]
        self.assertIn("private_key", nested)
        result = evaluate_security(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "secret_material_forbidden")
        self.assertEqual(
            result["error"]["field_path"],
            "request.adapter_output.nested.witness.private_key",
        )

    def test_secret_detection_precedes_operation(self) -> None:
        fx = copy.deepcopy(self.by_case_id["BTC-CONF-v0.1-SEC-NEG-005"])
        fx["request"]["private_key"] = MARKER_KEY
        result = evaluate_security(fx)
        self.assertEqual(result["code"], "secret_material_forbidden")
        self.assertNotEqual(result["code"], "operation_unsupported")

    def test_evaluator_does_not_echo_marker_values(self) -> None:
        for fx in self.fixtures:
            result = evaluate_security(fx)
            dumped = json.dumps(result)
            for marker in ALLOWED_MARKERS:
                self.assertNotIn(marker, dumped)
            self.assertIs(result["signing_authorized"], False)
            self.assertIs(result["broadcast_authorized"], False)
            self.assertIs(result["transaction_submitted"], False)
            self.assertIs(result["ledger_mutated"], False)
            self.assertIs(result["settlement_finalized"], False)

    def test_input_objects_are_not_mutated(self) -> None:
        for fx in self.fixtures:
            snapshot = copy.deepcopy(fx)
            evaluate_security(fx)
            self.assertEqual(fx, snapshot)

    def test_evaluator_matches_every_fixture_expected(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(evaluate_security(fx), fx["expected"])

    def test_deterministic_repeated_evaluation(self) -> None:
        first = [evaluate_security(fx) for fx in self.fixtures]
        second = [evaluate_security(fx) for fx in self.fixtures]
        self.assertEqual(first, second)

    def test_ast_imports_are_stdlib_only_and_offline(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        imported = imported_module_names(source)
        self.assertTrue(imported <= ALLOWED_IMPORT_ROOTS)
        self.assertTrue(imported.isdisjoint(FORBIDDEN_IMPORT_ROOTS))
        self.assertEqual(forbidden_executable_calls(source), [])

    def test_no_signing_broadcast_mining_or_bridge_execution(self) -> None:
        imported = imported_module_names(Path(__file__).read_text(encoding="utf-8"))
        self.assertNotIn("coin", imported)
        self.assertNotIn("contracts", imported)
        for fx in self.fixtures:
            self.assertIs(fx["safety"]["signing_performed"], False)
            self.assertIs(fx["safety"]["broadcast_performed"], False)
            result = evaluate_security(fx)
            self.assertIs(result["signing_authorized"], False)
            self.assertIs(result["broadcast_authorized"], False)
            self.assertIs(result["transaction_submitted"], False)

    def test_no_l28_economic_or_height_authority(self) -> None:
        for fx in self.fixtures:
            result = evaluate_security(fx)
            self.assertIs(result["adapter_override_allowed"], False)
            self.assertIs(result["l28_issuance_authorized"], False)
            self.assertEqual(fx["l28_invariants"]["height_authority"], "consensus_derived")


if __name__ == "__main__":
    unittest.main()
