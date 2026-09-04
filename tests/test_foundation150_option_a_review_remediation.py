# SPDX-License-Identifier: Apache-2.0

import ast
from dataclasses import replace
from pathlib import Path

import pytest

from coin.disposable_testnet_option_a_policy import (
    CandidateHistory,
    HistoryEntry,
    OptionAPolicyError,
    OptionAPolicyState,
    assess_option_a,
    assess_peer_equivocation,
    detect_equivocation,
    request_resume,
    transition_sync_state,
)


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "coin/disposable_testnet_option_a_policy.py"
NETWORK = "L28-DISPOSABLE-OPTIONA"
GENESIS = "a" * 64


class UnhashableStr(str):
    __hash__ = None


def history(source_id, block_ids):
    entries = []
    parent_id = "GENESIS"

    for height, block_id in enumerate(block_ids):
        entries.append(HistoryEntry(height, block_id, parent_id))
        parent_id = block_id

    return CandidateHistory(
        source_id=source_id,
        network_id=NETWORK,
        genesis_hash=GENESIS,
        entries=tuple(entries),
    )


def benign_assessment():
    return assess_option_a(
        history("LOCAL_CORE", ["A0", "A1"]),
        history("PEER_A", ["A0", "A1"]),
    )


def test_peer_equivocation_assessment_halts_and_retains_local_state():
    first = history("PEER_A", ["A0", "A1", "X2"])
    second = history("PEER_A", ["A0", "A1", "Y2"])

    assessment = assess_peer_equivocation(first, second)
    state = transition_sync_state(
        OptionAPolicyState(status="SYNCING", code="initial"),
        assessment,
    )

    assert assessment.code == "HALT_SYNC_PEER_EQUIVOCATION"
    assert assessment.conflict is True
    assert assessment.halt_sync is True
    assert assessment.divergence_height == 2
    assert assessment.retain_current_local_canonical_state is True
    assert state.status == "HALTED_CONFLICT"
    assert state.halt_height == 2
    assert state.canonical_state_changed is False
    assert state.ledger_mutated is False
    assert detect_equivocation(first, second) is True


def test_non_equivocation_remains_boolean_compatible_and_nontransitioning():
    first = history("PEER_A", ["A0", "A1"])
    second = history("PEER_A", ["A0", "A1", "A2"])

    assessment = assess_peer_equivocation(first, second)
    state = transition_sync_state(
        OptionAPolicyState(status="SYNCING", code="initial"),
        assessment,
    )

    assert assessment.code == "NO_PEER_EQUIVOCATION"
    assert assessment.conflict is False
    assert state.status == "SYNCING"
    assert detect_equivocation(first, second) is False


@pytest.mark.parametrize(
    "field",
    [
        "candidate_apply_authorized",
        "automatic_reorg_authorized",
        "winner_selected",
        "confirmation_claimed",
        "canonical_height_override_authorized",
        "ledger_mutation_authorized",
        "issuance_authority",
        "supply_authority",
        "validation_authority",
        "history_authority",
        "settlement_authority",
    ],
)
def test_forged_assessment_authority_is_rejected_before_transition(field):
    forged = replace(benign_assessment(), **{field: True})

    with pytest.raises(OptionAPolicyError) as exc:
        transition_sync_state(
            OptionAPolicyState(status="SYNCING", code="initial"),
            forged,
        )

    assert exc.value.code == "assessment_authority_invalid"


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"conflict": True}, "assessment_invariant_invalid"),
        ({"halt_sync": True}, "assessment_invariant_invalid"),
        ({"divergence_height": 0}, "assessment_invariant_invalid"),
        ({"code": "HALT_SYNC_CONFLICT"}, "assessment_invariant_invalid"),
        (
            {"retain_current_local_canonical_state": False},
            "assessment_retain_state_required",
        ),
    ],
)
def test_contradictory_assessment_invariants_fail_closed(changes, code):
    with pytest.raises(OptionAPolicyError) as exc:
        transition_sync_state(
            OptionAPolicyState(status="SYNCING", code="initial"),
            replace(benign_assessment(), **changes),
        )

    assert exc.value.code == code


@pytest.mark.parametrize("status", ["SYNCING", "HALTED_CONFLICT"])
def test_unhashable_assessment_code_fails_with_deterministic_error(status):
    state = OptionAPolicyState(
        status=status,
        code="initial",
        halt_height=1 if status == "HALTED_CONFLICT" else None,
    )

    with pytest.raises(OptionAPolicyError) as exc:
        transition_sync_state(
            state,
            replace(benign_assessment(), code=[]),
        )

    assert type(exc.value) is OptionAPolicyError
    assert exc.value.code == "assessment_invariant_invalid"


@pytest.mark.parametrize("operation", ["transition", "resume"])
def test_unhashable_policy_status_fails_with_deterministic_error(operation):
    state = OptionAPolicyState(status=[], code="initial")

    with pytest.raises(OptionAPolicyError) as exc:
        if operation == "transition":
            transition_sync_state(state, benign_assessment())
        else:
            request_resume(state)

    assert type(exc.value) is OptionAPolicyError
    assert exc.value.code == "policy_state_invalid"


def test_unhashable_string_subclass_assessment_code_fails_deterministically():
    malformed = UnhashableStr("NO_CONFLICT_EQUAL_HISTORY")

    with pytest.raises(OptionAPolicyError) as exc:
        transition_sync_state(
            OptionAPolicyState(status="SYNCING", code="initial"),
            replace(benign_assessment(), code=malformed),
        )

    assert type(exc.value) is OptionAPolicyError
    assert exc.value.code == "assessment_invariant_invalid"


@pytest.mark.parametrize("operation", ["transition", "resume"])
def test_unhashable_string_subclass_policy_status_fails_deterministically(
    operation,
):
    state = OptionAPolicyState(
        status=UnhashableStr("SYNCING"),
        code="initial",
    )

    with pytest.raises(OptionAPolicyError) as exc:
        if operation == "transition":
            transition_sync_state(state, benign_assessment())
        else:
            request_resume(state)

    assert type(exc.value) is OptionAPolicyError
    assert exc.value.code == "policy_state_invalid"


@pytest.mark.parametrize(
    "assessment",
    [
        replace(benign_assessment(), candidate_apply_authorized=True),
        replace(benign_assessment(), halt_sync=True),
    ],
)
def test_sticky_halt_does_not_bypass_assessment_validation(assessment):
    halted = OptionAPolicyState(
        status="HALTED_CONFLICT",
        code="HALTED_BY_OPTION_A",
        halt_height=1,
    )

    with pytest.raises(OptionAPolicyError):
        transition_sync_state(halted, assessment)


@pytest.mark.parametrize("field", ["canonical_state_changed", "ledger_mutated"])
@pytest.mark.parametrize("operation", ["transition", "resume"])
def test_forged_policy_state_mutation_flags_fail_closed(field, operation):
    state = replace(
        OptionAPolicyState(status="SYNCING", code="initial"),
        **{field: True},
    )

    with pytest.raises(OptionAPolicyError) as exc:
        if operation == "transition":
            transition_sync_state(state, benign_assessment())
        else:
            request_resume(state)

    assert exc.value.code == "policy_state_mutation_invalid"


def test_sticky_halt_and_governed_resume_denial_are_preserved():
    first = history("PEER_A", ["A0", "A1", "X2"])
    second = history("PEER_A", ["A0", "A1", "Y2"])
    halted = transition_sync_state(
        OptionAPolicyState(status="SYNCING", code="initial"),
        assess_peer_equivocation(first, second),
    )

    still_halted = transition_sync_state(halted, benign_assessment())
    resume = request_resume(still_halted)

    assert still_halted.status == "HALTED_CONFLICT"
    assert still_halted.code == "HALT_STICKY_GOVERNED_RESOLUTION_REQUIRED"
    assert still_halted.canonical_state_changed is False
    assert still_halted.ledger_mutated is False
    assert resume.allowed is False
    assert resume.code == "GOVERNED_DETERMINISTIC_RESOLUTION_RULE_REQUIRED"
    assert resume.canonical_state_changed is False


def test_remediation_adds_no_runtime_or_network_authority():
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    forbidden_imports = {
        "asyncio",
        "http",
        "os",
        "pathlib",
        "requests",
        "secrets",
        "socket",
        "subprocess",
        "time",
        "urllib",
    }
    forbidden_calls = {
        "accept",
        "bind",
        "broadcast",
        "connect",
        "listen",
        "open",
        "recv",
        "send",
        "sign",
        "submit",
    }
    imports = set()
    calls = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    assert forbidden_imports.isdisjoint(imports)
    assert forbidden_calls.isdisjoint(calls)
