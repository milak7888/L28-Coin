import ast
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from coin import creator_wallet_control_proof_evidence_cli as cli


def _result(
    *,
    ok=True,
    code="ok",
    checks=("proof_valid", "report_bound"),
    evidence_sha256="a" * 64,
):
    return SimpleNamespace(
        ok=ok,
        code=code,
        checks=checks,
        evidence_sha256=evidence_sha256,
    )


def _invoke(arguments, *, result=None, side_effect=None):
    stdout = io.StringIO()
    stderr = io.StringIO()

    patcher = mock.patch.object(
        cli,
        "verify_creator_wallet_control_proof_evidence_json",
        return_value=result,
        side_effect=side_effect,
    )
    with patcher as verifier, contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = cli.main(arguments)

    return exit_code, stdout.getvalue(), stderr.getvalue(), verifier


class CreatorWalletControlProofEvidenceCliTests(unittest.TestCase):
    def test_valid_evidence_file_success(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence_file = Path(directory) / "evidence.json"
            evidence_file.write_text("{}", encoding="utf-8")

            exit_code, output, error, verifier = _invoke(
                [str(evidence_file)],
                result=_result(),
            )

        self.assertEqual(exit_code, cli.EXIT_OK)
        self.assertEqual(error, "")
        verifier.assert_called_once_with(b"{}")

        report = json.loads(output)
        self.assertTrue(report["ok"])
        self.assertEqual(report["code"], "ok")
        self.assertEqual(report["evidence_sha256"], "a" * 64)

    def test_invalid_and_internal_results_use_stable_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence_file = Path(directory) / "evidence.json"
            evidence_file.write_text("{}", encoding="utf-8")

            invalid_exit, invalid_output, _, _ = _invoke(
                [str(evidence_file)],
                result=_result(ok=False, code="proof_invalid", checks=()),
            )
            internal_exit, internal_output, _, _ = _invoke(
                [str(evidence_file)],
                result=_result(ok=False, code="internal_error", checks=()),
            )

        self.assertEqual(invalid_exit, cli.EXIT_VERIFICATION)
        self.assertEqual(json.loads(invalid_output)["code"], "proof_invalid")
        self.assertEqual(internal_exit, cli.EXIT_INTERNAL)
        self.assertEqual(json.loads(internal_output)["code"], "internal_error")

    def test_missing_directory_and_symlink_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            regular_file = root / "regular.json"
            regular_file.write_text("{}", encoding="utf-8")
            symlink_file = root / "link.json"
            os.symlink(regular_file, symlink_file)

            for candidate in (
                root / "missing.json",
                root,
                symlink_file,
            ):
                with self.subTest(candidate=candidate):
                    exit_code, output, _, verifier = _invoke([str(candidate)])
                    self.assertEqual(exit_code, cli.EXIT_VERIFICATION)
                    self.assertEqual(json.loads(output)["code"], "path_invalid")
                    verifier.assert_not_called()

    def test_oversized_file_is_rejected_before_core_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence_file = Path(directory) / "oversized.json"
            with evidence_file.open("wb") as handle:
                handle.seek(cli.MAX_EVIDENCE_BYTES)
                handle.write(b"x")

            exit_code, output, _, verifier = _invoke([str(evidence_file)])

        self.assertEqual(exit_code, cli.EXIT_VERIFICATION)
        self.assertEqual(json.loads(output)["code"], "evidence_too_large")
        verifier.assert_not_called()

    def test_pretty_output_is_logically_equal(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence_file = Path(directory) / "evidence.json"
            evidence_file.write_text("{}", encoding="utf-8")

            compact_exit, compact, _, _ = _invoke(
                [str(evidence_file)],
                result=_result(),
            )
            pretty_exit, pretty, _, _ = _invoke(
                [str(evidence_file), "--pretty"],
                result=_result(),
            )

        self.assertEqual(compact_exit, cli.EXIT_OK)
        self.assertEqual(pretty_exit, cli.EXIT_OK)
        self.assertEqual(json.loads(compact), json.loads(pretty))
        self.assertNotEqual(compact, pretty)

    def test_report_fields_are_exact_and_report_id_is_body_bound(self):
        report = cli._report_for(_result())
        expected_fields = {
            "report_version",
            "ok",
            "code",
            "checks",
            "evidence_sha256",
            "report_id",
        }
        self.assertEqual(set(report), expected_fields)

        body = {key: value for key, value in report.items() if key != "report_id"}
        expected_id = hashlib.sha256(
            cli.REPORT_DOMAIN + cli._canonical_bytes(body)
        ).hexdigest()
        self.assertEqual(report["report_id"], expected_id)
        self.assertEqual(report, cli._report_for(_result()))

        changed = dict(body)
        changed["code"] = "proof_invalid"
        changed_id = hashlib.sha256(
            cli.REPORT_DOMAIN + cli._canonical_bytes(changed)
        ).hexdigest()
        self.assertNotEqual(expected_id, changed_id)

    def test_unexpected_cli_exception_is_sanitized(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence_file = Path(directory) / "evidence.json"
            evidence_file.write_text("{}", encoding="utf-8")

            exit_code, output, error, _ = _invoke(
                [str(evidence_file)],
                side_effect=RuntimeError("private detail"),
            )

        self.assertEqual(exit_code, cli.EXIT_INTERNAL)
        self.assertEqual(error, "")
        self.assertEqual(json.loads(output)["code"], "internal_error")
        self.assertNotIn("private detail", output)

    def test_usage_failures_are_sanitized(self):
        for arguments in ([], ["--unknown"]):
            with self.subTest(arguments=arguments):
                stdout = io.StringIO()
                stderr = io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as raised:
                        cli.main(arguments)

                self.assertEqual(raised.exception.code, cli.EXIT_USAGE)
                self.assertEqual(stdout.getvalue(), "")
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_production_cli_has_main_entrypoint_and_no_sensitive_imports(self):
        source = Path(cli.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)

        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        from_imports = {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }

        forbidden = {
            "socket",
            "subprocess",
            "urllib",
            "requests",
            "http",
            "cryptography",
        }
        self.assertFalse(imports & forbidden)
        self.assertFalse(from_imports & forbidden)
        self.assertNotIn("Ed25519PrivateKey", source)
        self.assertNotIn("load_wallet", source)
        self.assertNotIn("sign_entry", source)
        self.assertNotIn("transfer(", source)
        self.assertIn('if __name__ == "__main__":', source)


if __name__ == "__main__":
    unittest.main()
