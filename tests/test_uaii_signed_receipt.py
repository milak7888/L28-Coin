# SPDX-License-Identifier: Apache-2.0
"""Focused Foundation 66 F64 signed-receipt data-contract conformance tests."""

from __future__ import annotations

import base64
import hashlib
import importlib
import inspect
import unittest
from typing import Any
from unittest import mock

from coin import tx_validation
from coin.uaii_json import canon_uaii
from coin import uaii_signed_receipt as f66
from coin.uaii_signed_receipt import (
    APPROVAL_DECISION_FIELDS,
    REPLAY_MATERIAL_FIELDS,
    SIGNED_FACTS_FIELDS,
    UNSIGNED_FACTS_FIELDS,
    F64ReceiptSchemaError,
    approved_canonical_payload,
    build_signable_bytes,
    build_signed_facts_empty_id,
    compute_receipt_id,
    compute_replay_key,
    compute_signed_payload_digest,
    unsigned_facts_from_signed,
    validate_approval_decision,
    validate_replay_key_material,
    validate_signed_facts,
    validate_unsigned_facts,
)


def _hex64(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _ed25519_key_pair_material(seed: str) -> tuple[str, str]:
    raw = hashlib.sha256(seed.encode()).digest()
    public_key = raw.hex()
    key_id = "ed25519:" + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return public_key, key_id


def _valid_unsigned(**overrides: Any) -> dict[str, Any]:
    public_key, key_id = _ed25519_key_pair_material("payer-key")
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
        "signer_public_key_id": key_id,
        "signer_public_key": public_key,
        "signing_authorized": False,
        "spend_authorized": False,
        "settlement_authorized": False,
        "ledger_mutated": False,
        "execution_authorized": False,
    }
    obj.update(overrides)
    # Rebuild with exact field order after overrides
    return {k: obj[k] for k in UNSIGNED_FACTS_FIELDS}


def _valid_cumulative(*, policy_id: str = "policy-1", amount: int = 42) -> dict[str, Any]:
    return {
        "policy_id": policy_id,
        "subject_identity": "payer-alice",
        "asset_id": "L28",
        "window_start": 1_700_000_000,
        "window_end": 1_700_086_400,
        "prior_authorized_amount": 0,
        "proposed_amount": amount,
        "cumulative_maximum": 1000,
        "evaluation_timestamp": 1_700_000_010,
        "evaluation_result": "pass",
    }


def _valid_approval(**overrides: Any) -> dict[str, Any]:
    digest = compute_signed_payload_digest(_valid_unsigned())
    obj: dict[str, Any] = {
        "approval_profile": "l28-f64-approval-decision/v0.1",
        "approval_id": _hex64("approval"),
        "request_id": _hex64("req"),
        "correlation_id": _hex64("corr"),
        "quote_id": _hex64("quote"),
        "payer_identity": "payer-alice",
        "provider_identity": "provider-bob",
        "asset_id": "L28",
        "amount": 42,
        "purpose": "signed_receipt",
        "nonce": "approval-nonce-1",
        "expires_at": 1_700_000_600,
        "signable_digest": digest,
        "signer_key_handle": "local-handle-1",
        "policy_id": "policy-1",
        "per_transaction_limit": 100,
        "cumulative_limit_evaluation": _valid_cumulative(),
        "decision": "approved",
        "decided_at": 1_700_000_050,
        "approver_identity": "operator-1",
        "approval_signature_reference": None,
    }
    obj.update(overrides)
    if "cumulative_limit_evaluation" not in overrides and "amount" in overrides:
        obj["cumulative_limit_evaluation"] = _valid_cumulative(amount=int(obj["amount"]))
    if "signable_digest" not in overrides and "amount" in overrides:
        # keep digest from default unsigned unless caller overrides
        pass
    return {k: obj[k] for k in APPROVAL_DECISION_FIELDS}


def _valid_replay(**overrides: Any) -> dict[str, Any]:
    digest = compute_signed_payload_digest(_valid_unsigned())
    obj: dict[str, Any] = {
        "replay_profile": "l28-f64-signing-replay/v0.1",
        "signer_key_handle": "local-handle-1",
        "signature_purpose": "signed_receipt",
        "payer_identity": "payer-alice",
        "provider_identity": "provider-bob",
        "asset_id": "L28",
        "amount": 42,
        "request_id": _hex64("req"),
        "quote_id": _hex64("quote"),
        "correlation_id": _hex64("corr"),
        "nonce": "replay-nonce-1",
        "expires_at": 1_700_000_600,
        "signed_payload_digest": digest,
    }
    obj.update(overrides)
    return {k: obj[k] for k in REPLAY_MATERIAL_FIELDS}


def _valid_signed(**overrides: Any) -> dict[str, Any]:
    unsigned = _valid_unsigned()
    digest = compute_signed_payload_digest(unsigned)
    # Deterministic placeholder signature bytes (not a real PureEd25519 signature)
    signature = hashlib.sha512(b"placeholder-signature-material").hexdigest()
    empty = build_signed_facts_empty_id(
        unsigned_facts=unsigned,
        signed_payload_digest=digest,
        signature=signature,
    )
    receipt_id = compute_receipt_id(empty)
    obj = dict(empty)
    obj["receipt_id"] = receipt_id
    obj.update(overrides)
    return {k: obj[k] for k in SIGNED_FACTS_FIELDS}


class TestFoundation66SchemaCounts(unittest.TestCase):
    def test_field_counts(self) -> None:
        self.assertEqual(len(UNSIGNED_FACTS_FIELDS), 24)
        self.assertEqual(len(SIGNED_FACTS_FIELDS), 27)
        self.assertEqual(len(APPROVAL_DECISION_FIELDS), 21)
        self.assertEqual(len(REPLAY_MATERIAL_FIELDS), 13)


class TestValidSchemas(unittest.TestCase):
    def test_valid_unsigned(self) -> None:
        out = validate_unsigned_facts(_valid_unsigned())
        self.assertEqual(tuple(out.keys()), UNSIGNED_FACTS_FIELDS)
        self.assertIsNone(out["prior_receipt_id"])

    def test_valid_signed(self) -> None:
        out = validate_signed_facts(_valid_signed())
        self.assertEqual(tuple(out.keys()), SIGNED_FACTS_FIELDS)
        self.assertEqual(len(out["receipt_id"]), 64)

    def test_valid_approval(self) -> None:
        out = validate_approval_decision(_valid_approval())
        self.assertEqual(tuple(out.keys()), APPROVAL_DECISION_FIELDS)
        self.assertIsNone(out["approval_signature_reference"])

    def test_valid_replay(self) -> None:
        out = validate_replay_key_material(_valid_replay())
        self.assertEqual(tuple(out.keys()), REPLAY_MATERIAL_FIELDS)


class TestMissingAndUnexpectedFields(unittest.TestCase):
    def _assert_missing(self, fields: tuple[str, ...], builder, validator) -> None:
        base = builder()
        for missing in fields:
            bad = {k: v for k, v in base.items() if k != missing}
            with self.subTest(missing=missing):
                with self.assertRaises(F64ReceiptSchemaError) as ctx:
                    validator(bad)
                self.assertEqual(ctx.exception.code, "schema_invalid")

    def _assert_unexpected(self, builder, validator) -> None:
        bad = builder()
        bad["extra_field"] = "nope"
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            validator(bad)
        self.assertEqual(ctx.exception.code, "schema_invalid")

    def test_unsigned_missing_each(self) -> None:
        self._assert_missing(UNSIGNED_FACTS_FIELDS, _valid_unsigned, validate_unsigned_facts)

    def test_signed_missing_each(self) -> None:
        self._assert_missing(SIGNED_FACTS_FIELDS, _valid_signed, validate_signed_facts)

    def test_approval_missing_each(self) -> None:
        self._assert_missing(APPROVAL_DECISION_FIELDS, _valid_approval, validate_approval_decision)

    def test_replay_missing_each(self) -> None:
        self._assert_missing(REPLAY_MATERIAL_FIELDS, _valid_replay, validate_replay_key_material)

    def test_unexpected_fields(self) -> None:
        self._assert_unexpected(_valid_unsigned, validate_unsigned_facts)
        self._assert_unexpected(_valid_signed, validate_signed_facts)
        self._assert_unexpected(_valid_approval, validate_approval_decision)
        self._assert_unexpected(_valid_replay, validate_replay_key_material)


class TestTypesAndNulls(unittest.TestCase):
    def test_amount_wrong_type(self) -> None:
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            validate_unsigned_facts(_valid_unsigned(amount="42"))
        self.assertEqual(ctx.exception.code, "amount_invalid")

    def test_amount_bool_rejected(self) -> None:
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            validate_unsigned_facts(_valid_unsigned(amount=True))
        self.assertEqual(ctx.exception.code, "amount_invalid")

    def test_prior_receipt_id_empty_string_forbidden(self) -> None:
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            validate_unsigned_facts(_valid_unsigned(prior_receipt_id=""))
        self.assertEqual(ctx.exception.code, "schema_invalid")

    def test_prior_receipt_id_null_allowed(self) -> None:
        out = validate_unsigned_facts(_valid_unsigned(prior_receipt_id=None))
        self.assertIsNone(out["prior_receipt_id"])

    def test_approval_signature_reference_must_be_null(self) -> None:
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            validate_approval_decision(_valid_approval(approval_signature_reference=""))
        self.assertEqual(ctx.exception.code, "schema_invalid")

    def test_flags_must_be_false(self) -> None:
        with self.assertRaises(F64ReceiptSchemaError):
            validate_unsigned_facts(_valid_unsigned(signing_authorized=True))

    def test_nonce_nul_rejected(self) -> None:
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            validate_unsigned_facts(_valid_unsigned(receipt_nonce="bad\0nonce"))
        self.assertEqual(ctx.exception.code, "nonce_invalid")


class TestOrderingAndCanonicalBytes(unittest.TestCase):
    def test_reordered_fields_rejected(self) -> None:
        keys = list(UNSIGNED_FACTS_FIELDS)
        keys[0], keys[1] = keys[1], keys[0]
        base = _valid_unsigned()
        reordered = {k: base[k] for k in keys}
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            validate_unsigned_facts(reordered)
        self.assertEqual(ctx.exception.code, "schema_invalid")

    def test_identical_input_identical_canonical_bytes(self) -> None:
        a = _valid_unsigned()
        b = _valid_unsigned()
        self.assertEqual(approved_canonical_payload(a), approved_canonical_payload(b))
        self.assertEqual(compute_signed_payload_digest(a), compute_signed_payload_digest(b))
        signable_a = build_signable_bytes(a)
        signable_b = build_signable_bytes(b)
        self.assertEqual(signable_a, signable_b)
        self.assertTrue(signable_a.startswith(b"L28-UAII-SIGN-V0.1-RECEIPT\x00"))

    def test_altered_payload_changes_digest(self) -> None:
        a = _valid_unsigned()
        b = _valid_unsigned(amount=43)
        self.assertNotEqual(
            compute_signed_payload_digest(a),
            compute_signed_payload_digest(b),
        )

    def test_digest_excludes_digest_signature_receipt_id(self) -> None:
        unsigned = _valid_unsigned()
        digest = compute_signed_payload_digest(unsigned)
        signed = _valid_signed()
        extracted = unsigned_facts_from_signed(signed)
        self.assertEqual(tuple(extracted.keys()), UNSIGNED_FACTS_FIELDS)
        self.assertNotIn("receipt_id", extracted)
        self.assertNotIn("signed_payload_digest", extracted)
        self.assertNotIn("signature", extracted)
        self.assertEqual(compute_signed_payload_digest(extracted), digest)
        # Canonical unsigned bytes must not contain those field names
        payload = approved_canonical_payload(unsigned).decode("utf-8")
        self.assertNotIn('"receipt_id"', payload)
        self.assertNotIn('"signed_payload_digest"', payload)
        self.assertNotIn('"signature"', payload)

    def test_receipt_id_non_circular(self) -> None:
        unsigned = _valid_unsigned()
        digest = compute_signed_payload_digest(unsigned)
        signature = hashlib.sha512(b"placeholder-signature-material").hexdigest()
        empty = build_signed_facts_empty_id(
            unsigned_facts=unsigned,
            signed_payload_digest=digest,
            signature=signature,
        )
        rid = compute_receipt_id(empty)
        self.assertEqual(empty["receipt_id"], "")
        self.assertNotEqual(rid, "")
        # Changing signature changes receipt_id; digest construction stays independent
        empty2 = build_signed_facts_empty_id(
            unsigned_facts=unsigned,
            signed_payload_digest=digest,
            signature=hashlib.sha512(b"other-placeholder").hexdigest(),
        )
        self.assertNotEqual(compute_receipt_id(empty2), rid)

    def test_canon_uaii_not_m2m(self) -> None:
        self.assertIn("canon_uaii", f66.__dict__)
        self.assertNotIn("m2m_verifier", f66.__dict__)
        self.assertIsNone(getattr(f66, "canonicalize", None))
        self.assertFalse(any(name.startswith("coin.m2m") for name in f66.__dict__))
        with mock.patch("coin.uaii_signed_receipt.canon_uaii", wraps=canon_uaii) as wrapped:
            approved_canonical_payload(_valid_unsigned())
            wrapped.assert_called()
        # AST/import surface: no m2m_verifier import statement
        import ast
        from pathlib import Path

        tree = ast.parse(Path(f66.__file__).read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        self.assertTrue(any(m.endswith("uaii_json") or m == "uaii_json" for m in imported))
        self.assertFalse(any("m2m_verifier" in m for m in imported))


class TestSideEffectBoundaries(unittest.TestCase):
    def test_module_flags_false(self) -> None:
        self.assertFalse(f66.execution_authorized)
        self.assertFalse(f66.signing_authorized)
        self.assertFalse(f66.spend_authorized)
        self.assertFalse(f66.settlement_authorized)
        self.assertFalse(f66.ledger_mutated)
        self.assertFalse(f66.private_material_exposed)
        self.assertFalse(f66.persistent_keys_created)
        self.assertFalse(f66.runtime_activated)

    def test_no_uaii_processor_or_validator_calls(self) -> None:
        with mock.patch("coin.uaii_reference_core.process_uaii_request") as p, mock.patch(
            "coin.tx_validation.validate_transaction"
        ) as v:
            validate_unsigned_facts(_valid_unsigned())
            validate_approval_decision(_valid_approval())
            validate_replay_key_material(_valid_replay())
            signed = _valid_signed()
            validate_signed_facts(signed)
            compute_replay_key(_valid_replay())
            p.assert_not_called()
            v.assert_not_called()

    def test_no_network_or_env_or_random(self) -> None:
        src = inspect.getsource(f66)
        for needle in (
            "socket",
            "urllib",
            "requests",
            "http.client",
            "os.environ",
            "getenv",
            "secrets.",
            "PrivateKey",
            "SigningKey",
            "ReplayRegistry",
        ):
            self.assertNotIn(needle, src)

    def test_protected_economics_unchanged(self) -> None:
        self.assertEqual(tx_validation.L28_MAX_SUPPLY, 28_000_000)
        self.assertEqual(tx_validation.L28_EMISSION_CEILING, 11_130_000)
        self.assertEqual(tx_validation.L28_HISTORICAL_MINED, 2_824_584)
        self.assertEqual(tx_validation.L28_HALVING_INTERVAL, 210_000)
        self.assertEqual(tx_validation.L28_REWARD_SCHEDULE, (28, 14, 7, 3, 1))
        self.assertEqual(tx_validation.L28_HISTORICAL_LAST_ENTRY, 100_877)
        self.assertEqual(tx_validation.L28_NEXT_HEIGHT_AFTER_CHECKPOINT, 100_878)
        # Importing F66 must not mutate economics module
        importlib.reload(tx_validation)
        self.assertEqual(tx_validation.L28_MAX_SUPPLY, 28_000_000)


if __name__ == "__main__":
    unittest.main()
