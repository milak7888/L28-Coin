# SPDX-License-Identifier: Apache-2.0
"""Foundation 86 — isolated verify_signed_receipt fixture validation.

Test-local only. Does not import or initialize ledgers, wallets, mining,
networking, services, signing, settlement, or adapters. Does not implement a
production Universal Access Interface runtime validator or cryptographic
signed-receipt verification.
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
VSR_DIR = FIXTURE_ROOT / "verify_signed_receipt"

FIXTURE_SCHEMA = "l28-uai-conformance-fixture/v0.1"
PLAN_VERSION = "universal-access-conformance-plan/v0.1"
INTERFACE_PROFILE = "l28-universal-ai-access-interface/v0.1"
SIGNED_RECEIPT_PROFILE = "l28-uaii-signed-receipt/v0.1"
SIGNER_ALGORITHM_PROFILE = "ed25519-pure/v0.1"

# Foundation 64 §9.1.12 / §10.5 — documented here; this module does not import
# coin.uaii_signed_receipt.
RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS = 300

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
VSR_PARAM_KEYS = (
    "signed_receipt",
    "accepted_receipt_ids",
    "verification_time",
    "governance_approval_evidence",
    "authorization_response_evidence",
)
SIGNED_FACTS_KEYS = (
    "receipt_profile",
    "receipt_id",
    "prior_receipt_id",
    "correlation_id",
    "request_id",
    "quote_id",
    "service_result_id",
    "payer_public_identity",
    "provider_public_identity",
    "asset_id",
    "amount",
    "purpose",
    "created_at",
    "expires_at",
    "receipt_nonce",
    "transaction_id",
    "settlement_status",
    "signer_algorithm_profile",
    "signer_public_key_id",
    "signer_public_key",
    "signed_payload_digest",
    "signature",
    "signing_authorized",
    "spend_authorized",
    "settlement_authorized",
    "ledger_mutated",
    "execution_authorized",
)
ALWAYS_FALSE = (
    "signing_authorized",
    "spend_authorized",
    "settlement_authorized",
    "ledger_mutated",
    "execution_authorized",
    "transition_applied",
    "application_authorized",
    "authorization_granted",
    "authorization_active",
)
SECRET_KEYS = frozenset(
    {
        "private_key",
        "secret_key",
        "seed",
        "seed_phrase",
        "mnemonic",
        "signing_key",
    }
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
HEX128_RE = re.compile(r"^[0-9a-f]{128}$")
CASE_ID_RE = re.compile(r"^UAI-CONF-v0\.1-VSR-(POS|NEG|BND|FCL)-\d{3}$")

PLANNED_IDS = (
    "UAI-CONF-v0.1-VSR-POS-001",
    "UAI-CONF-v0.1-VSR-NEG-001",
    "UAI-CONF-v0.1-VSR-NEG-002",
    "UAI-CONF-v0.1-VSR-NEG-003",
    "UAI-CONF-v0.1-VSR-BND-001",
    "UAI-CONF-v0.1-VSR-BND-002",
    "UAI-CONF-v0.1-VSR-BND-003",
    "UAI-CONF-v0.1-VSR-FCL-001",
    "UAI-CONF-v0.1-VSR-FCL-002",
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
    by_id = {p.stem: p for p in VSR_DIR.glob("*.json")}
    missing = [cid for cid in PLANNED_IDS if cid not in by_id]
    if missing:
        raise AssertionError(f"missing fixtures: {missing}")
    extra = sorted(set(by_id) - set(PLANNED_IDS))
    if extra:
        raise AssertionError(f"unexpected fixtures: {extra}")
    return [by_id[cid] for cid in PLANNED_IDS]


def contains_secret_keys(obj: Any) -> bool:
    if isinstance(obj, dict):
        if SECRET_KEYS.intersection(obj.keys()):
            return True
        return any(contains_secret_keys(v) for v in obj.values())
    if isinstance(obj, list):
        return any(contains_secret_keys(v) for v in obj)
    return False


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
    if req["operation"] != "verify_signed_receipt":
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


def evidence_conflict(gov: Any, auth: Any) -> bool:
    if not isinstance(gov, dict) or not isinstance(auth, dict):
        return False
    if gov == {} or auth == {}:
        return False
    gov_decision = gov.get("approval_decision")
    auth_decision = auth.get("authorization_decision")
    if gov_decision == "approved" and auth_decision == "denied":
        return True
    if gov_decision == "rejected" and auth_decision == "authorized":
        return True
    return False


def expiration_status(expires_at: int, verification_time: int) -> str:
    if verification_time > expires_at + RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS:
        return "expired"
    return "valid"


def evaluate_verify_signed_receipt(fx: dict[str, Any]) -> dict[str, Any]:
    req = fx["request"]
    err = validate_envelope(req)
    if err is not None:
        return {"outcome": "reject", "ok": False, "code": err}

    params = req["params"]
    if "verification_time" not in params:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if tuple(params.keys()) != VSR_PARAM_KEYS:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    signed = params["signed_receipt"]
    if not isinstance(signed, dict):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if contains_secret_keys(signed) or contains_secret_keys(params):
        return {"outcome": "reject", "ok": False, "code": "secret_material_forbidden"}
    if tuple(signed.keys()) != SIGNED_FACTS_KEYS:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    signature = signed.get("signature")
    if not isinstance(signature, str) or not HEX128_RE.fullmatch(signature):
        return {"outcome": "reject", "ok": False, "code": "signature_invalid"}

    if signed["receipt_profile"] != SIGNED_RECEIPT_PROFILE:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if signed["signer_algorithm_profile"] != SIGNER_ALGORITHM_PROFILE:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if not isinstance(signed["signer_public_key_id"], str) or not HEX64_RE.fullmatch(
        signed["signer_public_key_id"]
    ):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if not isinstance(signed["signer_public_key"], str) or not HEX64_RE.fullmatch(
        signed["signer_public_key"]
    ):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if not isinstance(signed["receipt_id"], str) or not HEX64_RE.fullmatch(
        signed["receipt_id"]
    ):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    flag_err = assert_always_false_flags(signed)
    if flag_err is not None:
        return {"outcome": "reject", "ok": False, "code": flag_err}

    accepted = params["accepted_receipt_ids"]
    if not isinstance(accepted, list):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    verification_time = params["verification_time"]
    if type(verification_time) is not int:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if type(signed["expires_at"]) is not int:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    gov = params["governance_approval_evidence"]
    auth = params["authorization_response_evidence"]
    if not isinstance(gov, dict) or not isinstance(auth, dict):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if evidence_conflict(gov, auth):
        return {"outcome": "reject", "ok": False, "code": "conflicting_evidence"}

    exp_status = expiration_status(signed["expires_at"], verification_time)
    if signed["receipt_id"] in accepted:
        return {
            "outcome": "reject",
            "ok": False,
            "code": "replayed",
            "execution_authorized": False,
            "result": {
                "replay_status": "replayed",
                "expiration_status": exp_status,
                "rejection_reason": "replayed",
                "replay_precedes_expiration": True,
            },
        }

    supporting = fx.get("supporting_objects")
    if isinstance(supporting, dict):
        threshold = supporting.get("approval_threshold_evidence")
        if isinstance(threshold, dict):
            if threshold.get("authorization_granted") is not False:
                return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
            if threshold.get("spend_authorized") is not False:
                return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
            if threshold.get("execution_authorized") is not False:
                return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    expected_result = fx["expected"].get("result")
    if not isinstance(expected_result, dict):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    flag_err = assert_always_false_flags(expected_result)
    if flag_err is not None:
        return {"outcome": "reject", "ok": False, "code": flag_err}
    if expected_result.get("receipt_profile") != SIGNED_RECEIPT_PROFILE:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if expected_result.get("verification_composition") != "allowed":
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if expected_result.get("expiration_status") != "valid":
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if exp_status != "valid":
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    return {
        "outcome": "accept",
        "ok": True,
        "code": "signed_receipt_verified",
        "execution_authorized": False,
        "result": expected_result,
    }


def evaluate_fixture(fx: dict[str, Any]) -> dict[str, Any]:
    if fx["operation"] != "verify_signed_receipt":
        return {"outcome": "reject", "ok": False, "code": "operation_unsupported"}
    return evaluate_verify_signed_receipt(fx)


class TestUniversalAccessVerifySignedReceiptFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]
        cls.by_id = {fx["case_id"]: fx for fx in cls.fixtures}

    def test_discovers_only_verify_signed_receipt_dir_and_exactly_9(self) -> None:
        self.assertTrue(VSR_DIR.is_dir())
        self.assertEqual(len(self.paths), 9)
        self.assertEqual({p.parent for p in self.paths}, {VSR_DIR})

    def test_unique_planned_ids_and_order(self) -> None:
        ids = [fx["case_id"] for fx in self.fixtures]
        self.assertEqual(ids, list(PLANNED_IDS))
        self.assertEqual(len(set(ids)), 9)

    def test_counts(self) -> None:
        counts = Counter(fx["class"] for fx in self.fixtures)
        self.assertEqual(counts["positive"], 1)
        self.assertEqual(counts["negative"], 3)
        self.assertEqual(counts["boundary"], 3)
        self.assertEqual(counts["fail_closed"], 2)

    def test_structure_and_mapping(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(fx["fixture_schema"], FIXTURE_SCHEMA)
            self.assertEqual(fx["plan_version"], PLAN_VERSION)
            self.assertEqual(fx["interface_profile"], INTERFACE_PROFILE)
            self.assertEqual(fx["area"], "verify_signed_receipt")
            self.assertEqual(fx["operation"], "verify_signed_receipt")
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
                self.assertEqual(result["verification_composition"], "allowed")
                self.assertEqual(result["receipt_profile"], SIGNED_RECEIPT_PROFILE)

    def test_expected_result_flags_always_false_when_present(self) -> None:
        for fx in self.fixtures:
            result = fx["expected"].get("result")
            if isinstance(result, dict):
                for key in ALWAYS_FALSE:
                    if key in result:
                        self.assertIs(result[key], False, fx["case_id"])

    def test_pos_empty_evidence_and_grant_flags_false(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-VSR-POS-001"]
        params = fx["request"]["params"]
        self.assertEqual(params["governance_approval_evidence"], {})
        self.assertEqual(params["authorization_response_evidence"], {})
        self.assertEqual(tuple(params["signed_receipt"].keys()), SIGNED_FACTS_KEYS)
        result = fx["expected"]["result"]
        self.assertEqual(result["verification_status"], "verified")
        self.assertEqual(result["verification_composition"], "allowed")
        for key in ALWAYS_FALSE:
            self.assertIs(result[key], False)

    def test_neg_invalid_public_signature_material(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-VSR-NEG-001"]
        signature = fx["request"]["params"]["signed_receipt"]["signature"]
        self.assertFalse(bool(HEX128_RE.fullmatch(signature)))
        self.assertEqual(fx["expected"]["code"], "signature_invalid")

    def test_neg_replay_precedes_expiration(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-VSR-NEG-002"]
        params = fx["request"]["params"]
        receipt_id = params["signed_receipt"]["receipt_id"]
        self.assertIn(receipt_id, params["accepted_receipt_ids"])
        expires_at = params["signed_receipt"]["expires_at"]
        verification_time = params["verification_time"]
        self.assertEqual(
            expiration_status(expires_at, verification_time),
            "expired",
        )
        result = fx["expected"]["result"]
        self.assertEqual(result["replay_status"], "replayed")
        self.assertEqual(result["expiration_status"], "expired")
        self.assertEqual(result["rejection_reason"], "replayed")
        self.assertIs(result["replay_precedes_expiration"], True)
        self.assertEqual(fx["expected"]["code"], "replayed")

    def test_neg_conflicting_governance_vs_authorization(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-VSR-NEG-003"]
        params = fx["request"]["params"]
        self.assertEqual(
            params["governance_approval_evidence"]["approval_decision"],
            "approved",
        )
        self.assertEqual(
            params["authorization_response_evidence"]["authorization_decision"],
            "denied",
        )
        self.assertEqual(fx["expected"]["code"], "conflicting_evidence")

    def test_bnd_verification_time_equal_expires_at_is_valid(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-VSR-BND-001"]
        params = fx["request"]["params"]
        self.assertEqual(
            params["verification_time"],
            params["signed_receipt"]["expires_at"],
        )
        self.assertEqual(fx["expected"]["outcome"], "accept")
        self.assertEqual(fx["expected"]["result"]["expiration_status"], "valid")
        self.assertEqual(
            fx["expected"]["result"]["documented_boundary"],
            "verification_time_equal_expires_at_is_valid",
        )

    def test_bnd_approval_thresholds_never_implicit_grant(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-VSR-BND-002"]
        threshold = fx["supporting_objects"]["approval_threshold_evidence"]
        self.assertIn("per_transaction_limit", threshold)
        self.assertIn("cumulative_maximum", threshold)
        self.assertIs(threshold["authorization_granted"], False)
        self.assertIs(fx["expected"]["result"]["implicit_authorization"], False)
        self.assertIs(
            fx["expected"]["result"]["approval_threshold_fields_are_evidence_only"],
            True,
        )
        for key in ALWAYS_FALSE:
            self.assertIs(fx["expected"]["result"][key], False)

    def test_bnd_signature_metadata_public_only(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-VSR-BND-003"]
        signed = fx["request"]["params"]["signed_receipt"]
        self.assertEqual(signed["signer_algorithm_profile"], SIGNER_ALGORITHM_PROFILE)
        self.assertRegex(signed["signer_public_key_id"], HEX64_RE.pattern)
        self.assertNotIn("private_key", signed)
        self.assertIs(fx["expected"]["result"]["private_key_material_absent"], True)
        self.assertFalse(contains_secret_keys(fx))

    def test_fcl_missing_verification_time(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-VSR-FCL-001"]
        self.assertNotIn("verification_time", fx["request"]["params"])
        self.assertEqual(fx["expected"]["code"], "schema_invalid")

    def test_fcl_incomplete_signed_receipt(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-VSR-FCL-002"]
        signed = fx["request"]["params"]["signed_receipt"]
        self.assertNotEqual(tuple(signed.keys()), SIGNED_FACTS_KEYS)
        self.assertNotIn("receipt_id", signed)
        self.assertEqual(fx["expected"]["code"], "schema_invalid")

    def test_no_private_key_material_in_fixtures(self) -> None:
        for fx in self.fixtures:
            self.assertFalse(contains_secret_keys(fx), fx["case_id"])
            self.assertIs(fx["safety"]["contains_private_keys"], False)

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
