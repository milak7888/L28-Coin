# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "tests/foundation162_future_live_adapter_boundary.py"
TEST_PATH = ROOT / "tests/test_foundation162_future_live_adapter_boundary.py"
GATE_PATH = ROOT / "docs/l28_foundation162_future_live_adapter_security_gate_v0.1.json"
F161_HELPER_PATH = ROOT / "tests/foundation161_future_runtime_lifecycle_helper.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


boundary_model = load_module("foundation162_boundary", MODEL_PATH)
f161_model = load_module("foundation161_lifecycle", F161_HELPER_PATH)


class Token:
    pass


class LookalikeToken:
    def __eq__(self, _other):
        return True


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def make_resources(child_count=2, supervisor_count=2):
    ready = Token()
    result_channel = Token()
    children = tuple(Token() for _ in range(child_count))
    supervisors = tuple(Token() for _ in range(supervisor_count))
    helper = f161_model.FutureRuntimeLifecycleHelper(
        ready,
        result_channel,
        children,
        supervisors,
    )
    return helper, ready, result_channel, children, supervisors


def make_registered_boundary(child_count=2, supervisor_count=2):
    resources = make_resources(child_count, supervisor_count)
    boundary = boundary_model.FutureLiveAdapterBoundary()
    boundary.register_parent_owned_resources(*resources)
    return boundary, resources


def move_to_cleanup(boundary):
    for phase in boundary_model.LIFECYCLE_PHASES[1:-1]:
        boundary.transition_to(phase)


def mark_all_terminal(boundary):
    for child in boundary.children:
        boundary.mark_child_terminal(child)


def mark_all_quiescent(boundary):
    for supervisor in boundary.startup_supervisors:
        boundary.mark_supervisor_quiescent(supervisor)


def test_complete_exact_resource_registration_is_accepted_and_frozen():
    boundary, resources = make_registered_boundary()
    helper, ready, result_channel, children, supervisors = resources
    assert boundary.lifecycle_helper is helper
    assert boundary.ready is ready
    assert boundary.result_channel is result_channel
    assert all(a is b for a, b in zip(boundary.children, children, strict=True))
    assert all(
        a is b
        for a, b in zip(boundary.startup_supervisors, supervisors, strict=True)
    )
    assert boundary.registered is True
    assert boundary.resource_set_frozen is True
    assert boundary.provenance_verified is True


def test_hypothetical_eligibility_is_false_before_complete_registration():
    boundary = boundary_model.FutureLiveAdapterBoundary()
    assert boundary.hypothetical_start_eligible is False
    assert boundary.execution_authorized is False


@pytest.mark.parametrize(
    ("index", "replacement", "code"),
    [
        (0, None, "F161_PARENT_OWNERSHIP_REQUIRED"),
        (1, None, "READY_REFERENCE_REQUIRED"),
        (2, None, "RESULT_CHANNEL_REFERENCE_REQUIRED"),
        (3, (), "EXACT_CHILD_COLLECTION_REQUIRED"),
        (4, (), "EXACT_SUPERVISOR_COLLECTION_REQUIRED"),
    ],
)
def test_missing_required_resources_fail_closed(index, replacement, code):
    resources = list(make_resources())
    resources[index] = replacement
    boundary = boundary_model.FutureLiveAdapterBoundary()
    with pytest.raises(boundary_model.AdapterBoundaryFailure) as captured:
        boundary.register_parent_owned_resources(*resources)
    assert captured.value.code == code
    assert boundary.registered is False
    assert boundary.resource_set_frozen is False


@pytest.mark.parametrize(
    "collision",
    [
        "ready_child",
        "result_supervisor",
        "cross_role",
        "repeated_child",
        "repeated_supervisor",
    ],
)
def test_duplicate_resource_identity_is_rejected(collision):
    helper, ready, result_channel, children, supervisors = make_resources()
    supplied_children = children
    supplied_supervisors = supervisors
    if collision == "ready_child":
        supplied_children = (ready, children[1])
    elif collision == "result_supervisor":
        supplied_supervisors = (result_channel, supervisors[1])
    elif collision == "cross_role":
        supplied_supervisors = (children[0], supervisors[1])
    elif collision == "repeated_child":
        supplied_children = (children[0], children[0])
    else:
        supplied_supervisors = (supervisors[0], supervisors[0])
    boundary = boundary_model.FutureLiveAdapterBoundary()
    with pytest.raises(boundary_model.AdapterBoundaryFailure) as captured:
        boundary.register_parent_owned_resources(
            helper,
            ready,
            result_channel,
            supplied_children,
            supplied_supervisors,
        )
    assert captured.value.code == "DUPLICATE_RESOURCE_IDENTITY"


@pytest.mark.parametrize(
    ("resource_index", "replacement", "code"),
    [
        (3, (None,), "INVALID_CHILD_REFERENCE"),
        (4, (None,), "INVALID_SUPERVISOR_REFERENCE"),
        (3, [Token()], "EXACT_CHILD_COLLECTION_REQUIRED"),
        (4, [Token()], "EXACT_SUPERVISOR_COLLECTION_REQUIRED"),
    ],
)
def test_invalid_resource_collections_fail_closed(resource_index, replacement, code):
    resources = list(make_resources())
    resources[resource_index] = replacement
    boundary = boundary_model.FutureLiveAdapterBoundary()
    with pytest.raises(boundary_model.AdapterBoundaryFailure) as captured:
        boundary.register_parent_owned_resources(*resources)
    assert captured.value.code == code
    assert boundary.registered is False


@pytest.mark.parametrize(
    ("resource_index", "code"),
    [
        (1, "READY_PROVENANCE_MISMATCH"),
        (2, "RESULT_CHANNEL_PROVENANCE_MISMATCH"),
        (3, "CHILD_PROVENANCE_MISMATCH"),
        (4, "SUPERVISOR_PROVENANCE_MISMATCH"),
    ],
)
def test_replacement_and_lookalike_resources_are_rejected(resource_index, code):
    resources = list(make_resources())
    if resource_index in (1, 2):
        resources[resource_index] = LookalikeToken()
    else:
        sequence = list(resources[resource_index])
        sequence[0] = LookalikeToken()
        resources[resource_index] = tuple(sequence)
    boundary = boundary_model.FutureLiveAdapterBoundary()
    with pytest.raises(boundary_model.AdapterBoundaryFailure) as captured:
        boundary.register_parent_owned_resources(*resources)
    assert captured.value.code == code


@pytest.mark.parametrize(
    "role", ["ready", "result_channel", "child", "startup_supervisor"]
)
def test_mutation_after_freeze_is_rejected_and_ownership_preserved(role):
    boundary, resources = make_registered_boundary()
    with pytest.raises(boundary_model.AdapterBoundaryFailure) as captured:
        boundary.attempt_resource_replacement(role, LookalikeToken())
    assert captured.value.code == "RESOURCE_SET_FROZEN"
    assert boundary.ready is resources[1]
    assert boundary.result_channel is resources[2]
    assert boundary.children == resources[3]
    assert boundary.startup_supervisors == resources[4]


def test_repeated_registration_is_rejected():
    boundary, resources = make_registered_boundary()
    with pytest.raises(boundary_model.AdapterBoundaryFailure) as captured:
        boundary.register_parent_owned_resources(*resources)
    assert captured.value.code == "RESOURCE_SET_ALREADY_FROZEN"


def test_f161_parent_ownership_must_be_active_at_construction_phase():
    resources = make_resources()
    resources[0].transition_to("PROCESS_START_SUPERVISION")
    boundary = boundary_model.FutureLiveAdapterBoundary()
    with pytest.raises(boundary_model.AdapterBoundaryFailure) as captured:
        boundary.register_parent_owned_resources(*resources)
    assert captured.value.code == "F161_CONSTRUCTION_PHASE_REQUIRED"


def test_incomplete_helper_interface_fails_with_deterministic_code():
    class IncompleteHelper:
        released = False
        phase = "PROCESS_OBJECT_CONSTRUCTION"

    _helper, ready, result_channel, children, supervisors = make_resources()
    boundary = boundary_model.FutureLiveAdapterBoundary()
    with pytest.raises(boundary_model.AdapterBoundaryFailure) as captured:
        boundary.register_parent_owned_resources(
            IncompleteHelper(),
            ready,
            result_channel,
            children,
            supervisors,
        )
    assert captured.value.code == "F161_LIFECYCLE_INTERFACE_REQUIRED"
    assert boundary.registered is False


def test_hypothetical_eligibility_never_equals_execution_authority():
    boundary, _resources = make_registered_boundary()
    assert boundary.hypothetical_start_eligible is True
    assert boundary.execution_authorized is False
    assert boundary_model.F161_EXECUTION_AUTHORIZED is False
    assert boundary_model.F162_EXECUTION_AUTHORIZED is False


def test_lifecycle_mapping_matches_f161_and_advances_in_exact_order():
    boundary, _resources = make_registered_boundary()
    assert boundary_model.LIFECYCLE_PHASES == f161_model.REQUIRED_PHASES
    for phase in boundary_model.LIFECYCLE_PHASES[1:-1]:
        boundary.transition_to(phase)
        assert boundary.phase == phase
    assert boundary.hypothetical_start_eligible is False


def test_skipped_backward_repeated_and_direct_release_transitions_fail_closed():
    boundary, resources = make_registered_boundary()
    helper = resources[0]
    for invalid in (
        "CHILD_BOOTSTRAP_WINDOW",
        "PROCESS_OBJECT_CONSTRUCTION",
        "RELEASED",
    ):
        with pytest.raises(boundary_model.AdapterBoundaryFailure):
            boundary.transition_to(invalid)
        assert helper.ready is resources[1]
        assert helper.result_channel is resources[2]
    boundary.transition_to("PROCESS_START_SUPERVISION")
    with pytest.raises(boundary_model.AdapterBoundaryFailure) as repeated:
        boundary.transition_to("PROCESS_START_SUPERVISION")
    assert repeated.value.code == "INVALID_LIFECYCLE_TRANSITION"


def test_unknown_child_and_supervisor_mutations_fail_closed():
    boundary, resources = make_registered_boundary()
    for operation in (
        boundary.mark_child_terminal,
        boundary.mark_supervisor_quiescent,
    ):
        with pytest.raises(boundary_model.AdapterBoundaryFailure):
            operation(LookalikeToken())
    assert resources[0].ready is resources[1]
    assert resources[0].result_channel is resources[2]


@pytest.mark.parametrize("terminal_count", [0, 1])
def test_release_with_live_children_fails_and_preserves_parent_ownership(
    terminal_count,
):
    boundary, resources = make_registered_boundary()
    move_to_cleanup(boundary)
    for child in boundary.children[:terminal_count]:
        boundary.mark_child_terminal(child)
    mark_all_quiescent(boundary)
    with pytest.raises(f161_model.LifecycleFailure) as captured:
        boundary.release_owned_resources()
    assert captured.value.code == "NONTERMINAL_CHILD_PREVENTS_RELEASE"
    assert resources[0].ready is resources[1]
    assert resources[0].result_channel is resources[2]


@pytest.mark.parametrize("quiescent_count", [0, 1])
def test_release_with_active_supervisors_fails_and_preserves_parent_ownership(
    quiescent_count,
):
    boundary, resources = make_registered_boundary()
    move_to_cleanup(boundary)
    mark_all_terminal(boundary)
    for supervisor in boundary.startup_supervisors[:quiescent_count]:
        boundary.mark_supervisor_quiescent(supervisor)
    with pytest.raises(f161_model.LifecycleFailure) as captured:
        boundary.release_owned_resources()
    assert captured.value.code == "ACTIVE_SUPERVISOR_PREVENTS_RELEASE"
    assert resources[0].ready is resources[1]
    assert resources[0].result_channel is resources[2]


def test_release_requires_all_f161_cleanup_predicates():
    boundary, _resources = make_registered_boundary()
    move_to_cleanup(boundary)
    mark_all_terminal(boundary)
    mark_all_quiescent(boundary)
    boundary.release_owned_resources()
    assert boundary.phase == "RELEASED"
    assert boundary.lifecycle_helper.released is True
    assert boundary.ready is None
    assert boundary.result_channel is None
    assert boundary.children == ()
    assert boundary.startup_supervisors == ()
    assert boundary.resources_released is True
    assert boundary.hypothetical_start_eligible is False
    with pytest.raises(boundary_model.AdapterBoundaryFailure) as captured:
        boundary.transition_to("ACTIVE_EXECUTION")
    assert captured.value.code == "LIFECYCLE_ALREADY_RELEASED"


def test_single_deadline_contract_covers_construction_through_cleanup_initiation():
    boundary = boundary_model.FutureLiveAdapterBoundary()
    assert boundary.deadline_contract() == {
        "single_bounded_deadline_required": True,
        "coverage": (
            "RESOURCE_CONSTRUCTION",
            "STARTUP_SUPERVISION",
            "CHILD_BOOTSTRAP",
            "ACTIVE_WORK",
            "CLEANUP_INITIATION",
        ),
        "timer_implemented": False,
    }


@pytest.mark.parametrize("terminal_state", boundary_model.TERMINAL_STATES)
def test_terminal_states_are_distinct_data_only_values(terminal_state):
    boundary = boundary_model.FutureLiveAdapterBoundary()
    boundary.record_terminal_state(terminal_state)
    assert boundary.terminal_state == terminal_state
    assert len(set(boundary_model.TERMINAL_STATES)) == 4


def test_authorization_firewall_is_exact_and_non_reusable():
    boundary = boundary_model.FutureLiveAdapterBoundary()
    assert boundary.authority_contract() == {
        "NEW_AUTHORIZATION_REQUIRED": True,
        "SEPARATE_SECURITY_REVIEW_REQUIRED": True,
        "SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED": True,
        "F159_RETRY_FORBIDDEN": True,
        "F157_F158_F159_CONSUMPTION_STATE_REUSABLE": False,
        "F161_EXECUTION_AUTHORIZED": False,
        "F162_EXECUTION_AUTHORIZED": False,
    }


def test_historical_source_bindings_and_protected_hashes_are_exact():
    gate = load_json(GATE_PATH)
    for binding in gate["source_bindings"].values():
        assert sha256(ROOT / binding["path"]) == binding["sha256"]
    assert gate["historical_state"] == {
        "F159_RESULT": "ABORT",
        "ROOT_CAUSE": "NOT_PROVEN",
        "SEMLOCK_EVIDENCE_CLASSIFICATION": (
            "OPERATOR_OBSERVED_NOT_MACHINE_PERSISTED"
        ),
        "F159_RETRY_FORBIDDEN": True,
    }
    assert gate["protected_invariants"]["protocol_sha256"] == sha256(
        ROOT / "PROTOCOL.md"
    )
    assert gate["protected_invariants"]["tx_validation_sha256"] == sha256(
        ROOT / "coin/tx_validation.py"
    )


def test_gate_json_has_no_duplicate_keys():
    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            assert key not in result, key
            result[key] = value
        return result

    json.loads(
        GATE_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )


def test_capability_firewall_and_offline_boundary_are_exact():
    forbidden_imports = {
        "multiprocessing",
        "socket",
        "subprocess",
        "threading",
        "asyncio",
        "concurrent",
        "selectors",
        "ssl",
        "http",
        "urllib",
        "requests",
    }
    forbidden_calls = {
        "start",
        "fork",
        "spawn",
        "connect",
        "bind",
        "listen",
        "accept",
        "send",
        "sendall",
        "recv",
        "terminate",
        "kill",
        "Popen",
        "system",
        "exec",
        "run_authorized_experiment_once",
    }
    for path in (MODEL_PATH, TEST_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
                elif isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
        assert forbidden_imports.isdisjoint(imports)
        assert forbidden_calls.isdisjoint(calls)
    gate = load_json(GATE_PATH)
    assert gate["offline_boundary"] == {
        "NO_EXECUTION_OCCURRED": True,
        "PROCESSES_STARTED": False,
        "THREADS_STARTED": False,
        "SOCKETS_OPENED": False,
        "NETWORK_TRAFFIC_USED": False,
        "AUTHORIZATION_GRANTED": False,
        "AUTHORIZATION_CONSUMED": False,
    }
    assert set(gate["protected_authority"].values()) == {False}
