# SPDX-License-Identifier: Apache-2.0
"""Foundation 73 — governed acceptance-transition application boundary tests."""

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
    APPLICATION_BOUNDARY_RESULT_FIELDS,
    RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS,
    F64ReceiptSchemaError,
    application_boundary_from_proposed_acceptance,
    evaluate_signed_receipt_acceptance_transition_application_boundary,
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
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "signed_receipt": signed,
        "accepted_receipt_ids": [] if accepted is None else accepted,
        "verification_time": verification_time,
        "governance_approval_evidence": {},
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


def _eligible_boundary(receipt_id: str) -> dict[str, Any]:
    return {
        "application_boundary_status": "eligible",
        "application_boundary_reason": "",
        "receipt_id": receipt_id,
        "transition_kind": "add_accepted_receipt_id",
        "application_authorized": False,
        "application_executed": False,
        "state_mutated": False,
        "persistent_state_created": False,
    }


class TestFoundation73ApplicationBoundary(unittest.TestCase):
    def test_eligible_case_inert_flags(self) -> None:
        signed = _signed()
        out = evaluate_signed_receipt_acceptance_transition_application_boundary(
            signed, [], signed["created_at"]
        )
        boundary = out["acceptance_transition_application_boundary"]
        self.assertEqual(boundary, _eligible_boundary(signed["receipt_id"]))
        self.assertEqual(tuple(boundary.keys()), APPLICATION_BOUNDARY_RESULT_FIELDS)
        self.assertIs(boundary["application_authorized"], False)
        self.assertIs(boundary["application_executed"], False)
        self.assertIs(boundary["state_mutated"], False)
        self.assertIs(boundary["persistent_state_created"], False)
        again = evaluate_signed_receipt_acceptance_transition_application_boundary(
            signed, [], signed["created_at"]
        )
        self.assertEqual(boundary, again["acceptance_transition_application_boundary"])

    def test_rejected_paths_ineligible_with_precedence(self) -> None:
        signed = _signed()
        t_expired = signed["expires_at"] + RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS + 1

        replayed = evaluate_signed_receipt_acceptance_transition_application_boundary(
            signed, [signed["receipt_id"]], signed["created_at"]
        )
        self.assertEqual(replayed["rejection_reason"], "replayed")
        self.assertEqual(
            replayed["acceptance_transition_application_boundary"][
                "application_boundary_status"
            ],
            "ineligible",
        )
        self.assertEqual(
            replayed["acceptance_transition_application_boundary"][
                "application_boundary_reason"
            ],
            "replayed",
        )

        expired = evaluate_signed_receipt_acceptance_transition_application_boundary(
            signed, [], t_expired
        )
        self.assertEqual(expired["rejection_reason"], "expired")
        self.assertEqual(
            expired["acceptance_transition_application_boundary"][
                "application_boundary_reason"
            ],
            "expired",
        )

        both = evaluate_signed_receipt_acceptance_transition_application_boundary(
            signed, [signed["receipt_id"]], t_expired
        )
        self.assertEqual(both["rejection_reason"], "replayed")
        self.assertEqual(
            both["acceptance_transition_application_boundary"][
                "application_boundary_reason"
            ],
            "replayed",
        )
        self.assertEqual(
            both["acceptance_transition_application_boundary"]["transition_kind"],
            "",
        )

    def test_never_authorizes_or_executes(self) -> None:
        signed = _signed()
        for accepted, t in (
            ([], signed["created_at"]),
            ([signed["receipt_id"]], signed["created_at"]),
            ([], signed["expires_at"] + RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS + 1),
        ):
            out = evaluate_signed_receipt_acceptance_transition_application_boundary(
                signed, accepted, t
            )
            b = out["acceptance_transition_application_boundary"]
            self.assertIs(b["application_authorized"], False)
            self.assertIs(b["application_executed"], False)
            self.assertNotEqual(b.get("application_authorized"), True)
            self.assertNotEqual(b.get("application_executed"), True)

    def test_non_applicable_cannot_become_eligible(self) -> None:
        signed = _signed()
        proposed = propose_signed_receipt_acceptance_transition(
            signed, [signed["receipt_id"]], signed["created_at"]
        )
        self.assertEqual(
            proposed["acceptance_transition_proposal"]["proposal_status"],
            "not_applicable",
        )
        boundary = application_boundary_from_proposed_acceptance(proposed)
        self.assertEqual(boundary["application_boundary_status"], "ineligible")

        # Tamper an accepted proposal into inconsistent shape → ineligible
        good = propose_signed_receipt_acceptance_transition(
            signed, [], signed["created_at"]
        )
        bad = copy.deepcopy(good)
        bad["acceptance_transition_proposal"]["transition_applied"] = True
        inconsistent = application_boundary_from_proposed_acceptance(bad)
        self.assertEqual(inconsistent["application_boundary_status"], "ineligible")
        self.assertEqual(
            inconsistent["application_boundary_reason"], "proposal_inconsistent"
        )

        bad2 = copy.deepcopy(good)
        bad2["acceptance_transition_proposal"]["proposed_resulting_replay_status"] = (
            "accepted"
        )
        self.assertEqual(
            application_boundary_from_proposed_acceptance(bad2)[
                "application_boundary_reason"
            ],
            "proposal_inconsistent",
        )

    def test_caller_authorization_fields_rejected(self) -> None:
        signed = _signed()
        for extra in (
            {"application_authorized": True},
            {"approved": True},
            {"authorized": True},
            {"authority_id": "gov-1"},
            {"execution_request": True},
            {"application_executed": True},
        ):
            with self.subTest(extra=extra):
                r = _uaii_verify(
                    signed,
                    verification_time=signed["created_at"],
                    nonce="auth" + next(iter(extra)),
                    extra_params=extra,
                )
                self.assertFalse(r["ok"])

    def test_crypto_failure_no_boundary(self) -> None:
        signed = _signed()
        bad = dict(signed)
        bad["signature"] = "ab" * 64
        with self.assertRaises(F64ReceiptSchemaError):
            evaluate_signed_receipt_acceptance_transition_application_boundary(
                bad, [], signed["created_at"]
            )
        uaii = _uaii_verify(bad, verification_time=signed["created_at"], nonce="cfail")
        self.assertFalse(uaii["ok"])
        result = uaii.get("result") or {}
        self.assertNotIn("acceptance_transition_application_boundary", result)
        self.assertNotIn("acceptance_decision", result)

    def test_schema_and_tamper_fail_closed(self) -> None:
        signed = _signed()
        t = signed["created_at"]
        bad = dict(signed)
        bad["signed_payload_digest"] = "0" * 64
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            evaluate_signed_receipt_acceptance_transition_application_boundary(
                bad, [], t
            )
        self.assertEqual(ctx.exception.code, "digest_mismatch")

        for bad_accepted in (None, True, "x", [None], [signed["receipt_id"]] * 2):
            with self.subTest(a=bad_accepted):
                with self.assertRaises(F64ReceiptSchemaError):
                    evaluate_signed_receipt_acceptance_transition_application_boundary(
                        signed, bad_accepted, t
                    )
        for bad_time in (None, True, 1.5, "1", -1):
            with self.subTest(vt=bad_time):
                with self.assertRaises(F64ReceiptSchemaError):
                    evaluate_signed_receipt_acceptance_transition_application_boundary(
                        signed, [], bad_time
                    )

        with self.assertRaises(F64ReceiptSchemaError):
            application_boundary_from_proposed_acceptance(
                {"acceptance_decision": "accepted"}
            )

    def test_reuses_foundation72_path(self) -> None:
        signed = _signed()
        with mock.patch(
            "coin.uaii_signed_receipt.propose_signed_receipt_acceptance_transition",
            wraps=propose_signed_receipt_acceptance_transition,
        ) as wrapped:
            evaluate_signed_receipt_acceptance_transition_application_boundary(
                signed, [], signed["created_at"]
            )
            wrapped.assert_called_once()
        src = inspect.getsource(
            evaluate_signed_receipt_acceptance_transition_application_boundary
        )
        self.assertIn("propose_signed_receipt_acceptance_transition", src)
        self.assertIn("application_boundary_from_proposed_acceptance", src)
        self.assertNotIn("verify_signed_receipt_facts", src)
        self.assertNotIn("Ed25519PublicKey", src)

    def test_uaii_integration_capabilities_unchanged(self) -> None:
        signed = _signed()
        ok = _uaii_verify(signed, verification_time=signed["created_at"], nonce="ok")
        self.assertTrue(ok["ok"])
        self.assertEqual(
            ok["result"]["acceptance_transition_application_boundary"],
            _eligible_boundary(signed["receipt_id"]),
        )
        self.assertIs(ok["result"]["application_authorized"], False)
        self.assertIs(ok["result"]["application_executed"], False)
        self.assertIs(ok["result"]["boundary_evaluated_only"], True)

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
        self.assertFalse(
            process_uaii_request(
                json.dumps(unknown, separators=(",", ":"), ensure_ascii=False).encode(
                    "utf-8"
                ),
                _context(),
            )["ok"]
        )

    def test_inputs_stateless_no_side_effects(self) -> None:
        signed = _signed()
        accepted = [signed["receipt_id"]]
        snap_signed = copy.deepcopy(signed)
        snap_accepted = list(accepted)
        a = evaluate_signed_receipt_acceptance_transition_application_boundary(
            signed, accepted, signed["created_at"]
        )
        b = evaluate_signed_receipt_acceptance_transition_application_boundary(
            signed, [], signed["created_at"]
        )
        c = evaluate_signed_receipt_acceptance_transition_application_boundary(
            signed, accepted, signed["created_at"]
        )
        self.assertEqual(signed, snap_signed)
        self.assertEqual(accepted, snap_accepted)
        self.assertEqual(a, c)
        self.assertEqual(
            b["acceptance_transition_application_boundary"][
                "application_boundary_status"
            ],
            "eligible",
        )

        with mock.patch("coin.tx_validation.validate_transaction") as vt, mock.patch(
            "coin.m2m_verifier.canonicalize", create=True
        ) as canon:
            evaluate_signed_receipt_acceptance_transition_application_boundary(
                signed, [], signed["created_at"]
            )
            vt.assert_not_called()
            canon.assert_not_called()

        self.assertTrue(receipt.boundary_evaluated_only)
        self.assertFalse(receipt.application_authorized)
        self.assertFalse(receipt.application_executed)
        self.assertFalse(receipt.transition_applied)
        self.assertFalse(receipt.acceptance_state_mutated)
        self.assertFalse(receipt.accepted_receipt_ids_mutated)
        self.assertFalse(receipt.receipt_recorded)
        self.assertFalse(receipt.persistent_state_created)
        self.assertFalse(receipt.state_mutated)
        self.assertFalse(receipt.system_clock_read)
        self.assertFalse(receipt.implicit_time_used)
        self.assertFalse(receipt.signing_authorized)
        self.assertFalse(receipt.spend_authorized)
        self.assertFalse(receipt.settlement_authorized)
        self.assertFalse(receipt.transaction_submission_authorized)
        self.assertFalse(receipt.ledger_mutated)
        self.assertFalse(receipt.adapters_activated)
        self.assertFalse(receipt.runtime_activated)
        self.assertEqual(tx_validation.L28_MAX_SUPPLY, 28_000_000)
        src = Path(receipt.__file__).read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\bdatetime\.(now|utcnow)\b", src))
        self.assertNotIn("Ed25519PrivateKey", src)


if __name__ == "__main__":
    unittest.main()
