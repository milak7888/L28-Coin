# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_PATH = ROOT / "tests/foundation163_live_adapter_resource_contract.py"
EVALUATOR_PATH = ROOT / "tests/foundation163_live_adapter_readiness_evaluator.py"
RESOURCE_TEST_PATH = ROOT / "tests/test_foundation163_live_adapter_resource_contract.py"
EVALUATOR_TEST_PATH = ROOT / "tests/test_foundation163_live_adapter_readiness_evaluator.py"
GATE_PATH = ROOT / "docs/l28_foundation163_live_adapter_implementation_readiness_gate_v0.1.json"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


resource_model = load_module("foundation163_resource", RESOURCE_PATH)
evaluator = load_module("foundation163_evaluator", EVALUATOR_PATH)
boundary_model = load_module(
    "foundation162_boundary",
    ROOT / "tests/foundation162_future_live_adapter_boundary.py",
)
f161_model = load_module(
    "foundation161_lifecycle",
    ROOT / "tests/foundation161_future_runtime_lifecycle_helper.py",
)


class Token:
    pass


def make_contract():
    ready = Token()
    result_channel = Token()
    children = (Token(), Token())
    supervisors = (Token(), Token())
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
    contract = resource_model.LiveAdapterResourceContract()
    contract.register_and_freeze(
        boundary,
        owner,
        ready,
        result_channel,
        children,
        supervisors,
        resource_model.bounded_deadline_descriptor(),
    )
    return contract


def valid_state():
    return {
        "resource_contract": make_contract(),
        "resource_provenance_valid": True,
        "parent_ownership_valid": True,
        "lifecycle_phases": evaluator.LIFECYCLE_PHASES,
        "startup_preconditions_valid": True,
        "bootstrap_retention_valid": True,
        "single_deadline_required": True,
        "deadline_coverage": evaluator.DEADLINE_COVERAGE,
        "failure_preserves_parent_ownership": True,
        "cleanup_contract_valid": True,
        "terminal_states": evaluator.TERMINAL_STATES,
        "authority": dict(evaluator.REQUIRED_AUTHORITY),
        "protected_authority": {
            key: False for key in evaluator.PROTECTED_AUTHORITY_KEYS
        },
        "protocol_hash_valid": True,
        "validator_hash_valid": True,
        "capability_firewall_valid": True,
        "source_bindings": {"F160": True, "F161": True, "F162": True},
        "f158_hashes_valid": True,
        "historical_state_valid": True,
    }


def evaluate_with(mutator=None):
    state = valid_state()
    if mutator:
        mutator(state)
    return evaluator.evaluate_live_adapter_readiness(state)


def test_fully_valid_state_is_ready_for_implementation_review_only():
    result = evaluate_with()
    assert result["status"] == evaluator.READY
    assert result["implementation_review_ready"] is True
    assert result["execution_authorized"] is False
    assert result["runtime_authorized"] is False
    assert result["testnet_authorized"] is False
    assert result["production_ready"] is False
    assert set(result["dimensions"]) == set(evaluator.DIMENSIONS)
    assert set(item["result"] for item in result["dimensions"].values()) == {
        "PASS"
    }


@pytest.mark.parametrize("malformed_state", [None, (), "invalid"])
def test_malformed_evaluator_input_is_deterministically_blocked(malformed_state):
    result = evaluator.evaluate_live_adapter_readiness(malformed_state)
    assert result["status"] == evaluator.BLOCKED
    assert result["execution_authorized"] is False


@pytest.mark.parametrize("binding", ["F160", "F161", "F162"])
def test_missing_source_binding_is_not_ready(binding):
    def remove(state):
        state["source_bindings"].pop(binding)

    result = evaluate_with(remove)
    assert result["status"] == evaluator.NOT_READY
    assert result["dimensions"]["L_HISTORICAL_PRESERVATION"]["result"] == (
        evaluator.NOT_READY
    )


@pytest.mark.parametrize(
    ("key", "dimension"),
    [
        ("resource_provenance_valid", "A_RESOURCE_PROVENANCE"),
        ("parent_ownership_valid", "B_PARENT_OWNERSHIP"),
        ("startup_preconditions_valid", "D_STARTUP_PRECONDITIONS"),
        ("bootstrap_retention_valid", "E_BOOTSTRAP_RETENTION"),
        ("failure_preserves_parent_ownership", "G_FAILURE_PROPAGATION"),
        ("cleanup_contract_valid", "H_CLEANUP_TERMINALIZATION"),
    ],
)
def test_design_contract_failure_is_not_ready(key, dimension):
    result = evaluate_with(lambda state: state.__setitem__(key, False))
    assert result["status"] == evaluator.NOT_READY
    assert result["dimensions"][dimension]["result"] == evaluator.NOT_READY


def test_lifecycle_ordering_failure_is_not_ready():
    result = evaluate_with(
        lambda state: state.__setitem__(
            "lifecycle_phases",
            tuple(reversed(evaluator.LIFECYCLE_PHASES)),
        )
    )
    assert result["status"] == evaluator.NOT_READY


def test_incomplete_deadline_coverage_is_not_ready():
    result = evaluate_with(
        lambda state: state.__setitem__(
            "deadline_coverage",
            evaluator.DEADLINE_COVERAGE[:-1],
        )
    )
    assert result["status"] == evaluator.NOT_READY


def test_tampered_resource_contract_deadline_is_not_ready():
    def tamper(state):
        state["resource_contract"]._deadline_descriptor = ("UNBOUNDED",)

    result = evaluate_with(tamper)
    assert result["status"] == evaluator.NOT_READY
    assert result["dimensions"]["F_DEADLINE_COVERAGE"]["result"] == (
        evaluator.NOT_READY
    )


def test_collapsed_terminal_states_are_not_ready():
    result = evaluate_with(
        lambda state: state.__setitem__(
            "terminal_states",
            ("SUCCESS", "SUCCESS", "CLEANUP_FAILURE", "TERMINALIZATION_FAILURE"),
        )
    )
    assert result["status"] == evaluator.NOT_READY


@pytest.mark.parametrize(
    ("authority_key", "invalid_value"),
    [
        ("F157_F158_F159_CONSUMPTION_STATE_REUSABLE", True),
        ("F159_RETRY_FORBIDDEN", False),
        ("F161_EXECUTION_AUTHORIZED", True),
        ("F162_EXECUTION_AUTHORIZED", True),
        ("F163_EXECUTION_AUTHORIZED", True),
    ],
)
def test_authority_contradictions_are_blocked(authority_key, invalid_value):
    def contradict(state):
        state["authority"][authority_key] = invalid_value

    result = evaluate_with(contradict)
    assert result["status"] == evaluator.BLOCKED
    assert result["dimensions"]["I_AUTHORIZATION_SEPARATION"]["result"] == (
        evaluator.BLOCKED
    )
    assert result["execution_authorized"] is False


@pytest.mark.parametrize("hash_key", ["protocol_hash_valid", "validator_hash_valid"])
def test_protocol_or_validator_hash_mismatch_is_blocked(hash_key):
    result = evaluate_with(lambda state: state.__setitem__(hash_key, False))
    assert result["status"] == evaluator.BLOCKED
    assert result["dimensions"]["J_PROTOCOL_AUTHORITY_FIREWALL"]["result"] == (
        evaluator.BLOCKED
    )


def test_historical_f158_hash_mismatch_is_blocked():
    result = evaluate_with(
        lambda state: state.__setitem__("f158_hashes_valid", False)
    )
    assert result["status"] == evaluator.BLOCKED


def test_capability_firewall_violation_is_blocked():
    result = evaluate_with(
        lambda state: state.__setitem__("capability_firewall_valid", False)
    )
    assert result["status"] == evaluator.BLOCKED
    assert result["dimensions"]["K_CAPABILITY_FIREWALL"]["result"] == (
        evaluator.BLOCKED
    )


@pytest.mark.parametrize("authority", ["issuance", "supply", "height", "consensus"])
def test_protected_authority_introduction_is_blocked(authority):
    def introduce(state):
        state["protected_authority"][authority] = True

    result = evaluate_with(introduce)
    assert result["status"] == evaluator.BLOCKED


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_source_bindings_and_historical_state_are_exact():
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


def test_gate_readiness_dimensions_and_authority_are_exact():
    gate = load_json(GATE_PATH)
    valid_result = evaluator.evaluate_live_adapter_readiness(valid_state())
    assert set(gate["readiness_dimensions"]) == set(evaluator.DIMENSIONS)
    assert gate["readiness_dimensions"] == valid_result["dimensions"]
    assert gate["status"] == valid_result["status"]
    assert gate["implementation_readiness"] == {
        "READY_FOR_FUTURE_LIVE_ADAPTER_IMPLEMENTATION_REVIEW": True,
        "EXECUTION_AUTHORIZED": False,
        "RUNTIME_AUTHORIZED": False,
        "TESTNET_AUTHORIZED": False,
        "PRODUCTION_READY": False,
    }
    assert gate["authority"] == evaluator.REQUIRED_AUTHORITY


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


def test_all_new_python_files_obey_capability_firewall():
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
        "ctypes",
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
    for path in (
        RESOURCE_PATH,
        EVALUATOR_PATH,
        RESOURCE_TEST_PATH,
        EVALUATOR_TEST_PATH,
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        calls = set()
        dynamic_imports = set()
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
                    if node.func.id in {"__import__", "eval"}:
                        dynamic_imports.add(node.func.id)
        assert forbidden_imports.isdisjoint(imports)
        assert forbidden_calls.isdisjoint(calls)
        assert not dynamic_imports


def test_offline_and_protected_authority_boundaries_are_exact():
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
