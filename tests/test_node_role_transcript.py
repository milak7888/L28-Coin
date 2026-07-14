"""Adversarial tests for the offline node-role transcript verifier."""

from __future__ import annotations

import ast
from dataclasses import fields
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

from coin import node_role_transcript as transcript


def _entry(
    sequence: int,
    previous_state: str,
    requested_state: str,
    resulting_state: str,
    *,
    ok: bool = True,
    code: str = "transitioned",
) -> dict[str, object]:
    return {
        "sequence": sequence,
        "previous_state": previous_state,
        "requested_state": requested_state,
        "resulting_state": resulting_state,
        "ok": ok,
        "code": code,
    }


def _document(
    role: str,
    transitions: list[dict[str, object]],
    final_state: str = "STOPPED",
) -> dict[str, object]:
    return {
        "transcript_version": transcript.TRANSCRIPT_VERSION,
        "model_version": transcript.MODEL_VERSION,
        "role": role,
        "initial_state": "CREATED",
        "transitions": transitions,
        "final_state": final_state,
    }


def _core_document() -> dict[str, object]:
    return _document(
        transcript.CORE_ROLE,
        [
            _entry(0, "CREATED", "EVIDENCE_ONLY", "EVIDENCE_ONLY"),
            _entry(1, "EVIDENCE_ONLY", "PAUSED", "PAUSED"),
            _entry(2, "PAUSED", "STOPPED", "STOPPED"),
        ],
    )


def _p2p_document() -> dict[str, object]:
    return _document(
        transcript.P2P_ROLE,
        [
            _entry(0, "CREATED", "CONFIGURED", "CONFIGURED"),
            _entry(1, "CONFIGURED", "PAUSED", "PAUSED"),
            _entry(2, "PAUSED", "STOPPED", "STOPPED"),
        ],
    )


def _verify(document: object) -> transcript.NodeRoleTranscriptResult:
    return transcript.verify_transcript_json(
        json.dumps(document, separators=(",", ":"), sort_keys=True)
    )


class NodeRoleTranscriptTests(unittest.TestCase):
    def test_valid_core_and_p2p_transcripts(self) -> None:
        for document, role in (
            (_core_document(), transcript.CORE_ROLE),
            (_p2p_document(), transcript.P2P_ROLE),
        ):
            with self.subTest(role=role):
                result = _verify(document)
                self.assertTrue(result.ok)
                self.assertEqual(result.code, "transcript_valid")
                self.assertEqual(result.role, role)
                self.assertEqual(result.initial_state, "CREATED")
                self.assertEqual(result.final_state, "STOPPED")
                self.assertEqual(result.transition_count, 3)
                self.assertEqual(result.checks, transcript.SUCCESS_CHECKS)
                self.assertEqual(len(result.transcript_sha256), 64)

    def test_semantically_identical_reformatting_is_deterministic(self) -> None:
        document = _core_document()
        compact = json.dumps(document, separators=(",", ":"), sort_keys=True)
        pretty = json.dumps(document, indent=4, sort_keys=False)

        compact_result = transcript.verify_transcript_json(compact)
        pretty_result = transcript.verify_transcript_json(pretty)

        self.assertEqual(compact_result, pretty_result)
        self.assertTrue(compact_result.ok)

    def test_semantic_commitment_is_body_bound(self) -> None:
        first = _verify(_core_document())
        second = _verify(
            _document(
                transcript.CORE_ROLE,
                [
                    _entry(0, "CREATED", "PAUSED", "PAUSED"),
                    _entry(1, "PAUSED", "STOPPED", "STOPPED"),
                ],
            )
        )

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertNotEqual(first.transcript_sha256, second.transcript_sha256)

    def test_reserved_state_attempt_may_only_be_recorded_as_rejected(self) -> None:
        document = _document(
            transcript.CORE_ROLE,
            [
                _entry(
                    0,
                    "CREATED",
                    "RUNNING_RESERVED",
                    "CREATED",
                    ok=False,
                    code="reserved_state_unreachable",
                ),
                _entry(1, "CREATED", "PAUSED", "PAUSED"),
                _entry(2, "PAUSED", "STOPPED", "STOPPED"),
            ],
        )

        result = _verify(document)
        self.assertTrue(result.ok)
        self.assertEqual(result.final_state, "STOPPED")

        document["transitions"][0]["resulting_state"] = "RUNNING_RESERVED"
        result = _verify(document)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "transition_mismatch")

    def test_unknown_and_disallowed_attempts_can_be_verified_as_rejected(self) -> None:
        for requested_state, code in (
            ("UNKNOWN_STATE", "state_invalid"),
            ("STOPPED", "transition_not_allowed"),
        ):
            with self.subTest(requested_state=requested_state):
                document = _document(
                    transcript.CORE_ROLE,
                    [
                        _entry(
                            0,
                            "CREATED",
                            requested_state,
                            "CREATED",
                            ok=False,
                            code=code,
                        ),
                        _entry(1, "CREATED", "PAUSED", "PAUSED"),
                        _entry(2, "PAUSED", "STOPPED", "STOPPED"),
                    ],
                )
                self.assertTrue(_verify(document).ok)

    def test_declared_transition_fields_must_match_model_exactly(self) -> None:
        mutations = {
            "previous_state": "FAILED",
            "requested_state": "FAILED",
            "resulting_state": "FAILED",
            "ok": False,
            "code": "transition_not_allowed",
        }

        for field, value in mutations.items():
            with self.subTest(field=field):
                document = _core_document()
                document["transitions"][0][field] = value
                result = _verify(document)
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "transition_mismatch")

    def test_sequence_must_be_zero_based_and_contiguous(self) -> None:
        for index, replacement in ((0, 1), (1, 4), (2, True)):
            with self.subTest(index=index, replacement=replacement):
                document = _core_document()
                document["transitions"][index]["sequence"] = replacement
                result = _verify(document)
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "sequence_invalid")

    def test_initial_state_role_and_versions_fail_closed(self) -> None:
        cases = (
            ("initial_state", "PAUSED", "initial_state_invalid"),
            ("role", "UnknownNode", "role_invalid"),
            (
                "transcript_version",
                "l28-node-role-transcript/v9",
                "version_unsupported",
            ),
            ("model_version", "l28-node-role-model/v9", "version_unsupported"),
        )

        for field, value, expected_code in cases:
            with self.subTest(field=field):
                document = _core_document()
                document[field] = value
                result = _verify(document)
                self.assertFalse(result.ok)
                self.assertEqual(result.code, expected_code)

    def test_final_state_must_match_replay_and_be_stopped(self) -> None:
        mismatch = _core_document()
        mismatch["final_state"] = "PAUSED"

        result = _verify(mismatch)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "final_state_mismatch")

        incomplete = _document(
            transcript.CORE_ROLE,
            [_entry(0, "CREATED", "PAUSED", "PAUSED")],
            final_state="PAUSED",
        )

        result = _verify(incomplete)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "terminal_state_required")

    def test_missing_extra_and_wrongly_typed_fields_fail_schema(self) -> None:
        documents = []

        missing_top = _core_document()
        del missing_top["role"]
        documents.append(missing_top)

        extra_top = _core_document()
        extra_top["unexpected"] = False
        documents.append(extra_top)

        missing_entry = _core_document()
        del missing_entry["transitions"][0]["code"]
        documents.append(missing_entry)

        extra_entry = _core_document()
        extra_entry["transitions"][0]["unexpected"] = "value"
        documents.append(extra_entry)

        wrong_transitions = _core_document()
        wrong_transitions["transitions"] = {}
        documents.append(wrong_transitions)

        wrong_ok = _core_document()
        wrong_ok["transitions"][0]["ok"] = 1
        documents.append(wrong_ok)

        bad_code = _core_document()
        bad_code["transitions"][0]["code"] = "invented_code"
        documents.append(bad_code)

        for index, document in enumerate(documents):
            with self.subTest(index=index):
                result = _verify(document)
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "schema_error")

    def test_empty_and_excessive_transition_counts_are_rejected(self) -> None:
        empty = _document(transcript.CORE_ROLE, [])
        result = _verify(empty)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "transition_count_invalid")

        repeated = [
            _entry(index, "CREATED", "PAUSED", "PAUSED")
            for index in range(transcript.MAX_TRANSITIONS + 1)
        ]
        excessive = _document(transcript.CORE_ROLE, repeated)

        result = _verify(excessive)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "transition_count_invalid")

    def test_duplicate_keys_are_rejected_at_any_depth(self) -> None:
        top_level = (
            '{"transcript_version":"l28-node-role-transcript/v0.1",'
            '"transcript_version":"l28-node-role-transcript/v0.1"}'
        )
        nested = (
            '{"transcript_version":"l28-node-role-transcript/v0.1",'
            '"model_version":"l28-node-role-model/v0.1",'
            '"role":"CoreL28Node","initial_state":"CREATED",'
            '"transitions":[{"sequence":0,"sequence":0}],'
            '"final_state":"STOPPED"}'
        )

        for payload in (top_level, nested):
            with self.subTest(payload=payload):
                result = transcript.verify_transcript_json(payload)
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "duplicate_key")

    def test_invalid_json_encoding_nonfinite_and_input_type_are_rejected(self) -> None:
        cases = (
            ("{", "invalid_json"),
            ('{"value":NaN}', "invalid_json"),
            (b"\xff", "invalid_encoding"),
            (object(), "input_type_invalid"),
        )

        for payload, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                result = transcript.verify_transcript_json(payload)
                self.assertFalse(result.ok)
                self.assertEqual(result.code, expected_code)

    def test_oversized_input_is_rejected_before_parsing(self) -> None:
        payload = "{" + (" " * transcript.MAX_TRANSCRIPT_BYTES)
        result = transcript.verify_transcript_json(payload)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "transcript_too_large")
        self.assertEqual(result.transcript_sha256, "")

    def test_verification_does_not_modify_input_or_model_state(self) -> None:
        document = _core_document()
        before = json.dumps(document, sort_keys=True)
        payload = json.dumps(document)

        first = transcript.verify_transcript_json(payload)
        second = transcript.verify_transcript_json(payload)

        self.assertEqual(first, second)
        self.assertEqual(json.dumps(document, sort_keys=True), before)

        model = transcript.CoreNodeRoleModel()
        transcript.verify_transcript_json(payload)
        self.assertEqual(model.state, "CREATED")

    def test_internal_exception_is_sanitized(self) -> None:
        with mock.patch.object(
            transcript,
            "_parse_json",
            side_effect=RuntimeError("sensitive internal text"),
        ):
            result = transcript.verify_transcript_json("{}")

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "internal_error")
        self.assertEqual(result.detail, "")
        self.assertNotIn("sensitive", repr(result))

    def test_result_fields_and_stable_codes_are_explicit(self) -> None:
        self.assertEqual(
            tuple(field.name for field in fields(transcript.NodeRoleTranscriptResult)),
            (
                "ok",
                "code",
                "role",
                "initial_state",
                "final_state",
                "transition_count",
                "transcript_sha256",
                "checks",
                "detail",
                "transcript_version",
                "model_version",
                "verifier_version",
            ),
        )

        self.assertEqual(len(transcript.STABLE_CODES), len(set(transcript.STABLE_CODES)))
        self.assertEqual(
            transcript.STABLE_CODES,
            (
                "transcript_valid",
                "input_type_invalid",
                "transcript_too_large",
                "invalid_encoding",
                "invalid_json",
                "duplicate_key",
                "schema_error",
                "version_unsupported",
                "role_invalid",
                "initial_state_invalid",
                "transition_count_invalid",
                "sequence_invalid",
                "transition_mismatch",
                "final_state_mismatch",
                "terminal_state_required",
                "internal_error",
            ),
        )

    def test_production_module_has_no_io_or_activation_imports(self) -> None:
        path = Path(transcript.__file__)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))

        forbidden_imports = {
            "asyncio",
            "multiprocessing",
            "os",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "threading",
            "urllib",
        }

        observed_imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                observed_imports.update(
                    alias.name.split(".", 1)[0] for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.module:
                observed_imports.add(node.module.lstrip(".").split(".", 1)[0])

            if isinstance(node, ast.Call):
                self.assertNotIn(
                    ast.unparse(node.func),
                    {"open", "exec", "eval", "compile", "__import__"},
                )

        self.assertFalse(observed_imports & forbidden_imports)

    def test_canonical_sha256_matches_public_algorithm(self) -> None:
        document = _core_document()
        canonical = json.dumps(
            document,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

        result = _verify(document)

        self.assertTrue(result.ok)
        self.assertEqual(
            result.transcript_sha256,
            hashlib.sha256(canonical).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
