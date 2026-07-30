# SPDX-License-Identifier: Apache-2.0
"""Foundation 71 — signed-receipt acceptance decision composition tests."""

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
    F64ReceiptSchemaError,
    acceptance_decision_from_classifications,
    classify_signed_receipt_replay_and_expiration,
    decide_signed_receipt_acceptance,
    public_key_id_for_raw,
    required_signer_identity,
    sign_unsigned_receipt_facts,
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


class TestFoundation71AcceptanceDecision(unittest.TestCase):
    def test_decision_matrix_four_cases(self) -> None:
        signed = _signed()
        t_valid = signed["created_at"]
        t_expired = signed["expires_at"] + RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS + 1

        accepted = decide_signed_receipt_acceptance(signed, [], t_valid)
        self.assertEqual(accepted["replay_status"], "fresh")
        self.assertEqual(accepted["expiration_status"], "valid")
        self.assertEqual(accepted["acceptance_decision"], "accepted")
        self.assertEqual(accepted["rejection_reason"], "")

        replayed = decide_signed_receipt_acceptance(
            signed, [signed["receipt_id"]], t_valid
        )
        self.assertEqual(replayed["replay_status"], "replayed")
        self.assertEqual(replayed["expiration_status"], "valid")
        self.assertEqual(replayed["acceptance_decision"], "rejected")
        self.assertEqual(replayed["rejection_reason"], "replayed")

        expired = decide_signed_receipt_acceptance(signed, [], t_expired)
        self.assertEqual(expired["replay_status"], "fresh")
        self.assertEqual(expired["expiration_status"], "expired")
        self.assertEqual(expired["acceptance_decision"], "rejected")
        self.assertEqual(expired["rejection_reason"], "expired")

        both = decide_signed_receipt_acceptance(
            signed, [signed["receipt_id"]], t_expired
        )
        self.assertEqual(both["replay_status"], "replayed")
        self.assertEqual(both["expiration_status"], "expired")
        self.assertEqual(both["acceptance_decision"], "rejected")
        self.assertEqual(both["rejection_reason"], "replayed")

    def test_replayed_and_expired_precedence(self) -> None:
        decision, reason = acceptance_decision_from_classifications(
            replay_status="replayed",
            expiration_status="expired",
        )
        self.assertEqual(decision, "rejected")
        self.assertEqual(reason, "replayed")
        src = inspect.getsource(acceptance_decision_from_classifications)
        replay_check = src.index('replay_status == "replayed"')
        expired_check = src.index('expiration_status == "expired"')
        self.assertLess(replay_check, expired_check)

    def test_crypto_failure_emits_no_acceptance_decision(self) -> None:
        signed = _signed()
        bad = dict(signed)
        bad["signature"] = "ab" * 64
        with self.assertRaises(F64ReceiptSchemaError) as ctx:
            decide_signed_receipt_acceptance(bad, [], signed["created_at"])
        self.assertEqual(ctx.exception.code, "signature_invalid")

        bad_digest = dict(signed)
        bad_digest["signed_payload_digest"] = "0" * 64
        with self.assertRaises(F64ReceiptSchemaError) as ctx2:
            decide_signed_receipt_acceptance(bad_digest, [], signed["created_at"])
        self.assertEqual(ctx2.exception.code, "digest_mismatch")

        bad_id = dict(signed)
        bad_id["receipt_id"] = "1" * 64
        with self.assertRaises(F64ReceiptSchemaError) as ctx3:
            decide_signed_receipt_acceptance(bad_id, [], signed["created_at"])
        self.assertEqual(ctx3.exception.code, "receipt_id_invalid")

        uaii = _uaii_verify(bad, verification_time=signed["created_at"], nonce="fail")
        self.assertFalse(uaii["ok"])
        self.assertNotIn("acceptance_decision", uaii.get("result") or {})
        self.assertNotIn("rejection_reason", uaii.get("result") or {})

    def test_reuses_f67_f69_f70_composition(self) -> None:
        signed = _signed()
        with mock.patch(
            "coin.uaii_signed_receipt.classify_signed_receipt_replay_and_expiration",
            wraps=classify_signed_receipt_replay_and_expiration,
        ) as wrapped_compose, mock.patch(
            "coin.uaii_signed_receipt.verify_signed_receipt_facts",
            wraps=verify_signed_receipt_facts,
        ) as wrapped_verify:
            decide_signed_receipt_acceptance(signed, [], signed["created_at"])
            wrapped_compose.assert_called_once()
            wrapped_verify.assert_called_once()

        src = inspect.getsource(decide_signed_receipt_acceptance)
        self.assertIn("classify_signed_receipt_replay_and_expiration", src)
        self.assertIn("acceptance_decision_from_classifications", src)
        self.assertNotIn("Ed25519PublicKey", src)
        self.assertNotIn("signature_invalid", src)

    def test_status_fields_unchanged(self) -> None:
        signed = _signed()
        classified = classify_signed_receipt_replay_and_expiration(
            signed, [signed["receipt_id"]], signed["expires_at"] + 301
        )
        decided = decide_signed_receipt_acceptance(
            signed, [signed["receipt_id"]], signed["expires_at"] + 301
        )
        self.assertEqual(decided["replay_status"], classified["replay_status"])
        self.assertEqual(decided["expiration_status"], classified["expiration_status"])
        self.assertEqual(decided["replay_status"], "replayed")
        self.assertEqual(decided["expiration_status"], "expired")

    def test_fail_closed_context_and_request(self) -> None:
        signed = _signed()
        t = signed["created_at"]
        for bad_accepted in (
            None,
            "not-a-list",
            [None],
            [True],
            ["nothex"],
            [signed["receipt_id"], signed["receipt_id"]],
            {signed["receipt_id"]},
        ):
            with self.subTest(accepted=bad_accepted):
                with self.assertRaises(F64ReceiptSchemaError):
                    decide_signed_receipt_acceptance(signed, bad_accepted, t)

        for bad_time in (None, True, 1.5, "1700000000", -1):
            with self.subTest(t=bad_time):
                with self.assertRaises(F64ReceiptSchemaError):
                    decide_signed_receipt_acceptance(signed, [], bad_time)

        # Ambiguous / unexpected UAII params fail closed (wrong key order / extras)
        env = {
            "interface_profile": INTERFACE_PROFILE,
            "operation": "verify_signed_receipt",
            "request_id": _hex64("badparams"),
            "created_at": 1_699_999_000,
            "expires_at": 1_700_000_100,
            "nonce": "badp",
            "execution_authorized": False,
            "params": {
                "signed_receipt": signed,
                "verification_time": t,
                "accepted_receipt_ids": [],
            },
        }
        raw = json.dumps(env, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        r = process_uaii_request(raw, _context())
        self.assertFalse(r["ok"])

        env2 = dict(env)
        env2["params"] = {
            "signed_receipt": signed,
            "accepted_receipt_ids": [],
            "verification_time": t,
            "extra": 1,
        }
        env2["nonce"] = "badx"
        env2["request_id"] = _hex64("badextra")
        raw2 = json.dumps(env2, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        r2 = process_uaii_request(raw2, _context())
        self.assertFalse(r2["ok"])

    def test_uaii_result_contract_and_capabilities_unchanged(self) -> None:
        signed = _signed()
        r = _uaii_verify(signed, verification_time=signed["created_at"], nonce="ok")
        self.assertTrue(r["ok"])
        self.assertEqual(r["code"], "signed_receipt_verified")
        result = r["result"]
        self.assertEqual(result["acceptance_decision"], "accepted")
        self.assertEqual(result["rejection_reason"], "")
        self.assertEqual(
            tuple(result.keys())[:6],
            (
                "verification_status",
                "replay_status",
                "expiration_status",
                "acceptance_decision",
                "rejection_reason",
                "acceptance_transition_proposal",
            ),
        )

        both = _uaii_verify(
            signed,
            accepted=[signed["receipt_id"]],
            verification_time=signed["expires_at"] + RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS + 1,
            nonce="both",
        )
        self.assertTrue(both["ok"])
        self.assertEqual(both["result"]["acceptance_decision"], "rejected")
        self.assertEqual(both["result"]["rejection_reason"], "replayed")

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
        draw = json.dumps(disc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        d = process_uaii_request(draw, _context())
        self.assertTrue(d["ok"])
        self.assertEqual(d["result"]["operations"], list(OPERATIONS))

        unknown = {
            "interface_profile": INTERFACE_PROFILE,
            "operation": "not_a_real_operation",
            "request_id": _hex64("unk"),
            "created_at": 1_699_999_000,
            "expires_at": 1_700_000_100,
            "nonce": "unk",
            "execution_authorized": False,
            "params": {},
        }
        uraw = json.dumps(unknown, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        u = process_uaii_request(uraw, _context())
        self.assertFalse(u["ok"])
        self.assertIn("get_payment_receipt", d["result"]["operations"])

    def test_inputs_not_mutated_and_stateless(self) -> None:
        signed = _signed()
        accepted_ids = [signed["receipt_id"]]
        snapshot_signed = copy.deepcopy(signed)
        snapshot_ids = list(accepted_ids)
        a = decide_signed_receipt_acceptance(signed, accepted_ids, signed["created_at"])
        b = decide_signed_receipt_acceptance(signed, [], signed["created_at"])
        c = decide_signed_receipt_acceptance(signed, accepted_ids, signed["created_at"])
        self.assertEqual(signed, snapshot_signed)
        self.assertEqual(accepted_ids, snapshot_ids)
        self.assertEqual(a["acceptance_decision"], "rejected")
        self.assertEqual(b["acceptance_decision"], "accepted")
        self.assertEqual(c["acceptance_decision"], "rejected")
        self.assertEqual(a, c)

    def test_no_side_effects_or_forbidden_apis(self) -> None:
        signed = _signed()
        with mock.patch("coin.tx_validation.validate_transaction") as vt, mock.patch(
            "coin.m2m_verifier.canonicalize", create=True
        ) as canon:
            decide_signed_receipt_acceptance(signed, [], signed["created_at"])
            _uaii_verify(signed, verification_time=signed["created_at"], nonce="sx")
            vt.assert_not_called()
            canon.assert_not_called()
        self.assertFalse(receipt.acceptance_state_mutated)
        self.assertFalse(receipt.receipt_recorded)
        self.assertFalse(receipt.system_clock_read)
        self.assertFalse(receipt.implicit_time_used)
        self.assertFalse(receipt.persistent_replay_storage_created)
        self.assertFalse(receipt.persistent_expiration_state_created)
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
        self.assertIsNone(re.search(r"\bdate\.today\b", src))
        # Production acceptance path must not import private-key types
        self.assertNotIn("Ed25519PrivateKey", src)


if __name__ == "__main__":
    unittest.main()
