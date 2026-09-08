# SPDX-License-Identifier: Apache-2.0
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


candidate_model = load_module(
    "foundation164_candidate", "coin/future_live_adapter_candidate.py"
)
terminal_model = load_module(
    "foundation164_terminalization", "coin/future_live_adapter_terminalization.py"
)
boundary_model = load_module(
    "foundation162_boundary", "tests/foundation162_future_live_adapter_boundary.py"
)
f161_model = load_module(
    "foundation161_lifecycle", "tests/foundation161_future_runtime_lifecycle_helper.py"
)


class Token:
    pass


class LookalikeToken:
    def __eq__(self, _other):
        return True


def load_f163_gate():
    return json.loads(
        (
            ROOT
            / "docs/l28_foundation163_live_adapter_implementation_readiness_gate_v0.1.json"
        ).read_text(encoding="utf-8")
    )


def make_inputs(child_count=2, supervisor_count=2):
    ready = Token()
    result_channel = Token()
    children = tuple(Token() for _ in range(child_count))
    supervisors = tuple(Token() for _ in range(supervisor_count))
    owner = f161_model.FutureRuntimeLifecycleHelper(
        ready,
        result_channel,
        children,
        supervisors,
    )
    boundary = boundary_model.FutureLiveAdapterBoundary()
    boundary.register_parent_owned_resources(
        owner,
        ready,
        result_channel,
        children,
        supervisors,
    )
    return (
        owner,
        boundary,
        load_f163_gate(),
        ready,
        result_channel,
        children,
        supervisors,
        candidate_model.DEADLINE_DESCRIPTOR,
    )


def make_candidate():
    inputs = make_inputs()
    candidate = candidate_model.FutureLiveAdapterCandidate()
    candidate.register_and_freeze(*inputs)
    return candidate, inputs


def move_plan_to_cleanup(candidate):
    for phase in candidate_model.LIFECYCLE_PHASES[1:-1]:
        candidate.plan_lifecycle_transition(phase)


def record_all_terminal(candidate):
    for child in candidate.children:
        candidate.record_child_terminal_state(child)


def record_all_quiescent(candidate):
    for supervisor in candidate.startup_supervisors:
        candidate.record_supervisor_quiescent_state(supervisor)


def test_valid_registration_freeze_and_readiness_are_non_activating():
    candidate, inputs = make_candidate()
    assert candidate.lifecycle_owner is inputs[0]
    assert candidate.security_boundary is inputs[1]
    assert candidate.ready is inputs[3]
    assert candidate.result_channel is inputs[4]
    assert candidate.children == inputs[5]
    assert candidate.startup_supervisors == inputs[6]
    assert candidate.frozen is True
    assert candidate.provenance_verified is True
    assert candidate.preparation_state() == {
        "state": "PREPARED_NON_ACTIVATING_LIVE_ADAPTER_CANDIDATE",
        "planned_phase": "PROCESS_OBJECT_CONSTRUCTION",
        "resources_frozen": True,
        "provenance_verified": True,
        "execution_authorized": False,
        "runtime_authorized": False,
    }


@pytest.mark.parametrize(
    ("index", "replacement", "code"),
    [
        (0, None, "F161_LIFECYCLE_OWNER_REQUIRED"),
        (1, None, "F162_SECURITY_BOUNDARY_REQUIRED"),
        (2, None, "F163_READINESS_GATE_REQUIRED"),
        (3, None, "READY_REFERENCE_REQUIRED"),
        (4, None, "RESULT_CHANNEL_REFERENCE_REQUIRED"),
        (5, (), "EXACT_CHILD_COLLECTION_REQUIRED"),
        (6, (), "EXACT_SUPERVISOR_COLLECTION_REQUIRED"),
        (7, None, "BOUNDED_DEADLINE_DESCRIPTOR_REQUIRED"),
    ],
)
def test_each_missing_resource_fails_closed(index, replacement, code):
    inputs = list(make_inputs())
    inputs[index] = replacement
    candidate = candidate_model.FutureLiveAdapterCandidate()
    with pytest.raises(candidate_model.AdapterCandidateFailure) as captured:
        candidate.register_and_freeze(*inputs)
    assert captured.value.code == code
    assert candidate.frozen is False


@pytest.mark.parametrize("resource_index", [5, 6])
def test_duplicate_child_or_supervisor_is_rejected(resource_index):
    inputs = list(make_inputs())
    item = inputs[resource_index][0]
    inputs[resource_index] = (item, item)
    candidate = candidate_model.FutureLiveAdapterCandidate()
    with pytest.raises(candidate_model.AdapterCandidateFailure) as captured:
        candidate.register_and_freeze(*inputs)
    assert captured.value.code == "DUPLICATE_RESOURCE_IDENTITY"


@pytest.mark.parametrize(
    ("resource_index", "code"),
    [
        (3, "F161_READY_OWNERSHIP_MISMATCH"),
        (4, "F161_RESULT_OWNERSHIP_MISMATCH"),
        (5, "F161_CHILD_OWNERSHIP_MISMATCH"),
        (6, "F161_SUPERVISOR_OWNERSHIP_MISMATCH"),
    ],
)
def test_substitution_and_lookalikes_are_rejected(resource_index, code):
    inputs = list(make_inputs())
    if resource_index in (3, 4):
        inputs[resource_index] = LookalikeToken()
    else:
        resources = list(inputs[resource_index])
        resources[0] = LookalikeToken()
        inputs[resource_index] = tuple(resources)
    candidate = candidate_model.FutureLiveAdapterCandidate()
    with pytest.raises(candidate_model.AdapterCandidateFailure) as captured:
        candidate.register_and_freeze(*inputs)
    assert captured.value.code == code


def test_owner_identity_mismatch_is_rejected():
    inputs = list(make_inputs())
    inputs[0] = LookalikeToken()
    candidate = candidate_model.FutureLiveAdapterCandidate()
    with pytest.raises(candidate_model.AdapterCandidateFailure) as captured:
        candidate.register_and_freeze(*inputs)
    assert captured.value.code == "ACTIVE_F161_PARENT_OWNERSHIP_REQUIRED"


@pytest.mark.parametrize(
    "role",
    [
        "lifecycle_owner",
        "security_boundary",
        "f163_readiness_gate",
        "ready",
        "result_channel",
        "child",
        "startup_supervisor",
        "deadline_descriptor",
    ],
)
def test_mutation_after_freeze_is_rejected_and_resources_preserved(role):
    candidate, inputs = make_candidate()
    with pytest.raises(candidate_model.AdapterCandidateFailure) as captured:
        candidate.attempt_resource_replacement(role, LookalikeToken())
    assert captured.value.code == "FROZEN_CANDIDATE_IMMUTABLE"
    assert candidate.ready is inputs[3]
    assert candidate.result_channel is inputs[4]
    assert candidate.children == inputs[5]
    assert candidate.startup_supervisors == inputs[6]


def test_repeated_freeze_is_rejected():
    candidate, inputs = make_candidate()
    with pytest.raises(candidate_model.AdapterCandidateFailure) as captured:
        candidate.register_and_freeze(*inputs)
    assert captured.value.code == "CANDIDATE_ALREADY_FROZEN"


@pytest.mark.parametrize(
    ("invalid_phase", "code"),
    [
        ("CHILD_BOOTSTRAP_WINDOW", "INVALID_PLANNED_LIFECYCLE_TRANSITION"),
        ("PROCESS_OBJECT_CONSTRUCTION", "INVALID_PLANNED_LIFECYCLE_TRANSITION"),
        ("RELEASED", "INVALID_PLANNED_LIFECYCLE_TRANSITION"),
    ],
)
def test_skipped_backward_and_direct_release_plans_fail_closed(invalid_phase, code):
    candidate, inputs = make_candidate()
    with pytest.raises(candidate_model.AdapterCandidateFailure) as captured:
        candidate.plan_lifecycle_transition(invalid_phase)
    assert captured.value.code == code
    assert candidate.ready is inputs[3]
    assert candidate.result_channel is inputs[4]


def test_repeated_lifecycle_plan_is_rejected():
    candidate, _inputs = make_candidate()
    candidate.plan_lifecycle_transition("PROCESS_START_SUPERVISION")
    with pytest.raises(candidate_model.AdapterCandidateFailure) as captured:
        candidate.plan_lifecycle_transition("PROCESS_START_SUPERVISION")
    assert captured.value.code == "INVALID_PLANNED_LIFECYCLE_TRANSITION"


@pytest.mark.parametrize(
    "deadline",
    [
        ("UNBOUNDED",),
        (
            "SINGLE_BOUNDED_DEADLINE_DATA_ONLY",
            candidate_model.DEADLINE_COVERAGE[:-1],
            ("bounded", True),
            ("timer_implemented", False),
        ),
    ],
)
def test_malformed_or_incomplete_deadline_is_rejected(deadline):
    inputs = list(make_inputs())
    inputs[7] = deadline
    candidate = candidate_model.FutureLiveAdapterCandidate()
    with pytest.raises(candidate_model.AdapterCandidateFailure) as captured:
        candidate.register_and_freeze(*inputs)
    assert captured.value.code == "INVALID_DEADLINE_DESCRIPTOR"


def test_f163_readiness_is_required_and_never_authorizes_execution():
    inputs = list(make_inputs())
    inputs[2]["status"] = "NOT_READY"
    candidate = candidate_model.FutureLiveAdapterCandidate()
    with pytest.raises(candidate_model.AdapterCandidateFailure) as captured:
        candidate.register_and_freeze(*inputs)
    assert captured.value.code == "F163_READINESS_STATUS_REQUIRED"
    assert candidate.execution_authorized is False


@pytest.mark.parametrize(
    ("section", "mutator", "code"),
    [
        (
            "source_bindings",
            lambda value: value.pop("f158_helper"),
            "F163_SOURCE_BINDINGS_REQUIRED",
        ),
        (
            "source_bindings",
            lambda value: value["f160_gate"].__setitem__("sha256", "0" * 64),
            "F163_SOURCE_BINDING_MISMATCH",
        ),
        (
            "readiness_dimensions",
            lambda value: value.pop("A_RESOURCE_PROVENANCE"),
            "F163_READINESS_DIMENSIONS_REQUIRED",
        ),
        (
            "offline_boundary",
            lambda value: value.__setitem__("PROCESSES_STARTED", True),
            "F163_OFFLINE_BOUNDARY_INVALID",
        ),
        (
            "protected_authority",
            lambda value: value.__setitem__("issuance", True),
            "F163_PROTECTED_AUTHORITY_INVALID",
        ),
        (
            "protected_invariants",
            lambda value: value.__setitem__("canonical_validator", "substitute"),
            "F163_PROTECTED_INVARIANTS_INVALID",
        ),
        (
            "protected_invariants",
            lambda value: value.__setitem__("protocol_sha256", "0" * 64),
            "F163_PROTECTED_INVARIANTS_INVALID",
        ),
    ],
)
def test_f163_reduced_or_contradictory_security_evidence_is_rejected(
    section, mutator, code
):
    inputs = list(make_inputs())
    mutator(inputs[2][section])
    candidate = candidate_model.FutureLiveAdapterCandidate()
    with pytest.raises(candidate_model.AdapterCandidateFailure) as captured:
        candidate.register_and_freeze(*inputs)
    assert captured.value.code == code


@pytest.mark.parametrize("mutation", ["missing", "mismatch"])
def test_f163_source_binding_removal_or_substitution_is_rejected(mutation):
    inputs = list(make_inputs())
    if mutation == "missing":
        inputs[2]["source_bindings"].pop("f162_gate")
        code = "F163_SOURCE_BINDINGS_REQUIRED"
    else:
        inputs[2]["source_bindings"]["f162_gate"]["sha256"] = "0" * 64
        code = "F163_SOURCE_BINDING_MISMATCH"
    candidate = candidate_model.FutureLiveAdapterCandidate()
    with pytest.raises(candidate_model.AdapterCandidateFailure) as captured:
        candidate.register_and_freeze(*inputs)
    assert captured.value.code == code


@pytest.mark.parametrize(
    ("authority_key", "value"),
    [
        ("F157_F158_F159_CONSUMPTION_STATE_REUSABLE", True),
        ("F159_RETRY_FORBIDDEN", False),
        ("F163_EXECUTION_AUTHORIZED", True),
    ],
)
def test_f163_authority_contradiction_is_rejected(authority_key, value):
    inputs = list(make_inputs())
    inputs[2]["authority"][authority_key] = value
    candidate = candidate_model.FutureLiveAdapterCandidate()
    with pytest.raises(candidate_model.AdapterCandidateFailure) as captured:
        candidate.register_and_freeze(*inputs)
    assert captured.value.code == "F163_AUTHORITY_FIREWALL_INVALID"


def test_post_freeze_f163_gate_mutation_fails_closed_and_preserves_resources():
    candidate, inputs = make_candidate()
    inputs[2]["status"] = "BLOCKED"
    with pytest.raises(candidate_model.AdapterCandidateFailure) as captured:
        candidate.preparation_state()
    assert captured.value.code == "F163_READINESS_GATE_MUTATED"
    assert candidate.ready is inputs[3]
    assert candidate.result_channel is inputs[4]


@pytest.mark.parametrize("terminal_count", [0, 1])
def test_cleanup_denied_with_live_children_and_resources_preserved(terminal_count):
    candidate, inputs = make_candidate()
    move_plan_to_cleanup(candidate)
    for child in candidate.children[:terminal_count]:
        candidate.record_child_terminal_state(child)
    record_all_quiescent(candidate)
    with pytest.raises(candidate_model.AdapterCandidateFailure) as captured:
        candidate.cleanup_eligibility()
    assert captured.value.code == "LIVE_CHILD_PREVENTS_CLEANUP_ELIGIBILITY"
    assert candidate.ready is inputs[3]
    assert candidate.result_channel is inputs[4]


@pytest.mark.parametrize("quiescent_count", [0, 1])
def test_cleanup_denied_with_active_supervisors(quiescent_count):
    candidate, _inputs = make_candidate()
    move_plan_to_cleanup(candidate)
    record_all_terminal(candidate)
    for supervisor in candidate.startup_supervisors[:quiescent_count]:
        candidate.record_supervisor_quiescent_state(supervisor)
    with pytest.raises(candidate_model.AdapterCandidateFailure) as captured:
        candidate.cleanup_eligibility()
    assert captured.value.code == (
        "ACTIVE_SUPERVISOR_PREVENTS_CLEANUP_ELIGIBILITY"
    )


def test_cleanup_and_release_are_data_only_plans_after_all_predicates():
    candidate, inputs = make_candidate()
    move_plan_to_cleanup(candidate)
    record_all_terminal(candidate)
    record_all_quiescent(candidate)
    eligibility = candidate.cleanup_eligibility()
    assert eligibility["cleanup_action_performed"] is False
    assert eligibility["resources_released"] is False
    plan = candidate.plan_release_after_cleanup()
    assert plan["to"] == "RELEASED"
    assert plan["cleanup_action_performed"] is False
    assert plan["resources_released"] is False
    assert candidate.planned_phase == "RELEASED"
    assert candidate.ready is inputs[3]
    assert candidate.result_channel is inputs[4]


def test_authority_state_is_exact_and_non_activating():
    candidate, _inputs = make_candidate()
    assert candidate.authority_state() == {
        "NEW_AUTHORIZATION_REQUIRED": True,
        "SEPARATE_SECURITY_REVIEW_REQUIRED": True,
        "SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED": True,
        "F159_RETRY_FORBIDDEN": True,
        "OLD_AUTHORIZATION_REUSABLE": False,
        "F161_EXECUTION_AUTHORIZED": False,
        "F162_EXECUTION_AUTHORIZED": False,
        "F163_EXECUTION_AUTHORIZED": False,
        "F164_EXECUTION_AUTHORIZED": False,
    }


@pytest.mark.parametrize("terminal_state", terminal_model.TERMINAL_STATES)
def test_four_terminal_states_are_distinct_data_only(terminal_state):
    record = terminal_model.TerminalizationRecord()
    evidence = record.record(terminal_state)
    assert record.state == terminal_state
    assert record.terminal is True
    assert evidence["data_only"] is True
    assert evidence["execution_performed"] is False
    assert evidence["cleanup_performed"] is False
    assert record.execution_authorized is False
    assert len(set(terminal_model.TERMINAL_STATES)) == 4


def test_illegal_and_repeated_terminalization_transitions_are_rejected():
    record = terminal_model.TerminalizationRecord()
    with pytest.raises(terminal_model.TerminalizationFailure) as illegal:
        record.record("UNKNOWN")
    assert illegal.value.code == "ILLEGAL_TERMINAL_STATE"
    record.record(terminal_model.EXECUTION_ABORT)
    with pytest.raises(terminal_model.TerminalizationFailure) as repeated:
        record.record(terminal_model.SUCCESS)
    assert repeated.value.code == "TERMINAL_STATE_ALREADY_RECORDED"
