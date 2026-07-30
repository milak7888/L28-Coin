# SPDX-License-Identifier: Apache-2.0
"""Foundation 74 — caller-supplied governance-approval evaluation contract tests."""

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
    GOVERNANCE_APPROVAL_EVALUATION_FIELDS,
    RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS,
    SUPPORTED_GOVERNANCE_APPROVAL_SCOPE,
    F64ReceiptSchemaError,
    evaluate_signed_receipt_acceptance_transition_application_boundary,
    evaluate_signed_receipt_governance_approval,
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


class TestFoundation74GovernanceApprovalEvaluation(unittest.TestCase):
    def test_satisfied_never_grants_authorization(self) -> None:
        signed = _signed()
        evidence = _approval(signed["receipt_id"])
        out = evaluate_signed_receipt_governance_approval(
            signed, [], signed["created_at"], evidence
        )
        ev = out["governance_approval_evaluation"]
        self.assertEqual(ev["governance_approval_evaluation_status"], "satisfied")
        self.assertEqual(ev["governance_approval_evaluation_reason"], "")
        self.assertEqual(ev["approval_id"], evidence["approval_id"])
        self.assertEqual(tuple(ev.keys()), GOVERNANCE_APPROVAL_EVALUATION_FIELDS)
        for flag in (
            "approval_granted",
            "application_authorized",
            "application_executed",
            "transition_applied",
            "state_mutated",
            "persistent_state_created",
        ):
            self.assertIs(ev[flag], False)
        again = evaluate_signed_receipt_governance_approval(
            signed, [], signed["created_at"], evidence
        )
        self.assertEqual(ev, again["governance_approval_evaluation"])

    def test_rejected_and_missing_evidence(self) -> None:
        signed = _signed()
        rejected = evaluate_signed_receipt_governance_approval(
            signed,
            [],
            signed["created_at"],
            _approval(signed["receipt_id"], decision="rejected"),
        )["governance_approval_evaluation"]
        self.assertEqual(rejected["governance_approval_evaluation_status"], "not_satisfied")
        self.assertEqual(rejected["governance_approval_evaluation_reason"], "approval_rejected")

        missing = evaluate_signed_receipt_governance_approval(
            signed, [], signed["created_at"], {}
        )["governance_approval_evaluation"]
        self.assertEqual(missing["governance_approval_evaluation_status"], "not_supplied")
        self.assertEqual(missing["governance_approval_evaluation_reason"], "approval_not_supplied")
        self.assertEqual(missing["approval_id"], "")

    def test_mismatches_fail_closed(self) -> None:
        signed = _signed()
        t = signed["created_at"]
        rid = signed["receipt_id"]
        cases = [
            (_approval(_hex64("other")), "receipt_id_mismatch"),
            (_approval(rid, transition_kind="other_kind"), "transition_kind_mismatch"),
            (_approval(rid, scope="other_scope"), "approval_scope_mismatch"),
        ]
        for evidence, reason in cases:
            with self.subTest(reason=reason):
                ev = evaluate_signed_receipt_governance_approval(
                    signed, [], t, evidence
                )["governance_approval_evaluation"]
                self.assertEqual(ev["governance_approval_evaluation_status"], "not_satisfied")
                self.assertEqual(ev["governance_approval_evaluation_reason"], reason)

    def test_ineligible_boundary_not_overridable(self) -> None:
        signed = _signed()
        t_expired = signed["expires_at"] + RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS + 1
        evidence = _approval(signed["receipt_id"])

        replayed = evaluate_signed_receipt_governance_approval(
            signed, [signed["receipt_id"]], signed["created_at"], evidence
        )
        self.assertEqual(replayed["rejection_reason"], "replayed")
        self.assertEqual(
            replayed["governance_approval_evaluation"][
                "governance_approval_evaluation_reason"
            ],
            "boundary_ineligible",
        )

        expired = evaluate_signed_receipt_governance_approval(
            signed, [], t_expired, evidence
        )
        self.assertEqual(expired["rejection_reason"], "expired")
        self.assertEqual(
            expired["governance_approval_evaluation"][
                "governance_approval_evaluation_reason"
            ],
            "boundary_ineligible",
        )

        both = evaluate_signed_receipt_governance_approval(
            signed, [signed["receipt_id"]], t_expired, evidence
        )
        self.assertEqual(both["rejection_reason"], "replayed")
        self.assertEqual(
            both["governance_approval_evaluation"][
                "governance_approval_evaluation_reason"
            ],
            "boundary_ineligible",
        )

    def test_malformed_evidence_and_forbidden_fields(self) -> None:
        signed = _signed()
        t = signed["created_at"]
        for bad in (
            None,
            True,
            [],
            {"approval_id": _hex64("a")},
            {
                **_approval(signed["receipt_id"]),
                "extra": 1,
            },
            {
                "approval_decision": "approved",
                "approval_id": _hex64("a"),
                "approval_subject_receipt_id": signed["receipt_id"],
                "approval_transition_kind": "add_accepted_receipt_id",
                "approval_scope": SUPPORTED_GOVERNANCE_APPROVAL_SCOPE,
            },
            _approval(signed["receipt_id"], decision="maybe"),
            {
                "approval_id": "",
                "approval_subject_receipt_id": signed["receipt_id"],
                "approval_transition_kind": "add_accepted_receipt_id",
                "approval_decision": "approved",
                "approval_scope": SUPPORTED_GOVERNANCE_APPROVAL_SCOPE,
            },
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(F64ReceiptSchemaError):
                    evaluate_signed_receipt_governance_approval(signed, [], t, bad)

        for extra in (
            {"authority_id": "gov"},
            {"approval_token": "t"},
            {"credentials": "c"},
            {"signature": "ab" * 32},
            {"application_authorized": True},
            {"execution_request": True},
        ):
            with self.subTest(extra=extra):
                r = _uaii_verify(
                    signed,
                    verification_time=t,
                    nonce="bad" + next(iter(extra)),
                    extra_params=extra,
                )
                self.assertFalse(r["ok"])

    def test_crypto_failure_no_evaluation(self) -> None:
        signed = _signed()
        bad = dict(signed)
        bad["signature"] = "ab" * 64
        with self.assertRaises(F64ReceiptSchemaError):
            evaluate_signed_receipt_governance_approval(
                bad, [], signed["created_at"], _approval(signed["receipt_id"])
            )
        uaii = _uaii_verify(
            bad,
            verification_time=signed["created_at"],
            evidence=_approval(signed["receipt_id"]),
            nonce="cfail",
        )
        self.assertFalse(uaii["ok"])
        self.assertNotIn("governance_approval_evaluation", uaii.get("result") or {})

    def test_reuses_foundation73_path(self) -> None:
        signed = _signed()
        with mock.patch(
            "coin.uaii_signed_receipt.evaluate_signed_receipt_acceptance_transition_application_boundary",
            wraps=evaluate_signed_receipt_acceptance_transition_application_boundary,
        ) as wrapped:
            evaluate_signed_receipt_governance_approval(
                signed, [], signed["created_at"], {}
            )
            wrapped.assert_called_once()
        src = inspect.getsource(evaluate_signed_receipt_governance_approval)
        self.assertIn(
            "evaluate_signed_receipt_acceptance_transition_application_boundary", src
        )
        self.assertNotIn("verify_signed_receipt_facts", src)
        self.assertNotIn("Ed25519PublicKey", src)

    def test_uaii_integration(self) -> None:
        signed = _signed()
        ok = _uaii_verify(
            signed,
            verification_time=signed["created_at"],
            evidence=_approval(signed["receipt_id"]),
            nonce="ok",
        )
        self.assertTrue(ok["ok"])
        ev = ok["result"]["governance_approval_evaluation"]
        self.assertEqual(ev["governance_approval_evaluation_status"], "satisfied")
        self.assertIs(ok["result"]["approval_granted"], False)
        self.assertIs(ok["result"]["authorization_granted"], False)
        self.assertIs(ok["result"]["caller_supplied_approval_evaluated_only"], True)

        missing = _uaii_verify(
            signed, verification_time=signed["created_at"], evidence={}, nonce="ns"
        )
        self.assertEqual(
            missing["result"]["governance_approval_evaluation"][
                "governance_approval_evaluation_status"
            ],
            "not_supplied",
        )

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
        a = evaluate_signed_receipt_governance_approval(
            signed, accepted, signed["created_at"], evidence
        )
        b = evaluate_signed_receipt_governance_approval(
            signed, [signed["receipt_id"]], signed["created_at"], evidence
        )
        c = evaluate_signed_receipt_governance_approval(
            signed, accepted, signed["created_at"], evidence
        )
        self.assertEqual(signed, snap_signed)
        self.assertEqual(accepted, snap_accepted)
        self.assertEqual(evidence, snap_evidence)
        self.assertEqual(a, c)
        self.assertEqual(
            b["governance_approval_evaluation"][
                "governance_approval_evaluation_reason"
            ],
            "boundary_ineligible",
        )

        with mock.patch("coin.tx_validation.validate_transaction") as vt, mock.patch(
            "coin.m2m_verifier.canonicalize", create=True
        ) as canon:
            evaluate_signed_receipt_governance_approval(
                signed, [], signed["created_at"], evidence
            )
            vt.assert_not_called()
            canon.assert_not_called()

        self.assertTrue(receipt.caller_supplied_approval_evaluated_only)
        self.assertFalse(receipt.approval_issued)
        self.assertFalse(receipt.approval_granted)
        self.assertFalse(receipt.authorization_granted)
        self.assertFalse(receipt.application_authorized)
        self.assertFalse(receipt.application_executed)
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
