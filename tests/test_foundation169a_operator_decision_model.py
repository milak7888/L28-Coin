# SPDX-License-Identifier: Apache-2.0
import ast
import importlib.util
import json
from pathlib import Path

import pytest

from coin.foundation168_execution_authorization import (
    BASE_COMMIT,
    EXPERIMENT_ID,
    F164_CANDIDATE_SHA256,
    F166_DECISION,
    F166_GATE_SHA256,
    F167_GATE_SHA256,
)


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "tests/foundation169a_operator_decision_model.py"
GATE_PATH = ROOT / "docs/l28_foundation169a_operator_decision_gate_v0.1.json"
REVIEW_PATH = ROOT / "docs/foundation169a_operator_decision_review_v0.1.md"


def load_model():
    spec = importlib.util.spec_from_file_location("f169a_decision", MODEL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


model = load_model()


def load_gate():
    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            assert key not in result, key
            result[key] = value
        return result

    return json.loads(
        GATE_PATH.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys
    )


def test_gate_is_exact_operator_decision_evidence():
    assert load_gate() == {
        "experiment_id": "L28-F165-PROPOSED-BOUNDED-RUNTIME-001",
        "decision": "AUTHORIZE_ONE_NEW_BOUNDED_EXPERIMENT",
        "authorization_id": "L28-F168-BOUND-RUNTIME-001-AUTH-001",
        "base_commit": "8add82820e3d62692ecf7da4afc7327ec6ae740a",
        "f164_candidate_sha256": "1921fb28103e0240c9fac6f0e1c3e17f6c0a2b5824a1609ed3cbdf91f1e4d2db",
        "f166_gate_sha256": "f5433efd24f051b188d6e937f0debf651ddf61543089c10a8443745bb1c1b526",
        "f167_gate_sha256": "e569f395327db19deff63cc8228339e48f50ea2ece447cadbc35eba5daa82ca0",
        "one_shot": True,
        "f159_retry_forbidden": True,
        "old_authorization_reusable": False,
    }


def test_gate_matches_f168_authorization_validator_constants():
    gate = load_gate()
    assert gate["experiment_id"] == EXPERIMENT_ID
    assert gate["decision"] == F166_DECISION
    assert gate["base_commit"] == BASE_COMMIT
    assert gate["f164_candidate_sha256"] == F164_CANDIDATE_SHA256
    assert gate["f166_gate_sha256"] == F166_GATE_SHA256
    assert gate["f167_gate_sha256"] == F167_GATE_SHA256
    assert gate["authorization_id"].startswith("L28-F168-")


def test_operator_decision_is_recorded_but_execution_remains_closed():
    state = model.validate_decision_evidence(load_gate())
    assert state == {
        "F169A_DECISION": model.AUTHORIZE,
        "F169A_OPERATOR_DECISION_RECORDED": True,
        "F169A_AUTHORIZATION_GRANTED": True,
        "F168_INVOCATION_PRESENT": False,
        "F168_EXECUTION_AUTHORIZED": False,
        "F168_AUTHORIZATION_CONSUMED": False,
        "F168_EXECUTION_OCCURRED": False,
        "F159_RETRY_FORBIDDEN": True,
    }


@pytest.mark.parametrize(
    ("key", "invalid"),
    [
        ("experiment_id", "OLD-EXPERIMENT"),
        ("decision", "PENDING_OPERATOR_DECISION"),
        ("authorization_id", "L28-F157-OLD"),
        ("base_commit", "0" * 40),
        ("f164_candidate_sha256", "0" * 64),
        ("f166_gate_sha256", "0" * 64),
        ("f167_gate_sha256", "0" * 64),
        ("one_shot", False),
        ("f159_retry_forbidden", False),
        ("old_authorization_reusable", True),
    ],
)
def test_altered_expanded_or_reusable_decision_fails_closed(key, invalid):
    evidence = model.committed_decision_evidence()
    evidence[key] = invalid
    with pytest.raises(model.DecisionBoundaryError, match="BINDING_INVALID"):
        model.validate_decision_evidence(evidence)


def test_missing_or_extra_key_fails_closed():
    missing = model.committed_decision_evidence()
    del missing["one_shot"]
    with pytest.raises(model.DecisionBoundaryError, match="MISSING_OR_MALFORMED"):
        model.validate_decision_evidence(missing)
    extra = model.committed_decision_evidence()
    extra["invocation"] = "AUTHORIZE_FOUNDATION168_EXECUTION_ONCE"
    with pytest.raises(model.DecisionBoundaryError, match="MISSING_OR_MALFORMED"):
        model.validate_decision_evidence(extra)


def test_no_invocation_or_execution_evidence_is_created():
    gate = load_gate()
    assert "invocation" not in gate
    assert "separate_explicit_invocation" not in gate
    assert "F168_EXECUTION_AUTHORIZED" not in gate
    assert "F168_AUTHORIZATION_CONSUMED" not in gate
    assert "F168_EXECUTION_OCCURRED" not in gate


def test_capability_firewall_passes_for_both_python_files():
    forbidden_imports = {
        "multiprocessing", "socket", "subprocess", "threading", "asyncio",
        "concurrent", "selectors", "requests", "urllib", "http",
    }
    forbidden_calls = {
        "start", "spawn", "fork", "connect", "bind", "listen", "accept",
        "send", "recv", "terminate", "kill",
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


def test_review_records_pass_and_non_execution_boundary():
    review = REVIEW_PATH.read_text(encoding="utf-8")
    assert "PASS 7 / GAP 0 / BLOCKED 0" in review
    assert "F168_EXECUTION_AUTHORIZED=false" in review
    assert "F168_AUTHORIZATION_CONSUMED=false" in review
    assert "F168_EXECUTION_OCCURRED=false" in review
