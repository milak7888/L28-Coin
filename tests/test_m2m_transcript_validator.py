# SPDX-License-Identifier: Apache-2.0
"""
Offline tests for Foundation 6 M2M exchange transcript validation.

TEST-ONLY. Does not generate keys, sign messages, write ledger data,
or perform network operations.
"""
from __future__ import annotations

import ast
import copy
import json
import unittest
from pathlib import Path
from typing import Any, Set

from coin.m2m_transcript_validator import (
    MAX_TRANSCRIPT_MESSAGES,
    STABLE_CODES,
    verify_transcript,
    verify_transcript_json,
)

ROOT = Path(__file__).resolve().parents[1]
VECTOR_PATH = ROOT / "docs" / "m2m" / "test_vectors_transcript_v0.1.json"
RUNTIME_PATHS = (
    ROOT / "coin" / "m2m_transcript_validator.py",
    ROOT / "coin" / "m2m_verifier.py",
)
TEST_PATHS = (
    ROOT / "tests" / "test_m2m_transcript_validator.py",
    ROOT / "tests" / "test_m2m_ed25519_verifier.py",
    ROOT / "tests" / "test_m2m_interoperability_profile.py",
)

FORBIDDEN_IMPORT_NAMES = frozenset({"Ed25519PrivateKey", "from_private_bytes"})
FORBIDDEN_VECTOR_KEYS = frozenset(
    {
        "private_key",
        "seed",
        "seed_phrase",
        "mnemonic",
        "wallet_credential",
        "wallet_secret",
        "signing_secret",
        "secret_key",
    }
)


def _collect_keys(obj: Any, out: Set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(str(k))
            _collect_keys(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_keys(item, out)


class TestM2MTranscriptValidator(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doc = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
        cls.valid = {v["vector_id"]: v for v in cls.doc["valid_transcripts"]}
        cls.invalid = {v["vector_id"]: v for v in cls.doc["invalid_transcripts"]}

    def test_metadata(self):
        self.assertTrue(self.doc["test_only"])
        self.assertFalse(self.doc["live"])
        self.assertFalse(self.doc["accepted_settlement"])
        self.assertFalse(self.doc["private_material_committed"])
        self.assertEqual(len(self.valid), 3)
        self.assertGreaterEqual(len(self.invalid), 20)

    def test_valid_vectors(self):
        for vector_id, vec in self.valid.items():
            with self.subTest(vector_id):
                envelopes = copy.deepcopy(vec["envelopes"])
                before = json.dumps(envelopes, sort_keys=True)
                result = verify_transcript(
                    envelopes,
                    require_terminal=bool(vec["require_terminal"]),
                )
                after = json.dumps(envelopes, sort_keys=True)
                self.assertEqual(before, after)
                self.assertTrue(result.ok, result)
                self.assertEqual(result.code, "ok")
                self.assertEqual(result.state, vec["expected_state"])
                self.assertEqual(result.verified_messages, len(vec["envelopes"]))
                self.assertTrue(vec["test_only"])
                self.assertFalse(vec["accepted_settlement"])

    def test_invalid_vectors(self):
        for vector_id, vec in self.invalid.items():
            with self.subTest(vector_id):
                result = verify_transcript(
                    vec["envelopes"],
                    require_terminal=bool(vec["require_terminal"]),
                )
                self.assertFalse(result.ok, result)
                self.assertEqual(result.code, vec["expected_code"])
                if "expected_envelope_code" in vec:
                    self.assertEqual(result.envelope_code, vec["expected_envelope_code"])

    def test_happy_path_completed(self):
        vec = self.valid["valid_happy_path_completed"]
        result = verify_transcript(vec["envelopes"], require_terminal=True)
        self.assertTrue(result.ok)
        self.assertEqual(result.state, "completed")
        self.assertEqual(result.verified_messages, 5)
        self.assertIsNotNone(result.settlement_transaction_id)
        self.assertEqual(
            result.settlement_transaction_id,
            self.doc["l28_settlement_fixture"]["expected_l28_tx_id"],
        )

    def test_partial_and_require_terminal(self):
        vec = self.valid["valid_partial_quoted"]
        ok = verify_transcript(vec["envelopes"], require_terminal=False)
        self.assertTrue(ok.ok)
        self.assertEqual(ok.state, "quoted")
        incomplete = verify_transcript(vec["envelopes"], require_terminal=True)
        self.assertFalse(incomplete.ok)
        self.assertEqual(incomplete.code, "incomplete_transcript")
        self.assertEqual(incomplete.state, "quoted")

    def test_terminal_cancelled(self):
        vec = self.valid["valid_terminal_cancelled"]
        result = verify_transcript(vec["envelopes"], require_terminal=True)
        self.assertTrue(result.ok)
        self.assertEqual(result.state, "cancelled")

    def test_raw_json_duplicate_key(self):
        raw = '[{"protocol":"L28-M2M","protocol":"DUP"}]'
        result = verify_transcript_json(raw)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "duplicate_key")

    def test_raw_json_malformed_utf8(self):
        result = verify_transcript_json(b"\xff\xfe[")
        self.assertEqual(result.code, "invalid_json")

    def test_raw_json_not_array(self):
        result = verify_transcript_json('{"a":1}')
        self.assertEqual(result.code, "transcript_not_array")

    def test_empty_transcript(self):
        result = verify_transcript([])
        self.assertEqual(result.code, "empty_transcript")
        result_json = verify_transcript_json("[]")
        self.assertEqual(result_json.code, "empty_transcript")

    def test_transcript_too_large(self):
        env = copy.deepcopy(self.valid["valid_partial_quoted"]["envelopes"][0])
        huge = [env] * (MAX_TRANSCRIPT_MESSAGES + 1)
        result = verify_transcript(huge)
        self.assertEqual(result.code, "transcript_too_large")

    def test_element_not_object(self):
        result = verify_transcript_json("[1]")
        self.assertEqual(result.code, "transcript_element_not_object")

    def test_input_envelopes_unchanged(self):
        vec = self.valid["valid_happy_path_completed"]
        envelopes = copy.deepcopy(vec["envelopes"])
        snapshot = copy.deepcopy(envelopes)
        verify_transcript(envelopes, require_terminal=True)
        self.assertEqual(envelopes, snapshot)

    def test_stable_codes_bounded(self):
        required = {
            "ok",
            "invalid_json",
            "duplicate_key",
            "transcript_not_array",
            "empty_transcript",
            "transcript_too_large",
            "transcript_element_not_object",
            "envelope_verification_failed",
            "exchange_id_mismatch",
            "first_message_not_request",
            "invalid_first_previous_message",
            "message_chain_broken",
            "duplicate_message_id",
            "duplicate_nonce",
            "timestamp_regression",
            "prior_message_expired",
            "participant_mismatch",
            "role_mismatch",
            "invalid_transition",
            "message_after_terminal",
            "incomplete_transcript",
            "invalid_terminal_state",
            "unauthorized_terminal_transition",
            "quote_reference_mismatch",
            "amount_mismatch",
            "service_terms_mismatch",
            "settlement_participant_mismatch",
            "settlement_citation_invalid",
            "receipt_reference_mismatch",
        }
        self.assertTrue(required.issubset(STABLE_CODES))

    def test_ast_no_private_key_apis(self):
        for path in (*RUNTIME_PATHS, *TEST_PATHS):
            with self.subTest(path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            if alias.name in FORBIDDEN_IMPORT_NAMES:
                                self.fail(f"{path.name} imports {alias.name}")
                    if isinstance(node, ast.Call):
                        func = node.func
                        if isinstance(func, ast.Attribute) and func.attr in {"generate", "sign"}:
                            # Allow Attribute named verify only; forbid generate/sign calls.
                            self.fail(f"{path.name} calls forbidden {func.attr}()")

    def test_vector_keys_no_private_material(self):
        keys: Set[str] = set()
        _collect_keys(self.doc, keys)
        offenders = sorted(k for k in keys if k.lower() in FORBIDDEN_VECTOR_KEYS)
        self.assertEqual(offenders, [])

    def test_no_repo_data_side_effects(self):
        data_dir = ROOT / "data"
        self.assertFalse(data_dir.exists() and any(data_dir.rglob("shard_*.jsonl")))

    def test_json_roundtrip_happy_path(self):
        vec = self.valid["valid_happy_path_completed"]
        raw = json.dumps(vec["envelopes"], separators=(",", ":"), ensure_ascii=False)
        result = verify_transcript_json(raw, require_terminal=True)
        self.assertTrue(result.ok)
        self.assertEqual(result.state, "completed")


if __name__ == "__main__":
    unittest.main()
