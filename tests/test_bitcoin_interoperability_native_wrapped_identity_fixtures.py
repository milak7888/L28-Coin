# SPDX-License-Identifier: Apache-2.0
"""Foundation 103 — isolated Bitcoin native/wrapped asset identity checks.

Test-local evaluator only. This is not a production adapter, bridge, wallet,
validator, or issuance path. Identity is never guessed from symbol, name, or
bridge metadata. Bitcoin remains external evidence and never native L28.
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
FAMILY = "IDN"
BLOCKED = "BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION"
REJECT_CODE = "asset_identity_invalid"
ACCEPT_CODE = "bitcoin_observation_ok"
IDENTITY_REQUIRED_KEYS = (
    "claimed_asset_class",
    "representation",
    "native_asset",
    "claimed_native_l28",
)

PLANNED = (
    ("fx-btc-v01-0046", "BTC-CONF-v0.1-IDN-POS-001", "positive"),
    ("fx-btc-v01-0047", "BTC-CONF-v0.1-IDN-NEG-001", "negative"),
    ("fx-btc-v01-0048", "BTC-CONF-v0.1-IDN-NEG-002", "negative"),
    ("fx-btc-v01-0049", "BTC-CONF-v0.1-IDN-NEG-003", "negative"),
    ("fx-btc-v01-0050", "BTC-CONF-v0.1-IDN-NEG-004", "negative"),
    ("fx-btc-v01-0051", "BTC-CONF-v0.1-IDN-FCL-001", "fail_closed"),
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
        ("os", "remove"),
        ("os", "replace"),
        ("os", "rename"),
        ("shutil", "rmtree"),
        ("shutil", "move"),
        ("subprocess", "run"),
        ("subprocess", "call"),
        ("subprocess", "Popen"),
        ("subprocess", "check_output"),
        ("subprocess", "check_call"),
        ("importlib", "import_module"),
        ("importlib", "__import__"),
        ("coin", "multi_coin_miner"),
        ("contracts", "deploy_bridge"),
        ("Path", "write_text"),
        ("Path", "write_bytes"),
        ("Path", "unlink"),
        ("Path", "rename"),
        ("Path", "replace"),
    }
)
FORBIDDEN_NAME_CALLS = frozenset(
    {
        "__import__",
        "eval",
        "exec",
        "validate_transaction",
        "mint",
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
CASE_ID_RE = re.compile(r"^BTC-CONF-v0\.1-IDN-(POS|NEG|FCL)-\d{3}$")
FIXTURE_ID_RE = re.compile(r"^fx-btc-v01-004[6-9]$|^fx-btc-v01-005[01]$")


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


def discover_idn_fixture_paths() -> list[Path]:
    by_id = {fid: FIXTURE_DIR / f"{fid}.json" for fid in PLANNED_FIXTURE_IDS}
    missing = [fid for fid, path in by_id.items() if not path.is_file()]
    if missing:
        raise AssertionError(f"missing fixtures: {missing}")
    extra = sorted(
        path.stem
        for path in FIXTURE_DIR.glob("fx-btc-v01-004[6-9].json")
        if path.stem not in by_id
    ) + sorted(
        path.stem
        for path in FIXTURE_DIR.glob("fx-btc-v01-005[01].json")
        if path.stem not in by_id
    )
    if extra:
        raise AssertionError(f"unexpected Foundation103 fixtures: {extra}")
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
            if func.attr in {
                "write_text",
                "write_bytes",
                "unlink",
                "rmtree",
            }:
                found.append(func.attr)
    return found


def _grant_false() -> dict[str, Any]:
    return {key: False for key in GRANT_FLAGS}


def _reject(field_path: str) -> dict[str, Any]:
    payload = {
        "outcome": "reject",
        "ok": False,
        "code": REJECT_CODE,
        "native_asset": False,
        "result": None,
        "error": {
            "code": REJECT_CODE,
            "category": "asset_identity",
            "field_path": field_path,
        },
    }
    payload.update(_grant_false())
    return payload


def _accept(network: str) -> dict[str, Any]:
    result = {
        "evidence_domain": "bitcoin",
        "bitcoin_network": network,
        "native_asset": False,
        "asset_id": "BTC-EXTERNAL",
        "l28_network_identity": None,
    }
    result.update(_grant_false())
    payload = {
        "outcome": "accept",
        "ok": True,
        "code": ACCEPT_CODE,
        "native_asset": False,
        "result": result,
        "error": None,
    }
    payload.update(_grant_false())
    return payload


def _identity_missing_path(request: dict[str, Any]) -> str | None:
    for key in IDENTITY_REQUIRED_KEYS:
        if key not in request or request[key] is None:
            return f"request.{key}"
    return None


def evaluate_asset_identity(fx: dict[str, Any]) -> dict[str, Any]:
    """Test-local IDN evaluator. Not a production adapter.

    Accepts only explicit external Bitcoin-domain evidence. Never infers
    native or wrapped identity from symbol, name, or bridge metadata.
    Never mutates caller input or l28_invariants.
    """
    invariants = fx.get("l28_invariants")
    if not isinstance(invariants, dict) or invariants != L28_INVARIANTS:
        return _reject("l28_invariants")

    request = fx.get("request")
    if not isinstance(request, dict):
        return _reject("request")

    missing = _identity_missing_path(request)
    if missing is not None:
        return _reject(missing)

    if request.get("bridge_defines_native_l28") is True:
        return _reject("request.bridge_defines_native_l28")
    if request.get("claimed_identity_source") == "bridge_contract":
        return _reject("request.claimed_identity_source")

    asset_class = request.get("claimed_asset_class")
    native_identity = request.get("claimed_native_identity")
    if asset_class == "wrapped_btc" and (
        native_identity == "bitcoin" or request.get("native_asset") is True
    ):
        return _reject("request.claimed_native_identity")
    if asset_class == "wrapped_l28":
        return _reject("request.claimed_native_identity")
    if request.get("claimed_native_l28") is True:
        return _reject("request.claimed_native_l28")
    if native_identity == "l28" or asset_class == "native_l28":
        return _reject("request.claimed_native_identity")
    if request.get("native_asset") is True:
        return _reject("request.native_asset")

    evidence = fx.get("bitcoin_evidence")
    if not isinstance(evidence, dict):
        return _reject("bitcoin_evidence")
    if evidence.get("evidence_domain") != "bitcoin":
        return _reject("bitcoin_evidence.evidence_domain")
    if evidence.get("native_asset") is not False:
        return _reject("bitcoin_evidence.native_asset")
    if request.get("evidence_domain") != "bitcoin":
        return _reject("request.evidence_domain")
    if request.get("native_asset") is not False:
        return _reject("request.native_asset")
    if asset_class != "bitcoin_external":
        return _reject("request.claimed_asset_class")
    if request.get("representation") != "external":
        return _reject("request.representation")
    if request.get("claimed_native_l28") is not False:
        return _reject("request.claimed_native_l28")

    network = evidence.get("bitcoin_network")
    if not isinstance(network, str) or not network:
        return _reject("bitcoin_evidence.bitcoin_network")
    return _accept(network)


class TestBitcoinInteroperabilityNativeWrappedIdentityFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_idn_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]
        cls.by_fixture_id = {fx["fixture_id"]: fx for fx in cls.fixtures}
        cls.by_case_id = {fx["case_id"]: fx for fx in cls.fixtures}

    def test_exactly_six_foundation103_idn_fixtures(self) -> None:
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

    def test_exact_case_fixture_mapping_0046_through_0051(self) -> None:
        for fixture_id, case_id, polarity in PLANNED:
            fx = self.by_fixture_id[fixture_id]
            self.assertEqual(fx["case_id"], case_id)
            self.assertEqual(fx["polarity"], polarity)
            self.assertEqual(fx["family"], FAMILY)
            self.assertRegex(fx["fixture_id"], FIXTURE_ID_RE)
            self.assertRegex(fx["case_id"], CASE_ID_RE)

    def test_family_is_idn_and_polarity_counts(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(fx["family"], FAMILY)
        counts = Counter(fx["polarity"] for fx in self.fixtures)
        self.assertEqual(counts["positive"], 1)
        self.assertEqual(counts["negative"], 4)
        self.assertEqual(counts["fail_closed"], 1)
        self.assertEqual(self.by_fixture_id["fx-btc-v01-0046"]["polarity"], "positive")
        for fixture_id in (
            "fx-btc-v01-0047",
            "fx-btc-v01-0048",
            "fx-btc-v01-0049",
            "fx-btc-v01-0050",
        ):
            self.assertEqual(self.by_fixture_id[fixture_id]["polarity"], "negative")
        self.assertEqual(self.by_fixture_id["fx-btc-v01-0051"]["polarity"], "fail_closed")

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
            result = evaluate_asset_identity(fx)
            self.assertIs(result["native_asset"], False)
            self.assertIs(fx["expected"]["native_asset"], False)
            for key in GRANT_FLAGS:
                self.assertIs(fx["expected"][key], False)
                self.assertIs(result[key], False)

    def test_pos_001_accepts_external_bitcoin_domain_only(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-IDN-POS-001"]
        self.assertEqual(fx["bitcoin_evidence"]["evidence_domain"], "bitcoin")
        self.assertIs(fx["bitcoin_evidence"]["native_asset"], False)
        self.assertEqual(fx["request"]["claimed_asset_class"], "bitcoin_external")
        self.assertEqual(fx["request"]["representation"], "external")
        self.assertIs(fx["request"]["native_asset"], False)
        self.assertIs(fx["request"]["claimed_native_l28"], False)
        result = evaluate_asset_identity(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["outcome"], "accept")
        self.assertIs(result["ok"], True)
        self.assertIs(result["native_asset"], False)
        self.assertIs(result["result"]["native_asset"], False)
        self.assertEqual(result["result"]["evidence_domain"], "bitcoin")
        self.assertEqual(result["result"]["asset_id"], "BTC-EXTERNAL")
        self.assertIs(result["result"]["l28_network_identity"], None)
        self.assertNotIn("l28_canonical_height", result["result"])
        self.assertEqual(fx["bitcoin_evidence"]["bitcoin_height"], 100)
        self.assertEqual(fx["bitcoin_evidence"]["amount_satoshis"], 1)
        for key in GRANT_FLAGS:
            self.assertIs(result[key], False)
            self.assertIs(result["result"][key], False)

    def test_neg_001_btc_as_native_l28_rejected(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-IDN-NEG-001"]
        self.assertIs(fx["request"]["claimed_native_l28"], True)
        self.assertEqual(fx["request"]["claimed_native_identity"], "l28")
        result = evaluate_asset_identity(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], REJECT_CODE)
        self.assertIs(result["ok"], False)
        self.assertIs(result["native_asset"], False)
        self.assertIs(result["result"], None)

    def test_neg_002_wrapped_btc_is_not_native_btc(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-IDN-NEG-002"]
        self.assertEqual(fx["request"]["claimed_asset_class"], "wrapped_btc")
        self.assertEqual(fx["request"]["representation"], "wrapped")
        self.assertEqual(fx["request"]["claimed_native_identity"], "bitcoin")
        result = evaluate_asset_identity(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], REJECT_CODE)
        self.assertIs(result["native_asset"], False)
        self.assertIs(fx["bitcoin_evidence"]["native_asset"], False)

    def test_neg_003_wrapped_l28_is_not_native_l28(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-IDN-NEG-003"]
        self.assertEqual(fx["request"]["claimed_asset_class"], "wrapped_l28")
        self.assertEqual(fx["request"]["claimed_native_identity"], "l28")
        result = evaluate_asset_identity(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], REJECT_CODE)
        self.assertIs(result["native_asset"], False)
        self.assertNotEqual(fx["l28_invariants"]["issuance_mechanism"], "wrapped")

    def test_neg_004_bridge_metadata_never_defines_native_l28(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-IDN-NEG-004"]
        self.assertEqual(fx["request"]["claimed_identity_source"], "bridge_contract")
        self.assertIs(fx["request"]["bridge_defines_native_l28"], True)
        self.assertEqual(
            fx["request"]["bridge_contract_claim"],
            "FICTIONAL_DECLARATIVE_BRIDGE_IDENTITY_CLAIM",
        )
        result = evaluate_asset_identity(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], REJECT_CODE)
        self.assertIs(result["native_asset"], False)
        self.assertIs(result["l28_issuance_authorized"], False)

    def test_fcl_001_ambiguous_identity_is_never_guessed(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-IDN-FCL-001"]
        request = fx["request"]
        self.assertEqual(request["asset_symbol"], "BTC")
        self.assertEqual(request["asset_name"], "Bitcoin")
        self.assertNotIn("claimed_asset_class", request)
        self.assertNotIn("native_asset", request)
        self.assertNotIn("representation", request)
        result = evaluate_asset_identity(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], REJECT_CODE)
        self.assertIs(result["result"], None)
        self.assertNotIn("guessed_identity", result)
        self.assertNotIn("fallback_identity", result)

    def test_reject_0047_through_0051_asset_identity_invalid(self) -> None:
        for fixture_id in PLANNED_FIXTURE_IDS[1:]:
            fx = self.by_fixture_id[fixture_id]
            result = evaluate_asset_identity(fx)
            self.assertEqual(result["outcome"], "reject")
            self.assertIs(result["ok"], False)
            self.assertEqual(result["code"], REJECT_CODE)
            self.assertEqual(result, fx["expected"])

    def test_symbol_name_or_bridge_never_infer_identity(self) -> None:
        fx = copy.deepcopy(self.by_case_id["BTC-CONF-v0.1-IDN-FCL-001"])
        fx["request"]["asset_symbol"] = "L28"
        fx["request"]["asset_name"] = "L28 Coin"
        fx["request"]["bridge_contract_claim"] = "FICTIONAL_DECLARATIVE_BRIDGE_IDENTITY_CLAIM"
        result = evaluate_asset_identity(fx)
        self.assertEqual(result["code"], REJECT_CODE)
        self.assertIs(result["result"], None)

    def test_evaluator_does_not_mutate_request_fixture_or_invariants(self) -> None:
        for fx in self.fixtures:
            snapshot = copy.deepcopy(fx)
            request_snapshot = copy.deepcopy(fx["request"])
            invariant_snapshot = copy.deepcopy(fx["l28_invariants"])
            evaluate_asset_identity(fx)
            self.assertEqual(fx, snapshot)
            self.assertEqual(fx["request"], request_snapshot)
            self.assertEqual(fx["l28_invariants"], invariant_snapshot)

    def test_evaluator_does_not_mutate_caller_request_object(self) -> None:
        for fx in self.fixtures:
            request = copy.deepcopy(fx["request"])
            payload = {
                "l28_invariants": copy.deepcopy(L28_INVARIANTS),
                "request": request,
                "bitcoin_evidence": copy.deepcopy(fx["bitcoin_evidence"]),
            }
            before = copy.deepcopy(request)
            evaluate_asset_identity(payload)
            self.assertEqual(request, before)
            self.assertEqual(payload["l28_invariants"], L28_INVARIANTS)

    def test_deterministic_repeated_evaluation(self) -> None:
        first = [evaluate_asset_identity(fx) for fx in self.fixtures]
        second = [evaluate_asset_identity(fx) for fx in self.fixtures]
        third = [evaluate_asset_identity(copy.deepcopy(fx)) for fx in self.fixtures]
        self.assertEqual(first, second)
        self.assertEqual(second, third)

    def test_evaluator_matches_every_fixture_expected(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(evaluate_asset_identity(fx), fx["expected"])

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
        self.assertNotIn("bitcoinrpc", imported)
        self.assertNotIn("subprocess", imported)

    def test_no_runtime_network_wallet_signing_broadcast_mining_or_bridge(self) -> None:
        for fx in self.fixtures:
            result = evaluate_asset_identity(fx)
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
