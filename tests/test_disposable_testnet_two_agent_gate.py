# SPDX-License-Identifier: Apache-2.0

import ast
import copy
import dataclasses
import json
from pathlib import Path

import pytest

from coin.disposable_testnet_identity import PROTECTED_ECONOMIC_FACTS
from coin.disposable_testnet_p2p_conformance import build_offline_frame
from coin.disposable_testnet_runtime_boundary import prepare_runtime_boundary
from coin.disposable_testnet_two_agent_gate import (
    AGENT_A,
    AGENT_B,
    LOOPBACK_HOST,
    READINESS,
    AgentEndpointSpec,
    TwoAgentSecurityGateError,
    build_authorization_readiness_report,
    build_fixture_identity_evidence,
    build_two_agent_experiment_plan,
    evaluate_offline_transcript,
    evaluate_peer_tip_for_experiment,
    plan_experiment_lifecycle,
    plan_offline_session,
    plan_propagation_trial,
    validate_fixture_identity_evidence,
    validate_two_agent_experiment_plan,
)


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "coin/disposable_testnet_two_agent_gate.py"
CONTRACT = ROOT / "docs/l28_isolated_two_agent_transport_authorization_gate_v0.1.json"
FIXTURES = ROOT / "tests/fixtures/foundation142_two_agent_security_cases_v0.1.json"


def valid_config(network_id="L28-DISPOSABLE-LAB001"):
    suffix = network_id.rsplit("-", 1)[-1].lower()

    return {
        "profile": "l28-disposable-testnet-m1-binding/v0.1",
        "protocol_version": "1.0.0",
        "network_scope": "DISPOSABLE_TEST_ONLY",
        "network_id": network_id,
        "data_dir_tag": "l28-disposable-testnet:" + suffix,
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


def runtime_context(network_id="L28-DISPOSABLE-LAB001"):
    return prepare_runtime_boundary(
        valid_config(network_id),
        acknowledge_test_only=True,
    )


def experiment_context(network_id="L28-DISPOSABLE-LAB001"):
    binding, tip = runtime_context(network_id)
    plan = build_two_agent_experiment_plan(
        binding,
        tip,
    )
    return binding, tip, plan


def frame_for(
    binding,
    tip,
    *,
    nonce,
    message_type="HELLO",
    payload=None,
):
    if payload is None:
        payload = {
            "fixture": True,
            "evidence_only": True,
        }

    return build_offline_frame(
        binding,
        tip,
        message_type=message_type,
        peer_id="peer-fixture-01",
        nonce=nonce,
        timestamp=1000,
        expiry=1100,
        payload=payload,
    )


def assert_gate_code(call, code):
    with pytest.raises(TwoAgentSecurityGateError) as exc:
        call()
    assert exc.value.code == code


def test_plan_is_exact_two_agent_loopback_and_not_authorized():
    binding, tip, plan = experiment_context()

    assert plan.readiness == READINESS
    assert plan.max_agents == 2
    assert len(plan.agents) == 2
    assert {a.agent_id for a in plan.agents} == {
        AGENT_A,
        AGENT_B,
    }
    assert all(
        a.host == LOOPBACK_HOST
        for a in plan.agents
    )
    assert plan.writer_agent_id == AGENT_A
    assert plan.loopback_only is True

    for field in (
        "network_authorized",
        "socket_authorized",
        "listen_authorized",
        "connect_authorized",
        "process_start_authorized",
        "p2p_runtime_authorized",
        "rpc_authorized",
        "ledger_mutation_authorized",
        "canonical_height_override_authorized",
        "wallet_creation_authorized",
        "key_generation_authorized",
        "signing_authorized",
        "mining_authorized",
        "broadcast_authorized",
        "real_value_authorized",
        "historical_state_import_authorized",
        "testnet_start_authorized",
        "settlement_authorized",
    ):
        assert getattr(plan, field) is False

    assert validate_two_agent_experiment_plan(
        plan,
        binding,
        tip,
    ) is True


@pytest.mark.parametrize(
    "host",
    [
        "0.0.0.0",
        "192.168.1.10",
        "::1",
    ],
)
def test_non_exact_loopback_scope_is_rejected(host):
    binding, tip, plan = experiment_context()

    agents = list(plan.agents)
    agents[1] = dataclasses.replace(
        agents[1],
        host=host,
    )
    changed = dataclasses.replace(
        plan,
        agents=tuple(agents),
    )

    assert_gate_code(
        lambda: validate_two_agent_experiment_plan(
            changed,
            binding,
            tip,
        ),
        "loopback_scope_invalid",
    )


def test_third_agent_is_rejected():
    binding, tip, plan = experiment_context()

    third = AgentEndpointSpec(
        agent_id="agent-c",
        host=LOOPBACK_HOST,
        port=28430,
        role="PEER_EVIDENCE_ONLY",
        designated_single_writer=False,
        peer_evidence_only=True,
    )

    changed = dataclasses.replace(
        plan,
        agents=plan.agents + (third,),
    )

    assert_gate_code(
        lambda: validate_two_agent_experiment_plan(
            changed,
            binding,
            tip,
        ),
        "topology_agent_count_invalid",
    )


def test_port_collision_is_rejected():
    binding, tip, plan = experiment_context()

    agents = list(plan.agents)
    agents[1] = dataclasses.replace(
        agents[1],
        port=agents[0].port,
    )

    changed = dataclasses.replace(
        plan,
        agents=tuple(agents),
    )

    assert_gate_code(
        lambda: validate_two_agent_experiment_plan(
            changed,
            binding,
            tip,
        ),
        "topology_port_collision",
    )


def test_public_fixture_identity_is_deterministic_and_nonsecret():
    one = build_fixture_identity_evidence(
        AGENT_A
    )
    two = build_fixture_identity_evidence(
        AGENT_A
    )

    assert one == two
    assert one["secret_based"] is False
    assert one["production_authentication"] is False
    assert len(one["public_fixture_digest"]) == 64

    assert validate_fixture_identity_evidence(
        one,
        expected_agent_id=AGENT_A,
    ) is True


def test_fixture_identity_mismatch_is_rejected():
    evidence = build_fixture_identity_evidence(
        AGENT_A
    )

    assert_gate_code(
        lambda: validate_fixture_identity_evidence(
            evidence,
            expected_agent_id=AGENT_B,
        ),
        "fixture_identity_invalid",
    )


def test_session_plan_is_deterministic_and_nonexecuting():
    binding, tip, plan = experiment_context()

    one = plan_offline_session(
        plan,
        binding,
        tip,
        initiator=AGENT_B,
        responder=AGENT_A,
        reconnect_index=0,
    )

    two = plan_offline_session(
        plan,
        binding,
        tip,
        initiator=AGENT_B,
        responder=AGENT_A,
        reconnect_index=0,
    )

    assert one == two
    assert len(one.session_id) == 64
    assert one.network_authorized is False
    assert one.socket_authorized is False
    assert one.execute_authorized is False
    assert one.production_authentication is False


def test_reconnect_limit_is_enforced():
    binding, tip, plan = experiment_context()

    assert_gate_code(
        lambda: plan_offline_session(
            plan,
            binding,
            tip,
            initiator=AGENT_B,
            responder=AGENT_A,
            reconnect_index=2,
        ),
        "reconnect_limit_exceeded",
    )


def test_lifecycle_plan_is_defined_but_not_executable():
    binding, tip, plan = experiment_context()

    lifecycle = plan_experiment_lifecycle(
        plan
    )

    assert lifecycle["reset_after_shutdown_required"] is True
    assert lifecycle["reset_scope"] == "DISPOSABLE_TEST_STATE_ONLY"
    assert lifecycle["execute_authorized"] is False
    assert lifecycle["process_start_authorized"] is False
    assert lifecycle["network_authorized"] is False
    assert lifecycle["socket_authorized"] is False
    assert lifecycle["testnet_start_authorized"] is False


def test_propagation_trial_has_success_and_abort_criteria_only():
    binding, tip, plan = experiment_context()

    trial = plan_propagation_trial(plan)

    assert "HELLO_BIDIRECTIONAL" in trial["scenarios"]
    assert "WRONG_NETWORK_ABORT" in trial["scenarios"]
    assert "MESSAGE_REPLAY_ABORT" in trial["scenarios"]
    assert trial["abort_on_first_security_failure"] is True
    assert trial["propagation_execution_authorized"] is False
    assert trial["network_authorized"] is False
    assert trial["confirmation_policy_defined"] is False
    assert trial["reorg_policy_defined"] is False


def test_offline_transcript_accepts_valid_bounded_frames():
    binding, tip, plan = experiment_context()

    session = plan_offline_session(
        plan,
        binding,
        tip,
        initiator=AGENT_B,
        responder=AGENT_A,
    )

    frames = [
        frame_for(
            binding,
            tip,
            nonce="nonce-f142-001",
            message_type="HELLO",
        ),
        frame_for(
            binding,
            tip,
            nonce="nonce-f142-002",
            message_type="TIP_EVIDENCE",
            payload={
                "height": 0,
                "evidence_only": True,
            },
        ),
    ]

    result = evaluate_offline_transcript(
        session,
        plan,
        binding,
        tip,
        frames,
        now_ts=1000,
    )

    assert result.ok is True
    assert result.code == "offline_transcript_admitted"
    assert result.admitted_count == 2
    assert result.rejected_index is None
    assert result.disconnect_planned is False
    assert result.network_activity_performed is False
    assert result.ledger_mutated is False
    assert result.local_tip_changed is False
    assert result.settlement_performed is False
    assert tip.read_height() == 0


def test_session_message_limit_is_enforced_before_admission():
    binding, tip, plan = experiment_context()

    session = plan_offline_session(
        plan,
        binding,
        tip,
        initiator=AGENT_B,
        responder=AGENT_A,
    )

    frame = frame_for(
        binding,
        tip,
        nonce="nonce-f142-limit",
    )

    frames = [
        frame
        for _ in range(
            plan.limits.max_messages_per_session + 1
        )
    ]

    result = evaluate_offline_transcript(
        session,
        plan,
        binding,
        tip,
        frames,
        now_ts=1000,
    )

    assert result.ok is False
    assert result.code == "session_message_limit_exceeded"
    assert result.admitted_count == 0
    assert result.disconnect_planned is True


def test_experiment_payload_limit_is_enforced():
    binding, tip, plan = experiment_context()

    session = plan_offline_session(
        plan,
        binding,
        tip,
        initiator=AGENT_B,
        responder=AGENT_A,
    )

    frame = frame_for(
        binding,
        tip,
        nonce="nonce-f142-payload",
        payload={
            "blob": "x" * 2200,
        },
    )

    result = evaluate_offline_transcript(
        session,
        plan,
        binding,
        tip,
        [frame],
        now_ts=1000,
    )

    assert result.ok is False
    assert result.code == "experiment_payload_too_large"
    assert result.disconnect_planned is True
    assert result.network_activity_performed is False


def test_replay_state_persists_across_reconnect():
    binding, tip, plan = experiment_context()

    first_session = plan_offline_session(
        plan,
        binding,
        tip,
        initiator=AGENT_B,
        responder=AGENT_A,
        reconnect_index=0,
    )

    frame = frame_for(
        binding,
        tip,
        nonce="nonce-f142-replay",
    )

    first = evaluate_offline_transcript(
        first_session,
        plan,
        binding,
        tip,
        [frame],
        now_ts=1000,
    )

    assert first.ok is True

    second_session = plan_offline_session(
        plan,
        binding,
        tip,
        initiator=AGENT_B,
        responder=AGENT_A,
        reconnect_index=1,
    )

    second = evaluate_offline_transcript(
        second_session,
        plan,
        binding,
        tip,
        [frame],
        now_ts=1000,
        prior_seen_message_ids=set(
            first.seen_message_ids
        ),
        prior_seen_nonce_keys=set(
            first.seen_nonce_keys
        ),
    )

    assert second.ok is False
    assert second.code == "message_replayed"
    assert second.disconnect_planned is True


def test_wrong_network_frame_aborts_offline_transcript():
    binding_a, tip_a, plan_a = experiment_context(
        "L28-DISPOSABLE-LAB001"
    )
    binding_b, tip_b, plan_b = experiment_context(
        "L28-DISPOSABLE-LAB002"
    )

    frame = frame_for(
        binding_a,
        tip_a,
        nonce="nonce-f142-crossnet",
    )

    session_b = plan_offline_session(
        plan_b,
        binding_b,
        tip_b,
        initiator=AGENT_B,
        responder=AGENT_A,
    )

    result = evaluate_offline_transcript(
        session_b,
        plan_b,
        binding_b,
        tip_b,
        [frame],
        now_ts=1000,
    )

    assert result.ok is False
    assert result.code == "network_id_mismatch"
    assert result.disconnect_planned is True


def test_stale_runtime_binding_blocks_gate():
    binding, tip = runtime_context()

    advanced_tip = tip.propose_advance(
        expected_current_height=0,
        next_height=1,
    )

    with pytest.raises(
        TwoAgentSecurityGateError
    ) as exc:
        build_two_agent_experiment_plan(
            binding,
            advanced_tip,
        )

    assert exc.value.code.startswith(
        "runtime_binding_invalid:"
    )


def test_peer_ahead_sync_remains_core_only_and_plan_only():
    binding, tip, plan = experiment_context()

    result = evaluate_peer_tip_for_experiment(
        plan,
        binding,
        tip,
        peer_height=3,
    )

    assert result["relation"] == "PEER_AHEAD"
    assert result["sync_action"] == "REQUEST_CANDIDATE_RANGE"
    assert result["request_start"] == 1
    assert result["request_end"] == 3
    assert result["single_writer"] == "LOCAL_CORE_ONLY"
    assert result["peer_tip_authoritative"] is False
    assert result["peer_can_mutate_local_tip"] is False
    assert result["peer_can_override_canonical_height"] is False
    assert result["automatic_apply"] is False
    assert result["ledger_mutation_authorized"] is False
    assert result["confirmation_policy_defined"] is False
    assert result["reorg_policy_defined"] is False
    assert tip.read_height() == 0


def test_authorization_readiness_report_requires_separate_authorization():
    binding, tip, plan = experiment_context()

    report = build_authorization_readiness_report(
        plan,
        binding,
        tip,
    )

    assert report["readiness"] == READINESS
    assert report["two_agents_exact"] is True
    assert report["loopback_scope_defined"] is True
    assert report["single_writer_core_only"] is True
    assert report["peer_evidence_only"] is True
    assert report["separate_explicit_operator_authorization_required"] is True
    assert report["production_peer_authentication_defined"] is False
    assert report["trusted_production_time_defined"] is False
    assert report["confirmation_policy_defined"] is False
    assert report["reorg_policy_defined"] is False
    assert report["network_authorized"] is False
    assert report["socket_authorized"] is False
    assert report["p2p_runtime_authorized"] is False
    assert report["testnet_start_authorized"] is False
    assert report["settlement_authorized"] is False


def test_machine_gate_preserves_all_activation_blocks():
    contract = json.loads(
        CONTRACT.read_text(encoding="utf-8")
    )

    assert (
        contract["readiness"]
        == "READY_FOR_EXPLICIT_ISOLATED_TWO_AGENT_NETWORK_AUTHORIZATION"
    )

    assert contract["status"] == "PRENETWORK_SECURITY_GATE_ONLY"
    assert contract["topology"]["agent_count"] == 2
    assert contract["topology"]["loopback_only"] is True
    assert contract["topology"]["external_connectivity_authorized"] is False

    assert contract["identity"]["secret_based"] is False
    assert contract["identity"]["production_authentication_defined"] is False

    assert contract["gap_reassessment"]["F37-07"] == "PARTIAL_PRENETWORK_GATE_READY"
    assert contract["gap_reassessment"]["F37-10"] == "BLOCKED_NETWORK_PROPAGATION_EVIDENCE_REQUIREMENTS_DEFINED"
    assert contract["gap_reassessment"]["F37-11"] == "BLOCKED_REORG_POLICY"

    auth = contract["authorization"]

    assert auth["authorization_state"] == "NOT_AUTHORIZED"
    assert auth["explicit_operator_authorization_required"] is True

    for field in (
        "network_authorized",
        "socket_authorized",
        "listen_authorized",
        "connect_authorized",
        "process_start_authorized",
        "p2p_runtime_authorized",
        "rpc_authorized",
        "ledger_mutation_authorized",
        "canonical_height_override_authorized",
        "wallet_creation_authorized",
        "key_generation_authorized",
        "signing_authorized",
        "mining_authorized",
        "broadcast_authorized",
        "testnet_start_authorized",
        "settlement_authorized",
    ):
        assert auth[field] is False


def test_security_case_manifest_is_unique_and_offline():
    manifest = json.loads(
        FIXTURES.read_text(encoding="utf-8")
    )

    ids = [
        item["id"]
        for item in manifest["cases"]
    ]

    assert len(ids) == len(set(ids))
    assert manifest["offline_only"] is True
    assert manifest["network_execution_authorized"] is False
    assert len(ids) == 9


def test_production_gate_module_has_no_network_or_runtime_io():
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
        "accept",
        "send",
        "sendall",
        "recv",
        "recvfrom",
        "Popen",
        "run",
        "system",
    }

    imports = set()
    calls = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(
                alias.name.split(".")[0]
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(
                node.module.split(".")[0]
            )
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    assert forbidden_imports.isdisjoint(imports)
    assert forbidden_calls.isdisjoint(calls)
