# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from coin.foundation168_execution_evidence import evidence_is_hash_valid
from coin.foundation168_post_run_review import PASS, evaluate_post_run


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "tests/foundation170_forward_path_decision.py"
GATE_PATH = ROOT / "docs/l28_foundation170_forward_path_decision_gate_v0.1.json"
ASSESSMENT_PATH = ROOT / "docs/foundation170_post_proof_assessment_v0.1.md"


def load_model():
    spec = importlib.util.spec_from_file_location("f170_decision", MODEL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


model = load_model()


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, key
        result[key] = value
    return result


def load_json(path):
    return json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys
    )


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_default_is_pending_and_non_activating():
    result = model.assess_forward_path(model.required_proof())
    assert result == model.committed_decision_state()
    assert result["F170_DECISION"] == "PENDING_OPERATOR_SELECTION"
    assert result["OPERATOR_SELECTION_RECORDED"] is False
    assert result["SELECTED_DIRECTION"] is None
    assert result["NO_AUTOMATIC_ADVANCEMENT"] is True
    assert result["RUNTIME_ACTIVITY"] is False
    assert result["SIGNER_ACTIVATION"] is False
    assert result["TESTNET_ACTIVITY"] is False
    assert result["PUBLIC_TESTNET_ACTIVATION"] is False
    assert result["DEPLOYMENT"] is False


@pytest.mark.parametrize(
    ("key", "invalid"),
    [
        ("f169b_evidence_sha256", "0" * 64),
        ("f169b_gate_sha256", "0" * 64),
        ("F168_POST_RUN_RESULT", "ABORT_ACCEPTED"),
        ("F168_EXECUTION_OCCURRED", False),
        ("F168_AUTHORIZATION_CONSUMED", False),
        ("F168_RETRY_ALLOWED", True),
        ("F159_RETRY_FORBIDDEN", False),
        ("authorization_claim_count", 2),
    ],
)
def test_missing_invalid_retryable_or_reused_proof_blocks_advancement(key, invalid):
    proof = model.required_proof()
    proof[key] = invalid
    with pytest.raises(model.ForwardPathDecisionError, match="PROOF_MISSING_OR_INVALID"):
        model.assess_forward_path(proof, model.OPTION_A)


@pytest.mark.parametrize("proof", [None, {}, {"F168_POST_RUN_RESULT": "PASS"}])
def test_missing_proof_blocks_advancement(proof):
    with pytest.raises(model.ForwardPathDecisionError, match="PROOF_MISSING_OR_INVALID"):
        model.assess_forward_path(proof, model.OPTION_A)


def test_unknown_or_implicit_option_is_rejected():
    with pytest.raises(model.ForwardPathDecisionError, match="UNKNOWN_FORWARD_PATH"):
        model.assess_forward_path(model.required_proof(), "AUTOMATIC_NEXT_STEP")


@pytest.mark.parametrize(
    ("option", "description"),
    [
        (model.OPTION_A, "broader isolated two-agent testnet"),
        (model.OPTION_B, "signer and economic-control security gates"),
        (model.OPTION_C, "interoperability preparation"),
        (model.OPTION_D, "bounded public testnet planning"),
    ],
)
def test_explicit_option_records_direction_but_never_activation(option, description):
    result = model.assess_forward_path(model.required_proof(), option)
    assert result["F170_DECISION"] == option
    assert result["OPERATOR_SELECTION_RECORDED"] is True
    assert result["SELECTED_DIRECTION"] == description
    assert result["SEPARATE_FUTURE_REVIEW_REQUIRED"] is True
    assert result["SEPARATE_FUTURE_AUTHORIZATION_REQUIRED"] is True
    assert result["RUNTIME_ACTIVITY"] is False
    assert result["SIGNER_ACTIVATION"] is False
    assert result["TESTNET_ACTIVITY"] is False
    assert result["PUBLIC_TESTNET_ACTIVATION"] is False
    assert result["DEPLOYMENT"] is False
    assert result["PROTOCOL_AUTHORITY"] is False
    assert result["ECONOMIC_AUTHORITY"] is False
    assert result["SETTLEMENT_AUTHORITY"] is False


def test_gate_is_duplicate_free_hash_bound_and_requires_f168_pass():
    gate = load_json(GATE_PATH)
    for binding in gate["source_bindings"].values():
        assert sha256(ROOT / binding["path"]) == binding["sha256"]
    evidence_binding = gate["source_bindings"]["f169b_execution_evidence"]
    evidence = load_json(ROOT / evidence_binding["path"])
    assert evidence_is_hash_valid(evidence)
    assert evidence["evidence_sha256"] == evidence_binding["embedded_evidence_sha256"]
    assert evaluate_post_run(evidence) == PASS
    assert gate["post_proof_state"] == {
        "F168_POST_RUN_RESULT": "PASS",
        "F168_EXECUTION_OCCURRED": True,
        "F168_AUTHORIZATION_CONSUMED": True,
        "F168_RETRY_ALLOWED": False,
        "F159_RETRY_FORBIDDEN": True,
        "authorization_claim_count": 1,
    }


def test_gate_options_pending_state_and_remaining_boundaries_are_exact():
    gate = load_json(GATE_PATH)
    assert gate["forward_options"] == model.FORWARD_OPTIONS
    assert gate["decision_state"] == {
        "F170_DECISION": model.PENDING,
        "OPERATOR_SELECTION_RECORDED": False,
        "SELECTED_DIRECTION": None,
        "NO_AUTOMATIC_ADVANCEMENT": True,
    }
    assert gate["remaining_boundaries"] == {
        "signer_and_economic_control_gates": "UNRESOLVED_REQUIRES_SEPARATE_REVIEW",
        "broader_testnet": "REQUIRES_NEW_REVIEW",
        "interoperability": "REQUIRES_SEPARATE_DESIGN",
        "public_testnet": "REQUIRES_FUTURE_AUTHORIZATION",
    }


def test_security_rules_protocol_validator_and_authority_remain_protected():
    gate = load_json(GATE_PATH)
    rules = gate["security_rules"]
    assert rules["protocol_version"] == "1.0.0"
    assert rules["protocol_frozen"] is True
    assert rules["coinbase_only_issuance"] is True
    assert rules["canonical_validator"] == "coin.tx_validation.validate_transaction"
    assert rules["immutable_economics_and_history"] is True
    assert rules["bitcoin_role"] == "EXTERNAL_EVIDENCE_ONLY"
    assert rules["signer_activation_allowed"] is False
    assert rules["deployment_allowed"] is False
    assert rules["production_network_allowed"] is False
    assert not any(gate["protected_authority"].values())
    assert gate["protected_hashes"]["protocol_sha256"] == sha256(ROOT / "PROTOCOL.md")
    assert gate["protected_hashes"]["tx_validation_sha256"] == sha256(
        ROOT / "coin/tx_validation.py"
    )


def test_new_python_files_have_no_runtime_capability():
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


def test_security_review_and_exact_candidate_scope():
    gate = load_json(GATE_PATH)
    assert gate["candidate_scope"] == [
        "docs/foundation170_post_proof_assessment_v0.1.md",
        "docs/l28_foundation170_forward_path_decision_gate_v0.1.json",
        "tests/foundation170_forward_path_decision.py",
        "tests/test_foundation170_forward_path_decision.py",
    ]
    assert gate["security_review"] == {
        "PASS": 5, "GAP": 0, "BLOCKED": 0, "COMMIT_READY": True
    }
    assessment = ASSESSMENT_PATH.read_text(encoding="utf-8")
    assert "PASS 5 / GAP 0 / BLOCKED 0" in assessment
    assert "F170_DECISION=PENDING_OPERATOR_SELECTION" in assessment
