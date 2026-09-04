# SPDX-License-Identifier: Apache-2.0

import ast
import json
from pathlib import Path

import pytest

from coin.disposable_testnet_option_a_policy import (
    CandidateHistory,
    HistoryEntry,
    OptionAPolicyError,
    OptionAPolicyState,
    assess_option_a,
    detect_equivocation,
    request_resume,
    transition_sync_state,
)


ROOT = Path(__file__).resolve().parents[1]
SELECTED = ROOT / "docs/l28_option_a_selected_policy_v0.1.json"
EVIDENCE = ROOT / "docs/foundation148_option_a_adversarial_evidence_v0.1.json"
REVIEW = ROOT / "docs/l28_option_a_independent_review_checklist_v0.1.json"
MODULE = ROOT / "coin/disposable_testnet_option_a_policy.py"

NETWORK = "L28-DISPOSABLE-OPTIONA"
GENESIS = "a" * 64


def history(source, ids):
    entries = []
    parent = "GENESIS"

    for height, block_id in enumerate(ids):
        entries.append(
            HistoryEntry(
                height=height,
                block_id=block_id,
                parent_id=parent,
            )
        )
        parent = block_id

    return CandidateHistory(
        source_id=source,
        network_id=NETWORK,
        genesis_hash=GENESIS,
        entries=tuple(entries),
    )


def test_f146_selects_option_a_only_as_non_normative_offline_boundary():
    data = json.loads(SELECTED.read_text(encoding="utf-8"))

    assert data["selected_option"] == "OPTION_A_HALT_ON_CONFLICT"
    assert data["policy_selected"] is True
    assert data["selection_scope"] == "OFFLINE_IMPLEMENTATION_SAFETY_BOUNDARY"

    protocol = data["protocol"]

    assert protocol["normative_protocol_adoption"] is False
    assert protocol["protocol_invariants_changed"] is False
    assert protocol["economic_invariants_changed"] is False
    assert protocol["transaction_validation_changed"] is False
    assert protocol["canonical_height_rule_changed"] is False
    assert protocol["historical_state_changed"] is False
    assert protocol["future_normative_adoption_requires_governed_compatibility_decision"] is True
    assert protocol["breaking_normative_change_requires_v2_0_0"] is True


def test_runtime_authority_remains_false():
    auth = json.loads(
        SELECTED.read_text(encoding="utf-8")
    )["authorization"]

    assert auth["offline_policy_implementation_authorized"] is True

    for field, value in auth.items():
        if field != "offline_policy_implementation_authorized":
            assert value is False


def test_equal_history_is_not_conflict_and_never_auto_applies():
    local = history("LOCAL_CORE", ["A0", "A1", "A2"])
    peer = history("PEER_A", ["A0", "A1", "A2"])

    result = assess_option_a(local, peer)

    assert result.code == "NO_CONFLICT_EQUAL_HISTORY"
    assert result.conflict is False
    assert result.halt_sync is False
    assert result.candidate_apply_authorized is False
    assert result.automatic_reorg_authorized is False
    assert result.winner_selected is False


def test_extension_is_evidence_only():
    local = history("LOCAL_CORE", ["A0", "A1"])
    peer = history("PEER_A", ["A0", "A1", "A2"])

    result = assess_option_a(local, peer)

    assert result.code == "EXTENSION_EVIDENCE_ONLY"
    assert result.conflict is False
    assert result.candidate_apply_authorized is False
    assert result.retain_current_local_canonical_state is True


def test_stale_peer_is_nonauthoritative():
    local = history("LOCAL_CORE", ["A0", "A1", "A2"])
    peer = history("PEER_A", ["A0", "A1"])

    result = assess_option_a(local, peer)

    assert result.code == "STALE_NONAUTHORITATIVE_EVIDENCE"
    assert result.conflict is False
    assert result.halt_sync is False


def test_conflicting_history_halts_at_first_divergence():
    local = history("LOCAL_CORE", ["A0", "A1", "A2"])
    peer = history("PEER_A", ["A0", "B1", "B2"])

    result = assess_option_a(local, peer)

    assert result.code == "HALT_SYNC_CONFLICT"
    assert result.conflict is True
    assert result.halt_sync is True
    assert result.divergence_height == 1
    assert result.retain_current_local_canonical_state is True
    assert result.winner_selected is False


def test_deep_conflict_does_not_require_invented_reorg_depth():
    local = history("LOCAL_CORE", ["A0", "A1", "A2", "A3"])
    peer = history("PEER_A", ["B0", "B1", "B2", "B3", "B4"])

    result = assess_option_a(local, peer)

    assert result.conflict is True
    assert result.divergence_height == 0
    assert result.automatic_reorg_authorized is False
    assert result.confirmation_claimed is False


def test_halt_state_is_sticky_after_benign_later_evidence():
    local = history("LOCAL_CORE", ["A0", "A1", "A2"])
    conflict = history("PEER_A", ["A0", "B1", "B2"])
    benign = history("PEER_A", ["A0", "A1", "A2"])

    first = transition_sync_state(
        OptionAPolicyState(status="SYNCING", code="initial"),
        assess_option_a(local, conflict),
    )

    assert first.status == "HALTED_CONFLICT"

    second = transition_sync_state(
        first,
        assess_option_a(local, benign),
    )

    assert second.status == "HALTED_CONFLICT"
    assert second.code == "HALT_STICKY_GOVERNED_RESOLUTION_REQUIRED"
    assert second.canonical_state_changed is False


def test_resume_is_denied_without_governed_rule():
    state = OptionAPolicyState(
        status="HALTED_CONFLICT",
        code="HALTED_BY_OPTION_A",
        halt_height=1,
    )

    result = request_resume(state)

    assert result.allowed is False
    assert result.code == "GOVERNED_DETERMINISTIC_RESOLUTION_RULE_REQUIRED"
    assert result.canonical_state_changed is False


def test_equivocation_is_detected():
    first = history("PEER_A", ["A0", "A1", "X2"])
    second = history("PEER_A", ["A0", "A1", "Y2"])

    assert detect_equivocation(first, second) is True


def test_extension_by_same_peer_is_not_equivocation():
    first = history("PEER_A", ["A0", "A1"])
    second = history("PEER_A", ["A0", "A1", "A2"])

    assert detect_equivocation(first, second) is False


def test_partition_reconnect_conflict_cannot_rewrite_canonical_state():
    local = history("LOCAL_CORE", ["A0", "A1", "A2", "A3"])
    peer = history("PEER_PARTITION", ["A0", "A1", "P2", "P3", "P4"])

    assessment = assess_option_a(local, peer)
    state = transition_sync_state(
        OptionAPolicyState(status="SYNCING", code="initial"),
        assessment,
    )

    assert state.status == "HALTED_CONFLICT"
    assert state.canonical_state_changed is False
    assert state.ledger_mutated is False


def test_wrong_network_fails_closed():
    local = history("LOCAL_CORE", ["A0"])
    peer = CandidateHistory(
        source_id="PEER_A",
        network_id="OTHER-NETWORK",
        genesis_hash=GENESIS,
        entries=(
            HistoryEntry(
                height=0,
                block_id="A0",
                parent_id="GENESIS",
            ),
        ),
    )

    with pytest.raises(OptionAPolicyError) as exc:
        assess_option_a(local, peer)

    assert exc.value.code == "history_binding_mismatch"


def test_missing_required_history_state_fails_closed():
    empty = CandidateHistory(
        source_id="PEER_A",
        network_id=NETWORK,
        genesis_hash=GENESIS,
        entries=(),
    )

    local = history("LOCAL_CORE", ["A0"])

    with pytest.raises(OptionAPolicyError) as exc:
        assess_option_a(local, empty)

    assert exc.value.code == "required_history_state_missing"


def test_malformed_lineage_fails_closed():
    local = history("LOCAL_CORE", ["A0", "A1"])

    peer = CandidateHistory(
        source_id="PEER_A",
        network_id=NETWORK,
        genesis_hash=GENESIS,
        entries=(
            HistoryEntry(0, "A0", "GENESIS"),
            HistoryEntry(1, "B1", "WRONG-PARENT"),
        ),
    )

    with pytest.raises(OptionAPolicyError) as exc:
        assess_option_a(local, peer)

    assert exc.value.code == "history_link_invalid"


def test_bool_height_is_rejected():
    local = history("LOCAL_CORE", ["A0"])

    peer = CandidateHistory(
        source_id="PEER_A",
        network_id=NETWORK,
        genesis_hash=GENESIS,
        entries=(
            HistoryEntry(True, "A0", "GENESIS"),
        ),
    )

    with pytest.raises(OptionAPolicyError) as exc:
        assess_option_a(local, peer)

    assert exc.value.code == "history_height_invalid"


def test_f148_evidence_passed_without_authority_grant():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert data["status"] == "PASS"
    assert data["offline_only"] is True
    assert data["all_expected_results_matched"] is True
    assert data["equivocation_detected"] is True

    assert all(
        value is False
        for value in data["authority_preservation"].values()
    )


def test_f149_packet_does_not_self_certify_independent_review():
    data = json.loads(REVIEW.read_text(encoding="utf-8"))

    assert data["status"] == "READY_FOR_INDEPENDENT_SECURITY_REVIEW"
    assert data["independent_review_performed"] is False
    assert data["independent_review_passed"] is False
    assert data["self_certification_forbidden"] is True

    assert data["gap_reassessment"]["F37-11"] == (
        "PARTIAL_OFFLINE_OPTION_A_IMPLEMENTED_PENDING_INDEPENDENT_REVIEW"
    )


def test_option_a_module_has_no_runtime_io_or_network_stack():
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))

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
        "remove",
        "connect",
        "bind",
        "listen",
        "accept",
        "send",
        "recv",
        "run",
        "Popen",
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
