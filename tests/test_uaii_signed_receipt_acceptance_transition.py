# SPDX-License-Identifier: Apache-2.0
"""Foundation 72 — pure signed-receipt acceptance transition proposal tests."""

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
from coin.uaii_reference_core import (
    CAPABILITIES,
    INTERFACE_PROFILE,
    OPERATIONS,
    process_uaii_request,
)
from coin.uaii_signed_receipt import (
    ACCEPTANCE_TRANSITION_PROPOSAL_FIELDS,
    RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS,
    F64ReceiptSchemaError,
    acceptance_transition_proposal_from_decision,
    decide_signed_receipt_acceptance,
    propose_signed_receipt_acceptance_transition,
    public_key_id_for_raw,
    required_signer_identity,
    sign_unsigned_receipt_facts,
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


def _applicable_proposal(receipt_id: str) -> dict[str, Any]:
    return {
        "proposal_status": "applicable",
        "transition_kind": "add_accepted_receipt_id",
        "receipt_id": receipt_id,
        "expected_prior_replay_status": "fresh",
        "proposed_resulting_replay_status": "replayed",
        "precondition": "receipt_id_absent_from_accepted_receipt_ids",
        "proposed_effect": "add_receipt_id_to_accepted_receipt_ids",
        "transition_applied": False,
        "transition_proposed_only": True,
    }


def _not_applicable_proposal(receipt_id: str) -> dict[str, Any]:
    return {
        "proposal_status": "not_applicable",
        "transition_kind": "",
        "receipt_id": receipt_id,
        "expected_prior_replay_status": "",
        "proposed_resulting_replay_status": "",
        "precondition": "",
        "proposed_effect": "",
        "transition_applied": False,
        "transition_proposed_only": True,
    }


class TestFoundation72AcceptanceTransitionProposal(unittest.TestCase):
    def test_accepted_produces_exact_deterministic_proposal(self) -> None:
        signed = _signed()
        out = propose_signed_receipt_acceptance_transition(
            signed, [], signed["created_at"]
        )
        expected = _applicable_proposal(signed["receipt_id"])
        self.assertEqual(out["acceptance_decision"], "accepted")
        self.assertEqual(out["acceptance_transition_proposal"], expected)
        self.assertEqual(
            tuple(out["acceptance_transition_proposal"].keys()),
            ACCEPTANCE_TRANSITION_PROPOSAL_FIELDS,
        )
        again = propose_signed_receipt_acceptance_transition(
            signed, [], signed["created_at"]
        )
        self.assertEqual(out["acceptance_transition_proposal"], again["acceptance_transition_proposal"])

    def test_proposal_references_verified_receipt_id_and_precondition_effect(self) -> None:
        signed = _signed()
        proposal = propose_signed_receipt_acceptance_transition(
            signed, [], signed["created_at"]
        )["acceptance_transition_proposal"]
        self.assertEqual(proposal["receipt_id"], signed["receipt_id"])
        self.assertEqual(
            proposal["precondition"],
            "receipt_id_absent_from_accepted_receipt_ids",
        )
        self.assertEqual(
            proposal["proposed_effect"],
            "add_receipt_id_to_accepted_receipt_ids",
        )
        self.assertEqual(proposal["expected_prior_replay_status"], "fresh")
        self.assertEqual(proposal["proposed_resulting_replay_status"], "replayed")
        self.assertNotIn("accepted_receipt_ids", proposal)
        self.assertNotIn("signature", proposal)

    def test_caller_collections_not_mutated(self) -> None:
        signed = _signed()
        # Existing F69 rule: accepted_receipt_ids MUST be a list (tuple fails closed).
        with self.assertRaises(F64ReceiptSchemaError):
            propose_signed_receipt_acceptance_transition(
                signed, tuple(), signed["created_at"]  # type: ignore[arg-type]
            )
        mutable: list[str] = []
        snap_signed = copy.deepcopy(signed)
        propose_signed_receipt_acceptance_transition(signed, mutable, signed["created_at"])
        other = [signed["receipt_id"]]
        snap_other = list(other)
        propose_signed_receipt_acceptance_transition(signed, other, signed["created_at"])
        self.assertEqual(signed, snap_signed)
        self.assertEqual(mutable, [])
        self.assertEqual(other, snap_other)
        self.assertFalse(receipt.accepted_receipt_ids_mutated)
        self.assertFalse(receipt.transition_applied)

    def test_rejected_paths_not_applicable(self) -> None:
        signed = _signed()
        t_expired = signed["expires_at"] + RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS + 1

        replayed = propose_signed_receipt_acceptance_transition(
            signed, [signed["receipt_id"]], signed["created_at"]
        )
        self.assertEqual(replayed["acceptance_decision"], "rejected")
        self.assertEqual(replayed["rejection_reason"], "replayed")
        self.assertEqual(
            replayed["acceptance_transition_proposal"],
            _not_applicable_proposal(signed["receipt_id"]),
        )
        self.assertEqual(
            replayed["acceptance_transition_proposal"]["proposed_effect"],
            "",
        )

        expired = propose_signed_receipt_acceptance_transition(signed, [], t_expired)
        self.assertEqual(expired["acceptance_decision"], "rejected")
        self.assertEqual(expired["rejection_reason"], "expired")
        self.assertEqual(
            expired["acceptance_transition_proposal"],
            _not_applicable_proposal(signed["receipt_id"]),
        )

        both = propose_signed_receipt_acceptance_transition(
            signed, [signed["receipt_id"]], t_expired
        )
        self.assertEqual(both["rejection_reason"], "replayed")
        self.assertEqual(
            both["acceptance_transition_proposal"]["proposal_status"],
            "not_applicable",
        )

    def test_crypto_failure_emits_no_proposal(self) -> None:
        signed = _signed()
        bad = dict(signed)
        bad["signature"] = "ab" * 64
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            propose_signed_receipt_acceptance_transition(bad, [], signed["created_at"])
        self.assertEqual(ctx.exception.code, "signature_invalid")

        uaii = _uaii_verify(bad, verification_time=signed["created_at"], nonce="fail")
        self.assertFalse(uaii["ok"])
        result = uaii.get("result") or {}
        self.assertNotIn("acceptance_transition_proposal", result)
        self.assertNotIn("acceptance_decision", result)

    def test_tamper_and_schema_fail_closed(self) -> None:
        signed = _signed()
        t = signed["created_at"]
        cases = [
            ("signed_payload_digest", "0" * 64, "digest_mismatch"),
            ("receipt_id", "1" * 64, "receipt_id_invalid"),
            ("signer_public_key", "00" * 32, None),
            ("signature", "cd" * 64, "signature_invalid"),
        ]
        for field, value, code in cases:
            with self.subTest(field=field):
                bad = dict(signed)
                bad[field] = value
                with self.assertRaises(F64ReceiptSchemaError) as ctx:
                    propose_signed_receipt_acceptance_transition(bad, [], t)
                if code is not None:
                    self.assertEqual(ctx.exception.code, code)

        for bad_accepted in (None, "x", [None], [True], ["zz"], [signed["receipt_id"]] * 2):
            with self.subTest(accepted=bad_accepted):
                with self.assertRaises(F64ReceiptSchemaError):
                    propose_signed_receipt_acceptance_transition(signed, bad_accepted, t)
        for bad_time in (None, True, 1.5, "1", -1):
            with self.subTest(t=bad_time):
                with self.assertRaises(F64ReceiptSchemaError):
                    propose_signed_receipt_acceptance_transition(signed, [], bad_time)

    def test_reuses_foundation71_path(self) -> None:
        signed = _signed()
        with mock.patch(
            "coin.uaii_signed_receipt.decide_signed_receipt_acceptance",
            wraps=decide_signed_receipt_acceptance,
        ) as wrapped:
            propose_signed_receipt_acceptance_transition(signed, [], signed["created_at"])
            wrapped.assert_called_once()
        src = inspect.getsource(propose_signed_receipt_acceptance_transition)
        self.assertIn("decide_signed_receipt_acceptance", src)
        self.assertIn("acceptance_transition_proposal_from_decision", src)
        self.assertNotIn("Ed25519PublicKey", src)
        self.assertNotIn("verify_signed_receipt_facts", src)

    def test_no_execution_claim_in_output(self) -> None:
        signed = _signed()
        out = propose_signed_receipt_acceptance_transition(
            signed, [], signed["created_at"]
        )
        proposal = out["acceptance_transition_proposal"]
        blob = json.dumps(proposal, separators=(",", ":"), ensure_ascii=False)
        for forbidden in (
            "executed",
            "recorded",
            "persisted",
            "settled",
            "finalized",
            "applied_true",
        ):
            self.assertNotIn(forbidden, blob)
        self.assertIs(proposal["transition_applied"], False)
        self.assertIs(proposal["transition_proposed_only"], True)

        decided = decide_signed_receipt_acceptance(signed, [], signed["created_at"])
        mapped = acceptance_transition_proposal_from_decision(decided)
        self.assertEqual(mapped, proposal)

    def test_uaii_integration_and_capabilities(self) -> None:
        signed = _signed()
        ok = _uaii_verify(signed, verification_time=signed["created_at"], nonce="ok")
        self.assertTrue(ok["ok"])
        self.assertEqual(
            ok["result"]["acceptance_transition_proposal"],
            _applicable_proposal(signed["receipt_id"]),
        )
        self.assertIs(ok["result"]["transition_applied"], False)
        self.assertIs(ok["result"]["accepted_receipt_ids_mutated"], False)

        rejected = _uaii_verify(
            signed,
            accepted=[signed["receipt_id"]],
            verification_time=signed["created_at"],
            nonce="rej",
        )
        self.assertEqual(
            rejected["result"]["acceptance_transition_proposal"]["proposal_status"],
            "not_applicable",
        )

        self.assertIn("verify_signed_receipt", OPERATIONS)
        self.assertIn("get_payment_receipt", OPERATIONS)
        self.assertIn(
            ("uaii.verify_signed_receipt", "verify_signed_receipt", "supported"),
            CAPABILITIES,
        )
        disc = {
            "interface_profile": INTERFACE_PROFILE,
            "operation": "discover_capabilities",
            "request_id": _hex64("disc"),
            "created_at": 1_699_999_000,
            "expires_at": 1_700_000_100,
            "nonce": "disc",
            "execution_authorized": False,
            "params": {"include_adapter_declarations": False},
        }
        d = process_uaii_request(
            json.dumps(disc, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
            _context(),
        )
        self.assertEqual(d["result"]["operations"], list(OPERATIONS))

        unknown = dict(disc)
        unknown["operation"] = "not_a_real_operation"
        unknown["nonce"] = "unk"
        unknown["request_id"] = _hex64("unk")
        u = process_uaii_request(
            json.dumps(unknown, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
            _context(),
        )
        self.assertFalse(u["ok"])

    def test_stateless_order_independent_and_no_side_effects(self) -> None:
        signed = _signed()
        a = propose_signed_receipt_acceptance_transition(
            signed, [signed["receipt_id"]], signed["created_at"]
        )
        b = propose_signed_receipt_acceptance_transition(signed, [], signed["created_at"])
        c = propose_signed_receipt_acceptance_transition(
            signed, [signed["receipt_id"]], signed["created_at"]
        )
        self.assertEqual(a["acceptance_transition_proposal"]["proposal_status"], "not_applicable")
        self.assertEqual(b["acceptance_transition_proposal"]["proposal_status"], "applicable")
        self.assertEqual(a, c)

        with mock.patch("coin.tx_validation.validate_transaction") as vt, mock.patch(
            "coin.m2m_verifier.canonicalize", create=True
        ) as canon:
            propose_signed_receipt_acceptance_transition(signed, [], signed["created_at"])
            vt.assert_not_called()
            canon.assert_not_called()

        self.assertTrue(receipt.transition_proposed_only)
        self.assertFalse(receipt.transition_applied)
        self.assertFalse(receipt.acceptance_state_mutated)
        self.assertFalse(receipt.accepted_receipt_ids_mutated)
        self.assertFalse(receipt.receipt_recorded)
        self.assertFalse(receipt.persistent_state_created)
        self.assertFalse(receipt.system_clock_read)
        self.assertFalse(receipt.implicit_time_used)
        self.assertFalse(receipt.signing_authorized)
        self.assertFalse(receipt.persistent_keys_created)
        self.assertFalse(receipt.private_material_exposed)
        self.assertFalse(receipt.spend_authorized)
        self.assertFalse(receipt.settlement_authorized)
        self.assertFalse(receipt.transaction_submission_authorized)
        self.assertFalse(receipt.ledger_mutated)
        self.assertFalse(receipt.adapters_activated)
        self.assertFalse(receipt.runtime_activated)
        self.assertEqual(tx_validation.L28_MAX_SUPPLY, 28_000_000)
        src = Path(receipt.__file__).read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\bdatetime\.(now|utcnow)\b", src))
        self.assertIsNone(re.search(r"\btime\.time\b", src))
        self.assertNotIn("Ed25519PrivateKey", src)


if __name__ == "__main__":
    unittest.main()
