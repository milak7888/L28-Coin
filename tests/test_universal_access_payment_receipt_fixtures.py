# SPDX-License-Identifier: Apache-2.0
"""Foundation 85 — isolated get_payment_receipt fixture validation.

Test-local only. Does not import or initialize ledgers, wallets, mining,
networking, services, signing, settlement, or adapters. Does not implement a
production Universal Access Interface runtime validator or signed-receipt
verification.
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
RCP_DIR = FIXTURE_ROOT / "get_payment_receipt"

FIXTURE_SCHEMA = "l28-uai-conformance-fixture/v0.1"
PLAN_VERSION = "universal-access-conformance-plan/v0.1"
INTERFACE_PROFILE = "l28-universal-ai-access-interface/v0.1"
PAYMENT_RECEIPT_PROFILE = "l28-uaii-payment-receipt/v0.1"
SIGNED_RECEIPT_PROFILE = "l28-uaii-signed-receipt/v0.1"

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
RCP_PARAM_KEYS = (
    "quote_id",
    "payment_request_id",
    "payer_identity",
    "payee_identity",
    "amount",
    "currency",
    "service_id",
    "service_result_hash",
    "l28_tx_id",
    "l28_sender",
    "l28_receiver",
    "l28_amount",
    "l28_timestamp",
    "verification_status",
    "completed_at",
    "receipt_nonce",
)
RECEIPT_PUBLIC_KEYS = (
    "receipt_profile",
    "quote_id",
    "payment_request_id",
    "payer_identity",
    "payee_identity",
    "amount",
    "currency",
    "service_id",
    "service_result_hash",
    "l28_tx_id",
    "l28_sender",
    "l28_receiver",
    "l28_amount",
    "l28_timestamp",
    "verification_status",
    "completed_at",
    "receipt_nonce",
    "completion_assertion",
    "spend_authorized",
    "signing_authorized",
    "settlement_authorized",
    "ledger_mutated",
    "execution_authorized",
    "audit_id",
    "receipt_id",
)
ALWAYS_FALSE = (
    "spend_authorized",
    "signing_authorized",
    "settlement_authorized",
    "ledger_mutated",
    "execution_authorized",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
CASE_ID_RE = re.compile(r"^UAI-CONF-v0\.1-RCP-(POS|NEG|BND|FCL)-\d{3}$")

PLANNED_IDS = (
    "UAI-CONF-v0.1-RCP-POS-001",
    "UAI-CONF-v0.1-RCP-NEG-001",
    "UAI-CONF-v0.1-RCP-FCL-001",
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
    by_id = {p.stem: p for p in RCP_DIR.glob("*.json")}
    missing = [cid for cid in PLANNED_IDS if cid not in by_id]
    if missing:
        raise AssertionError(f"missing fixtures: {missing}")
    extra = sorted(set(by_id) - set(PLANNED_IDS))
    if extra:
        raise AssertionError(f"unexpected fixtures: {extra}")
    return [by_id[cid] for cid in PLANNED_IDS]


def assert_always_false_flags(obj: dict[str, Any]) -> str | None:
    for key in ALWAYS_FALSE:
        if obj.get(key) is not False:
            return "schema_invalid"
    return None


def validate_envelope(req: dict[str, Any]) -> str | None:
    if tuple(req.keys()) != ENVELOPE_KEYS:
        return "schema_invalid"
    if req["interface_profile"] != INTERFACE_PROFILE:
        return "interface_profile_unsupported"
    if req["operation"] != "get_payment_receipt":
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


def validate_receipt_object(receipt: dict[str, Any]) -> str | None:
    if "audit_id" not in receipt:
        return "schema_invalid"
    if tuple(receipt.keys()) != RECEIPT_PUBLIC_KEYS:
        return "schema_invalid"
    if receipt["receipt_profile"] != PAYMENT_RECEIPT_PROFILE:
        return "schema_invalid"
    if receipt["receipt_profile"] == SIGNED_RECEIPT_PROFILE:
        return "schema_invalid"
    if not isinstance(receipt["audit_id"], str) or not HEX64_RE.fullmatch(receipt["audit_id"]):
        return "schema_invalid"
    if not isinstance(receipt["receipt_id"], str) or not HEX64_RE.fullmatch(receipt["receipt_id"]):
        return "schema_invalid"
    body = {k: v for k, v in receipt.items() if k != "receipt_id"}
    if canon_sha256(body) != receipt["receipt_id"]:
        return "schema_invalid"
    return assert_always_false_flags(receipt)


def evaluate_get_payment_receipt(fx: dict[str, Any]) -> dict[str, Any]:
    req = fx["request"]
    err = validate_envelope(req)
    if err is not None:
        return {"outcome": "reject", "ok": False, "code": err}

    params = req["params"]
    if tuple(params.keys()) != RCP_PARAM_KEYS:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    if "candidate_receipt" in fx:
        candidate = fx["candidate_receipt"]
        if not isinstance(candidate, dict):
            return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
        if "audit_id" not in candidate:
            return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    if "candidate_response" in fx:
        candidate = fx["candidate_response"]
        if not isinstance(candidate, dict):
            return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
        result = candidate.get("result")
        if not isinstance(result, dict):
            return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
        receipt = result.get("receipt")
        profile = result.get("receipt_profile")
        if isinstance(receipt, dict):
            receipt_profile = receipt.get("receipt_profile")
        else:
            receipt_profile = None
        if (
            profile == SIGNED_RECEIPT_PROFILE
            or receipt_profile == SIGNED_RECEIPT_PROFILE
            or profile != PAYMENT_RECEIPT_PROFILE
            or receipt_profile != PAYMENT_RECEIPT_PROFILE
        ):
            return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    expected_result = fx["expected"].get("result")
    if not isinstance(expected_result, dict):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    receipt = expected_result.get("receipt")
    if not isinstance(receipt, dict):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    receipt_err = validate_receipt_object(receipt)
    if receipt_err is not None:
        return {"outcome": "reject", "ok": False, "code": receipt_err}
    if expected_result.get("receipt_profile") != PAYMENT_RECEIPT_PROFILE:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if expected_result.get("distinct_from_signed_receipt") is not True:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if expected_result.get("receipt_id") != receipt["receipt_id"]:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    flag_err = assert_always_false_flags(expected_result)
    if flag_err is not None:
        return {"outcome": "reject", "ok": False, "code": flag_err}

    return {
        "outcome": "accept",
        "ok": True,
        "code": "payment_receipt_ok",
        "execution_authorized": False,
        "result": expected_result,
    }


def evaluate_fixture(fx: dict[str, Any]) -> dict[str, Any]:
    if fx["operation"] != "get_payment_receipt":
        return {"outcome": "reject", "ok": False, "code": "operation_unsupported"}
    return evaluate_get_payment_receipt(fx)


class TestUniversalAccessPaymentReceiptFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]

    def test_discovers_only_get_payment_receipt_dir_and_exactly_3(self) -> None:
        self.assertTrue(RCP_DIR.is_dir())
        self.assertEqual(len(self.paths), 3)
        self.assertEqual({p.parent for p in self.paths}, {RCP_DIR})

    def test_unique_planned_ids_and_order(self) -> None:
        ids = [fx["case_id"] for fx in self.fixtures]
        self.assertEqual(ids, list(PLANNED_IDS))
        self.assertEqual(len(set(ids)), 3)

    def test_counts(self) -> None:
        counts = Counter(fx["class"] for fx in self.fixtures)
        self.assertEqual(counts["positive"], 1)
        self.assertEqual(counts["negative"], 1)
        self.assertEqual(counts["boundary"], 0)
        self.assertEqual(counts["fail_closed"], 1)

    def test_structure_and_mapping(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(fx["fixture_schema"], FIXTURE_SCHEMA)
            self.assertEqual(fx["plan_version"], PLAN_VERSION)
            self.assertEqual(fx["interface_profile"], INTERFACE_PROFILE)
            self.assertEqual(fx["area"], "get_payment_receipt")
            self.assertEqual(fx["operation"], "get_payment_receipt")
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
            if fx["case_id"] == "UAI-CONF-v0.1-RCP-POS-001":
                receipt = fx["expected"]["result"]["receipt"]
                body = {k: v for k, v in receipt.items() if k != "receipt_id"}
                self.assertEqual(
                    canon_sha256(body),
                    fx["canonical"]["receipt_canonical_sha256"],
                    fx["case_id"],
                )
                self.assertEqual(receipt["receipt_id"], fx["canonical"]["receipt_id"])
                self.assertEqual(receipt["audit_id"], fx["canonical"]["audit_id"])

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
                self.assertEqual(result["receipt_profile"], PAYMENT_RECEIPT_PROFILE)
                self.assertIs(result["distinct_from_signed_receipt"], True)
                self.assertNotEqual(result["receipt_profile"], SIGNED_RECEIPT_PROFILE)
                self.assertNotEqual(
                    result["receipt"]["receipt_profile"], SIGNED_RECEIPT_PROFILE
                )

    def test_expected_result_flags_always_false_when_present(self) -> None:
        for fx in self.fixtures:
            result = fx["expected"].get("result")
            if isinstance(result, dict):
                for key in ALWAYS_FALSE:
                    self.assertIs(result[key], False, fx["case_id"])

    def test_pos_receipt_profile_distinct_from_signed(self) -> None:
        fx = next(f for f in self.fixtures if f["case_id"] == "UAI-CONF-v0.1-RCP-POS-001")
        receipt = fx["expected"]["result"]["receipt"]
        self.assertEqual(receipt["receipt_profile"], PAYMENT_RECEIPT_PROFILE)
        self.assertNotEqual(receipt["receipt_profile"], SIGNED_RECEIPT_PROFILE)
        self.assertIn("audit_id", receipt)
        self.assertRegex(receipt["audit_id"], HEX64_RE.pattern)

    def test_neg_missing_audit_id(self) -> None:
        fx = next(f for f in self.fixtures if f["case_id"] == "UAI-CONF-v0.1-RCP-NEG-001")
        self.assertNotIn("audit_id", fx["candidate_receipt"])
        self.assertEqual(fx["expected"]["code"], "schema_invalid")

    def test_fcl_rejects_signed_receipt_profile_conflation(self) -> None:
        fx = next(f for f in self.fixtures if f["case_id"] == "UAI-CONF-v0.1-RCP-FCL-001")
        result = fx["candidate_response"]["result"]
        self.assertEqual(result["receipt_profile"], SIGNED_RECEIPT_PROFILE)
        self.assertEqual(
            result["receipt"]["receipt_profile"], SIGNED_RECEIPT_PROFILE
        )
        self.assertEqual(fx["expected"]["code"], "schema_invalid")

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
        for token in ("socket", "requests", "urllib", "subprocess", "nacl"):
            self.assertNotIn(token, joined)


if __name__ == "__main__":
    unittest.main()
