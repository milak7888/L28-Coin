# SPDX-License-Identifier: Apache-2.0
"""Foundation 87 — isolated create_refund_request fixture validation.

Test-local only. Does not import or initialize ledgers, wallets, mining,
networking, services, signing, settlement, or adapters. Does not implement
refund processing or a production Universal Access Interface runtime.
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
RFR_DIR = FIXTURE_ROOT / "create_refund_request"

FIXTURE_SCHEMA = "l28-uai-conformance-fixture/v0.1"
PLAN_VERSION = "universal-access-conformance-plan/v0.1"
INTERFACE_PROFILE = "l28-universal-ai-access-interface/v0.1"
REFUND_REQUEST_PROFILE = "l28-uaii-refund-request/v0.1"

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
REFUND_REQUEST_KEYS = (
    "refund_request_profile",
    "original_receipt_id",
    "original_quote_id",
    "payer_identity",
    "payee_identity",
    "asset_id",
    "amount",
    "refund_reason",
    "refund_nonce",
    "refund_expires_at",
    "spend_authorized",
    "execution_authorized",
    "ledger_mutated",
)
EXECUTE_SETTLEMENT_KEYS = frozenset(
    {
        "execute_settlement",
        "execute_refund",
        "settlement_authorized",
        "transaction_submitted",
    }
)
MINT_SUPPLY_KEYS = frozenset(
    {
        "mint_supply",
        "may_mint",
        "issuance_mechanism",
    }
)
ALWAYS_FALSE = (
    "spend_authorized",
    "signing_authorized",
    "settlement_authorized",
    "ledger_mutated",
    "execution_authorized",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
CASE_ID_RE = re.compile(r"^UAI-CONF-v0\.1-RFR-(POS|NEG|BND|FCL)-\d{3}$")

PLANNED_IDS = (
    "UAI-CONF-v0.1-RFR-POS-001",
    "UAI-CONF-v0.1-RFR-NEG-001",
    "UAI-CONF-v0.1-RFR-NEG-002",
    "UAI-CONF-v0.1-RFR-FCL-001",
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
    by_id = {p.stem: p for p in RFR_DIR.glob("*.json")}
    missing = [cid for cid in PLANNED_IDS if cid not in by_id]
    if missing:
        raise AssertionError(f"missing fixtures: {missing}")
    extra = sorted(set(by_id) - set(PLANNED_IDS))
    if extra:
        raise AssertionError(f"unexpected fixtures: {extra}")
    return [by_id[cid] for cid in PLANNED_IDS]


def assert_always_false_flags(obj: dict[str, Any]) -> str | None:
    for key in ALWAYS_FALSE:
        if key in obj and obj[key] is not False:
            return "schema_invalid"
    return None


def validate_envelope(req: dict[str, Any]) -> str | None:
    if tuple(req.keys()) != ENVELOPE_KEYS:
        return "schema_invalid"
    if req["interface_profile"] != INTERFACE_PROFILE:
        return "interface_profile_unsupported"
    if req["operation"] != "create_refund_request":
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


def evaluate_create_refund_request(fx: dict[str, Any]) -> dict[str, Any]:
    req = fx["request"]
    err = validate_envelope(req)
    if err is not None:
        return {"outcome": "reject", "ok": False, "code": err}

    params = req["params"]
    if any(k in MINT_SUPPLY_KEYS for k in params):
        return {
            "outcome": "reject",
            "ok": False,
            "code": "adapter_override_forbidden",
            "execution_authorized": False,
            "result": {"ledger_mutated": False, "mint_forbidden": True},
        }
    if any(k in EXECUTE_SETTLEMENT_KEYS for k in params):
        return {"outcome": "reject", "ok": False, "code": "operation_unsupported"}
    if tuple(params.keys()) != REFUND_REQUEST_KEYS:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    if params["refund_request_profile"] != REFUND_REQUEST_PROFILE:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if not isinstance(params["original_receipt_id"], str) or not HEX64_RE.fullmatch(
        params["original_receipt_id"]
    ):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if not isinstance(params["original_quote_id"], str) or not HEX64_RE.fullmatch(
        params["original_quote_id"]
    ):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if params["asset_id"] != "L28":
        return {"outcome": "reject", "ok": False, "code": "amount_mismatch"}
    if type(params["amount"]) is not int or params["amount"] <= 0:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if not isinstance(params["refund_reason"], str) or params["refund_reason"] == "":
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if type(params["refund_expires_at"]) is not int:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    flag_err = assert_always_false_flags(params)
    if flag_err is not None:
        return {"outcome": "reject", "ok": False, "code": flag_err}

    original = fx.get("supporting_objects", {}).get("original_receipt")
    if isinstance(original, dict):
        if params["amount"] != original.get("amount"):
            return {"outcome": "reject", "ok": False, "code": "amount_mismatch"}
        if params["asset_id"] != original.get("asset_id"):
            return {"outcome": "reject", "ok": False, "code": "amount_mismatch"}
        if params["original_receipt_id"] != original.get("receipt_id"):
            return {"outcome": "reject", "ok": False, "code": "amount_mismatch"}
        if params["original_quote_id"] != original.get("quote_id"):
            return {"outcome": "reject", "ok": False, "code": "amount_mismatch"}

    expected_result = fx["expected"].get("result")
    if not isinstance(expected_result, dict):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if expected_result.get("deferred") is not True:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if expected_result.get("non_executing") is not True:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if expected_result.get("message_shape_only") is not True:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    flag_err = assert_always_false_flags(expected_result)
    if flag_err is not None:
        return {"outcome": "reject", "ok": False, "code": flag_err}

    return {
        "outcome": "accept",
        "ok": True,
        "code": "deferred_non_executing",
        "execution_authorized": False,
        "result": expected_result,
    }


def evaluate_fixture(fx: dict[str, Any]) -> dict[str, Any]:
    if fx["operation"] != "create_refund_request":
        return {"outcome": "reject", "ok": False, "code": "operation_unsupported"}
    return evaluate_create_refund_request(fx)


class TestUniversalAccessRefundRequestFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]
        cls.by_id = {fx["case_id"]: fx for fx in cls.fixtures}

    def test_discovers_only_create_refund_request_dir_and_exactly_4(self) -> None:
        self.assertTrue(RFR_DIR.is_dir())
        self.assertEqual(len(self.paths), 4)
        self.assertEqual({p.parent for p in self.paths}, {RFR_DIR})

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
            self.assertEqual(fx["area"], "create_refund_request")
            self.assertEqual(fx["operation"], "create_refund_request")
            self.assertRegex(fx["case_id"], CASE_ID_RE)
            pol = fx["case_id"].split("-")[4]
            self.assertEqual(fx["class"], CLASS_FROM_POL[pol])
            for flag in (
                "contains_private_keys",
                "contains_credentials",
                "contains_production_addresses",
                "contains_environment_values",
                "mutates_historical_ledger",
                "uses_real_balances_or_transactions",
            ):
                self.assertIs(fx["safety"][flag], False)

    def test_canonical_hashes_recalculated(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(
                canon_sha256(fx["request"]),
                fx["canonical"]["request_canonical_sha256"],
                fx["case_id"],
            )
            if fx["case_id"] == "UAI-CONF-v0.1-RFR-POS-001":
                refund = fx["expected"]["result"]["refund_request"]
                self.assertEqual(
                    canon_sha256(refund),
                    fx["canonical"]["refund_request_canonical_sha256"],
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
                for key in ALWAYS_FALSE:
                    self.assertIs(result[key], False, fx["case_id"])
                self.assertIs(result["deferred"], True)
                self.assertIs(result["non_executing"], True)
                self.assertIs(result["message_shape_only"], True)

    def test_expected_result_flags_always_false_when_present(self) -> None:
        for fx in self.fixtures:
            result = fx["expected"].get("result")
            if isinstance(result, dict):
                for key in ALWAYS_FALSE:
                    if key in result:
                        self.assertIs(result[key], False, fx["case_id"])

    def test_pos_deferred_message_shape_only(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-RFR-POS-001"]
        params = fx["request"]["params"]
        self.assertEqual(tuple(params.keys()), REFUND_REQUEST_KEYS)
        self.assertEqual(params["refund_request_profile"], REFUND_REQUEST_PROFILE)
        self.assertEqual(params["asset_id"], "L28")
        self.assertEqual(params["amount"], 28)
        self.assertIs(params["spend_authorized"], False)
        self.assertIs(params["execution_authorized"], False)
        self.assertIs(params["ledger_mutated"], False)
        result = fx["expected"]["result"]
        self.assertEqual(result["refund_request"], params)
        self.assertEqual(fx["expected"]["code"], "deferred_non_executing")

    def test_neg_executable_settlement_unsupported(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-RFR-NEG-001"]
        self.assertIs(fx["request"]["params"]["execute_settlement"], True)
        self.assertEqual(fx["expected"]["code"], "operation_unsupported")

    def test_neg_amount_mismatch_against_original(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-RFR-NEG-002"]
        params = fx["request"]["params"]
        original = fx["supporting_objects"]["original_receipt"]
        self.assertNotEqual(params["amount"], original["amount"])
        self.assertEqual(original["amount"], 28)
        self.assertEqual(params["asset_id"], original["asset_id"])
        self.assertEqual(fx["expected"]["code"], "amount_mismatch")

    def test_fcl_mint_supply_fail_closed_no_ledger_mutation(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-RFR-FCL-001"]
        self.assertIs(fx["request"]["params"]["mint_supply"], True)
        self.assertEqual(fx["expected"]["code"], "adapter_override_forbidden")
        self.assertIs(fx["expected"]["result"]["ledger_mutated"], False)
        self.assertIs(fx["expected"]["result"]["mint_forbidden"], True)
        self.assertIs(fx["safety"]["mutates_historical_ledger"], False)

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
