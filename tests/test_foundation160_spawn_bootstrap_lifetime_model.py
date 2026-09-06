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
MODEL_PATH = ROOT / "tests/foundation160_spawn_bootstrap_lifetime_model.py"
TEST_PATH = ROOT / "tests/test_foundation160_spawn_bootstrap_lifetime_model.py"
GATE_PATH = ROOT / "docs/l28_foundation160_spawn_bootstrap_lifetime_gate_v0.1.json"
F159A_REVIEW = ROOT / "docs/l28_foundation159a_spawn_failure_review_v0.1.json"
F158_HELPER = ROOT / "tests/foundation158_corrected_one_shot_execution_helper.py"
F158_MARKER = ROOT / "docs/l28_foundation158_corrected_one_shot_execution_state_v1.0.json"
PROTOCOL = ROOT / "PROTOCOL.md"
VALIDATOR = ROOT / "coin/tx_validation.py"

spec = importlib.util.spec_from_file_location("foundation160_lifetime_model", MODEL_PATH)
model = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(model)


class Token:
    pass


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_bundle():
    ready = Token()
    result_channel = Token()
    children = (
        model.ChildLifecycle("child-a", (ready, result_channel)),
        model.ChildLifecycle("child-b", (ready, result_channel)),
    )
    supervisors = (
        model.StartupSupervisorLifecycle("startup-a"),
        model.StartupSupervisorLifecycle("startup-b"),
    )
    bundle = model.ParentOwnedLifetimeBundle(
        ready,
        result_channel,
        children,
        supervisors,
    )
    references = {
        "ready": weakref.ref(ready),
        "result_channel": weakref.ref(result_channel),
        "child_a": weakref.ref(children[0]),
        "child_b": weakref.ref(children[1]),
        "supervisor_a": weakref.ref(supervisors[0]),
        "supervisor_b": weakref.ref(supervisors[1]),
    }
    return bundle, references


def move_to_cleanup(bundle):
    for phase in model.REQUIRED_PHASES[1:]:
        bundle.transition_to(phase)


def test_parent_bundle_retains_every_resource_across_all_required_phases():
    bundle, references = make_bundle()
    assert bundle.phase == model.REQUIRED_PHASES[0]
    for child in bundle.children:
        child.drop_argument_references()
        assert child.argument_reference_count == 0
    del child
    for phase in model.REQUIRED_PHASES:
        if phase != bundle.phase:
            bundle.transition_to(phase)
        gc.collect()
        assert bundle.ready is references["ready"]()
        assert bundle.result_channel is references["result_channel"]()
        assert tuple(references[key]() for key in ("child_a", "child_b")) == bundle.children
        assert tuple(
            references[key]() for key in ("supervisor_a", "supervisor_b")
        ) == bundle.startup_supervisors


def test_live_child_prevents_release_without_dropping_any_parent_reference():
    bundle, references = make_bundle()
    move_to_cleanup(bundle)
    bundle.children[0].mark_terminal()
    for supervisor in bundle.startup_supervisors:
        supervisor.mark_quiescent()
    del supervisor
    with pytest.raises(model.LifetimeContractError, match="live_child_prevents_release"):
        bundle.release_resources()
    assert bundle.ready is references["ready"]()
    assert bundle.result_channel is references["result_channel"]()
    assert bundle.released is False


def test_active_startup_supervisor_prevents_release_fail_closed():
    bundle, references = make_bundle()
    move_to_cleanup(bundle)
    for child in bundle.children:
        child.mark_terminal()
    del child
    bundle.startup_supervisors[0].mark_quiescent()
    with pytest.raises(
        model.LifetimeContractError,
        match="active_startup_supervisor_prevents_release",
    ):
        bundle.release_resources()
    assert bundle.ready is references["ready"]()
    assert bundle.result_channel is references["result_channel"]()
    assert bundle.released is False


def test_terminal_quiescent_cleanup_releases_all_retained_resources():
    bundle, references = make_bundle()
    move_to_cleanup(bundle)
    for child in bundle.children:
        child.mark_terminal()
    del child
    for supervisor in bundle.startup_supervisors:
        supervisor.mark_quiescent()
    del supervisor
    bundle.release_resources()
    gc.collect()
    assert bundle.released is True
    assert bundle.ready is None
    assert bundle.result_channel is None
    assert bundle.children == ()
    assert bundle.startup_supervisors == ()
    assert all(reference() is None for reference in references.values())
    with pytest.raises(model.LifetimeContractError, match="bundle_already_released"):
        bundle.release_resources()
    with pytest.raises(model.LifetimeContractError, match="bundle_already_released"):
        bundle.transition_to("PROCESS_OBJECT_CONSTRUCTION")


def test_repeated_skipped_backward_and_early_transitions_fail_closed():
    bundle, references = make_bundle()
    with pytest.raises(model.LifetimeContractError, match="invalid_lifecycle_transition"):
        bundle.transition_to("CHILD_BOOTSTRAP_WINDOW")
    with pytest.raises(model.LifetimeContractError, match="cleanup_phase_required"):
        bundle.release_resources()
    bundle.transition_to("PROCESS_START_SUPERVISION")
    with pytest.raises(model.LifetimeContractError, match="invalid_lifecycle_transition"):
        bundle.transition_to("PROCESS_START_SUPERVISION")
    with pytest.raises(model.LifetimeContractError, match="invalid_lifecycle_transition"):
        bundle.transition_to("PROCESS_OBJECT_CONSTRUCTION")
    assert bundle.ready is references["ready"]()
    assert bundle.result_channel is references["result_channel"]()


def test_repeated_child_and_supervisor_state_changes_fail_closed():
    bundle, _references = make_bundle()
    child = bundle.children[0]
    child.drop_argument_references()
    with pytest.raises(
        model.LifetimeContractError,
        match="child_arguments_already_released",
    ):
        child.drop_argument_references()
    child.mark_terminal()
    with pytest.raises(model.LifetimeContractError, match="child_already_terminal"):
        child.mark_terminal()
    supervisor = bundle.startup_supervisors[0]
    supervisor.mark_quiescent()
    with pytest.raises(
        model.LifetimeContractError,
        match="startup_supervisor_already_quiescent",
    ):
        supervisor.mark_quiescent()


def test_historical_hashes_and_f159_classifications_remain_exact():
    gate = load(GATE_PATH)
    history = gate["historical_bindings"]
    assert sha256(F158_HELPER) == history["f158_helper_sha256"]
    assert sha256(F158_MARKER) == history["f158_consumption_marker_sha256"]
    review = load(F159A_REVIEW)
    assert review["foundation159_result"] == "ABORT"
    assert review["provenance"]["operator_observed_execution_output"]["classification"] == "OPERATOR_OBSERVED_NOT_MACHINE_PERSISTED"
    assert review["root_cause_assessment"]["status"] == "NOT_PROVEN"
    assert review["future_authority_requirements"]["F159_RETRY_FORBIDDEN"] is True


def test_protocol_validator_and_protected_boundaries_remain_exact():
    protected = load(GATE_PATH)["protected_boundaries"]
    assert protected["protocol_version"] == "1.0.0"
    assert protected["protocol_sha256"] == sha256(PROTOCOL)
    assert protected["canonical_validator"] == "coin.tx_validation.validate_transaction"
    assert protected["tx_validation_sha256"] == sha256(VALIDATOR)
    assert protected["economic_history_or_consensus_changed"] is False
    assert protected["bitcoin_authority_changed"] is False
    assert protected["signer_authority_changed"] is False
    assert protected["f37_status_changed"] is False


def test_future_authority_requirements_remain_explicit_and_nonreusable():
    requirements = load(GATE_PATH)["future_authority_requirements"]
    assert requirements == {
        "NEW_AUTHORIZATION_REQUIRED": True,
        "SEPARATE_SECURITY_REVIEW_REQUIRED": True,
        "SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED": True,
        "F159_RETRY_FORBIDDEN": True,
        "F157_F158_F159_CONSUMPTION_STATE_REUSABLE": False,
        "F160_EXECUTION_AUTHORIZED": False,
    }
    assert model.AUTHORIZATION_GRANTED is False
    assert model.EXECUTION_CAPABILITY_ADDED is False


def test_new_python_files_obey_offline_capability_firewall():
    forbidden_imports = {"multiprocessing", "socket", "subprocess", "threading", "asyncio"}
    forbidden_calls = {
        "start",
        "connect",
        "bind",
        "listen",
        "accept",
        "send",
        "recv",
        "Popen",
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
