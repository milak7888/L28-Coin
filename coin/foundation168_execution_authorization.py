# SPDX-License-Identifier: Apache-2.0
"""Fail-closed, one-shot F168 authorization state model."""

import hashlib
import json
import os
from pathlib import Path


EXPERIMENT_ID = "L28-F165-PROPOSED-BOUNDED-RUNTIME-001"
BASE_COMMIT = "8add82820e3d62692ecf7da4afc7327ec6ae740a"
F166_DECISION = "AUTHORIZE_ONE_NEW_BOUNDED_EXPERIMENT"
F168_INVOCATION = "AUTHORIZE_FOUNDATION168_EXECUTION_ONCE"
F164_CANDIDATE_SHA256 = "1921fb28103e0240c9fac6f0e1c3e17f6c0a2b5824a1609ed3cbdf91f1e4d2db"
F166_GATE_SHA256 = "f5433efd24f051b188d6e937f0debf651ddf61543089c10a8443745bb1c1b526"
F167_GATE_SHA256 = "e569f395327db19deff63cc8228339e48f50ea2ece447cadbc35eba5daa82ca0"

INITIAL_STATE = {
    "F166_DECISION": "PENDING_OPERATOR_DECISION",
    "F166_AUTHORIZATION_GRANTED": False,
    "F168_EXECUTION_AUTHORIZED": False,
    "F168_INVOCATION_PRESENT": False,
    "F168_AUTHORIZATION_CONSUMED": False,
    "F168_EXECUTION_OCCURRED": False,
    "F168_RETRY_ALLOWED": False,
    "F159_RETRY_FORBIDDEN": True,
    "OLD_AUTHORIZATION_REUSABLE": False,
    "claim_count": 0,
}


class AuthorizationFailure(RuntimeError):
    """Deterministic authorization-boundary failure."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def initial_state():
    return dict(INITIAL_STATE)


def _exact_keys(value, expected):
    return isinstance(value, dict) and set(value) == set(expected)


def _authorization_fingerprint(decision_evidence, invocation_evidence):
    encoded = json.dumps(
        {"decision": decision_evidence, "invocation": invocation_evidence},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class OneShotExecutionAuthorization:
    """Mutable only at the single claim boundary; no retry is possible."""

    def __init__(self, state, persistent_claim_path=None):
        if state != INITIAL_STATE:
            raise AuthorizationFailure("INITIAL_AUTHORIZATION_STATE_INVALID")
        self._state = dict(state)
        self._authorization_fingerprint = None
        self._persistent_claim_path = (
            Path(persistent_claim_path) if persistent_claim_path is not None else None
        )

    @property
    def state(self):
        return dict(self._state)

    @property
    def authorization_fingerprint(self):
        return self._authorization_fingerprint

    @staticmethod
    def validate_dual_evidence(decision_evidence, invocation_evidence):
        decision_keys = (
            "experiment_id",
            "decision",
            "authorization_id",
            "base_commit",
            "f164_candidate_sha256",
            "f166_gate_sha256",
            "f167_gate_sha256",
            "one_shot",
            "f159_retry_forbidden",
            "old_authorization_reusable",
        )
        invocation_keys = (
            "experiment_id",
            "invocation",
            "authorization_id",
            "separate_explicit_invocation",
        )
        if not _exact_keys(decision_evidence, decision_keys):
            raise AuthorizationFailure("EXPLICIT_OPERATOR_DECISION_MISSING_OR_MALFORMED")
        if not _exact_keys(invocation_evidence, invocation_keys):
            raise AuthorizationFailure("SEPARATE_F168_INVOCATION_MISSING_OR_MALFORMED")
        if (
            decision_evidence["experiment_id"] != EXPERIMENT_ID
            or decision_evidence["decision"] != F166_DECISION
            or decision_evidence["base_commit"] != BASE_COMMIT
            or decision_evidence["f164_candidate_sha256"] != F164_CANDIDATE_SHA256
            or decision_evidence["f166_gate_sha256"] != F166_GATE_SHA256
            or decision_evidence["f167_gate_sha256"] != F167_GATE_SHA256
            or decision_evidence["one_shot"] is not True
            or decision_evidence["f159_retry_forbidden"] is not True
            or decision_evidence["old_authorization_reusable"] is not False
            or not isinstance(decision_evidence["authorization_id"], str)
            or not decision_evidence["authorization_id"].startswith("L28-F168-")
        ):
            raise AuthorizationFailure("OPERATOR_DECISION_BINDING_INVALID")
        if (
            invocation_evidence["experiment_id"] != EXPERIMENT_ID
            or invocation_evidence["invocation"] != F168_INVOCATION
            or invocation_evidence["authorization_id"]
            != decision_evidence["authorization_id"]
            or invocation_evidence["separate_explicit_invocation"] is not True
        ):
            raise AuthorizationFailure("F168_INVOCATION_BINDING_INVALID")
        return _authorization_fingerprint(decision_evidence, invocation_evidence)

    def claim_once(self, decision_evidence, invocation_evidence):
        if self._state["F168_AUTHORIZATION_CONSUMED"] or self._state["claim_count"]:
            raise AuthorizationFailure("F168_AUTHORIZATION_ALREADY_CONSUMED")
        fingerprint = self.validate_dual_evidence(
            decision_evidence, invocation_evidence
        )
        if self._persistent_claim_path is not None:
            claim = json.dumps(
                {
                    "experiment_id": EXPERIMENT_ID,
                    "authorization_fingerprint": fingerprint,
                    "authorization_consumed": True,
                    "reusable": False,
                    "retry_allowed": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            try:
                descriptor = os.open(
                    self._persistent_claim_path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
            except FileExistsError as error:
                raise AuthorizationFailure(
                    "F168_PERSISTENT_AUTHORIZATION_ALREADY_CONSUMED"
                ) from error
            try:
                os.write(descriptor, claim)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        self._state.update(
            {
                "F166_DECISION": F166_DECISION,
                "F166_AUTHORIZATION_GRANTED": True,
                "F168_EXECUTION_AUTHORIZED": True,
                "F168_INVOCATION_PRESENT": True,
                "F168_AUTHORIZATION_CONSUMED": True,
                "F168_EXECUTION_OCCURRED": True,
                "F168_RETRY_ALLOWED": False,
                "claim_count": 1,
            }
        )
        self._authorization_fingerprint = fingerprint
        return fingerprint
