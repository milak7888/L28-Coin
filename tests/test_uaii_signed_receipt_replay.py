# SPDX-License-Identifier: Apache-2.0
"""Foundation 69 — pure signed-receipt replay classification tests."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from typing import Any
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import tx_validation
from coin import uaii_signed_receipt as receipt
from coin.uaii_reference_core import INTERFACE_PROFILE, process_uaii_request
from coin.uaii_signed_receipt import (
    MAX_ACCEPTED_RECEIPT_IDS,
    F64ReceiptSchemaError,
    classify_signed_receipt_replay,
    public_key_id_for_raw,
    required_signer_identity,
    sign_unsigned_receipt_facts,
    validate_accepted_receipt_ids,
)


def _hex64(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _unsigned(public_key_hex: str, public_key_id: str) -> dict[str, Any]:
    return {
        "receipt_profile": "l28-uaii-signed-receipt/v0.1",
        "prior_receipt_id": None,
        "correlation_id": _hex64("corr"),
        "request_id": _hex64("req"),
        "quote_id": _hex64("quote"),
        "service_result_id": _hex64("svc"),
        "payer_public_identity": "payer-alice",
        "provider_public_identity": "provider-bob",
        "asset_id": "L28",
        "amount": 42,
        "purpose": "signed_receipt",
        "created_at": 1_700_000_000,
        "expires_at": 1_700_000_600,
        "receipt_nonce": "nonce-abc",
        "transaction_id": "",
        "settlement_status": "authorization_signed",
        "signer_algorithm_profile": "ed25519-pure/v0.1",
        "signer_public_key_id": public_key_id,
        "signer_public_key": public_key_hex,
        "signing_authorized": False,
        "spend_authorized": False,
        "settlement_authorized": False,
        "ledger_mutated": False,
        "execution_authorized": False,
    }


def _signed() -> dict[str, Any]:
    private_key = Ed25519PrivateKey.generate()
    raw = private_key.public_key().public_bytes_raw()
    unsigned = _unsigned(raw.hex(), public_key_id_for_raw(raw))
    return sign_unsigned_receipt_facts(
        unsigned,
        sign_signable_bytes=private_key.sign,
        expected_signer_identity=required_signer_identity(unsigned),
    )


def _context() -> dict[str, Any]:
    class _Replay:
        def lookup(self, _key: str) -> str:
            return "absent"

    class _Ledger:
        def read_binding(self) -> dict[str, Any]:
            return {
                "canonical_height": 100878,
                "issued_supply": 2824584,
                "canonical_issuance_ready": True,
                "accepted_tx_count": 0,
            }

        def get_balance(self, _address: str) -> int:
            return 0

    class _Protocol:
        def current_balance_lookup(self, _address: str, _currency: str) -> int:
            return 0

        def seen_tx_lookup(self, _tx_id: str) -> bool:
            return False

    return {
        "t_eval": 1_700_000_000,
        "ledger_state": _Ledger(),
        "replay_state": _Replay(),
        "protocol_validate": _Protocol(),
    }


def _uaii_verify(signed: dict[str, Any], accepted: list[str], *, nonce: str) -> dict[str, Any]:
    env = {
        "interface_profile": INTERFACE_PROFILE,
        "operation": "verify_signed_receipt",
        "request_id": _hex64("verify" + nonce),
        "created_at": 1_699_999_000,
        "expires_at": 1_700_000_100,
        "nonce": nonce,
        "execution_authorized": False,
        "params": {
            "signed_receipt": signed,
            "accepted_receipt_ids": accepted,
            "verification_time": 1_700_000_000,
        },
    }
    raw = json.dumps(env, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return process_uaii_request(raw, _context())


class TestFoundation69ReplayClassification(unittest.TestCase):
    def test_fresh_unseen_receipt(self) -> None:
        signed = _signed()
        out = classify_signed_receipt_replay(signed, [])
        self.assertEqual(out["verification_status"], "verified")
        self.assertEqual(out["replay_status"], "fresh")
        self.assertEqual(out["receipt_id"], signed["receipt_id"])

    def test_replayed_when_receipt_id_in_context(self) -> None:
        signed = _signed()
        out = classify_signed_receipt_replay(signed, [signed["receipt_id"]])
        self.assertEqual(out["replay_status"], "replayed")
        self.assertEqual(out["receipt_id"], signed["receipt_id"])

    def test_compares_receipt_id_not_signature_or_object_identity(self) -> None:
        signed = _signed()
        # Same receipt_id string in a new list object; different signature text must not matter
        other_sig_text = "ab" * 64
        self.assertNotEqual(other_sig_text, signed["signature"])
        accepted = [str(signed["receipt_id"])]
        out = classify_signed_receipt_replay(dict(signed), accepted)
        self.assertEqual(out["replay_status"], "replayed")
        # Unrelated id → fresh
        out2 = classify_signed_receipt_replay(signed, [_hex64("other-accepted")])
        self.assertEqual(out2["replay_status"], "fresh")

    def test_integrity_failures_precede_replay_classification(self) -> None:
        signed = _signed()
        accepted = [signed["receipt_id"]]
        bad = dict(signed)
        bad["signed_payload_digest"] = "0" * 64
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            classify_signed_receipt_replay(bad, accepted)
        self.assertEqual(ctx.exception.code, "digest_mismatch")

        bad2 = dict(signed)
        bad2["receipt_id"] = "1" * 64
        with self.assertRaises(F64ReceiptSchemaError) as ctx2:
            classify_signed_receipt_replay(bad2, accepted)
        self.assertEqual(ctx2.exception.code, "receipt_id_invalid")

        bad3 = dict(signed)
        bad3["payer_public_identity"] = "mutated"
        with self.assertRaises(F64ReceiptSchemaError):
            classify_signed_receipt_replay(bad3, accepted)

        bad4 = dict(signed)
        bad4["signature"] = "ab" * 64
        with self.assertRaises(F64ReceiptSchemaError) as ctx4:
            classify_signed_receipt_replay(bad4, accepted)
        self.assertEqual(ctx4.exception.code, "signature_invalid")

        other = Ed25519PrivateKey.generate()
        raw = other.public_key().public_bytes_raw()
        bad5 = dict(signed)
        bad5["signer_public_key"] = raw.hex()
        bad5["signer_public_key_id"] = public_key_id_for_raw(raw)
        with self.assertRaises(F64ReceiptSchemaError) as ctx5:
            classify_signed_receipt_replay(bad5, accepted)
        self.assertEqual(ctx5.exception.code, "digest_mismatch")

    def test_malformed_replay_context(self) -> None:
        signed = _signed()
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            validate_accepted_receipt_ids("not-a-list")
        self.assertEqual(ctx.exception.code, "schema_invalid")
        with self.assertRaises(F64ReceiptSchemaError):
            classify_signed_receipt_replay(signed, {"id": signed["receipt_id"]})
        with self.assertRaises(F64ReceiptSchemaError):
            classify_signed_receipt_replay(signed, [None])
        with self.assertRaises(F64ReceiptSchemaError):
            classify_signed_receipt_replay(signed, [123])
        with self.assertRaises(F64ReceiptSchemaError):
            classify_signed_receipt_replay(signed, ["not-hex"])
        with self.assertRaises(F64ReceiptSchemaError) as dup:
            classify_signed_receipt_replay(signed, [signed["receipt_id"], signed["receipt_id"]])
        self.assertEqual(dup.exception.code, "schema_invalid")
        with self.assertRaises(F64ReceiptSchemaError) as big:
            classify_signed_receipt_replay(
                signed,
                [_hex64(f"x{i}") for i in range(MAX_ACCEPTED_RECEIPT_IDS + 1)],
            )
        self.assertEqual(big.exception.code, "input_too_large")

    def test_context_not_mutated(self) -> None:
        signed = _signed()
        accepted = [_hex64("a"), _hex64("b")]
        snapshot = copy.deepcopy(accepted)
        classify_signed_receipt_replay(signed, accepted)
        self.assertEqual(accepted, snapshot)

    def test_stateless_across_calls(self) -> None:
        a = _signed()
        b = _signed()
        self.assertEqual(classify_signed_receipt_replay(a, [])["replay_status"], "fresh")
        self.assertEqual(
            classify_signed_receipt_replay(a, [a["receipt_id"]])["replay_status"],
            "replayed",
        )
        # Prior call must not affect a later empty-context classification
        self.assertEqual(classify_signed_receipt_replay(a, [])["replay_status"], "fresh")
        self.assertEqual(classify_signed_receipt_replay(b, [a["receipt_id"]])["replay_status"], "fresh")

    def test_order_independence_of_classification(self) -> None:
        signed = _signed()
        first = classify_signed_receipt_replay(signed, [signed["receipt_id"]])
        second = classify_signed_receipt_replay(signed, [signed["receipt_id"]])
        self.assertEqual(first, second)

    def test_uaii_path_fresh_and_replayed(self) -> None:
        signed = _signed()
        fresh = _uaii_verify(signed, [], nonce="f1")
        self.assertTrue(fresh["ok"])
        self.assertEqual(fresh["result"]["replay_status"], "fresh")
        replayed = _uaii_verify(signed, [signed["receipt_id"]], nonce="r1")
        self.assertTrue(replayed["ok"])
        self.assertEqual(replayed["result"]["replay_status"], "replayed")
        self.assertEqual(replayed["code"], "signed_receipt_verified")

    def test_reuses_verify_not_duplicate_crypto(self) -> None:
        signed = _signed()
        with mock.patch(
            "coin.uaii_signed_receipt.verify_signed_receipt_facts",
            wraps=receipt.verify_signed_receipt_facts,
        ) as wrapped:
            classify_signed_receipt_replay(signed, [])
            wrapped.assert_called_once()

    def test_no_side_effects_or_persistence_flags(self) -> None:
        signed = _signed()
        with mock.patch("coin.tx_validation.validate_transaction") as vt, mock.patch(
            "coin.m2m_verifier.canonicalize", create=True
        ) as canon:
            classify_signed_receipt_replay(signed, [])
            _uaii_verify(signed, [], nonce="sx")
            vt.assert_not_called()
            canon.assert_not_called()
        self.assertFalse(receipt.persistent_replay_storage_created)
        self.assertFalse(receipt.replay_state_mutated)
        self.assertFalse(receipt.signing_authorized)
        self.assertFalse(receipt.persistent_keys_created)
        self.assertFalse(receipt.private_material_exposed)
        self.assertFalse(receipt.spend_authorized)
        self.assertFalse(receipt.settlement_authorized)
        self.assertFalse(receipt.ledger_mutated)
        self.assertFalse(receipt.runtime_activated)
        self.assertEqual(tx_validation.L28_MAX_SUPPLY, 28_000_000)
        self.assertEqual(tx_validation.L28_HISTORICAL_MINED, 2_824_584)


if __name__ == "__main__":
    unittest.main()
