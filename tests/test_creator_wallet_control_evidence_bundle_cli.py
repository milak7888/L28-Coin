from __future__ import annotations

import ast
from contextlib import redirect_stderr, redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from coin import creator_wallet_control_evidence_bundle as core
from coin import creator_wallet_control_evidence_bundle_cli as cli


def _success_result() -> core.CreatorWalletControlEvidenceBundleResult:
    return core.CreatorWalletControlEvidenceBundleResult(
        ok=True,
        code="ok",
        checks=core.SUCCESS_CHECKS,
        bundle_sha256="a" * 64,
        aggregate_commitment="b" * 64,
        member_evidence_sha256=("c" * 64, "d" * 64),
    )


def _invoke(path: Path, result, *, pretty: bool = False):
    output = io.StringIO()
    arguments = [str(path)] + (["--pretty"] if pretty else [])
    with redirect_stdout(output), mock.patch.object(
        cli,
        "verify_creator_wallet_control_evidence_bundle_json",
        return_value=result,
    ) as verifier:
        return_code = cli.run(arguments)
    return return_code, json.loads(output.getvalue()), verifier


class CreatorWalletControlEvidenceBundleCliTests(unittest.TestCase):
    def test_valid_bundle_file_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bundle.json"
            path.write_bytes(b"{}")
            return_code, report, verifier = _invoke(path, _success_result())
        self.assertEqual(return_code, cli.EXIT_OK)
        self.assertTrue(report["ok"])
        self.assertEqual(report["code"], "ok")
        self.assertEqual(report["member_count"], 2)
        self.assertEqual(tuple(report.keys()), cli.REPORT_FIELDS)
        verifier.assert_called_once_with(b"{}")

    def test_verification_failure_uses_verification_exit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bundle.json"
            path.write_text("{}", encoding="utf-8")
            failed = core.CreatorWalletControlEvidenceBundleResult(
                False,
                "member_invalid",
            )
            return_code, report, _ = _invoke(path, failed)
        self.assertEqual(return_code, cli.EXIT_VERIFICATION_FAILED)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "member_invalid")

    def test_report_fields_and_report_id_are_body_bound(self) -> None:
        report = cli._build_report(_success_result())
        self.assertEqual(tuple(report.keys()), cli.REPORT_FIELDS)
        body = {field: report[field] for field in cli.REPORT_BODY_FIELDS}
        expected = hashlib.sha256(
            cli.REPORT_DOMAIN + cli._canonical_bytes(body)
        ).hexdigest()
        self.assertEqual(report["report_id"], expected)
        changed = copy.deepcopy(body)
        changed["member_count"] = 3
        self.assertNotEqual(cli._report_id(changed), report["report_id"])

    def test_pretty_and_compact_outputs_are_logically_equal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bundle.json"
            path.write_bytes(b"{}")
            compact_code, compact, _ = _invoke(path, _success_result())
            pretty_code, pretty, _ = _invoke(path, _success_result(), pretty=True)
        self.assertEqual(compact_code, pretty_code)
        self.assertEqual(compact, pretty)

    def test_missing_directory_and_symlink_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.json"
            target.write_bytes(b"{}")
            link = root / "link.json"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symbolic links unavailable")
            for path in (root / "missing.json", root, link):
                with self.subTest(path=path):
                    return_code, report, verifier = _invoke(
                        path,
                        _success_result(),
                    )
                    self.assertEqual(return_code, cli.EXIT_USAGE_OR_INPUT)
                    self.assertEqual(report["code"], "input_path_invalid")
                    verifier.assert_not_called()

    def test_oversized_file_rejected_before_verification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.json"
            path.write_bytes(b"x" * (core.MAX_BUNDLE_BYTES + 1))
            return_code, report, verifier = _invoke(path, _success_result())
        self.assertEqual(return_code, cli.EXIT_USAGE_OR_INPUT)
        self.assertEqual(report["code"], "input_too_large")
        verifier.assert_not_called()

    def test_unexpected_exception_is_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bundle.json"
            path.write_bytes(b"{}")
            output = io.StringIO()
            with redirect_stdout(output), mock.patch.object(
                cli,
                "verify_creator_wallet_control_evidence_bundle_json",
                side_effect=RuntimeError("private detail"),
            ):
                return_code = cli.run([str(path)])
        report = json.loads(output.getvalue())
        self.assertEqual(return_code, cli.EXIT_INTERNAL)
        self.assertEqual(report["code"], "internal_error")
        self.assertNotIn("private", output.getvalue())

    def test_usage_failures_are_argparse_exit_two(self) -> None:
        for arguments in ([], ["--pretty"]):
            with self.subTest(arguments=arguments):
                with redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        cli.run(arguments)
                self.assertEqual(raised.exception.code, 2)

    def test_production_cli_has_main_and_no_network_imports(self) -> None:
        path = Path(cli.__file__)
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        functions = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertFalse(
            imports & {"socket", "subprocess", "urllib", "requests", "http"}
        )
        self.assertIn("run", functions)
        self.assertIn("main", functions)
        self.assertNotIn("Ed25519PrivateKey", text)


if __name__ == "__main__":
    unittest.main()
