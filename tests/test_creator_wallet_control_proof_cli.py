import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import creator_wallet_control_proof as proof
from coin import creator_wallet_control_proof_cli as cli


CHALLENGE = "c" * 64


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


def _run(argv):
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
        code = cli.main(argv)
    return code, json.loads(stdout.getvalue())


class CreatorWalletControlProofCliTests(unittest.TestCase):
    def test_valid_proof_file_success(self):
        value = _signed_proof()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proof.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with mock.patch.object(proof, "FIXED_CREATOR_PUBLIC_KEY", value["public_key"]), mock.patch.object(
                proof, "FIXED_CREATOR_ADDRESS", value["address"]
            ):
                code, report = _run([str(path), "--challenge-id", CHALLENGE])

        self.assertEqual(code, 0)
        self.assertTrue(report["ok"])
        self.assertEqual(report["code"], "ok")
        self.assertEqual(report["checks"], list(proof.SUCCESS_CHECKS))
        self.assertFalse(report["runtime_activation"])
        self.assertFalse(report["wallet_loaded"])
        self.assertFalse(report["private_key_read"])
        self.assertFalse(report["signature_created"])
        self.assertFalse(report["transfer_created"])
        self.assertFalse(report["ledger_mutated"])
        self.assertFalse(report["network_access"])

    def test_invalid_proof_is_verification_failure(self):
        value = _signed_proof()
        value["challenge_id"] = "d" * 64
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proof.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            code, report = _run([str(path), "--challenge-id", CHALLENGE])

        self.assertEqual(code, 1)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "challenge_invalid")

    def test_missing_directory_and_symlink_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "missing.json"
            directory = root / "dir"
            directory.mkdir()
            target = root / "target.json"
            target.write_text("{}", encoding="utf-8")
            symlink = root / "link.json"
            symlink.symlink_to(target)

            for path in (missing, directory, symlink):
                code, report = _run([str(path), "--challenge-id", CHALLENGE])
                self.assertEqual(code, 1)
                self.assertFalse(report["ok"])
                self.assertEqual(report["code"], "path_not_regular_file")

    def test_oversized_file_is_rejected_before_core_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proof.json"
            path.write_text("{" + (" " * proof.MAX_PROOF_BYTES) + "}", encoding="utf-8")
            with mock.patch.object(cli, "verify_creator_wallet_control_proof_json") as verifier:
                code, report = _run([str(path), "--challenge-id", CHALLENGE])

        verifier.assert_not_called()
        self.assertEqual(code, 1)
        self.assertEqual(report["code"], "proof_too_large")

    def test_usage_failures_are_sanitized(self):
        self.assertNotEqual(cli.main([]), 0)
        self.assertNotEqual(cli.main(["proof.json", "--unknown"]), 0)

    def test_internal_result_uses_internal_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proof.json"
            path.write_text("{}", encoding="utf-8")
            with mock.patch.object(
                cli,
                "verify_creator_wallet_control_proof_json",
                return_value=proof.CreatorWalletControlProofResult(False, "internal_error"),
            ):
                code, report = _run([str(path), "--challenge-id", CHALLENGE])

        self.assertEqual(code, 2)
        self.assertEqual(report["code"], "internal_error")

    def test_unexpected_cli_exception_is_sanitized(self):
        with mock.patch.object(cli, "_read_explicit_file", side_effect=RuntimeError("private detail")):
            code, report = _run(["proof.json", "--challenge-id", CHALLENGE])

        self.assertEqual(code, 2)
        self.assertEqual(report["code"], "internal_error")

    def test_report_id_is_deterministic_and_body_bound(self):
        report = cli._build_report(
            ok=False,
            code="challenge_invalid",
            checks=(),
            proof_sha256="",
        )
        again = cli._build_report(
            ok=False,
            code="challenge_invalid",
            checks=(),
            proof_sha256="",
        )
        changed = dict(report)
        changed["code"] = "identity_invalid"

        self.assertEqual(report, again)
        self.assertEqual(report["report_id"], cli._report_id(report))
        self.assertNotEqual(report["report_id"], cli._report_id(changed))

    def test_pretty_output_is_logically_equal(self):
        value = _signed_proof()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proof.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with mock.patch.object(proof, "FIXED_CREATOR_PUBLIC_KEY", value["public_key"]), mock.patch.object(
                proof, "FIXED_CREATOR_ADDRESS", value["address"]
            ):
                compact = _run([str(path), "--challenge-id", CHALLENGE])[1]
                pretty = _run([str(path), "--challenge-id", CHALLENGE, "--pretty"])[1]

        self.assertEqual(compact, pretty)

    def test_production_cli_has_no_network_or_wallet_imports(self):
        import ast

        source = Path(cli.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }

        self.assertFalse(imports & {"socket", "subprocess", "urllib", "requests"})
