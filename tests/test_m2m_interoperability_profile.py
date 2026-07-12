# SPDX-License-Identifier: Apache-2.0
"""
Offline tests for L28 M2M Interoperability Profile v0.1.

Canonicalization and digest helpers are provided by coin.m2m_verifier
(Foundation 5). This module remains test-only for unsigned Foundation 4
vectors and MUST NOT generate keys or sign messages.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

from coin.m2m_verifier import (
    DOMAIN_SIGNATURE,
    M2MVerifyError as M2MCanonicalError,
    canonical_bytes,
    canonicalize,
    decode_public_key as validate_public_key_transport,
    encode_b64url_unpadded as b64url_unpadded,
    message_id_for,
    parse_m2m_json,
    payload_hash_for,
    signature_preimage_for,
    unsigned_envelope,
)
from coin.tx_validation import compute_tx_id

ROOT = Path(__file__).resolve().parents[1]
VECTOR_PATH = ROOT / "docs" / "m2m" / "test_vectors_v0.1.json"


def build_signed_ready_envelope(base: Dict[str, Any]) -> Dict[str, Any]:
    """Attach recomputed payload_hash and message_id; leave unsigned."""
    env = dict(base)
    if "payload" not in env:
        raise M2MCanonicalError("missing_field")
    env["payload_hash"] = payload_hash_for(env["payload"])
    env.pop("message_id", None)
    env.pop("signature", None)
    env["message_id"] = message_id_for(env)
    return env


def vector_record_from_envelope(vector_id: str, envelope: Dict[str, Any], *, notes: str) -> Dict[str, Any]:
    env = build_signed_ready_envelope(envelope)
    payload_bytes = canonical_bytes(env["payload"])
    unsigned_bytes = canonical_bytes(unsigned_envelope(env))
    preimage = signature_preimage_for(env)
    return {
        "vector_id": vector_id,
        "status": "unsigned_not_operational",
        "notes": notes,
        "envelope": env,
        "canonical_payload_hex": payload_bytes.hex(),
        "expected_payload_hash": env["payload_hash"],
        "canonical_unsigned_envelope_hex": unsigned_bytes.hex(),
        "expected_message_id": env["message_id"],
        "signature_preimage_hex": preimage.hex(),
        "signature_suite": "ed25519",
        "operationally_valid": False,
    }


def _demo_pubkey(seed_byte: int) -> str:
    """Deterministic fake 32-byte public key material for vectors (NOT a real key)."""
    raw = bytes([(seed_byte + i) % 256 for i in range(32)])
    return b64url_unpadded(raw)


def generate_vectors() -> Dict[str, Any]:
    pk_a = _demo_pubkey(1)
    pk_b = _demo_pubkey(2)
    kid_a = f"ed25519:{pk_a}"

    l28_tx = {
        "sender": "l28_test_account_alice",
        "receiver": "l28_test_account_bob",
        "amount": 28,
        "timestamp": 1700000000,
        "type": "transfer",
        "network": "TEST",
    }
    l28_tx_id = compute_tx_id(l28_tx)

    valid: List[Dict[str, Any]] = []

    valid.append(
        vector_record_from_envelope(
            "valid_minimal_service_request",
            {
                "protocol": "L28-M2M",
                "protocol_version": "0.1",
                "message_type": "service_request",
                "transaction_id": "m2m_tx_minimal_001",
                "sender_public_key": pk_a,
                "sender_identity": "l28_test_account_alice",
                "recipient_public_key": pk_b,
                "recipient_identity": "l28_test_account_bob",
                "created_at": 1700000000,
                "expires_at": 1700003600,
                "nonce": "nonce_minimal_001",
                "previous_message_id": None,
                "payload": {
                    "service_id": "echo",
                    "service_params": {},
                    "max_amount": 28,
                    "currency": "L28",
                },
            },
            notes="Minimal service_request unsigned digest vector. Fixture timestamps only.",
        )
    )

    valid.append(
        vector_record_from_envelope(
            "valid_unicode_nested_service_request",
            {
                "protocol": "L28-M2M",
                "protocol_version": "0.1",
                "message_type": "service_request",
                "transaction_id": "m2m_tx_unicode_002",
                "sender_public_key": pk_a,
                "sender_identity": "l28_test_account_alice",
                "recipient_public_key": pk_b,
                "recipient_identity": "l28_test_account_bob",
                "created_at": 1700000001,
                "expires_at": 1700007200,
                "nonce": "nonce_unicode_002",
                "previous_message_id": None,
                "payload": {
                    "service_id": "translate",
                    "service_params": {
                        "text": "café — 你好 / path",
                        "nested": {"note": "quote\"and\\slash/ok", "level": 2},
                    },
                    "max_amount": 7,
                    "currency": "L28",
                    "metadata": {"label": "δοκιμή"},
                },
            },
            notes="Unicode strings and nested objects; solidus unescaped.",
        )
    )

    prev_id = valid[0]["expected_message_id"]
    valid.append(
        vector_record_from_envelope(
            "valid_chained_service_quote",
            {
                "protocol": "L28-M2M",
                "protocol_version": "0.1",
                "message_type": "service_quote",
                "transaction_id": "m2m_tx_minimal_001",
                "sender_public_key": pk_b,
                "sender_identity": "l28_test_account_bob",
                "recipient_public_key": pk_a,
                "recipient_identity": "l28_test_account_alice",
                "created_at": 1700000010,
                "expires_at": 1700003610,
                "nonce": "nonce_quote_003",
                "previous_message_id": prev_id,
                "payload": {
                    "request_message_id": prev_id,
                    "service_id": "echo",
                    "amount": 5,
                    "currency": "L28",
                    "quote_expires_at": 1700003000,
                    "service_terms_hash": payload_hash_for({"term": "fixed"}),
                    "service_terms": {"term": "fixed"},
                    "rejectable": True,
                },
            },
            notes="Chained service_quote referencing previous message_id.",
        )
    )

    valid.append(
        vector_record_from_envelope(
            "valid_settlement_reference_l28_txid",
            {
                "protocol": "L28-M2M",
                "protocol_version": "0.1",
                "message_type": "settlement_reference",
                "transaction_id": "m2m_tx_settle_004",
                "sender_public_key": pk_a,
                "sender_identity": "l28_test_account_alice",
                "recipient_public_key": pk_b,
                "recipient_identity": "l28_test_account_bob",
                "created_at": 1700000020,
                "expires_at": 1700003620,
                "nonce": "nonce_settle_004",
                "previous_message_id": None,
                "payload": {
                    "authorization_message_id": "auth_fixture_not_live",
                    "l28_tx_id": l28_tx_id,
                    "l28_sender": "l28_test_account_alice",
                    "l28_receiver": "l28_test_account_bob",
                    "amount": 28,
                    "l28_timestamp": 1700000000,
                    "verification_status": "unverified_fixture",
                    "l28_transaction_material": l28_tx,
                },
            },
            notes=(
                "Settlement citation fixture. l28_tx_id MUST equal compute_tx_id(material). "
                "Does NOT claim accepted/live settlement."
            ),
        )
    )

    invalid: List[Dict[str, Any]] = [
        {
            "vector_id": "invalid_float_amount",
            "status": "invalid",
            "expected_failure": "float_rejected",
            "envelope": {
                "protocol": "L28-M2M",
                "protocol_version": "0.1",
                "message_type": "service_request",
                "transaction_id": "bad_float",
                "sender_public_key": pk_a,
                "recipient_public_key": pk_b,
                "created_at": 1700000000,
                "expires_at": 1700003600,
                "nonce": "n",
                "previous_message_id": None,
                "payload": {
                    "service_id": "echo",
                    "service_params": {},
                    "max_amount": 1.5,
                    "currency": "L28",
                },
            },
        },
        {
            "vector_id": "invalid_bool_amount",
            "status": "invalid",
            "expected_failure": "bool_as_amount",
            "envelope": {
                "protocol": "L28-M2M",
                "protocol_version": "0.1",
                "message_type": "service_request",
                "transaction_id": "bad_bool",
                "sender_public_key": pk_a,
                "recipient_public_key": pk_b,
                "created_at": 1700000000,
                "expires_at": 1700003600,
                "nonce": "n",
                "previous_message_id": None,
                "payload": {
                    "service_id": "echo",
                    "service_params": {},
                    "max_amount": True,
                    "currency": "L28",
                },
            },
        },
        {
            "vector_id": "invalid_numeric_string_amount",
            "status": "invalid",
            "expected_failure": "numeric_string_amount",
            "envelope": {
                "protocol": "L28-M2M",
                "protocol_version": "0.1",
                "message_type": "service_request",
                "transaction_id": "bad_str_amt",
                "sender_public_key": pk_a,
                "recipient_public_key": pk_b,
                "created_at": 1700000000,
                "expires_at": 1700003600,
                "nonce": "n",
                "previous_message_id": None,
                "payload": {
                    "service_id": "echo",
                    "service_params": {},
                    "max_amount": "28",
                    "currency": "L28",
                },
            },
        },
        {
            "vector_id": "invalid_duplicate_json_key",
            "status": "invalid",
            "expected_failure": "duplicate_object_key",
            "raw_json": '{"protocol":"L28-M2M","protocol":"DUP"}',
        },
        {
            "vector_id": "invalid_non_ascii_property_name",
            "status": "invalid",
            "expected_failure": "invalid_property_name",
            "envelope": {"café": 1},
        },
        {
            "vector_id": "invalid_property_name_grammar",
            "status": "invalid",
            "expected_failure": "invalid_property_name",
            "envelope": {"BadName": 1},
        },
        {
            "vector_id": "invalid_integer_outside_safe_range",
            "status": "invalid",
            "expected_failure": "integer_out_of_safe_range",
            "envelope": {"amount": 9007199254740992},
        },
        {
            "vector_id": "invalid_lone_surrogate",
            "status": "invalid",
            "expected_failure": "lone_surrogate",
            "raw_json": '{"note":"\\ud800"}',
        },
        {
            "vector_id": "invalid_mismatched_payload_hash",
            "status": "invalid",
            "expected_failure": "mismatched_payload_hash",
            "envelope": {
                **{k: v for k, v in valid[0]["envelope"].items() if k != "signature"},
                "payload_hash": "0" * 64,
            },
        },
        {
            "vector_id": "invalid_mismatched_message_id",
            "status": "invalid",
            "expected_failure": "mismatched_message_id",
            "envelope": {
                **{k: v for k, v in valid[0]["envelope"].items() if k != "signature"},
                "message_id": "1" * 64,
            },
        },
        {
            "vector_id": "invalid_padded_base64url_key",
            "status": "invalid",
            "expected_failure": "padded_base64url",
            "public_key": pk_a + "=",
        },
        {
            "vector_id": "invalid_malformed_public_key_length",
            "status": "invalid",
            "expected_failure": "malformed_public_key_length",
            "public_key": b64url_unpadded(b"\x00" * 16),
        },
        {
            "vector_id": "invalid_unknown_signature_suite",
            "status": "invalid",
            "expected_failure": "unknown_signature_suite",
            "signature_suite": "rsa-pss",
        },
        {
            "vector_id": "invalid_missing_required_field",
            "status": "invalid",
            "expected_failure": "missing_required_field",
            "envelope": {
                "protocol": "L28-M2M",
                "protocol_version": "0.1",
                "message_type": "service_request",
                "sender_public_key": pk_a,
                "recipient_public_key": pk_b,
                "created_at": 1700000000,
                "expires_at": 1700003600,
                "nonce": "n",
                "previous_message_id": None,
                "payload": {
                    "service_id": "echo",
                    "service_params": {},
                    "max_amount": 1,
                    "currency": "L28",
                },
            },
        },
        {
            "vector_id": "invalid_null_required_field",
            "status": "invalid",
            "expected_failure": "null_required_field",
            "envelope": {
                "protocol": "L28-M2M",
                "protocol_version": "0.1",
                "message_type": "service_request",
                "transaction_id": None,
                "sender_public_key": pk_a,
                "recipient_public_key": pk_b,
                "created_at": 1700000000,
                "expires_at": 1700003600,
                "nonce": "n",
                "previous_message_id": None,
                "payload": {
                    "service_id": "echo",
                    "service_params": {},
                    "max_amount": 1,
                    "currency": "L28",
                },
            },
        },
        {
            "vector_id": "invalid_malformed_l28_tx_id",
            "status": "invalid",
            "expected_failure": "malformed_l28_tx_id",
            "payload": {
                "l28_tx_id": "not-a-sha256-hex",
                "l28_transaction_material": l28_tx,
            },
        },
        {
            "vector_id": "invalid_altered_settlement_material",
            "status": "invalid",
            "expected_failure": "altered_settlement_material",
            "payload": {
                "l28_tx_id": l28_tx_id,
                "l28_transaction_material": {**l28_tx, "amount": 29},
            },
        },
    ]

    return {
        "profile": "L28 M2M Interoperability Profile v0.1",
        "status": "offline_non_operational",
        "subordinate_to": "L28 Protocol v1.0.0",
        "domains": {
            "payload": "L28-M2M-V0.1-PAYLOAD\\x00",
            "message": "L28-M2M-V0.1-MESSAGE\\x00",
            "signature": "L28-M2M-V0.1-SIGNATURE\\x00",
        },
        "signature_suite_selected": "ed25519",
        "signature_implemented": False,
        "contains_private_material": False,
        "claims_live_settlement": False,
        "machine_key_id_example": kid_a,
        "l28_settlement_fixture": {
            "transaction_material": l28_tx,
            "expected_l28_tx_id": l28_tx_id,
            "accepted": False,
            "live": False,
        },
        "valid_unsigned_vectors": valid,
        "invalid_vectors": invalid,
    }


def _assert_no_secrets(obj: Any) -> None:
    forbidden = {
        "private_key",
        "seed",
        "seed_phrase",
        "mnemonic",
        "secret",
        "wallet_credential",
    }
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in forbidden:
                raise AssertionError(f"forbidden secret field: {k}")
            _assert_no_secrets(v)
    elif isinstance(obj, list):
        for v in obj:
            _assert_no_secrets(v)


def _amount_invalid_reason(amount: Any) -> Optional[str]:
    if isinstance(amount, float):
        return "float_rejected"
    if isinstance(amount, bool):
        return "bool_as_amount"
    if isinstance(amount, str):
        return "numeric_string_amount"
    if amount is None:
        return "null_required_field"
    if type(amount) is int:
        try:
            from coin.m2m_verifier import SAFE_INT_MAX, SAFE_INT_MIN

            if amount < SAFE_INT_MIN or amount > SAFE_INT_MAX:
                return "integer_out_of_safe_range"
        except Exception:
            return "integer_out_of_safe_range"
        return None
    return "invalid_amount_type"


class TestM2MInteroperabilityProfile(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doc = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))

    def test_vector_file_metadata(self):
        self.assertEqual(self.doc["profile"], "L28 M2M Interoperability Profile v0.1")
        self.assertFalse(self.doc["signature_implemented"])
        self.assertFalse(self.doc["contains_private_material"])
        self.assertFalse(self.doc["claims_live_settlement"])
        self.assertEqual(self.doc["signature_suite_selected"], "ed25519")
        _assert_no_secrets(self.doc)

    def test_valid_unsigned_vectors_recompute(self):
        for vec in self.doc["valid_unsigned_vectors"]:
            with self.subTest(vec["vector_id"]):
                env = vec["envelope"]
                self.assertEqual(vec["status"], "unsigned_not_operational")
                self.assertFalse(vec["operationally_valid"])
                self.assertNotIn("private_key", env)
                self.assertNotIn("seed", env)

                payload = env["payload"]
                payload_bytes = canonical_bytes(payload)
                self.assertEqual(payload_bytes.hex(), vec["canonical_payload_hex"])
                ph = payload_hash_for(payload)
                self.assertEqual(ph, vec["expected_payload_hash"])
                self.assertEqual(ph, env["payload_hash"])

                unsigned_bytes = canonical_bytes(unsigned_envelope(env))
                self.assertEqual(unsigned_bytes.hex(), vec["canonical_unsigned_envelope_hex"])
                mid = message_id_for(env)
                self.assertEqual(mid, vec["expected_message_id"])
                self.assertEqual(mid, env["message_id"])

                preimage = signature_preimage_for(env)
                self.assertEqual(preimage.hex(), vec["signature_preimage_hex"])
                self.assertTrue(preimage.startswith(DOMAIN_SIGNATURE))

    def test_settlement_l28_txid_stable(self):
        fixture = self.doc["l28_settlement_fixture"]
        material = fixture["transaction_material"]
        expected = fixture["expected_l28_tx_id"]
        self.assertEqual(compute_tx_id(material), expected)
        self.assertFalse(fixture["accepted"])
        self.assertFalse(fixture["live"])

        settle = next(
            v for v in self.doc["valid_unsigned_vectors"] if v["vector_id"] == "valid_settlement_reference_l28_txid"
        )
        payload = settle["envelope"]["payload"]
        self.assertEqual(payload["l28_tx_id"], expected)
        self.assertEqual(compute_tx_id(payload["l28_transaction_material"]), expected)
        self.assertEqual(payload["verification_status"], "unverified_fixture")

    def test_invalid_vectors(self):
        for vec in self.doc["invalid_vectors"]:
            with self.subTest(vec["vector_id"]):
                reason = vec["expected_failure"]
                if "raw_json" in vec:
                    with self.assertRaises(M2MCanonicalError) as ctx:
                        parse_m2m_json(vec["raw_json"])
                    if reason == "duplicate_object_key":
                        # Foundation 4 vector name; runtime stable code is duplicate_key.
                        self.assertEqual(ctx.exception.code, "duplicate_key")
                    if reason == "lone_surrogate":
                        self.assertEqual(ctx.exception.code, "lone_surrogate")
                    continue

                if "public_key" in vec:
                    with self.assertRaises(M2MCanonicalError) as ctx:
                        validate_public_key_transport(vec["public_key"])
                    self.assertEqual(ctx.exception.code, reason)
                    continue

                if reason == "unknown_signature_suite":
                    self.assertNotEqual(vec["signature_suite"], "ed25519")
                    continue

                if reason == "malformed_l28_tx_id":
                    txid = vec["payload"]["l28_tx_id"]
                    self.assertFalse(re.fullmatch(r"[0-9a-f]{64}", txid or ""))
                    continue

                if reason == "altered_settlement_material":
                    material = vec["payload"]["l28_transaction_material"]
                    cited = vec["payload"]["l28_tx_id"]
                    self.assertNotEqual(compute_tx_id(material), cited)
                    continue

                env = vec["envelope"]
                if reason == "missing_required_field":
                    self.assertNotIn("transaction_id", env)
                    continue
                if reason == "null_required_field":
                    self.assertIsNone(env.get("transaction_id"))
                    continue
                if reason == "mismatched_payload_hash":
                    self.assertNotEqual(payload_hash_for(env["payload"]), env["payload_hash"])
                    continue
                if reason == "mismatched_message_id":
                    tmp = dict(env)
                    self.assertNotEqual(message_id_for(tmp), env["message_id"])
                    continue
                if reason in {
                    "float_rejected",
                    "bool_as_amount",
                    "numeric_string_amount",
                    "integer_out_of_safe_range",
                }:
                    if "payload" in env and "max_amount" in env["payload"]:
                        self.assertEqual(_amount_invalid_reason(env["payload"]["max_amount"]), reason)
                    elif "amount" in env:
                        with self.assertRaises(M2MCanonicalError):
                            canonicalize(env)
                    continue
                if reason == "invalid_property_name":
                    with self.assertRaises(M2MCanonicalError) as ctx:
                        canonicalize(env)
                    self.assertEqual(ctx.exception.code, "invalid_property_name")
                    continue
                self.fail(f"unhandled invalid vector {vec['vector_id']}")

    def test_no_runtime_data_created(self):
        data_dir = ROOT / "data"
        self.assertFalse(data_dir.exists() and any(data_dir.rglob("shard_*.jsonl")))


if __name__ == "__main__":
    unittest.main()
