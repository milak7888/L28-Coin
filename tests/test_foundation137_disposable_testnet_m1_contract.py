# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "docs/l28_disposable_testnet_m1_contract_v0.1.json"
DOC = ROOT / "docs/foundation137_disposable_testnet_m1_contract_v0.1.md"


def load_profile():
    return json.loads(PROFILE.read_text(encoding="utf-8"))


def test_m1_contract_is_nonactivating():
    p = load_profile()
    assert p["status"] == "SPECIFICATION_ONLY"
    assert p["protocol_version"] == "1.0.0"
    assert p["network_scope"] == "DISPOSABLE_TEST_ONLY"
    assert p["runtime_authorized"] is False
    assert p["network_authorized"] is False
    assert p["signing_authorized"] is False
    assert p["settlement_authorized"] is False
    assert p["mining_authorized"] is False
    assert p["testnet_start_authorized"] is False


def test_m1_contract_separates_main_and_history():
    p = load_profile()
    assert p["network_id_required"] is True
    assert p["network_id_must_differ_from_main"] is True
    assert p["genesis_binding_required"] is True
    assert p["genesis_hash_required"] is True
    assert p["ephemeral_data_dir_required"] is True
    assert p["historical_checkpoint_import_allowed"] is False
    assert p["historical_balances_live_genesis_allowed"] is False
    assert p["main_identity_reuse_allowed"] is False
    assert p["production_keys_allowed"] is False


def test_protected_economics_are_exact():
    e = load_profile()["protected_economic_facts"]
    assert e["hard_cap"] == 28000000
    assert e["emission_ceiling"] == 11130000
    assert e["historically_mined"] == 2824584
    assert e["treasury_locked"] == 500000
    assert e["circulating_snapshot"] == 2324584
    assert e["halving_interval"] == 210000
    assert e["reward_sequence"] == [28, 14, 7, 3, 1, 0]
    assert e["historical_mined_through_entry"] == 100877
    assert e["next_canonical_height"] == 100878


def test_foundation137_does_not_claim_readiness():
    text = DOC.read_text(encoding="utf-8")
    assert "does not close F37-12" in text
    assert "F37-12 remains BLOCKED" in text
    assert "separate explicit operator authorization" in text
