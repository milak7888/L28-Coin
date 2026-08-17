# SPDX-License-Identifier: Apache-2.0
"""Foundation 99 — isolated Bitcoin replay/duplicate fixture checks.

Test-local evaluator only. This is not a production Bitcoin adapter and
does not query a replay database, ledger, wallet, network, or Bitcoin node.
Caller-supplied prior_evidence_ids and prior_outpoints are fictional
test-local state only.
"""

from __future__ import annotations

import ast
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
FAMILY = "RPL"
BLOCKED = "BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION"
NET_MAIN = "bitcoin-test-mainnet"
EVIDENCE_A = "evidence-btc-conf-a"
EVIDENCE_B = "evidence-btc-conf-b"
TXID_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

PLANNED = (
    ("fx-btc-v01-0022", "BTC-CONF-v0.1-RPL-POS-001", "positive"),
    ("fx-btc-v01-0023", "BTC-CONF-v0.1-RPL-NEG-001", "negative"),
    ("fx-btc-v01-0024", "BTC-CONF-v0.1-RPL-NEG-002", "negative"),
    ("fx-btc-v01-0025", "BTC-CONF-v0.1-RPL-FCL-001", "fail_closed"),
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
ROOT_KEYS_WITH_PRIOR = (
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
    "prior_accept_state",
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
    "settlement_finalized",
    "ledger_mutated",
    "adapter_override_allowed",
)
ACCEPT_RESULT_FLAGS = (
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
SECRET_FIELD_NAMES = frozenset(
    {
        "private_key",
        "secret_key",
        "seed_phrase",
        "mnemonic",
        "xprv",
        "rpc_user",
        "rpc_password",
        "rpc_cookie",
        "password",
        "api_key",
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
    }
)
ALLOWED_IMPORT_ROOTS = frozenset(
    {
        "__future__",
        "ast",
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
CASE_ID_RE = re.compile(r"^BTC-CONF-v0\.1-RPL-(POS|NEG|FCL)-\d{3}$")
FIXTURE_ID_RE = re.compile(r"^fx-btc-v01-002[2-5]$")


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


def discover_rpl_fixture_paths() -> list[Path]:
    by_id = {fid: FIXTURE_DIR / f"{fid}.json" for fid in PLANNED_FIXTURE_IDS}
    missing = [fid for fid, path in by_id.items() if not path.is_file()]
    if missing:
        raise AssertionError(f"missing fixtures: {missing}")
    extra = sorted(
        path.stem
        for path in FIXTURE_DIR.glob("fx-btc-v01-002[2-5].json")
        if path.stem not in by_id
    )
    if extra:
        raise AssertionError(f"unexpected Foundation99 fixtures: {extra}")
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


def _reject(code: str) -> dict[str, Any]:
    return {
        "outcome": "reject",
        "ok": False,
        "code": code,
        "execution_authorized": False,
        "spend_authorized": False,
        "settlement_finalized": False,
        "ledger_mutated": False,
        "adapter_override_allowed": False,
        "result": None,
        "error": {"code": code},
    }


def _accept(network: str, evidence_id: str) -> dict[str, Any]:
    return {
        "outcome": "accept",
        "ok": True,
        "code": "bitcoin_observation_ok",
        "execution_authorized": False,
        "spend_authorized": False,
        "settlement_finalized": False,
        "ledger_mutated": False,
        "adapter_override_allowed": False,
        "result": {
            "evidence_domain": "bitcoin",
            "bitcoin_network": network,
            "native_asset": False,
            "asset_id": "BTC-EXTERNAL",
            "evidence_id": evidence_id,
            "proof_evaluation": "structural_only",
            "production_proof_architecture": BLOCKED,
            "l28_network_identity": None,
            "l28_canonical_height": None,
            "execution_authorized": False,
            "spend_authorized": False,
            "signing_authorized": False,
            "broadcast_authorized": False,
            "ledger_mutated": False,
            "settlement_finalized": False,
            "transaction_submitted": False,
            "l28_issuance_authorized": False,
            "adapter_override_allowed": False,
        },
        "error": None,
    }


def _l28_fields_overridden(fx: dict[str, Any]) -> bool:
    request = fx.get("request")
    if not isinstance(request, dict):
        return True
    forbidden = {
        "l28_canonical_height",
        "hard_cap_l28",
        "emission_ceiling_l28",
        "historically_mined_l28",
        "treasury_locked_l28",
        "circulating_snapshot_l28",
        "issuance_mechanism",
    }
    if any(key in request for key in forbidden):
        return True
    evidence = fx.get("bitcoin_evidence")
    if isinstance(evidence, dict) and "l28_canonical_height" in evidence:
        return True
    return False


def _collect_prior_ids(source: dict[str, Any]) -> list[str] | None:
    if "prior_evidence_ids" not in source:
        return None
    value = source.get("prior_evidence_ids")
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return None
    return value


def _collect_prior_outpoints(source: dict[str, Any]) -> set[tuple[str, int]] | None:
    if "prior_outpoints" not in source:
        return None
    value = source.get("prior_outpoints")
    if not isinstance(value, list):
        return None
    outpoints: set[tuple[str, int]] = set()
    for item in value:
        if not isinstance(item, dict):
            return None
        txid = item.get("txid")
        vout = item.get("vout")
        if not isinstance(txid, str) or type(vout) is not int:
            return None
        outpoints.add((txid, vout))
    return outpoints


def evaluate_replay(fx: dict[str, Any]) -> dict[str, Any]:
    """Test-local RPL evaluator. Not a production adapter.

    Uses only caller-supplied evidence_id, outpoint, and prior lists.
    Does not query a database, ledger, filesystem, or Bitcoin node.
    """
    invariants = fx.get("l28_invariants")
    if not isinstance(invariants, dict) or invariants != L28_INVARIANTS:
        return _reject("adapter_override_forbidden")
    if _l28_fields_overridden(fx):
        return _reject("adapter_override_forbidden")

    policy = fx.get("test_policy")
    if not isinstance(policy, dict):
        return _reject("schema_invalid")
    if policy.get("not_production_policy") is not True:
        return _reject("schema_invalid")
    for key in (
        "production_proof_architecture",
        "production_confirmation_count",
        "production_quorum",
    ):
        if policy.get(key) != BLOCKED:
            return _reject("schema_invalid")

    request = fx.get("request")
    evidence = fx.get("bitcoin_evidence")
    if not isinstance(request, dict) or request.get("evidence_domain") != "bitcoin":
        return _reject("asset_identity_invalid")
    if not isinstance(evidence, dict):
        return _reject("required_state_unavailable")

    prior = fx.get("prior_accept_state")
    evidence_state_ok = evidence.get("evidence_state_available") is True
    prior_state_ok = isinstance(prior, dict) and prior.get("evidence_state_available") is True
    if not evidence_state_ok and not prior_state_ok:
        return _reject("required_state_unavailable")
    if evidence.get("evidence_state_available") is False:
        return _reject("required_state_unavailable")

    prior_ids = _collect_prior_ids(evidence)
    prior_outpoints = _collect_prior_outpoints(evidence)
    if isinstance(prior, dict):
        prior_ids = _collect_prior_ids(prior) if prior_ids is None else prior_ids
        prior_outpoints = (
            _collect_prior_outpoints(prior) if prior_outpoints is None else prior_outpoints
        )
    if prior_ids is None or prior_outpoints is None:
        return _reject("required_state_unavailable")

    evidence_id = evidence.get("evidence_id")
    txid = evidence.get("transaction_id")
    vout = evidence.get("vout")
    if not isinstance(evidence_id, str) or evidence_id == "":
        return _reject("required_state_unavailable")
    if not isinstance(txid, str) or type(vout) is not int:
        return _reject("schema_invalid")

    if evidence_id in prior_ids:
        return _reject("replay_detected")
    if (txid, vout) in prior_outpoints:
        return _reject("duplicate_evidence")
    return _accept(evidence.get("bitcoin_network"), evidence_id)


class TestBitcoinInteroperabilityReplayDuplicateFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_rpl_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]
        cls.by_fixture_id = {fx["fixture_id"]: fx for fx in cls.fixtures}
        cls.by_case_id = {fx["case_id"]: fx for fx in cls.fixtures}

    def test_exactly_four_foundation99_rpl_fixtures(self) -> None:
        self.assertTrue(FIXTURE_DIR.is_dir())
        self.assertEqual(len(self.paths), 4)
        self.assertEqual([p.stem for p in self.paths], list(PLANNED_FIXTURE_IDS))

    def test_unique_fixture_and_case_ids(self) -> None:
        fixture_ids = [fx["fixture_id"] for fx in self.fixtures]
        case_ids = [fx["case_id"] for fx in self.fixtures]
        self.assertEqual(fixture_ids, list(PLANNED_FIXTURE_IDS))
        self.assertEqual(case_ids, list(PLANNED_CASE_IDS))
        self.assertEqual(len(set(fixture_ids)), 4)
        self.assertEqual(len(set(case_ids)), 4)

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
        self.assertEqual(counts["positive"], 1)
        self.assertEqual(counts["negative"], 2)
        self.assertEqual(counts["fail_closed"], 1)
        self.assertEqual(counts["boundary"], 0)

    def test_conceptual_fields_and_blocked_production_policy(self) -> None:
        for fx in self.fixtures:
            expected_keys = (
                ROOT_KEYS_WITH_PRIOR if "prior_accept_state" in fx else ROOT_KEYS
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
            self.assertNotIn("l28_canonical_height", fx["l28_invariants"])
            self.assertNotIn("l28_canonical_height", fx["request"])

    def test_protected_values_byte_for_byte_in_fixture_text(self) -> None:
        for path in self.paths:
            text = path.read_text(encoding="utf-8")
            for fragment in PROTECTED_JSON_FRAGMENTS:
                self.assertIn(fragment, text)

    def test_all_safety_flags_false(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(tuple(fx["safety"].keys()), SAFETY_KEYS)
            for key in SAFETY_KEYS:
                self.assertIs(fx["safety"][key], False)
            for key in GRANT_FLAGS:
                self.assertIs(fx["expected"][key], False)

    def test_pos_001_first_presentation_of_evidence_a(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-RPL-POS-001"]
        evidence = fx["bitcoin_evidence"]
        self.assertEqual(evidence["evidence_id"], EVIDENCE_A)
        self.assertEqual(evidence["transaction_id"], TXID_A)
        self.assertEqual(evidence["vout"], 0)
        self.assertEqual(evidence["prior_evidence_ids"], [])
        self.assertEqual(evidence["prior_outpoints"], [])
        self.assertIs(evidence["evidence_state_available"], True)
        self.assertNotIn("prior_accept_state", fx)
        result = evaluate_replay(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["outcome"], "accept")
        self.assertEqual(result["result"]["evidence_id"], EVIDENCE_A)
        self.assertIs(result["settlement_finalized"], False)
        for key in ACCEPT_RESULT_FLAGS:
            self.assertIs(result["result"][key], False)

    def test_neg_001_replay_of_evidence_a(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-RPL-NEG-001"]
        self.assertEqual(fx["bitcoin_evidence"]["evidence_id"], EVIDENCE_A)
        self.assertIn(EVIDENCE_A, fx["prior_accept_state"]["prior_evidence_ids"])
        result = evaluate_replay(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "replay_detected")
        self.assertIs(result["settlement_finalized"], False)
        self.assertIs(result["spend_authorized"], False)
        self.assertIs(result["ledger_mutated"], False)
        self.assertIs(result["execution_authorized"], False)
        self.assertIsNone(result["result"])

    def test_neg_002_duplicate_txid_outpoint(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-RPL-NEG-002"]
        evidence = fx["bitcoin_evidence"]
        prior = fx["prior_accept_state"]
        self.assertEqual(evidence["evidence_id"], EVIDENCE_B)
        self.assertNotEqual(evidence["evidence_id"], prior["prior_evidence_ids"][0])
        self.assertEqual(evidence["transaction_id"], TXID_A)
        self.assertEqual(evidence["vout"], 0)
        self.assertEqual(prior["prior_outpoints"][0]["txid"], TXID_A)
        self.assertEqual(prior["prior_outpoints"][0]["vout"], 0)
        result = evaluate_replay(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "duplicate_evidence")
        self.assertNotEqual(result["code"], "replay_detected")
        self.assertIs(result["spend_authorized"], False)
        self.assertIs(result["execution_authorized"], False)
        self.assertIs(result["settlement_finalized"], False)

    def test_fcl_001_unavailable_replay_state_not_first_seen(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-RPL-FCL-001"]
        evidence = fx["bitcoin_evidence"]
        self.assertIs(evidence["evidence_state_available"], False)
        self.assertNotIn("prior_evidence_ids", evidence)
        self.assertNotIn("prior_outpoints", evidence)
        self.assertNotIn("prior_accept_state", fx)
        result = evaluate_replay(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "required_state_unavailable")
        self.assertNotEqual(result["outcome"], "accept")
        mutated = json.loads(json.dumps(fx))
        mutated["bitcoin_evidence"]["evidence_id"] = EVIDENCE_A
        mutated["bitcoin_evidence"]["transaction_id"] = TXID_A
        mutated["bitcoin_evidence"]["vout"] = 0
        self.assertEqual(
            evaluate_replay(mutated)["code"],
            "required_state_unavailable",
        )

    def test_missing_prior_lists_are_not_inferred_empty(self) -> None:
        fx = json.loads(json.dumps(self.by_case_id["BTC-CONF-v0.1-RPL-POS-001"]))
        del fx["bitcoin_evidence"]["prior_evidence_ids"]
        del fx["bitcoin_evidence"]["prior_outpoints"]
        self.assertEqual(evaluate_replay(fx)["code"], "required_state_unavailable")

    def test_evaluator_matches_every_fixture_expected(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(evaluate_replay(fx), fx["expected"])

    def test_deterministic_repeated_evaluation(self) -> None:
        first = [evaluate_replay(fx) for fx in self.fixtures]
        second = [evaluate_replay(fx) for fx in self.fixtures]
        self.assertEqual(first, second)

    def test_ast_imports_are_stdlib_only_and_offline(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        imported = imported_module_names(source)
        self.assertTrue(imported <= ALLOWED_IMPORT_ROOTS)
        self.assertTrue(imported.isdisjoint(FORBIDDEN_IMPORT_ROOTS))
        self.assertEqual(forbidden_executable_calls(source), [])

    def test_no_secret_fields_or_production_addresses(self) -> None:
        def walk(node: Any) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    self.assertNotIn(key, SECRET_FIELD_NAMES)
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        for fx in self.fixtures:
            walk(fx)
            blob = json.dumps(fx)
            self.assertNotIn("bc1", blob)
            self.assertNotIn("http://", blob)
            self.assertNotIn("https://", blob)

    def test_no_private_key_or_rpc_credential_fields(self) -> None:
        for path in self.paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("BEGIN PRIVATE", text)
            for token in (
                '"private_key"',
                '"secret_key"',
                '"seed_phrase"',
                '"mnemonic"',
                '"xprv"',
                '"rpc_user"',
                '"rpc_password"',
                '"rpc_cookie"',
            ):
                self.assertNotIn(token, text)

    def test_no_signing_broadcast_mining_or_bridge_execution(self) -> None:
        imported = imported_module_names(Path(__file__).read_text(encoding="utf-8"))
        self.assertNotIn("coin", imported)
        self.assertNotIn("contracts", imported)
        for path in self.paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("multi_coin_miner", text)
            self.assertNotIn("deploy_bridge", text)
            self.assertNotIn("L28Bridge", text)
        for fx in self.fixtures:
            self.assertIs(fx["safety"]["signing_performed"], False)
            self.assertIs(fx["safety"]["broadcast_performed"], False)
            self.assertIs(fx["safety"]["ledger_mutated"], False)

    def test_no_l28_economic_or_height_authority(self) -> None:
        for fx in self.fixtures:
            result = evaluate_replay(fx)
            self.assertIs(result["ledger_mutated"], False)
            self.assertIs(result["settlement_finalized"], False)
            self.assertIs(result["adapter_override_allowed"], False)
            self.assertEqual(fx["l28_invariants"]["height_authority"], "consensus_derived")
            if result["result"] is not None:
                self.assertIsNone(result["result"]["l28_canonical_height"])


if __name__ == "__main__":
    unittest.main()
