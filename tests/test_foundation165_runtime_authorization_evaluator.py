# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "tests/foundation165_runtime_authorization_package.py"
EVALUATOR_PATH = ROOT / "tests/foundation165_runtime_authorization_evaluator.py"
GATE_PATH = ROOT / "docs/l28_foundation165_runtime_authorization_decision_gate_v0.1.json"
NEW_PYTHON_PATHS = (
    PACKAGE_PATH,
    EVALUATOR_PATH,
    ROOT / "tests/test_foundation165_runtime_authorization_package.py",
    ROOT / "tests/test_foundation165_runtime_authorization_evaluator.py",
)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


package_model = load_module("f165_package_for_evaluator", PACKAGE_PATH)
evaluator = load_module("f165_evaluator", EVALUATOR_PATH)


def test_package_and_evaluator_canonical_constants_are_identical():
    assert evaluator.PROPOSED_EXPERIMENT_ID == package_model.PROPOSED_EXPERIMENT_ID
    assert evaluator.REQUIRED_SOURCE_BINDINGS == package_model.REQUIRED_SOURCE_BINDINGS
    assert evaluator.EXPECTED_SCOPE == package_model.EXPECTED_SCOPE


def package_snapshot():
    package = package_model.RuntimeAuthorizationDecisionPackage()
    package.configure_proposal(
        package_model.PROPOSED_EXPERIMENT_ID,
        package_model.proposed_scope(),
        package_model.required_source_bindings(),
    )
    return package.snapshot()


def valid_evidence():
    return {
        "f164_security_review": {"PASS": 13, "GAP": 0, "BLOCKED": 0},
        "authority": dict(evaluator.EXPECTED_AUTHORITY),
        "single_deadline_contract_complete": True,
        "cleanup_contract_complete": True,
        "terminalization_contract_complete": True,
        "protected_authority": {
            key: False for key in evaluator.PROTECTED_AUTHORITY_KEYS
        },
        "protocol_hash_valid": True,
        "validator_hash_valid": True,
        "capability_firewall_valid": True,
        "historical_f159_state_valid": True,
    }


def evaluate(mutator=None, package_mutator=None):
    snapshot = package_snapshot()
    evidence = valid_evidence()
    if package_mutator:
        package_mutator(snapshot)
    if mutator:
        mutator(evidence)
    return evaluator.evaluate_runtime_authorization_decision(snapshot, evidence)


def test_valid_package_is_ready_for_operator_decision_only():
    result = evaluate()
    assert result["status"] == evaluator.READY
    assert result["ready_for_operator_authorization_decision"] is True
    assert result["authorization_granted"] is False
    assert result["execution_authorized"] is False
    assert result["execution_invocation_present"] is False


@pytest.mark.parametrize("malformed", (None, (), "invalid"))
def test_malformed_inputs_are_blocked(malformed):
    result = evaluator.evaluate_runtime_authorization_decision(malformed, {})
    assert result["status"] == evaluator.BLOCKED
    assert result["authorization_granted"] is False


@pytest.mark.parametrize("foundation", ("F160", "F161", "F162", "F163", "F164"))
def test_missing_each_required_binding_is_blocked(foundation):
    def remove(snapshot):
        snapshot["source_bindings"].pop(foundation)

    result = evaluate(package_mutator=remove)
    assert result["status"] == evaluator.BLOCKED
    assert "MISSING_" + foundation + "_BINDING" in result["reasons"]


def test_f164_review_failure_is_blocked():
    result = evaluate(
        lambda evidence: evidence.__setitem__(
            "f164_security_review", {"PASS": 12, "GAP": 1, "BLOCKED": 0}
        )
    )
    assert result["status"] == evaluator.BLOCKED


def test_scope_or_identity_forgery_is_blocked_without_trusting_caller_assertions():
    def forge_scope(snapshot):
        snapshot["scope"]["agent_count"] = 3

    assert evaluate(package_mutator=forge_scope)["status"] == evaluator.BLOCKED
    assert evaluate(
        package_mutator=lambda snapshot: snapshot.__setitem__(
            "proposed_experiment_id", "L28-F157-CORRECTED-RECONNECT-ONE-SHOT-001"
        )
    )["status"] == evaluator.BLOCKED


def test_binding_forgery_cannot_be_approved_by_parallel_caller_evidence():
    def forge(snapshot):
        snapshot["source_bindings"]["F164"] = "0" * 64

    result = evaluate(package_mutator=forge)
    assert result["status"] == evaluator.BLOCKED
    assert "F164_BINDING_MISMATCH" in result["reasons"]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("F159_RETRY_FORBIDDEN", False),
        ("OLD_AUTHORIZATION_REUSABLE", True),
        ("F165_AUTHORIZATION_GRANTED", True),
        ("F165_EXECUTION_AUTHORIZED", True),
        ("SEPARATE_SECURITY_REVIEW_REQUIRED", False),
        ("SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED", False),
    ],
)
def test_every_authority_contradiction_is_blocked(key, value):
    def contradict(evidence):
        evidence["authority"][key] = value

    result = evaluate(contradict)
    assert result["status"] == evaluator.BLOCKED
    assert result["authorization_granted"] is False
    assert result["execution_authorized"] is False


@pytest.mark.parametrize(
    "key",
    (
        "single_deadline_contract_complete",
        "cleanup_contract_complete",
        "terminalization_contract_complete",
    ),
)
def test_incomplete_deadline_cleanup_or_terminalization_is_blocked(key):
    result = evaluate(lambda evidence: evidence.__setitem__(key, False))
    assert result["status"] == evaluator.BLOCKED


def test_unconfigured_but_noncontradictory_package_is_not_ready():
    result = evaluate(package_mutator=lambda snapshot: snapshot.__setitem__("package_configured", False))
    assert result["status"] == evaluator.NOT_READY


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_gate():
    return json.loads(GATE_PATH.read_text(encoding="utf-8"))


def test_gate_has_no_duplicate_keys_and_all_source_hashes_are_exact():
    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            assert key not in result, key
            result[key] = value
        return result

    gate = json.loads(
        GATE_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )
    for binding in gate["source_bindings"].values():
        assert sha256(ROOT / binding["path"]) == binding["sha256"]
    assert gate["protected_invariants"]["protocol_sha256"] == sha256(ROOT / "PROTOCOL.md")
    assert gate["protected_invariants"]["tx_validation_sha256"] == sha256(ROOT / "coin/tx_validation.py")


def test_gate_records_exact_authority_and_historical_state():
    gate = load_gate()
    assert gate["decision_result"] == evaluator.READY
    assert gate["authority"] == evaluator.EXPECTED_AUTHORITY
    assert gate["historical_state"] == {
        "F159_RESULT": "ABORT",
        "F159_RETRY_FORBIDDEN": True,
        "F159_AUTHORIZATION_REUSABLE": False,
        "ROOT_CAUSE": "NOT_PROVEN",
        "SEMLOCK_EVIDENCE_CLASSIFICATION": "OPERATOR_OBSERVED_NOT_MACHINE_PERSISTED",
    }
    assert set(gate["protected_authority"].values()) == {False}
    assert set(gate["offline_boundary"].values()) == {False, True}
    assert gate["offline_boundary"]["NO_ACTIVITY_OCCURRED"] is True
    assert gate["proposed_state"] == {
        "authorization_granted": False,
        "execution_authorized": False,
        "execution_invocation_present": False,
        "consumed": False,
        "reusable": False,
    }
    expected_scope = {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in package_model.EXPECTED_SCOPE.items()
    }
    assert gate["proposed_maximum_scope"] == expected_scope
    assert gate["review_result"] == {
        "PASS": 13,
        "GAP": 0,
        "BLOCKED": 0,
        "COMMIT_READY": True,
        "OFFLINE_ONLY": True,
        "AUTHORIZATION_GRANTED": False,
        "EXECUTION_AUTHORIZED": False,
    }


def test_f165_python_capability_firewall():
    forbidden_imports = {
        "multiprocessing", "socket", "subprocess", "threading", "asyncio",
        "concurrent", "selectors", "ssl", "http", "urllib", "requests", "ctypes",
    }
    forbidden_calls = {
        "start", "fork", "spawn", "connect", "bind", "listen", "accept",
        "send", "recv", "terminate", "kill", "Popen", "system", "exec",
        "run_authorized_experiment_once",
    }
    for path in NEW_PYTHON_PATHS:
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
        assert forbidden_imports.isdisjoint(imports), path
        assert forbidden_calls.isdisjoint(calls), path
