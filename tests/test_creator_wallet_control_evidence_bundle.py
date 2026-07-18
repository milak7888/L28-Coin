from __future__ import annotations

import ast
import copy
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

from coin import creator_wallet_control_evidence_bundle as bundle


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _member(index: int) -> dict[str, object]:
    return {
        "evidence_version": "l28-creator-wallet-control-proof-evidence/v0.1",
        "expected_challenge_id": f"{index + 1:064x}",
        "proof": {},
        "report": {},
    }


def _digest(member: dict[str, object]) -> str:
    return hashlib.sha256(_canonical(member)).hexdigest()


def _valid_result(payload: bytes) -> SimpleNamespace:
    member = json.loads(payload.decode("utf-8"))
    return SimpleNamespace(ok=True, evidence_sha256=_digest(member))


def _members(count: int) -> list[dict[str, object]]:
    values = [_member(index) for index in range(count)]
    return sorted(values, key=_digest)


def _payload(members: list[object]) -> dict[str, object]:
    return {
        "bundle_version": bundle.BUNDLE_VERSION,
        "members": members,
    }


def _verify(value: dict[str, object]):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    with mock.patch.object(
        bundle,
        "verify_creator_wallet_control_proof_evidence_json",
        side_effect=_valid_result,
    ):
        return bundle.verify_creator_wallet_control_evidence_bundle_json(raw)


class CreatorWalletControlEvidenceBundleTests(unittest.TestCase):
    def test_public_constants_and_stable_codes(self) -> None:
        self.assertEqual(
            bundle.BUNDLE_VERSION,
            "l28-creator-wallet-control-evidence-bundle/v0.1",
        )
        self.assertEqual(bundle.MIN_MEMBERS, 1)
        self.assertEqual(bundle.MAX_MEMBERS, 32)
        self.assertEqual(bundle.MAX_BUNDLE_BYTES, 270336)
        self.assertEqual(len(bundle.STABLE_CODES), len(set(bundle.STABLE_CODES)))
        self.assertEqual(len(bundle.SUCCESS_CHECKS), len(set(bundle.SUCCESS_CHECKS)))
        self.assertIn("duplicate_member", bundle.STABLE_CODES)
        self.assertIn("duplicate_challenge", bundle.STABLE_CODES)
        self.assertIn("noncanonical_member_order", bundle.STABLE_CODES)

    def test_one_and_thirty_two_members_succeed(self) -> None:
        for count in (1, 32):
            with self.subTest(count=count):
                result = _verify(_payload(_members(count)))
                self.assertTrue(result.ok)
                self.assertEqual(result.code, "ok")
                self.assertEqual(result.checks, bundle.SUCCESS_CHECKS)
                self.assertEqual(len(result.member_evidence_sha256), count)

    def test_member_count_is_bounded(self) -> None:
        self.assertEqual(_verify(_payload([])).code, "member_count_invalid")
        self.assertEqual(
            _verify(_payload([{} for _ in range(33)])).code,
            "member_count_invalid",
        )

    def test_top_level_schema_order_version_and_members_type(self) -> None:
        wrong_order = {
            "members": _members(1),
            "bundle_version": bundle.BUNDLE_VERSION,
        }
        self.assertEqual(_verify(wrong_order).code, "invalid_top_level")
        extra = _payload(_members(1))
        extra["extra"] = False
        self.assertEqual(_verify(extra).code, "invalid_top_level")
        wrong_version = _payload(_members(1))
        wrong_version["bundle_version"] = "v0"
        self.assertEqual(_verify(wrong_version).code, "invalid_bundle_version")
        wrong_members = _payload(_members(1))
        wrong_members["members"] = {}
        self.assertEqual(_verify(wrong_members).code, "invalid_members")

    def test_invalid_inputs_encoding_json_duplicates_and_nonfinite_fail_closed(self) -> None:
        verify = bundle.verify_creator_wallet_control_evidence_bundle_json
        self.assertEqual(verify(123).code, "invalid_input_type")  # type: ignore[arg-type]
        self.assertEqual(verify(b"\xff").code, "invalid_encoding")
        self.assertEqual(verify("{").code, "invalid_json")
        duplicate = (
            '{"bundle_version":"' + bundle.BUNDLE_VERSION + '",'
            '"members":[{"a":1,"a":2}]}'
        )
        self.assertEqual(verify(duplicate).code, "duplicate_key")
        nonfinite = (
            '{"bundle_version":"' + bundle.BUNDLE_VERSION + '",'
            '"members":[NaN]}'
        )
        self.assertEqual(verify(nonfinite).code, "invalid_json")

    def test_oversized_input_rejected_before_json_parsing(self) -> None:
        raw = b"{" + (b" " * bundle.MAX_BUNDLE_BYTES)
        with mock.patch.object(bundle.json, "loads") as loads:
            result = bundle.verify_creator_wallet_control_evidence_bundle_json(raw)
        self.assertEqual(result.code, "bundle_too_large")
        loads.assert_not_called()

    def test_non_object_or_failed_member_is_rejected(self) -> None:
        self.assertEqual(_verify(_payload([[]])).code, "member_invalid")
        raw = json.dumps(_payload(_members(1)), separators=(",", ":"))
        failed = SimpleNamespace(ok=False, evidence_sha256="")
        with mock.patch.object(
            bundle,
            "verify_creator_wallet_control_proof_evidence_json",
            return_value=failed,
        ):
            result = bundle.verify_creator_wallet_control_evidence_bundle_json(raw)
        self.assertEqual(result.code, "member_invalid")

    def test_duplicate_member_commitment_is_rejected(self) -> None:
        values = _members(2)
        raw = json.dumps(_payload(values), separators=(",", ":"))
        repeated = SimpleNamespace(ok=True, evidence_sha256="a" * 64)
        with mock.patch.object(
            bundle,
            "verify_creator_wallet_control_proof_evidence_json",
            return_value=repeated,
        ):
            result = bundle.verify_creator_wallet_control_evidence_bundle_json(raw)
        self.assertEqual(result.code, "duplicate_member")

    def test_duplicate_challenge_is_rejected(self) -> None:
        first = _member(1)
        second = copy.deepcopy(first)
        second["report"] = {"variant": 1}
        values = sorted([first, second], key=_digest)
        self.assertEqual(_verify(_payload(values)).code, "duplicate_challenge")

    def test_noncanonical_member_order_is_rejected_without_reordering(self) -> None:
        values = _members(3)
        reversed_values = list(reversed(values))
        original = copy.deepcopy(reversed_values)
        result = _verify(_payload(reversed_values))
        self.assertEqual(result.code, "noncanonical_member_order")
        self.assertEqual(reversed_values, original)

    def test_commitments_match_public_algorithms(self) -> None:
        values = _members(3)
        value = _payload(values)
        result = _verify(value)
        hashes = tuple(_digest(member) for member in values)
        body = {
            "bundle_version": bundle.BUNDLE_VERSION,
            "member_evidence_sha256": list(hashes),
        }
        expected_aggregate = hashlib.sha256(
            bundle.BUNDLE_DOMAIN + _canonical(body)
        ).hexdigest()
        self.assertTrue(result.ok)
        self.assertEqual(result.member_evidence_sha256, hashes)
        self.assertEqual(result.aggregate_commitment, expected_aggregate)
        self.assertEqual(
            result.bundle_sha256,
            hashlib.sha256(_canonical(value)).hexdigest(),
        )

    def test_formatting_is_deterministic_and_wrapper_matches(self) -> None:
        value = _payload(_members(2))
        compact = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        pretty = json.dumps(value, ensure_ascii=False, indent=2)
        with mock.patch.object(
            bundle,
            "verify_creator_wallet_control_proof_evidence_json",
            side_effect=_valid_result,
        ):
            first = bundle.verify_creator_wallet_control_evidence_bundle_json(compact)
            second = bundle.CreatorWalletControlEvidenceBundleVerifier.verify_json(pretty)
        self.assertEqual(first, second)

    def test_result_is_frozen_and_input_is_not_modified(self) -> None:
        value = _payload(_members(2))
        original = copy.deepcopy(value)
        result = _verify(value)
        self.assertEqual(value, original)
        with self.assertRaises(FrozenInstanceError):
            result.code = "changed"  # type: ignore[misc]

    def test_unexpected_exception_is_sanitized(self) -> None:
        raw = json.dumps(_payload(_members(1)), separators=(",", ":"))
        with mock.patch.object(
            bundle,
            "verify_creator_wallet_control_proof_evidence_json",
            side_effect=RuntimeError("private detail"),
        ):
            result = bundle.verify_creator_wallet_control_evidence_bundle_json(raw)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "internal_error")
        self.assertNotIn("private", repr(result))

    def test_production_core_has_no_io_network_or_private_key_imports(self) -> None:
        path = Path(bundle.__file__)
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertFalse(
            imports & {"os", "pathlib", "socket", "subprocess", "urllib", "requests"}
        )
        self.assertNotIn("open", calls)
        self.assertNotIn("Ed25519PrivateKey", text)

    def test_end_to_end_foundation29_to_31_with_ephemeral_key(self) -> None:
        from contextlib import redirect_stdout
        import io
        import tempfile
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from coin import creator_wallet_control_proof as proof
        from coin import creator_wallet_control_proof_cli as proof_cli
        from coin import creator_wallet_control_proof_evidence as evidence

        private_key = Ed25519PrivateKey.generate()
        public_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        public_key = public_bytes.hex()
        address = "L28" + hashlib.sha256(public_bytes).hexdigest()[:40]
        challenge = "1" * 64
        proof_value = {
            "proof_version": proof.PROOF_VERSION,
            "domain": proof.PROOF_DOMAIN,
            "challenge_id": challenge,
            "public_key": public_key,
            "address": address,
            "signature": "0" * 128,
        }
        proof_value["signature"] = private_key.sign(
            proof._signature_preimage(proof_value)
        ).hex()

        with mock.patch.object(proof, "FIXED_CREATOR_PUBLIC_KEY", public_key), \
             mock.patch.object(proof, "FIXED_CREATOR_ADDRESS", address), \
             tempfile.TemporaryDirectory() as directory:
            proof_path = Path(directory) / "proof.json"
            proof_path.write_text(json.dumps(proof_value, separators=(",", ":")))
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    proof_cli.main([str(proof_path), "--challenge-id", challenge]),
                    0,
                )
            evidence_value = {
                "evidence_version": evidence.EVIDENCE_VERSION,
                "expected_challenge_id": challenge,
                "proof": proof_value,
                "report": json.loads(output.getvalue()),
            }
            evidence_result = evidence.verify_creator_wallet_control_proof_evidence_json(
                json.dumps(evidence_value, separators=(",", ":"))
            )
            self.assertTrue(evidence_result.ok, evidence_result.code)
            result = bundle.verify_creator_wallet_control_evidence_bundle_json(
                json.dumps(_payload([evidence_value]), separators=(",", ":"))
            )

        self.assertTrue(result.ok, result.code)
        self.assertEqual(
            result.member_evidence_sha256,
            (evidence_result.evidence_sha256,),
        )


if __name__ == "__main__":
    unittest.main()
