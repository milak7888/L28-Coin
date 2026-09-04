# SPDX-License-Identifier: Apache-2.0

import ast
import copy
import json
from pathlib import Path

import pytest

from coin.disposable_testnet_identity import PROTECTED_ECONOMIC_FACTS
from coin.disposable_testnet_p2p_conformance import (
    ALLOWED_MESSAGE_TYPES,
    ENVELOPE_FIELDS,
    OFFLINE_CONFORMANCE_MAX_FRAME_BYTES,
    STABLE_CODES,
    DisposableP2PConformanceError,
    assess_frame_bytes,
    assess_offline_frame,
    build_offline_frame,
    encode_frame_bytes,
    evaluate_peer_tip_evidence,
    nonce_replay_key,
    plan_single_writer_sync,
    prepare_p2p_conformance_boundary,
)
from coin.disposable_testnet_runtime_boundary import (
    prepare_runtime_boundary,
)
from coin.node_role_model import P2PNodeRoleModel


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "coin/disposable_testnet_p2p_conformance.py"
SECURITY_PROFILE = ROOT / "docs/l28_core_p2p_security_profile_v0.1.json"
M3_CONTRACT = ROOT / "docs/l28_disposable_testnet_m3_security_contract_v0.1.json"
FIXTURES = ROOT / "tests/fixtures/foundation141_m3_adversarial_cases_v0.1.json"


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


def valid_frame(binding, tip):
    return build_offline_frame(
        binding,
        tip,
        message_type="HELLO",
        peer_id="peer-fixture-01",
        nonce="nonce-0001",
        timestamp=1000,
        expiry=1100,
        payload={
            "capabilities": [
                "offline-conformance"
            ]
        },
    )


def test_p2p_boundary_configures_without_listening():
    binding, tip = runtime_context()
    boundary = prepare_p2p_conformance_boundary(
        binding,
        tip,
    )

    assert boundary["lifecycle_state"] == "CONFIGURED"
    assert boundary["offline_conformance_only"] is True

    for field in (
        "network_authorized",
        "socket_authorized",
        "listen_authorized",
        "connect_authorized",
        "rpc_authorized",
        "p2p_runtime_authorized",
        "ledger_mutation_authorized",
        "canonical_height_override_authorized",
        "signing_authorized",
        "mining_authorized",
        "broadcast_authorized",
        "testnet_start_authorized",
        "settlement_authorized",
    ):
        assert boundary[field] is False


def test_listening_reserved_remains_unreachable():
    p2p = P2PNodeRoleModel()
    updated, result = p2p.transition(
        "LISTENING_RESERVED"
    )

    assert result.ok is False
    assert result.code == "reserved_state_unreachable"
    assert updated is p2p


def test_valid_frame_is_deterministic_and_admitted():
    binding, tip = runtime_context()

    one = valid_frame(binding, tip)
    two = valid_frame(binding, tip)

    assert one == two
    assert len(one["message_id"]) == 64
    assert len(one["payload_digest"]) == 64

    result = assess_offline_frame(
        one,
        binding,
        tip,
        now_ts=1000,
    )

    assert result.ok is True
    assert result.code == "admitted_offline_evidence"
    assert result.disconnect is False
    assert result.peer_authenticated is False
    assert result.transport_authority is False
    assert result.core_override_authority is False
    assert result.ledger_mutation_authority is False
    assert result.canonical_height_authority is False
    assert result.issuance_authority is False
    assert result.supply_authority is False
    assert result.settlement_authority is False


def test_canonical_encode_decode_round_trip():
    binding, tip = runtime_context()
    frame = valid_frame(binding, tip)

    encoded = encode_frame_bytes(frame)

    assert type(encoded) is bytes
    assert len(encoded) <= OFFLINE_CONFORMANCE_MAX_FRAME_BYTES

    result = assess_frame_bytes(
        encoded,
        binding,
        tip,
        now_ts=1000,
    )

    assert result.ok is True
    assert result.normalized_frame == frame


def test_prior_security_profile_required_fields_are_preserved():
    profile = json.loads(
        SECURITY_PROFILE.read_text(encoding="utf-8")
    )

    required = set(
        profile["future_frame_requirements"]["required_fields"]
    )

    assert required <= ENVELOPE_FIELDS
    assert {
        "genesis_hash",
        "config_hash",
        "payload",
    } <= ENVELOPE_FIELDS

    assert (
        profile["p2p_lifecycle"]["network_activation_transition_present"]
        is False
    )


def test_stable_codes_are_unique():
    assert len(STABLE_CODES) == len(set(STABLE_CODES))
    assert "frame_too_large" in STABLE_CODES
    assert "network_id_mismatch" in STABLE_CODES
    assert "message_replayed" in STABLE_CODES


def test_cross_network_frame_is_rejected():
    binding_a, tip_a = runtime_context(
        "L28-DISPOSABLE-LAB001"
    )
    binding_b, tip_b = runtime_context(
        "L28-DISPOSABLE-LAB002"
    )

    frame = valid_frame(binding_a, tip_a)

    result = assess_offline_frame(
        frame,
        binding_b,
        tip_b,
        now_ts=1000,
    )

    assert result.ok is False
    assert result.code == "network_id_mismatch"
    assert result.disconnect is True


@pytest.mark.parametrize(
    "field,expected",
    [
        ("genesis_hash", "genesis_hash_mismatch"),
        ("config_hash", "config_hash_mismatch"),
    ],
)
def test_binding_hash_mismatch_is_rejected(field, expected):
    binding, tip = runtime_context()
    frame = valid_frame(binding, tip)
    changed = dict(frame)
    changed[field] = "0" * 64

    result = assess_offline_frame(
        changed,
        binding,
        tip,
        now_ts=1000,
    )

    assert result.ok is False
    assert result.code == expected


def test_unknown_critical_field_is_rejected():
    binding, tip = runtime_context()
    frame = valid_frame(binding, tip)
    changed = dict(frame)
    changed["unknown_critical"] = True

    result = assess_offline_frame(
        changed,
        binding,
        tip,
        now_ts=1000,
    )

    assert result.ok is False
    assert result.code == "unknown_critical_field"


def test_missing_field_is_rejected():
    binding, tip = runtime_context()
    frame = valid_frame(binding, tip)
    changed = dict(frame)
    changed.pop("nonce")

    result = assess_offline_frame(
        changed,
        binding,
        tip,
        now_ts=1000,
    )

    assert result.ok is False
    assert result.code == "malformed_frame"


def test_peer_identity_evidence_is_structural_only():
    binding, tip = runtime_context()
    frame = valid_frame(binding, tip)
    changed = dict(frame)
    changed["peer_identity_evidence"] = {
        "kind": "production_authenticated",
        "peer_id": "peer-fixture-01",
    }

    result = assess_offline_frame(
        changed,
        binding,
        tip,
        now_ts=1000,
    )

    assert result.ok is False
    assert result.code == "peer_identity_evidence_invalid"


def test_expired_message_is_rejected():
    binding, tip = runtime_context()
    frame = build_offline_frame(
        binding,
        tip,
        message_type="HELLO",
        peer_id="peer-fixture-01",
        nonce="nonce-expired",
        timestamp=1000,
        expiry=1001,
        payload={"mode": "offline"},
    )

    result = assess_offline_frame(
        frame,
        binding,
        tip,
        now_ts=1002,
    )

    assert result.ok is False
    assert result.code == "message_expired"


def test_message_replay_is_rejected():
    binding, tip = runtime_context()
    frame = valid_frame(binding, tip)

    result = assess_offline_frame(
        frame,
        binding,
        tip,
        now_ts=1000,
        seen_message_ids={frame["message_id"]},
    )

    assert result.ok is False
    assert result.code == "message_replayed"


def test_nonce_replay_is_rejected():
    binding, tip = runtime_context()
    frame = valid_frame(binding, tip)
    key = nonce_replay_key(frame)

    result = assess_offline_frame(
        frame,
        binding,
        tip,
        now_ts=1000,
        seen_nonce_keys={key},
    )

    assert result.ok is False
    assert result.code == "nonce_replayed"


def test_duplicate_json_field_is_rejected_before_admission():
    binding, tip = runtime_context()

    raw = (
        b"{\"protocol_version\":\"1.0.0\","
        b"\"protocol_version\":\"1.0.0\"}"
    )

    result = assess_frame_bytes(
        raw,
        binding,
        tip,
        now_ts=1000,
    )

    assert result.ok is False
    assert result.code == "duplicate_field"


def test_malformed_json_is_rejected():
    binding, tip = runtime_context()

    result = assess_frame_bytes(
        b"{",
        binding,
        tip,
        now_ts=1000,
    )

    assert result.ok is False
    assert result.code == "malformed_frame"


def test_oversized_frame_is_rejected_predecode():
    binding, tip = runtime_context()

    raw = b"x" * (
        OFFLINE_CONFORMANCE_MAX_FRAME_BYTES + 1
    )

    result = assess_frame_bytes(
        raw,
        binding,
        tip,
        now_ts=1000,
    )

    assert result.ok is False
    assert result.code == "frame_too_large"


def test_adversarial_fixture_manifest_mutations():
    binding, tip = runtime_context()
    manifest = json.loads(
        FIXTURES.read_text(encoding="utf-8")
    )

    ids = [
        item["id"]
        for item in manifest["cases"]
    ]

    assert len(ids) == len(set(ids))
    assert manifest["offline_only"] is True

    for case in manifest["cases"]:
        frame = valid_frame(binding, tip)
        changed = dict(frame)
        changed[case["mutation"]] = case["value"]

        result = assess_offline_frame(
            changed,
            binding,
            tip,
            now_ts=1000,
        )

        assert result.ok is False, case["id"]
        assert (
            result.code == case["expected_code"]
        ), case["id"]


@pytest.mark.parametrize(
    "message_type",
    sorted(ALLOWED_MESSAGE_TYPES),
)
def test_all_allowed_message_types_validate(message_type):
    binding, tip = runtime_context()

    frame = build_offline_frame(
        binding,
        tip,
        message_type=message_type,
        peer_id="peer-fixture-02",
        nonce="nonce-" + message_type.lower(),
        timestamp=2000,
        expiry=2100,
        payload={
            "message_type": message_type,
            "evidence_only": True,
        },
    )

    result = assess_offline_frame(
        frame,
        binding,
        tip,
        now_ts=2000,
    )

    assert result.ok is True


@pytest.mark.parametrize(
    "peer_height,relation",
    [
        (0, "EQUAL"),
        (1, "PEER_AHEAD"),
    ],
)
def test_peer_tip_is_evidence_only(peer_height, relation):
    binding, tip = runtime_context()

    assessment = evaluate_peer_tip_evidence(
        binding,
        tip,
        peer_height=peer_height,
    )

    assert assessment.local_height == 0
    assert assessment.peer_height == peer_height
    assert assessment.relation == relation
    assert assessment.peer_tip_authoritative is False
    assert assessment.local_tip_changed is False
    assert assessment.confirmation_claimed is False
    assert assessment.reorg_decision_made is False
    assert tip.read_height() == 0


def test_single_writer_sync_plan_has_zero_peer_authority():
    binding, tip = runtime_context()

    assessment = evaluate_peer_tip_evidence(
        binding,
        tip,
        peer_height=3,
    )

    plan = plan_single_writer_sync(assessment)

    assert plan["action"] == "REQUEST_CANDIDATE_RANGE"
    assert plan["request_start"] == 1
    assert plan["request_end"] == 3
    assert plan["plan_only"] is True
    assert plan["single_writer"] == "LOCAL_CORE_ONLY"
    assert plan["peer_candidate_evidence_only"] is True
    assert plan["peer_can_mutate_local_tip"] is False
    assert plan["peer_can_override_canonical_height"] is False
    assert plan["automatic_apply"] is False
    assert plan["ledger_mutation_authorized"] is False
    assert plan["issuance_authority"] is False
    assert plan["supply_authority"] is False
    assert plan["validation_override_authority"] is False
    assert plan["history_override_authority"] is False
    assert plan["settlement_authority"] is False
    assert plan["confirmation_policy_defined"] is False
    assert plan["reorg_policy_defined"] is False
    assert tip.read_height() == 0


def test_machine_contract_keeps_network_and_policy_blocked():
    contract = json.loads(
        M3_CONTRACT.read_text(encoding="utf-8")
    )

    assert contract["status"] == "OFFLINE_CONFORMANCE_ONLY"
    assert contract["m3_offline_conformance_ready"] is True

    assert (
        contract["gap_reassessment"]["F37-07"]
        == "PARTIAL_OFFLINE_CONFORMANCE"
    )
    assert (
        contract["gap_reassessment"]["F37-10"]
        == "BLOCKED_NETWORK_PROPAGATION"
    )
    assert (
        contract["gap_reassessment"]["F37-11"]
        == "BLOCKED_REORG_POLICY"
    )

    assert (
        contract["peer_controls"]["production_authentication_defined"]
        is False
    )
    assert (
        contract["peer_controls"]["trusted_production_time_defined"]
        is False
    )
    assert (
        contract["resource_limits"]["production_runtime_limits_defined"]
        is False
    )
    assert (
        contract["single_writer_sync"]["confirmation_policy_defined"]
        is False
    )
    assert (
        contract["single_writer_sync"]["reorg_policy_defined"]
        is False
    )

    for field in (
        "network_authorized",
        "socket_authorized",
        "listen_authorized",
        "connect_authorized",
        "rpc_authorized",
        "p2p_runtime_authorized",
        "ledger_mutation_authorized",
        "wallet_creation_authorized",
        "key_generation_authorized",
        "signing_authorized",
        "mining_authorized",
        "broadcast_authorized",
        "testnet_start_authorized",
        "settlement_authorized",
    ):
        assert contract[field] is False


def test_production_p2p_module_has_no_network_or_runtime_io():
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
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    assert forbidden_imports.isdisjoint(imports)
    assert forbidden_calls.isdisjoint(calls)
