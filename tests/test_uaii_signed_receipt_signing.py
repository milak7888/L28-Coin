# SPDX-License-Identifier: Apache-2.0
"""Foundation 67 isolated Ed25519 receipt signing/verification tests.

Disposable keys are generated in-process via Ed25519PrivateKey.generate() and
never written to disk, fixtures, environment variables, or assertions as private
material. Only public keys, signatures, digests, and receipt IDs are asserted.
"""

from __future__ import annotations

import ast
import hashlib
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import tx_validation
from coin import uaii_signed_receipt as receipt
from coin.uaii_json import canon_uaii
from coin.uaii_signed_receipt import (
    SIGNED_FACTS_FIELDS,
    UNSIGNED_FACTS_FIELDS,
    F64ReceiptSchemaError,
    build_signable_bytes,
    compute_signed_payload_digest,
    public_key_id_for_raw,
    required_signer_identity,
    sign_unsigned_receipt_facts,
    validate_unsigned_facts,
    verify_signed_receipt_facts,
)


def _hex64(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _disposable_signer() -> tuple[Ed25519PrivateKey, str, str]:
    """Fresh in-memory key only; private material never leaves this process."""
    private_key = Ed25519PrivateKey.generate()
    raw = private_key.public_key().public_bytes_raw()
    return private_key, raw.hex(), public_key_id_for_raw(raw)


def _valid_unsigned_for(
    *,
    public_key_hex: str,
    public_key_id: str,
    settlement_status: str = "authorization_signed",
    **overrides: Any,
) -> dict[str, Any]:
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
        "settlement_status": settlement_status,
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
    return {k: obj[k] for k in UNSIGNED_FACTS_FIELDS}


def _sign_pair(
    *,
    settlement_status: str = "authorization_signed",
    **overrides: Any,
) -> tuple[Ed25519PrivateKey, dict[str, Any], dict[str, Any]]:
    private_key, pk_hex, pk_id = _disposable_signer()
    unsigned = _valid_unsigned_for(
        public_key_hex=pk_hex,
        public_key_id=pk_id,
        settlement_status=settlement_status,
        **overrides,
    )
    identity = required_signer_identity(unsigned)
    signed = sign_unsigned_receipt_facts(
        unsigned,
        sign_signable_bytes=private_key.sign,
        expected_signer_identity=identity,
    )
    return private_key, unsigned, signed


class TestFoundation67SignVerify(unittest.TestCase):
    def test_round_trip(self) -> None:
        _pk, unsigned, signed = _sign_pair()
        out = verify_signed_receipt_facts(signed)
        self.assertEqual(tuple(out.keys()), SIGNED_FACTS_FIELDS)
        self.assertEqual(
            compute_signed_payload_digest(unsigned),
            signed["signed_payload_digest"],
        )

    def test_stable_signable_bytes(self) -> None:
        private_key, pk_hex, pk_id = _disposable_signer()
        unsigned = _valid_unsigned_for(public_key_hex=pk_hex, public_key_id=pk_id)
        a = build_signable_bytes(unsigned)
        b = build_signable_bytes(dict(unsigned))
        self.assertEqual(a, b)
        signed = sign_unsigned_receipt_facts(
            unsigned,
            sign_signable_bytes=private_key.sign,
            expected_signer_identity=required_signer_identity(unsigned),
        )
        self.assertEqual(build_signable_bytes(unsigned), a)
        verify_signed_receipt_facts(signed)

    def test_wrong_public_key_fails(self) -> None:
        private_key, unsigned, signed = _sign_pair()
        other = Ed25519PrivateKey.generate()
        # Same public facts / digest, but signature from a different key → signature_invalid
        tampered = dict(signed)
        tampered["signature"] = other.sign(build_signable_bytes(unsigned)).hex()
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            verify_signed_receipt_facts(tampered)
        self.assertEqual(ctx.exception.code, "signature_invalid")
        del private_key

    def test_declared_key_swap_fails_closed(self) -> None:
        _pk, _unsigned, signed = _sign_pair()
        other = Ed25519PrivateKey.generate()
        raw = other.public_key().public_bytes_raw()
        tampered = dict(signed)
        tampered["signer_public_key"] = raw.hex()
        tampered["signer_public_key_id"] = public_key_id_for_raw(raw)
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            verify_signed_receipt_facts(tampered)
        # Public key is part of unsigned facts → digest checked before signature
        self.assertEqual(ctx.exception.code, "digest_mismatch")

    def test_altered_approved_payload_fails(self) -> None:
        private_key, unsigned, _signed = _sign_pair()
        # Sign original, then verify against mutated unsigned reconstruction path
        signed = sign_unsigned_receipt_facts(
            unsigned,
            sign_signable_bytes=private_key.sign,
            expected_signer_identity=required_signer_identity(unsigned),
        )
        tampered = dict(signed)
        tampered["amount"] = 43
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            verify_signed_receipt_facts(tampered)
        self.assertIn(ctx.exception.code, {"digest_mismatch", "signature_invalid", "receipt_id_invalid"})

    def test_altered_signed_fact_fails(self) -> None:
        _pk, _u, signed = _sign_pair()
        tampered = dict(signed)
        tampered["receipt_nonce"] = "nonce-mutated"
        with self.assertRaises(F64ReceiptSchemaError):
            verify_signed_receipt_facts(tampered)

    def test_altered_digest_fails(self) -> None:
        _pk, _u, signed = _sign_pair()
        tampered = dict(signed)
        tampered["signed_payload_digest"] = "0" * 64
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            verify_signed_receipt_facts(tampered)
        self.assertEqual(ctx.exception.code, "digest_mismatch")

    def test_altered_receipt_id_fails(self) -> None:
        _pk, _u, signed = _sign_pair()
        tampered = dict(signed)
        tampered["receipt_id"] = "1" * 64
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            verify_signed_receipt_facts(tampered)
        self.assertEqual(ctx.exception.code, "receipt_id_invalid")

    def test_altered_signer_identity_fails(self) -> None:
        _pk, _u, signed = _sign_pair()
        tampered = dict(signed)
        tampered["payer_public_identity"] = "payer-mutated"
        with self.assertRaises(F64ReceiptSchemaError):
            verify_signed_receipt_facts(tampered)

    def test_identity_binding_enforced_on_sign(self) -> None:
        private_key, pk_hex, pk_id = _disposable_signer()
        unsigned = _valid_unsigned_for(public_key_hex=pk_hex, public_key_id=pk_id)
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            sign_unsigned_receipt_facts(
                unsigned,
                sign_signable_bytes=private_key.sign,
                expected_signer_identity="provider-bob",  # wrong for authorization_signed
            )
        self.assertEqual(ctx.exception.code, "key_binding_invalid")

    def test_service_result_binds_provider(self) -> None:
        _pk, unsigned, signed = _sign_pair(settlement_status="service_result_signed")
        self.assertEqual(required_signer_identity(unsigned), "provider-bob")
        verify_signed_receipt_facts(signed)

    def test_malformed_signature_encoding_fails(self) -> None:
        _pk, _u, signed = _sign_pair()
        tampered = dict(signed)
        tampered["signature"] = "g" * 128
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            verify_signed_receipt_facts(tampered)
        # Non-hex fails schema before cryptographic verify (F64 structure precedence)
        self.assertEqual(ctx.exception.code, "schema_invalid")
        # Uppercase hex is also non-canonical under lowercase-only grammar
        tampered2 = dict(signed)
        tampered2["signature"] = signed["signature"].upper()
        with self.assertRaises(F64ReceiptSchemaError) as ctx2:
            verify_signed_receipt_facts(tampered2)
        self.assertEqual(ctx2.exception.code, "schema_invalid")

    def test_wrong_signature_length_fails(self) -> None:
        _pk, _u, signed = _sign_pair()
        tampered = dict(signed)
        tampered["signature"] = "ab" * 32  # 64 hex chars, not 128
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            verify_signed_receipt_facts(tampered)
        self.assertEqual(ctx.exception.code, "schema_invalid")

    def test_missing_and_unexpected_fields_fail(self) -> None:
        _pk, _u, signed = _sign_pair()
        missing = {k: v for k, v in signed.items() if k != "signature"}
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            verify_signed_receipt_facts(missing)
        self.assertEqual(ctx.exception.code, "schema_invalid")
        extra = dict(signed)
        extra["extra_field"] = "x"
        with self.assertRaises(F64ReceiptSchemaError) as ctx2:
            verify_signed_receipt_facts(extra)
        self.assertEqual(ctx2.exception.code, "schema_invalid")

    def test_unsupported_algorithm_fails(self) -> None:
        private_key, pk_hex, pk_id = _disposable_signer()
        unsigned = _valid_unsigned_for(public_key_hex=pk_hex, public_key_id=pk_id)
        # Bypass validate to inject algorithm after building a signed object is hard;
        # signing path rejects when unsigned has wrong algorithm at validation time.
        bad = dict(unsigned)
        bad["signer_algorithm_profile"] = "ed25519-prehash/v0.1"
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            validate_unsigned_facts(bad)
        self.assertEqual(ctx.exception.code, "algorithm_unsupported")
        # Also verify path: start from valid signed then mutate algorithm
        _pk, _u, signed = _sign_pair()
        tampered = dict(signed)
        tampered["signer_algorithm_profile"] = "ed25519-prehash/v0.1"
        with self.assertRaises(F64ReceiptSchemaError) as ctx2:
            verify_signed_receipt_facts(tampered)
        self.assertEqual(ctx2.exception.code, "algorithm_unsupported")
        del private_key  # ensure local only

    def test_schema_null_enforcement_still_active(self) -> None:
        private_key, pk_hex, pk_id = _disposable_signer()
        with self.assertRaises(F64ReceiptSchemaError):
            sign_unsigned_receipt_facts(
                _valid_unsigned_for(
                    public_key_hex=pk_hex,
                    public_key_id=pk_id,
                    prior_receipt_id="",
                ),
                sign_signable_bytes=private_key.sign,
                expected_signer_identity="payer-alice",
            )

    def test_signable_excludes_circular_fields(self) -> None:
        _pk, unsigned, signed = _sign_pair()
        payload_text = build_signable_bytes(unsigned).decode("utf-8", errors="replace")
        self.assertNotIn('"receipt_id"', payload_text)
        self.assertNotIn('"signed_payload_digest"', payload_text)
        self.assertNotIn('"signature"', payload_text)
        self.assertTrue(build_signable_bytes(unsigned).startswith(b"L28-UAII-SIGN-V0.1-RECEIPT\x00"))
        verify_signed_receipt_facts(signed)

    def test_no_m2m_canonicalize(self) -> None:
        tree = ast.parse(Path(receipt.__file__).read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        self.assertFalse(any("m2m_verifier" in m for m in imported))
        self.assertNotIn("Ed25519PrivateKey", receipt.__dict__)
        with mock.patch("coin.uaii_signed_receipt.canon_uaii", wraps=canon_uaii) as wrapped:
            _sign_pair()
            wrapped.assert_called()

    def test_no_side_effect_authorities(self) -> None:
        with mock.patch("coin.uaii_reference_core.process_uaii_request") as p, mock.patch(
            "coin.tx_validation.validate_transaction"
        ) as v:
            _pk, _u, signed = _sign_pair()
            verify_signed_receipt_facts(signed)
            p.assert_not_called()
            v.assert_not_called()

    def test_flags_and_economics(self) -> None:
        self.assertFalse(receipt.execution_authorized)
        self.assertFalse(receipt.persistent_keys_created)
        self.assertFalse(receipt.private_material_exposed)
        self.assertFalse(receipt.spend_authorized)
        self.assertFalse(receipt.settlement_authorized)
        self.assertFalse(receipt.ledger_mutated)
        self.assertFalse(receipt.runtime_activated)
        self.assertEqual(tx_validation.L28_MAX_SUPPLY, 28_000_000)
        self.assertEqual(tx_validation.L28_EMISSION_CEILING, 11_130_000)
        self.assertEqual(tx_validation.L28_HISTORICAL_MINED, 2_824_584)

    def test_no_private_material_in_module_or_exceptions(self) -> None:
        src = Path(receipt.__file__).read_text(encoding="utf-8")
        self.assertNotIn("Ed25519PrivateKey", src)
        self.assertNotIn("from_private_bytes", src)
        pem_marker = "BEGIN" + " PRIVATE"
        self.assertNotIn(pem_marker, src)
        private_key, unsigned, signed = _sign_pair()
        # Exception messages must be code-only
        tampered = dict(signed)
        tampered["signed_payload_digest"] = "0" * 64
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            verify_signed_receipt_facts(tampered)
        self.assertEqual(str(ctx.exception), "digest_mismatch")
        # Capture stdout/stderr during a round trip — must not contain private bytes
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            verify_signed_receipt_facts(signed)
        combined = buf_out.getvalue() + buf_err.getvalue()
        # private key object has no stable printable secret we assert; ensure hex private not dumped
        self.assertNotIn("PRIVATE", combined.upper())
        # No key files created in temp cwd
        with tempfile.TemporaryDirectory() as tmp:
            before = set(Path(tmp).rglob("*"))
            sign_unsigned_receipt_facts(
                unsigned,
                sign_signable_bytes=private_key.sign,
                expected_signer_identity=required_signer_identity(unsigned),
            )
            after = set(Path(tmp).rglob("*"))
            self.assertEqual(before, after)

    def test_matching_key_only(self) -> None:
        private_key, unsigned, signed = _sign_pair()
        verify_signed_receipt_facts(signed)
        other = Ed25519PrivateKey.generate()
        # Re-sign with other key but keep original public key in facts → sign rejects
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            sign_unsigned_receipt_facts(
                unsigned,
                sign_signable_bytes=other.sign,
                expected_signer_identity=required_signer_identity(unsigned),
            )
        self.assertEqual(ctx.exception.code, "signature_invalid")
        del private_key


if __name__ == "__main__":
    unittest.main()
