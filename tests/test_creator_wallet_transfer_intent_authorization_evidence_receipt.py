from __future__ import annotations

import ast
import copy
import hashlib
import json
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import creator_wallet_transfer_intent as intent
from coin import creator_wallet_transfer_intent_authorization as authorization
from coin import creator_wallet_transfer_intent_authorization_evidence as evidence
from coin import creator_wallet_transfer_intent_authorization_evidence_receipt as receipt

BUNDLE_SHA256 = "a" * 64
BUNDLE_AGGREGATE = "b" * 64


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")


def _build_authorization() -> tuple[dict[str, object], str, str]:
    private_key = Ed25519PrivateKey.generate()
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    public_key = public_bytes.hex()
    address = "L28" + hashlib.sha256(public_bytes).hexdigest()[:40]
    intent_value: dict[str, object] = {
        "intent_version": intent.INTENT_VERSION,
        "domain": intent.INTENT_DOMAIN,
        "creator_address": address,
        "recipient_address": "L28" + "1" * 40,
        "amount": 28,
        "nonce": "2" * 64,
        "expires_at_unix": 2_000_000_000,
        "control_bundle_sha256": BUNDLE_SHA256,
        "control_bundle_aggregate_commitment": BUNDLE_AGGREGATE,
    }
    intent_value["intent_id"] = hashlib.sha256(
        intent.INTENT_ID_DOMAIN + _canonical(intent_value)
    ).hexdigest()
    value: dict[str, object] = {
        "authorization_version": authorization.AUTHORIZATION_VERSION,
        "domain": authorization.AUTHORIZATION_DOMAIN,
        "intent": intent_value,
        "intent_sha256": hashlib.sha256(_canonical(intent_value)).hexdigest(),
        "intent_id": intent_value["intent_id"],
        "creator_address": address,
        "creator_public_key": public_key,
    }
    payload = {name: value[name] for name in authorization.SIGNATURE_PAYLOAD_FIELDS}
    value["signature"] = private_key.sign(_canonical(payload)).hex()
    value["authorization_id"] = hashlib.sha256(
        authorization.AUTHORIZATION_ID_DOMAIN + _canonical(value)
    ).hexdigest()
    return value, public_key, address


def _patch_identity(public_key: str, address: str):
    return mock.patch.multiple(
        authorization,
        FIXED_CREATOR_PUBLIC_KEY=public_key,
        FIXED_CREATOR_ADDRESS=address,
    ), mock.patch.object(intent, "FIXED_CREATOR_ADDRESS", address)


def _valid_evidence() -> tuple[dict[str, object], str, str]:
    authorization_value, public_key, address = _build_authorization()
    auth_patch, intent_patch = _patch_identity(public_key, address)
    with auth_patch, intent_patch:
        result = authorization.verify_creator_wallet_transfer_intent_authorization_json(
            _json_bytes(authorization_value),
            expected_control_bundle_sha256=BUNDLE_SHA256,
            expected_control_bundle_aggregate_commitment=BUNDLE_AGGREGATE,
        )
    assert result.ok, result.code
    report = evidence._build_expected_authorization_report(result)
    evidence_value = {
        "evidence_version": evidence.EVIDENCE_VERSION,
        "expected_control_bundle_sha256": BUNDLE_SHA256,
        "expected_control_bundle_aggregate_commitment": BUNDLE_AGGREGATE,
        "authorization": authorization_value,
        "report": report,
    }
    return evidence_value, public_key, address


def _valid_receipt() -> tuple[dict[str, object], str, str]:
    evidence_value, public_key, address = _valid_evidence()
    auth_patch, intent_patch = _patch_identity(public_key, address)
    with auth_patch, intent_patch:
        result = evidence.verify_creator_wallet_transfer_intent_authorization_evidence_json(
            _json_bytes(evidence_value)
        )
    assert result.ok, result.code
    value: dict[str, object] = {
        "receipt_version": receipt.RECEIPT_VERSION,
        "expected_control_bundle_sha256": BUNDLE_SHA256,
        "expected_control_bundle_aggregate_commitment": BUNDLE_AGGREGATE,
        "evidence": evidence_value,
        "evidence_sha256": result.evidence_sha256,
        "authorization_report_id": evidence_value["report"]["report_id"],
        "authorization_sha256": result.authorization_sha256,
        "authorization_id": result.authorization_id,
        "checks": list(result.checks),
        "execution_authorized": False,
    }
    value["receipt_id"] = receipt._receipt_id(value)
    return value, public_key, address


def _verify(value: object, public_key: str | None = None, address: str | None = None):
    if isinstance(value, dict):
        evidence_value = value.get("evidence")
        if isinstance(evidence_value, dict):
            authorization_value = evidence_value.get("authorization")
            if isinstance(authorization_value, dict):
                public_key = public_key or str(authorization_value["creator_public_key"])
                address = address or str(authorization_value["creator_address"])
        raw: str | bytes = _json_bytes(value)
    else:
        raw = value  # type: ignore[assignment]
        public_key = public_key or "0" * 64
        address = address or ("L28" + "0" * 40)
    auth_patch, intent_patch = _patch_identity(public_key, address)
    with auth_patch, intent_patch:
        return receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
            raw
        )


class CreatorWalletTransferIntentAuthorizationEvidenceReceiptTests(unittest.TestCase):
    def test_valid_receipt_binds_f31_f33_f34(self) -> None:
        value, _, _ = _valid_receipt()
        result = _verify(value)
        self.assertTrue(result.ok, result.code)
        self.assertEqual(result.code, "ok")
        self.assertEqual(result.checks, receipt.SUCCESS_CHECKS)
        self.assertEqual(result.receipt_id, value["receipt_id"])
        self.assertEqual(result.evidence_sha256, value["evidence_sha256"])
        self.assertEqual(result.authorization_report_id, value["authorization_report_id"])
        self.assertEqual(result.authorization_sha256, value["authorization_sha256"])
        self.assertEqual(result.authorization_id, value["authorization_id"])
        self.assertIs(value["execution_authorized"], False)

    def test_independently_invokes_foundation_34_verifier(self) -> None:
        value, public_key, address = _valid_receipt()
        auth_patch, intent_patch = _patch_identity(public_key, address)
        with auth_patch, intent_patch, mock.patch.object(
            receipt,
            "verify_creator_wallet_transfer_intent_authorization_evidence_json",
            wraps=evidence.verify_creator_wallet_transfer_intent_authorization_evidence_json,
        ) as wrapped:
            result = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                _json_bytes(value)
            )
        self.assertTrue(result.ok, result.code)
        wrapped.assert_called_once()
        self.assertEqual(json.loads(wrapped.call_args.args[0]), value["evidence"])

    def test_top_level_schema_and_order_are_exact(self) -> None:
        value, _, _ = _valid_receipt()
        missing = dict(value)
        missing.pop("checks")
        self.assertEqual(_verify(missing).code, "schema_invalid")
        extra = dict(value)
        extra["extra"] = False
        self.assertEqual(_verify(extra).code, "schema_invalid")
        bad_version = dict(value)
        bad_version["receipt_version"] = "other"
        self.assertEqual(_verify(bad_version).code, "schema_invalid")
        reordered = {
            "expected_control_bundle_sha256": value["expected_control_bundle_sha256"],
            "receipt_version": value["receipt_version"],
            "expected_control_bundle_aggregate_commitment": value[
                "expected_control_bundle_aggregate_commitment"
            ],
            "evidence": value["evidence"],
            "evidence_sha256": value["evidence_sha256"],
            "authorization_report_id": value["authorization_report_id"],
            "authorization_sha256": value["authorization_sha256"],
            "authorization_id": value["authorization_id"],
            "checks": value["checks"],
            "execution_authorized": value["execution_authorized"],
            "receipt_id": value["receipt_id"],
        }
        self.assertEqual(_verify(reordered).code, "schema_invalid")

    def test_expected_commitments_and_mismatch(self) -> None:
        value, _, _ = _valid_receipt()
        bad = dict(value)
        bad["expected_control_bundle_sha256"] = "A" * 64
        self.assertEqual(_verify(bad).code, "invalid_expected_commitment")
        mismatch = copy.deepcopy(value)
        mismatch["expected_control_bundle_sha256"] = "c" * 64
        mismatch["receipt_id"] = receipt._receipt_id(mismatch)
        self.assertEqual(_verify(mismatch).code, "commitment_mismatch")

    def test_execution_authorized_must_be_false(self) -> None:
        value, _, _ = _valid_receipt()
        value["execution_authorized"] = True
        value["receipt_id"] = receipt._receipt_id(value)
        self.assertEqual(_verify(value).code, "schema_invalid")

    def test_invalid_evidence_is_rejected(self) -> None:
        value, _, _ = _valid_receipt()
        value["evidence"]["authorization"]["signature"] = "0" * 128
        value["receipt_id"] = receipt._receipt_id(value)
        self.assertEqual(_verify(value).code, "evidence_invalid")
        bad_type = dict(value)
        bad_type["evidence"] = []
        self.assertEqual(_verify(bad_type).code, "evidence_invalid")

    def test_authorization_report_and_evidence_hash_binding(self) -> None:
        value, _, _ = _valid_receipt()
        bad_report = copy.deepcopy(value)
        bad_report["authorization_report_id"] = "0" * 64
        bad_report["receipt_id"] = receipt._receipt_id(bad_report)
        self.assertEqual(_verify(bad_report).code, "authorization_report_invalid")
        bad_hash = copy.deepcopy(value)
        bad_hash["evidence_sha256"] = "0" * 64
        bad_hash["receipt_id"] = receipt._receipt_id(bad_hash)
        self.assertEqual(_verify(bad_hash).code, "evidence_commitment_invalid")
        bad_auth = copy.deepcopy(value)
        bad_auth["authorization_id"] = "0" * 64
        bad_auth["receipt_id"] = receipt._receipt_id(bad_auth)
        self.assertEqual(_verify(bad_auth).code, "evidence_commitment_invalid")

    def test_checks_and_receipt_id_binding(self) -> None:
        value, _, _ = _valid_receipt()
        bad_checks = copy.deepcopy(value)
        bad_checks["checks"] = ["schema_exact"]
        bad_checks["receipt_id"] = receipt._receipt_id(bad_checks)
        self.assertEqual(_verify(bad_checks).code, "checks_invalid")
        bad_id = copy.deepcopy(value)
        bad_id["receipt_id"] = "0" * 64
        self.assertEqual(_verify(bad_id).code, "receipt_id_invalid")

    def test_invalid_inputs_fail_closed(self) -> None:
        cases = (
            (object(), "input_type_invalid"),
            (b"x" * (receipt.MAX_RECEIPT_BYTES + 1), "input_too_large"),
            (bytes([255]), "encoding_invalid"),
            ("{", "json_invalid"),
            ("[]", "invalid_top_level"),
            ('{"x":NaN}', "json_invalid"),
            ('{"a":1,"a":2}', "duplicate_key"),
        )
        for payload, code in cases:
            with self.subTest(code=code):
                result = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                    payload  # type: ignore[arg-type]
                )
                self.assertEqual(result.code, code)

    def test_nested_duplicate_key_fails(self) -> None:
        value, public_key, address = _valid_receipt()
        raw = _json_bytes(value).decode("utf-8").replace(
            '"amount":28', '"amount":28,"amount":28', 1
        )
        self.assertEqual(_verify(raw, public_key, address).code, "duplicate_key")

    def test_results_are_frozen_and_input_unmodified(self) -> None:
        value, _, _ = _valid_receipt()
        before = copy.deepcopy(value)
        result = _verify(value)
        self.assertEqual(value, before)
        with self.assertRaises(FrozenInstanceError):
            result.code = "changed"  # type: ignore[misc]

    def test_formatting_is_deterministic(self) -> None:
        value, public_key, address = _valid_receipt()
        compact = json.dumps(value, separators=(",", ":"))
        pretty = json.dumps(value, indent=2)
        auth_patch, intent_patch = _patch_identity(public_key, address)
        with auth_patch, intent_patch:
            one = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                compact
            )
            two = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                pretty
            )
        self.assertTrue(one.ok and two.ok)
        self.assertEqual(one, two)

    def test_wrapper_and_internal_error(self) -> None:
        value, public_key, address = _valid_receipt()
        auth_patch, intent_patch = _patch_identity(public_key, address)
        with auth_patch, intent_patch:
            direct = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                _json_bytes(value)
            )
            wrapped = receipt.CreatorWalletTransferIntentAuthorizationEvidenceReceiptVerifier.verify_json(
                _json_bytes(value)
            )
        self.assertEqual(direct, wrapped)
        with mock.patch.object(receipt, "_parse", side_effect=RuntimeError("secret")):
            failed = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                "{}"
            )
        self.assertEqual(failed.code, "internal_error")
        self.assertNotIn("secret", failed.code)

    def test_production_core_has_no_io_wallet_or_network(self) -> None:
        path = Path(receipt.__file__)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports |= {
            (node.module or "").split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        self.assertFalse(
            imports
            & {
                "os",
                "pathlib",
                "socket",
                "subprocess",
                "requests",
                "urllib",
                "http",
                "asyncio",
                "wallet",
                "ledger",
                "mining",
            }
        )
        self.assertNotIn("Ed25519PrivateKey", source)
        self.assertNotIn("load_wallet", source)
        self.assertNotIn("sign_entry", source)
        self.assertNotIn("open(", source)
        self.assertNotIn("time.", source)
        self.assertNotIn("datetime", source)


if __name__ == "__main__":
    unittest.main()
