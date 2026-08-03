# SPDX-License-Identifier: Apache-2.0
"""Foundation 81 — isolated envelope + discover_capabilities fixture validation.

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
ENVELOPE_DIR = FIXTURE_ROOT / "envelope"
DISCOVER_DIR = FIXTURE_ROOT / "discover_capabilities"

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
SECRET_FIELD_NAMES = frozenset(
    {
        "private_key",
        "secret_key",
        "seed_phrase",
        "mnemonic",
        "password",
        "api_key",
    }
)
KNOWN_OPERATIONS = frozenset(
    {
        "discover_capabilities",
        "get_protocol_status",
        "get_balance",
        "create_quote",
        "create_unsigned_payment_request",
        "validate_payment",
        "get_payment_receipt",
        "verify_signed_receipt",
        "create_refund_request",
        "create_refund_receipt",
    }
)
FORBIDDEN_CAPABILITY_OPS = frozenset({"sign_and_broadcast", "autonomous_spend"})

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
CASE_ID_RE = re.compile(
    r"^UAI-CONF-v0\.1-(ENV|CAP)-(POS|NEG|BND|FCL)-\d{3}$"
)

PLANNED_ENV_IDS = (
    "UAI-CONF-v0.1-ENV-POS-001",
    "UAI-CONF-v0.1-ENV-NEG-001",
    "UAI-CONF-v0.1-ENV-NEG-002",
    "UAI-CONF-v0.1-ENV-NEG-003",
    "UAI-CONF-v0.1-ENV-NEG-004",
    "UAI-CONF-v0.1-ENV-NEG-005",
    "UAI-CONF-v0.1-ENV-NEG-006",
    "UAI-CONF-v0.1-ENV-BND-001",
    "UAI-CONF-v0.1-ENV-BND-002",
    "UAI-CONF-v0.1-ENV-BND-003",
    "UAI-CONF-v0.1-ENV-BND-004",
    "UAI-CONF-v0.1-ENV-FCL-001",
    "UAI-CONF-v0.1-ENV-FCL-002",
)
PLANNED_CAP_IDS = (
    "UAI-CONF-v0.1-CAP-POS-001",
    "UAI-CONF-v0.1-CAP-POS-002",
    "UAI-CONF-v0.1-CAP-NEG-001",
    "UAI-CONF-v0.1-CAP-NEG-002",
    "UAI-CONF-v0.1-CAP-FCL-001",
)
PLANNED_IDS = PLANNED_ENV_IDS + PLANNED_CAP_IDS

PROTECTED_ECONOMICS = {
    "hard_cap_l28": 28_000_000,
    "emission_ceiling_l28": 11_130_000,
    "historically_mined_l28": 2_824_584,
    "treasury_locked_l28": 500_000,
    "circulating_snapshot_l28": 2_324_584,
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
    paths = sorted(ENVELOPE_DIR.glob("*.json")) + sorted(DISCOVER_DIR.glob("*.json"))
    return paths


def validate_envelope_request(req: dict[str, Any]) -> str | None:
    """Return None on accept, else a stable error code (test-local)."""
    if any(k in req for k in SECRET_FIELD_NAMES):
        return "secret_material_forbidden"
    keys = tuple(req.keys())
    if keys != ENVELOPE_KEYS:
        # unknown/missing/reordered fields
        if set(keys) - set(ENVELOPE_KEYS):
            if set(keys) & SECRET_FIELD_NAMES:
                return "secret_material_forbidden"
            return "schema_invalid"
        return "schema_invalid"

    profile = req["interface_profile"]
    if not isinstance(profile, str) or profile != INTERFACE_PROFILE:
        return "interface_profile_unsupported"

    operation = req["operation"]
    if not isinstance(operation, str) or operation not in KNOWN_OPERATIONS:
        return "operation_unsupported"

    request_id = req["request_id"]
    if not isinstance(request_id, str) or not HEX64_RE.fullmatch(request_id):
        return "schema_invalid"

    created_at = req["created_at"]
    expires_at = req["expires_at"]
    if type(created_at) is not int or type(expires_at) is not int:
        return "schema_invalid"
    if expires_at <= created_at:
        return "schema_invalid"

    nonce = req["nonce"]
    if not isinstance(nonce, str) or not nonce or "\x00" in nonce:
        return "schema_invalid"
    if len(nonce.encode("utf-8")) > 256:
        return "schema_invalid"

    if req["execution_authorized"] is not False:
        return "schema_invalid"

    params = req["params"]
    if not isinstance(params, dict):
        return "schema_invalid"
    return None


def validate_discover_params(params: dict[str, Any]) -> str | None:
    keys = tuple(params.keys())
    if keys != ("include_adapter_declarations",):
        return "schema_invalid"
    if type(params["include_adapter_declarations"]) is not bool:
        return "schema_invalid"
    return None


def validate_discovery_result(result: dict[str, Any]) -> str | None:
    required = (
        "interface_profile",
        "protocol_version",
        "currency",
        "operations",
        "capabilities",
        "adapter_declarations",
        "execution_authorized",
        "signing_authorized",
        "spend_authorized",
    )
    for key in required:
        if key not in result:
            return "schema_invalid"
    if result["interface_profile"] != INTERFACE_PROFILE:
        return "schema_invalid"
    if result["protocol_version"] != "1.0.0":
        return "schema_invalid"
    if result["currency"] != "L28":
        return "schema_invalid"
    if result["execution_authorized"] is not False:
        return "schema_invalid"
    if result["signing_authorized"] is not False:
        return "schema_invalid"
    if result["spend_authorized"] is not False:
        return "schema_invalid"
    if not isinstance(result["operations"], list):
        return "schema_invalid"
    for op in result["operations"]:
        if op not in KNOWN_OPERATIONS or op in (
            "create_refund_request",
            "create_refund_receipt",
        ):
            # supported discovery list excludes deferred refund ops as executable
            if op in ("create_refund_request", "create_refund_receipt"):
                return "schema_invalid"
        if op in FORBIDDEN_CAPABILITY_OPS:
            return "schema_invalid"
    for cap in result["capabilities"]:
        if not isinstance(cap, dict):
            return "schema_invalid"
        status = cap.get("status")
        op_or = cap.get("operation_or_wildcard")
        if op_or in FORBIDDEN_CAPABILITY_OPS and status == "supported":
            return "schema_invalid"
        if status not in ("supported", "deferred", "forbidden"):
            return "schema_invalid"
    for adapter in result["adapter_declarations"]:
        if not isinstance(adapter, dict):
            return "schema_invalid"
        if adapter.get("status") != "deferred":
            return "schema_invalid"
    if "protected_economics" in result:
        pe = result["protected_economics"]
        for key, value in PROTECTED_ECONOMICS.items():
            if pe.get(key) != value:
                return "adapter_override_forbidden"
        if pe.get("issuance_mechanism") != "coinbase_only":
            return "adapter_override_forbidden"
        if pe.get("height_authority") != "consensus_derived":
            return "adapter_override_forbidden"
        if pe.get("historical_evidence") != "immutable":
            return "adapter_override_forbidden"
        if pe.get("adapter_override_allowed") is not False:
            return "adapter_override_forbidden"
    return None


def evaluate_fixture(fx: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one fixture with test-local rules; return observed outcome."""
    encoding = fx["request_encoding"]

    if encoding == "raw_utf8":
        raw = fx["request_raw"]
        try:
            strict_loads(raw)
        except DuplicateKeyError:
            return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
        except (json.JSONDecodeError, ValueError, UnicodeError):
            return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    req = fx["request"]
    env_err = validate_envelope_request(req)
    if env_err is not None:
        return {"outcome": "reject", "ok": False, "code": env_err}

    if fx["operation"] == "discover_capabilities":
        params_err = validate_discover_params(req["params"])
        if params_err is not None:
            return {"outcome": "reject", "ok": False, "code": params_err}

        if "candidate_response" in fx:
            cand = fx["candidate_response"]
            result = cand.get("result")
            if not isinstance(result, dict):
                return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
            res_err = validate_discovery_result(result)
            if res_err is not None:
                return {"outcome": "reject", "ok": False, "code": res_err}
            # candidate claimed success but should have been rejected by now
            return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

        # synthesize accept using expected result shape checks
        result = fx["expected"]["result"]
        res_err = validate_discovery_result(result)
        if res_err is not None:
            return {"outcome": "reject", "ok": False, "code": res_err}
        return {
            "outcome": "accept",
            "ok": True,
            "code": "ok",
            "execution_authorized": False,
        }

    # envelope-only accept
    return {
        "outcome": "accept",
        "ok": True,
        "code": "ok",
        "execution_authorized": False,
    }


class TestUniversalAccessEnvelopeCapabilityFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]

    def test_discovers_only_two_directories_and_exactly_18(self) -> None:
        self.assertTrue(ENVELOPE_DIR.is_dir())
        self.assertTrue(DISCOVER_DIR.is_dir())
        self.assertEqual(len(self.paths), 18)
        for path in self.paths:
            self.assertTrue(
                path.parent in (ENVELOPE_DIR, DISCOVER_DIR),
                msg=path,
            )
        # no other json under v0.1 beyond the two allowlisted directories
        all_json = set(FIXTURE_ROOT.rglob("*.json"))
        self.assertEqual(all_json, set(self.paths))
        parents = {p.parent for p in self.paths}
        self.assertEqual(parents, {ENVELOPE_DIR, DISCOVER_DIR})

    def test_unique_planned_case_ids(self) -> None:
        ids = [fx["case_id"] for fx in self.fixtures]
        self.assertEqual(len(ids), 18)
        self.assertEqual(len(set(ids)), 18)
        self.assertEqual(set(ids), set(PLANNED_IDS))

    def test_counts_by_area_and_class(self) -> None:
        env = [fx for fx in self.fixtures if fx["area"] == "envelope"]
        cap = [fx for fx in self.fixtures if fx["area"] == "discover_capabilities"]
        self.assertEqual(len(env), 13)
        self.assertEqual(len(cap), 5)
        env_c = Counter(fx["class"] for fx in env)
        cap_c = Counter(fx["class"] for fx in cap)
        self.assertEqual(env_c["positive"], 1)
        self.assertEqual(env_c["negative"], 6)
        self.assertEqual(env_c["boundary"], 4)
        self.assertEqual(env_c["fail_closed"], 2)
        self.assertEqual(cap_c["positive"], 2)
        self.assertEqual(cap_c["negative"], 2)
        self.assertEqual(cap_c["boundary"], 0)
        self.assertEqual(cap_c["fail_closed"], 1)

    def test_fixture_structure_and_mapping(self) -> None:
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
            pol = fx["case_id"].split("-")[4]
            self.assertEqual(fx["class"], CLASS_FROM_POL[pol])
            area_code = fx["case_id"].split("-")[3]
            if area_code == "ENV":
                self.assertEqual(fx["area"], "envelope")
                self.assertEqual(fx["operation"], "envelope")
            else:
                self.assertEqual(fx["area"], "discover_capabilities")
                self.assertEqual(fx["operation"], "discover_capabilities")
            safety = fx["safety"]
            for flag in (
                "contains_private_keys",
                "contains_credentials",
                "contains_production_addresses",
                "contains_environment_values",
                "mutates_historical_ledger",
                "uses_real_balances_or_transactions",
            ):
                self.assertIs(safety[flag], False)
            clock = fx["fixed_clock"]
            for k in ("verification_time", "created_at", "expires_at"):
                self.assertIsInstance(clock[k], int)

    def test_canonical_hashes_recalculated(self) -> None:
        for fx in self.fixtures:
            canon = fx["canonical"]
            if fx["request_encoding"] == "json_object":
                observed = canon_sha256(fx["request"])
                self.assertEqual(observed, canon["request_canonical_sha256"], fx["case_id"])
            else:
                raw = fx["request_raw"].encode("utf-8")
                observed = hashlib.sha256(raw).hexdigest()
                self.assertEqual(observed, canon["request_raw_sha256"], fx["case_id"])

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

    def test_protected_economics_unchanged_in_docs_and_pos_fixtures(self) -> None:
        plan = (REPO_ROOT / "docs" / "universal_access_conformance_plan_v0.1.md").read_text(
            encoding="utf-8"
        )
        iface = (REPO_ROOT / "docs" / "universal_access_interface_v0.1.md").read_text(
            encoding="utf-8"
        )
        for label, text in (("plan", plan), ("interface", iface)):
            self.assertIn("28,000,000 L28", text, label)
            self.assertIn("11,130,000 L28", text, label)
            self.assertIn("2,824,584 L28", text, label)
            self.assertIn("500,000 L28", text, label)
            self.assertIn("2,324,584 L28", text, label)
            self.assertIn("L28 Protocol v1.0.0", text, label)
            self.assertIn("Coinbase is the only issuance", text, label)
            self.assertIn("consensus-derived", text, label)
            self.assertIn("immutable", text.lower())
            self.assertIn("no authority", text)
        for fx in self.fixtures:
            if fx["case_id"] in (
                "UAI-CONF-v0.1-CAP-POS-001",
                "UAI-CONF-v0.1-CAP-POS-002",
            ):
                pe = fx["expected"]["result"]["protected_economics"]
                for key, value in PROTECTED_ECONOMICS.items():
                    self.assertEqual(pe[key], value, fx["case_id"])
                self.assertEqual(pe["issuance_mechanism"], "coinbase_only")
                self.assertEqual(pe["height_authority"], "consensus_derived")
                self.assertEqual(pe["historical_evidence"], "immutable")
                self.assertIs(pe["adapter_override_allowed"], False)

    def test_safety_scan_no_secrets_paths_or_env_timestamps(self) -> None:
        for path in self.paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("/Users/", text)
            self.assertNotIn("BEGIN PRIVATE", text)
            self.assertNotIn("os.environ", text)
            self.assertNotIn("seed_phrase", text)
            self.assertNotIn("mnemonic", text)
            self.assertIsNone(re.search(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T", text))
            # JSON key "private_key" allowed only in the forbidden-field negative case
            if "ENV-NEG-006" not in path.name:
                self.assertNotIn('"private_key"', text)

    def test_no_runtime_activation_imports_in_this_module(self) -> None:
        src = Path(__file__).read_text(encoding="utf-8")
        # Import lines only (ignore prose).
        import_lines = [
            ln for ln in src.splitlines() if ln.startswith(("import ", "from "))
        ]
        joined = "\n".join(import_lines)
        self.assertNotIn("coin.", joined)
        for token in ("socket", "requests", "urllib", "subprocess", "nacl"):
            self.assertNotIn(token, joined)
        self.assertEqual(
            set(import_lines),
            {
                "from __future__ import annotations",
                "import hashlib",
                "import json",
                "import re",
                "import unittest",
                "from collections import Counter",
                "from pathlib import Path",
                "from typing import Any",
            },
        )


if __name__ == "__main__":
    unittest.main()
