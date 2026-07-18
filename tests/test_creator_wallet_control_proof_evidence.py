import copy
import json
import unittest
from dataclasses import FrozenInstanceError
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import creator_wallet_control_proof as proof
from coin import creator_wallet_control_proof_evidence as evidence


CHALLENGE = "d" * 64


def _canonical_bytes(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _json_bytes(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _address_for(public_key_hex):
    import hashlib

    return "L28" + hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()[:40]


def _signed_proof():
    private_key = Ed25519PrivateKey.generate()
    public_key_hex = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    address = _address_for(public_key_hex)
    unsigned = {
        "proof_version": proof.PROOF_VERSION,
        "domain": proof.PROOF_DOMAIN,
        "challenge_id": CHALLENGE,
        "public_key": public_key_hex,
        "address": address,
    }
    return {**unsigned, "signature": private_key.sign(_canonical_bytes(unsigned)).hex()}


def _valid_evidence():
    proof_value = _signed_proof()
    with mock.patch.object(proof, "FIXED_CREATOR_PUBLIC_KEY", proof_value["public_key"]), mock.patch.object(
        proof, "FIXED_CREATOR_ADDRESS", proof_value["address"]
    ):
        result = proof.verify_creator_wallet_control_proof_json(
            _json_bytes(proof_value),
            expected_challenge_id=CHALLENGE,
        )
    assert result.ok
    report = evidence._build_expected_proof_report(
        ok=result.ok,
        code=result.code,
        checks=result.checks,
        proof_sha256=result.proof_sha256,
    )
    return {
        "evidence_version": evidence.EVIDENCE_VERSION,
        "expected_challenge_id": CHALLENGE,
        "proof": proof_value,
        "report": report,
    }


def _verify_with_test_identity(value):
    proof_value = value.get("proof") if isinstance(value, dict) else None
    if isinstance(proof_value, dict):
        with mock.patch.object(proof, "FIXED_CREATOR_PUBLIC_KEY", proof_value["public_key"]), mock.patch.object(
            proof, "FIXED_CREATOR_ADDRESS", proof_value["address"]
        ):
            return evidence.verify_creator_wallet_control_proof_evidence_json(_json_bytes(value))
    return evidence.verify_creator_wallet_control_proof_evidence_json(_json_bytes(value))


class CreatorWalletControlProofEvidenceTests(unittest.TestCase):
    def test_canonical_evidence_is_valid_and_bound(self):
        value = _valid_evidence()
        result = _verify_with_test_identity(value)

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "ok")
        self.assertEqual(result.checks, evidence.SUCCESS_CHECKS)
        self.assertEqual(result.evidence_sha256, evidence.hashlib.sha256(_canonical_bytes(value)).hexdigest())
        self.assertEqual(result.proof_sha256, value["report"]["proof_sha256"])

    def test_evidence_version_and_top_level_schema_are_exact(self):
        value = _valid_evidence()

        missing = dict(value)
        missing.pop("report")
        self.assertEqual(_verify_with_test_identity(missing).code, "schema_invalid")

        extra = dict(value)
        extra["extra"] = {}
        self.assertEqual(_verify_with_test_identity(extra).code, "schema_invalid")

        bad_version = dict(value)
        bad_version["evidence_version"] = "other"
        self.assertEqual(_verify_with_test_identity(bad_version).code, "schema_invalid")

    def test_field_order_is_exact(self):
        value = _valid_evidence()
        reordered = {
            "expected_challenge_id": value["expected_challenge_id"],
            "evidence_version": value["evidence_version"],
            "proof": value["proof"],
            "report": value["report"],
        }

        self.assertEqual(_verify_with_test_identity(reordered).code, "schema_invalid")

    def test_challenge_is_bounded_and_reverified(self):
        value = _valid_evidence()

        bad_shape = dict(value)
        bad_shape["expected_challenge_id"] = "not-hex"
        self.assertEqual(_verify_with_test_identity(bad_shape).code, "challenge_invalid")

        mismatch = copy.deepcopy(value)
        mismatch["expected_challenge_id"] = "e" * 64
        self.assertEqual(_verify_with_test_identity(mismatch).code, "proof_invalid")

    def test_proof_and_report_must_be_objects(self):
        value = _valid_evidence()

        bad_proof = dict(value)
        bad_proof["proof"] = []
        self.assertEqual(_verify_with_test_identity(bad_proof).code, "proof_invalid")

        bad_report = dict(value)
        bad_report["report"] = []
        self.assertEqual(_verify_with_test_identity(bad_report).code, "report_invalid")

    def test_invalid_proof_is_rejected_before_report_acceptance(self):
        value = _valid_evidence()
        value["proof"]["signature"] = "0" * 128

        self.assertEqual(_verify_with_test_identity(value).code, "proof_invalid")

    def test_report_schema_is_exact(self):
        value = _valid_evidence()

        missing = copy.deepcopy(value)
        missing["report"].pop("network_access")
        self.assertEqual(_verify_with_test_identity(missing).code, "report_invalid")

        extra = copy.deepcopy(value)
        extra["report"]["extra"] = False
        self.assertEqual(_verify_with_test_identity(extra).code, "report_invalid")

        wrong_version = copy.deepcopy(value)
        wrong_version["report"]["report_version"] = "other"
        self.assertEqual(_verify_with_test_identity(wrong_version).code, "report_invalid")

    def test_report_id_and_body_binding_are_enforced(self):
        value = _valid_evidence()

        bad_id = copy.deepcopy(value)
        bad_id["report"]["report_id"] = "0" * 64
        self.assertEqual(_verify_with_test_identity(bad_id).code, "report_invalid")

        bad_code = copy.deepcopy(value)
        bad_code["report"]["code"] = "challenge_invalid"
        bad_code["report"]["report_id"] = evidence._report_id(bad_code["report"])
        self.assertEqual(_verify_with_test_identity(bad_code).code, "report_invalid")

    def test_report_runtime_safety_flags_must_remain_false(self):
        for key in (
            "runtime_activation",
            "wallet_loaded",
            "private_key_read",
            "signature_created",
            "transfer_created",
            "ledger_mutated",
            "network_access",
        ):
            value = _valid_evidence()
            value["report"][key] = True
            value["report"]["report_id"] = evidence._report_id(value["report"])
            self.assertEqual(_verify_with_test_identity(value).code, "report_invalid", key)

    def test_recomputed_proof_sha256_claim_is_enforced(self):
        value = _valid_evidence()
        value["report"]["proof_sha256"] = "0" * 64
        value["report"]["report_id"] = evidence._report_id(value["report"])

        self.assertEqual(_verify_with_test_identity(value).code, "report_invalid")

    def test_semantic_proof_mutation_breaks_report_binding(self):
        value = _valid_evidence()
        value["proof"]["domain"] = proof.PROOF_DOMAIN
        value["proof"]["signature"] = "1" * 128

        self.assertEqual(_verify_with_test_identity(value).code, "proof_invalid")

    def test_duplicate_keys_nonfinite_encoding_and_input_type_fail_closed(self):
        self.assertEqual(
            evidence.verify_creator_wallet_control_proof_evidence_json(
                '{"evidence_version":"x","evidence_version":"x"}'
            ).code,
            "invalid_json",
        )
        self.assertEqual(
            evidence.verify_creator_wallet_control_proof_evidence_json('{"value":NaN}').code,
            "invalid_json",
        )
        self.assertEqual(
            evidence.verify_creator_wallet_control_proof_evidence_json(b"\xff").code,
            "invalid_json",
        )
        self.assertEqual(
            evidence.verify_creator_wallet_control_proof_evidence_json({"not": "json"}).code,  # type: ignore[arg-type]
            "invalid_input_type",
        )

    def test_oversized_input_is_rejected_before_json_parsing(self):
        payload = "{" + (" " * evidence.MAX_EVIDENCE_BYTES) + "}"
        result = evidence.verify_creator_wallet_control_proof_evidence_json(payload)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "evidence_too_large")

    def test_results_are_frozen_and_input_is_not_modified(self):
        value = _valid_evidence()
        original = copy.deepcopy(value)
        result = _verify_with_test_identity(value)

        self.assertEqual(value, original)
        with self.assertRaises(FrozenInstanceError):
            result.code = "changed"  # type: ignore[misc]

    def test_semantically_identical_formatting_is_deterministic(self):
        value = _valid_evidence()
        pretty = json.dumps(value, indent=2)
        compact = json.dumps(value, separators=(",", ":"))

        proof_value = value["proof"]
        with mock.patch.object(proof, "FIXED_CREATOR_PUBLIC_KEY", proof_value["public_key"]), mock.patch.object(
            proof, "FIXED_CREATOR_ADDRESS", proof_value["address"]
        ):
            first = evidence.verify_creator_wallet_control_proof_evidence_json(pretty)
            second = evidence.verify_creator_wallet_control_proof_evidence_json(compact)

        self.assertEqual(first, second)

    def test_wrapper_matches_public_function(self):
        value = _valid_evidence()
        proof_value = value["proof"]
        with mock.patch.object(proof, "FIXED_CREATOR_PUBLIC_KEY", proof_value["public_key"]), mock.patch.object(
            proof, "FIXED_CREATOR_ADDRESS", proof_value["address"]
        ):
            wrapped = evidence.CreatorWalletControlProofEvidenceVerifier.verify_json(_json_bytes(value))
            direct = evidence.verify_creator_wallet_control_proof_evidence_json(_json_bytes(value))

        self.assertEqual(wrapped, direct)

    def test_internal_exception_is_sanitized(self):
        with mock.patch.object(evidence, "_parse", side_effect=RuntimeError("private detail")):
            result = evidence.verify_creator_wallet_control_proof_evidence_json("{}")

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "internal_error")

    def test_production_module_has_no_io_private_key_or_network_imports(self):
        import ast
        from pathlib import Path

        source = Path(evidence.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }

        self.assertFalse(imports & {"os", "pathlib", "socket", "subprocess", "urllib", "requests"})
        self.assertNotIn("Ed25519PrivateKey", source)
        self.assertNotIn("open(", source)
        self.assertNotIn("wallet_dir", source)
        self.assertNotIn("load_wallet", source)


if __name__ == "__main__":
    unittest.main()
