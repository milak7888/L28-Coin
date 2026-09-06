# SPDX-License-Identifier: Apache-2.0
import ast
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import weakref

import pytest


ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "tests/foundation161_future_runtime_lifecycle_helper.py"
TEST_PATH = ROOT / "tests/test_foundation161_future_runtime_lifecycle_helper.py"
GATE_PATH = ROOT / "docs/l28_foundation161_future_runtime_lifecycle_gate_v0.1.json"
F160_MODEL = ROOT / "tests/foundation160_spawn_bootstrap_lifetime_model.py"
F160_GATE = ROOT / "docs/l28_foundation160_spawn_bootstrap_lifetime_gate_v0.1.json"
F159A_GATE = ROOT / "docs/l28_foundation159a_spawn_failure_review_v0.1.json"
F158_HELPER = ROOT / "tests/foundation158_corrected_one_shot_execution_helper.py"
F158_MARKER = ROOT / "docs/l28_foundation158_corrected_one_shot_execution_state_v1.0.json"
PROTOCOL = ROOT / "PROTOCOL.md"
VALIDATOR = ROOT / "coin/tx_validation.py"

spec = importlib.util.spec_from_file_location("foundation161_lifecycle", HELPER_PATH)
lifecycle = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(lifecycle)


class Token:
    pass


class LookalikeToken:
    def __eq__(self, _other):
        return True


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_helper(child_count=2, supervisor_count=2):
    ready = Token()
    result_channel = Token()
    children = tuple(Token() for _ in range(child_count))
    supervisors = tuple(Token() for _ in range(supervisor_count))
    helper = lifecycle.FutureRuntimeLifecycleHelper(
        ready,
        result_channel,
        children,
        supervisors,
    )
    references = {
        "ready": weakref.ref(ready),
        "result_channel": weakref.ref(result_channel),
        "children": tuple(weakref.ref(child) for child in children),
        "supervisors": tuple(weakref.ref(item) for item in supervisors),
    }
    return helper, references


def move_to_cleanup(helper):
    for phase in lifecycle.F160_REQUIRED_PHASES[1:]:
        helper.transition_to(phase)


def quiesce_all(helper):
    for supervisor in helper.startup_supervisors:
        helper.mark_supervisor_quiescent(supervisor)


def terminate_all(helper):
    for child in helper.children:
        helper.mark_child_terminal(child)


def assert_owned(helper, references):
    assert helper.ready is references["ready"]()
    assert helper.result_channel is references["result_channel"]()
    assert helper.children == tuple(item() for item in references["children"])
    assert helper.startup_supervisors == tuple(
        item() for item in references["supervisors"]
    )


def test_exact_parent_ownership_and_f160_phase_inheritance():
    helper, references = make_helper()
    gate = load(F160_GATE)
    assert lifecycle.F160_REQUIRED_PHASES == tuple(
        gate["parent_owned_bundle_contract"]["required_phases"]
    )
    assert lifecycle.REQUIRED_PHASES == lifecycle.F160_REQUIRED_PHASES + ("RELEASED",)
    assert_owned(helper, references)


def test_ready_and_result_survive_gc_after_simulated_child_arguments_drop():
    helper, references = make_helper()
    child_argument_references = [helper.ready, helper.result_channel]
    for child in helper.children:
        helper.record_child_arguments_released(child)
    child_argument_references.clear()
    gc.collect()
    assert all(helper.child_arguments_released(child) for child in helper.children)
    assert_owned(helper, references)


def test_ready_and_result_survive_gc_through_every_prerelease_phase():
    helper, references = make_helper()
    for phase in lifecycle.F160_REQUIRED_PHASES:
        if helper.phase != phase:
            helper.transition_to(phase)
        gc.collect()
        assert_owned(helper, references)


def test_release_before_cleanup_fails_closed_and_preserves_all_resources():
    helper, references = make_helper()
    with pytest.raises(lifecycle.LifecycleFailure) as captured:
        helper.release_resources()
    assert captured.value.code == "CLEANUP_PHASE_REQUIRED"
    assert helper.released is False
    assert_owned(helper, references)


@pytest.mark.parametrize("child_count,terminal_count", [(2, 1), (3, 0)])
def test_one_or_multiple_live_children_prevent_release(child_count, terminal_count):
    helper, references = make_helper(child_count=child_count)
    move_to_cleanup(helper)
    for child in helper.children[:terminal_count]:
        helper.mark_child_terminal(child)
    quiesce_all(helper)
    with pytest.raises(lifecycle.LifecycleFailure) as captured:
        helper.release_resources()
    assert captured.value.code == "NONTERMINAL_CHILD_PREVENTS_RELEASE"
    assert_owned(helper, references)


@pytest.mark.parametrize("supervisor_count,quiescent_count", [(2, 1), (3, 0)])
def test_one_or_multiple_active_supervisors_prevent_release(
    supervisor_count, quiescent_count
):
    helper, references = make_helper(supervisor_count=supervisor_count)
    move_to_cleanup(helper)
    terminate_all(helper)
    for supervisor in helper.startup_supervisors[:quiescent_count]:
        helper.mark_supervisor_quiescent(supervisor)
    with pytest.raises(lifecycle.LifecycleFailure) as captured:
        helper.release_resources()
    assert captured.value.code == "ACTIVE_SUPERVISOR_PREVENTS_RELEASE"
    assert_owned(helper, references)


def test_terminal_quiescent_release_clears_all_resources_together():
    helper, references = make_helper()
    move_to_cleanup(helper)
    terminate_all(helper)
    quiesce_all(helper)
    helper.release_resources()
    gc.collect()
    assert helper.phase == "RELEASED"
    assert helper.released is True
    assert helper.ready is None
    assert helper.result_channel is None
    assert helper.children == ()
    assert helper.startup_supervisors == ()
    assert references["ready"]() is None
    assert references["result_channel"]() is None
    assert all(item() is None for item in references["children"])
    assert all(item() is None for item in references["supervisors"])


def test_unknown_child_and_supervisor_operations_fail_closed():
    helper, references = make_helper()
    with pytest.raises(lifecycle.LifecycleFailure) as child_error:
        helper.mark_child_terminal(Token())
    with pytest.raises(lifecycle.LifecycleFailure) as supervisor_error:
        helper.mark_supervisor_quiescent(Token())
    assert child_error.value.code == "UNKNOWN_CHILD_REFERENCE"
    assert supervisor_error.value.code == "UNKNOWN_SUPERVISOR_REFERENCE"
    assert_owned(helper, references)


def test_lookalike_and_replacement_resources_are_rejected_by_identity():
    helper, references = make_helper()
    lookalike = LookalikeToken()
    with pytest.raises(lifecycle.LifecycleFailure, match="UNKNOWN_CHILD_REFERENCE"):
        helper.record_child_arguments_released(lookalike)
    with pytest.raises(AttributeError):
        helper.children = (lookalike,)
    with pytest.raises(AttributeError):
        helper.startup_supervisors = (lookalike,)
    assert_owned(helper, references)


def test_duplicate_child_and_supervisor_registration_fails_closed():
    ready = Token()
    result_channel = Token()
    child = Token()
    supervisor = Token()
    with pytest.raises(lifecycle.LifecycleFailure) as child_error:
        lifecycle.FutureRuntimeLifecycleHelper(
            ready, result_channel, (child, child), (supervisor,)
        )
    with pytest.raises(lifecycle.LifecycleFailure) as supervisor_error:
        lifecycle.FutureRuntimeLifecycleHelper(
            ready, result_channel, (child,), (supervisor, supervisor)
        )
    assert child_error.value.code == "DUPLICATE_CHILD_REGISTRATION"
    assert supervisor_error.value.code == "DUPLICATE_SUPERVISOR_REGISTRATION"


@pytest.mark.parametrize("colliding_role", ["ready", "result", "child"])
def test_cross_role_identity_collision_fails_closed(colliding_role):
    ready = Token()
    result_channel = Token()
    child = Token()
    supervisor = Token()
    if colliding_role == "ready":
        child = ready
    elif colliding_role == "result":
        supervisor = result_channel
    else:
        supervisor = child
    with pytest.raises(lifecycle.LifecycleFailure) as captured:
        lifecycle.FutureRuntimeLifecycleHelper(
            ready, result_channel, (child,), (supervisor,)
        )
    assert captured.value.code == "RESOURCE_ROLE_COLLISION"


@pytest.mark.parametrize(
    ("ready", "result_channel", "children", "supervisors", "code"),
    [
        (None, Token(), (Token(),), (Token(),), "READY_REFERENCE_REQUIRED"),
        (Token(), None, (Token(),), (Token(),), "RESULT_CHANNEL_REFERENCE_REQUIRED"),
        (Token(), Token(), (), (Token(),), "EXACT_CHILD_COLLECTION_REQUIRED"),
        (Token(), Token(), (Token(),), (), "EXACT_SUPERVISOR_COLLECTION_REQUIRED"),
        (Token(), Token(), [Token()], (Token(),), "EXACT_CHILD_COLLECTION_REQUIRED"),
        (Token(), Token(), (Token(),), [Token()], "EXACT_SUPERVISOR_COLLECTION_REQUIRED"),
        (Token(), Token(), (None,), (Token(),), "INVALID_CHILD_REFERENCE"),
        (Token(), Token(), (Token(),), (None,), "INVALID_SUPERVISOR_REFERENCE"),
    ],
)
def test_empty_or_invalid_resource_collections_fail_closed(
    ready, result_channel, children, supervisors, code
):
    with pytest.raises(lifecycle.LifecycleFailure) as captured:
        lifecycle.FutureRuntimeLifecycleHelper(
            ready,
            result_channel,
            children,
            supervisors,
        )
    assert captured.value.code == code


def test_skipped_backward_repeated_and_released_transitions_fail_closed():
    helper, _references = make_helper()
    with pytest.raises(lifecycle.LifecycleFailure) as skipped:
        helper.transition_to("CHILD_BOOTSTRAP_WINDOW")
    assert skipped.value.code == "INVALID_LIFECYCLE_TRANSITION"
    helper.transition_to("PROCESS_START_SUPERVISION")
    for invalid in ("PROCESS_START_SUPERVISION", "PROCESS_OBJECT_CONSTRUCTION"):
        with pytest.raises(lifecycle.LifecycleFailure) as captured:
            helper.transition_to(invalid)
        assert captured.value.code == "INVALID_LIFECYCLE_TRANSITION"
    helper.transition_to("CHILD_BOOTSTRAP_WINDOW")
    helper.transition_to("ACTIVE_EXECUTION")
    helper.transition_to("CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL")
    with pytest.raises(lifecycle.LifecycleFailure) as direct_release_phase:
        helper.transition_to("RELEASED")
    assert direct_release_phase.value.code == "RELEASE_OPERATION_REQUIRED"
    terminate_all(helper)
    quiesce_all(helper)
    child = helper.children[0]
    helper.release_resources()
    with pytest.raises(lifecycle.LifecycleFailure) as after_release:
        helper.mark_child_terminal(child)
    assert after_release.value.code == "LIFECYCLE_ALREADY_RELEASED"


def test_repeated_child_and_supervisor_mutations_fail_closed():
    helper, _references = make_helper()
    child = helper.children[0]
    supervisor = helper.startup_supervisors[0]
    helper.record_child_arguments_released(child)
    helper.mark_child_terminal(child)
    helper.mark_supervisor_quiescent(supervisor)
    operations = (
        (helper.record_child_arguments_released, child, "CHILD_ARGUMENT_RELEASE_ALREADY_RECORDED"),
        (helper.mark_child_terminal, child, "CHILD_ALREADY_TERMINAL"),
        (helper.mark_supervisor_quiescent, supervisor, "SUPERVISOR_ALREADY_QUIESCENT"),
    )
    for operation, resource, code in operations:
        with pytest.raises(lifecycle.LifecycleFailure) as captured:
            operation(resource)
        assert captured.value.code == code


def test_historical_f158_f160_and_f159_classifications_are_exact():
    gate = load(GATE_PATH)
    bindings = gate["source_bindings"]
    assert sha256(F158_HELPER) == bindings["f158_helper_sha256"]
    assert sha256(F158_MARKER) == bindings["f158_consumption_marker_sha256"]
    assert sha256(F160_MODEL) == bindings["f160_model_sha256"]
    assert sha256(F160_GATE) == bindings["f160_gate_sha256"]
    review = load(F159A_GATE)
    assert gate["F159_RESULT"] == review["foundation159_result"] == "ABORT"
    assert gate["ROOT_CAUSE_STATUS"] == review["root_cause_assessment"]["status"] == "NOT_PROVEN"
    assert gate["SEMLOCK_EVIDENCE_CLASSIFICATION"] == review["provenance"]["operator_observed_execution_output"]["classification"]


def test_future_authority_and_protected_boundaries_are_exact():
    gate = load(GATE_PATH)
    assert gate["authority"] == {
        "NEW_AUTHORIZATION_REQUIRED": True,
        "SEPARATE_SECURITY_REVIEW_REQUIRED": True,
        "SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED": True,
        "F159_RETRY_FORBIDDEN": True,
        "F157_F158_F159_CONSUMPTION_STATE_REUSABLE": False,
        "F161_EXECUTION_AUTHORIZED": False,
    }
    assert lifecycle.AUTHORIZATION_GRANTED is False
    assert lifecycle.AUTHORIZATION_CONSUMED is False
    assert lifecycle.EXECUTION_CAPABILITY_ADDED is False
    assert set(gate["protected_authority"].values()) == {False}
    assert gate["protected_invariants"]["protocol_sha256"] == sha256(PROTOCOL)
    assert gate["protected_invariants"]["tx_validation_sha256"] == sha256(VALIDATOR)


def test_gate_json_has_no_duplicate_keys():
    def reject(pairs):
        result = {}
        for key, value in pairs:
            assert key not in result, key
            result[key] = value
        return result

    json.loads(GATE_PATH.read_text(encoding="utf-8"), object_pairs_hook=reject)


def test_new_python_files_obey_capability_firewall():
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
        "Popen",
        "system",
        "exec",
        "terminate",
        "kill",
        "run_authorized_experiment_once",
    }
    for path in (HELPER_PATH, TEST_PATH):
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
    assert load(GATE_PATH)["offline_boundary"] == {
        "NO_EXECUTION_OCCURRED": True,
        "SOCKETS_OPENED": False,
        "PROCESSES_STARTED": False,
        "THREADS_STARTED": False,
        "NETWORK_TRAFFIC_USED": False,
        "AUTHORIZATION_GRANTED": False,
        "AUTHORIZATION_CONSUMED": False,
    }
