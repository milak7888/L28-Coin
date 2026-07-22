# SPDX-License-Identifier: Apache-2.0
"""Foundation 43 peer admission decision envelope validator tests."""

from __future__ import annotations

import ast
import hashlib
import json
import unittest
from pathlib import Path
from unittest import mock

from coin import disposable_network_identity_genesis_binding as identity
from coin import peer_admission_decision_envelope as admission
from coin import peer_handshake_identity_binding as handshake
from coin import tx_validation


def _wire(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")


def _fixture() -> dict[str, object]:
    genesis_result = identity.verify_disposable_network_genesis_json(
        identity.genesis_json_bytes()
    )
    assert genesis_result.ok
    peer_key = hashlib.sha256(b"l28-f43-peer-vector").hexdigest()
    peer = handshake.build_peer_identity(peer_key)
    session_id = hashlib.sha256(b"l28-f43-session").hexdigest()
    replay: set[str] = set()

    hello = handshake.build_handshake_hello(
        chain_id=genesis_result.chain_id,
        genesis_digest=genesis_result.genesis_digest,
        session_id=session_id,
        peer=peer,
        nonce=hashlib.sha256(b"f43-nonce-hello").hexdigest(),
    )
    hello_result = handshake.verify_peer_handshake_hello_json(
        _wire(hello),
        expected_genesis_digest=genesis_result.genesis_digest,
        expected_chain_id=genesis_result.chain_id,
        logical_now=0,
        replay_set=replay,
    )
    assert hello_result.ok, hello_result.code
    replay.add(hello["message_id"])
    replay.add(hello["nonce"])

    challenge = handshake.build_handshake_challenge(
        chain_id=genesis_result.chain_id,
        genesis_digest=genesis_result.genesis_digest,
        session_id=session_id,
        peer=peer,
        nonce=hashlib.sha256(b"f43-nonce-challenge").hexdigest(),
        hello_message_id=hello["message_id"],
    )
    challenge_result = handshake.verify_peer_handshake_challenge_json(
        _wire(challenge),
        expected_genesis_digest=genesis_result.genesis_digest,
        expected_chain_id=genesis_result.chain_id,
        logical_now=0,
        replay_set=replay,
        expected_hello_message_id=hello["message_id"],
    )
    assert challenge_result.ok, challenge_result.code
    replay.add(challenge["message_id"])
    replay.add(challenge["nonce"])

    response = handshake.build_handshake_response(
        chain_id=genesis_result.chain_id,
        genesis_digest=genesis_result.genesis_digest,
        session_id=session_id,
        peer=peer,
        nonce=hashlib.sha256(b"f43-nonce-response").hexdigest(),
        challenge=challenge,
    )
    response_result = handshake.verify_peer_handshake_response_json(
        _wire(response),
        expected_genesis_digest=genesis_result.genesis_digest,
        expected_chain_id=genesis_result.chain_id,
        logical_now=0,
        replay_set=replay,
        expected_challenge=challenge,
    )
    assert response_result.ok, response_result.code
    replay.add(response["message_id"])
    replay.add(response["nonce"])

    accept = handshake.build_handshake_accept(
        chain_id=genesis_result.chain_id,
        genesis_digest=genesis_result.genesis_digest,
        session_id=session_id,
        peer=peer,
        nonce=hashlib.sha256(b"f43-nonce-accept").hexdigest(),
        response_message_id=response["message_id"],
    )
    accept_result = handshake.verify_peer_handshake_accept_json(
        _wire(accept),
        expected_genesis_digest=genesis_result.genesis_digest,
        expected_chain_id=genesis_result.chain_id,
        logical_now=0,
        replay_set=replay,
        expected_response_message_id=response["message_id"],
        expected_peer_id=peer["peer_id"],
    )
    assert accept_result.ok, accept_result.code

    envelope = admission.build_peer_admission_decision_envelope(
        chain_id=genesis_result.chain_id,
        genesis_digest=genesis_result.genesis_digest,
        peer_id=peer["peer_id"],
        peer_public_key=peer["peer_public_key"],
        peer_address=peer["peer_address"],
        handshake_accept_message_id=accept["message_id"],
        handshake_accept_report_id=accept_result.report_id,
        handshake_session_id=session_id,
        challenge=challenge["challenge"],
        challenge_id=challenge["challenge_id"],
        response=response["response"],
        challenge_message_id=challenge["message_id"],
        response_message_id=response["message_id"],
        nonce=hashlib.sha256(b"f43-envelope-nonce").hexdigest(),
    )
    return {
        "chain_id": genesis_result.chain_id,
        "genesis_digest": genesis_result.genesis_digest,
        "peer": peer,
        "session_id": session_id,
        "challenge": challenge,
        "response": response,
        "accept": accept,
        "accept_result": accept_result,
        "envelope": envelope,
    }


def _verify(
    envelope: dict[str, object],
    fx: dict[str, object],
    *,
    logical_now: int = 0,
    replay_set: set[str] | None = None,
    **overrides: object,
) -> admission.PeerAdmissionDecisionResult:
    kwargs = {
        "expected_genesis_digest": fx["genesis_digest"],
        "expected_chain_id": fx["chain_id"],
        "expected_handshake_accept_report_id": fx["accept_result"].report_id,  # type: ignore[attr-defined]
        "expected_handshake_accept_message_id": fx["accept"]["message_id"],  # type: ignore[index]
        "expected_peer_id": fx["peer"]["peer_id"],  # type: ignore[index]
        "expected_session_id": fx["session_id"],
        "expected_challenge_hex": fx["challenge"]["challenge"],  # type: ignore[index]
        "expected_challenge_message_id": fx["challenge"]["message_id"],  # type: ignore[index]
        "expected_response_message_id": fx["response"]["message_id"],  # type: ignore[index]
        "logical_now": logical_now,
        "replay_set": set() if replay_set is None else replay_set,
    }
    kwargs.update(overrides)
    return admission.verify_peer_admission_decision_envelope_json(
        _wire(envelope), **kwargs  # type: ignore[arg-type]
    )


class SuccessPathTests(unittest.TestCase):
    def test_success_path_checks_and_flags(self) -> None:
        fx = _fixture()
        result = _verify(fx["envelope"], fx)  # type: ignore[arg-type]
        self.assertTrue(result.ok, result.code)
        self.assertEqual(result.code, "ok")
        self.assertEqual(result.decision, admission.DECISION_CANDIDATE)
        self.assertEqual(result.checks, admission.SUCCESS_CHECKS)
        self.assertEqual(len(result.checks), 13)
        self.assertIs(result.execution_authorized, False)
        self.assertIs(result.admission_authorized, False)
        self.assertEqual(result.detail, "")

    def test_success_binds_identity_and_handshake_ids(self) -> None:
        fx = _fixture()
        result = _verify(fx["envelope"], fx)  # type: ignore[arg-type]
        self.assertTrue(result.ok)
        self.assertEqual(result.network_id, identity.NETWORK_ID)
        self.assertEqual(result.chain_id, fx["chain_id"])
        self.assertEqual(result.genesis_digest, fx["genesis_digest"])
        self.assertEqual(
            result.handshake_accept_report_id, fx["accept_result"].report_id  # type: ignore[attr-defined]
        )


class DeterminismTests(unittest.TestCase):
    def test_identical_bytes_and_report_id(self) -> None:
        fx = _fixture()
        raw = _wire(fx["envelope"])
        one = admission.verify_peer_admission_decision_envelope_json(
            raw,
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            expected_handshake_accept_report_id=fx["accept_result"].report_id,  # type: ignore[attr-defined]
            expected_handshake_accept_message_id=fx["accept"]["message_id"],  # type: ignore[index]
            expected_peer_id=fx["peer"]["peer_id"],  # type: ignore[index]
            expected_session_id=fx["session_id"],  # type: ignore[arg-type]
            expected_challenge_hex=fx["challenge"]["challenge"],  # type: ignore[index]
            expected_challenge_message_id=fx["challenge"]["message_id"],  # type: ignore[index]
            expected_response_message_id=fx["response"]["message_id"],  # type: ignore[index]
            logical_now=0,
            replay_set=set(),
        )
        two = admission.verify_peer_admission_decision_envelope_json(
            raw,
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            expected_handshake_accept_report_id=fx["accept_result"].report_id,  # type: ignore[attr-defined]
            expected_handshake_accept_message_id=fx["accept"]["message_id"],  # type: ignore[index]
            expected_peer_id=fx["peer"]["peer_id"],  # type: ignore[index]
            expected_session_id=fx["session_id"],  # type: ignore[arg-type]
            expected_challenge_hex=fx["challenge"]["challenge"],  # type: ignore[index]
            expected_challenge_message_id=fx["challenge"]["message_id"],  # type: ignore[index]
            expected_response_message_id=fx["response"]["message_id"],  # type: ignore[index]
            logical_now=0,
            replay_set=set(),
        )
        self.assertEqual(one, two)
        self.assertEqual(one.report_id, two.report_id)
        pretty = json.dumps(fx["envelope"], indent=2)
        self.assertEqual(
            admission.verify_peer_admission_decision_envelope_json(
                pretty,
                expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
                expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
                expected_handshake_accept_report_id=fx["accept_result"].report_id,  # type: ignore[attr-defined]
                expected_handshake_accept_message_id=fx["accept"]["message_id"],  # type: ignore[index]
                expected_peer_id=fx["peer"]["peer_id"],  # type: ignore[index]
                expected_session_id=fx["session_id"],  # type: ignore[arg-type]
                expected_challenge_hex=fx["challenge"]["challenge"],  # type: ignore[index]
                expected_challenge_message_id=fx["challenge"]["message_id"],  # type: ignore[index]
                expected_response_message_id=fx["response"]["message_id"],  # type: ignore[index]
                logical_now=0,
                replay_set=set(),
            ),
            one,
        )


class IdentityMismatchTests(unittest.TestCase):
    def test_main_network_id_invalid(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["network_id"] = "MAIN"
        env["envelope_id"] = admission.compute_peer_admission_envelope_id(env)
        result = _verify(env, fx)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "network_id_invalid")
        self.assertIs(result.execution_authorized, False)
        self.assertIs(result.admission_authorized, False)


class ForbiddenEnvironmentTests(unittest.TestCase):
    def _assert_forbidden(self, environment: str) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["environment"] = environment
        env["network_id"] = "MAIN"  # would also fail later; forbidden must win
        env["envelope_id"] = admission.compute_peer_admission_envelope_id(env)
        result = _verify(env, fx)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "historical_import_forbidden")

    def test_main_environment(self) -> None:
        self._assert_forbidden("MAIN")

    def test_canonical_environment(self) -> None:
        self._assert_forbidden("CANONICAL")

    def test_historical_environment(self) -> None:
        self._assert_forbidden("HISTORICAL")

    def test_production_environment(self) -> None:
        self._assert_forbidden("PRODUCTION")

    def test_forbidden_precedes_other_failures(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["environment"] = "CANONICAL"
        env["decision"] = "not_a_candidate"
        env["envelope_id"] = admission.compute_peer_admission_envelope_id(env)
        result = _verify(env, fx)
        self.assertEqual(result.code, "historical_import_forbidden")


class GenericEnvironmentTests(unittest.TestCase):
    def test_other_environment_invalid(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["environment"] = "OTHER"
        env["envelope_id"] = admission.compute_peer_admission_envelope_id(env)
        result = _verify(env, fx)
        self.assertEqual(result.code, "environment_invalid")


class BindingMismatchTests(unittest.TestCase):
    def test_handshake_report_mismatch(self) -> None:
        fx = _fixture()
        result = _verify(
            fx["envelope"],  # type: ignore[arg-type]
            fx,
            expected_handshake_accept_report_id="0" * 64,
        )
        self.assertEqual(result.code, "handshake_binding_invalid")

    def test_peer_mismatch(self) -> None:
        fx = _fixture()
        result = _verify(
            fx["envelope"],  # type: ignore[arg-type]
            fx,
            expected_peer_id="0" * 64,
        )
        self.assertEqual(result.code, "peer_identity_invalid")

    def test_challenge_id_mismatch(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["challenge_id"] = "0" * 64
        env["envelope_id"] = admission.compute_peer_admission_envelope_id(env)
        result = _verify(env, fx)
        self.assertEqual(result.code, "challenge_binding_invalid")

    def test_response_mismatch(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["response"] = "0" * 64
        env["envelope_id"] = admission.compute_peer_admission_envelope_id(env)
        result = _verify(env, fx)
        self.assertEqual(result.code, "challenge_binding_invalid")

    def test_decision_invalid(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["decision"] = "admitted"
        env["envelope_id"] = admission.compute_peer_admission_envelope_id(env)
        result = _verify(env, fx)
        self.assertEqual(result.code, "decision_invalid")


class ReplayFreshnessTests(unittest.TestCase):
    def test_replay_envelope_id(self) -> None:
        fx = _fixture()
        env = fx["envelope"]
        replay = {env["envelope_id"]}  # type: ignore[index]
        result = _verify(env, fx, replay_set=replay)  # type: ignore[arg-type]
        self.assertEqual(result.code, "replay_detected")

    def test_replay_nonce(self) -> None:
        fx = _fixture()
        env = fx["envelope"]
        replay = {env["nonce"]}  # type: ignore[index]
        result = _verify(env, fx, replay_set=replay)  # type: ignore[arg-type]
        self.assertEqual(result.code, "replay_detected")

    def test_replay_set_not_mutated(self) -> None:
        fx = _fixture()
        replay: set[str] = set()
        snapshot = set(replay)
        _verify(fx["envelope"], fx, replay_set=replay)  # type: ignore[arg-type]
        self.assertEqual(replay, snapshot)

    def test_message_stale(self) -> None:
        fx = _fixture()
        result = _verify(fx["envelope"], fx, logical_now=61)  # type: ignore[arg-type]
        self.assertEqual(result.code, "message_stale")

    def test_message_premature(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["issued_at_logical"] = 10
        env["expires_at_logical"] = 70
        env["envelope_id"] = admission.compute_peer_admission_envelope_id(env)
        result = _verify(env, fx, logical_now=0)
        self.assertEqual(result.code, "message_premature")


class LifetimeTests(unittest.TestCase):
    def test_lifetime_below_one(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["issued_at_logical"] = 5
        env["expires_at_logical"] = 5
        env["envelope_id"] = admission.compute_peer_admission_envelope_id(env)
        result = _verify(env, fx, logical_now=5)
        self.assertEqual(result.code, "schema_invalid")

    def test_lifetime_above_3600(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["issued_at_logical"] = 0
        env["expires_at_logical"] = 3601
        env["envelope_id"] = admission.compute_peer_admission_envelope_id(env)
        result = _verify(env, fx, logical_now=0)
        self.assertEqual(result.code, "schema_invalid")


class MalformedMatrixTests(unittest.TestCase):
    def test_input_type_invalid(self) -> None:
        fx = _fixture()
        result = admission.verify_peer_admission_decision_envelope_json(
            123,  # type: ignore[arg-type]
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            expected_handshake_accept_report_id=fx["accept_result"].report_id,  # type: ignore[attr-defined]
            expected_handshake_accept_message_id=fx["accept"]["message_id"],  # type: ignore[index]
            expected_peer_id=fx["peer"]["peer_id"],  # type: ignore[index]
            expected_session_id=fx["session_id"],  # type: ignore[arg-type]
            expected_challenge_hex=fx["challenge"]["challenge"],  # type: ignore[index]
            expected_challenge_message_id=fx["challenge"]["message_id"],  # type: ignore[index]
            expected_response_message_id=fx["response"]["message_id"],  # type: ignore[index]
            logical_now=0,
            replay_set=set(),
        )
        self.assertEqual(result.code, "input_type_invalid")

    def test_input_too_large(self) -> None:
        fx = _fixture()
        huge = b"{" + b"a" * (admission.MAX_ENVELOPE_BYTES + 1) + b"}"
        result = admission.verify_peer_admission_decision_envelope_json(
            huge,
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            expected_handshake_accept_report_id=fx["accept_result"].report_id,  # type: ignore[attr-defined]
            expected_handshake_accept_message_id=fx["accept"]["message_id"],  # type: ignore[index]
            expected_peer_id=fx["peer"]["peer_id"],  # type: ignore[index]
            expected_session_id=fx["session_id"],  # type: ignore[arg-type]
            expected_challenge_hex=fx["challenge"]["challenge"],  # type: ignore[index]
            expected_challenge_message_id=fx["challenge"]["message_id"],  # type: ignore[index]
            expected_response_message_id=fx["response"]["message_id"],  # type: ignore[index]
            logical_now=0,
            replay_set=set(),
        )
        self.assertEqual(result.code, "input_too_large")

    def test_encoding_invalid(self) -> None:
        fx = _fixture()
        result = admission.verify_peer_admission_decision_envelope_json(
            b"\xff\xfe",
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            expected_handshake_accept_report_id=fx["accept_result"].report_id,  # type: ignore[attr-defined]
            expected_handshake_accept_message_id=fx["accept"]["message_id"],  # type: ignore[index]
            expected_peer_id=fx["peer"]["peer_id"],  # type: ignore[index]
            expected_session_id=fx["session_id"],  # type: ignore[arg-type]
            expected_challenge_hex=fx["challenge"]["challenge"],  # type: ignore[index]
            expected_challenge_message_id=fx["challenge"]["message_id"],  # type: ignore[index]
            expected_response_message_id=fx["response"]["message_id"],  # type: ignore[index]
            logical_now=0,
            replay_set=set(),
        )
        self.assertEqual(result.code, "encoding_invalid")

    def test_json_invalid(self) -> None:
        fx = _fixture()
        result = admission.verify_peer_admission_decision_envelope_json(
            "{",
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            expected_handshake_accept_report_id=fx["accept_result"].report_id,  # type: ignore[attr-defined]
            expected_handshake_accept_message_id=fx["accept"]["message_id"],  # type: ignore[index]
            expected_peer_id=fx["peer"]["peer_id"],  # type: ignore[index]
            expected_session_id=fx["session_id"],  # type: ignore[arg-type]
            expected_challenge_hex=fx["challenge"]["challenge"],  # type: ignore[index]
            expected_challenge_message_id=fx["challenge"]["message_id"],  # type: ignore[index]
            expected_response_message_id=fx["response"]["message_id"],  # type: ignore[index]
            logical_now=0,
            replay_set=set(),
        )
        self.assertEqual(result.code, "json_invalid")

    def test_duplicate_key(self) -> None:
        fx = _fixture()
        raw = _wire(fx["envelope"]).decode("utf-8")
        raw = raw.replace('"environment":', '"environment":"DISPOSABLE_TEST","environment":', 1)
        result = admission.verify_peer_admission_decision_envelope_json(
            raw,
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            expected_handshake_accept_report_id=fx["accept_result"].report_id,  # type: ignore[attr-defined]
            expected_handshake_accept_message_id=fx["accept"]["message_id"],  # type: ignore[index]
            expected_peer_id=fx["peer"]["peer_id"],  # type: ignore[index]
            expected_session_id=fx["session_id"],  # type: ignore[arg-type]
            expected_challenge_hex=fx["challenge"]["challenge"],  # type: ignore[index]
            expected_challenge_message_id=fx["challenge"]["message_id"],  # type: ignore[index]
            expected_response_message_id=fx["response"]["message_id"],  # type: ignore[index]
            logical_now=0,
            replay_set=set(),
        )
        self.assertEqual(result.code, "duplicate_key")

    def test_invalid_top_level(self) -> None:
        fx = _fixture()
        result = admission.verify_peer_admission_decision_envelope_json(
            "[]",
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            expected_handshake_accept_report_id=fx["accept_result"].report_id,  # type: ignore[attr-defined]
            expected_handshake_accept_message_id=fx["accept"]["message_id"],  # type: ignore[index]
            expected_peer_id=fx["peer"]["peer_id"],  # type: ignore[index]
            expected_session_id=fx["session_id"],  # type: ignore[arg-type]
            expected_challenge_hex=fx["challenge"]["challenge"],  # type: ignore[index]
            expected_challenge_message_id=fx["challenge"]["message_id"],  # type: ignore[index]
            expected_response_message_id=fx["response"]["message_id"],  # type: ignore[index]
            logical_now=0,
            replay_set=set(),
        )
        self.assertEqual(result.code, "invalid_top_level")

    def test_unknown_field(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["extra"] = "nope"
        result = _verify(env, fx)
        self.assertEqual(result.code, "schema_invalid")

    def test_reordered_fields(self) -> None:
        fx = _fixture()
        env = fx["envelope"]
        keys = list(env.keys())  # type: ignore[attr-defined]
        reordered = {keys[1]: env[keys[1]], keys[0]: env[keys[0]]}  # type: ignore[index]
        for key in keys[2:]:
            reordered[key] = env[key]  # type: ignore[index]
        result = _verify(reordered, fx)
        self.assertEqual(result.code, "schema_invalid")

    def test_handshake_version_schema_invalid(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["handshake_version"] = "l28-peer-handshake-identity-binding/v9.9.9"
        env["envelope_id"] = admission.compute_peer_admission_envelope_id(env)
        result = _verify(env, fx)
        self.assertEqual(result.code, "schema_invalid")

    def test_unsupported_envelope_version(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["envelope_version"] = "l28-peer-admission-decision-envelope/v9.9.9"
        env["envelope_id"] = admission.compute_peer_admission_envelope_id(env)
        result = _verify(env, fx)
        self.assertEqual(result.code, "envelope_version_unsupported")


class LifecycleAuthorityTests(unittest.TestCase):
    def test_lifecycle_invalid(self) -> None:
        session = admission.PeerAdmissionDecisionSession()
        with self.assertRaises(admission._AdmissionError) as ctx:
            session.transition("ENVELOPE_VERIFIED")
        self.assertEqual(ctx.exception.code, "lifecycle_invalid")

    def test_lifecycle_happy_path(self) -> None:
        session = admission.PeerAdmissionDecisionSession()
        session.transition("HANDSHAKE_ACCEPTED")
        session.transition("ENVELOPE_CANDIDATE")
        session.transition("ENVELOPE_VERIFIED")
        session.transition("CLOSED")
        self.assertEqual(session.state, "CLOSED")

    def test_execution_authorized_invalid(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["execution_authorized"] = True
        env["envelope_id"] = admission.compute_peer_admission_envelope_id(env)
        result = _verify(env, fx)
        self.assertEqual(result.code, "execution_authorized_invalid")

    def test_admission_authorized_invalid(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["admission_authorized"] = True
        env["envelope_id"] = admission.compute_peer_admission_envelope_id(env)
        result = _verify(env, fx)
        self.assertEqual(result.code, "admission_authorized_invalid")

    def test_execution_flag_checked_before_admission(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["execution_authorized"] = True
        env["admission_authorized"] = True
        env["envelope_id"] = admission.compute_peer_admission_envelope_id(env)
        result = _verify(env, fx)
        self.assertEqual(result.code, "execution_authorized_invalid")

    def test_envelope_id_invalid(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["envelope_id"] = "0" * 64
        result = _verify(env, fx)
        self.assertEqual(result.code, "envelope_id_invalid")


class HygieneEconomicsTests(unittest.TestCase):
    def test_static_hygiene(self) -> None:
        source = Path(admission.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        forbidden = {
            "socket",
            "subprocess",
            "requests",
            "urllib",
            "http",
            "asyncio",
            "wallet",
            "ledger",
            "mining",
        }
        self.assertTrue(imported.isdisjoint(forbidden))
        self.assertNotIn("Leap28", source)
        self.assertNotIn("Nova", source)
        self.assertIn("validate_disposable_handshake_identity_binding", source)
        self.assertIn("compute_peer_handshake_challenge_id", source)
        self.assertIn("compute_peer_handshake_response", source)

    def test_economics_unchanged(self) -> None:
        self.assertEqual(tx_validation.L28_MAX_SUPPLY, 28_000_000)
        self.assertEqual(tx_validation.L28_EMISSION_CEILING, 11_130_000)
        self.assertEqual(tx_validation.L28_HALVING_INTERVAL, 210_000)
        self.assertEqual(tx_validation.L28_MAX_COINBASE_REWARD, 28)
        self.assertEqual(tx_validation.L28_REWARD_SCHEDULE, (28, 14, 7, 3, 1))


class StableErrorCoverageTests(unittest.TestCase):
    def _assert_fail(
        self, result: admission.PeerAdmissionDecisionResult, code: str
    ) -> None:
        self.assertFalse(result.ok)
        self.assertEqual(result.code, code)
        self.assertIs(result.execution_authorized, False)
        self.assertIs(result.admission_authorized, False)
        self.assertEqual(result.detail, "")

    def test_protocol_version_invalid(self) -> None:
        fx = _fixture()
        env = dict(fx["envelope"])  # type: ignore[arg-type]
        env["protocol_version"] = "l28-protocol/9.9.9"
        env["envelope_id"] = admission.compute_peer_admission_envelope_id(env)
        self._assert_fail(_verify(env, fx), "protocol_version_invalid")

    def test_chain_id_invalid(self) -> None:
        fx = _fixture()
        self._assert_fail(
            _verify(fx["envelope"], fx, expected_chain_id="0" * 64),  # type: ignore[arg-type]
            "chain_id_invalid",
        )

    def test_genesis_digest_invalid(self) -> None:
        fx = _fixture()
        self._assert_fail(
            _verify(fx["envelope"], fx, expected_genesis_digest="0" * 64),  # type: ignore[arg-type]
            "genesis_digest_invalid",
        )

    def test_session_binding_invalid(self) -> None:
        fx = _fixture()
        self._assert_fail(
            _verify(fx["envelope"], fx, expected_session_id="0" * 64),  # type: ignore[arg-type]
            "handshake_binding_invalid",
        )

    def test_challenge_message_id_invalid(self) -> None:
        fx = _fixture()
        self._assert_fail(
            _verify(
                fx["envelope"],  # type: ignore[arg-type]
                fx,
                expected_challenge_message_id="0" * 64,
            ),
            "challenge_binding_invalid",
        )

    def test_internal_error_via_public_api_monkeypatch(self) -> None:
        fx = _fixture()
        with mock.patch.object(
            admission,
            "_parse",
            side_effect=RuntimeError("forced-unexpected-failure"),
        ):
            first = _verify(fx["envelope"], fx)  # type: ignore[arg-type]
            second = _verify(fx["envelope"], fx)  # type: ignore[arg-type]
        self._assert_fail(first, "internal_error")
        self.assertEqual(first, second)
        self.assertNotIn("forced-unexpected-failure", first.code)
        self.assertNotIn("forced-unexpected-failure", first.detail)

    def test_all_27_stable_codes_are_explicitly_asserted(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        required = admission.STABLE_CODES
        self.assertEqual(len(required), 27)
        self.assertEqual(len(set(required)), 27)
        missing = [
            code
            for code in required
            if f'"{code}"' not in source and f"'{code}'" not in source
        ]
        self.assertEqual(missing, [], missing)
        fx = _fixture()
        ok_result = _verify(fx["envelope"], fx)  # type: ignore[arg-type]
        self.assertTrue(ok_result.ok)
        self.assertEqual(ok_result.code, "ok")


if __name__ == "__main__":
    unittest.main()
