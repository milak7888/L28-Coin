import hashlib
import json
from pathlib import Path

from coin import uaii_reference_core as core
from coin.uaii_json import canon_uaii

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/uaii_canonical_preservation_manifest_v0.1.json"

OPS = [
    "discover_capabilities",
    "get_protocol_status",
    "get_balance",
    "create_quote",
    "create_unsigned_payment_request",
    "validate_payment",
    "get_payment_receipt",
    "verify_signed_receipt",
]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))

def test_manifest_identity_and_authority():
    m = load()
    assert m["interface_profile"] == "l28-universal-ai-access-interface/v0.1"
    assert m["protocol_version"] == "1.0.0"
    assert m["canonical_operations"] == OPS
    assert m["authority"]["validator"] == "coin.tx_validation.validate_transaction"
    assert m["authority"]["execution_authorized"] is False
    assert m["authority"]["signing_authorized"] is False
    assert m["authority"]["spend_authorized"] is False
    assert m["authority"]["adapters_activated"] is False

def test_locked_canonical_artifacts_are_unchanged():
    for item in load()["canonical_artifacts"]:
        path = ROOT / item["path"]
        assert path.is_file()
        assert digest(path) == item["sha256"]

def test_fixture_inventory_and_bytes_are_unchanged():
    m = load()
    actual = sorted(
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / m["fixture_root"]).rglob("*.json")
    )
    expected = [item["path"] for item in m["fixtures"]]
    assert actual == expected
    assert len(actual) == m["fixture_count"]
    for item in m["fixtures"]:
        assert digest(ROOT / item["path"]) == item["sha256"]

def test_fixture_files_remain_json_objects():
    for item in load()["fixtures"]:
        value = json.loads((ROOT / item["path"]).read_text(encoding="utf-8"))
        assert isinstance(value, dict)

def test_exact_order_serializer_remains_exact_order():
    assert canon_uaii({"z": 1, "a": 2}) == b'{"z":1,"a":2}'

def test_reference_core_remains_bound_to_canonical_profile():
    assert core.INTERFACE_PROFILE == "l28-universal-ai-access-interface/v0.1"
    assert list(core.OPERATIONS) == OPS
    assert core.adapters_activated is False
    assert core.runtime_activated is False
    assert core.signing_authorized is False
    assert core.settlement_authorized is False
