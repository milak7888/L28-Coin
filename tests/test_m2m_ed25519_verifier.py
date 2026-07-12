# SPDX-License-Identifier: Apache-2.0
"""
Offline tests for Foundation 5 Ed25519 M2M envelope verification.

TEST-ONLY. Does not generate keys, sign messages, write ledger data,
or perform network operations.
"""
from __future__ import annotations

import ast
import copy
import json
import unittest
from pathlib import Path
from typing import Any, Dict, Set

from coin.m2m_verifier import (
    STABLE_CODES,
    canonical_bytes,
    encode_b64url_unpadded,
    message_id_for,
    payload_hash_for,
    signature_preimage_for,
    unsigned_envelope,
    verify_envelope,
    verify_envelope_json,
    verify_settlement_citation,
)

ROOT = Path(__file__).resolve().parents[1]
UNSIGNED_PATH = ROOT / "docs" / "m2m" / "test_vectors_v0.1.json"
SIGNED_PATH = ROOT / "docs" / "m2m" / "test_vectors_signed_v0.1.json"
VERIFIER_PATH = ROOT / "coin" / "m2m_verifier.py"
TEST_PATHS = (
    ROOT / "tests" / "test_m2m_ed25519_verifier.py",
    ROOT / "tests" / "test_m2m_interoperability_profile.py",
)

# Exact forbidden identifiers in runtime/test Python ASTs (imports/attributes/calls).
FORBIDDEN_IMPORT_NAMES = frozenset(
    {
        "Ed25519PrivateKey",
        "from_private_bytes",
    }
)
FORBIDDEN_ATTR_NAMES = frozenset(
    {
        "from_private_bytes",
        "private_bytes_raw",
        "private_bytes",
    }
)

# Forbidden JSON field names in committed vector artifacts (exact keys).
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


def _mutated_env(env: Dict[str, Any], **updates: Any) -> Dict[str, Any]:
    out = copy.deepcopy(env)
    out.update(updates)
    return out


class TestM2MEd25519Verifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.unsigned_doc = json.loads(UNSIGNED_PATH.read_text(encoding="utf-8"))
        cls.signed_doc = json.loads(SIGNED_PATH.read_text(encoding="utf-8"))
        cls.signed = {v["vector_id"]: v for v in cls.signed_doc["signed_vectors"]}

    def test_signed_vectors_metadata(self):
        self.assertTrue(self.signed_doc["test_only"])
        self.assertFalse(self.signed_doc["live"])
        self.assertFalse(self.signed_doc["accepted_settlement"])
        self.assertFalse(self.signed_doc["private_material_committed"])
        self.assertFalse(self.signed_doc["contains_private_material"])
        self.assertEqual(len(self.signed_doc["signed_vectors"]), 3)
        self.assertEqual(
            set(self.signed),
            {
                "signed_service_request",
                "signed_chained_service_quote",
                "signed_settlement_reference",
            },
        )

    def test_verify_all_signed_vectors(self):
        for vector_id, vec in self.signed.items():
            with self.subTest(vector_id):
                env = vec["envelope"]
                result = verify_envelope(env)
                self.assertTrue(result.ok, result)
                self.assertEqual(result.code, "ok")
                self.assertEqual(result.message_id, vec["message_id"])
                self.assertEqual(result.message_id, env["message_id"])

                self.assertEqual(canonical_bytes(env["payload"]).hex(), vec["canonical_payload_hex"])
                self.assertEqual(payload_hash_for(env["payload"]), vec["payload_hash"])
                self.assertEqual(
                    canonical_bytes(unsigned_envelope(env)).hex(),
                    vec["canonical_unsigned_envelope_hex"],
                )
                self.assertEqual(message_id_for(env), vec["message_id"])
                self.assertEqual(signature_preimage_for(env).hex(), vec["signature_preimage_hex"])
                self.assertEqual(env["sender_public_key"], vec["public_key_b64url"])
                self.assertEqual(env["signature"], vec["signature_b64url"])
                self.assertTrue(vec["test_only"])
                self.assertFalse(vec["live"])
                self.assertFalse(vec["accepted_settlement"])
                self.assertFalse(vec["private_material_committed"])

                raw = json.dumps(env, separators=(",", ":"), ensure_ascii=False)
                raw_result = verify_envelope_json(raw)
                self.assertTrue(raw_result.ok, raw_result)

    def test_settlement_citation_on_signed_vector(self):
        vec = self.signed["signed_settlement_reference"]
        citation = verify_settlement_citation(vec["envelope"]["payload"])
        self.assertTrue(citation.ok)
        self.assertEqual(citation.code, "settlement_citation_valid")
        self.assertEqual(
            citation.l28_transaction_id,
            self.signed_doc["l28_settlement_fixture"]["expected_l28_tx_id"],
        )
        env_result = verify_envelope(vec["envelope"])
        self.assertTrue(env_result.ok)
        self.assertEqual(env_result.l28_transaction_id, citation.l28_transaction_id)

    def test_unsigned_foundation4_vectors_not_operational(self):
        for vec in self.unsigned_doc["valid_unsigned_vectors"]:
            with self.subTest(vec["vector_id"]):
                result = verify_envelope(vec["envelope"])
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "unsigned_envelope")

    def test_wrong_public_key(self):
        env = copy.deepcopy(self.signed["signed_service_request"]["envelope"])
        other = self.signed["signed_chained_service_quote"]["envelope"]["sender_public_key"]
        env["sender_public_key"] = other
        env["sender_key_id"] = f"ed25519:{other}"
        # Digests change when identity fields change; recompute so we hit signature failure.
        env["payload_hash"] = payload_hash_for(env["payload"])
        env["message_id"] = message_id_for(env)
        result = verify_envelope(env)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "bad_signature")

    def test_altered_signature(self):
        env = copy.deepcopy(self.signed["signed_service_request"]["envelope"])
        raw = bytearray(
            __import__("base64").urlsafe_b64decode(
                env["signature"] + "=" * ((4 - len(env["signature"]) % 4) % 4)
            )
        )
        raw[0] ^= 0x01
        env["signature"] = encode_b64url_unpadded(bytes(raw))
        result = verify_envelope(env)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "bad_signature")

    def test_altered_payload(self):
        env = copy.deepcopy(self.signed["signed_service_request"]["envelope"])
        env["payload"] = dict(env["payload"])
        env["payload"]["max_amount"] = 27
        # Keep transmitted digests so mismatch is detected before/at digest stage.
        result = verify_envelope(env)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "mismatched_payload_hash")

    def test_altered_previous_message_id(self):
        env = copy.deepcopy(self.signed["signed_chained_service_quote"]["envelope"])
        env["previous_message_id"] = "0" * 64
        result = verify_envelope(env)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "mismatched_message_id")

    def test_altered_settlement_transaction(self):
        env = copy.deepcopy(self.signed["signed_settlement_reference"]["envelope"])
        env["payload"] = dict(env["payload"])
        material = dict(env["payload"]["l28_transaction_material"])
        material["amount"] = 29
        env["payload"]["l28_transaction_material"] = material
        # Recompute digests so citation check runs before signature verification.
        env["payload_hash"] = payload_hash_for(env["payload"])
        env["message_id"] = message_id_for(env)
        result = verify_envelope(env)
        self.assertEqual(result.code, "altered_settlement_material")

    def test_mismatched_payload_hash(self):
        env = _mutated_env(
            self.signed["signed_service_request"]["envelope"],
            payload_hash="0" * 64,
        )
        result = verify_envelope(env)
        self.assertEqual(result.code, "mismatched_payload_hash")

    def test_mismatched_message_id(self):
        env = _mutated_env(
            self.signed["signed_service_request"]["envelope"],
            message_id="1" * 64,
        )
        result = verify_envelope(env)
        self.assertEqual(result.code, "mismatched_message_id")

    def test_padded_base64url(self):
        env = copy.deepcopy(self.signed["signed_service_request"]["envelope"])
        env["signature"] = env["signature"] + "="
        result = verify_envelope(env)
        self.assertEqual(result.code, "padded_base64url")

    def test_invalid_base64url(self):
        env = _mutated_env(
            self.signed["signed_service_request"]["envelope"],
            signature="!!!not-base64url!!!",
        )
        result = verify_envelope(env)
        self.assertEqual(result.code, "malformed_base64url")

    def test_wrong_key_length(self):
        env = copy.deepcopy(self.signed["signed_service_request"]["envelope"])
        short_pk = encode_b64url_unpadded(b"\x00" * 16)
        env["sender_public_key"] = short_pk
        env["sender_key_id"] = f"ed25519:{short_pk}"
        env["payload_hash"] = payload_hash_for(env["payload"])
        env["message_id"] = message_id_for(env)
        result = verify_envelope(env)
        self.assertEqual(result.code, "malformed_public_key_length")

    def test_wrong_signature_length(self):
        env = _mutated_env(
            self.signed["signed_service_request"]["envelope"],
            signature=encode_b64url_unpadded(b"\x00" * 32),
        )
        result = verify_envelope(env)
        self.assertEqual(result.code, "malformed_signature_length")

    def test_unsigned_envelope(self):
        env = copy.deepcopy(self.signed["signed_service_request"]["envelope"])
        del env["signature"]
        result = verify_envelope(env)
        self.assertEqual(result.code, "unsigned_envelope")

    def test_unknown_suite(self):
        env = _mutated_env(
            self.signed["signed_service_request"]["envelope"],
            signature_suite="rsa-pss",
        )
        result = verify_envelope(env)
        self.assertEqual(result.code, "unknown_suite")

    def test_duplicate_json_key_raw_boundary(self):
        result = verify_envelope_json('{"protocol":"L28-M2M","protocol":"DUP"}')
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "duplicate_key")

    def test_malformed_utf8(self):
        result = verify_envelope_json(b"\xff\xfe{")
        self.assertEqual(result.code, "invalid_json")

    def test_float_rejected(self):
        result = verify_envelope_json('{"amount":1.5}')
        self.assertEqual(result.code, "float_rejected")

    def test_unsafe_integer(self):
        result = verify_envelope_json('{"amount":9007199254740992}')
        self.assertEqual(result.code, "integer_out_of_safe_range")

    def test_non_ascii_property_key(self):
        env = copy.deepcopy(self.signed["signed_service_request"]["envelope"])
        env["café"] = 1
        result = verify_envelope(env)
        self.assertEqual(result.code, "invalid_property_name")

    def test_lone_surrogate(self):
        result = verify_envelope_json('{"note":"\\ud800"}')
        self.assertEqual(result.code, "lone_surrogate")

    def test_null_required_field(self):
        env = _mutated_env(
            self.signed["signed_service_request"]["envelope"],
            transaction_id=None,
        )
        result = verify_envelope(env)
        self.assertEqual(result.code, "null_required_field")

    def test_wrong_field_type(self):
        env = _mutated_env(
            self.signed["signed_service_request"]["envelope"],
            nonce=123,
        )
        result = verify_envelope(env)
        self.assertEqual(result.code, "invalid_field_type")

    def test_invalid_time_order(self):
        env = _mutated_env(
            self.signed["signed_service_request"]["envelope"],
            created_at=1700004600,
            expires_at=1700001000,
        )
        # Digests will mismatch after time mutation; structural time check runs first.
        result = verify_envelope(env)
        self.assertEqual(result.code, "invalid_time_order")

    def test_identity_binding_mismatch(self):
        env = _mutated_env(
            self.signed["signed_service_request"]["envelope"],
            sender_key_id="ed25519:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        )
        result = verify_envelope(env)
        self.assertEqual(result.code, "identity_binding_mismatch")

    def test_reserved_identity(self):
        env = _mutated_env(
            self.signed["signed_service_request"]["envelope"],
            sender_identity="COINBASE",
        )
        result = verify_envelope(env)
        self.assertEqual(result.code, "reserved_identity")

    def test_unknown_message_type(self):
        env = _mutated_env(
            self.signed["signed_service_request"]["envelope"],
            message_type="not_a_type",
        )
        result = verify_envelope(env)
        self.assertEqual(result.code, "unknown_message_type")

    def test_top_level_not_object(self):
        result = verify_envelope_json("[1,2,3]")
        self.assertEqual(result.code, "top_level_not_object")

    def test_malformed_l28_transaction_id(self):
        result = verify_settlement_citation(
            {
                "l28_tx_id": "not-hex",
                "l28_transaction_material": self.signed_doc["l28_settlement_fixture"][
                    "transaction_material"
                ],
            }
        )
        self.assertEqual(result.code, "malformed_l28_transaction_id")

    def test_altered_settlement_material_citation(self):
        material = dict(self.signed_doc["l28_settlement_fixture"]["transaction_material"])
        material["amount"] = 29
        result = verify_settlement_citation(
            {
                "l28_tx_id": self.signed_doc["l28_settlement_fixture"]["expected_l28_tx_id"],
                "l28_transaction_material": material,
            }
        )
        self.assertEqual(result.code, "altered_settlement_material")

    def test_stable_codes_bounded(self):
        required = {
            "ok",
            "settlement_citation_valid",
            "invalid_json",
            "duplicate_key",
            "top_level_not_object",
            "missing_field",
            "unknown_message_type",
            "unknown_suite",
            "unsigned_envelope",
            "null_required_field",
            "invalid_field_type",
            "invalid_time_order",
            "float_rejected",
            "invalid_property_name",
            "integer_out_of_safe_range",
            "lone_surrogate",
            "padded_base64url",
            "malformed_base64url",
            "malformed_public_key_length",
            "malformed_signature_length",
            "mismatched_payload_hash",
            "mismatched_message_id",
            "identity_binding_mismatch",
            "reserved_identity",
            "verification_backend_unavailable",
            "bad_signature",
            "malformed_l28_transaction_id",
            "altered_settlement_material",
        }
        self.assertTrue(required.issubset(STABLE_CODES))

    def test_ast_no_private_key_apis(self):
        paths = (VERIFIER_PATH, *TEST_PATHS)
        for path in paths:
            with self.subTest(path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            if alias.name in FORBIDDEN_IMPORT_NAMES:
                                self.fail(f"{path.name} imports forbidden {alias.name}")
                    if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTR_NAMES:
                        self.fail(f"{path.name} references forbidden attribute {node.attr}")
                    if isinstance(node, ast.Call):
                        func = node.func
                        if isinstance(func, ast.Attribute) and func.attr == "generate":
                            self.fail(f"{path.name} calls forbidden generate()")
                        if isinstance(func, ast.Attribute) and func.attr == "sign":
                            self.fail(f"{path.name} calls forbidden sign()")
                        if isinstance(func, ast.Name) and func.id == "generate":
                            self.fail(f"{path.name} calls forbidden generate()")

        runtime = VERIFIER_PATH.read_text(encoding="utf-8")
        self.assertIn("Ed25519PublicKey", runtime)
        # Forbid private-key import forms without false-positiving on security prose.
        self.assertNotRegex(runtime, r"import\s+.*Ed25519PrivateKey")
        self.assertNotRegex(runtime, r"from_private_bytes\s*\(")
        for path in TEST_PATHS:
            src = path.read_text(encoding="utf-8")
            self.assertNotRegex(src, r"import\s+.*Ed25519PrivateKey")
            self.assertNotRegex(src, r"Ed25519PrivateKey\s*\(")

    def test_vector_keys_no_private_material(self):
        keys: Set[str] = set()
        _collect_keys(self.unsigned_doc, keys)
        _collect_keys(self.signed_doc, keys)
        offenders = sorted(k for k in keys if k.lower() in FORBIDDEN_VECTOR_KEYS)
        self.assertEqual(offenders, [])
        # Explicit metadata flags
        self.assertFalse(self.signed_doc["private_material_committed"])
        self.assertFalse(self.unsigned_doc["contains_private_material"])

    def test_no_repo_data_side_effects(self):
        data_dir = ROOT / "data"
        self.assertFalse(data_dir.exists() and any(data_dir.rglob("shard_*.jsonl")))


if __name__ == "__main__":
    unittest.main()
