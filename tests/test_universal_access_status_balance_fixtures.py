# SPDX-License-Identifier: Apache-2.0
"""Foundation 82 — isolated get_protocol_status + get_balance fixture validation.

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
STATUS_DIR = FIXTURE_ROOT / "get_protocol_status"
BALANCE_DIR = FIXTURE_ROOT / "get_balance"

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
RESERVED_IDENTITIES = frozenset({"COINBASE", "__MINT__"})
OVERRIDE_PARAM_KEYS = frozenset(
    {
        "hard_cap_l28",
        "emission_ceiling_l28",
        "historically_mined_l28",
        "treasury_locked_l28",
        "circulating_snapshot_l28",
        "max_supply",
        "emission_ceiling",
        "historical_mined",
    }
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
CASE_ID_RE = re.compile(r"^UAI-CONF-v0\.1-(PST|BAL)-(POS|NEG|BND|FCL)-\d{3}$")

PLANNED_PST_IDS = (
    "UAI-CONF-v0.1-PST-POS-001",
    "UAI-CONF-v0.1-PST-NEG-001",
    "UAI-CONF-v0.1-PST-FCL-001",
)
PLANNED_BAL_IDS = (
    "UAI-CONF-v0.1-BAL-POS-001",
    "UAI-CONF-v0.1-BAL-NEG-001",
    "UAI-CONF-v0.1-BAL-NEG-002",
    "UAI-CONF-v0.1-BAL-FCL-001",
    "UAI-CONF-v0.1-BAL-FCL-002",
)
PLANNED_IDS = PLANNED_PST_IDS + PLANNED_BAL_IDS

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
    """Return fixtures in Foundation 80 catalog order (not filesystem alpha)."""
    by_id: dict[str, Path] = {}
    for path in list(STATUS_DIR.glob("*.json")) + list(BALANCE_DIR.glob("*.json")):
        case_id = path.stem
        by_id[case_id] = path
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


def validate_protected_economics(pe: dict[str, Any]) -> str | None:
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


def evaluate_protocol_status(fx: dict[str, Any]) -> dict[str, Any]:
    req = fx["request"]
    err = validate_envelope(req, "get_protocol_status")
    if err is not None:
        return {"outcome": "reject", "ok": False, "code": err}

    params = req["params"]
    if any(k in OVERRIDE_PARAM_KEYS for k in params):
        return {"outcome": "reject", "ok": False, "code": "adapter_override_forbidden"}
    if tuple(params.keys()) != ():
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    if fx.get("require_consensus_state") is True:
        consensus = fx.get("consensus_view")
        if not isinstance(consensus, dict) or consensus.get("available") is not True:
            return {
                "outcome": "reject",
                "ok": False,
                "code": "consensus_state_unavailable",
            }

    consensus = fx.get("consensus_view")
    if isinstance(consensus, dict):
        pe = consensus.get("protected_economics")
        if isinstance(pe, dict):
            pe_err = validate_protected_economics(pe)
            if pe_err is not None:
                return {"outcome": "reject", "ok": False, "code": pe_err}
        if consensus.get("height_authority") != "consensus_derived":
            return {"outcome": "reject", "ok": False, "code": "adapter_override_forbidden"}

    result = fx["expected"]["result"]
    if _contains_secret_keys(result):
        return {"outcome": "reject", "ok": False, "code": "secret_material_forbidden"}
    if result.get("protocol_version") != "1.0.0":
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if result.get("execution_authorized") is not False:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    pe = result.get("protected_economics")
    if not isinstance(pe, dict):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    pe_err = validate_protected_economics(pe)
    if pe_err is not None:
        return {"outcome": "reject", "ok": False, "code": pe_err}
    if result.get("height_authority") != "consensus_derived":
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    return {
        "outcome": "accept",
        "ok": True,
        "code": fx["expected"]["code"],
        "execution_authorized": False,
    }


def evaluate_balance(fx: dict[str, Any]) -> dict[str, Any]:
    req = fx["request"]
    err = validate_envelope(req, "get_balance")
    if err is not None:
        return {"outcome": "reject", "ok": False, "code": err}

    params = req["params"]
    if tuple(params.keys()) != ("address", "require_canonical_height"):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    address = params["address"]
    require_height = params["require_canonical_height"]
    if type(require_height) is not bool:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if not isinstance(address, str) or address == "":
        return {"outcome": "reject", "ok": False, "code": "identity_invalid"}
    if address in RESERVED_IDENTITIES:
        return {"outcome": "reject", "ok": False, "code": "reserved_identity_forbidden"}

    if "candidate_response" in fx:
        cand = fx["candidate_response"]
        result = cand.get("result")
        if _contains_secret_keys(result):
            return {"outcome": "reject", "ok": False, "code": "secret_material_forbidden"}
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    ledger = fx.get("ledger_view")
    if not isinstance(ledger, dict):
        return {"outcome": "reject", "ok": False, "code": "ledger_state_unavailable"}
    if ledger.get("read_only") is not True:
        return {"outcome": "reject", "ok": False, "code": "adapter_override_forbidden"}
    if ledger.get("may_mint") is not False or ledger.get("may_mutate_canonical_state") is not False:
        return {"outcome": "reject", "ok": False, "code": "adapter_override_forbidden"}
    if ledger.get("height_authority") != "consensus_derived":
        return {"outcome": "reject", "ok": False, "code": "adapter_override_forbidden"}

    height = ledger.get("canonical_height")
    if require_height is True and type(height) is not int:
        return {"outcome": "reject", "ok": False, "code": "canonical_height_unavailable"}

    balances = ledger.get("balances")
    if not isinstance(balances, dict):
        return {"outcome": "reject", "ok": False, "code": "ledger_state_unavailable"}
    balance = balances.get(address, 0)
    if type(balance) is not int or balance < 0:
        return {"outcome": "reject", "ok": False, "code": "ledger_state_unavailable"}

    state_id = ledger.get("ledger_state_id")
    if not isinstance(state_id, str) or not HEX64_RE.fullmatch(state_id):
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}

    result = fx["expected"]["result"]
    if _contains_secret_keys(result):
        return {"outcome": "reject", "ok": False, "code": "secret_material_forbidden"}
    if result.get("currency") != "L28":
        return {"outcome": "reject", "ok": False, "code": "currency_invalid"}
    if result.get("execution_authorized") is not False:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if result.get("read_only") is not True:
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if result.get("may_mint") is not False or result.get("may_mutate_canonical_state") is not False:
        return {"outcome": "reject", "ok": False, "code": "adapter_override_forbidden"}
    if result.get("height_authority") != "consensus_derived":
        return {"outcome": "reject", "ok": False, "code": "schema_invalid"}
    if result.get("balance") != balance:
        return {"outcome": "reject", "ok": False, "code": "conflicting_evidence"}
    if result.get("canonical_height") != height:
        return {"outcome": "reject", "ok": False, "code": "conflicting_evidence"}

    return {
        "outcome": "accept",
        "ok": True,
        "code": "ok",
        "execution_authorized": False,
    }


def evaluate_fixture(fx: dict[str, Any]) -> dict[str, Any]:
    if fx["operation"] == "get_protocol_status":
        return evaluate_protocol_status(fx)
    if fx["operation"] == "get_balance":
        return evaluate_balance(fx)
    return {"outcome": "reject", "ok": False, "code": "operation_unsupported"}


class TestUniversalAccessStatusBalanceFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = discover_fixture_paths()
        cls.fixtures = [load_fixture_file(p) for p in cls.paths]

    def test_discovers_only_two_new_directories_and_exactly_8(self) -> None:
        self.assertTrue(STATUS_DIR.is_dir())
        self.assertTrue(BALANCE_DIR.is_dir())
        self.assertEqual(len(self.paths), 8)
        self.assertEqual({p.parent for p in self.paths}, {STATUS_DIR, BALANCE_DIR})
        # Do not claim ownership of Foundation 81 dirs; only these two new ones.
        for path in self.paths:
            self.assertIn(path.parent.name, {"get_protocol_status", "get_balance"})

    def test_unique_planned_case_ids_and_order(self) -> None:
        ids = [fx["case_id"] for fx in self.fixtures]
        self.assertEqual(len(ids), 8)
        self.assertEqual(len(set(ids)), 8)
        self.assertEqual(set(ids), set(PLANNED_IDS))
        # Deterministic order: PST then BAL; within area POS, NEG, FCL ascending.
        self.assertEqual(ids, list(PLANNED_IDS))

    def test_counts_by_area_and_class(self) -> None:
        pst = [fx for fx in self.fixtures if fx["area"] == "get_protocol_status"]
        bal = [fx for fx in self.fixtures if fx["area"] == "get_balance"]
        self.assertEqual(len(pst), 3)
        self.assertEqual(len(bal), 5)
        pst_c = Counter(fx["class"] for fx in pst)
        bal_c = Counter(fx["class"] for fx in bal)
        self.assertEqual(pst_c["positive"], 1)
        self.assertEqual(pst_c["negative"], 1)
        self.assertEqual(pst_c["boundary"], 0)
        self.assertEqual(pst_c["fail_closed"], 1)
        self.assertEqual(bal_c["positive"], 1)
        self.assertEqual(bal_c["negative"], 2)
        self.assertEqual(bal_c["boundary"], 0)
        self.assertEqual(bal_c["fail_closed"], 2)

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
            if area_code == "PST":
                self.assertEqual(fx["area"], "get_protocol_status")
                self.assertEqual(fx["operation"], "get_protocol_status")
            else:
                self.assertEqual(fx["area"], "get_balance")
                self.assertEqual(fx["operation"], "get_balance")
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
            observed = canon_sha256(fx["request"])
            self.assertEqual(
                observed,
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

    def test_deterministic_repeated_evaluation(self) -> None:
        first = [evaluate_fixture(fx) for fx in self.fixtures]
        second = [evaluate_fixture(fx) for fx in self.fixtures]
        third = [canon_sha256(fx) for fx in self.fixtures]
        fourth = [canon_sha256(fx) for fx in self.fixtures]
        self.assertEqual(first, second)
        self.assertEqual(third, fourth)

    def test_consensus_derived_height_and_read_only_balance(self) -> None:
        bal_pos = next(fx for fx in self.fixtures if fx["case_id"] == "UAI-CONF-v0.1-BAL-POS-001")
        ledger = bal_pos["ledger_view"]
        self.assertEqual(ledger["height_authority"], "consensus_derived")
        self.assertIs(ledger["read_only"], True)
        self.assertIs(ledger["may_mint"], False)
        self.assertIs(ledger["may_mutate_canonical_state"], False)
        result = bal_pos["expected"]["result"]
        self.assertEqual(result["height_authority"], "consensus_derived")
        self.assertIs(result["read_only"], True)
        self.assertIs(result["may_mint"], False)
        self.assertIs(result["may_mutate_canonical_state"], False)

        pst_pos = next(fx for fx in self.fixtures if fx["case_id"] == "UAI-CONF-v0.1-PST-POS-001")
        self.assertEqual(
            pst_pos["consensus_view"]["height_authority"], "consensus_derived"
        )
        pe = pst_pos["expected"]["result"]["protected_economics"]
        for key, value in PROTECTED_ECONOMICS.items():
            self.assertEqual(pe[key], value)

    def test_protected_economics_unchanged_in_docs(self) -> None:
        for rel in (
            "docs/universal_access_conformance_plan_v0.1.md",
            "docs/universal_access_interface_v0.1.md",
        ):
            text = (REPO_ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("28,000,000 L28", text)
            self.assertIn("11,130,000 L28", text)
            self.assertIn("2,824,584 L28", text)
            self.assertIn("500,000 L28", text)
            self.assertIn("2,324,584 L28", text)
            self.assertIn("L28 Protocol v1.0.0", text)
            self.assertIn("Coinbase is the only issuance", text)
            self.assertIn("consensus-derived", text)
            self.assertIn("no authority", text)

    def test_safety_scan_no_secrets_paths_or_env_timestamps(self) -> None:
        for path in self.paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("/Users/", text)
            self.assertNotIn("BEGIN PRIVATE", text)
            self.assertNotIn("os.environ", text)
            self.assertNotIn("seed_phrase", text)
            self.assertNotIn("mnemonic", text)
            self.assertIsNone(re.search(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T", text))
            if "BAL-FCL-002" not in path.name:
                self.assertNotIn('"private_key"', text)

    def test_no_runtime_activation_imports_in_this_module(self) -> None:
        src = Path(__file__).read_text(encoding="utf-8")
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

    def test_foundation81_artifacts_untouched(self) -> None:
        # Existing F81 fixture/test paths must still exist and not be in this candidate's dirty set.
        self.assertTrue((FIXTURE_ROOT / "envelope").is_dir())
        self.assertTrue((FIXTURE_ROOT / "discover_capabilities").is_dir())
        self.assertTrue(
            (REPO_ROOT / "tests" / "test_universal_access_envelope_capability_fixtures.py").is_file()
        )


if __name__ == "__main__":
    unittest.main()
