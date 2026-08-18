# SPDX-License-Identifier: Apache-2.0
"""Foundation 102 — isolated Bitcoin economic / authority firewall checks.

Test-local evaluator only. This is not a production adapter, mint, ledger,
validator, or height authority. Proposed values are never accepted. Canonical
L28 economics are never recalculated, rounded, or replaced.
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
FAMILY = "ECO"
BLOCKED = "BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION"
REJECT_CODE = "adapter_override_forbidden"

PLANNED = (
    ("fx-btc-v01-0038", "BTC-CONF-v0.1-ECO-NEG-001", "negative"),
    ("fx-btc-v01-0039", "BTC-CONF-v0.1-ECO-NEG-002", "negative"),
    ("fx-btc-v01-0040", "BTC-CONF-v0.1-ECO-NEG-003", "negative"),
    ("fx-btc-v01-0041", "BTC-CONF-v0.1-ECO-NEG-004", "negative"),
    ("fx-btc-v01-0042", "BTC-CONF-v0.1-ECO-NEG-005", "negative"),
    ("fx-btc-v01-0043", "BTC-CONF-v0.1-ECO-NEG-006", "negative"),
    ("fx-btc-v01-0044", "BTC-CONF-v0.1-ECO-NEG-007", "negative"),
    ("fx-btc-v01-0045", "BTC-CONF-v0.1-ECO-FCL-001", "fail_closed"),
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
PROTECTED_OVERRIDE_TARGETS = frozenset(
    {
        "hard_cap_l28",
        "emission_ceiling_l28",
        "historically_mined_l28",
        "treasury_locked_l28",
        "circulating_snapshot_l28",
        "issuance_mechanism",
        "height_authority",
        "validate_transaction",
        "historical_evidence",
        "l28_canonical_height",
        "claimed_l28_canonical_height",
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
CASE_ID_RE = re.compile(r"^BTC-CONF-v0\.1-ECO-(NEG|FCL)-\d{3}$")
FIXTURE_ID_RE = re.compile(r"^fx-btc-v01-003[89]$|^fx-btc-v01-004[0-5]$")


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


def discover_eco_fixture_paths() -> list[Path]:
    by_id = {fid: FIXTURE_DIR / f"{fid}.json" for fid in PLANNED_FIXTURE_IDS}
    missing = [fid for fid, path in by_id.items() if not path.is_file()]
    if missing:
        raise AssertionError(f"missing fixtures: {missing}")
    extra = sorted(
        path.stem
        for path in FIXTURE_DIR.glob("fx-btc-v01-003[89].json")
        if path.stem not in by_id
    ) + sorted(
        path.stem
        for path in FIXTURE_DIR.glob("fx-btc-v01-004[0-5].json")
        if path.stem not in by_id
    )
    if extra:
        raise AssertionError(f"unexpected Foundation102 fixtures: {extra}")
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
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            pair = (func.value.id, func.attr)
            if pair in FORBIDDEN_DYNAMIC_ATTRS:
                found.append(f"{func.value.id}.{func.attr}")
            if func.attr in FORBIDDEN_NAME_CALLS:
                found.append(f"{func.value.id}.{func.attr}")
    return found


def _reject(field_path: str) -> dict[str, Any]:
    return {
        "outcome": "reject",
        "ok": False,
        "code": REJECT_CODE,
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
            "code": REJECT_CODE,
            "category": "economic_override",
            "field_path": field_path,
        },
    }


def _override_field_path(request: dict[str, Any]) -> str | None:
    """Locate an authority-override attempt. Proposed values are irrelevant."""
    if "claimed_l28_canonical_height" in request:
        return "request.claimed_l28_canonical_height"
    target = request.get("override_target")
    if target in PROTECTED_OVERRIDE_TARGETS:
        return "request.override_target"
    circulating = request.get("override_target_circulating")
    if circulating in PROTECTED_OVERRIDE_TARGETS:
        return "request.override_target_circulating"
    for key in PROTECTED_OVERRIDE_TARGETS:
        if key in request:
            return f"request.{key}"
    if request.get("override_action") == "force_accept":
        return "request.override_action"
    if request.get("mutation") == "replace_record":
        return "request.mutation"
    return None


def evaluate_economic_firewall(fx: dict[str, Any]) -> dict[str, Any]:
    """Test-local ECO evaluator. Not a production adapter.

    Any attempt to override protected L28 authority is forbidden. The proposed
    value is never compared for economic reasonableness and is never accepted,
    including when it equals the canonical value. Inputs are never mutated.
    """
    invariants = fx.get("l28_invariants")
    if not isinstance(invariants, dict) or invariants != L28_INVARIANTS:
        return _reject("l28_invariants")

    request = fx.get("request")
    if not isinstance(request, dict):
        return _reject("request")

    field_path = _override_field_path(request)
    if field_path is not None:
        return _reject(field_path)
    return _reject("request")


class TestBitcoinInteroperabilityEconomicAuthorityFirewallFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_eco_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]
        cls.by_fixture_id = {fx["fixture_id"]: fx for fx in cls.fixtures}
        cls.by_case_id = {fx["case_id"]: fx for fx in cls.fixtures}

    def test_exactly_eight_foundation102_eco_fixtures(self) -> None:
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

    def test_exact_case_fixture_mapping_0038_through_0045(self) -> None:
        for fixture_id, case_id, polarity in PLANNED:
            fx = self.by_fixture_id[fixture_id]
            self.assertEqual(fx["case_id"], case_id)
            self.assertEqual(fx["polarity"], polarity)
            self.assertEqual(fx["family"], FAMILY)
            self.assertRegex(fx["fixture_id"], FIXTURE_ID_RE)
            self.assertRegex(fx["case_id"], CASE_ID_RE)

    def test_family_is_eco_and_polarity_counts(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(fx["family"], FAMILY)
        counts = Counter(fx["polarity"] for fx in self.fixtures)
        self.assertEqual(counts["negative"], 7)
        self.assertEqual(counts["fail_closed"], 1)
        self.assertEqual(counts["positive"], 0)
        for fixture_id in PLANNED_FIXTURE_IDS[:7]:
            self.assertEqual(self.by_fixture_id[fixture_id]["polarity"], "negative")
        self.assertEqual(self.by_fixture_id["fx-btc-v01-0045"]["polarity"], "fail_closed")

    def test_conceptual_fields_and_blocked_production_policy(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(tuple(fx.keys()), ROOT_KEYS)
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
            self.assertEqual(fx["l28_invariants"]["hard_cap_l28"], 28000000)
            self.assertEqual(fx["l28_invariants"]["emission_ceiling_l28"], 11130000)
            self.assertEqual(fx["l28_invariants"]["historically_mined_l28"], 2824584)
            self.assertEqual(fx["l28_invariants"]["treasury_locked_l28"], 500000)
            self.assertEqual(fx["l28_invariants"]["circulating_snapshot_l28"], 2324584)
            self.assertEqual(fx["l28_invariants"]["issuance_mechanism"], "coinbase_only")
            self.assertEqual(fx["l28_invariants"]["height_authority"], "consensus_derived")
            self.assertEqual(fx["l28_invariants"]["historical_evidence"], "immutable")
            self.assertIs(fx["l28_invariants"]["adapter_override_allowed"], False)
            self.assertEqual(fx["l28_invariants"]["protocol_version"], "1.0.0")

    def test_protected_values_byte_for_byte_in_fixture_text(self) -> None:
        for path in self.paths:
            text = path.read_text(encoding="utf-8")
            for fragment in PROTECTED_JSON_FRAGMENTS:
                self.assertIn(fragment, text)

    def test_all_eight_return_adapter_override_forbidden(self) -> None:
        for fx in self.fixtures:
            result = evaluate_economic_firewall(fx)
            self.assertEqual(result, fx["expected"])
            self.assertEqual(result["outcome"], "reject")
            self.assertIs(result["ok"], False)
            self.assertEqual(result["code"], REJECT_CODE)
            self.assertEqual(result["error"]["code"], REJECT_CODE)

    def test_all_grant_and_mutation_flags_false(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(tuple(fx["safety"].keys()), SAFETY_KEYS)
            for key in SAFETY_KEYS:
                self.assertIs(fx["safety"][key], False)
            result = evaluate_economic_firewall(fx)
            for key in GRANT_FLAGS:
                self.assertIs(fx["expected"][key], False)
                self.assertIs(result[key], False)

    def test_neg_001_hard_cap_override_rejected(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-ECO-NEG-001"]
        self.assertEqual(fx["request"]["override_target"], "hard_cap_l28")
        self.assertEqual(fx["request"]["proposed_value"], 28000001)
        result = evaluate_economic_firewall(fx)
        self.assertEqual(result["code"], REJECT_CODE)
        self.assertEqual(fx["l28_invariants"]["hard_cap_l28"], 28000000)
        self.assertNotEqual(fx["l28_invariants"]["hard_cap_l28"], fx["request"]["proposed_value"])

    def test_neg_002_emission_ceiling_override_rejected(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-ECO-NEG-002"]
        self.assertEqual(fx["request"]["override_target"], "emission_ceiling_l28")
        self.assertEqual(fx["request"]["proposed_value"], 11130001)
        result = evaluate_economic_firewall(fx)
        self.assertEqual(result["code"], REJECT_CODE)
        self.assertEqual(fx["l28_invariants"]["emission_ceiling_l28"], 11130000)
        self.assertNotEqual(
            fx["l28_invariants"]["emission_ceiling_l28"],
            fx["request"]["proposed_value"],
        )

    def test_neg_003_historically_mined_override_rejected(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-ECO-NEG-003"]
        self.assertEqual(fx["request"]["override_target"], "historically_mined_l28")
        self.assertEqual(fx["request"]["proposed_value"], 2824585)
        result = evaluate_economic_firewall(fx)
        self.assertEqual(result["code"], REJECT_CODE)
        self.assertEqual(fx["l28_invariants"]["historically_mined_l28"], 2824584)
        self.assertNotEqual(
            fx["l28_invariants"]["historically_mined_l28"],
            fx["request"]["proposed_value"],
        )

    def test_neg_004_treasury_and_circulating_override_rejected(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-ECO-NEG-004"]
        self.assertEqual(fx["request"]["override_target"], "treasury_locked_l28")
        self.assertEqual(fx["request"]["override_target_circulating"], "circulating_snapshot_l28")
        self.assertEqual(fx["request"]["proposed_value"], 500001)
        self.assertEqual(fx["request"]["proposed_circulating_value"], 2324585)
        result = evaluate_economic_firewall(fx)
        self.assertEqual(result["code"], REJECT_CODE)
        self.assertEqual(fx["l28_invariants"]["treasury_locked_l28"], 500000)
        self.assertEqual(fx["l28_invariants"]["circulating_snapshot_l28"], 2324584)

    def test_neg_005_non_coinbase_issuance_claim_rejected(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-ECO-NEG-005"]
        self.assertEqual(fx["request"]["override_target"], "issuance_mechanism")
        self.assertEqual(fx["request"]["proposed_value"], "adapter_mint")
        result = evaluate_economic_firewall(fx)
        self.assertEqual(result["code"], REJECT_CODE)
        self.assertEqual(fx["l28_invariants"]["issuance_mechanism"], "coinbase_only")
        self.assertIs(result["l28_issuance_authorized"], False)
        self.assertIs(fx["expected"]["l28_issuance_authorized"], False)

    def test_neg_006_bitcoin_height_cannot_become_l28_canonical_height(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-ECO-NEG-006"]
        self.assertEqual(fx["bitcoin_evidence"]["bitcoin_height"], 840000)
        self.assertEqual(fx["request"]["claimed_l28_canonical_height"], 840000)
        self.assertEqual(fx["request"]["override_target"], "l28_canonical_height")
        result = evaluate_economic_firewall(fx)
        self.assertEqual(result["code"], REJECT_CODE)
        self.assertEqual(fx["l28_invariants"]["height_authority"], "consensus_derived")
        self.assertNotEqual(fx["l28_invariants"]["height_authority"], 840000)
        self.assertNotIn("l28_canonical_height", fx["l28_invariants"])
        self.assertEqual(result["error"]["field_path"], "request.claimed_l28_canonical_height")

    def test_neg_007_validate_transaction_override_rejected(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-ECO-NEG-007"]
        self.assertEqual(fx["request"]["override_target"], "validate_transaction")
        self.assertEqual(fx["request"]["override_action"], "force_accept")
        result = evaluate_economic_firewall(fx)
        self.assertEqual(result["code"], REJECT_CODE)
        source = Path(__file__).read_text(encoding="utf-8")
        imported = imported_full_module_names(source)
        self.assertTrue(all("tx_validation" not in name for name in imported))
        self.assertNotIn("validate_transaction", forbidden_executable_calls(source))

    def test_fcl_001_historical_evidence_mutation_rejected(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-ECO-FCL-001"]
        self.assertEqual(fx["request"]["override_target"], "historical_evidence")
        self.assertEqual(fx["request"]["mutation"], "replace_record")
        result = evaluate_economic_firewall(fx)
        self.assertEqual(result["code"], REJECT_CODE)
        self.assertEqual(fx["l28_invariants"]["historical_evidence"], "immutable")
        self.assertIs(result["ledger_mutated"], False)
        self.assertIs(fx["safety"]["ledger_mutated"], False)
        self.assertIs(fx["expected"]["ledger_mutated"], False)

    def test_proposed_value_equal_to_canonical_is_still_forbidden(self) -> None:
        fx = copy.deepcopy(self.by_case_id["BTC-CONF-v0.1-ECO-NEG-001"])
        fx["request"]["proposed_value"] = 28000000
        result = evaluate_economic_firewall(fx)
        self.assertEqual(result["code"], REJECT_CODE)
        self.assertEqual(fx["l28_invariants"]["hard_cap_l28"], 28000000)

    def test_evaluator_does_not_mutate_request_fixture_or_invariants(self) -> None:
        for fx in self.fixtures:
            snapshot = copy.deepcopy(fx)
            request_snapshot = copy.deepcopy(fx["request"])
            invariant_snapshot = copy.deepcopy(fx["l28_invariants"])
            evaluate_economic_firewall(fx)
            self.assertEqual(fx, snapshot)
            self.assertEqual(fx["request"], request_snapshot)
            self.assertEqual(fx["l28_invariants"], invariant_snapshot)
            result = evaluate_economic_firewall(copy.deepcopy(fx))
            self.assertEqual(fx["l28_invariants"], L28_INVARIANTS)
            self.assertEqual(result["code"], REJECT_CODE)

    def test_evaluator_does_not_mutate_caller_request_object(self) -> None:
        for fx in self.fixtures:
            request = copy.deepcopy(fx["request"])
            payload = {"l28_invariants": copy.deepcopy(L28_INVARIANTS), "request": request}
            before = copy.deepcopy(request)
            evaluate_economic_firewall(payload)
            self.assertEqual(request, before)
            self.assertEqual(payload["l28_invariants"], L28_INVARIANTS)

    def test_deterministic_repeated_evaluation(self) -> None:
        first = [evaluate_economic_firewall(fx) for fx in self.fixtures]
        second = [evaluate_economic_firewall(fx) for fx in self.fixtures]
        third = [evaluate_economic_firewall(copy.deepcopy(fx)) for fx in self.fixtures]
        self.assertEqual(first, second)
        self.assertEqual(second, third)

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

    def test_no_runtime_network_wallet_signing_broadcast_or_mining(self) -> None:
        for fx in self.fixtures:
            self.assertIs(fx["safety"]["network_call_performed"], False)
            self.assertIs(fx["safety"]["uses_real_wallet"], False)
            self.assertIs(fx["safety"]["signing_performed"], False)
            self.assertIs(fx["safety"]["broadcast_performed"], False)
            self.assertIs(fx["safety"]["ledger_mutated"], False)
            self.assertIs(fx["safety"]["settlement_finalized"], False)
            result = evaluate_economic_firewall(fx)
            self.assertIs(result["signing_authorized"], False)
            self.assertIs(result["broadcast_authorized"], False)
            self.assertIs(result["transaction_submitted"], False)
            self.assertIs(result["ledger_mutated"], False)
            self.assertIs(result["settlement_finalized"], False)
            self.assertIs(result["l28_issuance_authorized"], False)
            self.assertIs(result["adapter_override_allowed"], False)


if __name__ == "__main__":
    unittest.main()
