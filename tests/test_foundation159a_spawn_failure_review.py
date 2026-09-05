# SPDX-License-Identifier: Apache-2.0
import ast
import gc
import hashlib
import json
from pathlib import Path
import weakref


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs/l28_foundation159a_spawn_failure_review_v0.1.json"
HELPER = ROOT / "tests/foundation158_corrected_one_shot_execution_helper.py"
MARKER = ROOT / "docs/l28_foundation158_corrected_one_shot_execution_state_v1.0.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LifetimeToken:
    pass


class OfflineRuntimeBundle:
    def __init__(self, ready, processes):
        self.ready = ready
        self.processes = processes

    def release_after_cleanup(self):
        assert all(process["terminal"] for process in self.processes)
        self.ready = None


def test_machine_operator_and_hypothesis_provenance_are_separate():
    review = load(REVIEW)
    marker = load(MARKER)
    provenance = review["provenance"]
    assert provenance["persisted_machine_evidence"]["result"] == marker["result"]
    assert provenance["persisted_machine_evidence"]["controller_execution_error"] == marker["execution_error"]
    assert provenance["operator_observed_execution_output"]["classification"] == "OPERATOR_OBSERVED_NOT_MACHINE_PERSISTED"
    assert provenance["raw_stderr_retained_or_hash_bound"] is False
    assert provenance["machine_proves_no_retry_attempted"] is False
    assert review["root_cause_assessment"]["status"] == "NOT_PROVEN"
    assert review["root_cause_assessment"]["deeper_os_or_multiprocessing_root_cause_claimed"] is False


def test_authoritative_marker_and_historical_helper_are_hash_bound_unchanged():
    bindings = load(REVIEW)["bindings"]
    assert bindings["f158_helper_sha256"] == sha256(HELPER)
    assert bindings["authoritative_consumption_marker_sha256"] == sha256(MARKER)


def test_current_helper_does_not_return_the_local_ready_reference():
    source = HELPER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_build_process_bundle_bounded"
    )
    assert 'ready = ctx.Event()' in source
    assert "values.append((results, processes))" in source
    returns = [node for node in ast.walk(function) if isinstance(node, ast.Return)]
    assert any(ast.unparse(node.value) == "values[0]" for node in returns)
    lifetime = load(REVIEW)["synchronization_lifetime"]
    assert lifetime["current_f158_helper_parent_retains_ready_in_returned_bundle"] is False
    assert lifetime["historical_f158_helper_modified"] is False


def test_offline_bundle_retains_ready_through_bootstrap_active_and_cleanup():
    ready = LifetimeToken()
    reference = weakref.ref(ready)
    processes = [
        {"args": [ready], "terminal": False},
        {"args": [ready], "terminal": False},
    ]
    bundle = OfflineRuntimeBundle(ready, processes)
    del ready
    phases = load(REVIEW)["synchronization_lifetime"]["required_retention_phases"]
    assert phases == [
        "PROCESS_OBJECT_CONSTRUCTION",
        "PROCESS_START_SUPERVISION",
        "CHILD_BOOTSTRAP_WINDOW",
        "ACTIVE_EXECUTION",
        "CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL",
    ]
    for phase in phases:
        if phase == "PROCESS_START_SUPERVISION":
            for process in processes:
                process["args"].clear()
        if phase == "CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL":
            for process in processes:
                process["terminal"] = True
        gc.collect()
        assert reference() is bundle.ready

    bundle.release_after_cleanup()
    gc.collect()
    assert reference() is None


def test_release_before_every_child_is_terminal_fails_closed():
    ready = LifetimeToken()
    bundle = OfflineRuntimeBundle(
        ready,
        [{"terminal": True}, {"terminal": False}],
    )
    try:
        bundle.release_after_cleanup()
    except AssertionError:
        pass
    else:
        raise AssertionError("ready released before all children were terminal")
    assert bundle.ready is ready


def test_future_authority_requirements_are_explicit_and_nonreusable():
    requirements = load(REVIEW)["future_authority_requirements"]
    assert requirements == {
        "NEW_AUTHORIZATION_REQUIRED": True,
        "SEPARATE_SECURITY_REVIEW_REQUIRED": True,
        "SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED": True,
        "F159_RETRY_FORBIDDEN": True,
        "F157_F158_F159_CONSUMPTION_STATE_REUSABLE": False,
    }


def test_review_is_offline_and_adds_no_execution_capability():
    boundary = load(REVIEW)["offline_boundary"]
    assert boundary == {
        "NO_EXECUTION_OCCURRED": True,
        "SOCKETS_OPENED": False,
        "PROCESSES_STARTED": False,
        "NETWORK_TRAFFIC_USED": False,
        "AUTHORIZATION_GRANTED": False,
    }
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
            elif isinstance(node.func, ast.Name):
                calls.add(node.func.id)
    assert {"multiprocessing", "socket", "subprocess"}.isdisjoint(imports)
    assert {"start", "connect", "bind", "listen"}.isdisjoint(calls)
