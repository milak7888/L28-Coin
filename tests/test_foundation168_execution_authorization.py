# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path

import pytest

from coin.foundation168_execution_authorization import (
    AuthorizationFailure,
    BASE_COMMIT,
    EXPERIMENT_ID,
    F164_CANDIDATE_SHA256,
    F166_DECISION,
    F166_GATE_SHA256,
    F167_GATE_SHA256,
    F168_INVOCATION,
    OneShotExecutionAuthorization,
    initial_state,
)


ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "docs/l28_foundation168_execution_authorization_state_v1.0.json"


def decision_evidence():
    return {
        "experiment_id": EXPERIMENT_ID,
        "decision": F166_DECISION,
        "authorization_id": "L28-F168-FUTURE-ONE-SHOT-001",
        "base_commit": BASE_COMMIT,
        "f164_candidate_sha256": F164_CANDIDATE_SHA256,
        "f166_gate_sha256": F166_GATE_SHA256,
        "f167_gate_sha256": F167_GATE_SHA256,
        "one_shot": True,
        "f159_retry_forbidden": True,
        "old_authorization_reusable": False,
    }


def invocation_evidence():
    return {
        "experiment_id": EXPERIMENT_ID,
        "invocation": F168_INVOCATION,
        "authorization_id": "L28-F168-FUTURE-ONE-SHOT-001",
        "separate_explicit_invocation": True,
    }


def test_initial_committed_state_is_pending_unconsumed_and_closed():
    expected = initial_state()
    assert expected["F166_DECISION"] == "PENDING_OPERATOR_DECISION"
    assert expected["F166_AUTHORIZATION_GRANTED"] is False
    assert expected["F168_EXECUTION_AUTHORIZED"] is False
    assert expected["F168_INVOCATION_PRESENT"] is False
    assert expected["F168_AUTHORIZATION_CONSUMED"] is False
    assert expected["F168_EXECUTION_OCCURRED"] is False
    assert json.loads(STATE_PATH.read_text(encoding="utf-8"))["state"] == expected


def test_pending_state_or_missing_either_evidence_blocks_claim():
    authorization = OneShotExecutionAuthorization(initial_state())
    with pytest.raises(AuthorizationFailure, match="DECISION_MISSING"):
        authorization.claim_once(None, invocation_evidence())
    with pytest.raises(AuthorizationFailure, match="INVOCATION_MISSING"):
        authorization.claim_once(decision_evidence(), None)
    assert authorization.state == initial_state()


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
def test_stale_expanded_old_or_reusable_decision_is_blocked(key, invalid):
    decision = decision_evidence()
    decision[key] = invalid
    with pytest.raises(AuthorizationFailure, match="DECISION_BINDING_INVALID"):
        OneShotExecutionAuthorization(initial_state()).claim_once(
            decision, invocation_evidence()
        )


@pytest.mark.parametrize(
    ("key", "invalid"),
    [
        ("experiment_id", "OTHER"),
        ("invocation", "AUTHORIZE_SOMETHING_ELSE"),
        ("authorization_id", "L28-F168-DIFFERENT"),
        ("separate_explicit_invocation", False),
    ],
)
def test_invocation_is_independent_and_exactly_bound(key, invalid):
    invocation = invocation_evidence()
    invocation[key] = invalid
    with pytest.raises(AuthorizationFailure, match="INVOCATION_BINDING_INVALID"):
        OneShotExecutionAuthorization(initial_state()).claim_once(
            decision_evidence(), invocation
        )


def test_one_shot_claim_consumes_before_reuse_and_never_allows_retry():
    authorization = OneShotExecutionAuthorization(initial_state())
    fingerprint = authorization.claim_once(decision_evidence(), invocation_evidence())
    assert len(fingerprint) == 64
    state = authorization.state
    assert state["F168_AUTHORIZATION_CONSUMED"] is True
    assert state["claim_count"] == 1
    assert state["F168_RETRY_ALLOWED"] is False
    with pytest.raises(AuthorizationFailure, match="ALREADY_CONSUMED"):
        authorization.claim_once(decision_evidence(), invocation_evidence())


def test_persistent_claim_is_exclusive_across_authorization_instances(tmp_path):
    marker = tmp_path / "f168.claim"
    first = OneShotExecutionAuthorization(initial_state(), marker)
    first.claim_once(decision_evidence(), invocation_evidence())
    persisted = json.loads(marker.read_text(encoding="utf-8"))
    assert persisted["authorization_consumed"] is True
    assert persisted["reusable"] is False
    second = OneShotExecutionAuthorization(initial_state(), marker)
    with pytest.raises(AuthorizationFailure, match="PERSISTENT_AUTHORIZATION_ALREADY_CONSUMED"):
        second.claim_once(decision_evidence(), invocation_evidence())
