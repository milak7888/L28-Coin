# SPDX-License-Identifier: Apache-2.0
"""Foundation 104 — isolated Bitcoin deterministic serialization checks.

Test-local evaluator and canonical serializer only. This is not a production
adapter. No system clock, environment, network, random, or UUID values are
read or generated. Caller input is never mutated or repaired.
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
FAMILY = "DET"
BLOCKED = "BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION"
ACCEPT_CODE = "bitcoin_observation_ok"
SCHEMA_INVALID = "schema_invalid"
REQUIRED_STATE = "required_state_unavailable"

TXID_A = "a" * 64
TXID_B = "b" * 64
BLOCK_A = "c" * 64
HEX64_LOWER = re.compile(r"^[0-9a-f]{64}$")
HEX_ID_KEYS = ("txid", "block_hash")

PLANNED = (
    ("fx-btc-v01-0052", "BTC-CONF-v0.1-DET-POS-001", "positive"),
    ("fx-btc-v01-0053", "BTC-CONF-v0.1-DET-POS-002", "positive"),
    ("fx-btc-v01-0054", "BTC-CONF-v0.1-DET-NEG-001", "negative"),
    ("fx-btc-v01-0055", "BTC-CONF-v0.1-DET-NEG-002", "negative"),
    ("fx-btc-v01-0056", "BTC-CONF-v0.1-DET-BND-001", "boundary"),
    ("fx-btc-v01-0057", "BTC-CONF-v0.1-DET-FCL-001", "fail_closed"),
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
STRICT_REQUEST_KEYS = frozenset(
    {
        "evidence_domain",
        "declared_network",
        "execution_authorized",
        "spend_authorized",
        "txid",
        "block_hash",
        "output_index",
        "amount_satoshis",
        "raw_public_input",
        "public_state_available",
        "required_public_state",
        "forbidden_inference",
    }
)
CANONICAL_OUTCOME_KEYS = (
    "outcome",
    "ok",
    "code",
    "native_asset",
    *GRANT_FLAGS,
    "result",
    "error",
)
CANONICAL_RESULT_KEYS = (
    "evidence_domain",
    "bitcoin_network",
    "native_asset",
    "asset_id",
    "txid",
    "block_hash",
    "output_index",
    "amount_satoshis",
    "l28_network_identity",
    *GRANT_FLAGS,
)
CANONICAL_ERROR_KEYS = ("code", "category", "field_path")
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
        "bitcoinlib",
        "bit",
        "coincurve",
        "ecdsa",
        "web3",
        "bitcoin",
        "os",
        "shutil",
        "time",
        "datetime",
        "random",
        "secrets",
        "uuid",
        "platform",
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
        ("os", "getenv"),
        ("os", "environ"),
        ("time", "time"),
        ("time", "monotonic"),
        ("datetime", "now"),
        ("datetime", "utcnow"),
        ("date", "today"),
        ("random", "random"),
        ("secrets", "token_bytes"),
        ("uuid", "uuid4"),
        ("uuid", "uuid1"),
        ("subprocess", "run"),
        ("subprocess", "call"),
        ("subprocess", "Popen"),
        ("importlib", "import_module"),
        ("coin", "multi_coin_miner"),
        ("contracts", "deploy_bridge"),
    }
)
FORBIDDEN_NAME_CALLS = frozenset(
    {
        "__import__",
        "eval",
        "exec",
        "validate_transaction",
        "mint",
        "getenv",
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
CASE_ID_RE = re.compile(r"^BTC-CONF-v0\.1-DET-(POS|NEG|BND|FCL)-\d{3}$")
FIXTURE_ID_RE = re.compile(r"^fx-btc-v01-005[2-7]$")


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


def discover_det_fixture_paths() -> list[Path]:
    by_id = {fid: FIXTURE_DIR / f"{fid}.json" for fid in PLANNED_FIXTURE_IDS}
    missing = [fid for fid, path in by_id.items() if not path.is_file()]
    if missing:
        raise AssertionError(f"missing fixtures: {missing}")
    extra = sorted(
        path.stem
        for path in FIXTURE_DIR.glob("fx-btc-v01-005[2-7].json")
        if path.stem not in by_id
    )
    if extra:
        raise AssertionError(f"unexpected Foundation104 fixtures: {extra}")
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


def imported_full_module_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            for alias in node.names:
                names.add(f"{node.module}.{alias.name}")
    return names


def forbidden_executable_calls(source: str) -> list[str]:
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in FORBIDDEN_NAME_CALLS:
            found.append(func.id)
        elif isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name):
                pair = (func.value.id, func.attr)
                if pair in FORBIDDEN_DYNAMIC_ATTRS:
                    found.append(f"{func.value.id}.{func.attr}")
                if func.attr in FORBIDDEN_NAME_CALLS:
                    found.append(f"{func.value.id}.{func.attr}")
            if func.attr in {"write_text", "write_bytes", "unlink", "rmtree"}:
                found.append(func.attr)
    return found


def _grant_false() -> dict[str, bool]:
    return {key: False for key in GRANT_FLAGS}


def _ordered(mapping: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: mapping[key] for key in keys if key in mapping}


def serialize_public_outcome(outcome: dict[str, Any]) -> bytes:
    """Deterministic UTF-8 JSON. Documented field order. Not repr()."""
    ordered = _ordered(outcome, CANONICAL_OUTCOME_KEYS)
    result = ordered.get("result")
    if isinstance(result, dict):
        ordered["result"] = _ordered(result, CANONICAL_RESULT_KEYS)
    error = ordered.get("error")
    if isinstance(error, dict):
        ordered["error"] = _ordered(error, CANONICAL_ERROR_KEYS)
    return json.dumps(
        ordered,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _reject(code: str, category: str, field_path: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "outcome": "reject",
        "ok": False,
        "code": code,
        "native_asset": False,
        "result": None,
        "error": {
            "code": code,
            "category": category,
            "field_path": field_path,
        },
    }
    payload.update(_grant_false())
    return payload


def _accept(evidence: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "evidence_domain": "bitcoin",
        "bitcoin_network": evidence["bitcoin_network"],
        "native_asset": False,
        "asset_id": "BTC-EXTERNAL",
        "txid": request["txid"],
        "block_hash": request["block_hash"],
        "output_index": request["output_index"],
        "amount_satoshis": request["amount_satoshis"],
        "l28_network_identity": None,
    }
    result.update(_grant_false())
    payload: dict[str, Any] = {
        "outcome": "accept",
        "ok": True,
        "code": ACCEPT_CODE,
        "native_asset": False,
        "result": result,
        "error": None,
    }
    payload.update(_grant_false())
    return payload


def _unknown_request_path(request: dict[str, Any]) -> str | None:
    for key in request:
        if key not in STRICT_REQUEST_KEYS:
            return f"request.{key}"
    return None


def _hex_field_path(node: dict[str, Any], prefix: str) -> str | None:
    for key in HEX_ID_KEYS:
        if key not in node:
            continue
        value = node[key]
        if not isinstance(value, str) or HEX64_LOWER.fullmatch(value) is None:
            return f"{prefix}.{key}"
    return None


def evaluate_deterministic(fx: dict[str, Any]) -> dict[str, Any]:
    """Test-local DET evaluator. Not a production serializer or adapter.

    Unknown fields, duplicate keys, and noncanonical hex are rejected without
    repair. Missing public state is never inferred from clock, network, or
    environment. Inputs are never mutated.
    """
    invariants = fx.get("l28_invariants")
    if not isinstance(invariants, dict) or invariants != L28_INVARIANTS:
        return _reject(SCHEMA_INVALID, "schema", "l28_invariants")

    request = fx.get("request")
    if not isinstance(request, dict):
        return _reject(SCHEMA_INVALID, "schema", "request")

    unknown = _unknown_request_path(request)
    if unknown is not None:
        return _reject(SCHEMA_INVALID, "schema", unknown)

    raw = request.get("raw_public_input")
    if isinstance(raw, str):
        try:
            strict_loads(raw)
        except DuplicateKeyError:
            return _reject(SCHEMA_INVALID, "schema", "request.raw_public_input")
        except ValueError:
            return _reject(SCHEMA_INVALID, "schema", "request.raw_public_input")

    if request.get("public_state_available") is False:
        return _reject(REQUIRED_STATE, "required_state", "request.public_state_available")

    hex_path = _hex_field_path(request, "request")
    if hex_path is not None:
        return _reject(SCHEMA_INVALID, "schema", hex_path)
    evidence = fx.get("bitcoin_evidence")
    if not isinstance(evidence, dict):
        return _reject(SCHEMA_INVALID, "schema", "bitcoin_evidence")
    hex_path = _hex_field_path(evidence, "bitcoin_evidence")
    if hex_path is not None:
        return _reject(SCHEMA_INVALID, "schema", hex_path)

    if evidence.get("evidence_domain") != "bitcoin":
        return _reject(SCHEMA_INVALID, "schema", "bitcoin_evidence.evidence_domain")
    if evidence.get("native_asset") is not False:
        return _reject(SCHEMA_INVALID, "schema", "bitcoin_evidence.native_asset")
    if request.get("evidence_domain") != "bitcoin":
        return _reject(SCHEMA_INVALID, "schema", "request.evidence_domain")
    if request.get("declared_network") != evidence.get("bitcoin_network"):
        return _reject(SCHEMA_INVALID, "schema", "request.declared_network")
    for key in ("txid", "block_hash", "output_index", "amount_satoshis"):
        if key not in request:
            return _reject(REQUIRED_STATE, "required_state", f"request.{key}")
    return _accept(evidence, request)


class TestBitcoinInteroperabilityDeterministicSerializationFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_det_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]
        cls.by_fixture_id = {fx["fixture_id"]: fx for fx in cls.fixtures}
        cls.by_case_id = {fx["case_id"]: fx for fx in cls.fixtures}

    def test_exactly_six_foundation104_det_fixtures(self) -> None:
        self.assertTrue(FIXTURE_DIR.is_dir())
        self.assertEqual(len(self.paths), 6)
        self.assertEqual([p.stem for p in self.paths], list(PLANNED_FIXTURE_IDS))

    def test_unique_fixture_and_case_ids(self) -> None:
        fixture_ids = [fx["fixture_id"] for fx in self.fixtures]
        case_ids = [fx["case_id"] for fx in self.fixtures]
        self.assertEqual(fixture_ids, list(PLANNED_FIXTURE_IDS))
        self.assertEqual(case_ids, list(PLANNED_CASE_IDS))
        self.assertEqual(len(set(fixture_ids)), 6)
        self.assertEqual(len(set(case_ids)), 6)

    def test_exact_case_fixture_mapping_0052_through_0057(self) -> None:
        for fixture_id, case_id, polarity in PLANNED:
            fx = self.by_fixture_id[fixture_id]
            self.assertEqual(fx["case_id"], case_id)
            self.assertEqual(fx["polarity"], polarity)
            self.assertEqual(fx["family"], FAMILY)
            self.assertRegex(fx["fixture_id"], FIXTURE_ID_RE)
            self.assertRegex(fx["case_id"], CASE_ID_RE)

    def test_family_is_det_and_polarity_counts(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(fx["family"], FAMILY)
        counts = Counter(fx["polarity"] for fx in self.fixtures)
        self.assertEqual(counts["positive"], 2)
        self.assertEqual(counts["negative"], 2)
        self.assertEqual(counts["boundary"], 1)
        self.assertEqual(counts["fail_closed"], 1)
        self.assertEqual(self.by_fixture_id["fx-btc-v01-0052"]["polarity"], "positive")
        self.assertEqual(self.by_fixture_id["fx-btc-v01-0053"]["polarity"], "positive")
        self.assertEqual(self.by_fixture_id["fx-btc-v01-0054"]["polarity"], "negative")
        self.assertEqual(self.by_fixture_id["fx-btc-v01-0055"]["polarity"], "negative")
        self.assertEqual(self.by_fixture_id["fx-btc-v01-0056"]["polarity"], "boundary")
        self.assertEqual(self.by_fixture_id["fx-btc-v01-0057"]["polarity"], "fail_closed")

    def test_conceptual_fields_and_blocked_production_policy(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(tuple(fx.keys()), ROOT_KEYS)
            self.assertEqual(fx["plan_version"], PLAN_VERSION)
            self.assertEqual(fx["design_profile"], DESIGN_PROFILE)
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

    def test_all_authority_and_safety_flags_false(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(tuple(fx["safety"].keys()), SAFETY_KEYS)
            for key in SAFETY_KEYS:
                self.assertIs(fx["safety"][key], False)
            result = evaluate_deterministic(fx)
            for key in GRANT_FLAGS:
                self.assertIs(fx["expected"][key], False)
                self.assertIs(result[key], False)

    def test_pos_001_byte_stable_canonical_output(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-DET-POS-001"]
        self.assertEqual(fx["request"]["txid"], TXID_A)
        self.assertEqual(fx["request"]["block_hash"], BLOCK_A)
        first = evaluate_deterministic(fx)
        second = evaluate_deterministic(copy.deepcopy(fx))
        self.assertEqual(first, fx["expected"])
        self.assertEqual(first, second)
        first_bytes = serialize_public_outcome(first)
        second_bytes = serialize_public_outcome(second)
        self.assertEqual(first_bytes, second_bytes)
        self.assertIsInstance(first_bytes, bytes)
        first_bytes.decode("utf-8")
        text = first_bytes.decode("utf-8")
        self.assertLess(text.index('"outcome"'), text.index('"ok"'))
        self.assertLess(text.index('"ok"'), text.index('"code"'))
        alphabetized = json.dumps(first, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.assertNotEqual(first_bytes, alphabetized)

    def test_pos_002_repeated_evaluation_identical(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-DET-POS-002"]
        snapshot = copy.deepcopy(fx)
        first = evaluate_deterministic(fx)
        second = evaluate_deterministic(fx)
        third = evaluate_deterministic(copy.deepcopy(fx))
        self.assertEqual(first, fx["expected"])
        self.assertEqual(first, second)
        self.assertEqual(second, third)
        self.assertEqual(serialize_public_outcome(first), serialize_public_outcome(second))
        self.assertEqual(serialize_public_outcome(second), serialize_public_outcome(third))
        self.assertEqual(fx, snapshot)

    def test_equivalent_public_inputs_are_byte_identical(self) -> None:
        pos1 = evaluate_deterministic(self.by_case_id["BTC-CONF-v0.1-DET-POS-001"])
        pos2 = evaluate_deterministic(self.by_case_id["BTC-CONF-v0.1-DET-POS-002"])
        bnd = evaluate_deterministic(self.by_case_id["BTC-CONF-v0.1-DET-BND-001"])
        self.assertEqual(serialize_public_outcome(pos1), serialize_public_outcome(pos2))
        self.assertEqual(serialize_public_outcome(pos2), serialize_public_outcome(bnd))

    def test_neg_001_duplicate_key_raw_input_schema_invalid(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-DET-NEG-001"]
        raw = fx["request"]["raw_public_input"]
        self.assertIsInstance(raw, str)
        self.assertEqual(raw.count('"txid"'), 2)
        self.assertIn(TXID_A, raw)
        self.assertIn(TXID_B, raw)
        with self.assertRaises(DuplicateKeyError):
            strict_loads(raw)
        silent = json.loads(raw)
        self.assertEqual(silent["txid"], TXID_B)
        result = evaluate_deterministic(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], SCHEMA_INVALID)
        self.assertIs(result["ok"], False)
        self.assertIs(result["result"], None)
        dumped = json.dumps(result)
        self.assertNotIn(TXID_A, dumped)
        self.assertNotIn(TXID_B, dumped)

    def test_neg_002_unknown_strict_field_schema_invalid(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-DET-NEG-002"]
        self.assertIn("unknown_strict_field", fx["request"])
        self.assertEqual(fx["request"]["unknown_strict_field"], "unsupported_adapter_extension")
        result = evaluate_deterministic(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], SCHEMA_INVALID)
        self.assertEqual(result["error"]["field_path"], "request.unknown_strict_field")
        self.assertIs(result["result"], None)

    def test_bnd_001_lowercase_canonical_hex_accepted(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-DET-BND-001"]
        self.assertEqual(fx["request"]["txid"], TXID_A)
        self.assertEqual(fx["request"]["block_hash"], BLOCK_A)
        self.assertEqual(fx["bitcoin_evidence"]["txid"], TXID_A)
        self.assertEqual(fx["bitcoin_evidence"]["block_hash"], BLOCK_A)
        result = evaluate_deterministic(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["outcome"], "accept")
        self.assertEqual(result["result"]["txid"], TXID_A)
        self.assertEqual(result["result"]["block_hash"], BLOCK_A)

    def test_bnd_001_uppercase_hex_is_never_repaired(self) -> None:
        fx = copy.deepcopy(self.by_case_id["BTC-CONF-v0.1-DET-BND-001"])
        original_fixture = copy.deepcopy(self.by_case_id["BTC-CONF-v0.1-DET-BND-001"])
        uppercase_txid = TXID_A.upper()
        fx["request"]["txid"] = uppercase_txid
        result = evaluate_deterministic(fx)
        self.assertEqual(result["outcome"], "reject")
        self.assertIs(result["ok"], False)
        self.assertEqual(result["code"], SCHEMA_INVALID)
        self.assertEqual(fx["request"]["txid"], uppercase_txid)
        self.assertNotEqual(fx["request"]["txid"], TXID_A)
        self.assertIs(result["result"], None)
        if isinstance(result.get("result"), dict):
            self.assertNotEqual(result["result"].get("txid"), TXID_A)
        self.assertEqual(self.by_case_id["BTC-CONF-v0.1-DET-BND-001"], original_fixture)

    def test_fcl_001_required_state_unavailable_without_inference(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-DET-FCL-001"]
        self.assertIs(fx["request"]["public_state_available"], False)
        self.assertEqual(fx["request"]["required_public_state"], "verification_time")
        self.assertEqual(
            fx["request"]["forbidden_inference"],
            ["system_clock", "network", "process_environment"],
        )
        result = evaluate_deterministic(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], REQUIRED_STATE)
        self.assertIs(result["ok"], False)
        self.assertIs(result["result"], None)
        self.assertNotEqual(result["code"], "bitcoin_observation_ok")

    def test_evaluator_does_not_use_fixture_clock_as_inference(self) -> None:
        fx = copy.deepcopy(self.by_case_id["BTC-CONF-v0.1-DET-FCL-001"])
        fx["fixed_clock"]["verification_time"] = 1700000100
        result = evaluate_deterministic(fx)
        self.assertEqual(result["code"], REQUIRED_STATE)
        self.assertIs(result["result"], None)

    def test_evaluator_matches_every_fixture_expected(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(evaluate_deterministic(fx), fx["expected"])

    def test_evaluator_does_not_mutate_request_fixture_or_invariants(self) -> None:
        for fx in self.fixtures:
            snapshot = copy.deepcopy(fx)
            request_snapshot = copy.deepcopy(fx["request"])
            invariant_snapshot = copy.deepcopy(fx["l28_invariants"])
            evaluate_deterministic(fx)
            self.assertEqual(fx, snapshot)
            self.assertEqual(fx["request"], request_snapshot)
            self.assertEqual(fx["l28_invariants"], invariant_snapshot)

    def test_deterministic_repeated_evaluation(self) -> None:
        first = [evaluate_deterministic(fx) for fx in self.fixtures]
        second = [evaluate_deterministic(fx) for fx in self.fixtures]
        third = [evaluate_deterministic(copy.deepcopy(fx)) for fx in self.fixtures]
        self.assertEqual(first, second)
        self.assertEqual(second, third)
        first_bytes = [serialize_public_outcome(item) for item in first]
        second_bytes = [serialize_public_outcome(item) for item in second]
        self.assertEqual(first_bytes, second_bytes)

    def test_ast_imports_are_stdlib_only_and_offline(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        imported = imported_module_names(source)
        self.assertTrue(imported <= ALLOWED_IMPORT_ROOTS)
        self.assertTrue(imported.isdisjoint(FORBIDDEN_IMPORT_ROOTS))
        self.assertEqual(forbidden_executable_calls(source), [])
        full = imported_full_module_names(source)
        self.assertTrue(all("multi_coin_miner" not in name for name in full))
        self.assertTrue(all("deploy_bridge" not in name for name in full))
        self.assertTrue(all("tx_validation" not in name for name in full))
        self.assertNotIn("time", imported)
        self.assertNotIn("datetime", imported)
        self.assertNotIn("random", imported)
        self.assertNotIn("secrets", imported)
        self.assertNotIn("uuid", imported)
        self.assertNotIn("os", imported)
        self.assertNotIn("platform", imported)

    def test_no_production_mutation_or_authority_surfaces(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        calls = forbidden_executable_calls(source)
        self.assertNotIn("validate_transaction", calls)
        self.assertNotIn("mint", calls)
        imported = imported_module_names(source)
        self.assertNotIn("coin", imported)
        self.assertNotIn("contracts", imported)
        self.assertNotIn("socket", imported)
        self.assertNotIn("requests", imported)
        self.assertNotIn("urllib", imported)
        self.assertNotIn("httpx", imported)
        self.assertNotIn("aiohttp", imported)
        self.assertNotIn("websocket", imported)
        self.assertNotIn("websockets", imported)
        self.assertNotIn("bitcoinrpc", imported)
        self.assertNotIn("subprocess", imported)
        self.assertNotIn("web3", imported)

    def test_no_runtime_network_wallet_signing_broadcast_mining_or_bridge(self) -> None:
        for fx in self.fixtures:
            result = evaluate_deterministic(fx)
            self.assertIs(fx["safety"]["network_call_performed"], False)
            self.assertIs(fx["safety"]["uses_real_wallet"], False)
            self.assertIs(fx["safety"]["signing_performed"], False)
            self.assertIs(fx["safety"]["broadcast_performed"], False)
            self.assertIs(fx["safety"]["ledger_mutated"], False)
            self.assertIs(fx["safety"]["settlement_finalized"], False)
            self.assertIs(result["signing_authorized"], False)
            self.assertIs(result["broadcast_authorized"], False)
            self.assertIs(result["transaction_submitted"], False)
            self.assertIs(result["ledger_mutated"], False)
            self.assertIs(result["settlement_finalized"], False)
            self.assertIs(result["l28_issuance_authorized"], False)
            self.assertIs(result["adapter_override_allowed"], False)


if __name__ == "__main__":
    unittest.main()
