# SPDX-License-Identifier: Apache-2.0
"""Foundation 88 — isolated create_refund_receipt fixture validation.

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
RRC_DIR = FIXTURE_ROOT / "create_refund_receipt"

FIXTURE_SCHEMA = "l28-uai-conformance-fixture/v0.1"
PLAN_VERSION = "universal-access-conformance-plan/v0.1"
INTERFACE_PROFILE = "l28-universal-ai-access-interface/v0.1"
REFUND_RECEIPT_PROFILE = "l28-uaii-refund-receipt/v0.1"

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
REFUND_RECEIPT_KEYS = (
    "refund_receipt_profile",
    "refund_request_id",
    "original_receipt_id",
    "refund_status",
    "amount",
    "asset_id",
    "payer_identity",
    "payee_identity",
    "audit_id",
    "spend_authorized",
    "execution_authorized",
    "ledger_mutated",
    "settlement_finalized",
)
ALWAYS_FALSE = (
    "spend_authorized",
    "signing_authorized",
    "settlement_authorized",
    "ledger_mutated",
    "execution_authorized",
    "settlement_finalized",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
CASE_ID_RE = re.compile(r"^UAI-CONF-v0\.1-RRC-(POS|NEG|BND|FCL)-\d{3}$")

PLANNED_IDS = (
    "UAI-CONF-v0.1-RRC-POS-001",
    "UAI-CONF-v0.1-RRC-NEG-001",
    "UAI-CONF-v0.1-RRC-FCL-001",
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
    by_id = {p.stem: p for p in RRC_DIR.glob("*.json")}
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
    if req["operation"] != "create_refund_receipt":
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


def evaluate_create_refund_receipt(fx: dict[str, Any]) -> dict[str, Any]:
    req = fx["request"]
    err = validate_envelope(req)
    if err is not None:
        return {"outcome": "reject", "ok": False, "code": err}

    params = req["params"]
    if tuple(params.keys()) != REFUND_RECEIPT_KEYS:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if params["refund_receipt_profile"] != REFUND_RECEIPT_PROFILE:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if not isinstance(params["refund_request_id"], str) or not HEX64_RE.fullmatch(
        params["refund_request_id"]
    ):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if not isinstance(params["original_receipt_id"], str) or not HEX64_RE.fullmatch(
        params["original_receipt_id"]
    ):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if params["refund_status"] not in ("proposed", "rejected", "deferred"):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if type(params["amount"]) is not int or params["amount"] <= 0:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if params["asset_id"] != "L28":
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if not isinstance(params["audit_id"], str) or not HEX64_RE.fullmatch(params["audit_id"]):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if params.get("settlement_finalized") is not False:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    flag_err = assert_always_false_flags(params)
    if flag_err is not None:
        return {"outcome": "reject", "ok": False, "code": flag_err}

    expected_result = fx["expected"].get("result")
    if not isinstance(expected_result, dict):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if expected_result.get("deferred") is not True:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if expected_result.get("non_executing") is not True:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if expected_result.get("message_shape_only") is not True:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if expected_result.get("refund_status") != "deferred":
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if expected_result.get("settlement_finalized") is not False:
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
    if fx["operation"] != "create_refund_receipt":
        return {"outcome": "reject", "ok": False, "code": "operation_unsupported"}
    return evaluate_create_refund_receipt(fx)


class TestUniversalAccessRefundReceiptFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]
        cls.by_id = {fx["case_id"]: fx for fx in cls.fixtures}

    def test_discovers_only_create_refund_receipt_dir_and_exactly_3(self) -> None:
        self.assertTrue(RRC_DIR.is_dir())
        self.assertEqual(len(self.paths), 3)
        self.assertEqual({p.parent for p in self.paths}, {RRC_DIR})

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
            self.assertEqual(fx["area"], "create_refund_receipt")
            self.assertEqual(fx["operation"], "create_refund_receipt")
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
            if fx["case_id"] == "UAI-CONF-v0.1-RRC-POS-001":
                receipt = fx["expected"]["result"]["refund_receipt"]
                self.assertEqual(
                    canon_sha256(receipt),
                    fx["canonical"]["refund_receipt_canonical_sha256"],
                )
                self.assertEqual(receipt["audit_id"], fx["canonical"]["audit_id"])
                self.assertEqual(
                    receipt["refund_request_id"],
                    fx["canonical"]["refund_request_id"],
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
                self.assertEqual(result["refund_status"], "deferred")

    def test_expected_result_flags_always_false_when_present(self) -> None:
        for fx in self.fixtures:
            result = fx["expected"].get("result")
            if isinstance(result, dict):
                for key in ALWAYS_FALSE:
                    if key in result:
                        self.assertIs(result[key], False, fx["case_id"])

    def test_pos_deferred_message_shape_only(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-RRC-POS-001"]
        params = fx["request"]["params"]
        self.assertEqual(tuple(params.keys()), REFUND_RECEIPT_KEYS)
        self.assertEqual(params["refund_receipt_profile"], REFUND_RECEIPT_PROFILE)
        self.assertEqual(params["refund_status"], "deferred")
        self.assertEqual(params["asset_id"], "L28")
        self.assertEqual(params["amount"], 28)
        self.assertIs(params["spend_authorized"], False)
        self.assertIs(params["execution_authorized"], False)
        self.assertIs(params["ledger_mutated"], False)
        self.assertIs(params["settlement_finalized"], False)
        result = fx["expected"]["result"]
        self.assertEqual(result["refund_receipt"], params)
        self.assertEqual(fx["expected"]["code"], "deferred_non_executing")

    def test_neg_settlement_finalized_true_rejected(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-RRC-NEG-001"]
        self.assertIs(fx["request"]["params"]["settlement_finalized"], True)
        self.assertEqual(fx["expected"]["code"], "schema_invalid")

    def test_fcl_incomplete_refund_receipt(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-RRC-FCL-001"]
        params = fx["request"]["params"]
        self.assertNotEqual(tuple(params.keys()), REFUND_RECEIPT_KEYS)
        self.assertNotIn("audit_id", params)
        self.assertNotIn("refund_request_id", params)
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
        for token in ("socket", "requests", "urllib", "subprocess", "nacl", "cryptography"):
            self.assertNotIn(token, joined)


if __name__ == "__main__":
    unittest.main()
