# SPDX-License-Identifier: Apache-2.0

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "tests/foundation143_loopback_transport_helper.py"
EVIDENCE = ROOT / "docs/foundation143_isolated_loopback_experiment_evidence_v0.1.json"


def evidence():
    return json.loads(
        EVIDENCE.read_text(encoding="utf-8")
    )


def test_real_loopback_evidence_passed():
    data = evidence()

    assert data["result"] == "PASS"
    assert data["status"] == "ISOLATED_TWO_AGENT_PROPAGATION_EVIDENCE=PASS"

    topology = data["topology"]

    assert topology["agent_count"] == 2
    assert topology["agent_a"]["host"] == "127.0.0.1"
    assert topology["agent_a"]["port"] == 28428
    assert topology["agent_b"]["host"] == "127.0.0.1"
    assert topology["agent_b"]["port"] == 28429
    assert topology["ipv4_loopback_only"] is True
    assert topology["external_network_used"] is False


def test_actual_transport_and_reconnect_replay_evidence():
    data = evidence()
    actual = data["actual_transport"]
    replay = data["reconnect_replay"]

    assert actual["socket_opened"] is True
    assert actual["listener_started"] is True
    assert actual["outbound_connection_started"] is True
    assert actual["tcp_connection_established"] is True
    assert actual["source_endpoint_verified"] is True
    assert actual["valid_session_completed"] is True
    assert actual["reconnect_completed"] is True
    assert actual["sockets_closed_after_experiment"] is True
    assert actual["subprocess_started"] is False
    assert actual["production_p2p_runtime_started"] is False
    assert actual["rpc_started"] is False

    assert replay["replay_state_preserved"] is True
    assert replay["replayed_message_rejected"] is True
    assert replay["stable_code"] == "message_replayed"
    assert replay["disconnect_required"] is True


def test_all_three_peer_evidence_types_propagated():
    data = evidence()
    propagation = data["propagation"]

    assert propagation["agent_b_to_agent_a"] == [
        "HELLO",
        "TIP_EVIDENCE",
        "CANDIDATE_EVIDENCE",
    ]

    assert propagation["agent_a_to_agent_b"] == [
        "HELLO",
    ]

    assert propagation["all_valid_frames_admitted"] is True

    for value in propagation["frame_ids"].values():
        assert len(value) == 64

    for value in propagation["frame_sha256"].values():
        assert len(value) == 64


def test_core_authority_and_economic_state_were_unchanged():
    data = evidence()
    authority = data["authority_preservation"]

    assert authority["local_tip_before"] == 0
    assert authority["local_tip_after"] == 0

    for field in (
        "ledger_mutated",
        "canonical_height_overridden",
        "issuance_authority_granted",
        "supply_authority_granted",
        "validation_authority_granted",
        "history_authority_granted",
        "wallet_created",
        "key_generated",
        "signing_performed",
        "mining_performed",
        "public_broadcast_performed",
        "settlement_performed",
        "real_value_used",
        "historical_state_imported",
    ):
        assert authority[field] is False


def test_unresolved_production_policies_remain_undefined():
    data = evidence()
    policy = data["policy_state"]

    assert policy["production_peer_authentication_defined"] is False
    assert policy["trusted_production_time_defined"] is False
    assert policy["production_resource_limits_defined"] is False
    assert policy["confirmation_policy_defined"] is False
    assert policy["reorg_policy_defined"] is False


def test_f37_reassessment_is_bounded():
    data = evidence()
    gaps = data["gap_reassessment"]

    assert gaps["F37-07"] == "PARTIAL_ISOLATED_LOOPBACK_TRANSPORT_EVIDENCE"
    assert gaps["F37-10"] == "PARTIAL_ISOLATED_LOOPBACK_PROPAGATION_EVIDENCE"
    assert gaps["F37-11"] == "BLOCKED_REORG_POLICY"


def test_network_helper_is_test_only_and_has_no_process_or_external_stack():
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
            imports.add(
                node.module.split(".")[0]
            )

    assert "socket" in imports

    forbidden = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "asyncio",
        "multiprocessing",
    }

    assert forbidden.isdisjoint(imports)

    assert "HOST = \"127.0.0.1\"" in source
    assert "0.0.0.0" not in source
    assert "\"::1\"" not in source
