# SPDX-License-Identifier: Apache-2.0
"""Foundation 84 — isolated validate_payment fixture validation.

Test-local only. Does not import or initialize ledgers, wallets, mining,
networking, services, signing, settlement, or adapters. Does not implement a
production Universal Access Interface runtime validator.
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
VAL_DIR = FIXTURE_ROOT / "validate_payment"

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
VAL_PARAM_KEYS = (
    "quote",
    "quote_id",
    "unsigned_payment_request",
    "payment_request_id",
    "proposed_transfer",
    "check_ledger_balance",
)
QUOTE_OBJECT_KEYS = (
    "quote_profile",
    "payer_identity",
    "payee_identity",
    "service_id",
    "service_params",
    "amount",
    "currency",
    "purpose",
    "quote_expires_at",
    "quote_nonce",
    "max_amount",
    "rejectable",
    "service_terms",
    "service_terms_hash",
    "spend_authorized",
    "execution_authorized",
)
PAYMENT_OBJECT_KEYS = (
    "payment_request_profile",
    "quote_id",
    "payer_identity",
    "payee_identity",
    "amount",
    "currency",
    "purpose",
    "service_id",
    "service_terms_hash",
    "payment_nonce",
    "payment_expires_at",
    "quote_expires_at",
    "quote_nonce",
    "spend_authorized",
    "execution_authorized",
)
OVERRIDE_PARAM_KEYS = frozenset(
    {
        "validate_transaction_override",
        "validation_authority",
        "adapter_validate_transaction",
        "bypass_validate_transaction",
    }
)
ALWAYS_FALSE = (
    "spend_authorized",
    "execution_authorized",
    "ledger_mutated",
    "transaction_submitted",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
CASE_ID_RE = re.compile(r"^UAI-CONF-v0\.1-VAL-(POS|NEG|BND|FCL)-\d{3}$")

PLANNED_IDS = (
    "UAI-CONF-v0.1-VAL-POS-001",
    "UAI-CONF-v0.1-VAL-NEG-001",
    "UAI-CONF-v0.1-VAL-NEG-002",
    "UAI-CONF-v0.1-VAL-FCL-001",
    "UAI-CONF-v0.1-VAL-FCL-002",
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
    by_id = {p.stem: p for p in VAL_DIR.glob("*.json")}
    missing = [cid for cid in PLANNED_IDS if cid not in by_id]
    if missing:
        raise AssertionError(f"missing fixtures: {missing}")
    extra = sorted(set(by_id) - set(PLANNED_IDS))
    if extra:
        raise AssertionError(f"unexpected fixtures: {extra}")
    return [by_id[cid] for cid in PLANNED_IDS]


def assert_always_false_flags(result: dict[str, Any]) -> str | None:
    for key in ALWAYS_FALSE:
        if result.get(key) is not False:
            return "schema_invalid"
    return None


def validate_envelope(req: dict[str, Any]) -> str | None:
    if tuple(req.keys()) != ENVELOPE_KEYS:
        return "schema_invalid"
    if req["interface_profile"] != INTERFACE_PROFILE:
        return "interface_profile_unsupported"
    if req["operation"] != "validate_payment":
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


def evaluate_validate_payment(fx: dict[str, Any]) -> dict[str, Any]:
    req = fx["request"]
    err = validate_envelope(req)
    if err is not None:
        return {"outcome": "reject", "ok": False, "code": err}

    params = req["params"]
    if any(k in OVERRIDE_PARAM_KEYS for k in params):
        return {"outcome": "reject", "ok": False, "code": "adapter_override_forbidden"}
    if set(params.keys()) - set(VAL_PARAM_KEYS):
        return {"outcome": "reject", "ok": False, "code": "adapter_override_forbidden"}
    if tuple(params.keys()) != VAL_PARAM_KEYS:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    if "candidate_response" in fx:
        result = fx["candidate_response"].get("result")
        if not isinstance(result, dict):
            return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
        flag_err = assert_always_false_flags(result)
        if flag_err is not None:
            return {"outcome": "reject", "ok": False, "code": flag_err}
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    quote = params["quote"]
    payment = params["unsigned_payment_request"]
    if not isinstance(quote, dict) or not isinstance(payment, dict):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if tuple(quote.keys()) != QUOTE_OBJECT_KEYS:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if tuple(payment.keys()) != PAYMENT_OBJECT_KEYS:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    if canon_sha256(quote["service_terms"]) != quote["service_terms_hash"]:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    computed_qid = canon_sha256(quote)
    if params["quote_id"] != computed_qid:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    computed_prid = canon_sha256(payment)
    if params["payment_request_id"] != computed_prid:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    if payment["quote_id"] != params["quote_id"]:
        return {"outcome": "reject", "ok": False, "code": "amount_mismatch"}
    if payment["amount"] != quote["amount"]:
        return {"outcome": "reject", "ok": False, "code": "amount_mismatch"}
    for key in ("payer_identity", "payee_identity", "currency", "purpose", "service_id"):
        if payment[key] != quote[key]:
            return {"outcome": "reject", "ok": False, "code": "amount_mismatch"}
    if payment["service_terms_hash"] != quote["service_terms_hash"]:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if payment["quote_expires_at"] != quote["quote_expires_at"]:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if payment["quote_nonce"] != quote["quote_nonce"]:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if type(params["check_ledger_balance"]) is not bool:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if not isinstance(params["proposed_transfer"], dict):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    result = {
        "validation_status": "accepted",
        "validation_code": "structural_accepted",
        "quote_id": params["quote_id"],
        "payment_request_id": params["payment_request_id"],
        "spend_authorized": False,
        "execution_authorized": False,
        "ledger_mutated": False,
        "transaction_submitted": False,
    }
    flag_err = assert_always_false_flags(result)
    if flag_err is not None:
        return {"outcome": "reject", "ok": False, "code": flag_err}
    return {
        "outcome": "accept",
        "ok": True,
        "code": "ok",
        "execution_authorized": False,
        "result": result,
    }


def evaluate_fixture(fx: dict[str, Any]) -> dict[str, Any]:
    if fx["operation"] != "validate_payment":
        return {"outcome": "reject", "ok": False, "code": "operation_unsupported"}
    return evaluate_validate_payment(fx)


class TestUniversalAccessValidatePaymentFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]

    def test_discovers_only_validate_payment_dir_and_exactly_5(self) -> None:
        self.assertTrue(VAL_DIR.is_dir())
        self.assertEqual(len(self.paths), 5)
        self.assertEqual({p.parent for p in self.paths}, {VAL_DIR})

    def test_unique_planned_ids_and_order(self) -> None:
        ids = [fx["case_id"] for fx in self.fixtures]
        self.assertEqual(ids, list(PLANNED_IDS))
        self.assertEqual(len(set(ids)), 5)

    def test_counts(self) -> None:
        counts = Counter(fx["class"] for fx in self.fixtures)
        self.assertEqual(counts["positive"], 1)
        self.assertEqual(counts["negative"], 2)
        self.assertEqual(counts["boundary"], 0)
        self.assertEqual(counts["fail_closed"], 2)

    def test_structure_and_mapping(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(fx["fixture_schema"], FIXTURE_SCHEMA)
            self.assertEqual(fx["plan_version"], PLAN_VERSION)
            self.assertEqual(fx["interface_profile"], INTERFACE_PROFILE)
            self.assertEqual(fx["area"], "validate_payment")
            self.assertEqual(fx["operation"], "validate_payment")
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
                self.assertEqual(result["validation_status"], "accepted")

    def test_expected_result_flags_always_false_when_present(self) -> None:
        for fx in self.fixtures:
            result = fx["expected"].get("result")
            if isinstance(result, dict):
                for key in ALWAYS_FALSE:
                    self.assertIs(result[key], False, fx["case_id"])

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
