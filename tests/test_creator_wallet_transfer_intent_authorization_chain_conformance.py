# SPDX-License-Identifier: Apache-2.0
"""Foundation 36 offline authorization-chain conformance suite.

Exercises Foundations 31–35 public APIs end-to-end with deterministic disposable
synthetic fixtures. Does not duplicate verifier logic or activate runtime paths.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import creator_wallet_control_evidence_bundle as bundle
from coin import creator_wallet_transfer_intent as intent
from coin import creator_wallet_transfer_intent_authorization as authorization
from coin import creator_wallet_transfer_intent_authorization_evidence as evidence
from coin import creator_wallet_transfer_intent_authorization_evidence_receipt as receipt

SUITE_SEED = b"l28-f36-authorization-chain-conformance/v0.1"
SUITE_ID = "l28-creator-wallet-transfer-intent-authorization-chain-conformance/v0.1"


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


def _suite_private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(hashlib.sha256(SUITE_SEED).digest())


def _address_for(public_key_hex: str) -> str:
    return "L28" + hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()[:40]


def _identity() -> tuple[Ed25519PrivateKey, str, str]:
    private_key = _suite_private_key()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    return private_key, public_key, _address_for(public_key)


def _patch_identity(public_key: str, address: str):
    return (
        mock.patch.multiple(
            authorization,
            FIXED_CREATOR_PUBLIC_KEY=public_key,
            FIXED_CREATOR_ADDRESS=address,
        ),
        mock.patch.object(intent, "FIXED_CREATOR_ADDRESS", address),
    )


def _f31_member(index: int) -> dict[str, object]:
    return {
        "evidence_version": "l28-creator-wallet-control-proof-evidence/v0.1",
        "expected_challenge_id": hashlib.sha256(
            SUITE_SEED + f":challenge:{index}".encode()
        ).hexdigest(),
        "proof": {"suite_marker": f"f36-{index}"},
        "report": {"suite_marker": f"f36-{index}"},
    }


def _f30_side_effect(payload: bytes) -> SimpleNamespace:
    member = json.loads(payload.decode("utf-8"))
    return SimpleNamespace(ok=True, evidence_sha256=hashlib.sha256(_canonical(member)).hexdigest())


def _build_f31_commitments() -> tuple[str, str, dict[str, object]]:
    members = sorted((_f31_member(0), _f31_member(1)), key=lambda m: hashlib.sha256(_canonical(m)).hexdigest())
    value = {"bundle_version": bundle.BUNDLE_VERSION, "members": members}
    raw = _json_bytes(value)
    with mock.patch.object(
        bundle,
        "verify_creator_wallet_control_proof_evidence_json",
        side_effect=_f30_side_effect,
    ):
        result = bundle.verify_creator_wallet_control_evidence_bundle_json(raw)
    if not result.ok:
        raise AssertionError(result.code)
    return result.bundle_sha256, result.aggregate_commitment, value


def _build_intent(bundle_sha256: str, aggregate: str, address: str) -> dict[str, object]:
    value: dict[str, object] = {
        "intent_version": intent.INTENT_VERSION,
        "domain": intent.INTENT_DOMAIN,
        "creator_address": address,
        "recipient_address": "L28" + "1" * 40,
        "amount": 28,
        "nonce": hashlib.sha256(SUITE_SEED + b":nonce").hexdigest(),
        "expires_at_unix": 2_000_000_000,
        "control_bundle_sha256": bundle_sha256,
        "control_bundle_aggregate_commitment": aggregate,
    }
    value["intent_id"] = hashlib.sha256(intent.INTENT_ID_DOMAIN + _canonical(value)).hexdigest()
    return value


def _build_authorization(
    intent_value: dict[str, object],
    private_key: Ed25519PrivateKey,
    public_key: str,
    address: str,
) -> dict[str, object]:
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
    return value


def _build_chain() -> dict[str, Any]:
    private_key, public_key, address = _identity()
    bundle_sha256, aggregate, f31_value = _build_f31_commitments()
    intent_value = _build_intent(bundle_sha256, aggregate, address)
    authorization_value = _build_authorization(
        intent_value, private_key, public_key, address
    )
    auth_patch, intent_patch = _patch_identity(public_key, address)
    with auth_patch, intent_patch:
        auth_result = authorization.verify_creator_wallet_transfer_intent_authorization_json(
            _json_bytes(authorization_value),
            expected_control_bundle_sha256=bundle_sha256,
            expected_control_bundle_aggregate_commitment=aggregate,
        )
    if not auth_result.ok:
        raise AssertionError(auth_result.code)
    report = evidence._build_expected_authorization_report(auth_result)
    evidence_value = {
        "evidence_version": evidence.EVIDENCE_VERSION,
        "expected_control_bundle_sha256": bundle_sha256,
        "expected_control_bundle_aggregate_commitment": aggregate,
        "authorization": authorization_value,
        "report": report,
    }
    auth_patch, intent_patch = _patch_identity(public_key, address)
    with auth_patch, intent_patch:
        evidence_result = evidence.verify_creator_wallet_transfer_intent_authorization_evidence_json(
            _json_bytes(evidence_value)
        )
    if not evidence_result.ok:
        raise AssertionError(evidence_result.code)
    receipt_value: dict[str, object] = {
        "receipt_version": receipt.RECEIPT_VERSION,
        "expected_control_bundle_sha256": bundle_sha256,
        "expected_control_bundle_aggregate_commitment": aggregate,
        "evidence": evidence_value,
        "evidence_sha256": evidence_result.evidence_sha256,
        "authorization_report_id": report["report_id"],
        "authorization_sha256": evidence_result.authorization_sha256,
        "authorization_id": evidence_result.authorization_id,
        "checks": list(evidence_result.checks),
        "execution_authorized": False,
    }
    receipt_value["receipt_id"] = receipt._receipt_id(receipt_value)
    return {
        "public_key": public_key,
        "address": address,
        "bundle_sha256": bundle_sha256,
        "aggregate": aggregate,
        "f31": f31_value,
        "intent": intent_value,
        "authorization": authorization_value,
        "evidence": evidence_value,
        "receipt": receipt_value,
        "auth_result": auth_result,
        "evidence_result": evidence_result,
    }


def _verify_layers(chain: dict[str, Any]) -> dict[str, Any]:
    auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
    with auth_patch, intent_patch:
        intent_result = intent.verify_creator_wallet_transfer_intent_json(
            _json_bytes(chain["intent"]),
            expected_control_bundle_sha256=chain["bundle_sha256"],
            expected_control_bundle_aggregate_commitment=chain["aggregate"],
        )
        auth_result = authorization.verify_creator_wallet_transfer_intent_authorization_json(
            _json_bytes(chain["authorization"]),
            expected_control_bundle_sha256=chain["bundle_sha256"],
            expected_control_bundle_aggregate_commitment=chain["aggregate"],
        )
        evidence_result = evidence.verify_creator_wallet_transfer_intent_authorization_evidence_json(
            _json_bytes(chain["evidence"])
        )
        receipt_result = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
            _json_bytes(chain["receipt"])
        )
    return {
        "intent": intent_result,
        "authorization": auth_result,
        "evidence": evidence_result,
        "receipt": receipt_result,
    }


class FixtureDeterminismTests(unittest.TestCase):
    def test_seeded_construction_is_repeatable(self) -> None:
        first = _build_chain()
        second = _build_chain()
        self.assertEqual(first["bundle_sha256"], second["bundle_sha256"])
        self.assertEqual(first["aggregate"], second["aggregate"])
        self.assertEqual(first["intent"], second["intent"])
        self.assertEqual(first["authorization"], second["authorization"])
        self.assertEqual(first["evidence"], second["evidence"])
        self.assertEqual(first["receipt"], second["receipt"])
        self.assertEqual(first["public_key"], second["public_key"])
        self.assertEqual(SUITE_ID, SUITE_ID)

    def test_identical_bytes_verify_twice_equal(self) -> None:
        chain = _build_chain()
        one = _verify_layers(chain)
        two = _verify_layers(chain)
        for name in ("intent", "authorization", "evidence", "receipt"):
            self.assertEqual(one[name], two[name], name)

    def test_compact_and_pretty_are_logically_equal(self) -> None:
        chain = _build_chain()
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        compact = json.dumps(chain["receipt"], separators=(",", ":"))
        pretty = json.dumps(chain["receipt"], indent=2)
        with auth_patch, intent_patch:
            first = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                compact
            )
            second = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                pretty
            )
        self.assertEqual(first, second)


class SuccessPathChainTests(unittest.TestCase):
    def test_complete_authorization_evidence_receipt_chain(self) -> None:
        chain = _build_chain()
        with mock.patch.object(
            bundle,
            "verify_creator_wallet_control_proof_evidence_json",
            side_effect=_f30_side_effect,
        ):
            f31 = bundle.verify_creator_wallet_control_evidence_bundle_json(
                _json_bytes(chain["f31"])
            )
        self.assertTrue(f31.ok, f31.code)
        self.assertEqual(f31.bundle_sha256, chain["bundle_sha256"])
        self.assertEqual(f31.aggregate_commitment, chain["aggregate"])

        results = _verify_layers(chain)
        for name, result in results.items():
            self.assertTrue(result.ok, f"{name}:{result.code}")
            self.assertEqual(result.code, "ok", name)

        self.assertEqual(results["evidence"].checks, evidence.SUCCESS_CHECKS)
        self.assertEqual(results["receipt"].checks, receipt.SUCCESS_CHECKS)
        self.assertEqual(
            results["receipt"].authorization_report_id,
            chain["evidence"]["report"]["report_id"],
        )
        self.assertEqual(
            results["receipt"].evidence_sha256, results["evidence"].evidence_sha256
        )
        self.assertEqual(
            results["receipt"].authorization_sha256,
            results["evidence"].authorization_sha256,
        )
        self.assertEqual(
            results["receipt"].authorization_id, results["evidence"].authorization_id
        )
        self.assertIs(chain["receipt"]["execution_authorized"], False)
        self.assertIs(chain["evidence"]["report"]["execution_authorized"], False)


class Foundation31CommitmentContinuityTests(unittest.TestCase):
    def test_intent_rejects_mutated_bundle_sha256(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["intent"])
        bad["control_bundle_sha256"] = "c" * 64
        bad["intent_id"] = hashlib.sha256(
            intent.INTENT_ID_DOMAIN + _canonical({k: v for k, v in bad.items() if k != "intent_id"})
        ).hexdigest()
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = intent.verify_creator_wallet_transfer_intent_json(
                _json_bytes(bad),
                expected_control_bundle_sha256=chain["bundle_sha256"],
                expected_control_bundle_aggregate_commitment=chain["aggregate"],
            )
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "control_bundle_mismatch")

    def test_intent_rejects_mutated_aggregate(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["intent"])
        bad["control_bundle_aggregate_commitment"] = "d" * 64
        bad["intent_id"] = hashlib.sha256(
            intent.INTENT_ID_DOMAIN + _canonical({k: v for k, v in bad.items() if k != "intent_id"})
        ).hexdigest()
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = intent.verify_creator_wallet_transfer_intent_json(
                _json_bytes(bad),
                expected_control_bundle_sha256=chain["bundle_sha256"],
                expected_control_bundle_aggregate_commitment=chain["aggregate"],
            )
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "control_bundle_mismatch")

    def test_authorization_rejects_uppercase_commitment(self) -> None:
        chain = _build_chain()
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = authorization.verify_creator_wallet_transfer_intent_authorization_json(
                _json_bytes(chain["authorization"]),
                expected_control_bundle_sha256=chain["bundle_sha256"].upper(),
                expected_control_bundle_aggregate_commitment=chain["aggregate"],
            )
        self.assertEqual(result.code, "invalid_expected_commitment")

    def test_receipt_rejects_commitment_mismatch_against_embedded_evidence(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["receipt"])
        bad["expected_control_bundle_sha256"] = "e" * 64
        bad["receipt_id"] = receipt._receipt_id(bad)
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                _json_bytes(bad)
            )
        self.assertEqual(result.code, "commitment_mismatch")


class Foundation33TamperMatrixTests(unittest.TestCase):
    def test_signature_mutation_fails(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["authorization"])
        bad["signature"] = "0" * 128
        bad["authorization_id"] = hashlib.sha256(
            authorization.AUTHORIZATION_ID_DOMAIN
            + _canonical({k: v for k, v in bad.items() if k != "authorization_id"})
        ).hexdigest()
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = authorization.verify_creator_wallet_transfer_intent_authorization_json(
                _json_bytes(bad),
                expected_control_bundle_sha256=chain["bundle_sha256"],
                expected_control_bundle_aggregate_commitment=chain["aggregate"],
            )
        self.assertEqual(result.code, "signature_invalid")

    def test_authorization_id_mutation_fails(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["authorization"])
        bad["authorization_id"] = "0" * 64
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = authorization.verify_creator_wallet_transfer_intent_authorization_json(
                _json_bytes(bad),
                expected_control_bundle_sha256=chain["bundle_sha256"],
                expected_control_bundle_aggregate_commitment=chain["aggregate"],
            )
        self.assertEqual(result.code, "authorization_id_invalid")

    def test_intent_amount_mutation_fails(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["authorization"])
        bad["intent"]["amount"] = 29
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = authorization.verify_creator_wallet_transfer_intent_authorization_json(
                _json_bytes(bad),
                expected_control_bundle_sha256=chain["bundle_sha256"],
                expected_control_bundle_aggregate_commitment=chain["aggregate"],
            )
        self.assertEqual(result.code, "intent_invalid")

    def test_report_id_forgery_fails_at_evidence(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["evidence"])
        bad["report"]["report_id"] = "0" * 64
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = evidence.verify_creator_wallet_transfer_intent_authorization_evidence_json(
                _json_bytes(bad)
            )
        self.assertEqual(result.code, "report_invalid")


class Foundation34TamperMatrixTests(unittest.TestCase):
    def test_embedded_authorization_mutation_fails(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["evidence"])
        bad["authorization"]["signature"] = "1" * 128
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = evidence.verify_creator_wallet_transfer_intent_authorization_evidence_json(
                _json_bytes(bad)
            )
        self.assertEqual(result.code, "authorization_invalid")

    def test_evidence_sha256_claim_mutation_fails_at_receipt(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["receipt"])
        bad["evidence_sha256"] = "0" * 64
        bad["receipt_id"] = receipt._receipt_id(bad)
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                _json_bytes(bad)
            )
        self.assertEqual(result.code, "evidence_commitment_invalid")

    def test_forged_report_body_fails(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["evidence"])
        bad["report"]["amount"] = 99
        bad["report"]["report_id"] = evidence._authorization_report_id(bad["report"])
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = evidence.verify_creator_wallet_transfer_intent_authorization_evidence_json(
                _json_bytes(bad)
            )
        self.assertEqual(result.code, "report_invalid")

    def test_reordered_evidence_fields_fail(self) -> None:
        chain = _build_chain()
        value = chain["evidence"]
        reordered = {
            "expected_control_bundle_sha256": value["expected_control_bundle_sha256"],
            "evidence_version": value["evidence_version"],
            "expected_control_bundle_aggregate_commitment": value[
                "expected_control_bundle_aggregate_commitment"
            ],
            "authorization": value["authorization"],
            "report": value["report"],
        }
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = evidence.verify_creator_wallet_transfer_intent_authorization_evidence_json(
                _json_bytes(reordered)
            )
        self.assertEqual(result.code, "schema_invalid")


class Foundation35TamperMatrixTests(unittest.TestCase):
    def test_receipt_commitment_tamper_fails(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["receipt"])
        bad["expected_control_bundle_aggregate_commitment"] = "f" * 64
        bad["receipt_id"] = receipt._receipt_id(bad)
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                _json_bytes(bad)
            )
        self.assertEqual(result.code, "commitment_mismatch")

    def test_authorization_report_id_tamper_fails(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["receipt"])
        bad["authorization_report_id"] = "0" * 64
        bad["receipt_id"] = receipt._receipt_id(bad)
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                _json_bytes(bad)
            )
        self.assertEqual(result.code, "authorization_report_invalid")

    def test_authorization_id_tamper_fails(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["receipt"])
        bad["authorization_id"] = "0" * 64
        bad["receipt_id"] = receipt._receipt_id(bad)
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                _json_bytes(bad)
            )
        self.assertEqual(result.code, "evidence_commitment_invalid")

    def test_checks_tamper_fails(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["receipt"])
        bad["checks"] = ["schema_exact"]
        bad["receipt_id"] = receipt._receipt_id(bad)
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                _json_bytes(bad)
            )
        self.assertEqual(result.code, "checks_invalid")

    def test_execution_authorized_true_fails(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["receipt"])
        bad["execution_authorized"] = True
        bad["receipt_id"] = receipt._receipt_id(bad)
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                _json_bytes(bad)
            )
        self.assertEqual(result.code, "schema_invalid")

    def test_receipt_id_tamper_fails(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["receipt"])
        bad["receipt_id"] = "0" * 64
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                _json_bytes(bad)
            )
        self.assertEqual(result.code, "receipt_id_invalid")

    def test_reordered_receipt_fields_fail(self) -> None:
        chain = _build_chain()
        value = chain["receipt"]
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
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                _json_bytes(reordered)
            )
        self.assertEqual(result.code, "schema_invalid")


class MalformedAndSizeLimitMatrixTests(unittest.TestCase):
    def test_authorization_malformed_matrix(self) -> None:
        cases = (
            (object(), "input_type_invalid"),
            (b"x" * (authorization.MAX_AUTHORIZATION_BYTES + 1), "input_too_large"),
            (bytes([255]), "encoding_invalid"),
            ("{", "json_invalid"),
            ("[]", "invalid_top_level"),
            ('{"x":NaN}', "json_invalid"),
            ('{"a":1,"a":2}', "duplicate_key"),
        )
        for payload, code in cases:
            with self.subTest(layer="authorization", code=code):
                result = authorization.verify_creator_wallet_transfer_intent_authorization_json(
                    payload,  # type: ignore[arg-type]
                    expected_control_bundle_sha256="a" * 64,
                    expected_control_bundle_aggregate_commitment="b" * 64,
                )
                self.assertEqual(result.code, code)
                self.assertNotIn("Traceback", result.code)

    def test_evidence_malformed_matrix(self) -> None:
        cases = (
            (object(), "input_type_invalid"),
            (b"x" * (evidence.MAX_EVIDENCE_BYTES + 1), "input_too_large"),
            (bytes([255]), "encoding_invalid"),
            ("{", "json_invalid"),
            ("[]", "invalid_top_level"),
            ('{"x":NaN}', "json_invalid"),
            ('{"a":1,"a":2}', "duplicate_key"),
        )
        for payload, code in cases:
            with self.subTest(layer="evidence", code=code):
                result = evidence.verify_creator_wallet_transfer_intent_authorization_evidence_json(
                    payload  # type: ignore[arg-type]
                )
                self.assertEqual(result.code, code)

    def test_receipt_malformed_matrix(self) -> None:
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
            with self.subTest(layer="receipt", code=code):
                result = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                    payload  # type: ignore[arg-type]
                )
                self.assertEqual(result.code, code)

    def test_nested_duplicate_key_fails_closed(self) -> None:
        chain = _build_chain()
        raw = _json_bytes(chain["authorization"]).decode("utf-8").replace(
            '"amount":28', '"amount":28,"amount":28', 1
        )
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = authorization.verify_creator_wallet_transfer_intent_authorization_json(
                raw,
                expected_control_bundle_sha256=chain["bundle_sha256"],
                expected_control_bundle_aggregate_commitment=chain["aggregate"],
            )
        self.assertEqual(result.code, "duplicate_key")

    def test_schema_order_failures_are_stable(self) -> None:
        chain = _build_chain()
        auth = chain["authorization"]
        reordered = {name: auth[name] for name in reversed(list(auth.keys()))}
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = authorization.verify_creator_wallet_transfer_intent_authorization_json(
                _json_bytes(reordered),
                expected_control_bundle_sha256=chain["bundle_sha256"],
                expected_control_bundle_aggregate_commitment=chain["aggregate"],
            )
        self.assertEqual(result.code, "schema_invalid")


class NonActivationMatrixTests(unittest.TestCase):
    def test_success_path_keeps_execution_authorized_false(self) -> None:
        chain = _build_chain()
        results = _verify_layers(chain)
        self.assertTrue(results["receipt"].ok)
        self.assertIs(chain["receipt"]["execution_authorized"], False)
        self.assertIs(chain["evidence"]["report"]["execution_authorized"], False)

    def test_failure_path_does_not_authorize_execution(self) -> None:
        chain = _build_chain()
        bad = copy.deepcopy(chain["receipt"])
        bad["receipt_id"] = "0" * 64
        auth_patch, intent_patch = _patch_identity(chain["public_key"], chain["address"])
        with auth_patch, intent_patch:
            result = receipt.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
                _json_bytes(bad)
            )
        self.assertFalse(result.ok)
        self.assertEqual(result.receipt_id, "")
        self.assertNotIn("wallet", result.code)
        self.assertNotIn("secret", result.code)

    def test_suite_avoids_wallet_secret_loading(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        forbidden = ("load" + "_wallet", "BEGIN" + " PRIVATE", "FIXED_CREATOR_" + "PRIVATE")
        for needle in forbidden:
            self.assertNotIn(needle, source)
        self.assertIn("SUITE_SEED", source)
        self.assertIn("from_private_bytes", source)


class StaticHygieneTests(unittest.TestCase):
    def test_suite_module_has_no_network_ledger_or_runtime_imports(self) -> None:
        path = Path(__file__)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        modules = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        modules |= {
            (node.module or "").split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        self.assertFalse(
            modules
            & {
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
        for needle in ("load" + "_wallet(", "sign" + "_entry(", "time" + ".", "date" + "time"):
            self.assertNotIn(needle, source)
        # Public APIs must be referenced; no local parallel verifier functions.
        self.assertIn("verify_creator_wallet_control_evidence_bundle_json", source)
        self.assertIn("verify_creator_wallet_transfer_intent_json", source)
        self.assertIn("verify_creator_wallet_transfer_intent_authorization_json", source)
        self.assertIn(
            "verify_creator_wallet_transfer_intent_authorization_evidence_json", source
        )
        self.assertIn(
            "verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json",
            source,
        )


if __name__ == "__main__":
    unittest.main()
