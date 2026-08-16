# SPDX-License-Identifier: Apache-2.0
"""Foundation 91 — isolated economic-invariant fixture validation.

Test-local only. Does not import or initialize ledgers, wallets, mining,
networking, services, signing, settlement, or adapters. Does not implement a
production Universal Access Interface runtime. Protected Protocol constants
are asserted exactly and are never recalculated.
"""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "conformance" / "universal_access" / "v0.1"
ECO_DIR = FIXTURE_ROOT / "economic_invariants"

FIXTURE_SCHEMA = "l28-uai-conformance-fixture/v0.1"
PLAN_VERSION = "universal-access-conformance-plan/v0.1"
INTERFACE_PROFILE = "l28-universal-ai-access-interface/v0.1"

ENVELOPE_KEYS = (
    "interface_profile",
    "operation",
    "request_id",
    "created_at",
    "expires_at",
    "nonce",
    "execution_authorized",
    "params",
)
PROTECTED_ECONOMICS = {
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
OVERRIDE_PARAM_KEYS = frozenset(PROTECTED_ECONOMICS.keys())
ALWAYS_FALSE = (
    "spend_authorized",
    "signing_authorized",
    "settlement_authorized",
    "ledger_mutated",
    "execution_authorized",
    "transaction_submitted",
)
SAFETY_FLAGS = (
    "contains_private_keys",
    "contains_credentials",
    "contains_production_addresses",
    "contains_environment_values",
    "mutates_historical_ledger",
    "uses_real_balances_or_transactions",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
CASE_ID_RE = re.compile(r"^UAI-CONF-v0\.1-ECO-(POS|NEG|BND|FCL)-\d{3}$")

PLANNED_IDS = (
    "UAI-CONF-v0.1-ECO-POS-001",
    "UAI-CONF-v0.1-ECO-NEG-001",
    "UAI-CONF-v0.1-ECO-NEG-002",
    "UAI-CONF-v0.1-ECO-FCL-001",
)

CLASS_FROM_POL = {
    "POS": "positive",
    "NEG": "negative",
    "BND": "boundary",
    "FCL": "fail_closed",
}


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


def canon_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
        allow_nan=False,
    ).encode("utf-8")


def canon_sha256(obj: Any) -> str:
    return hashlib.sha256(canon_bytes(obj)).hexdigest()


def load_fixture_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if "\t" in text:
        raise AssertionError(f"tabs forbidden in {path}")
    obj = strict_loads(text)
    if not isinstance(obj, dict):
        raise AssertionError(f"fixture root must be object: {path}")
    return obj


def discover_fixture_paths() -> list[Path]:
    by_id = {p.stem: p for p in ECO_DIR.glob("*.json")}
    missing = [cid for cid in PLANNED_IDS if cid not in by_id]
    if missing:
        raise AssertionError(f"missing fixtures: {missing}")
    extra = sorted(set(by_id) - set(PLANNED_IDS))
    if extra:
        raise AssertionError(f"unexpected fixtures: {extra}")
    return [by_id[cid] for cid in PLANNED_IDS]


def validate_protected_economics(pe: dict[str, Any]) -> str | None:
    if tuple(pe.keys()) != tuple(PROTECTED_ECONOMICS.keys()):
        return "adapter_override_forbidden"
    for key, value in PROTECTED_ECONOMICS.items():
        if pe.get(key) != value:
            return "adapter_override_forbidden"
    return None


def validate_envelope(req: dict[str, Any]) -> str | None:
    if tuple(req.keys()) != ENVELOPE_KEYS:
        return "schema_invalid"
    if req["interface_profile"] != INTERFACE_PROFILE:
        return "interface_profile_unsupported"
    if req["operation"] != "get_protocol_status":
        return "operation_unsupported"
    if not isinstance(req["request_id"], str) or not HEX64_RE.fullmatch(req["request_id"]):
        return "schema_invalid"
    if type(req["created_at"]) is not int or type(req["expires_at"]) is not int:
        return "schema_invalid"
    if req["expires_at"] <= req["created_at"]:
        return "schema_invalid"
    if req["execution_authorized"] is not False:
        return "schema_invalid"
    if not isinstance(req["params"], dict):
        return "schema_invalid"
    return None


def evaluate_economic_invariant(fx: dict[str, Any]) -> dict[str, Any]:
    req = fx["request"]
    err = validate_envelope(req)
    if err is not None:
        return {"outcome": "reject", "ok": False, "code": err}

    consensus = fx.get("consensus_view")
    if not isinstance(consensus, dict):
        return {"outcome": "reject", "ok": False, "code": "adapter_override_forbidden"}
    if consensus.get("protocol_version") != "1.0.0":
        return {"outcome": "reject", "ok": False, "code": "adapter_override_forbidden"}
    pe = consensus.get("protected_economics")
    if not isinstance(pe, dict):
        return {"outcome": "reject", "ok": False, "code": "adapter_override_forbidden"}
    pe_err = validate_protected_economics(pe)
    if pe_err is not None:
        return {"outcome": "reject", "ok": False, "code": pe_err}

    params = req["params"]
    if any(k in OVERRIDE_PARAM_KEYS for k in params):
        return {
            "outcome": "reject",
            "ok": False,
            "code": "adapter_override_forbidden",
            "execution_authorized": False,
        }
    if tuple(params.keys()) != ():
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    expected_result = fx["expected"].get("result")
    if not isinstance(expected_result, dict):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if expected_result.get("protocol_version") != "1.0.0":
        return {"outcome": "reject", "ok": False, "code": "adapter_override_forbidden"}
    result_pe = expected_result.get("protected_economics")
    if not isinstance(result_pe, dict):
        return {"outcome": "reject", "ok": False, "code": "adapter_override_forbidden"}
    pe_err = validate_protected_economics(result_pe)
    if pe_err is not None:
        return {"outcome": "reject", "ok": False, "code": pe_err}
    for key in ALWAYS_FALSE:
        if expected_result.get(key) is not False:
            return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    return {
        "outcome": "accept",
        "ok": True,
        "code": "protocol_status_ok",
        "execution_authorized": False,
        "result": expected_result,
    }


def evaluate_fixture(fx: dict[str, Any]) -> dict[str, Any]:
    return evaluate_economic_invariant(fx)


class TestUniversalAccessEconomicInvariantFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]
        cls.by_id = {fx["case_id"]: fx for fx in cls.fixtures}

    def test_discovers_only_economic_invariants_dir_and_exactly_4(self) -> None:
        self.assertTrue(ECO_DIR.is_dir())
        self.assertEqual(len(self.paths), 4)
        self.assertEqual({p.parent for p in self.paths}, {ECO_DIR})

    def test_unique_planned_ids_and_order(self) -> None:
        ids = [fx["case_id"] for fx in self.fixtures]
        self.assertEqual(ids, list(PLANNED_IDS))
        self.assertEqual(len(set(ids)), 4)

    def test_counts(self) -> None:
        counts = Counter(fx["class"] for fx in self.fixtures)
        self.assertEqual(counts["positive"], 1)
        self.assertEqual(counts["negative"], 2)
        self.assertEqual(counts["boundary"], 0)
        self.assertEqual(counts["fail_closed"], 1)

    def test_structure_and_mapping(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(fx["fixture_schema"], FIXTURE_SCHEMA)
            self.assertEqual(fx["plan_version"], PLAN_VERSION)
            self.assertEqual(fx["interface_profile"], INTERFACE_PROFILE)
            self.assertEqual(fx["area"], "economic_invariants")
            self.assertEqual(fx["operation"], "get_protocol_status")
            self.assertRegex(fx["case_id"], CASE_ID_RE)
            pol = fx["case_id"].split("-")[4]
            self.assertEqual(fx["class"], CLASS_FROM_POL[pol])
            for flag in SAFETY_FLAGS:
                self.assertIs(fx["safety"][flag], False)

    def test_protected_values_byte_for_byte_in_fixture_text(self) -> None:
        for path in self.paths:
            text = path.read_text(encoding="utf-8")
            for fragment in PROTECTED_JSON_FRAGMENTS:
                self.assertIn(fragment, text, f"{path.name}: missing {fragment}")

    def test_consensus_view_protected_economics_exact(self) -> None:
        for fx in self.fixtures:
            pe = fx["consensus_view"]["protected_economics"]
            self.assertEqual(pe, PROTECTED_ECONOMICS, fx["case_id"])
            self.assertEqual(fx["consensus_view"]["protocol_version"], "1.0.0")
            self.assertEqual(tuple(pe.keys()), tuple(PROTECTED_ECONOMICS.keys()))

    def test_canonical_hashes_recalculated(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(
                canon_sha256(fx["request"]),
                fx["canonical"]["request_canonical_sha256"],
                fx["case_id"],
            )

    def test_evaluate_matches_expected_codes(self) -> None:
        for fx in self.fixtures:
            observed = evaluate_fixture(fx)
            self.assertEqual(observed["outcome"], fx["expected"]["outcome"], fx["case_id"])
            self.assertEqual(observed["ok"], fx["expected"]["ok"], fx["case_id"])
            self.assertEqual(observed["code"], fx["expected"]["code"], fx["case_id"])
            self.assertIs(observed.get("execution_authorized", False), False)
            if observed["outcome"] == "accept":
                result = observed["result"]
                self.assertEqual(result["protected_economics"], PROTECTED_ECONOMICS)
                for key in ALWAYS_FALSE:
                    self.assertIs(result[key], False, fx["case_id"])

    def test_expected_result_flags_always_false_when_present(self) -> None:
        for fx in self.fixtures:
            self.assertIs(fx["expected"]["execution_authorized"], False)
            result = fx["expected"].get("result")
            if isinstance(result, dict):
                for key in ALWAYS_FALSE:
                    if key in result:
                        self.assertIs(result[key], False, fx["case_id"])

    def test_pos_exact_protected_values(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-ECO-POS-001"]
        result = fx["expected"]["result"]
        self.assertEqual(result["protocol_version"], "1.0.0")
        self.assertEqual(result["protected_economics"], PROTECTED_ECONOMICS)
        self.assertEqual(fx["expected"]["code"], "protocol_status_ok")
        self.assertEqual(fx["request"]["params"], {})

    def test_neg_hard_cap_redefine_forbidden(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-ECO-NEG-001"]
        self.assertEqual(fx["request"]["params"]["hard_cap_l28"], 99999999)
        self.assertEqual(fx["expected"]["code"], "adapter_override_forbidden")
        self.assertEqual(
            fx["consensus_view"]["protected_economics"]["hard_cap_l28"],
            28000000,
        )

    def test_neg_non_coinbase_issuance_fail_closed(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-ECO-NEG-002"]
        self.assertEqual(fx["request"]["params"]["issuance_mechanism"], "governance")
        self.assertNotEqual(fx["request"]["params"]["issuance_mechanism"], "coinbase_only")
        self.assertEqual(fx["expected"]["code"], "adapter_override_forbidden")
        self.assertIs(fx["expected"]["result"]["issuance_authorized"], False)
        self.assertIs(fx["expected"]["result"]["supply_changed"], False)
        self.assertEqual(
            fx["consensus_view"]["protected_economics"]["issuance_mechanism"],
            "coinbase_only",
        )

    def test_fcl_historical_evidence_unchanged(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-ECO-FCL-001"]
        params = fx["request"]["params"]
        self.assertEqual(params["historically_mined_l28"], 0)
        self.assertEqual(params["historical_evidence"], "rewritten")
        self.assertEqual(fx["expected"]["code"], "adapter_override_forbidden")
        result = fx["expected"]["result"]
        self.assertEqual(result["historical_evidence"], "immutable")
        self.assertEqual(result["historically_mined_l28"], 2824584)
        self.assertIs(result["historical_data_unchanged"], True)
        pe = fx["consensus_view"]["protected_economics"]
        self.assertEqual(pe["historically_mined_l28"], 2824584)
        self.assertEqual(pe["historical_evidence"], "immutable")

    def test_no_secret_or_private_material(self) -> None:
        for path in self.paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("/Users/", text)
            self.assertNotIn("BEGIN PRIVATE", text)
            self.assertNotIn("os.environ", text)
            self.assertNotIn("seed_phrase", text)
            self.assertNotIn('"private_key"', text)
            self.assertNotIn('"secret_key"', text)
            self.assertIsNone(re.search(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T", text))

    def test_deterministic_repeated_evaluation(self) -> None:
        first = [evaluate_fixture(fx) for fx in self.fixtures]
        second = [evaluate_fixture(fx) for fx in self.fixtures]
        third = [canon_sha256(fx) for fx in self.fixtures]
        fourth = [canon_sha256(fx) for fx in self.fixtures]
        self.assertEqual(first, second)
        self.assertEqual(third, fourth)

    def test_safety_scan(self) -> None:
        for path in self.paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("/Users/", text)
            self.assertNotIn("BEGIN PRIVATE", text)
            self.assertNotIn("os.environ", text)
            self.assertNotIn("seed_phrase", text)
            self.assertNotIn('"private_key"', text)
            self.assertIsNone(re.search(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T", text))

    def test_stdlib_only_imports(self) -> None:
        src = Path(__file__).read_text(encoding="utf-8")
        import_lines = [
            ln for ln in src.splitlines() if ln.startswith(("import ", "from "))
        ]
        joined = "\n".join(import_lines)
        self.assertNotIn("coin.", joined)
        for token in ("socket", "requests", "urllib", "subprocess", "nacl", "cryptography"):
            self.assertNotIn(token, joined)


if __name__ == "__main__":
    unittest.main()
