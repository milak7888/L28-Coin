# SPDX-License-Identifier: Apache-2.0
"""Foundation 76 — caller-supplied authorization-response evaluation tests."""

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
    AUTHORIZATION_RESPONSE_EVALUATION_FIELDS,
    RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS,
    SUPPORTED_GOVERNANCE_APPROVAL_SCOPE,
    F64ReceiptSchemaError,
    evaluate_signed_receipt_authorization_response,
    propose_signed_receipt_transition_authorization_request,
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


def _approval(receipt_id: str, **overrides: Any) -> dict[str, Any]:
    obj = {
        "approval_id": _hex64("approval"),
        "approval_subject_receipt_id": receipt_id,
        "approval_transition_kind": "add_accepted_receipt_id",
        "approval_decision": "approved",
        "approval_scope": SUPPORTED_GOVERNANCE_APPROVAL_SCOPE,
    }
    obj.update(overrides)
    return obj


def _response(
    receipt_id: str,
    approval_id: str,
    *,
    decision: str = "authorized",
    transition_kind: str = "add_accepted_receipt_id",
    scope: str = SUPPORTED_GOVERNANCE_APPROVAL_SCOPE,
    response_id: str | None = None,
) -> dict[str, Any]:
    return {
        "authorization_response_id": response_id or _hex64("auth-resp"),
        "authorization_request_receipt_id": receipt_id,
        "authorization_request_transition_kind": transition_kind,
        "authorization_request_approval_id": approval_id,
        "authorization_decision": decision,
        "authorization_scope": scope,
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
    governance: dict[str, Any] | None = None,
    response: dict[str, Any] | None = None,
    nonce: str,
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "signed_receipt": signed,
        "accepted_receipt_ids": [] if accepted is None else accepted,
        "verification_time": verification_time,
        "governance_approval_evidence": {} if governance is None else governance,
        "authorization_response_evidence": {} if response is None else response,
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


class TestFoundation76AuthorizationResponseEvaluation(unittest.TestCase):
    def test_satisfied_never_grants(self) -> None:
        signed = _signed()
        approval = _approval(signed["receipt_id"])
        response = _response(signed["receipt_id"], approval["approval_id"])
        out = evaluate_signed_receipt_authorization_response(
            signed, [], signed["created_at"], approval, response
        )
        ev = out["authorization_response_evaluation"]
        self.assertEqual(ev["authorization_response_evaluation_status"], "satisfied")
        self.assertEqual(ev["authorization_response_evaluation_reason"], "")
        self.assertEqual(ev["authorization_response_id"], response["authorization_response_id"])
        self.assertEqual(tuple(ev.keys()), AUTHORIZATION_RESPONSE_EVALUATION_FIELDS)
        for flag in (
            "authorization_issued",
            "authorization_granted",
            "authorization_active",
            "application_authorized",
            "application_executed",
            "transition_applied",
            "state_mutated",
            "persistent_state_created",
        ):
            self.assertIs(ev[flag], False)
        again = evaluate_signed_receipt_authorization_response(
            signed, [], signed["created_at"], approval, response
        )
        self.assertEqual(ev, again["authorization_response_evaluation"])

    def test_denied_and_missing(self) -> None:
        signed = _signed()
        approval = _approval(signed["receipt_id"])
        denied = evaluate_signed_receipt_authorization_response(
            signed,
            [],
            signed["created_at"],
            approval,
            _response(signed["receipt_id"], approval["approval_id"], decision="denied"),
        )["authorization_response_evaluation"]
        self.assertEqual(denied["authorization_response_evaluation_status"], "not_satisfied")
        self.assertEqual(denied["authorization_response_evaluation_reason"], "authorization_denied")

        missing = evaluate_signed_receipt_authorization_response(
            signed, [], signed["created_at"], approval, {}
        )["authorization_response_evaluation"]
        self.assertEqual(missing["authorization_response_evaluation_status"], "not_supplied")
        self.assertEqual(
            missing["authorization_response_evaluation_reason"],
            "authorization_response_not_supplied",
        )

    def test_mismatches_fail_closed(self) -> None:
        signed = _signed()
        approval = _approval(signed["receipt_id"])
        aid = approval["approval_id"]
        rid = signed["receipt_id"]
        cases = [
            (_response(_hex64("other"), aid), "receipt_id_mismatch"),
            (_response(rid, aid, transition_kind="other"), "transition_kind_mismatch"),
            (_response(rid, _hex64("other-appr")), "approval_id_mismatch"),
            (_response(rid, aid, scope="other"), "authorization_scope_mismatch"),
        ]
        for evidence, reason in cases:
            with self.subTest(reason=reason):
                ev = evaluate_signed_receipt_authorization_response(
                    signed, [], signed["created_at"], approval, evidence
                )["authorization_response_evaluation"]
                self.assertEqual(ev["authorization_response_evaluation_status"], "not_satisfied")
                self.assertEqual(ev["authorization_response_evaluation_reason"], reason)

    def test_not_proposed_cannot_override(self) -> None:
        signed = _signed()
        approval = _approval(signed["receipt_id"])
        response = _response(signed["receipt_id"], approval["approval_id"])
        # No governance → F75 not_proposed
        missing_gov = evaluate_signed_receipt_authorization_response(
            signed, [], signed["created_at"], {}, response
        )["authorization_response_evaluation"]
        self.assertEqual(
            missing_gov["authorization_response_evaluation_reason"],
            "authorization_request_not_proposed",
        )

        rejected_gov = evaluate_signed_receipt_authorization_response(
            signed,
            [],
            signed["created_at"],
            _approval(signed["receipt_id"], approval_decision="rejected"),
            response,
        )["authorization_response_evaluation"]
        self.assertEqual(
            rejected_gov["authorization_response_evaluation_reason"],
            "authorization_request_not_proposed",
        )

        replayed = evaluate_signed_receipt_authorization_response(
            signed,
            [signed["receipt_id"]],
            signed["created_at"],
            approval,
            response,
        )
        self.assertEqual(replayed["rejection_reason"], "replayed")
        self.assertEqual(
            replayed["authorization_response_evaluation"][
                "authorization_response_evaluation_reason"
            ],
            "authorization_request_not_proposed",
        )

        expired = evaluate_signed_receipt_authorization_response(
            signed,
            [],
            signed["expires_at"] + RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS + 1,
            approval,
            response,
        )
        self.assertEqual(expired["rejection_reason"], "expired")
        self.assertEqual(
            expired["authorization_response_evaluation"][
                "authorization_response_evaluation_reason"
            ],
            "authorization_request_not_proposed",
        )

        both = evaluate_signed_receipt_authorization_response(
            signed,
            [signed["receipt_id"]],
            signed["expires_at"] + RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS + 1,
            approval,
            response,
        )
        self.assertEqual(both["rejection_reason"], "replayed")

    def test_malformed_and_forbidden_fields(self) -> None:
        signed = _signed()
        approval = _approval(signed["receipt_id"])
        t = signed["created_at"]
        for bad in (
            None,
            True,
            [],
            {"authorization_response_id": _hex64("x")},
            {**_response(signed["receipt_id"], approval["approval_id"]), "extra": 1},
            _response(signed["receipt_id"], approval["approval_id"], decision="maybe"),
            {
                "authorization_response_id": "",
                "authorization_request_receipt_id": signed["receipt_id"],
                "authorization_request_transition_kind": "add_accepted_receipt_id",
                "authorization_request_approval_id": approval["approval_id"],
                "authorization_decision": "authorized",
                "authorization_scope": SUPPORTED_GOVERNANCE_APPROVAL_SCOPE,
            },
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(F64ReceiptSchemaError):
                    evaluate_signed_receipt_authorization_response(
                        signed, [], t, approval, bad
                    )

        for extra in (
            {"authority_id": "gov"},
            {"authorization_token": "t"},
            {"credentials": "c"},
            {"signature": "ab" * 32},
            {"execution_request": True},
            {"persist": True},
        ):
            with self.subTest(extra=extra):
                r = _uaii_verify(
                    signed,
                    verification_time=t,
                    governance=approval,
                    response=_response(signed["receipt_id"], approval["approval_id"]),
                    nonce="x" + next(iter(extra)),
                    extra_params=extra,
                )
                self.assertFalse(r["ok"])

    def test_crypto_failure_no_evaluation(self) -> None:
        signed = _signed()
        approval = _approval(signed["receipt_id"])
        response = _response(signed["receipt_id"], approval["approval_id"])
        bad = dict(signed)
        bad["signature"] = "ab" * 64
        with self.assertRaises(F64ReceiptSchemaError):
            evaluate_signed_receipt_authorization_response(
                bad, [], signed["created_at"], approval, response
            )
        uaii = _uaii_verify(
            bad,
            verification_time=signed["created_at"],
            governance=approval,
            response=response,
            nonce="cfail",
        )
        self.assertFalse(uaii["ok"])
        self.assertNotIn("authorization_response_evaluation", uaii.get("result") or {})

    def test_reuses_foundation75_path(self) -> None:
        signed = _signed()
        with mock.patch(
            "coin.uaii_signed_receipt.propose_signed_receipt_transition_authorization_request",
            wraps=propose_signed_receipt_transition_authorization_request,
        ) as wrapped:
            evaluate_signed_receipt_authorization_response(
                signed, [], signed["created_at"], {}, {}
            )
            wrapped.assert_called_once()
        src = inspect.getsource(evaluate_signed_receipt_authorization_response)
        self.assertIn("propose_signed_receipt_transition_authorization_request", src)
        self.assertNotIn("verify_signed_receipt_facts", src)
        self.assertNotIn("Ed25519PublicKey", src)

    def test_uaii_integration(self) -> None:
        signed = _signed()
        approval = _approval(signed["receipt_id"])
        response = _response(signed["receipt_id"], approval["approval_id"])
        ok = _uaii_verify(
            signed,
            verification_time=signed["created_at"],
            governance=approval,
            response=response,
            nonce="ok",
        )
        self.assertTrue(ok["ok"])
        ev = ok["result"]["authorization_response_evaluation"]
        self.assertEqual(ev["authorization_response_evaluation_status"], "satisfied")
        self.assertIs(ok["result"]["authorization_granted"], False)
        self.assertIs(ok["result"]["authorization_active"], False)
        self.assertIs(
            ok["result"]["caller_supplied_authorization_response_evaluated_only"], True
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
        approval = _approval(signed["receipt_id"])
        response = _response(signed["receipt_id"], approval["approval_id"])
        snap_signed = copy.deepcopy(signed)
        snap_accepted = list(accepted)
        snap_approval = copy.deepcopy(approval)
        snap_response = copy.deepcopy(response)
        a = evaluate_signed_receipt_authorization_response(
            signed, accepted, signed["created_at"], approval, response
        )
        b = evaluate_signed_receipt_authorization_response(
            signed, accepted, signed["created_at"], approval, {}
        )
        c = evaluate_signed_receipt_authorization_response(
            signed, accepted, signed["created_at"], approval, response
        )
        self.assertEqual(signed, snap_signed)
        self.assertEqual(accepted, snap_accepted)
        self.assertEqual(approval, snap_approval)
        self.assertEqual(response, snap_response)
        self.assertEqual(a, c)
        self.assertEqual(
            b["authorization_response_evaluation"][
                "authorization_response_evaluation_status"
            ],
            "not_supplied",
        )

        with mock.patch("coin.tx_validation.validate_transaction") as vt, mock.patch(
            "coin.m2m_verifier.canonicalize", create=True
        ) as canon:
            evaluate_signed_receipt_authorization_response(
                signed, [], signed["created_at"], approval, response
            )
            vt.assert_not_called()
            canon.assert_not_called()

        self.assertTrue(receipt.caller_supplied_authorization_response_evaluated_only)
        self.assertFalse(receipt.authorization_response_issued)
        self.assertFalse(receipt.authorization_requested)
        self.assertFalse(receipt.authorization_submitted)
        self.assertFalse(receipt.authorization_issued)
        self.assertFalse(receipt.authorization_granted)
        self.assertFalse(receipt.authorization_active)
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
