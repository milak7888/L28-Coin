# SPDX-License-Identifier: Apache-2.0
"""Foundation 68 — UAII verify_signed_receipt operation tests."""

from __future__ import annotations

import hashlib
import json
import unittest
from typing import Any
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import tx_validation
from coin.uaii_reference_core import (
    CAPABILITIES,
    INTERFACE_PROFILE,
    OPERATIONS,
    adapters_activated,
    execution_authorized,
    ledger_mutated,
    persistent_keys_created,
    private_material_exposed,
    process_uaii_request,
    runtime_activated,
    settlement_authorized,
    signing_authorized,
    spend_authorized,
)
from coin.uaii_signed_receipt import (
    public_key_id_for_raw,
    required_signer_identity,
    sign_unsigned_receipt_facts,
)


def _hex64(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _context(*, t_eval: int = 1_700_000_000) -> dict[str, Any]:
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

        def get_balance(self, address: str) -> int:
            return 1000 if address == "alice" else 0

    class _Protocol:
        def current_balance_lookup(self, address: str, _currency: str) -> int:
            return 1000 if address == "alice" else 0

        def seen_tx_lookup(self, _tx_id: str) -> bool:
            return False

    return {
        "t_eval": t_eval,
        "ledger_state": _Ledger(),
        "replay_state": _Replay(),
        "protocol_validate": _Protocol(),
    }


def _envelope(operation: str, params: dict[str, Any], *, nonce: str = "n1") -> dict[str, Any]:
    return {
        "interface_profile": INTERFACE_PROFILE,
        "operation": operation,
        "request_id": _hex64(operation + nonce),
        "created_at": 1_699_999_000,
        "expires_at": 1_700_000_100,
        "nonce": nonce,
        "execution_authorized": False,
        "params": params,
    }


def _call(env: dict[str, Any], ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = json.dumps(env, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return process_uaii_request(raw, ctx if ctx is not None else _context())


def _valid_unsigned(public_key_hex: str, public_key_id: str) -> dict[str, Any]:
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


def _disposable_signed_receipt() -> dict[str, Any]:
    private_key = Ed25519PrivateKey.generate()
    raw = private_key.public_key().public_bytes_raw()
    unsigned = _valid_unsigned(raw.hex(), public_key_id_for_raw(raw))
    return sign_unsigned_receipt_facts(
        unsigned,
        sign_signable_bytes=private_key.sign,
        expected_signer_identity=required_signer_identity(unsigned),
    )


def _verify_params(
    signed: dict[str, Any],
    accepted: list[str] | None = None,
    verification_time: int | None = None,
) -> dict[str, Any]:
    # Default evaluation time is before expires_at (fixtures use expires_at=1700000600).
    t = 1_700_000_000 if verification_time is None else verification_time
    return {
        "signed_receipt": signed,
        "accepted_receipt_ids": [] if accepted is None else accepted,
        "verification_time": t,
        "governance_approval_evidence": {},
    }


class TestFoundation68VerifySignedReceipt(unittest.TestCase):
    def test_registered_and_discoverable(self) -> None:
        self.assertIn("verify_signed_receipt", OPERATIONS)
        self.assertIn(
            ("uaii.verify_signed_receipt", "verify_signed_receipt", "supported"),
            CAPABILITIES,
        )
        r = _call(_envelope("discover_capabilities", {"include_adapter_declarations": False}, nonce="disc"))
        self.assertTrue(r["ok"])
        self.assertIn("verify_signed_receipt", r["result"]["operations"])
        ids = [c["capability_id"] for c in r["result"]["capabilities"]]
        self.assertIn("uaii.verify_signed_receipt", ids)

    def test_valid_receipt_verifies_through_uaii(self) -> None:
        signed = _disposable_signed_receipt()
        r = _call(_envelope("verify_signed_receipt", _verify_params(signed), nonce="ok1"))
        self.assertTrue(r["ok"])
        self.assertEqual(r["code"], "signed_receipt_verified")
        self.assertEqual(r["operation"], "verify_signed_receipt")
        self.assertEqual(r["detail"], "")
        result = r["result"]
        self.assertEqual(result["verification_status"], "verified")
        self.assertEqual(result["replay_status"], "fresh")
        self.assertEqual(result["expiration_status"], "valid")
        self.assertEqual(result["acceptance_decision"], "accepted")
        self.assertEqual(result["rejection_reason"], "")
        self.assertEqual(result["receipt_id"], signed["receipt_id"])
        self.assertEqual(result["signed_payload_digest"], signed["signed_payload_digest"])
        proposal = result["acceptance_transition_proposal"]
        self.assertEqual(proposal["proposal_status"], "applicable")
        self.assertEqual(proposal["transition_kind"], "add_accepted_receipt_id")
        self.assertEqual(proposal["receipt_id"], signed["receipt_id"])
        self.assertIs(proposal["transition_applied"], False)
        self.assertIs(result["transition_applied"], False)
        self.assertIs(result["transition_proposed_only"], True)
        self.assertIs(result["accepted_receipt_ids_mutated"], False)
        boundary = result["acceptance_transition_application_boundary"]
        self.assertEqual(boundary["application_boundary_status"], "eligible")
        self.assertEqual(boundary["application_boundary_reason"], "")
        self.assertEqual(boundary["receipt_id"], signed["receipt_id"])
        self.assertEqual(boundary["transition_kind"], "add_accepted_receipt_id")
        self.assertIs(boundary["application_authorized"], False)
        self.assertIs(boundary["application_executed"], False)
        self.assertIs(result["application_authorized"], False)
        self.assertIs(result["application_executed"], False)
        self.assertIs(result["boundary_evaluated_only"], True)
        evaluation = result["governance_approval_evaluation"]
        self.assertEqual(evaluation["governance_approval_evaluation_status"], "not_supplied")
        self.assertEqual(evaluation["governance_approval_evaluation_reason"], "approval_not_supplied")
        self.assertIs(evaluation["approval_granted"], False)
        self.assertIs(result["approval_granted"], False)
        self.assertIs(result["caller_supplied_approval_evaluated_only"], True)
        self.assertEqual(
            tuple(result.keys()),
            (
                "verification_status",
                "replay_status",
                "expiration_status",
                "acceptance_decision",
                "rejection_reason",
                "acceptance_transition_proposal",
                "acceptance_transition_application_boundary",
                "governance_approval_evaluation",
                "receipt_profile",
                "receipt_id",
                "signed_payload_digest",
                "signer_algorithm_profile",
                "signer_public_key_id",
                "signer_public_key",
                "settlement_status",
                "payer_public_identity",
                "provider_public_identity",
                "asset_id",
                "amount",
                "purpose",
                "correlation_id",
                "request_id",
                "quote_id",
                "expires_at",
                "verification_time",
                "signing_authorized",
                "spend_authorized",
                "settlement_authorized",
                "ledger_mutated",
                "execution_authorized",
                "transition_applied",
                "transition_proposed_only",
                "accepted_receipt_ids_mutated",
                "application_authorized",
                "application_executed",
                "state_mutated",
                "persistent_state_created",
                "boundary_evaluated_only",
                "approval_granted",
                "approval_issued",
                "authorization_granted",
                "caller_supplied_approval_evaluated_only",
            ),
        )
        for flag in (
            "signing_authorized",
            "spend_authorized",
            "settlement_authorized",
            "ledger_mutated",
            "execution_authorized",
        ):
            self.assertIs(result[flag], False)

    def test_deterministic_repeat(self) -> None:
        signed = _disposable_signed_receipt()
        a = _call(_envelope("verify_signed_receipt", _verify_params(signed), nonce="d1"))
        b = _call(_envelope("verify_signed_receipt", _verify_params(signed), nonce="d2"))
        self.assertEqual(a["result"], b["result"])
        self.assertEqual(a["code"], b["code"])

    def test_tamper_paths_fail_closed(self) -> None:
        signed = _disposable_signed_receipt()
        cases = [
            ("amount", 99, {"digest_mismatch", "signature_invalid", "receipt_id_invalid"}),
            ("receipt_nonce", "mutated", {"digest_mismatch", "signature_invalid", "receipt_id_invalid"}),
            ("signed_payload_digest", "0" * 64, {"digest_mismatch"}),
            ("receipt_id", "1" * 64, {"receipt_id_invalid"}),
            ("payer_public_identity", "mutated-payer", {"digest_mismatch", "signature_invalid", "receipt_id_invalid"}),
            ("signature", "ab" * 64, {"signature_invalid"}),
        ]
        for field, value, codes in cases:
            with self.subTest(field=field):
                bad = dict(signed)
                bad[field] = value
                r = _call(
                    _envelope("verify_signed_receipt", _verify_params(bad), nonce=f"t-{field}"),
                )
                self.assertFalse(r["ok"])
                self.assertIn(r["code"], codes)
                self.assertEqual(r["result"], {})

    def test_public_key_swap_fails(self) -> None:
        signed = _disposable_signed_receipt()
        other = Ed25519PrivateKey.generate()
        raw = other.public_key().public_bytes_raw()
        bad = dict(signed)
        bad["signer_public_key"] = raw.hex()
        bad["signer_public_key_id"] = public_key_id_for_raw(raw)
        r = _call(_envelope("verify_signed_receipt", _verify_params(bad), nonce="pk"))
        self.assertFalse(r["ok"])
        self.assertEqual(r["code"], "digest_mismatch")

    def test_malformed_signature_and_unsupported_algorithm(self) -> None:
        signed = _disposable_signed_receipt()
        bad_sig = dict(signed)
        bad_sig["signature"] = "g" * 128
        r1 = _call(_envelope("verify_signed_receipt", _verify_params(bad_sig), nonce="ms"))
        self.assertFalse(r1["ok"])
        self.assertEqual(r1["code"], "schema_invalid")

        bad_alg = dict(signed)
        bad_alg["signer_algorithm_profile"] = "ed25519-prehash/v0.1"
        r2 = _call(_envelope("verify_signed_receipt", _verify_params(bad_alg), nonce="alg"))
        self.assertFalse(r2["ok"])
        self.assertEqual(r2["code"], "algorithm_unsupported")

    def test_request_schema_failures(self) -> None:
        signed = _disposable_signed_receipt()
        r_missing = _call(_envelope("verify_signed_receipt", {}, nonce="miss"))
        self.assertEqual(r_missing["code"], "schema_invalid")

        r_extra = _call(
            _envelope(
                "verify_signed_receipt",
                {**_verify_params(signed), "extra_field": 1},
                nonce="extra",
            )
        )
        self.assertEqual(r_extra["code"], "schema_invalid")

        r_type = _call(
            _envelope(
                "verify_signed_receipt",
                {
                    "signed_receipt": "not-an-object",
                    "accepted_receipt_ids": [],
                    "verification_time": 1_700_000_000,
                    "governance_approval_evidence": {},
                },
                nonce="type",
            )
        )
        self.assertEqual(r_type["code"], "schema_invalid")

        bad_null = dict(signed)
        bad_null["prior_receipt_id"] = ""
        r_null = _call(
            _envelope("verify_signed_receipt", _verify_params(bad_null), nonce="null")
        )
        self.assertFalse(r_null["ok"])
        self.assertEqual(r_null["code"], "schema_invalid")

        r_missing_ids = _call(
            _envelope("verify_signed_receipt", {"signed_receipt": signed}, nonce="no-ids")
        )
        self.assertEqual(r_missing_ids["code"], "schema_invalid")

        r_missing_time = _call(
            _envelope(
                "verify_signed_receipt",
                {"signed_receipt": signed, "accepted_receipt_ids": []},
                nonce="no-time",
            )
        )
        self.assertEqual(r_missing_time["code"], "schema_invalid")

    def test_delegates_to_foundation67(self) -> None:
        signed = _disposable_signed_receipt()
        with mock.patch(
            "coin.uaii_signed_receipt.verify_signed_receipt_facts",
            wraps=__import__(
                "coin.uaii_signed_receipt", fromlist=["verify_signed_receipt_facts"]
            ).verify_signed_receipt_facts,
        ) as wrapped:
            r = _call(_envelope("verify_signed_receipt", _verify_params(signed), nonce="del"))
            self.assertTrue(r["ok"])
            wrapped.assert_called_once()

    def test_get_payment_receipt_unchanged(self) -> None:
        params = {
            "quote_id": _hex64("q"),
            "payment_request_id": _hex64("pr"),
            "payer_identity": "alice",
            "payee_identity": "bob",
            "amount": 10,
            "currency": "L28",
            "service_id": "svc",
            "service_result_hash": _hex64("sr"),
            "l28_tx_id": _hex64("tx"),
            "l28_sender": "alice",
            "l28_receiver": "bob",
            "l28_amount": 10,
            "l28_timestamp": 1_700_000_000,
            "verification_status": "verified",
            "completed_at": 1_700_000_001,
            "receipt_nonce": "rn1",
        }
        r = _call(_envelope("get_payment_receipt", params, nonce="gpr"))
        self.assertTrue(r["ok"])
        self.assertEqual(r["code"], "payment_receipt_ok")
        self.assertEqual(r["result"]["receipt"]["receipt_profile"], "l28-uaii-payment-receipt/v0.1")

    def test_unknown_operation_unchanged(self) -> None:
        r = _call(_envelope("not_a_real_operation", {}, nonce="unk"))
        self.assertFalse(r["ok"])
        self.assertEqual(r["code"], "operation_unsupported")

    def test_no_forbidden_side_effects(self) -> None:
        signed = _disposable_signed_receipt()
        with mock.patch("coin.tx_validation.validate_transaction") as vt, mock.patch(
            "coin.m2m_verifier.canonicalize", create=True
        ) as canon:
            r = _call(_envelope("verify_signed_receipt", _verify_params(signed), nonce="side"))
            self.assertTrue(r["ok"])
            vt.assert_not_called()
            canon.assert_not_called()
        self.assertFalse(signing_authorized)
        self.assertFalse(persistent_keys_created)
        self.assertFalse(private_material_exposed)
        self.assertFalse(spend_authorized)
        self.assertFalse(settlement_authorized)
        self.assertFalse(ledger_mutated)
        self.assertFalse(adapters_activated)
        self.assertFalse(runtime_activated)
        self.assertFalse(execution_authorized)
        self.assertEqual(tx_validation.L28_MAX_SUPPLY, 28_000_000)
        self.assertEqual(tx_validation.L28_HISTORICAL_MINED, 2_824_584)


if __name__ == "__main__":
    unittest.main()
