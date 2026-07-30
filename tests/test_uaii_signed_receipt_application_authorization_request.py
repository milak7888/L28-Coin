# SPDX-License-Identifier: Apache-2.0
"""Foundation 78 — transition-application authorization request proposal tests."""

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
    TRANSITION_APPLICATION_AUTHORIZATION_REQUEST_PROPOSAL_FIELDS,
    F64ReceiptSchemaError,
    propose_signed_receipt_transition_application_authorization_eligibility,
    propose_signed_receipt_transition_application_authorization_request,
    public_key_id_for_raw,
    required_signer_identity,
    sign_unsigned_receipt_facts,
    transition_application_authorization_request_proposal_from_eligibility,
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


_INERT_FLAGS = (
    "application_authorization_requested",
    "application_authorization_submitted",
    "authorization_issued",
    "authorization_granted",
    "authorization_active",
    "application_authorized",
    "application_executed",
    "transition_applied",
    "state_mutated",
    "persistent_state_created",
)


class TestFoundation78ApplicationAuthorizationRequestProposal(unittest.TestCase):
    def test_proposed_never_authorizes(self) -> None:
        signed = _signed()
        approval = _approval(signed["receipt_id"])
        response = _response(signed["receipt_id"], approval["approval_id"])
        out = propose_signed_receipt_transition_application_authorization_request(
            signed, [], signed["created_at"], approval, response
        )
        prop = out["transition_application_authorization_request_proposal"]
        self.assertEqual(
            prop["transition_application_authorization_request_status"], "proposed"
        )
        self.assertEqual(prop["transition_application_authorization_request_reason"], "")
        self.assertEqual(prop["receipt_id"], signed["receipt_id"])
        self.assertEqual(prop["transition_kind"], "add_accepted_receipt_id")
        self.assertEqual(prop["approval_id"], approval["approval_id"])
        self.assertEqual(
            prop["authorization_response_id"], response["authorization_response_id"]
        )
        self.assertEqual(prop["authorization_scope"], SUPPORTED_GOVERNANCE_APPROVAL_SCOPE)
        self.assertEqual(
            tuple(prop.keys()),
            TRANSITION_APPLICATION_AUTHORIZATION_REQUEST_PROPOSAL_FIELDS,
        )
        for flag in _INERT_FLAGS:
            self.assertIs(prop[flag], False)
        again = propose_signed_receipt_transition_application_authorization_request(
            signed, [], signed["created_at"], approval, response
        )
        self.assertEqual(
            prop, again["transition_application_authorization_request_proposal"]
        )

    def test_proposed_is_not_submission_or_grant(self) -> None:
        signed = _signed()
        approval = _approval(signed["receipt_id"])
        response = _response(signed["receipt_id"], approval["approval_id"])
        out = propose_signed_receipt_transition_application_authorization_request(
            signed, [], signed["created_at"], approval, response
        )
        prop = out["transition_application_authorization_request_proposal"]
        self.assertEqual(
            prop["transition_application_authorization_request_status"], "proposed"
        )
        self.assertIs(prop["application_authorization_requested"], False)
        self.assertIs(prop["application_authorization_submitted"], False)
        self.assertIs(prop["authorization_issued"], False)
        self.assertIs(prop["authorization_granted"], False)
        self.assertIs(prop["authorization_active"], False)
        self.assertIs(prop["application_authorized"], False)
        self.assertIs(prop["application_executed"], False)
        self.assertIs(prop["transition_applied"], False)
        self.assertEqual(
            out["transition_application_authorization_eligibility_proposal"][
                "transition_application_authorization_eligibility_status"
            ],
            "eligible",
        )

    def test_f77_not_eligible_cannot_propose(self) -> None:
        signed = _signed()
        approval = _approval(signed["receipt_id"])
        missing = propose_signed_receipt_transition_application_authorization_request(
            signed, [], signed["created_at"], approval, {}
        )["transition_application_authorization_request_proposal"]
        self.assertEqual(
            missing["transition_application_authorization_request_status"],
            "not_proposed",
        )
        self.assertEqual(
            missing["transition_application_authorization_request_reason"],
            "application_authorization_not_eligible",
        )

        denied = propose_signed_receipt_transition_application_authorization_request(
            signed,
            [],
            signed["created_at"],
            approval,
            _response(signed["receipt_id"], approval["approval_id"], decision="denied"),
        )["transition_application_authorization_request_proposal"]
        self.assertEqual(
            denied["transition_application_authorization_request_reason"],
            "application_authorization_not_eligible",
        )

    def test_earlier_foundations_block_proposal(self) -> None:
        signed = _signed()
        approval = _approval(signed["receipt_id"])
        response = _response(signed["receipt_id"], approval["approval_id"])

        no_gov = propose_signed_receipt_transition_application_authorization_request(
            signed, [], signed["created_at"], {}, response
        )["transition_application_authorization_request_proposal"]
        self.assertEqual(
            no_gov["transition_application_authorization_request_reason"],
            "application_authorization_not_eligible",
        )

        rejected_gov = propose_signed_receipt_transition_application_authorization_request(
            signed,
            [],
            signed["created_at"],
            _approval(signed["receipt_id"], approval_decision="rejected"),
            response,
        )["transition_application_authorization_request_proposal"]
        self.assertEqual(
            rejected_gov["transition_application_authorization_request_reason"],
            "application_authorization_not_eligible",
        )

        replayed = propose_signed_receipt_transition_application_authorization_request(
            signed, [signed["receipt_id"]], signed["created_at"], approval, response
        )
        self.assertEqual(replayed["rejection_reason"], "replayed")
        self.assertEqual(
            replayed["transition_application_authorization_request_proposal"][
                "transition_application_authorization_request_reason"
            ],
            "application_authorization_not_eligible",
        )

        t_expired = signed["expires_at"] + RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS + 1
        expired = propose_signed_receipt_transition_application_authorization_request(
            signed, [], t_expired, approval, response
        )
        self.assertEqual(expired["rejection_reason"], "expired")
        self.assertEqual(
            expired["transition_application_authorization_request_proposal"][
                "transition_application_authorization_request_reason"
            ],
            "application_authorization_not_eligible",
        )

        both = propose_signed_receipt_transition_application_authorization_request(
            signed, [signed["receipt_id"]], t_expired, approval, response
        )
        self.assertEqual(both["rejection_reason"], "replayed")
        self.assertEqual(
            both["transition_application_authorization_request_proposal"][
                "transition_application_authorization_request_reason"
            ],
            "application_authorization_not_eligible",
        )

    def test_inconsistent_prerequisites_not_proposed(self) -> None:
        signed = _signed()
        approval = _approval(signed["receipt_id"])
        response = _response(signed["receipt_id"], approval["approval_id"])
        eligible = propose_signed_receipt_transition_application_authorization_eligibility(
            signed, [], signed["created_at"], approval, response
        )

        bad = copy.deepcopy(eligible)
        bad["transition_application_authorization_eligibility_proposal"][
            "authorization_granted"
        ] = True
        prop = transition_application_authorization_request_proposal_from_eligibility(bad)
        self.assertEqual(
            prop["transition_application_authorization_request_status"], "not_proposed"
        )
        self.assertEqual(
            prop["transition_application_authorization_request_reason"],
            "application_authorization_request_inconsistent",
        )

        bad2 = copy.deepcopy(eligible)
        bad2["transition_application_authorization_eligibility_proposal"][
            "receipt_id"
        ] = ""
        prop2 = transition_application_authorization_request_proposal_from_eligibility(
            bad2
        )
        self.assertEqual(
            prop2["transition_application_authorization_request_reason"],
            "receipt_id_missing",
        )

        bad3 = copy.deepcopy(eligible)
        bad3["transition_application_authorization_eligibility_proposal"][
            "transition_kind"
        ] = "other"
        prop3 = transition_application_authorization_request_proposal_from_eligibility(
            bad3
        )
        self.assertEqual(
            prop3["transition_application_authorization_request_reason"],
            "transition_kind_mismatch",
        )

        bad4 = copy.deepcopy(eligible)
        bad4["transition_application_authorization_eligibility_proposal"][
            "approval_id"
        ] = ""
        prop4 = transition_application_authorization_request_proposal_from_eligibility(
            bad4
        )
        self.assertEqual(
            prop4["transition_application_authorization_request_reason"],
            "approval_id_missing",
        )

        bad5 = copy.deepcopy(eligible)
        bad5["transition_application_authorization_eligibility_proposal"][
            "authorization_response_id"
        ] = ""
        prop5 = transition_application_authorization_request_proposal_from_eligibility(
            bad5
        )
        self.assertEqual(
            prop5["transition_application_authorization_request_reason"],
            "authorization_response_id_missing",
        )

        bad6 = copy.deepcopy(eligible)
        bad6["transition_application_authorization_eligibility_proposal"][
            "transition_application_authorization_eligibility_status"
        ] = "not_eligible"
        prop6 = transition_application_authorization_request_proposal_from_eligibility(
            bad6
        )
        self.assertEqual(
            prop6["transition_application_authorization_request_reason"],
            "application_authorization_not_eligible",
        )

    def test_forbidden_caller_fields_rejected(self) -> None:
        signed = _signed()
        approval = _approval(signed["receipt_id"])
        response = _response(signed["receipt_id"], approval["approval_id"])
        for extra in (
            {"transition_application_authorization_request_status": "proposed"},
            {"application_authorization_requested": True},
            {"application_authorization_submitted": True},
            {"authority_id": "gov"},
            {"authorization_token": "t"},
            {"credentials": "c"},
            {"signature": "ab" * 32},
            {"execution_request": True},
            {"submission_request": True},
            {"persist": True},
        ):
            with self.subTest(extra=extra):
                r = _uaii_verify(
                    signed,
                    verification_time=signed["created_at"],
                    governance=approval,
                    response=response,
                    nonce="x" + next(iter(extra)),
                    extra_params=extra,
                )
                self.assertFalse(r["ok"])

    def test_crypto_failure_no_proposal(self) -> None:
        signed = _signed()
        approval = _approval(signed["receipt_id"])
        response = _response(signed["receipt_id"], approval["approval_id"])
        bad = dict(signed)
        bad["signature"] = "ab" * 64
        with self.assertRaises(F64ReceiptSchemaError):
            propose_signed_receipt_transition_application_authorization_request(
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
        self.assertNotIn(
            "transition_application_authorization_request_proposal",
            uaii.get("result") or {},
        )

    def test_reuses_foundation77_path(self) -> None:
        signed = _signed()
        with mock.patch(
            "coin.uaii_signed_receipt.propose_signed_receipt_transition_application_authorization_eligibility",
            wraps=propose_signed_receipt_transition_application_authorization_eligibility,
        ) as wrapped:
            propose_signed_receipt_transition_application_authorization_request(
                signed, [], signed["created_at"], {}, {}
            )
            wrapped.assert_called_once()
        src = inspect.getsource(
            propose_signed_receipt_transition_application_authorization_request
        )
        self.assertIn(
            "propose_signed_receipt_transition_application_authorization_eligibility",
            src,
        )
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
        prop = ok["result"]["transition_application_authorization_request_proposal"]
        self.assertEqual(
            prop["transition_application_authorization_request_status"], "proposed"
        )
        self.assertIs(ok["result"]["application_authorization_requested"], False)
        self.assertIs(ok["result"]["application_authorization_submitted"], False)
        self.assertIs(
            ok["result"]["application_authorization_request_proposed_only"], True
        )
        self.assertIs(ok["result"]["authorization_granted"], False)
        self.assertIs(ok["result"]["authorization_active"], False)
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
        a = propose_signed_receipt_transition_application_authorization_request(
            signed, accepted, signed["created_at"], approval, response
        )
        b = propose_signed_receipt_transition_application_authorization_request(
            signed, accepted, signed["created_at"], approval, {}
        )
        c = propose_signed_receipt_transition_application_authorization_request(
            signed, accepted, signed["created_at"], approval, response
        )
        self.assertEqual(signed, snap_signed)
        self.assertEqual(accepted, snap_accepted)
        self.assertEqual(approval, snap_approval)
        self.assertEqual(response, snap_response)
        self.assertEqual(a, c)
        self.assertEqual(
            b["transition_application_authorization_request_proposal"][
                "transition_application_authorization_request_status"
            ],
            "not_proposed",
        )

        with mock.patch("coin.tx_validation.validate_transaction") as vt, mock.patch(
            "coin.m2m_verifier.canonicalize", create=True
        ) as canon:
            propose_signed_receipt_transition_application_authorization_request(
                signed, [], signed["created_at"], approval, response
            )
            vt.assert_not_called()
            canon.assert_not_called()

        self.assertTrue(receipt.application_authorization_request_proposed_only)
        self.assertFalse(receipt.application_authorization_requested)
        self.assertFalse(receipt.application_authorization_submitted)
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
        self.assertIsNone(re.search(r"\brequests\b", src))
        self.assertNotIn("Ed25519PrivateKey", src)


if __name__ == "__main__":
    unittest.main()
