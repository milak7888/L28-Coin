# SPDX-License-Identifier: Apache-2.0
"""Isolated Agent Purchase Demo v0.1 tests — disposable in-memory keys only."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import re
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import tx_validation
from coin.isolated_agent_purchase_demo import (
    APPROVAL_FIELDS,
    DEMO_PROFILE,
    RESULT_FIELDS,
    SERVICE_ID,
    DemoError,
    main,
    run_isolated_agent_purchase_demo,
    verify_isolated_agent_purchase_demo_result,
)
from coin.uaii_json import canon_uaii
from coin.uaii_signed_receipt import public_key_id_for_raw


def _disposable() -> tuple[Ed25519PrivateKey, str]:
    key = Ed25519PrivateKey.generate()
    return key, key.public_key().public_bytes_raw().hex()


def _run_with_keys(
    *,
    request_input: Any = "fixed-demo-input",
    buyer: Ed25519PrivateKey | None = None,
    seller: Ed25519PrivateKey | None = None,
) -> dict[str, Any]:
    buyer_key = buyer or Ed25519PrivateKey.generate()
    seller_key = seller or Ed25519PrivateKey.generate()
    return run_isolated_agent_purchase_demo(
        request_input=request_input,
        buyer_signer=buyer_key.sign,
        seller_signer=seller_key.sign,
        buyer_public_key_hex=buyer_key.public_key().public_bytes_raw().hex(),
        seller_public_key_hex=seller_key.public_key().public_bytes_raw().hex(),
    )


class TestIsolatedAgentPurchaseDemo(unittest.TestCase):
    def test_happy_path_verifies(self) -> None:
        result = _run_with_keys()
        self.assertEqual(tuple(result.keys()), RESULT_FIELDS)
        self.assertTrue(result["demo_completed"])
        self.assertTrue(result["service_output_verified"])
        self.assertTrue(result["receipt_signature_verified"])
        self.assertTrue(result["simulation_only"])
        self.assertFalse(result["real_payment_executed"])
        self.assertFalse(result["settlement_finalized"])
        self.assertFalse(result["transaction_submitted"])
        self.assertFalse(result["ledger_mutated"])
        self.assertFalse(result["persistent_state_created"])
        self.assertFalse(result["public_network_used"])
        self.assertEqual(result["service_id"], SERVICE_ID)
        check = verify_isolated_agent_purchase_demo_result(result)
        self.assertTrue(check["ok"])

    def test_output_independently_recomputable(self) -> None:
        result = _run_with_keys(request_input="recompute-me")
        expected = hashlib.sha256(canon_uaii(result["request"]["input"])).hexdigest()
        self.assertEqual(result["output_digest"], expected)
        self.assertEqual(result["delivery"]["output"], expected)

    def test_receipt_uses_public_material_only(self) -> None:
        result = _run_with_keys()
        receipt = result["signed_receipt"]
        self.assertEqual(receipt["signer_public_key"], result["seller_public_key"])
        self.assertEqual(
            receipt["signer_public_key_id"],
            public_key_id_for_raw(bytes.fromhex(result["seller_public_key"])),
        )
        blob = json.dumps(result)
        self.assertNotIn("private_key", blob)
        self.assertNotIn("secret_key", blob)
        self.assertNotIn("seed_phrase", blob)

    def test_tamper_fail_closed(self) -> None:
        result = _run_with_keys()
        cases: list[tuple[str, Any]] = [
            ("request", {**result["request"], "input": {"text": "tampered"}}),
            ("quote", {**result["quote"], "amount": 999}),
            ("quote_id", "ab" * 32),
            ("buyer_public_identity", "wrong-buyer"),
            ("seller_public_identity", "wrong-seller"),
            ("service_id", "other.service"),
            ("simulated_approval", {**result["simulated_approval"], "simulation_only": False}),
            ("delivery", {**result["delivery"], "output": "00" * 32}),
            ("output_digest", "11" * 32),
            ("quote_signature", "ab" * 64),
            ("signed_receipt", {**result["signed_receipt"], "signature": "cd" * 64}),
        ]
        for key, value in cases:
            with self.subTest(key=key):
                bad = copy.deepcopy(result)
                bad[key] = value
                with self.assertRaises(DemoError):
                    verify_isolated_agent_purchase_demo_result(bad)

    def test_cross_run_artifacts_cannot_mix(self) -> None:
        a = _run_with_keys(request_input="run-a")
        b = _run_with_keys(request_input="run-b")
        mixed = copy.deepcopy(a)
        mixed["delivery"] = b["delivery"]
        mixed["delivery_signature"] = b["delivery_signature"]
        mixed["output_digest"] = b["output_digest"]
        with self.assertRaises(DemoError):
            verify_isolated_agent_purchase_demo_result(mixed)

    def test_wrong_buyer_or_seller_key_fails(self) -> None:
        buyer, buyer_hex = _disposable()
        seller, seller_hex = _disposable()
        other, other_hex = _disposable()
        with self.assertRaises(DemoError):
            run_isolated_agent_purchase_demo(
                request_input="x",
                buyer_signer=buyer.sign,
                seller_signer=seller.sign,
                buyer_public_key_hex=other_hex,
                seller_public_key_hex=seller_hex,
            )
        with self.assertRaises(DemoError):
            run_isolated_agent_purchase_demo(
                request_input="x",
                buyer_signer=buyer.sign,
                seller_signer=seller.sign,
                buyer_public_key_hex=buyer_hex,
                seller_public_key_hex=other_hex,
            )

    def test_malformed_inputs_fail_closed(self) -> None:
        for bad in (None, True, "", [], {}):
            with self.subTest(bad=bad):
                with self.assertRaises(DemoError):
                    run_isolated_agent_purchase_demo(request_input=bad)
        with self.assertRaises(DemoError):
            run_isolated_agent_purchase_demo(
                request_input="x",
                buyer_signer=lambda _b: b"\x00" * 64,
                seller_signer=None,
                buyer_public_key_hex="ab" * 32,
                seller_public_key_hex=None,
            )

    def test_deterministic_with_injected_keys(self) -> None:
        buyer, _ = _disposable()
        seller, _ = _disposable()
        a = _run_with_keys(request_input="same", buyer=buyer, seller=seller)
        b = _run_with_keys(request_input="same", buyer=buyer, seller=seller)
        self.assertEqual(a, b)

    def test_caller_inputs_unmodified(self) -> None:
        payload = {"text": "immutable-check", "n": 1}
        snap = copy.deepcopy(payload)
        accepted = ["keep"]
        snap_accepted = list(accepted)
        run_isolated_agent_purchase_demo(request_input=payload)
        self.assertEqual(payload, snap)
        self.assertEqual(accepted, snap_accepted)

    def test_no_private_material_in_cli_output(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["--input", "cli-demo"])
        self.assertEqual(code, 0)
        out = stdout.getvalue()
        err = stderr.getvalue()
        self.assertNotRegex(out + err, r"private_key|secret_key|seed_phrase|BEGIN PRIVATE")
        summary = json.loads(out)
        self.assertTrue(summary["demo_completed"])
        self.assertTrue(summary["simulation_only"])
        self.assertNotIn("signed_receipt", summary)

    def test_no_side_effects(self) -> None:
        with mock.patch("coin.tx_validation.validate_transaction") as vt, mock.patch(
            "coin.uaii_reference_core.process_uaii_request"
        ) as proc:
            result = _run_with_keys()
            vt.assert_not_called()
            proc.assert_not_called()
        self.assertFalse(result["ledger_mutated"])
        self.assertEqual(tx_validation.L28_MAX_SUPPLY, 28_000_000)
        src = Path(run_isolated_agent_purchase_demo.__code__.co_filename).read_text(
            encoding="utf-8"
        )
        self.assertIsNone(re.search(r"\bdatetime\.(now|utcnow)\b", src))
        self.assertIsNone(re.search(r"\bsocket\b", src))
        self.assertIsNone(re.search(r"\burllib\b", src))
        self.assertNotIn("private_bytes", src)

    def test_approval_never_claims_payment(self) -> None:
        result = _run_with_keys()
        approval = result["simulated_approval"]
        self.assertEqual(tuple(approval.keys()), APPROVAL_FIELDS)
        self.assertIs(approval["simulation_only"], True)
        self.assertIs(approval["real_payment_executed"], False)
        self.assertIs(approval["spend_authorized"], False)
        self.assertIs(result["quote"]["spend_authorized"], False)
        self.assertEqual(result["demo_profile"], DEMO_PROFILE)


if __name__ == "__main__":
    unittest.main()
