import copy
import json
import unittest
from dataclasses import FrozenInstanceError
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import creator_wallet_control_proof as proof


CHALLENGE = "a" * 64


def _canonical_bytes(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _address_for(public_key_hex):
    import hashlib

    return "L28" + hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()[:40]


def _test_key_material():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_key_hex = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    return private_key, public_key_hex, _address_for(public_key_hex)


def _signed_proof():
    private_key, public_key_hex, address = _test_key_material()
    unsigned = {
        "proof_version": proof.PROOF_VERSION,
        "domain": proof.PROOF_DOMAIN,
        "challenge_id": CHALLENGE,
        "public_key": public_key_hex,
        "address": address,
    }
    signature = private_key.sign(_canonical_bytes(unsigned)).hex()
    return {
        **unsigned,
        "signature": signature,
    }


def _verify_test_identity(value, challenge=CHALLENGE):
    with mock.patch.object(proof, "FIXED_CREATOR_PUBLIC_KEY", value["public_key"]), mock.patch.object(
        proof, "FIXED_CREATOR_ADDRESS", value["address"]
    ):
        return proof.verify_creator_wallet_control_proof_json(
            json.dumps(value, separators=(",", ":")),
            expected_challenge_id=challenge,
        )


class CreatorWalletControlProofTests(unittest.TestCase):
    def test_valid_non_production_control_proof_succeeds(self):
        value = _signed_proof()
        result = _verify_test_identity(value)

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "ok")
        self.assertEqual(result.checks, proof.SUCCESS_CHECKS)
        self.assertEqual(result.proof_sha256, proof.hashlib.sha256(_canonical_bytes(value)).hexdigest())

    def test_real_creator_identity_is_fixed_and_public_only(self):
        self.assertEqual(
            proof.FIXED_CREATOR_PUBLIC_KEY,
            "c03a4ffd7e94cba2199f6a95a94f13d5aa0c6090f0c3f06aa59f6afc8dd26ff5",
        )
        self.assertEqual(
            proof.FIXED_CREATOR_ADDRESS,
            "L28d7d0903ab9e10e706c418c31fac95109577cdea6",
        )
        self.assertEqual(_address_for(proof.FIXED_CREATOR_PUBLIC_KEY), proof.FIXED_CREATOR_ADDRESS)

    def test_challenge_must_match_expected_value(self):
        value = _signed_proof()
        result = _verify_test_identity(value, challenge="b" * 64)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "challenge_invalid")

    def test_expected_challenge_shape_is_checked_before_json(self):
        result = proof.verify_creator_wallet_control_proof_json(
            "{",
            expected_challenge_id="not-hex",
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "challenge_invalid")

    def test_schema_is_exact(self):
        value = _signed_proof()

        missing = dict(value)
        missing.pop("signature")
        self.assertEqual(_verify_test_identity(missing).code, "schema_invalid")

        extra = dict(value)
        extra["extra"] = "field"
        self.assertEqual(_verify_test_identity(extra).code, "schema_invalid")

        wrong_type = dict(value)
        wrong_type["address"] = 28
        self.assertEqual(_verify_test_identity(wrong_type).code, "schema_invalid")

    def test_field_order_is_exact(self):
        value = _signed_proof()
        reordered = {
            "domain": value["domain"],
            "proof_version": value["proof_version"],
            "challenge_id": value["challenge_id"],
            "public_key": value["public_key"],
            "address": value["address"],
            "signature": value["signature"],
        }

        self.assertEqual(_verify_test_identity(reordered).code, "schema_invalid")

    def test_version_and_domain_are_exact(self):
        value = _signed_proof()

        bad_version = dict(value)
        bad_version["proof_version"] = "other"
        self.assertEqual(_verify_test_identity(bad_version).code, "version_invalid")

        bad_domain = dict(value)
        bad_domain["domain"] = "other"
        self.assertEqual(_verify_test_identity(bad_domain).code, "domain_invalid")

    def test_public_key_address_and_signature_shapes_fail_closed(self):
        value = _signed_proof()

        bad_key = dict(value)
        bad_key["public_key"] = "A" * 64
        self.assertEqual(_verify_test_identity(bad_key).code, "identity_invalid")

        bad_address = dict(value)
        bad_address["address"] = "L28" + "g" * 40
        self.assertEqual(_verify_test_identity(bad_address).code, "identity_invalid")

        bad_signature = dict(value)
        bad_signature["signature"] = "0" * 127
        self.assertEqual(_verify_test_identity(bad_signature).code, "signature_invalid")

    def test_identity_mismatch_fails_closed(self):
        value = _signed_proof()

        with mock.patch.object(proof, "FIXED_CREATOR_PUBLIC_KEY", "b" * 64), mock.patch.object(
            proof, "FIXED_CREATOR_ADDRESS", value["address"]
        ):
            self.assertEqual(
                proof.verify_creator_wallet_control_proof_json(
                    json.dumps(value),
                    expected_challenge_id=CHALLENGE,
                ).code,
                "identity_invalid",
            )

    def test_signature_is_over_wallet_compatible_canonical_payload_without_signature(self):
        value = _signed_proof()
        changed = dict(value)
        changed["domain"] = proof.PROOF_DOMAIN
        changed["signature"] = "0" * 128

        self.assertEqual(_verify_test_identity(changed).code, "signature_invalid")

    def test_duplicate_keys_nonfinite_invalid_encoding_and_top_level_fail_closed(self):
        duplicate = (
            '{"proof_version":"l28-creator-wallet-control-proof/v0.1",'
            '"proof_version":"l28-creator-wallet-control-proof/v0.1"}'
        )
        self.assertEqual(
            proof.verify_creator_wallet_control_proof_json(
                duplicate,
                expected_challenge_id=CHALLENGE,
            ).code,
            "invalid_json",
        )
        self.assertEqual(
            proof.verify_creator_wallet_control_proof_json(
                '{"proof_version":NaN}',
                expected_challenge_id=CHALLENGE,
            ).code,
            "invalid_json",
        )
        self.assertEqual(
            proof.verify_creator_wallet_control_proof_json(
                b"\xff",
                expected_challenge_id=CHALLENGE,
            ).code,
            "invalid_json",
        )
        self.assertEqual(
            proof.verify_creator_wallet_control_proof_json(
                "[]",
                expected_challenge_id=CHALLENGE,
            ).code,
            "schema_invalid",
        )

    def test_oversized_input_is_rejected_before_json_parsing(self):
        payload = "{" + (" " * proof.MAX_PROOF_BYTES) + "}"
        result = proof.verify_creator_wallet_control_proof_json(
            payload,
            expected_challenge_id=CHALLENGE,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "proof_too_large")

    def test_invalid_input_type_fails_closed(self):
        result = proof.verify_creator_wallet_control_proof_json(  # type: ignore[arg-type]
            {"not": "json"},
            expected_challenge_id=CHALLENGE,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "invalid_input_type")

    def test_result_is_frozen_and_input_is_not_modified(self):
        value = _signed_proof()
        original = copy.deepcopy(value)
