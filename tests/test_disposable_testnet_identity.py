# SPDX-License-Identifier: Apache-2.0

import ast
import copy
import json
from pathlib import Path

import pytest

from coin.disposable_testnet_identity import (
    PROTECTED_ECONOMIC_FACTS,
    DisposableTestnetConfigError,
    validate_and_bind_disposable_testnet_config,
)

ROOT = Path(__file__).resolve().parents[1]


def valid_config(network_id="L28-DISPOSABLE-LAB001"):
    return {
        "profile": "l28-disposable-testnet-m1-binding/v0.1",
        "protocol_version": "1.0.0",
        "network_scope": "DISPOSABLE_TEST_ONLY",
        "network_id": network_id,
        "data_dir_tag": "l28-disposable-testnet:lab001",
        "genesis": {
            "profile": "l28-disposable-genesis/v0.1",
            "network_id": network_id,
            "initial_height": 0,
            "initial_issued_supply": 0,
            "historical_checkpoint_imported": False,
            "historical_balances_loaded": False,
            "protected_economic_facts": copy.deepcopy(PROTECTED_ECONOMIC_FACTS),
        },
        "key_policy": {
            "allow_production_keys": False,
            "allow_creator_private_material": False,
            "allow_external_wallet_paths": False,
        },
        "acknowledge_disposable_test_only": True,
    }


def assert_code(config, code):
    with pytest.raises(DisposableTestnetConfigError) as exc:
        validate_and_bind_disposable_testnet_config(config)
    assert exc.value.code == code


def test_positive_binding_is_deterministic():
    config = valid_config()
    one = validate_and_bind_disposable_testnet_config(config)
    two = validate_and_bind_disposable_testnet_config(copy.deepcopy(config))
    assert one == two
    assert len(one["genesis_hash"]) == 64
    assert len(one["config_hash"]) == 64
    assert one["runtime_authorized"] is False
    assert one["network_authorized"] is False
    assert one["testnet_start_authorized"] is False
    assert one["signing_authorized"] is False
    assert one["mining_authorized"] is False
    assert one["broadcast_authorized"] is False
    assert one["settlement_authorized"] is False


def test_cross_network_binding_changes_hashes():
    a = valid_config("L28-DISPOSABLE-LAB001")
    b = valid_config("L28-DISPOSABLE-LAB002")
    rb = b["data_dir_tag"] = "l28-disposable-testnet:lab002"
    assert rb == "l28-disposable-testnet:lab002"
    one = validate_and_bind_disposable_testnet_config(a)
    two = validate_and_bind_disposable_testnet_config(b)
    assert one["genesis_hash"] != two["genesis_hash"]
    assert one["config_hash"] != two["config_hash"]


@pytest.mark.parametrize("network_id", ["MAIN", "MAINNET", "L28-MAIN"])
def test_main_identity_is_rejected(network_id):
    c = valid_config()
    c["network_id"] = network_id
    c["genesis"]["network_id"] = network_id
    assert_code(c, "main_identity_forbidden")


def test_outer_and_genesis_network_mismatch_fails_closed():
    c = valid_config()
    c["genesis"]["network_id"] = "L28-DISPOSABLE-OTHER01"
    assert_code(c, "network_binding_mismatch")


@pytest.mark.parametrize(
    "field,code",
    [
        ("historical_checkpoint_imported", "historical_checkpoint_import_forbidden"),
        ("historical_balances_loaded", "historical_balances_forbidden"),
    ],
)
def test_historical_state_import_is_rejected(field, code):
    c = valid_config()
    c["genesis"][field] = True
    assert_code(c, code)


def test_nonzero_initial_supply_is_rejected():
    c = valid_config()
    c["genesis"]["initial_issued_supply"] = 2_824_584
    assert_code(c, "historical_supply_reuse_forbidden")


def test_nonzero_initial_height_is_rejected():
    c = valid_config()
    c["genesis"]["initial_height"] = 100_878
    assert_code(c, "genesis_height_invalid")


def test_economic_mutation_is_rejected():
    c = valid_config()
    c["genesis"]["protected_economic_facts"]["hard_cap"] = 28_000_001
    assert_code(c, "economic_facts_mismatch")


@pytest.mark.parametrize(
    "field",
    [
        "allow_production_keys",
        "allow_creator_private_material",
        "allow_external_wallet_paths",
    ],
)
def test_production_key_references_are_rejected(field):
    c = valid_config()
    c["key_policy"][field] = True
    assert_code(c, "production_key_reference_forbidden")


@pytest.mark.parametrize(
    "tag",
    [
        "main",
        "../lab001",
        "l28-disposable-testnet:../lab001",
        "l28-disposable-testnet:/tmp/lab001",
    ],
)
def test_bad_data_dir_tags_are_rejected(tag):
    c = valid_config()
    c["data_dir_tag"] = tag
    assert_code(c, "data_dir_tag_invalid")


def test_acknowledgement_is_required():
    c = valid_config()
    c["acknowledge_disposable_test_only"] = False
    assert_code(c, "test_only_acknowledgement_required")


def test_unknown_fields_fail_closed():
    c = valid_config()
    c["runtime"] = True
    assert_code(c, "schema_invalid")


def test_f137_protected_economic_facts_match_exactly():
    contract = json.loads(
        (ROOT / "docs/l28_disposable_testnet_m1_contract_v0.1.json")
        .read_text(encoding="utf-8")
    )
    assert contract["protected_economic_facts"] == PROTECTED_ECONOMIC_FACTS


def test_module_has_no_runtime_or_secret_io_imports():
    path = ROOT / "coin/disposable_testnet_identity.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden = {
        "socket",
        "subprocess",
        "requests",
        "urllib",
        "http",
        "asyncio",
        "time",
        "random",
        "secrets",
        "pathlib",
        "os",
    }
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert forbidden.isdisjoint(imported)
