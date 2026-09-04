# SPDX-License-Identifier: Apache-2.0

import ast
import copy
import dataclasses
import json
from pathlib import Path

import pytest

from coin.disposable_testnet_identity import PROTECTED_ECONOMIC_FACTS
from coin.disposable_testnet_m2 import mark_tip_unavailable
from coin.disposable_testnet_runtime_boundary import (
    DisposableRuntimeBoundaryError,
    describe_process_hook_boundary,
    materialize_genesis_artifact_bytes,
    prepare_runtime_boundary,
    validate_runtime_binding,
)
from coin.node_role_model import CoreNodeRoleModel
from tests.disposable_testnet_state_fs_helper import (
    DisposableTestStateSandbox,
)


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "coin/disposable_testnet_runtime_boundary.py"
HELPER = ROOT / "tests/disposable_testnet_state_fs_helper.py"
CONTRACT = ROOT / "docs/l28_disposable_testnet_runtime_boundary_v0.1.json"


def valid_config(network_id="L28-DISPOSABLE-LAB001"):
    tag_suffix = network_id.rsplit("-", 1)[-1].lower()

    return {
        "profile": "l28-disposable-testnet-m1-binding/v0.1",
        "protocol_version": "1.0.0",
        "network_scope": "DISPOSABLE_TEST_ONLY",
        "network_id": network_id,
        "data_dir_tag": "l28-disposable-testnet:" + tag_suffix,
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
    with pytest.raises(DisposableRuntimeBoundaryError) as exc:
        call()
    assert exc.value.code == code


def test_runtime_boundary_consumes_m1_and_m2():
    binding, tip = prepare_runtime_boundary(
        valid_config(),
        acknowledge_test_only=True,
    )

    assert binding.lifecycle_state == "DISPOSABLE_TEST_READY"
    assert binding.tip_height == 0
    assert binding.issued_supply == 0
    assert binding.runtime_authorized is False
    assert binding.process_start_authorized is False
    assert binding.filesystem_mutation_authorized is False
    assert binding.network_authorized is False
    assert binding.socket_authorized is False
    assert binding.signing_authorized is False
    assert binding.mining_authorized is False
    assert binding.broadcast_authorized is False
    assert binding.settlement_authorized is False
    assert validate_runtime_binding(binding, tip) is True


def test_missing_test_only_acknowledgement_fails_closed():
    with pytest.raises(DisposableRuntimeBoundaryError) as exc:
        prepare_runtime_boundary(
            valid_config(),
            acknowledge_test_only=False,
        )

    assert exc.value.code.startswith(
        "m2_preparation_invalid:"
    )


def test_invalid_historical_supply_fails_closed():
    config = valid_config()
    config["genesis"]["initial_issued_supply"] = 2_824_584

    with pytest.raises(DisposableRuntimeBoundaryError) as exc:
        prepare_runtime_boundary(
            config,
            acknowledge_test_only=True,
        )

    assert exc.value.code.startswith(
        "m2_preparation_invalid:"
    )


def test_cross_network_bindings_are_distinct():
    a, _ = prepare_runtime_boundary(
        valid_config("L28-DISPOSABLE-LAB001"),
        acknowledge_test_only=True,
    )

    b, _ = prepare_runtime_boundary(
        valid_config("L28-DISPOSABLE-LAB002"),
        acknowledge_test_only=True,
    )

    assert a.network_id != b.network_id
    assert a.genesis_hash != b.genesis_hash
    assert a.config_hash != b.config_hash


@pytest.mark.parametrize(
    "field",
    [
        "network_id",
        "genesis_hash",
        "config_hash",
    ],
)
def test_identity_mismatch_fails_closed(field):
    binding, tip = prepare_runtime_boundary(
        valid_config(),
        acknowledge_test_only=True,
    )

    changed = dataclasses.replace(
        binding,
        **{field: getattr(binding, field) + "-MISMATCH"},
    )

    assert_code(
        lambda: validate_runtime_binding(changed, tip),
        "runtime_binding_identity_mismatch",
    )


def test_stale_tip_binding_fails_closed():
    binding, tip = prepare_runtime_boundary(
        valid_config(),
        acknowledge_test_only=True,
    )

    advanced = tip.propose_advance(
        expected_current_height=0,
        next_height=1,
    )

    assert_code(
        lambda: validate_runtime_binding(binding, advanced),
        "stale_tip_binding",
    )


def test_unavailable_tip_fails_closed():
    binding, tip = prepare_runtime_boundary(
        valid_config(),
        acknowledge_test_only=True,
    )

    unavailable = mark_tip_unavailable(tip)

    assert_code(
        lambda: validate_runtime_binding(
            binding,
            unavailable,
        ),
        "tip_unavailable",
    )


def test_activation_authority_mutation_fails_closed():
    binding, tip = prepare_runtime_boundary(
        valid_config(),
        acknowledge_test_only=True,
    )

    changed = dataclasses.replace(
        binding,
        runtime_authorized=True,
    )

    assert_code(
        lambda: validate_runtime_binding(changed, tip),
        "activation_authority_invalid",
    )


def test_genesis_artifact_is_deterministic_bytes_only():
    binding, tip = prepare_runtime_boundary(
        valid_config(),
        acknowledge_test_only=True,
    )

    one = materialize_genesis_artifact_bytes(binding, tip)
    two = materialize_genesis_artifact_bytes(binding, tip)

    assert one == two
    assert type(one.payload) is bytes
    assert len(one.payload_sha256) == 64
    assert one.bytes_only is True
    assert one.file_written is False
    assert one.runtime_authorized is False

    decoded = json.loads(one.payload.decode("utf-8"))

    assert decoded["network_id"] == binding.network_id
    assert decoded["genesis_hash"] == binding.genesis_hash
    assert decoded["config_hash"] == binding.config_hash
    assert decoded["initial_tip_height"] == 0
    assert decoded["initial_issued_supply"] == 0
    assert decoded["historical_checkpoint_imported"] is False
    assert decoded["historical_balances_loaded"] is False
    assert decoded["runtime_authorized"] is False
    assert decoded["testnet_start_authorized"] is False


def test_process_hooks_are_interface_only():
    boundary = describe_process_hook_boundary()

    assert boundary["interface_only"] is True
    assert boundary["start_hook_defined"] is True
    assert boundary["stop_hook_defined"] is True
    assert boundary["hook_invocation_authorized"] is False
    assert boundary["process_control_authorized"] is False
    assert boundary["runtime_authorized"] is False
    assert boundary["network_authorized"] is False


def test_reserved_running_states_remain_unreachable():
    core = CoreNodeRoleModel()

    for state in (
        "CANONICAL_READY_RESERVED",
        "RUNNING_RESERVED",
    ):
        updated, result = core.transition(state)

        assert result.ok is False
        assert result.code == "reserved_state_unreachable"
        assert updated is core


def test_test_sandbox_create_reset_cleanup():
    binding, tip = prepare_runtime_boundary(
        valid_config(),
        acknowledge_test_only=True,
    )

    sandbox = DisposableTestStateSandbox(binding, tip)
    root = sandbox.root

    try:
        state = sandbox.create()

        assert state.exists()
        assert state.parent == root

        marker = json.loads(
            (state / "binding.json").read_text(
                encoding="utf-8"
            )
        )

        assert marker["network_id"] == binding.network_id
        assert marker["genesis_hash"] == binding.genesis_hash
        assert marker["config_hash"] == binding.config_hash
        assert marker["test_only"] is True
        assert marker["runtime_authorized"] is False

        disposable = state / "disposable.tmp"
        disposable.write_text(
            "test-only",
            encoding="utf-8",
        )
        assert disposable.exists()

        reset = sandbox.reset()

        assert reset.exists()
        assert not disposable.exists()
        assert (reset / "binding.json").exists()

    finally:
        sandbox.cleanup()

    assert not root.exists()


def test_test_sandbox_cleanup_is_idempotent():
    binding, tip = prepare_runtime_boundary(
        valid_config(),
        acknowledge_test_only=True,
    )

    sandbox = DisposableTestStateSandbox(binding, tip)
    root = sandbox.root

    sandbox.create()
    sandbox.cleanup()
    sandbox.cleanup()

    assert sandbox.closed is True
    assert not root.exists()


def test_test_sandbox_create_twice_fails_closed():
    binding, tip = prepare_runtime_boundary(
        valid_config(),
        acknowledge_test_only=True,
    )

    sandbox = DisposableTestStateSandbox(binding, tip)

    try:
        sandbox.create()

        with pytest.raises(
            RuntimeError,
            match="sandbox_state_exists",
        ):
            sandbox.create()
    finally:
        sandbox.cleanup()


def test_machine_contract_preserves_activation_blockers():
    contract = json.loads(
        CONTRACT.read_text(encoding="utf-8")
    )

    assert contract["status"] == "OFFLINE_TESTED_BOUNDARY_ONLY"
    assert contract["genesis_artifact"]["materialization"] == "BYTES_ONLY"
    assert contract["process_hooks"]["interface_only"] is True
    assert contract["process_hooks"]["invocation_authorized"] is False

    assert (
        contract["gap_reassessment"]["F37-05"]
        == "PARTIAL_TEST_SANDBOX_ONLY"
    )
    assert (
        contract["gap_reassessment"]["F37-06"]
        == "BLOCKED_RUNTIME"
    )
    assert (
        contract["gap_reassessment"]["F37-13"]
        == "PARTIAL_TEST_SANDBOX_ONLY"
    )

    for field in (
        "runtime_authorized",
        "process_start_authorized",
        "process_control_authorized",
        "production_filesystem_mutation_authorized",
        "network_authorized",
        "socket_authorized",
        "rpc_authorized",
        "p2p_authorized",
        "wallet_creation_authorized",
        "key_generation_authorized",
        "signing_authorized",
        "mining_authorized",
        "broadcast_authorized",
        "testnet_start_authorized",
        "settlement_authorized",
    ):
        assert contract[field] is False


def test_production_boundary_has_no_runtime_or_filesystem_io():
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden_imports = {
        "socket",
        "subprocess",
        "requests",
        "urllib",
        "http",
        "asyncio",
        "os",
        "pathlib",
        "tempfile",
        "shutil",
        "time",
        "random",
        "secrets",
    }

    forbidden_calls = {
        "open",
        "mkdir",
        "write_text",
        "write_bytes",
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
    assert forbidden_calls.isdisjoint(called)


def test_test_helper_is_explicitly_test_only():
    source = HELPER.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(
                alias.name.split(".")[0]
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    assert "socket" not in imports
    assert "subprocess" not in imports
    assert "requests" not in imports
    assert "secrets" not in imports
    assert "tempfile" in imports
    assert "shutil" in imports


def test_production_coin_modules_do_not_import_test_helper():
    forbidden_module = "tests.disposable_testnet_state_fs_helper"

    for path in sorted((ROOT / "coin").glob("*.py")):
        tree = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(
                    alias.name != forbidden_module
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                assert node.module != forbidden_module
