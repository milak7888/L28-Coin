# SPDX-License-Identifier: Apache-2.0

import ast
import copy
import dataclasses
import json
from pathlib import Path

import pytest

from coin.disposable_testnet_identity import PROTECTED_ECONOMIC_FACTS
from coin.disposable_testnet_m2 import (
    DisposableM2Error,
    build_data_dir_contract,
    build_local_tip_authority,
    build_m2_offline_bundle,
    build_wallet_isolation_contract,
    mark_tip_unavailable,
    plan_disposable_state_action,
    prepare_disposable_core,
)
from coin.node_role_model import CoreNodeRoleModel


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "coin/disposable_testnet_m2.py"
CONTRACT = ROOT / "docs/l28_disposable_testnet_m2_contract_v0.1.json"


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
            "protected_economic_facts": copy.deepcopy(
                PROTECTED_ECONOMIC_FACTS
            ),
        },
        "key_policy": {
            "allow_production_keys": False,
            "allow_creator_private_material": False,
            "allow_external_wallet_paths": False,
        },
        "acknowledge_disposable_test_only": True,
    }


def assert_code(call, code):
    with pytest.raises(DisposableM2Error) as exc:
        call()
    assert exc.value.code == code


def test_core_preparation_consumes_m1_binding():
    prep = prepare_disposable_core(
        valid_config(),
        acknowledge_test_only=True,
    )
    assert prep.lifecycle_state == "DISPOSABLE_TEST_READY"
    assert prep.issuance_acknowledged is True
    assert prep.initial_tip_height == 0
    assert prep.initial_issued_supply == 0
    assert prep.runtime_authorized is False
    assert prep.process_start_authorized is False
    assert prep.network_authorized is False
    assert prep.signing_authorized is False
    assert prep.mining_authorized is False
    assert prep.settlement_authorized is False


def test_separate_m2_acknowledgement_is_required():
    assert_code(
        lambda: prepare_disposable_core(
            valid_config(),
            acknowledge_test_only=False,
        ),
        "issuance_acknowledgement_required",
    )


def test_invalid_m1_binding_fails_closed():
    c = valid_config()
    c["genesis"]["initial_issued_supply"] = 2_824_584
    with pytest.raises(DisposableM2Error) as exc:
        prepare_disposable_core(
            c,
            acknowledge_test_only=True,
        )
    assert exc.value.code.startswith("m1_binding_invalid:")


def test_stopped_core_remains_terminal():
    stopped = CoreNodeRoleModel._from_valid_state("STOPPED")
    updated, result = stopped.transition(
        "DISPOSABLE_TEST_READY"
    )
    assert result.ok is False
    assert result.code == "transition_not_allowed"
    assert updated is stopped


def test_reserved_core_runtime_states_remain_unreachable():
    current = CoreNodeRoleModel()
    for state in (
        "CANONICAL_READY_RESERVED",
        "RUNNING_RESERVED",
    ):
        updated, result = current.transition(state)
        assert result.ok is False
        assert result.code == "reserved_state_unreachable"
        assert updated is current


def test_local_tip_starts_at_zero_and_is_immutable():
    prep = prepare_disposable_core(
        valid_config(),
        acknowledge_test_only=True,
    )
    tip = build_local_tip_authority(prep)

    assert tip.read_height() == 0
    assert tip.network_consensus_authority is False
    assert tip.main_network_authority is False

    advanced = tip.propose_advance(
        expected_current_height=0,
        next_height=1,
    )

    assert tip.height == 0
    assert advanced.height == 1

    with pytest.raises(dataclasses.FrozenInstanceError):
        tip.height = 99


@pytest.mark.parametrize(
    "expected,next_height,code",
    [
        (1, 1, "tip_height_mismatch"),
        (0, 2, "tip_advance_invalid"),
        (0, -1, "tip_advance_invalid"),
        (False, 1, "expected_height_invalid"),
        (0, True, "next_height_invalid"),
    ],
)
def test_tip_updates_fail_closed(expected, next_height, code):
    prep = prepare_disposable_core(
        valid_config(),
        acknowledge_test_only=True,
    )
    tip = build_local_tip_authority(prep)

    assert_code(
        lambda: tip.propose_advance(
            expected_current_height=expected,
            next_height=next_height,
        ),
        code,
    )


def test_unavailable_tip_fails_closed():
    prep = prepare_disposable_core(
        valid_config(),
        acknowledge_test_only=True,
    )
    tip = mark_tip_unavailable(
        build_local_tip_authority(prep)
    )

    assert_code(
        lambda: tip.read_height(),
        "tip_unavailable",
    )
    assert_code(
        lambda: tip.propose_advance(
            expected_current_height=0,
            next_height=1,
        ),
        "tip_unavailable",
    )


def test_wallet_contract_is_isolation_only():
    prep = prepare_disposable_core(
        valid_config(),
        acknowledge_test_only=True,
    )
    wallet = build_wallet_isolation_contract(prep)

    assert wallet.ephemeral_keys_required is True
    assert wallet.key_generation_authorized is False
    assert wallet.persistent_key_storage_authorized is False
    assert wallet.production_key_loading_authorized is False
    assert wallet.creator_private_material_authorized is False
    assert wallet.external_wallet_paths_authorized is False
    assert wallet.signing_authorized is False


def test_data_dir_contract_has_no_filesystem_authority():
    prep = prepare_disposable_core(
        valid_config(),
        acknowledge_test_only=True,
    )
    contract = build_data_dir_contract(prep)

    assert contract.disposable_only is True
    assert contract.filesystem_access_authorized is False
    assert contract.create_authorized is False
    assert contract.reset_authorized is False
    assert contract.cleanup_authorized is False
    assert contract.persistence_authorized is False


@pytest.mark.parametrize("action", ["stop", "reset", "cleanup"])
def test_state_actions_are_plans_only(action):
    prep = prepare_disposable_core(
        valid_config(),
        acknowledge_test_only=True,
    )
    plan = plan_disposable_state_action(prep, action)

    assert plan["action"] == action
    assert plan["plan_only"] is True
    assert plan["execution_authorized"] is False
    assert plan["filesystem_mutation_authorized"] is False
    assert plan["process_control_authorized"] is False
    assert plan["network_authorized"] is False


def test_unknown_state_action_fails_closed():
    prep = prepare_disposable_core(
        valid_config(),
        acknowledge_test_only=True,
    )
    assert_code(
        lambda: plan_disposable_state_action(
            prep,
            "start",
        ),
        "state_action_invalid",
    )


def test_full_offline_bundle_has_no_activation_authority():
    bundle = build_m2_offline_bundle(
        valid_config(),
        acknowledge_test_only=True,
    )

    for field in (
        "runtime_authorized",
        "process_start_authorized",
        "network_authorized",
        "socket_authorized",
        "signing_authorized",
        "mining_authorized",
        "broadcast_authorized",
        "settlement_authorized",
    ):
        assert bundle[field] is False


def test_machine_contract_preserves_runtime_blockers():
    contract = json.loads(
        CONTRACT.read_text(encoding="utf-8")
    )

    assert contract["status"] == "OFFLINE_MODEL_ONLY"
    assert contract["stopped_state_remains_terminal"] is True
    assert contract["gap_reassessment"]["F37-02"] == "PARTIAL"
    assert contract["gap_reassessment"]["F37-05"] == "PARTIAL"
    assert contract["gap_reassessment"]["F37-06"] == "BLOCKED_RUNTIME"
    assert contract["gap_reassessment"]["F37-09"] == "PARTIAL"
    assert contract["gap_reassessment"]["F37-13"] == "PARTIAL"
    assert contract["testnet_start_authorized"] is False


def test_module_has_no_runtime_io_or_secret_generation():
    tree = ast.parse(
        MODULE.read_text(encoding="utf-8")
    )

    forbidden_imports = {
        "socket",
        "subprocess",
        "requests",
        "urllib",
        "http",
        "asyncio",
        "os",
        "pathlib",
        "time",
        "random",
        "secrets",
    }

    imported = set()
    called = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(
                alias.name.split(".")[0]
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)

    assert forbidden_imports.isdisjoint(imported)

    forbidden_calls = {
        "open",
        "mkdir",
        "unlink",
        "rmdir",
        "remove",
        "connect",
        "bind",
        "listen",
        "send",
        "sendall",
        "Popen",
        "run",
        "system",
    }

    assert forbidden_calls.isdisjoint(called)
