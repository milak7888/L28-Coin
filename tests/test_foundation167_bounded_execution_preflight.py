# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "tests/foundation167_bounded_execution_preflight.py"
F166_MODEL_PATH = ROOT / "tests/foundation166_runtime_authorization_decision.py"
GATE_PATH = ROOT / "docs/l28_foundation167_bounded_execution_preflight_gate_v0.1.json"
NEW_PYTHON_PATHS = (
    F166_MODEL_PATH,
    ROOT / "tests/test_foundation166_runtime_authorization_decision.py",
    MODEL_PATH,
    Path(__file__),
)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


model = load_module("f167_preflight", MODEL_PATH)
f166_model = load_module("f166_for_f167", F166_MODEL_PATH)


def assess(scope=None, bindings=None, f166_record=None, invocation=None):
    return model.assess_bounded_execution_preflight(
        model.exact_scope() if scope is None else scope,
        model.required_source_bindings() if bindings is None else bindings,
        model.pending_f166_record() if f166_record is None else f166_record,
        invocation,
    )


def future_authorize_record():
    evidence = {
        "evidence_kind": "EXPLICIT_OPERATOR_AUTHORIZATION_DECISION",
        "separate_future_step": True,
        "proposed_experiment_id": f166_model.PROPOSED_EXPERIMENT_ID,
        "decision": f166_model.AUTHORIZE,
        "operator_decision_id": "FUTURE-OPERATOR-DECISION-ID",
        "security_review_id": "FUTURE-SECURITY-REVIEW-ID",
        "separate_explicit_execution_invocation_required": True,
    }
    return f166_model.assess_operator_decision(
        f166_model.required_f165_input(), f166_model.AUTHORIZE, evidence
    )


def future_invocation_template():
    return {
        "invocation_kind": "SEPARATE_EXPLICIT_F168_INVOCATION_TEMPLATE",
        "separate_future_step": True,
        "proposed_experiment_id": model.PROPOSED_EXPERIMENT_ID,
        "execution_occurred": False,
    }


def test_exact_scope_with_pending_f166_keeps_every_execution_state_false():
    result = assess()
    assert result["F166_DECISION"] == model.PENDING
    assert result["READY_FOR_EXECUTION"] is False
    assert result["EXECUTION_GATE_OPEN"] is False
    assert result["EXECUTION_AUTHORIZED"] is False
    assert result["EXECUTION_OCCURRED"] is False


@pytest.mark.parametrize(
    ("key", "expanded"),
    [
        ("disposable", False),
        ("isolated", False),
        ("agent_count", 3),
        ("child_process_count", 3),
        ("network_family", "IPv4_ANY"),
        ("external_network_allowed", True),
        ("agent_a_listener", ("0.0.0.0", 28428)),
        ("agent_b_bind", ("127.0.0.1", 28429)),
        ("fixed_client_source_port_28429_forbidden", False),
        ("session_count", 3),
        ("reconnect_count", 0),
        ("reconnect_count", 2),
        ("maximum_duration_seconds", 61),
        ("deadline_kind", "MULTIPLE_DEADLINES"),
        ("deadline_coverage", model.DEADLINE_COVERAGE[:-1]),
        ("strong_parent_resource_ownership_required", False),
        ("parent_ownership_contracts", ("F161",)),
        ("provenance_freeze_security_contracts", ("F162",)),
        ("f164_candidate_required", False),
        ("f164_candidate_activating", True),
        ("f164_candidate_sha256", "0" * 64),
        ("cleanup_requires_all_children_terminal", False),
        ("cleanup_requires_all_supervisors_quiescent", False),
        ("terminal_states", model.TERMINAL_STATES[:-1]),
    ],
)
def test_scope_expansion_or_contract_weakening_is_blocked(key, expanded):
    scope = model.exact_scope()
    scope[key] = expanded
    with pytest.raises(model.PreflightContractError, match="SCOPE_NOT_EXACT"):
        assess(scope=scope)


@pytest.mark.parametrize("foundation", ("F160", "F161", "F162", "F163", "F164", "F165", "F166"))
def test_missing_or_tampered_f160_f166_binding_is_blocked(foundation):
    bindings = model.required_source_bindings()
    bindings.pop(foundation)
    with pytest.raises(model.PreflightContractError, match="BINDINGS_NOT_EXACT"):
        assess(bindings=bindings)
    bindings = model.required_source_bindings()
    bindings[foundation] = "0" * 64
    with pytest.raises(model.PreflightContractError, match="BINDINGS_NOT_EXACT"):
        assess(bindings=bindings)


def test_defer_remains_non_executable():
    record = model.pending_f166_record()
    record["decision"] = model.DEFER
    result = assess(f166_record=record, invocation=future_invocation_template())
    assert result["FUTURE_ELIGIBILITY_REQUIREMENTS_SATISFIED"] is False
    assert result["READY_FOR_EXECUTION"] is False
    assert result["EXECUTION_AUTHORIZED"] is False


def test_future_authorize_without_separate_f168_invocation_is_not_eligible():
    result = assess(f166_record=future_authorize_record())
    assert result["FUTURE_AUTHORIZE_RECORD_STRUCTURALLY_VALID"] is True
    assert result["SEPARATE_F168_INVOCATION_TEMPLATE_PRESENT"] is False
    assert result["FUTURE_ELIGIBILITY_REQUIREMENTS_SATISFIED"] is False
    assert result["READY_FOR_EXECUTION"] is False


def test_only_future_authorize_plus_separate_invocation_satisfies_prerequisites():
    result = assess(
        f166_record=future_authorize_record(), invocation=future_invocation_template()
    )
    assert result["FUTURE_ELIGIBILITY_REQUIREMENTS_SATISFIED"] is True
    assert result["READY_FOR_EXECUTION"] is True
    assert result["EXECUTION_GATE_OPEN"] is True
    assert result["EXECUTION_AUTHORIZED"] is True
    assert result["EXECUTION_OCCURRED"] is False


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_gate_json_is_duplicate_free_hash_bound_and_closed():
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
    assert gate["preflight_state"] == {
        "F166_DECISION": "PENDING_OPERATOR_DECISION",
        "READY_FOR_EXECUTION": False,
        "EXECUTION_GATE_OPEN": False,
        "EXECUTION_AUTHORIZED": False,
        "F168_EXECUTION_OCCURRED": False,
    }
    assert gate["protected_invariants"]["protocol_sha256"] == sha256(ROOT / "PROTOCOL.md")
    assert gate["protected_invariants"]["tx_validation_sha256"] == sha256(
        ROOT / "coin/tx_validation.py"
    )
    assert set(gate["protected_authority"].values()) == {False}
    assert gate["cross_batch_security_review"] == {
        "PASS": 12,
        "GAP": 0,
        "BLOCKED": 0,
        "COMMIT_READY": True,
        "OFFLINE_ONLY": True,
    }


def test_all_new_python_files_pass_capability_firewall():
    forbidden_imports = {
        "multiprocessing", "socket", "subprocess", "threading", "asyncio",
        "concurrent", "selectors", "ssl", "http", "urllib", "requests", "ctypes",
    }
    forbidden_calls = {
        "start", "fork", "spawn", "connect", "bind", "listen", "accept", "send",
        "recv", "terminate", "kill", "Popen", "system", "exec",
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
