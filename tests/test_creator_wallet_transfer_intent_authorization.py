from __future__ import annotations

import ast
import copy
import hashlib
import json
import unittest
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import creator_wallet_transfer_intent as intent
from coin import creator_wallet_transfer_intent_authorization as authorization

BUNDLE_SHA256 = "a" * 64
BUNDLE_AGGREGATE = "b" * 64


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":"), sort_keys=True).encode("utf-8")


def _build() -> tuple[dict[str, object], str, str]:
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


def _verify(value: object):
    public_key = value.get("creator_public_key", "0" * 64) if isinstance(value, dict) else "0" * 64
    address = value.get("creator_address", "L28" + "0" * 40) if isinstance(value, dict) else "L28" + "0" * 40
    raw = value if isinstance(value, (str, bytes)) else json.dumps(value, separators=(",", ":"))
    with mock.patch.object(authorization, "FIXED_CREATOR_PUBLIC_KEY", public_key), \
         mock.patch.object(authorization, "FIXED_CREATOR_ADDRESS", address), \
         mock.patch.object(intent, "FIXED_CREATOR_ADDRESS", address):
        return authorization.verify_creator_wallet_transfer_intent_authorization_json(
            raw,
            expected_control_bundle_sha256=BUNDLE_SHA256,
            expected_control_bundle_aggregate_commitment=BUNDLE_AGGREGATE,
        )


class CreatorWalletTransferIntentAuthorizationTests(unittest.TestCase):
    def test_valid_ephemeral_authorization_succeeds(self) -> None:
        value, _, _ = _build()
        result = _verify(value)
        self.assertTrue(result.ok, result.code)
        self.assertEqual(result.authorization_id, value["authorization_id"])
        self.assertEqual(result.intent_id, value["intent_id"])
        self.assertEqual(result.amount, 28)
        self.assertEqual(result.checks, authorization.SUCCESS_CHECKS)

    def test_invalid_signature_fails_closed(self) -> None:
        value, _, _ = _build()
        value["signature"] = "0" * 128
        value["authorization_id"] = hashlib.sha256(
            authorization.AUTHORIZATION_ID_DOMAIN
            + _canonical({k: v for k, v in value.items() if k != "authorization_id"})
        ).hexdigest()
        self.assertEqual(_verify(value).code, "signature_invalid")

    def test_expected_commitment_checked_before_parse(self) -> None:
        with mock.patch.object(authorization, "_parse") as parse:
            result = authorization.verify_creator_wallet_transfer_intent_authorization_json(
                object(), expected_control_bundle_sha256="bad",
                expected_control_bundle_aggregate_commitment=BUNDLE_AGGREGATE,
            )
        self.assertEqual(result.code, "invalid_expected_commitment")
        parse.assert_not_called()

    def test_schema_missing_extra_and_order_fail(self) -> None:
        value, _, _ = _build()
        missing = copy.deepcopy(value); missing.pop("domain")
        self.assertEqual(_verify(missing).code, "schema_invalid")
        extra = copy.deepcopy(value); extra["extra"] = False
        self.assertEqual(_verify(extra).code, "schema_invalid")
        reordered = {name: value[name] for name in reversed(value)}
        self.assertEqual(_verify(reordered).code, "schema_invalid")

    def test_duplicate_key_at_nested_depth_fails(self) -> None:
        value, public_key, address = _build()
        raw = json.dumps(value, separators=(",", ":")).replace(
            '"amount":28', '"amount":28,"amount":28', 1
        )
        with mock.patch.object(authorization, "FIXED_CREATOR_PUBLIC_KEY", public_key), \
             mock.patch.object(authorization, "FIXED_CREATOR_ADDRESS", address), \
             mock.patch.object(intent, "FIXED_CREATOR_ADDRESS", address):
            result = authorization.verify_creator_wallet_transfer_intent_authorization_json(
                raw, expected_control_bundle_sha256=BUNDLE_SHA256,
                expected_control_bundle_aggregate_commitment=BUNDLE_AGGREGATE,
            )
        self.assertEqual(result.code, "duplicate_key")

    def test_invalid_inputs_fail_closed(self) -> None:
        cases = (
            (object(), "input_type_invalid"),
            (b"x" * (authorization.MAX_AUTHORIZATION_BYTES + 1), "input_too_large"),
            (bytes([255]), "encoding_invalid"),
            ("{", "json_invalid"),
            ("[]", "invalid_top_level"),
            ('{"x":NaN}', "json_invalid"),
        )
        for payload, code in cases:
            with self.subTest(code=code):
                result = authorization.verify_creator_wallet_transfer_intent_authorization_json(
                    payload, expected_control_bundle_sha256=BUNDLE_SHA256,
                    expected_control_bundle_aggregate_commitment=BUNDLE_AGGREGATE,
                )
                self.assertEqual(result.code, code)

    def test_version_domain_and_identity_are_exact(self) -> None:
        value, _, _ = _build(); value["authorization_version"] = "v1"
        self.assertEqual(_verify(value).code, "version_invalid")
        value, _, _ = _build(); value["domain"] = "other"
        self.assertEqual(_verify(value).code, "domain_invalid")
        value, public_key, address = _build(); value["creator_address"] = "L28" + "3" * 40
        raw = json.dumps(value, separators=(",", ":"))
        with mock.patch.object(authorization, "FIXED_CREATOR_PUBLIC_KEY", public_key), \
             mock.patch.object(authorization, "FIXED_CREATOR_ADDRESS", address), \
             mock.patch.object(intent, "FIXED_CREATOR_ADDRESS", address):
            result = authorization.verify_creator_wallet_transfer_intent_authorization_json(
                raw, expected_control_bundle_sha256=BUNDLE_SHA256,
                expected_control_bundle_aggregate_commitment=BUNDLE_AGGREGATE,
            )
        self.assertEqual(result.code, "identity_invalid")

    def test_intent_reverification_and_binding(self) -> None:
        value, _, _ = _build(); value["intent"]["amount"] = 29
        self.assertEqual(_verify(value).code, "intent_invalid")
        value, _, _ = _build(); value["intent_sha256"] = "0" * 64
        self.assertEqual(_verify(value).code, "intent_binding_invalid")
        value, _, _ = _build(); value["intent_id"] = "0" * 64
        self.assertEqual(_verify(value).code, "intent_binding_invalid")

    def test_signature_and_authorization_id_shapes(self) -> None:
        value, _, _ = _build(); value["signature"] = "0"
        self.assertEqual(_verify(value).code, "signature_invalid")
        value, _, _ = _build(); value["authorization_id"] = "0"
        self.assertEqual(_verify(value).code, "authorization_id_invalid")
        value, _, _ = _build(); value["authorization_id"] = "0" * 64
        self.assertEqual(_verify(value).code, "authorization_id_invalid")

    def test_result_frozen_input_unmodified_and_format_deterministic(self) -> None:
        value, public_key, address = _build(); before = copy.deepcopy(value)
        result = _verify(value)
        self.assertEqual(value, before)
        with self.assertRaises((AttributeError, TypeError)):
            result.code = "changed"  # type: ignore[misc]
        compact = json.dumps(value, separators=(",", ":")); pretty = json.dumps(value, indent=2)
        with mock.patch.object(authorization, "FIXED_CREATOR_PUBLIC_KEY", public_key), \
             mock.patch.object(authorization, "FIXED_CREATOR_ADDRESS", address), \
             mock.patch.object(intent, "FIXED_CREATOR_ADDRESS", address):
            one = authorization.verify_creator_wallet_transfer_intent_authorization_json(
                compact, expected_control_bundle_sha256=BUNDLE_SHA256,
                expected_control_bundle_aggregate_commitment=BUNDLE_AGGREGATE)
            two = authorization.verify_creator_wallet_transfer_intent_authorization_json(
                pretty, expected_control_bundle_sha256=BUNDLE_SHA256,
                expected_control_bundle_aggregate_commitment=BUNDLE_AGGREGATE)
        self.assertTrue(one.ok and two.ok)
        self.assertEqual(one.authorization_sha256, two.authorization_sha256)

    def test_wrapper_internal_error_and_public_constants(self) -> None:
        value, public_key, address = _build(); raw = json.dumps(value, separators=(",", ":"))
        with mock.patch.object(authorization, "FIXED_CREATOR_PUBLIC_KEY", public_key), \
             mock.patch.object(authorization, "FIXED_CREATOR_ADDRESS", address), \
             mock.patch.object(intent, "FIXED_CREATOR_ADDRESS", address):
            direct = _verify(value)
            wrapped = authorization.CreatorWalletTransferIntentAuthorizationVerifier.verify_json(
                raw, expected_control_bundle_sha256=BUNDLE_SHA256,
                expected_control_bundle_aggregate_commitment=BUNDLE_AGGREGATE)
        self.assertEqual(direct, wrapped)
        with mock.patch.object(authorization, "_parse", side_effect=RuntimeError("secret")):
            failed = authorization.verify_creator_wallet_transfer_intent_authorization_json(
                "{}", expected_control_bundle_sha256=BUNDLE_SHA256,
                expected_control_bundle_aggregate_commitment=BUNDLE_AGGREGATE)
        self.assertEqual(failed.code, "internal_error")
        self.assertEqual(len(authorization.STABLE_CODES), len(set(authorization.STABLE_CODES)))
        self.assertIn("signature_verified", authorization.SUCCESS_CHECKS)

    def test_production_core_has_no_private_key_io_or_activation(self) -> None:
        path = Path("coin/creator_wallet_transfer_intent_authorization.py")
        source = path.read_text(encoding="utf-8"); tree = ast.parse(source)
        imports = {alias.name.split(".", 1)[0] for node in ast.walk(tree)
                   if isinstance(node, ast.Import) for alias in node.names}
        imports |= {(node.module or "").split(".", 1)[0] for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom)}
        self.assertFalse(imports & {"os", "pathlib", "socket", "subprocess", "requests",
                                    "urllib", "http", "asyncio", "wallet", "ledger", "mining"})
        self.assertNotIn("Ed25519PrivateKey", source)
        self.assertNotIn("load_wallet", source)
        self.assertNotIn("sign_entry", source)


if __name__ == "__main__":
    unittest.main()
