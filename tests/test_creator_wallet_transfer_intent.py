import ast
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

from coin import creator_wallet_transfer_intent as intent


BUNDLE_SHA256 = "2" * 64
AGGREGATE_COMMITMENT = "3" * 64
RECIPIENT_ADDRESS = "L28" + "4" * 40


def _json(value, *, sort_keys=False):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=sort_keys,
        separators=(",", ":"),
    )


def _valid_intent():
    value = {
        "intent_version": intent.INTENT_VERSION,
        "domain": intent.INTENT_DOMAIN,
        "creator_address": intent.FIXED_CREATOR_ADDRESS,
        "recipient_address": RECIPIENT_ADDRESS,
        "amount": 28,
        "nonce": "1" * 64,
        "expires_at_unix": 2_000_000_000,
        "control_bundle_sha256": BUNDLE_SHA256,
        "control_bundle_aggregate_commitment": AGGREGATE_COMMITMENT,
        "intent_id": "0" * 64,
    }
    value["intent_id"] = intent._intent_id(value)
    return value


def _verify(value):
    return intent.verify_creator_wallet_transfer_intent_json(
        _json(value),
        expected_control_bundle_sha256=BUNDLE_SHA256,
        expected_control_bundle_aggregate_commitment=AGGREGATE_COMMITMENT,
    )


class CreatorWalletTransferIntentTests(unittest.TestCase):
    def test_valid_unsigned_intent_succeeds(self):
        value = _valid_intent()
        result = _verify(value)
        self.assertTrue(result.ok, result.code)
        self.assertEqual(result.code, "ok")
        self.assertEqual(result.checks, intent.SUCCESS_CHECKS)
        self.assertEqual(result.intent_id, value["intent_id"])
        self.assertEqual(result.creator_address, intent.FIXED_CREATOR_ADDRESS)
        self.assertEqual(result.recipient_address, RECIPIENT_ADDRESS)
        self.assertEqual(result.amount, 28)
        self.assertEqual(result.control_bundle_sha256, BUNDLE_SHA256)
        self.assertEqual(
            result.control_bundle_aggregate_commitment,
            AGGREGATE_COMMITMENT,
        )

    def test_public_constants_and_schema_are_explicit(self):
        self.assertEqual(
            intent.INTENT_VERSION,
            "l28-creator-wallet-transfer-intent/v0.1",
        )
        self.assertEqual(intent.INTENT_DOMAIN, intent.INTENT_VERSION)
        self.assertEqual(intent.MAX_INTENT_BYTES, 4096)
        self.assertEqual(
            intent.FIXED_CREATOR_ADDRESS,
            "L28d7d0903ab9e10e706c418c31fac95109577cdea6",
        )
        self.assertEqual(tuple(_valid_intent()), intent.TOP_LEVEL_FIELDS)
        self.assertNotIn("signature", intent.TOP_LEVEL_FIELDS)
        self.assertEqual(len(intent.STABLE_CODES), len(set(intent.STABLE_CODES)))

    def test_intent_id_matches_public_canonical_algorithm(self):
        value = _valid_intent()
        body = {key: item for key, item in value.items() if key != "intent_id"}
        expected = hashlib.sha256(
            b"l28-creator-wallet-transfer-intent/v0.1\x00"
            + json.dumps(
                body,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(value["intent_id"], expected)

    def test_formatting_is_deterministic(self):
        value = _valid_intent()
        compact = intent.verify_creator_wallet_transfer_intent_json(
            _json(value),
            expected_control_bundle_sha256=BUNDLE_SHA256,
            expected_control_bundle_aggregate_commitment=AGGREGATE_COMMITMENT,
        )
        pretty = intent.verify_creator_wallet_transfer_intent_json(
            json.dumps(value, ensure_ascii=False, indent=2),
            expected_control_bundle_sha256=BUNDLE_SHA256,
            expected_control_bundle_aggregate_commitment=AGGREGATE_COMMITMENT,
        )
        self.assertTrue(compact.ok)
        self.assertEqual(compact, pretty)

    def test_semantic_mutation_breaks_intent_id(self):
        value = _valid_intent()
        value["amount"] += 1
        self.assertEqual(_verify(value).code, "intent_id_mismatch")

    def test_duplicate_keys_are_rejected_at_any_depth(self):
        duplicate = '{"intent_version":"x","intent_version":"y"}'
        result = intent.verify_creator_wallet_transfer_intent_json(
            duplicate,
            expected_control_bundle_sha256=BUNDLE_SHA256,
            expected_control_bundle_aggregate_commitment=AGGREGATE_COMMITMENT,
        )
        self.assertEqual(result.code, "duplicate_key")
        nested = '{"outer":{"key":1,"key":2}}'
        result = intent.verify_creator_wallet_transfer_intent_json(
            nested,
            expected_control_bundle_sha256=BUNDLE_SHA256,
            expected_control_bundle_aggregate_commitment=AGGREGATE_COMMITMENT,
        )
        self.assertEqual(result.code, "duplicate_key")

    def test_invalid_encoding_json_nonfinite_type_and_top_level_fail_closed(self):
        cases = (
            (b"\xff", "invalid_encoding"),
            ("{", "invalid_json"),
            ('{"value":NaN}', "invalid_json"),
            ([], "invalid_input_type"),
            ("[]", "invalid_top_level"),
        )
        for payload, code in cases:
            with self.subTest(code=code):
                result = intent.verify_creator_wallet_transfer_intent_json(
                    payload,
                    expected_control_bundle_sha256=BUNDLE_SHA256,
                    expected_control_bundle_aggregate_commitment=(
                        AGGREGATE_COMMITMENT
                    ),
                )
                self.assertEqual(result.code, code)

    def test_oversized_input_is_rejected_before_json_parsing(self):
        payload = b"x" * (intent.MAX_INTENT_BYTES + 1)
        with mock.patch.object(intent.json, "loads", side_effect=AssertionError):
            result = intent.verify_creator_wallet_transfer_intent_json(
                payload,
                expected_control_bundle_sha256=BUNDLE_SHA256,
                expected_control_bundle_aggregate_commitment=(
                    AGGREGATE_COMMITMENT
                ),
            )
        self.assertEqual(result.code, "intent_too_large")

    def test_schema_is_exact_and_ordered(self):
        value = _valid_intent()
        value["extra"] = False
        self.assertEqual(_verify(value).code, "schema_invalid")
        value = _valid_intent()
        value.pop("nonce")
        self.assertEqual(_verify(value).code, "schema_invalid")
        value = _valid_intent()
        reordered = dict(reversed(tuple(value.items())))
        self.assertEqual(_verify(reordered).code, "schema_invalid")

    def test_version_and_domain_are_exact(self):
        for field, code in (
            ("intent_version", "intent_version_invalid"),
            ("domain", "domain_invalid"),
        ):
            for bad in ("wrong", None, 1, True):
                with self.subTest(field=field, bad=bad):
                    value = _valid_intent()
                    value[field] = bad
                    self.assertEqual(_verify(value).code, code)

    def test_creator_identity_is_fixed(self):
        value = _valid_intent()
        value["creator_address"] = "L28" + "5" * 40
        self.assertEqual(_verify(value).code, "creator_identity_mismatch")

    def test_recipient_shape_and_self_transfer_are_rejected(self):
        for bad in (
            intent.FIXED_CREATOR_ADDRESS,
            "L28" + "A" * 40,
            "L28" + "1" * 39,
            "not-an-address",
            None,
        ):
            with self.subTest(bad=bad):
                value = _valid_intent()
                value["recipient_address"] = bad
                self.assertEqual(_verify(value).code, "recipient_invalid")

    def test_amount_is_a_strict_positive_integer(self):
        for bad in (True, False, 0, -1, 1.0, "1", None):
            with self.subTest(bad=bad):
                value = _valid_intent()
                value["amount"] = bad
                self.assertEqual(_verify(value).code, "amount_invalid")

    def test_nonce_is_lowercase_hex64(self):
        for bad in ("a" * 63, "A" * 64, "g" * 64, 1, None):
            with self.subTest(bad=bad):
                value = _valid_intent()
                value["nonce"] = bad
                self.assertEqual(_verify(value).code, "nonce_invalid")

    def test_expiry_is_a_strict_positive_integer(self):
        for bad in (True, False, 0, -1, 1.0, "1", None):
            with self.subTest(bad=bad):
                value = _valid_intent()
                value["expires_at_unix"] = bad
                self.assertEqual(_verify(value).code, "expiry_invalid")

    def test_commitment_shapes_and_expected_binding_are_enforced(self):
        value = _valid_intent()
        value["control_bundle_sha256"] = "z" * 64
        self.assertEqual(
            _verify(value).code,
            "control_bundle_sha256_invalid",
        )
        value = _valid_intent()
        value["control_bundle_aggregate_commitment"] = "z" * 64
        self.assertEqual(
            _verify(value).code,
            "control_bundle_aggregate_commitment_invalid",
        )
        value = _valid_intent()
        result = intent.verify_creator_wallet_transfer_intent_json(
            _json(value),
            expected_control_bundle_sha256="4" * 64,
            expected_control_bundle_aggregate_commitment=AGGREGATE_COMMITMENT,
        )
        self.assertEqual(result.code, "control_bundle_mismatch")

    def test_invalid_expected_commitment_is_checked_before_json(self):
        with mock.patch.object(intent.json, "loads", side_effect=AssertionError):
            result = intent.verify_creator_wallet_transfer_intent_json(
                "not-json",
                expected_control_bundle_sha256="bad",
                expected_control_bundle_aggregate_commitment=(
                    AGGREGATE_COMMITMENT
                ),
            )
        self.assertEqual(result.code, "invalid_expected_commitment")

    def test_intent_id_shape_and_value_are_enforced(self):
        value = _valid_intent()
        value["intent_id"] = "bad"
        self.assertEqual(_verify(value).code, "intent_id_invalid")
        value = _valid_intent()
        value["intent_id"] = "f" * 64
        self.assertEqual(_verify(value).code, "intent_id_mismatch")

    def test_result_is_frozen_and_input_is_not_modified(self):
        value = _valid_intent()
        original = json.loads(_json(value))
        result = _verify(value)
        self.assertEqual(value, original)
        with self.assertRaises(FrozenInstanceError):
            result.code = "changed"

    def test_unexpected_exception_is_sanitized(self):
        with mock.patch.object(intent, "_parse", side_effect=RuntimeError("secret")):
            result = intent.verify_creator_wallet_transfer_intent_json(
                _json(_valid_intent()),
                expected_control_bundle_sha256=BUNDLE_SHA256,
                expected_control_bundle_aggregate_commitment=(
                    AGGREGATE_COMMITMENT
                ),
            )
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "internal_error")
        self.assertNotIn("secret", repr(result))

    def test_wrapper_matches_public_function(self):
        value = _valid_intent()
        direct = _verify(value)
        wrapped = intent.CreatorWalletTransferIntentVerifier.verify_json(
            _json(value),
            expected_control_bundle_sha256=BUNDLE_SHA256,
            expected_control_bundle_aggregate_commitment=AGGREGATE_COMMITMENT,
        )
        self.assertEqual(wrapped, direct)

    def test_production_module_has_no_io_signing_or_activation_imports(self):
        path = Path(intent.__file__)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertFalse(
            imports & {
                "os",
                "pathlib",
                "socket",
                "subprocess",
                "urllib",
                "requests",
            }
        )
        self.assertNotIn("Ed25519PrivateKey", source)
        self.assertNotIn("wallet_dir", source)
        self.assertNotIn("signature\"", source)


if __name__ == "__main__":
    unittest.main()
