# SPDX-License-Identifier: Apache-2.0
"""Foundation 70 — pure signed-receipt expiration classification tests."""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import re
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import tx_validation
from coin import uaii_signed_receipt as receipt
from coin.uaii_reference_core import INTERFACE_PROFILE, process_uaii_request
from coin.uaii_signed_receipt import (
    MAX_UNIX_SECONDS,
    RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS,
    F64ReceiptSchemaError,
    classify_signed_receipt_expiration,
    classify_signed_receipt_replay_and_expiration,
    expiration_status_for_verified_facts,
    public_key_id_for_raw,
    required_signer_identity,
    sign_unsigned_receipt_facts,
    validate_verification_time,
    verify_signed_receipt_facts,
)


def _hex64(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _unsigned(public_key_hex: str, public_key_id: str, **overrides: Any) -> dict[str, Any]:
    obj: dict[str, Any] = {
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
    obj.update(overrides)
    from coin.uaii_signed_receipt import UNSIGNED_FACTS_FIELDS

    return {k: obj[k] for k in UNSIGNED_FACTS_FIELDS}


def _signed(**overrides: Any) -> dict[str, Any]:
    private_key = Ed25519PrivateKey.generate()
    raw = private_key.public_key().public_bytes_raw()
    unsigned = _unsigned(raw.hex(), public_key_id_for_raw(raw), **overrides)
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


def _uaii_verify(
    signed: dict[str, Any],
    *,
    accepted: list[str] | None = None,
    verification_time: int,
    nonce: str,
) -> dict[str, Any]:
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
            "accepted_receipt_ids": [] if accepted is None else accepted,
            "verification_time": verification_time,
        },
    }
    raw = json.dumps(env, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return process_uaii_request(raw, _context())


class TestFoundation70Expiration(unittest.TestCase):
    def test_valid_before_expiration(self) -> None:
        signed = _signed()
        out = classify_signed_receipt_expiration(signed, signed["expires_at"] - 1)
        self.assertEqual(out["expiration_status"], "valid")

    def test_expired_after_skew_window(self) -> None:
        signed = _signed()
        t = signed["expires_at"] + RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS + 1
        out = classify_signed_receipt_expiration(signed, t)
        self.assertEqual(out["expiration_status"], "expired")

    def test_equality_at_expires_at_is_valid(self) -> None:
        signed = _signed()
        out = classify_signed_receipt_expiration(signed, signed["expires_at"])
        self.assertEqual(out["expiration_status"], "valid")

    def test_equality_at_skew_boundary_is_valid(self) -> None:
        signed = _signed()
        t = signed["expires_at"] + RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS
        self.assertEqual(
            expiration_status_for_verified_facts(signed, t),
            "valid",
        )

    def test_verification_time_mandatory_no_clock_fallback(self) -> None:
        signed = _signed()
        with self.assertRaises(TypeError):
            classify_signed_receipt_expiration(signed)  # type: ignore[call-arg]
        src = Path(receipt.__file__).read_text(encoding="utf-8")
        for needle in (
            "datetime.now",
            "datetime.utcnow",
            "time.time",
            "date.today",
            "time.monotonic",
        ):
            self.assertNotIn(needle, src)
        self.assertFalse(receipt.system_clock_read)
        self.assertFalse(receipt.implicit_time_used)

    def test_time_input_failures(self) -> None:
        signed = _signed()
        cases = [
            None,
            True,
            False,
            1.5,
            "1700000000",
            -1,
            MAX_UNIX_SECONDS + 1,
        ]
        for bad in cases:
            with self.subTest(bad=bad):
                with self.assertRaises(F64ReceiptSchemaError) as ctx:
                    validate_verification_time(bad)
                self.assertEqual(ctx.exception.code, "schema_invalid")
                with self.assertRaises(F64ReceiptSchemaError):
                    classify_signed_receipt_expiration(signed, bad)

    def test_integrity_failures_precede_expiration(self) -> None:
        signed = _signed()
        t = signed["expires_at"]
        bad = dict(signed)
        bad["signed_payload_digest"] = "0" * 64
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            classify_signed_receipt_expiration(bad, t)
        self.assertEqual(ctx.exception.code, "digest_mismatch")

        bad2 = dict(signed)
        bad2["expires_at"] = signed["expires_at"] + 10
        with self.assertRaises(F64ReceiptSchemaError):
            classify_signed_receipt_expiration(bad2, t)

        bad3 = dict(signed)
        bad3["signature"] = "ab" * 64
        with self.assertRaises(F64ReceiptSchemaError) as ctx3:
            classify_signed_receipt_expiration(bad3, t)
        self.assertEqual(ctx3.exception.code, "signature_invalid")

    def test_reuses_foundation67_verify(self) -> None:
        signed = _signed()
        with mock.patch(
            "coin.uaii_signed_receipt.verify_signed_receipt_facts",
            wraps=verify_signed_receipt_facts,
        ) as wrapped:
            classify_signed_receipt_expiration(signed, signed["created_at"])
            wrapped.assert_called_once()

    def test_replay_unchanged_and_precedence_order(self) -> None:
        signed = _signed()
        # Replay classification still works; crypto failures still precede both
        out = classify_signed_receipt_replay_and_expiration(
            signed,
            [signed["receipt_id"]],
            signed["created_at"],
        )
        self.assertEqual(out["replay_status"], "replayed")
        self.assertEqual(out["expiration_status"], "valid")

        # Documented order in combined helper source
        src = inspect.getsource(classify_signed_receipt_replay_and_expiration)
        verify_pos = src.index("verify_signed_receipt_facts")
        replay_pos = src.index("replay_status")
        exp_pos = src.index("expiration_status_for_verified_facts")
        self.assertLess(verify_pos, replay_pos)
        self.assertLess(replay_pos, exp_pos)

        bad = dict(signed)
        bad["receipt_id"] = "1" * 64
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            classify_signed_receipt_replay_and_expiration(bad, [], signed["created_at"])
        self.assertEqual(ctx.exception.code, "receipt_id_invalid")

    def test_inputs_not_mutated(self) -> None:
        signed = _signed()
        snapshot = copy.deepcopy(signed)
        classify_signed_receipt_expiration(signed, signed["created_at"])
        self.assertEqual(signed, snapshot)

    def test_independent_of_call_order(self) -> None:
        signed = _signed()
        a = classify_signed_receipt_expiration(signed, signed["expires_at"] + 301)
        b = classify_signed_receipt_expiration(signed, signed["expires_at"])
        c = classify_signed_receipt_expiration(signed, signed["expires_at"] + 301)
        self.assertEqual(a["expiration_status"], "expired")
        self.assertEqual(b["expiration_status"], "valid")
        self.assertEqual(c["expiration_status"], "expired")

    def test_uaii_path(self) -> None:
        signed = _signed()
        valid = _uaii_verify(signed, verification_time=signed["created_at"], nonce="v1")
        self.assertTrue(valid["ok"])
        self.assertEqual(valid["result"]["expiration_status"], "valid")
        self.assertEqual(valid["result"]["replay_status"], "fresh")
        expired = _uaii_verify(
            signed,
            verification_time=signed["expires_at"] + RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS + 1,
            nonce="e1",
        )
        self.assertTrue(expired["ok"])
        self.assertEqual(expired["result"]["expiration_status"], "expired")
        replayed = _uaii_verify(
            signed,
            accepted=[signed["receipt_id"]],
            verification_time=signed["created_at"],
            nonce="r1",
        )
        self.assertEqual(replayed["result"]["replay_status"], "replayed")
        self.assertEqual(replayed["result"]["expiration_status"], "valid")

    def test_no_side_effects_or_forbidden_time_apis(self) -> None:
        signed = _signed()
        with mock.patch("coin.tx_validation.validate_transaction") as vt, mock.patch(
            "coin.m2m_verifier.canonicalize", create=True
        ) as canon:
            classify_signed_receipt_expiration(signed, signed["created_at"])
            _uaii_verify(signed, verification_time=signed["created_at"], nonce="sx")
            vt.assert_not_called()
            canon.assert_not_called()
        self.assertFalse(receipt.persistent_expiration_state_created)
        self.assertFalse(receipt.system_clock_read)
        self.assertFalse(receipt.implicit_time_used)
        self.assertFalse(receipt.replay_state_mutated)
        self.assertEqual(tx_validation.L28_MAX_SUPPLY, 28_000_000)
        # Module must not reference prohibited clock helpers
        src = Path(receipt.__file__).read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\bdatetime\.(now|utcnow)\b", src))
        self.assertIsNone(re.search(r"\btime\.time\b", src))
        self.assertIsNone(re.search(r"\bdate\.today\b", src))


if __name__ == "__main__":
    unittest.main()
