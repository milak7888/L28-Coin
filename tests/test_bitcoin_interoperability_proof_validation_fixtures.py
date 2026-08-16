# SPDX-License-Identifier: Apache-2.0
"""Foundation 96 — isolated Bitcoin proof-validation fixture checks.

Test-local evaluator only. This is not a production Bitcoin adapter and
does not perform Bitcoin consensus, SPV, Merkle-inclusion, RPC, or
header-chain verification. hashlib is used only for a fixture-local
structural fingerprint comparison.
"""

from __future__ import annotations

import ast
import hashlib
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
FAMILY = "PRF"
BLOCKED = "BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION"
NET_MAIN = "bitcoin-test-mainnet"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
CASE_ID_RE = re.compile(r"^BTC-CONF-v0\.1-PRF-(POS|NEG|BND|FCL)-\d{3}$")
FIXTURE_ID_RE = re.compile(r"^fx-btc-v01-00(0[6-9]|10|11)$")

REQUIRED_PROOF_FIELDS = (
    "bitcoin_network",
    "transaction_id",
    "block_hash",
    "header",
    "merkle_path",
    "proof_digest",
)
FINGERPRINT_FIELDS = (
    "bitcoin_network",
    "transaction_id",
    "block_hash",
    "header",
    "merkle_path",
)

PLANNED = (
    ("fx-btc-v01-0006", "BTC-CONF-v0.1-PRF-POS-001", "positive"),
    ("fx-btc-v01-0007", "BTC-CONF-v0.1-PRF-NEG-001", "negative"),
    ("fx-btc-v01-0008", "BTC-CONF-v0.1-PRF-NEG-002", "negative"),
    ("fx-btc-v01-0009", "BTC-CONF-v0.1-PRF-NEG-003", "negative"),
    ("fx-btc-v01-0010", "BTC-CONF-v0.1-PRF-BND-001", "boundary"),
    ("fx-btc-v01-0011", "BTC-CONF-v0.1-PRF-FCL-001", "fail_closed"),
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
    "test_required_proof_fields",
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
    }
)
ALLOWED_IMPORT_ROOTS = frozenset(
    {
        "__future__",
        "ast",
        "hashlib",
        "json",
        "re",
        "unittest",
        "collections",
        "pathlib",
        "typing",
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


def discover_prf_fixture_paths() -> list[Path]:
    by_id = {
        fid: FIXTURE_DIR / f"{fid}.json" for fid in PLANNED_FIXTURE_IDS
    }
    missing = [fid for fid, path in by_id.items() if not path.is_file()]
    if missing:
        raise AssertionError(f"missing fixtures: {missing}")
    extra = sorted(
        path.stem
        for path in FIXTURE_DIR.glob("fx-btc-v01-00*.json")
        if path.stem.startswith("fx-btc-v01-00")
        and path.stem[11:].isdigit()
        and 6 <= int(path.stem[11:]) <= 11
        and path.stem not in by_id
    )
    if extra:
        raise AssertionError(f"unexpected Foundation96 fixtures: {extra}")
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


def structural_fingerprint(proof: dict[str, Any]) -> str:
    """Fixture-local structural fingerprint.

    This is NOT Bitcoin consensus validation, NOT proof-of-work, NOT SPV,
    and NOT Merkle inclusion against Bitcoin blocks. It only hashes the
    caller-supplied fictional public fields already present in the fixture.
    """
    payload = {key: proof[key] for key in FINGERPRINT_FIELDS}
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


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


def _accept(network: str) -> dict[str, Any]:
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


def _proof_field_types_invalid(proof: dict[str, Any]) -> bool:
    if not isinstance(proof.get("bitcoin_network"), str):
        return True
    for key in ("transaction_id", "block_hash", "header", "proof_digest"):
        value = proof.get(key)
        if not isinstance(value, str) or not HEX64_RE.fullmatch(value):
            return True
    path = proof.get("merkle_path")
    if not isinstance(path, list) or not path:
        return True
    if any(not isinstance(item, str) or not HEX64_RE.fullmatch(item) for item in path):
        return True
    return False


def evaluate_proof(fx: dict[str, Any]) -> dict[str, Any]:
    """Test-local PRF evaluator. Not a production adapter."""
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
    required = policy.get("test_required_proof_fields")
    if required != list(REQUIRED_PROOF_FIELDS):
        return _reject("schema_invalid")

    request = fx.get("request")
    if not isinstance(request, dict) or request.get("evidence_domain") != "bitcoin":
        return _reject("asset_identity_invalid")

    evidence = fx.get("bitcoin_evidence")
    if not isinstance(evidence, dict):
        return _reject("required_state_unavailable")
    if evidence.get("proof_state_available") is not True:
        return _reject("required_state_unavailable")
    if "proof" not in evidence or evidence.get("proof") is None:
        return _reject("required_state_unavailable")

    proof = evidence["proof"]
    if not isinstance(proof, dict):
        return _reject("proof_invalid")

    missing = [key for key in REQUIRED_PROOF_FIELDS if key not in proof]
    if missing:
        return _reject("proof_insufficient")
    if _proof_field_types_invalid(proof):
        return _reject("proof_invalid")
    if proof["bitcoin_network"] != request.get("declared_network"):
        return _reject("network_mismatch")
    if structural_fingerprint(proof) != proof["proof_digest"]:
        return _reject("proof_invalid")
    return _accept(proof["bitcoin_network"])


class TestBitcoinInteroperabilityProofValidationFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_prf_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]
        cls.by_fixture_id = {fx["fixture_id"]: fx for fx in cls.fixtures}
        cls.by_case_id = {fx["case_id"]: fx for fx in cls.fixtures}

    def test_exactly_six_foundation96_prf_fixtures(self) -> None:
        self.assertTrue(FIXTURE_DIR.is_dir())
        self.assertEqual(len(self.paths), 6)
        self.assertEqual([p.stem for p in self.paths], list(PLANNED_FIXTURE_IDS))
        self.assertEqual({p.parent for p in self.paths}, {FIXTURE_DIR})

    def test_unique_fixture_and_case_ids(self) -> None:
        fixture_ids = [fx["fixture_id"] for fx in self.fixtures]
        case_ids = [fx["case_id"] for fx in self.fixtures]
        self.assertEqual(fixture_ids, list(PLANNED_FIXTURE_IDS))
        self.assertEqual(case_ids, list(PLANNED_CASE_IDS))
        self.assertEqual(len(set(fixture_ids)), 6)
        self.assertEqual(len(set(case_ids)), 6)

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
        self.assertEqual(counts["negative"], 3)
        self.assertEqual(counts["boundary"], 1)
        self.assertEqual(counts["fail_closed"], 1)

    def test_conceptual_fields_and_blocked_production_policy(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(tuple(fx.keys()), ROOT_KEYS)
            self.assertEqual(fx["plan_version"], PLAN_VERSION)
            self.assertEqual(fx["design_profile"], DESIGN_PROFILE)
            self.assertEqual(fx["family"], FAMILY)
            self.assertNotIn("observer_views", fx)
            self.assertNotIn("prior_accept_state", fx)
            self.assertEqual(tuple(fx["test_policy"].keys()), TEST_POLICY_KEYS)
            self.assertIs(fx["test_policy"]["not_production_policy"], True)
            self.assertEqual(fx["test_policy"]["production_proof_architecture"], BLOCKED)
            self.assertEqual(fx["test_policy"]["production_confirmation_count"], BLOCKED)
            self.assertEqual(fx["test_policy"]["production_quorum"], BLOCKED)
            self.assertEqual(
                fx["test_policy"]["test_required_proof_fields"],
                list(REQUIRED_PROOF_FIELDS),
            )

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

    def test_pos_001_structurally_valid_proof(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-PRF-POS-001"]
        proof = fx["bitcoin_evidence"]["proof"]
        self.assertIsInstance(proof, dict)
        for key in REQUIRED_PROOF_FIELDS:
            self.assertIn(key, proof)
        self.assertGreater(len(proof.keys()), len(REQUIRED_PROOF_FIELDS))
        result = evaluate_proof(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["outcome"], "accept")
        self.assertEqual(result["result"]["proof_evaluation"], "structural_only")
        self.assertEqual(result["result"]["production_proof_architecture"], BLOCKED)
        self.assertIsNone(result["result"]["l28_canonical_height"])
        for key in ACCEPT_RESULT_FLAGS:
            self.assertIs(result["result"][key], False)

    def test_neg_001_malformed_proof(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-PRF-NEG-001"]
        self.assertIsInstance(fx["bitcoin_evidence"]["proof"], str)
        result = evaluate_proof(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "proof_invalid")

    def test_neg_002_incomplete_proof_no_inference(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-PRF-NEG-002"]
        proof = fx["bitcoin_evidence"]["proof"]
        self.assertNotIn("header", proof)
        self.assertNotIn("header", fx["bitcoin_evidence"])
        self.assertNotIn("header", fx["request"])
        result = evaluate_proof(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "proof_insufficient")
        mutated = json.loads(json.dumps(fx))
        mutated["bitcoin_evidence"]["header"] = (
            "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
        )
        self.assertEqual(evaluate_proof(mutated)["code"], "proof_insufficient")

    def test_neg_003_mutated_digest(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-PRF-NEG-003"]
        proof = fx["bitcoin_evidence"]["proof"]
        self.assertNotEqual(structural_fingerprint(proof), proof["proof_digest"])
        result = evaluate_proof(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "proof_invalid")

    def test_bnd_001_minimum_sufficient_proof(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-PRF-BND-001"]
        proof = fx["bitcoin_evidence"]["proof"]
        self.assertEqual(tuple(proof.keys()), REQUIRED_PROOF_FIELDS)
        result = evaluate_proof(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["outcome"], "accept")
        for key in GRANT_FLAGS:
            self.assertIs(result[key], False)

    def test_fcl_001_required_proof_state_unavailable(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-PRF-FCL-001"]
        self.assertIs(fx["bitcoin_evidence"]["proof_state_available"], False)
        self.assertNotIn("proof", fx["bitcoin_evidence"])
        result = evaluate_proof(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "required_state_unavailable")
        self.assertIsNone(result["result"])

    def test_evaluator_matches_every_fixture_expected(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(evaluate_proof(fx), fx["expected"])

    def test_deterministic_repeated_evaluation(self) -> None:
        first = [evaluate_proof(fx) for fx in self.fixtures]
        second = [evaluate_proof(fx) for fx in self.fixtures]
        self.assertEqual(first, second)

    def test_hashlib_is_not_bitcoin_consensus_verification(self) -> None:
        doc = structural_fingerprint.__doc__ or ""
        self.assertIn("NOT Bitcoin consensus", doc)
        self.assertIn("NOT proof-of-work", doc)
        self.assertIn("NOT SPV", doc)
        self.assertIn("NOT Merkle inclusion", doc)
        source = Path(__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        hashlib_uses: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == "hashlib":
                    hashlib_uses.append(node.attr)
        self.assertEqual(set(hashlib_uses), {"sha256"})

    def test_ast_imports_are_stdlib_only_and_offline(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        imported = imported_module_names(source)
        self.assertTrue(imported <= ALLOWED_IMPORT_ROOTS)
        self.assertTrue(imported.isdisjoint(FORBIDDEN_IMPORT_ROOTS))
        self.assertNotIn("coin", imported)
        self.assertNotIn("contracts", imported)
        self.assertNotIn("socket", imported)
        self.assertNotIn("subprocess", imported)
        self.assertNotIn("bitcoinrpc", imported)

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
            self.assertNotIn("sign", fx["request"])
            self.assertNotIn("broadcast", fx["request"])

    def test_no_l28_economic_or_height_authority(self) -> None:
        for fx in self.fixtures:
            result = evaluate_proof(fx)
            self.assertIs(result["ledger_mutated"], False)
            self.assertIs(result["adapter_override_allowed"], False)
            self.assertEqual(fx["l28_invariants"]["issuance_mechanism"], "coinbase_only")
            self.assertEqual(fx["l28_invariants"]["height_authority"], "consensus_derived")
            if result["result"] is not None:
                self.assertIsNone(result["result"]["l28_canonical_height"])
                self.assertEqual(result["result"]["proof_evaluation"], "structural_only")


if __name__ == "__main__":
    unittest.main()
