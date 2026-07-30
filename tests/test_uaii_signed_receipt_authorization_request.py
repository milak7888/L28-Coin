# SPDX-License-Identifier: Apache-2.0
"""Foundation 75 — inert transition-authorization request proposal tests."""

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
    RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS,
    SUPPORTED_GOVERNANCE_APPROVAL_SCOPE,
    TRANSITION_AUTHORIZATION_REQUEST_PROPOSAL_FIELDS,
    F64ReceiptSchemaError,
    evaluate_signed_receipt_governance_approval,
    propose_signed_receipt_transition_authorization_request,
    public_key_id_for_raw,
    required_signer_identity,
    sign_unsigned_receipt_facts,
    transition_authorization_request_proposal_from_evaluation,
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


def _approval(
    receipt_id: str,
    *,
    decision: str = "approved",
    transition_kind: str = "add_accepted_receipt_id",
    scope: str = SUPPORTED_GOVERNANCE_APPROVAL_SCOPE,
    approval_id: str | None = None,
) -> dict[str, Any]:
    return {
        "approval_id": approval_id or _hex64("approval"),
        "approval_subject_receipt_id": receipt_id,
        "approval_transition_kind": transition_kind,
        "approval_decision": decision,
        "approval_scope": scope,
    }


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
    evidence: dict[str, Any] | None = None,
    nonce: str,
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "signed_receipt": signed,
        "accepted_receipt_ids": [] if accepted is None else accepted,
        "verification_time": verification_time,
        "governance_approval_evidence": {} if evidence is None else evidence,
        "authorization_response_evidence": {},
    }
    if extra_params:
        params.update(extra_params)
    env = {
        "interface_profile": INTERFACE_PROFILE,
        "operation": "verify_signed_receipt",
        "request_id": _hex64("verify" + nonce),
        "created_at": 1_699_999_000,
        "expires_at": 1_700_000_100,
        "nonce": nonce,
        "execution_authorized": False,
        "params": params,
    }
    raw = json.dumps(env, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return process_uaii_request(raw, _context())


class TestFoundation75AuthorizationRequestProposal(unittest.TestCase):
    def test_proposed_case_all_flags_false(self) -> None:
        signed = _signed()
        evidence = _approval(signed["receipt_id"])
        out = propose_signed_receipt_transition_authorization_request(
            signed, [], signed["created_at"], evidence
        )
        prop = out["transition_authorization_request_proposal"]
        self.assertEqual(prop["authorization_request_proposal_status"], "proposed")
        self.assertEqual(prop["authorization_request_proposal_reason"], "")
        self.assertEqual(prop["receipt_id"], signed["receipt_id"])
        self.assertEqual(prop["transition_kind"], "add_accepted_receipt_id")
        self.assertEqual(prop["approval_id"], evidence["approval_id"])
        self.assertEqual(tuple(prop.keys()), TRANSITION_AUTHORIZATION_REQUEST_PROPOSAL_FIELDS)
        for flag in (
            "authorization_requested",
            "authorization_granted",
            "application_authorized",
            "application_executed",
            "transition_applied",
            "state_mutated",
            "persistent_state_created",
        ):
            self.assertIs(prop[flag], False)
        again = propose_signed_receipt_transition_authorization_request(
            signed, [], signed["created_at"], evidence
        )
        self.assertEqual(prop, again["transition_authorization_request_proposal"])

    def test_not_satisfied_and_not_supplied_cannot_propose(self) -> None:
        signed = _signed()
        missing = propose_signed_receipt_transition_authorization_request(
            signed, [], signed["created_at"], {}
        )["transition_authorization_request_proposal"]
        self.assertEqual(missing["authorization_request_proposal_status"], "not_proposed")
        self.assertEqual(
            missing["authorization_request_proposal_reason"],
            "governance_approval_not_satisfied",
        )

        rejected = propose_signed_receipt_transition_authorization_request(
            signed,
            [],
            signed["created_at"],
            _approval(signed["receipt_id"], decision="rejected"),
        )["transition_authorization_request_proposal"]
        self.assertEqual(rejected["authorization_request_proposal_status"], "not_proposed")
        self.assertEqual(
            rejected["authorization_request_proposal_reason"],
            "governance_approval_not_satisfied",
        )

        for evidence, _reason in (
            (_approval(_hex64("other")), "receipt_id_mismatch"),
            (_approval(signed["receipt_id"], transition_kind="other"), "transition_kind_mismatch"),
            (_approval(signed["receipt_id"], scope="other"), "approval_scope_mismatch"),
        ):
            prop = propose_signed_receipt_transition_authorization_request(
                signed, [], signed["created_at"], evidence
            )["transition_authorization_request_proposal"]
            self.assertEqual(prop["authorization_request_proposal_status"], "not_proposed")
            self.assertEqual(
                prop["authorization_request_proposal_reason"],
                "governance_approval_not_satisfied",
            )

    def test_ineligible_and_replay_precedence(self) -> None:
        signed = _signed()
        evidence = _approval(signed["receipt_id"])
        t_expired = signed["expires_at"] + RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS + 1

        replayed = propose_signed_receipt_transition_authorization_request(
            signed, [signed["receipt_id"]], signed["created_at"], evidence
        )
        self.assertEqual(replayed["rejection_reason"], "replayed")
        self.assertEqual(
            replayed["transition_authorization_request_proposal"][
                "authorization_request_proposal_reason"
            ],
            "acceptance_not_accepted",
        )

        expired = propose_signed_receipt_transition_authorization_request(
            signed, [], t_expired, evidence
        )
        self.assertEqual(expired["rejection_reason"], "expired")
        self.assertEqual(
            expired["transition_authorization_request_proposal"][
                "authorization_request_proposal_reason"
            ],
            "acceptance_not_accepted",
        )

        both = propose_signed_receipt_transition_authorization_request(
            signed, [signed["receipt_id"]], t_expired, evidence
        )
        self.assertEqual(both["rejection_reason"], "replayed")
        self.assertEqual(
            both["transition_authorization_request_proposal"][
                "authorization_request_proposal_reason"
            ],
            "acceptance_not_accepted",
        )

    def test_inconsistent_prerequisites_not_proposed(self) -> None:
        signed = _signed()
        evidence = _approval(signed["receipt_id"])
        evaluated = evaluate_signed_receipt_governance_approval(
            signed, [], signed["created_at"], evidence
        )
        bad = copy.deepcopy(evaluated)
        bad["governance_approval_evaluation"]["approval_granted"] = True
        prop = transition_authorization_request_proposal_from_evaluation(bad)
        self.assertEqual(prop["authorization_request_proposal_status"], "not_proposed")
        self.assertEqual(prop["authorization_request_proposal_reason"], "proposal_inconsistent")

        bad2 = copy.deepcopy(evaluated)
        bad2["governance_approval_evaluation"]["approval_id"] = ""
        prop2 = transition_authorization_request_proposal_from_evaluation(bad2)
        self.assertEqual(prop2["authorization_request_proposal_reason"], "approval_id_missing")

    def test_forbidden_caller_fields_rejected(self) -> None:
        signed = _signed()
        for extra in (
            {"authorization_requested": True},
            {"authorization_token": "t"},
            {"authority_id": "gov"},
            {"signature": "ab" * 32},
            {"execution_request": True},
            {"persist": True},
        ):
            with self.subTest(extra=extra):
                r = _uaii_verify(
                    signed,
                    verification_time=signed["created_at"],
                    evidence=_approval(signed["receipt_id"]),
                    nonce="x" + next(iter(extra)),
                    extra_params=extra,
                )
                self.assertFalse(r["ok"])

    def test_crypto_failure_no_proposal(self) -> None:
        signed = _signed()
        bad = dict(signed)
        bad["signature"] = "ab" * 64
        with self.assertRaises(F64ReceiptSchemaError):
            propose_signed_receipt_transition_authorization_request(
                bad, [], signed["created_at"], _approval(signed["receipt_id"])
            )
        uaii = _uaii_verify(
            bad,
            verification_time=signed["created_at"],
            evidence=_approval(signed["receipt_id"]),
            nonce="cfail",
        )
        self.assertFalse(uaii["ok"])
        self.assertNotIn(
            "transition_authorization_request_proposal", uaii.get("result") or {}
        )

    def test_reuses_foundation74_path(self) -> None:
        signed = _signed()
        with mock.patch(
            "coin.uaii_signed_receipt.evaluate_signed_receipt_governance_approval",
            wraps=evaluate_signed_receipt_governance_approval,
        ) as wrapped:
            propose_signed_receipt_transition_authorization_request(
                signed, [], signed["created_at"], {}
            )
            wrapped.assert_called_once()
        src = inspect.getsource(propose_signed_receipt_transition_authorization_request)
        self.assertIn("evaluate_signed_receipt_governance_approval", src)
        self.assertNotIn("verify_signed_receipt_facts", src)
        self.assertNotIn("Ed25519PublicKey", src)

    def test_uaii_integration(self) -> None:
        signed = _signed()
        evidence = _approval(signed["receipt_id"])
        ok = _uaii_verify(
            signed,
            verification_time=signed["created_at"],
            evidence=evidence,
            nonce="ok",
        )
        self.assertTrue(ok["ok"])
        prop = ok["result"]["transition_authorization_request_proposal"]
        self.assertEqual(prop["authorization_request_proposal_status"], "proposed")
        self.assertIs(ok["result"]["authorization_requested"], False)
        self.assertIs(ok["result"]["authorization_granted"], False)
        self.assertIs(ok["result"]["authorization_request_proposed_only"], True)

        self.assertIn("verify_signed_receipt", OPERATIONS)
        self.assertIn("get_payment_receipt", OPERATIONS)
        self.assertIn(
            ("uaii.verify_signed_receipt", "verify_signed_receipt", "supported"),
            CAPABILITIES,
        )

    def test_inputs_stateless_no_side_effects(self) -> None:
        signed = _signed()
        accepted: list[str] = []
        evidence = _approval(signed["receipt_id"])
        snap_signed = copy.deepcopy(signed)
        snap_accepted = list(accepted)
        snap_evidence = copy.deepcopy(evidence)
        a = propose_signed_receipt_transition_authorization_request(
            signed, accepted, signed["created_at"], evidence
        )
        b = propose_signed_receipt_transition_authorization_request(
            signed, accepted, signed["created_at"], {}
        )
        c = propose_signed_receipt_transition_authorization_request(
            signed, accepted, signed["created_at"], evidence
        )
        self.assertEqual(signed, snap_signed)
        self.assertEqual(accepted, snap_accepted)
        self.assertEqual(evidence, snap_evidence)
        self.assertEqual(a, c)
        self.assertEqual(
            b["transition_authorization_request_proposal"][
                "authorization_request_proposal_status"
            ],
            "not_proposed",
        )

        with mock.patch("coin.tx_validation.validate_transaction") as vt, mock.patch(
            "coin.m2m_verifier.canonicalize", create=True
        ) as canon:
            propose_signed_receipt_transition_authorization_request(
                signed, [], signed["created_at"], evidence
            )
            vt.assert_not_called()
            canon.assert_not_called()

        self.assertTrue(receipt.authorization_request_proposed_only)
        self.assertFalse(receipt.authorization_requested)
        self.assertFalse(receipt.authorization_submitted)
        self.assertFalse(receipt.authorization_issued)
        self.assertFalse(receipt.authorization_granted)
        self.assertFalse(receipt.application_authorized)
        self.assertFalse(receipt.transition_applied)
        self.assertFalse(receipt.accepted_receipt_ids_mutated)
        self.assertFalse(receipt.persistent_state_created)
        self.assertFalse(receipt.system_clock_read)
        self.assertEqual(tx_validation.L28_MAX_SUPPLY, 28_000_000)
        src = Path(receipt.__file__).read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\bdatetime\.(now|utcnow)\b", src))
        self.assertNotIn("Ed25519PrivateKey", src)


if __name__ == "__main__":
    unittest.main()
