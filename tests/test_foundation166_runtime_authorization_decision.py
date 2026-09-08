# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "tests/foundation166_runtime_authorization_decision.py"
GATE_PATH = ROOT / "docs/l28_foundation166_runtime_authorization_decision_gate_v0.1.json"


def load_model():
    spec = importlib.util.spec_from_file_location("f166_decision", MODEL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


model = load_model()


def future_evidence():
    return {
        "evidence_kind": "EXPLICIT_OPERATOR_AUTHORIZATION_DECISION",
        "separate_future_step": True,
        "proposed_experiment_id": model.PROPOSED_EXPERIMENT_ID,
        "decision": model.AUTHORIZE,
        "operator_decision_id": "FUTURE-OPERATOR-DECISION-ID",
        "security_review_id": "FUTURE-SECURITY-REVIEW-ID",
        "separate_explicit_execution_invocation_required": True,
    }


def test_valid_f165_binding_yields_pending_default_without_authority():
    result = model.assess_operator_decision(model.required_f165_input())
    assert result == model.committed_decision_state()
    assert result["decision"] == model.PENDING
    assert result["authorization_granted"] is False
    assert result["execution_authorized"] is False
    assert result["execution_invocation_present"] is False


@pytest.mark.parametrize(
    ("key", "invalid"),
    [
        ("f165_gate_sha256", "0" * 64),
        ("decision_result", "NOT_READY"),
        ("new_authorization_required", False),
        ("f159_retry_forbidden", False),
        ("old_authorization_reusable", True),
        ("authorization_granted", True),
        ("execution_authorized", True),
        ("execution_invocation_present", True),
    ],
)
def test_f165_binding_authority_or_history_contradiction_is_blocked(key, invalid):
    value = model.required_f165_input()
    value[key] = invalid
    with pytest.raises(model.DecisionBoundaryError, match="F165_BINDING_OR_STATE_INVALID"):
        model.assess_operator_decision(value)


def test_invalid_decision_is_rejected():
    with pytest.raises(model.DecisionBoundaryError, match="UNKNOWN_OPERATOR_DECISION"):
        model.assess_operator_decision(model.required_f165_input(), "EXECUTE")


def test_authorize_requires_separate_explicit_future_operator_evidence():
    with pytest.raises(model.DecisionBoundaryError, match="EVIDENCE_REQUIRED"):
        model.assess_operator_decision(model.required_f165_input(), model.AUTHORIZE)
    result = model.assess_operator_decision(
        model.required_f165_input(), model.AUTHORIZE, future_evidence()
    )
    assert result["decision_valid"] is True
    assert result["future_operator_evidence_present"] is True
    assert result["new_authorization_only"] is True
    assert result["f159_retry_forbidden"] is True
    assert result["old_authorization_reusable"] is False
    assert result["authorization_granted"] is True
    assert result["execution_authorized"] is False


@pytest.mark.parametrize(
    ("key", "invalid"),
    [
        ("evidence_kind", "IMPLICIT"),
        ("separate_future_step", False),
        ("proposed_experiment_id", "OLD-EXPERIMENT"),
        ("decision", "DEFER"),
        ("operator_decision_id", "CURRENT-ID"),
        ("security_review_id", "CURRENT-ID"),
        ("separate_explicit_execution_invocation_required", False),
    ],
)
def test_malformed_future_operator_evidence_is_rejected(key, invalid):
    evidence = future_evidence()
    evidence[key] = invalid
    with pytest.raises(model.DecisionBoundaryError, match="EVIDENCE_INVALID"):
        model.assess_operator_decision(
            model.required_f165_input(), model.AUTHORIZE, evidence
        )


def test_defer_remains_non_executable_and_rejects_operator_evidence():
    result = model.assess_operator_decision(
        model.required_f165_input(), model.DEFER
    )
    assert result["decision"] == model.DEFER
    assert result["authorization_granted"] is False
    assert result["execution_authorized"] is False
    with pytest.raises(model.DecisionBoundaryError, match="NOT_ALLOWED"):
        model.assess_operator_decision(
            model.required_f165_input(), model.DEFER, future_evidence()
        )


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_f166_gate_is_duplicate_free_hash_bound_and_pending():
    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            assert key not in result, key
            result[key] = value
        return result

    gate = json.loads(
        GATE_PATH.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys
    )
    for binding in gate["source_bindings"].values():
        assert sha256(ROOT / binding["path"]) == binding["sha256"]
    assert gate["decision_state"] == model.committed_decision_state()
    assert gate["authority"]["F166_AUTHORIZATION_GRANTED"] is False
    assert gate["authority"]["F166_EXECUTION_AUTHORIZED"] is False
    assert gate["protected_invariants"]["protocol_sha256"] == sha256(ROOT / "PROTOCOL.md")
    assert gate["protected_invariants"]["tx_validation_sha256"] == sha256(
        ROOT / "coin/tx_validation.py"
    )


def test_f166_python_capability_firewall():
    forbidden_imports = {
        "multiprocessing", "socket", "subprocess", "threading", "asyncio",
        "concurrent", "selectors", "ssl", "http", "urllib", "requests", "ctypes",
    }
    forbidden_calls = {
        "start", "fork", "spawn", "connect", "bind", "listen", "accept", "send",
        "recv", "terminate", "kill", "Popen", "system", "exec",
        "run_authorized_experiment_once",
    }
    for path in (MODEL_PATH, Path(__file__)):
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
