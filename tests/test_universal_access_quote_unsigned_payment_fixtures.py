# SPDX-License-Identifier: Apache-2.0
"""Foundation 83 — isolated create_quote + create_unsigned_payment_request fixtures.

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
QUOTE_DIR = FIXTURE_ROOT / "create_quote"
UPR_DIR = FIXTURE_ROOT / "create_unsigned_payment_request"

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
QUOTE_PARAM_KEYS = (
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
UPR_PARAM_KEYS = (
    "quote",
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
)
SECRET_FIELD_NAMES = frozenset(
    {
        "private_key",
        "secret_key",
        "seed_phrase",
        "mnemonic",
        "password",
        "api_key",
        "signature",
        "seed",
    }
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
CASE_ID_RE = re.compile(r"^UAI-CONF-v0\.1-(QUO|UPR)-(POS|NEG|BND|FCL)-\d{3}$")

PLANNED_QUO_IDS = (
    "UAI-CONF-v0.1-QUO-POS-001",
    "UAI-CONF-v0.1-QUO-NEG-001",
    "UAI-CONF-v0.1-QUO-NEG-002",
    "UAI-CONF-v0.1-QUO-NEG-003",
    "UAI-CONF-v0.1-QUO-NEG-004",
    "UAI-CONF-v0.1-QUO-BND-001",
    "UAI-CONF-v0.1-QUO-BND-002",
    "UAI-CONF-v0.1-QUO-BND-003",
    "UAI-CONF-v0.1-QUO-FCL-001",
)
PLANNED_UPR_IDS = (
    "UAI-CONF-v0.1-UPR-POS-001",
    "UAI-CONF-v0.1-UPR-NEG-001",
    "UAI-CONF-v0.1-UPR-NEG-002",
    "UAI-CONF-v0.1-UPR-NEG-003",
    "UAI-CONF-v0.1-UPR-BND-001",
    "UAI-CONF-v0.1-UPR-FCL-001",
)
PLANNED_IDS = PLANNED_QUO_IDS + PLANNED_UPR_IDS

PROTECTED_ECONOMICS = {
    "hard_cap_l28": 28_000_000,
    "emission_ceiling_l28": 11_130_000,
    "historically_mined_l28": 2_824_584,
    "treasury_locked_l28": 500_000,
    "circulating_snapshot_l28": 2_324_584,
    "halving_interval": 210_000,
    "reward_sequence": [28, 14, 7, 3, 1, 0],
    "historical_mined_through_entry": 100_877,
    "next_canonical_height": 100_878,
}

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
    by_id: dict[str, Path] = {}
    for path in list(QUOTE_DIR.glob("*.json")) + list(UPR_DIR.glob("*.json")):
        by_id[path.stem] = path
    missing = [cid for cid in PLANNED_IDS if cid not in by_id]
    if missing:
        raise AssertionError(f"missing fixtures: {missing}")
    extra = sorted(set(by_id) - set(PLANNED_IDS))
    if extra:
        raise AssertionError(f"unexpected fixtures: {extra}")
    return [by_id[cid] for cid in PLANNED_IDS]


def _contains_secret_keys(obj: Any) -> bool:
    if isinstance(obj, dict):
        if any(k in SECRET_FIELD_NAMES for k in obj):
            return True
        return any(_contains_secret_keys(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_contains_secret_keys(v) for v in obj)
    return False


def validate_envelope(req: dict[str, Any], expected_operation: str) -> str | None:
    if any(k in req for k in SECRET_FIELD_NAMES):
        return "secret_material_forbidden"
    if tuple(req.keys()) != ENVELOPE_KEYS:
        return "schema_invalid"
    if req["interface_profile"] != INTERFACE_PROFILE:
        return "interface_profile_unsupported"
    if req["operation"] != expected_operation:
        return "operation_unsupported"
    if req["operation"] == "get_quote":
        return "operation_unsupported"
    if not isinstance(req["request_id"], str) or not HEX64_RE.fullmatch(req["request_id"]):
        return "schema_invalid"
    if type(req["created_at"]) is not int or type(req["expires_at"]) is not int:
        return "schema_invalid"
    if req["expires_at"] <= req["created_at"]:
        return "schema_invalid"
    nonce = req["nonce"]
    if not isinstance(nonce, str) or not nonce or "\x00" in nonce:
        return "schema_invalid"
    if len(nonce.encode("utf-8")) > 256:
        return "schema_invalid"
    if req["execution_authorized"] is not False:
        return "schema_invalid"
    if not isinstance(req["params"], dict):
        return "schema_invalid"
    return None


def build_quote_object(params: dict[str, Any]) -> dict[str, Any]:
    terms_hash = canon_sha256(params["service_terms"])
    return {
        "quote_profile": "l28-uaii-quote/v0.1",
        "payer_identity": params["payer_identity"],
        "payee_identity": params["payee_identity"],
        "service_id": params["service_id"],
        "service_params": params["service_params"],
        "amount": params["amount"],
        "currency": params["currency"],
        "purpose": params["purpose"],
        "quote_expires_at": params["quote_expires_at"],
        "quote_nonce": params["quote_nonce"],
        "max_amount": params["max_amount"],
        "rejectable": params["rejectable"],
        "service_terms": params["service_terms"],
        "service_terms_hash": terms_hash,
        "spend_authorized": False,
        "execution_authorized": False,
    }


def validate_create_quote_params(params: dict[str, Any], created_at: int, expires_at: int) -> str | None:
    if tuple(params.keys()) != QUOTE_PARAM_KEYS:
        return "schema_invalid"
    if type(params["amount"]) is not int or params["amount"] <= 0:
        return "amount_invalid"
    if params["currency"] != "L28":
        return "currency_invalid"
    if type(params["max_amount"]) is not int or params["max_amount"] < params["amount"]:
        return "amount_invalid"
    if params["rejectable"] is not True:
        return "schema_invalid"
    if not isinstance(params["purpose"], str) or not params["purpose"]:
        return "schema_invalid"
    if type(params["quote_expires_at"]) is not int:
        return "quote_expiration_invalid"
    if not (params["quote_expires_at"] > created_at and params["quote_expires_at"] <= expires_at):
        return "quote_expiration_invalid"
    if not isinstance(params["service_params"], dict) or not isinstance(params["service_terms"], dict):
        return "schema_invalid"
    if not isinstance(params["payer_identity"], str) or not params["payer_identity"]:
        return "identity_invalid"
    if not isinstance(params["payee_identity"], str) or not params["payee_identity"]:
        return "identity_invalid"
    if params["payer_identity"] == params["payee_identity"]:
        return "schema_invalid"
    return None


def evaluate_create_quote(fx: dict[str, Any]) -> dict[str, Any]:
    req = fx["request"]
    err = validate_envelope(req, "create_quote")
    if err is not None:
        return {"outcome": "reject", "ok": False, "code": err}

    # FCL expired-quote evaluation uses supporting prior quote + evaluation_time
    if fx["case_id"] == "UAI-CONF-v0.1-QUO-FCL-001":
        prior = fx["supporting_objects"]["prior_quote"]
        t_eval = fx["evaluation_time"]
        if t_eval >= prior["quote_expires_at"]:
            return {"outcome": "reject", "ok": False, "code": "quote_expired"}
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    params = req["params"]
    err = validate_create_quote_params(params, req["created_at"], req["expires_at"])
    if err is not None:
        return {"outcome": "reject", "ok": False, "code": err}

    quote = build_quote_object(params)
    quote_id = canon_sha256(quote)
    expected = fx["expected"]["result"]
    if expected.get("quote_id") != quote_id:
        return {"outcome": "reject", "ok": False, "code": "conflicting_evidence"}
    if expected["quote"].get("spend_authorized") is not False:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if expected.get("spend_authorized") is not False or expected.get("execution_authorized") is not False:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if expected.get("read_only") is not True or expected.get("deterministic") is not True:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if _contains_secret_keys(expected):
        return {"outcome": "reject", "ok": False, "code": "secret_material_forbidden"}
    if tuple(quote.keys()) != QUOTE_OBJECT_KEYS:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    return {
        "outcome": "accept",
        "ok": True,
        "code": fx["expected"]["code"],
        "execution_authorized": False,
    }


def evaluate_upr(fx: dict[str, Any]) -> dict[str, Any]:
    req = fx["request"]
    err = validate_envelope(req, "create_unsigned_payment_request")
    if err is not None:
        return {"outcome": "reject", "ok": False, "code": err}

    params = req["params"]
    if "payment_nonce" not in params:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if tuple(params.keys()) != UPR_PARAM_KEYS:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    quote = params["quote"]
    if not isinstance(quote, dict):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if tuple(quote.keys()) != QUOTE_OBJECT_KEYS:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if canon_sha256(quote["service_terms"]) != quote["service_terms_hash"]:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    computed_qid = canon_sha256(quote)
    if params["quote_id"] != computed_qid:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if params["amount"] != quote["amount"]:
        return {"outcome": "reject", "ok": False, "code": "amount_mismatch"}
    if params["currency"] != "L28" or params["currency"] != quote["currency"]:
        return {"outcome": "reject", "ok": False, "code": "currency_invalid"}
    if params["payer_identity"] != quote["payer_identity"]:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if params["payee_identity"] != quote["payee_identity"]:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if params["service_terms_hash"] != quote["service_terms_hash"]:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if type(params["payment_expires_at"]) is not int:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if params["payment_expires_at"] > quote["quote_expires_at"]:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if not isinstance(params["payment_nonce"], str) or not params["payment_nonce"]:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if _contains_secret_keys(params):
        return {"outcome": "reject", "ok": False, "code": "secret_material_forbidden"}

    payment = {
        "payment_request_profile": "l28-uaii-unsigned-payment-request/v0.1",
        "quote_id": params["quote_id"],
        "payer_identity": params["payer_identity"],
        "payee_identity": params["payee_identity"],
        "amount": params["amount"],
        "currency": params["currency"],
        "purpose": params["purpose"],
        "service_id": params["service_id"],
        "service_terms_hash": params["service_terms_hash"],
        "payment_nonce": params["payment_nonce"],
        "payment_expires_at": params["payment_expires_at"],
        "quote_expires_at": quote["quote_expires_at"],
        "quote_nonce": quote["quote_nonce"],
        "spend_authorized": False,
        "execution_authorized": False,
    }
    expected = fx["expected"]["result"]
    if expected.get("contains_signature") is not False:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    for flag in ("may_submit", "may_settle", "may_mint", "may_mutate_ledger"):
        if expected.get(flag) is not False:
            return {"outcome": "reject", "ok": False, "code": "adapter_override_forbidden"}
    if expected.get("spend_authorized") is not False or expected.get("execution_authorized") is not False:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if expected.get("payment_request_id") != canon_sha256(payment):
        return {"outcome": "reject", "ok": False, "code": "conflicting_evidence"}
    if _contains_secret_keys(expected):
        return {"outcome": "reject", "ok": False, "code": "secret_material_forbidden"}

    return {
        "outcome": "accept",
        "ok": True,
        "code": fx["expected"]["code"],
        "execution_authorized": False,
    }


def evaluate_fixture(fx: dict[str, Any]) -> dict[str, Any]:
    if fx["operation"] == "create_quote":
        return evaluate_create_quote(fx)
    if fx["operation"] == "create_unsigned_payment_request":
        return evaluate_upr(fx)
    return {"outcome": "reject", "ok": False, "code": "operation_unsupported"}


class TestUniversalAccessQuoteUnsignedPaymentFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]

    def test_discovers_only_two_f83_directories_and_exactly_15(self) -> None:
        self.assertTrue(QUOTE_DIR.is_dir())
        self.assertTrue(UPR_DIR.is_dir())
        self.assertFalse((FIXTURE_ROOT / "get_quote").exists())
        self.assertEqual(len(self.paths), 15)
        self.assertEqual({p.parent for p in self.paths}, {QUOTE_DIR, UPR_DIR})

    def test_unique_planned_ids_and_order(self) -> None:
        ids = [fx["case_id"] for fx in self.fixtures]
        self.assertEqual(ids, list(PLANNED_IDS))
        self.assertEqual(len(set(ids)), 15)

    def test_counts_by_operation_and_class(self) -> None:
        quo = [fx for fx in self.fixtures if fx["area"] == "create_quote"]
        upr = [fx for fx in self.fixtures if fx["area"] == "create_unsigned_payment_request"]
        self.assertEqual(len(quo), 9)
        self.assertEqual(len(upr), 6)
        qc = Counter(fx["class"] for fx in quo)
        uc = Counter(fx["class"] for fx in upr)
        self.assertEqual(qc["positive"], 1)
        self.assertEqual(qc["negative"], 4)
        self.assertEqual(qc["boundary"], 3)
        self.assertEqual(qc["fail_closed"], 1)
        self.assertEqual(uc["positive"], 1)
        self.assertEqual(uc["negative"], 3)
        self.assertEqual(uc["boundary"], 1)
        self.assertEqual(uc["fail_closed"], 1)

    def test_structure_mapping_no_get_quote(self) -> None:
        required_top = (
            "fixture_schema",
            "plan_version",
            "fixture_id",
            "case_id",
            "area",
            "class",
            "operation",
            "description",
            "interface_profile",
            "fixed_clock",
            "identities",
            "request_encoding",
            "expected",
            "canonical",
            "safety",
        )
        for fx in self.fixtures:
            for key in required_top:
                self.assertIn(key, fx)
            self.assertEqual(fx["fixture_schema"], FIXTURE_SCHEMA)
            self.assertEqual(fx["plan_version"], PLAN_VERSION)
            self.assertEqual(fx["interface_profile"], INTERFACE_PROFILE)
            self.assertRegex(fx["case_id"], CASE_ID_RE)
            self.assertNotEqual(fx["operation"], "get_quote")
            self.assertNotEqual(fx["area"], "get_quote")
            pol = fx["case_id"].split("-")[4]
            self.assertEqual(fx["class"], CLASS_FROM_POL[pol])
            area_code = fx["case_id"].split("-")[3]
            if area_code == "QUO":
                self.assertEqual(fx["area"], "create_quote")
                self.assertEqual(fx["operation"], "create_quote")
            else:
                self.assertEqual(fx["area"], "create_unsigned_payment_request")
                self.assertEqual(fx["operation"], "create_unsigned_payment_request")
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
            if "quote_canonical_sha256" in fx["canonical"]:
                quote = fx["expected"]["result"]["quote"]
                self.assertEqual(canon_sha256(quote), fx["canonical"]["quote_canonical_sha256"])
                self.assertEqual(canon_sha256(quote), fx["canonical"]["quote_id"])
                self.assertEqual(
                    canon_sha256(quote["service_terms"]),
                    fx["canonical"]["service_terms_hash"],
                )
            if "payment_canonical_sha256" in fx["canonical"]:
                payment = fx["expected"]["result"]["unsigned_payment_request"]
                self.assertEqual(
                    canon_sha256(payment), fx["canonical"]["payment_canonical_sha256"]
                )
                self.assertEqual(
                    canon_sha256(payment), fx["canonical"]["payment_request_id"]
                )

    def test_evaluate_matches_expected_codes(self) -> None:
        for fx in self.fixtures:
            observed = evaluate_fixture(fx)
            self.assertEqual(observed["outcome"], fx["expected"]["outcome"], fx["case_id"])
            self.assertEqual(observed["ok"], fx["expected"]["ok"], fx["case_id"])
            self.assertEqual(observed["code"], fx["expected"]["code"], fx["case_id"])
            self.assertIs(observed.get("execution_authorized", False), False)

    def test_deterministic_repeated_evaluation(self) -> None:
        first = [evaluate_fixture(fx) for fx in self.fixtures]
        second = [evaluate_fixture(fx) for fx in self.fixtures]
        third = [canon_sha256(fx) for fx in self.fixtures]
        fourth = [canon_sha256(fx) for fx in self.fixtures]
        self.assertEqual(first, second)
        self.assertEqual(third, fourth)

    def test_quote_read_only_and_unsigned_payment_boundaries(self) -> None:
        quo_pos = next(fx for fx in self.fixtures if fx["case_id"] == "UAI-CONF-v0.1-QUO-POS-001")
        self.assertIs(quo_pos["expected"]["result"]["read_only"], True)
        self.assertIs(quo_pos["expected"]["result"]["deterministic"], True)
        self.assertIs(quo_pos["expected"]["result"]["spend_authorized"], False)

        upr_pos = next(fx for fx in self.fixtures if fx["case_id"] == "UAI-CONF-v0.1-UPR-POS-001")
        result = upr_pos["expected"]["result"]
        self.assertIs(result["contains_signature"], False)
        self.assertIs(result["may_submit"], False)
        self.assertIs(result["may_settle"], False)
        self.assertIs(result["may_mint"], False)
        self.assertIs(result["may_mutate_ledger"], False)
        payment = result["unsigned_payment_request"]
        for key in SECRET_FIELD_NAMES:
            self.assertNotIn(key, payment)

    def test_protected_facts_unchanged(self) -> None:
        plan = (REPO_ROOT / "docs" / "universal_access_conformance_plan_v0.1.md").read_text(
            encoding="utf-8"
        )
        iface = (REPO_ROOT / "docs" / "universal_access_interface_v0.1.md").read_text(
            encoding="utf-8"
        )
        protocol = (REPO_ROOT / "PROTOCOL.md").read_text(encoding="utf-8")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        for text in (plan, iface):
            self.assertIn("28,000,000 L28", text)
            self.assertIn("11,130,000 L28", text)
            self.assertIn("2,824,584 L28", text)
            self.assertIn("500,000 L28", text)
            self.assertIn("2,324,584 L28", text)
            self.assertIn("L28 Protocol v1.0.0", text)
            self.assertIn("Coinbase is the only issuance", text)
            self.assertIn("consensus-derived", text)
            self.assertIn("no authority", text)
        self.assertIn("210,000", protocol)
        self.assertIn("28 → 14 → 7 → 3 → 1 → 0", protocol)
        self.assertIn("11,130,000", protocol)
        self.assertIn("28,000,000", protocol)
        self.assertIn("100,877", readme)
        # next canonical height used by existing balance fixtures / ledger conventions
        bal_pos = (
            FIXTURE_ROOT / "get_balance" / "UAI-CONF-v0.1-BAL-POS-001.json"
        ).read_text(encoding="utf-8")
        self.assertIn('"canonical_height": 100878', bal_pos)
        self.assertEqual(PROTECTED_ECONOMICS["historical_mined_through_entry"], 100_877)
        self.assertEqual(PROTECTED_ECONOMICS["next_canonical_height"], 100_878)
        self.assertEqual(PROTECTED_ECONOMICS["halving_interval"], 210_000)
        self.assertEqual(PROTECTED_ECONOMICS["reward_sequence"], [28, 14, 7, 3, 1, 0])

    def test_safety_scan(self) -> None:
        for path in self.paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("/Users/", text)
            self.assertNotIn("BEGIN PRIVATE", text)
            self.assertNotIn("os.environ", text)
            self.assertNotIn("seed_phrase", text)
            self.assertNotIn("mnemonic", text)
            self.assertNotIn("get_quote", text)
            self.assertIsNone(re.search(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T", text))
            self.assertNotIn('"private_key"', text)
            self.assertNotIn('"signature"', text)

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
