# SPDX-License-Identifier: Apache-2.0
"""Foundation 95 — isolated Bitcoin network-identity fixture validation.

Test-local evaluator only. This is not a production Bitcoin adapter.
It does not import or initialize ledgers, wallets, mining, networking,
services, signing, settlement, RPC clients, or bridge code.
"""

from __future__ import annotations

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
FAMILY = "NID"
BLOCKED = "BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION"

NET_MAIN = "bitcoin-test-mainnet"
NET_TEST = "bitcoin-test-testnet"
NET_UNKNOWN = "bitcoin-test-unknown-network"
SUPPORTED_NETWORKS = frozenset(
    {
        NET_MAIN,
        NET_TEST,
        "bitcoin-test-signet",
        "bitcoin-test-regtest",
    }
)
NETWORK_IDENTITY_KEYS = ("bitcoin_network", "network_identity", "network")
NON_IDENTITY_HINT_KEYS = (
    "evidence_domain",
    "block_hash",
    "bitcoin_height",
    "txid",
    "output_index",
    "amount_satoshis",
    "description",
)

PLANNED = (
    ("fx-btc-v01-0001", "BTC-CONF-v0.1-NID-POS-001", "positive"),
    ("fx-btc-v01-0002", "BTC-CONF-v0.1-NID-NEG-001", "negative"),
    ("fx-btc-v01-0003", "BTC-CONF-v0.1-NID-NEG-002", "negative"),
    ("fx-btc-v01-0004", "BTC-CONF-v0.1-NID-NEG-003", "negative"),
    ("fx-btc-v01-0005", "BTC-CONF-v0.1-NID-FCL-001", "fail_closed"),
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
FORBIDDEN_SOURCE_TOKENS = (
    "socket",
    "requests",
    "urllib",
    "subprocess",
    "nacl",
    "cryptography",
    "multi_coin_miner",
    "deploy_bridge",
    "L28Bridge",
    "bitcoinrpc",
    "bitcoind",
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
CASE_ID_RE = re.compile(r"^BTC-CONF-v0\.1-NID-(POS|NEG|FCL)-\d{3}$")
FIXTURE_ID_RE = re.compile(r"^fx-btc-v01-000[1-5]$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


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


def discover_fixture_paths() -> list[Path]:
    by_id = {p.stem: p for p in FIXTURE_DIR.glob("fx-btc-v01-000[1-5].json")}
    missing = [fid for fid in PLANNED_FIXTURE_IDS if fid not in by_id]
    if missing:
        raise AssertionError(f"missing fixtures: {missing}")
    extra = sorted(set(by_id) - set(PLANNED_FIXTURE_IDS))
    if extra:
        raise AssertionError(f"unexpected fixtures: {extra}")
    all_json = sorted(p.name for p in FIXTURE_DIR.glob("*.json"))
    expected_names = [f"{fid}.json" for fid in PLANNED_FIXTURE_IDS]
    if all_json != expected_names:
        raise AssertionError(f"fixture directory must contain only {expected_names}")
    return [by_id[fid] for fid in PLANNED_FIXTURE_IDS]


def _present_identity(value: Any) -> str | None:
    if not isinstance(value, str) or value == "":
        return None
    return value


def _collect_network_identities(fx: dict[str, Any]) -> dict[str, Any]:
    request = fx.get("request")
    evidence = fx.get("bitcoin_evidence")
    declared = None
    if isinstance(request, dict) and "declared_network" in request:
        declared = _present_identity(request.get("declared_network"))

    evidence_primary = None
    evidence_extra: list[str] = []
    if isinstance(evidence, dict):
        if "bitcoin_network" in evidence:
            evidence_primary = _present_identity(evidence.get("bitcoin_network"))
        for key in ("network_identity", "network"):
            if key in evidence:
                extra = _present_identity(evidence.get(key))
                if extra is not None:
                    evidence_extra.append(extra)

    observer_nets: list[str] = []
    views = fx.get("observer_views")
    if isinstance(views, list):
        for view in views:
            if isinstance(view, dict) and "bitcoin_network" in view:
                identity = _present_identity(view.get("bitcoin_network"))
                if identity is not None:
                    observer_nets.append(identity)

    collected: list[str] = []
    if declared is not None:
        collected.append(declared)
    if evidence_primary is not None:
        collected.append(evidence_primary)
    collected.extend(evidence_extra)
    collected.extend(observer_nets)
    return {
        "declared": declared,
        "evidence_primary": evidence_primary,
        "evidence_extra": evidence_extra,
        "observer_nets": observer_nets,
        "collected": collected,
    }


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
            "l28_network_identity": None,
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
    forbidden_request_keys = {
        "l28_canonical_height",
        "hard_cap_l28",
        "emission_ceiling_l28",
        "historically_mined_l28",
        "treasury_locked_l28",
        "circulating_snapshot_l28",
        "issuance_mechanism",
    }
    if any(key in request for key in forbidden_request_keys):
        return True
    evidence = fx.get("bitcoin_evidence")
    if isinstance(evidence, dict) and "l28_canonical_height" in evidence:
        return True
    return False


def evaluate_network_identity(fx: dict[str, Any]) -> dict[str, Any]:
    """Test-local NID evaluator. Not a production adapter."""
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
    if not isinstance(request, dict):
        return _reject("schema_invalid")
    if request.get("evidence_domain") != "bitcoin":
        return _reject("asset_identity_invalid")

    identities = _collect_network_identities(fx)
    collected: list[str] = identities["collected"]
    if not collected:
        return _reject("network_identity_invalid")
    if any(value not in SUPPORTED_NETWORKS for value in collected):
        return _reject("network_identity_invalid")

    unique = set(collected)
    if len(unique) > 1:
        simple_mismatch = (
            identities["declared"] is not None
            and identities["evidence_primary"] is not None
            and identities["declared"] != identities["evidence_primary"]
            and not identities["evidence_extra"]
            and not identities["observer_nets"]
            and unique == {identities["declared"], identities["evidence_primary"]}
        )
        if simple_mismatch:
            return _reject("network_mismatch")
        return _reject("network_identity_invalid")

    return _accept(next(iter(unique)))


class TestBitcoinInteroperabilityNetworkIdentityFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]
        cls.by_fixture_id = {fx["fixture_id"]: fx for fx in cls.fixtures}
        cls.by_case_id = {fx["case_id"]: fx for fx in cls.fixtures}

    def test_exactly_five_nid_fixtures(self) -> None:
        self.assertTrue(FIXTURE_DIR.is_dir())
        self.assertEqual(len(self.paths), 5)
        self.assertEqual({p.parent for p in self.paths}, {FIXTURE_DIR})
        self.assertEqual(
            [p.stem for p in self.paths],
            list(PLANNED_FIXTURE_IDS),
        )

    def test_unique_fixture_and_case_ids(self) -> None:
        fixture_ids = [fx["fixture_id"] for fx in self.fixtures]
        case_ids = [fx["case_id"] for fx in self.fixtures]
        self.assertEqual(fixture_ids, list(PLANNED_FIXTURE_IDS))
        self.assertEqual(case_ids, list(PLANNED_CASE_IDS))
        self.assertEqual(len(set(fixture_ids)), 5)
        self.assertEqual(len(set(case_ids)), 5)

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
        self.assertEqual(counts["fail_closed"], 1)
        self.assertEqual(counts["boundary"], 0)

    def test_conceptual_field_order_and_required_fields(self) -> None:
        for fx in self.fixtures:
            expected_keys = (
                ROOT_KEYS_WITH_OBSERVERS
                if "observer_views" in fx
                else ROOT_KEYS
            )
            self.assertEqual(tuple(fx.keys()), expected_keys)
            self.assertEqual(fx["plan_version"], PLAN_VERSION)
            self.assertEqual(fx["design_profile"], DESIGN_PROFILE)
            self.assertEqual(fx["family"], FAMILY)
            self.assertNotIn("prior_accept_state", fx)
            clock = fx["fixed_clock"]
            self.assertEqual(
                tuple(clock.keys()),
                ("verification_time", "created_at", "expires_at"),
            )
            for key in clock:
                self.assertIs(type(clock[key]), int)
            self.assertEqual(tuple(fx["test_policy"].keys()), TEST_POLICY_KEYS)
            self.assertIs(fx["test_policy"]["not_production_policy"], True)
            self.assertEqual(fx["test_policy"]["production_proof_architecture"], BLOCKED)
            self.assertEqual(fx["test_policy"]["production_confirmation_count"], BLOCKED)
            self.assertEqual(fx["test_policy"]["production_quorum"], BLOCKED)
            self.assertEqual(fx["test_policy"]["test_min_confirmations"], 2)
            self.assertEqual(fx["test_policy"]["test_observer_count"], 2)

    def test_exact_protected_l28_invariants(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(tuple(fx["l28_invariants"].keys()), L28_INVARIANT_KEYS)
            self.assertEqual(fx["l28_invariants"], L28_INVARIANTS)
            self.assertNotIn("l28_canonical_height", fx["l28_invariants"])
            evidence = fx["bitcoin_evidence"]
            if "bitcoin_height" in evidence:
                self.assertNotEqual(
                    evidence["bitcoin_height"],
                    fx["l28_invariants"].get("l28_canonical_height"),
                )
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

    def test_pos_001_explicit_supported_network(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-NID-POS-001"]
        self.assertEqual(fx["request"]["declared_network"], NET_MAIN)
        self.assertEqual(fx["bitcoin_evidence"]["bitcoin_network"], NET_MAIN)
        result = evaluate_network_identity(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["outcome"], "accept")
        self.assertEqual(result["code"], "bitcoin_observation_ok")
        self.assertEqual(result["result"]["evidence_domain"], "bitcoin")
        self.assertEqual(result["result"]["bitcoin_network"], NET_MAIN)
        self.assertIsNone(result["result"]["l28_network_identity"])
        self.assertIs(result["result"]["native_asset"], False)
        for key in ACCEPT_RESULT_FLAGS:
            self.assertIs(result["result"][key], False)
        for key in GRANT_FLAGS:
            self.assertIs(result[key], False)

    def test_neg_001_unknown_network(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-NID-NEG-001"]
        self.assertEqual(fx["request"]["declared_network"], NET_UNKNOWN)
        self.assertEqual(fx["bitcoin_evidence"]["bitcoin_network"], NET_UNKNOWN)
        result = evaluate_network_identity(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "network_identity_invalid")
        self.assertEqual(result["outcome"], "reject")
        self.assertIsNone(result["result"])

    def test_neg_002_missing_network_no_inference(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-NID-NEG-002"]
        self.assertNotIn("declared_network", fx["request"])
        evidence = fx["bitcoin_evidence"]
        for key in NETWORK_IDENTITY_KEYS:
            self.assertNotIn(key, evidence)
        for key in NON_IDENTITY_HINT_KEYS:
            if key in evidence:
                self.assertNotIn(evidence[key], SUPPORTED_NETWORKS)
        result = evaluate_network_identity(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "network_identity_invalid")
        mutated = json.loads(json.dumps(fx))
        mutated["bitcoin_evidence"]["evidence_domain"] = "bitcoin"
        mutated["bitcoin_evidence"]["bitcoin_height"] = 840000
        self.assertEqual(
            evaluate_network_identity(mutated)["code"],
            "network_identity_invalid",
        )

    def test_neg_003_declared_differs_from_evidence(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-NID-NEG-003"]
        self.assertEqual(fx["request"]["declared_network"], NET_MAIN)
        self.assertEqual(fx["bitcoin_evidence"]["bitcoin_network"], NET_TEST)
        result = evaluate_network_identity(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "network_mismatch")
        self.assertNotEqual(result["code"], "network_identity_invalid")

    def test_fcl_001_conflicting_identities_fail_closed(self) -> None:
        fx = self.by_case_id["BTC-CONF-v0.1-NID-FCL-001"]
        evidence = fx["bitcoin_evidence"]
        self.assertEqual(evidence["bitcoin_network"], NET_MAIN)
        self.assertEqual(evidence["network_identity"], NET_TEST)
        views = fx["observer_views"]
        self.assertEqual(views[0]["bitcoin_network"], NET_MAIN)
        self.assertEqual(views[1]["bitcoin_network"], NET_TEST)
        result = evaluate_network_identity(fx)
        self.assertEqual(result, fx["expected"])
        self.assertEqual(result["code"], "network_identity_invalid")
        self.assertNotEqual(result["code"], "required_state_unavailable")
        self.assertNotEqual(result["code"], "network_mismatch")

    def test_evaluator_matches_every_fixture_expected(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(evaluate_network_identity(fx), fx["expected"])

    def test_deterministic_repeated_evaluation(self) -> None:
        first = [evaluate_network_identity(fx) for fx in self.fixtures]
        second = [evaluate_network_identity(fx) for fx in self.fixtures]
        self.assertEqual(first, second)

    def test_no_private_key_seed_mnemonic_or_xprv_material(self) -> None:
        for path in self.paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("BEGIN PRIVATE", text)
            for token in (
                '"private_key"',
                '"secret_key"',
                '"seed_phrase"',
                '"mnemonic"',
                '"xprv"',
            ):
                self.assertNotIn(token, text)

    def test_no_rpc_credentials(self) -> None:
        for path in self.paths:
            text = path.read_text(encoding="utf-8")
            for token in (
                "rpc_user",
                "rpc_password",
                "rpc_cookie",
                "rpcwallet",
                "bitcoinrpc",
            ):
                self.assertNotIn(token, text)

    def test_no_production_address_dependency(self) -> None:
        for fx in self.fixtures:
            blob = json.dumps(fx)
            self.assertNotIn("bc1", blob)
            self.assertNotRegex(blob, r"[13][a-km-zA-HJ-NP-Z1-9]{25,}")
            txid = fx["bitcoin_evidence"].get("txid")
            if txid is not None:
                self.assertRegex(txid, HEX64_RE.pattern)

    def test_no_secret_fields_in_fixture_objects(self) -> None:
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

    def test_no_socket_rpc_or_network_helpers(self) -> None:
        src = Path(__file__).read_text(encoding="utf-8")
        import_lines = [
            line for line in src.splitlines() if line.startswith(("import ", "from "))
        ]
        joined = "\n".join(import_lines)
        self.assertNotIn("coin.", joined)
        self.assertNotIn("contracts", joined)
        for token in FORBIDDEN_SOURCE_TOKENS:
            self.assertNotIn(token, joined)
        for path in self.paths:
            text = path.read_text(encoding="utf-8")
            for token in (
                "http://",
                "https://",
                "dns",
                "socket",
                "127.0.0.1",
                "localhost",
            ):
                self.assertNotIn(token, text)

    def test_no_signing_broadcast_mining_or_bridge_execution(self) -> None:
        src = Path(__file__).read_text(encoding="utf-8")
        import_lines = [
            line for line in src.splitlines() if line.startswith(("import ", "from "))
        ]
        joined = "\n".join(import_lines)
        self.assertNotIn("coin.", joined)
        self.assertNotIn("import coin", joined)
        self.assertNotIn("contracts", joined)
        self.assertNotIn("multi_coin_miner", joined)
        self.assertNotIn("deploy_bridge", joined)
        self.assertNotIn("L28Bridge", joined)
        for path in self.paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("multi_coin_miner", text)
            self.assertNotIn("deploy_bridge", text)
            self.assertNotIn("L28Bridge", text)
        for fx in self.fixtures:
            self.assertIs(fx["safety"]["signing_performed"], False)
            self.assertIs(fx["safety"]["broadcast_performed"], False)
            self.assertNotIn("sign", fx["request"])
            self.assertNotIn("broadcast", fx["request"])

    def test_no_l28_ledger_mutation_or_economic_authority(self) -> None:
        for fx in self.fixtures:
            self.assertIs(fx["safety"]["ledger_mutated"], False)
            self.assertIs(fx["safety"]["adapter_override_allowed"], False)
            self.assertIs(fx["l28_invariants"]["adapter_override_allowed"], False)
            self.assertEqual(fx["l28_invariants"]["issuance_mechanism"], "coinbase_only")
            self.assertEqual(fx["l28_invariants"]["height_authority"], "consensus_derived")
            result = evaluate_network_identity(fx)
            self.assertIs(result["ledger_mutated"], False)
            self.assertIs(result["adapter_override_allowed"], False)

    def test_stdlib_only_imports(self) -> None:
        src = Path(__file__).read_text(encoding="utf-8")
        import_lines = [
            line for line in src.splitlines() if line.startswith(("import ", "from "))
        ]
        allowed_prefixes = (
            "from __future__",
            "import json",
            "import re",
            "import unittest",
            "from collections",
            "from pathlib",
            "from typing",
        )
        for line in import_lines:
            self.assertTrue(
                any(line.startswith(prefix) for prefix in allowed_prefixes),
                line,
            )


if __name__ == "__main__":
    unittest.main()
