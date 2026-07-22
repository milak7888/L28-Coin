# SPDX-License-Identifier: Apache-2.0
"""Foundation 41 peer-handshake identity-binding validator tests."""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from coin import disposable_network_identity_genesis_binding as identity
from coin import peer_handshake_identity_binding as handshake


def _wire(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")


def _fixture() -> dict[str, object]:
    genesis = identity.build_disposable_genesis_document()
    genesis_result = identity.verify_disposable_network_genesis_json(
        identity.genesis_json_bytes()
    )
    assert genesis_result.ok
    peer_key = hashlib.sha256(b"l28-f41-peer-vector").hexdigest()
    peer = handshake.build_peer_identity(peer_key)
    session_id = hashlib.sha256(b"l28-f41-session").hexdigest()
    return {
        "genesis": genesis,
        "chain_id": genesis_result.chain_id,
        "genesis_digest": genesis_result.genesis_digest,
        "peer": peer,
        "session_id": session_id,
    }


class VectorASuccessPathTests(unittest.TestCase):
    def test_hello_challenge_response_accept(self) -> None:
        fx = _fixture()
        replay: set[str] = set()
        hello = handshake.build_handshake_hello(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-hello").hexdigest(),
        )
        hello_result = handshake.verify_peer_handshake_hello_json(
            _wire(hello),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=replay,
        )
        self.assertTrue(hello_result.ok, hello_result.code)
        self.assertIs(hello_result.execution_authorized, False)
        replay.add(hello["message_id"])
        replay.add(hello["nonce"])

        challenge = handshake.build_handshake_challenge(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-challenge").hexdigest(),
            hello_message_id=hello["message_id"],
        )
        challenge_result = handshake.verify_peer_handshake_challenge_json(
            _wire(challenge),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=replay,
            expected_hello_message_id=hello["message_id"],
        )
        self.assertTrue(challenge_result.ok, challenge_result.code)
        replay.add(challenge["message_id"])
        replay.add(challenge["nonce"])

        response = handshake.build_handshake_response(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-response").hexdigest(),
            challenge=challenge,
        )
        response_result = handshake.verify_peer_handshake_response_json(
            _wire(response),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=replay,
            expected_challenge=challenge,
        )
        self.assertTrue(response_result.ok, response_result.code)
        replay.add(response["message_id"])
        replay.add(response["nonce"])

        accept = handshake.build_handshake_accept(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-accept").hexdigest(),
            response_message_id=response["message_id"],
        )
        accept_result = handshake.verify_peer_handshake_accept_json(
            _wire(accept),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=replay,
            expected_response_message_id=response["message_id"],
            expected_peer_id=fx["peer"]["peer_id"],  # type: ignore[index]
        )
        self.assertTrue(accept_result.ok, accept_result.code)
        self.assertEqual(accept_result.checks, handshake.SUCCESS_CHECKS)
        self.assertIs(accept_result.execution_authorized, False)


class DeterminismTests(unittest.TestCase):
    def test_identical_bytes_verify_twice(self) -> None:
        fx = _fixture()
        hello = handshake.build_handshake_hello(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-det").hexdigest(),
        )
        raw = _wire(hello)
        one = handshake.verify_peer_handshake_hello_json(
            raw,
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
        )
        two = handshake.verify_peer_handshake_hello_json(
            raw,
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
        )
        self.assertEqual(one, two)
        compact = json.dumps(hello, separators=(",", ":"))
        pretty = json.dumps(hello, indent=2)
        self.assertEqual(
            handshake.verify_peer_handshake_hello_json(
                compact,
                expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
                expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
                logical_now=0,
                replay_set=set(),
            ),
            handshake.verify_peer_handshake_hello_json(
                pretty,
                expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
                expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
                logical_now=0,
                replay_set=set(),
            ),
        )


class IdentityMismatchTests(unittest.TestCase):
    def test_main_network_id_rejected(self) -> None:
        fx = _fixture()
        hello = handshake.build_handshake_hello(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-main").hexdigest(),
        )
        hello["network_id"] = "MAIN"
        hello["message_id"] = handshake.compute_peer_handshake_message_id(hello)
        result = handshake.verify_peer_handshake_hello_json(
            _wire(hello),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
        )
        self.assertIn(result.code, {"network_id_invalid", "historical_import_forbidden"})
        self.assertIs(result.execution_authorized, False)

    def test_wrong_genesis_digest_rejected(self) -> None:
        fx = _fixture()
        hello = handshake.build_handshake_hello(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-digest").hexdigest(),
        )
        result = handshake.verify_peer_handshake_hello_json(
            _wire(hello),
            expected_genesis_digest="a" * 64,
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
        )
        self.assertEqual(result.code, "genesis_digest_invalid")

    def test_canonical_environment_rejected(self) -> None:
        fx = _fixture()
        hello = handshake.build_handshake_hello(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-canon").hexdigest(),
        )
        hello["environment"] = "CANONICAL"
        hello["message_id"] = handshake.compute_peer_handshake_message_id(hello)
        result = handshake.verify_peer_handshake_hello_json(
            _wire(hello),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
        )
        self.assertEqual(result.code, "historical_import_forbidden")


class ReplayAndStaleTests(unittest.TestCase):
    def test_replay_detected(self) -> None:
        fx = _fixture()
        hello = handshake.build_handshake_hello(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-replay").hexdigest(),
        )
        replay = {hello["message_id"]}
        result = handshake.verify_peer_handshake_hello_json(
            _wire(hello),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=replay,
        )
        self.assertEqual(result.code, "replay_detected")

    def test_stale_message(self) -> None:
        fx = _fixture()
        hello = handshake.build_handshake_hello(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-stale").hexdigest(),
            issued_at_logical=0,
            expires_at_logical=60,
        )
        result = handshake.verify_peer_handshake_hello_json(
            _wire(hello),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=61,
            replay_set=set(),
        )
        self.assertEqual(result.code, "message_stale")

    def test_premature_message(self) -> None:
        fx = _fixture()
        hello = handshake.build_handshake_hello(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-early").hexdigest(),
            issued_at_logical=10,
            expires_at_logical=70,
        )
        result = handshake.verify_peer_handshake_hello_json(
            _wire(hello),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=5,
            replay_set=set(),
        )
        self.assertEqual(result.code, "message_premature")


class ChallengeResponseTests(unittest.TestCase):
    def test_response_forgery_rejected(self) -> None:
        fx = _fixture()
        hello = handshake.build_handshake_hello(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-h2").hexdigest(),
        )
        challenge = handshake.build_handshake_challenge(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-c2").hexdigest(),
            hello_message_id=hello["message_id"],
        )
        response = handshake.build_handshake_response(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-r2").hexdigest(),
            challenge=challenge,
        )
        response["response"] = "0" * 64
        response["message_id"] = handshake.compute_peer_handshake_message_id(response)
        result = handshake.verify_peer_handshake_response_json(
            _wire(response),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
            expected_challenge=challenge,
        )
        self.assertEqual(result.code, "response_invalid")


class MalformedMatrixTests(unittest.TestCase):
    def test_malformed_inputs(self) -> None:
        fx = _fixture()
        cases = (
            (object(), "input_type_invalid"),
            (b"x" * (handshake.MAX_HANDSHAKE_BYTES + 1), "input_too_large"),
            (bytes([255]), "encoding_invalid"),
            ("{", "json_invalid"),
            ("[]", "invalid_top_level"),
            ('{"a":1,"a":2}', "duplicate_key"),
        )
        for payload, code in cases:
            with self.subTest(code=code):
                result = handshake.verify_peer_handshake_message_json(
                    payload,  # type: ignore[arg-type]
                    expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
                    expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
                    logical_now=0,
                    replay_set=set(),
                )
                self.assertEqual(result.code, code)
                self.assertIs(result.execution_authorized, False)

    def test_unknown_field_and_reorder(self) -> None:
        fx = _fixture()
        hello = handshake.build_handshake_hello(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-schema").hexdigest(),
        )
        hello["extra"] = "nope"
        result = handshake.verify_peer_handshake_hello_json(
            _wire(hello),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
        )
        self.assertEqual(result.code, "schema_invalid")

        hello2 = handshake.build_handshake_hello(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-order").hexdigest(),
        )
        reordered = {k: hello2[k] for k in reversed(list(hello2.keys()))}
        result2 = handshake.verify_peer_handshake_hello_json(
            _wire(reordered),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
        )
        self.assertEqual(result2.code, "schema_invalid")

    def test_execution_authorized_true_rejected(self) -> None:
        fx = _fixture()
        hello = handshake.build_handshake_hello(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-exec").hexdigest(),
        )
        hello["execution_authorized"] = True
        hello["message_id"] = handshake.compute_peer_handshake_message_id(hello)
        result = handshake.verify_peer_handshake_hello_json(
            _wire(hello),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
        )
        self.assertEqual(result.code, "execution_authorized_invalid")
        self.assertIs(result.execution_authorized, False)


class LifecycleCleanupHygieneTests(unittest.TestCase):
    def test_lifecycle_and_cleanup(self) -> None:
        session = handshake.PeerHandshakeSession()
        self.assertEqual(session.state, "CREATED")
        session.transition("HELLO_RECEIVED")
        session.transition("CHALLENGED")
        session.transition("RESPONDED")
        session.transition("ACCEPTED")
        session.record_accepted(message_id="a" * 64, nonce="b" * 64)
        self.assertIn("a" * 64, session.replay_set)
        session.clear()
        self.assertEqual(session.state, "CLOSED")
        self.assertEqual(session.replay_set, set())
        with self.assertRaises(handshake._HandshakeError) as ctx:
            session.transition("HELLO_SENT")
        self.assertEqual(ctx.exception.code, "lifecycle_invalid")

    def test_temp_dir_cleanup(self) -> None:
        fx = _fixture()
        hello = handshake.build_handshake_hello(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-tmp").hexdigest(),
        )
        root = Path(tempfile.mkdtemp(prefix=f"{identity.DATA_DIR_TAG}-hs-"))
        try:
            path = root / "hello.json"
            path.write_bytes(_wire(hello))
            result = handshake.verify_peer_handshake_hello_json(
                path.read_bytes(),
                expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
                expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
                logical_now=0,
                replay_set=set(),
            )
            self.assertTrue(result.ok, result.code)
        finally:
            shutil.rmtree(root)
        self.assertFalse(root.exists())

    def test_static_hygiene(self) -> None:
        path = Path(handshake.__file__)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        modules = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        modules |= {
            (node.module or "").split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        self.assertFalse(
            modules
            & {
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
        )
        self.assertNotIn("Leap28", source)
        self.assertNotIn("Nova", source)
        self.assertIn("validate_disposable_handshake_identity_binding", source)


class StableErrorCoverageTests(unittest.TestCase):
    def _hello(self, fx: dict[str, object], *, nonce_seed: bytes) -> dict[str, object]:
        return handshake.build_handshake_hello(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(nonce_seed).hexdigest(),
        )

    def _assert_fail(self, result: handshake.PeerHandshakeResult, code: str) -> None:
        self.assertFalse(result.ok)
        self.assertEqual(result.code, code)
        self.assertIs(result.execution_authorized, False)

    def test_handshake_version_unsupported(self) -> None:
        fx = _fixture()
        hello = self._hello(fx, nonce_seed=b"err-version")
        hello["handshake_version"] = "l28-peer-handshake-identity-binding/v9.9.9"
        hello["message_id"] = handshake.compute_peer_handshake_message_id(hello)
        result = handshake.verify_peer_handshake_hello_json(
            _wire(hello),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
        )
        self._assert_fail(result, "handshake_version_unsupported")

    def test_message_type_invalid(self) -> None:
        fx = _fixture()
        hello = self._hello(fx, nonce_seed=b"err-type")
        hello["message_type"] = "handshake_nope"
        hello["message_id"] = handshake.compute_peer_handshake_message_id(hello)
        result = handshake.verify_peer_handshake_message_json(
            _wire(hello),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
        )
        self._assert_fail(result, "message_type_invalid")

    def test_environment_invalid(self) -> None:
        fx = _fixture()
        hello = self._hello(fx, nonce_seed=b"err-env")
        hello["environment"] = "DISPOSABLE_OTHER"
        hello["message_id"] = handshake.compute_peer_handshake_message_id(hello)
        result = handshake.verify_peer_handshake_hello_json(
            _wire(hello),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
        )
        self._assert_fail(result, "environment_invalid")

    def test_protocol_version_invalid(self) -> None:
        fx = _fixture()
        hello = self._hello(fx, nonce_seed=b"err-proto")
        hello["protocol_version"] = "l28-protocol/9.9.9"
        hello["message_id"] = handshake.compute_peer_handshake_message_id(hello)
        result = handshake.verify_peer_handshake_hello_json(
            _wire(hello),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
        )
        self._assert_fail(result, "protocol_version_invalid")

    def test_chain_id_invalid(self) -> None:
        fx = _fixture()
        hello = self._hello(fx, nonce_seed=b"err-chain")
        result = handshake.verify_peer_handshake_hello_json(
            _wire(hello),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id="0" * 64,
            logical_now=0,
            replay_set=set(),
        )
        self._assert_fail(result, "chain_id_invalid")

    def test_peer_identity_invalid(self) -> None:
        fx = _fixture()
        hello = self._hello(fx, nonce_seed=b"err-peer")
        hello["peer"] = dict(hello["peer"])  # type: ignore[arg-type]
        hello["peer"]["peer_id"] = "0" * 64  # type: ignore[index]
        hello["message_id"] = handshake.compute_peer_handshake_message_id(hello)
        result = handshake.verify_peer_handshake_hello_json(
            _wire(hello),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
        )
        self._assert_fail(result, "peer_identity_invalid")

    def test_challenge_invalid(self) -> None:
        fx = _fixture()
        hello = self._hello(fx, nonce_seed=b"err-chal-hello")
        challenge = handshake.build_handshake_challenge(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"err-chal").hexdigest(),
            hello_message_id=hello["message_id"],  # type: ignore[arg-type]
        )
        challenge["challenge_id"] = "0" * 64
        challenge["message_id"] = handshake.compute_peer_handshake_message_id(challenge)
        result = handshake.verify_peer_handshake_challenge_json(
            _wire(challenge),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
            expected_hello_message_id=hello["message_id"],  # type: ignore[arg-type]
        )
        self._assert_fail(result, "challenge_invalid")

    def test_binding_mismatch(self) -> None:
        fx = _fixture()
        hello = self._hello(fx, nonce_seed=b"err-bind-hello")
        challenge = handshake.build_handshake_challenge(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"err-bind").hexdigest(),
            hello_message_id=hello["message_id"],  # type: ignore[arg-type]
        )
        result = handshake.verify_peer_handshake_challenge_json(
            _wire(challenge),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
            expected_hello_message_id="f" * 64,
        )
        self._assert_fail(result, "binding_mismatch")

    def test_internal_error_via_public_api_monkeypatch(self) -> None:
        fx = _fixture()
        hello = self._hello(fx, nonce_seed=b"err-internal")
        with mock.patch.object(
            handshake,
            "_parse",
            side_effect=RuntimeError("forced-unexpected-failure"),
        ):
            first = handshake.verify_peer_handshake_message_json(
                _wire(hello),
                expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
                expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
                logical_now=0,
                replay_set=set(),
            )
            second = handshake.verify_peer_handshake_message_json(
                _wire(hello),
                expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
                expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
                logical_now=0,
                replay_set=set(),
            )
        self._assert_fail(first, "internal_error")
        self.assertEqual(first, second)
        self.assertNotIn("forced-unexpected-failure", first.code)
        self.assertNotIn("Traceback", first.code)

    def test_all_26_stable_errors_are_explicitly_asserted(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        required = (
            "ok",
            "input_type_invalid",
            "input_too_large",
            "encoding_invalid",
            "json_invalid",
            "duplicate_key",
            "invalid_top_level",
            "schema_invalid",
            "handshake_version_unsupported",
            "message_type_invalid",
            "environment_invalid",
            "network_id_invalid",
            "protocol_version_invalid",
            "chain_id_invalid",
            "genesis_digest_invalid",
            "peer_identity_invalid",
            "challenge_invalid",
            "response_invalid",
            "binding_mismatch",
            "replay_detected",
            "message_stale",
            "message_premature",
            "historical_import_forbidden",
            "execution_authorized_invalid",
            "lifecycle_invalid",
            "internal_error",
        )
        self.assertEqual(required, handshake.STABLE_CODES)
        missing = [
            code
            for code in required
            if f'"{code}"' not in source and f"'{code}'" not in source
        ]
        self.assertEqual(missing, [], missing)
        fx = _fixture()
        hello = self._hello(fx, nonce_seed=b"err-ok-code")
        ok_result = handshake.verify_peer_handshake_hello_json(
            _wire(hello),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
        )
        self.assertTrue(ok_result.ok)
        self.assertEqual(ok_result.code, "ok")
        self.assertIs(ok_result.execution_authorized, False)


class FixtureReportTests(unittest.TestCase):
    def test_report_deterministic_values(self) -> None:
        fx = _fixture()
        hello = handshake.build_handshake_hello(
            chain_id=fx["chain_id"],  # type: ignore[arg-type]
            genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            session_id=fx["session_id"],  # type: ignore[arg-type]
            peer=fx["peer"],  # type: ignore[arg-type]
            nonce=hashlib.sha256(b"nonce-report").hexdigest(),
        )
        result = handshake.verify_peer_handshake_hello_json(
            _wire(hello),
            expected_genesis_digest=fx["genesis_digest"],  # type: ignore[arg-type]
            expected_chain_id=fx["chain_id"],  # type: ignore[arg-type]
            logical_now=0,
            replay_set=set(),
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.chain_id, fx["chain_id"])
        self.assertEqual(result.genesis_digest, fx["genesis_digest"])
        self.assertEqual(result.network_id, identity.NETWORK_ID)
        self.assertEqual(result.protocol_version, identity.PROTOCOL_VERSION)


if __name__ == "__main__":
    unittest.main()
