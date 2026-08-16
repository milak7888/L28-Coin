# SPDX-License-Identifier: Apache-2.0
"""Foundation 90 — isolated control/idempotency/audit fixture validation.

Test-local only. Does not import or initialize ledgers, wallets, mining,
networking, services, signing, settlement, or adapters. Does not implement a
production Universal Access Interface runtime.
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
CTL_DIR = FIXTURE_ROOT / "control"

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
ALWAYS_FALSE = (
    "spend_authorized",
    "signing_authorized",
    "settlement_authorized",
    "ledger_mutated",
    "execution_authorized",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
CASE_ID_RE = re.compile(r"^UAI-CONF-v0\.1-CTL-(POS|NEG|BND|FCL)-\d{3}$")

PLANNED_IDS = (
    "UAI-CONF-v0.1-CTL-POS-001",
    "UAI-CONF-v0.1-CTL-NEG-001",
    "UAI-CONF-v0.1-CTL-BND-001",
    "UAI-CONF-v0.1-CTL-BND-002",
    "UAI-CONF-v0.1-CTL-FCL-001",
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
    by_id = {p.stem: p for p in CTL_DIR.glob("*.json")}
    missing = [cid for cid in PLANNED_IDS if cid not in by_id]
    if missing:
        raise AssertionError(f"missing fixtures: {missing}")
    extra = sorted(set(by_id) - set(PLANNED_IDS))
    if extra:
        raise AssertionError(f"unexpected fixtures: {extra}")
    return [by_id[cid] for cid in PLANNED_IDS]


def collect_audit_ids(obj: Any) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in (
                "request_id",
                "quote_id",
                "payment_request_id",
                "receipt_id",
                "report_id",
                "audit_id",
            ) and isinstance(value, str):
                found.append(value)
            found.extend(collect_audit_ids(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(collect_audit_ids(item))
    return found


def validate_envelope(req: dict[str, Any]) -> str | None:
    if tuple(req.keys()) != ENVELOPE_KEYS:
        return "schema_invalid"
    if req["interface_profile"] != INTERFACE_PROFILE:
        return "interface_profile_unsupported"
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


def evaluate_control(fx: dict[str, Any]) -> dict[str, Any]:
    req = fx["request"]
    err = validate_envelope(req)
    if err is not None:
        return {"outcome": "reject", "ok": False, "code": err}

    params = req["params"]
    receipt_id = params.get("receipt_id")
    accepted = params.get("accepted_receipt_ids")
    if isinstance(accepted, list) and isinstance(receipt_id, str) and receipt_id in accepted:
        return {
            "outcome": "reject",
            "ok": False,
            "code": "replayed",
            "execution_authorized": False,
            "result": {"replay_status": "replayed", "rejection_reason": "replayed"},
        }

    supporting = fx.get("supporting_objects")
    if isinstance(supporting, dict):
        threshold = supporting.get("approval_threshold_evidence")
        if isinstance(threshold, dict):
            if threshold.get("spend_authorized") is not False:
                return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
            if threshold.get("authorization_granted") is not False:
                return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
            if threshold.get("execution_authorized") is not False:
                return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    if "repeat_request" in fx:
        if canon_sha256(fx["repeat_request"]) != canon_sha256(req):
            return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    expected_result = fx["expected"].get("result")
    if not isinstance(expected_result, dict):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    for key in ALWAYS_FALSE:
        if expected_result.get(key) is not False:
            return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    return {
        "outcome": "accept",
        "ok": True,
        "code": "ok",
        "execution_authorized": False,
        "result": expected_result,
    }


def evaluate_fixture(fx: dict[str, Any]) -> dict[str, Any]:
    return evaluate_control(fx)


class TestUniversalAccessControlFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]
        cls.by_id = {fx["case_id"]: fx for fx in cls.fixtures}

    def test_discovers_only_control_dir_and_exactly_5(self) -> None:
        self.assertTrue(CTL_DIR.is_dir())
        self.assertEqual(len(self.paths), 5)
        self.assertEqual({p.parent for p in self.paths}, {CTL_DIR})

    def test_unique_planned_ids_and_order(self) -> None:
        ids = [fx["case_id"] for fx in self.fixtures]
        self.assertEqual(ids, list(PLANNED_IDS))
        self.assertEqual(len(set(ids)), 5)

    def test_counts(self) -> None:
        counts = Counter(fx["class"] for fx in self.fixtures)
        self.assertEqual(counts["positive"], 1)
        self.assertEqual(counts["negative"], 1)
        self.assertEqual(counts["boundary"], 2)
        self.assertEqual(counts["fail_closed"], 1)

    def test_structure_and_mapping(self) -> None:
        for fx in self.fixtures:
            self.assertEqual(fx["fixture_schema"], FIXTURE_SCHEMA)
            self.assertEqual(fx["plan_version"], PLAN_VERSION)
            self.assertEqual(fx["interface_profile"], INTERFACE_PROFILE)
            self.assertEqual(fx["area"], "control")
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
            if "repeat_request" in fx:
                self.assertEqual(
                    canon_sha256(fx["repeat_request"]),
                    fx["canonical"]["repeat_request_canonical_sha256"],
                    fx["case_id"],
                )
                self.assertEqual(
                    fx["canonical"]["request_canonical_sha256"],
                    fx["canonical"]["repeat_request_canonical_sha256"],
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
                for key in ALWAYS_FALSE:
                    self.assertIs(observed["result"][key], False, fx["case_id"])

    def test_expected_result_flags_always_false_when_present(self) -> None:
        for fx in self.fixtures:
            result = fx["expected"].get("result")
            if isinstance(result, dict):
                for key in ALWAYS_FALSE:
                    if key in result:
                        self.assertIs(result[key], False, fx["case_id"])

    def test_pos_identical_canonical_inputs_equivalent(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-CTL-POS-001"]
        self.assertEqual(fx["request"], fx["repeat_request"])
        first = evaluate_fixture(fx)
        second = evaluate_fixture(fx)
        self.assertEqual(first, second)
        self.assertIs(fx["expected"]["result"]["deterministic_equivalence"], True)
        self.assertIs(fx["expected"]["result"]["repeat_equivalent"], True)

    def test_neg_uppercase_audit_id_rejected(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-CTL-NEG-001"]
        request_id = fx["request"]["request_id"]
        self.assertEqual(len(request_id), 64)
        self.assertNotEqual(request_id, request_id.lower())
        self.assertIsNone(HEX64_RE.fullmatch(request_id))
        self.assertEqual(fx["expected"]["code"], "schema_invalid")

    def test_bnd_audit_ids_are_64_lowercase_hex(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-CTL-BND-001"]
        for value in collect_audit_ids(fx["request"]):
            self.assertRegex(value, HEX64_RE.pattern)
        result = fx["expected"]["result"]
        self.assertIs(result["audit_ids_lowercase_hex64"], True)
        self.assertRegex(result["request_id"], HEX64_RE.pattern)
        self.assertRegex(result["quote_id"], HEX64_RE.pattern)
        self.assertRegex(result["receipt_id"], HEX64_RE.pattern)
        self.assertEqual(fx["expected"]["outcome"], "accept")

    def test_bnd_limits_never_grant_spend(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-CTL-BND-002"]
        threshold = fx["supporting_objects"]["approval_threshold_evidence"]
        self.assertIn("per_transaction_limit", threshold)
        self.assertIn("cumulative_maximum", threshold)
        self.assertIn("max_amount", threshold)
        self.assertIs(threshold["spend_authorized"], False)
        self.assertIs(fx["expected"]["result"]["implicit_authorization"], False)
        self.assertIs(
            fx["expected"]["result"]["approval_threshold_fields_are_evidence_only"],
            True,
        )
        self.assertIs(fx["expected"]["result"]["spend_authorized"], False)

    def test_fcl_replay_after_accept_fail_closed(self) -> None:
        fx = self.by_id["UAI-CONF-v0.1-CTL-FCL-001"]
        params = fx["request"]["params"]
        self.assertIn(params["receipt_id"], params["accepted_receipt_ids"])
        self.assertEqual(fx["expected"]["code"], "replayed")
        self.assertEqual(fx["expected"]["result"]["replay_status"], "replayed")

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
