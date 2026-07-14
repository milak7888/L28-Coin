import contextlib
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from coin import historical_continuity_cli as cli
from coin.historical_continuity_verifier import ContinuityVerifyResult


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_MANIFEST = (
    ROOT / "docs" / "l28_historical_continuity_manifest_v0.1.json"
)


class HistoricalContinuityCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.temp_path = Path(self.temp.name)

    def run_cli(self, *arguments):
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "coin.historical_continuity_cli",
                *arguments,
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def parse_stdout(self, completed):
        self.assertTrue(completed.stdout.endswith("\n"))
        return json.loads(completed.stdout)

    def test_report_id_is_deterministic_and_body_bound(self):
        result = ContinuityVerifyResult(
            ok=True,
            code="manifest_valid",
            manifest_sha256="a" * 64,
            manifest_version="l28-historical-continuity/v0.1",
            checks=("identity",),
        )

        first = cli.build_report(result)
        second = cli.build_report(result)

        self.assertEqual(first, second)
        self.assertEqual(len(first["report_id"]), 64)

        changed = cli.build_report(
            ContinuityVerifyResult(
                ok=False,
                code="invariant_violation",
                manifest_sha256="a" * 64,
                manifest_version="l28-historical-continuity/v0.1",
                detail="changed",
            )
        )
        self.assertNotEqual(first["report_id"], changed["report_id"])

    def test_valid_manifest_cli_success(self):
        completed = self.run_cli(
            "--manifest",
            str(CANONICAL_MANIFEST),
        )
        report = self.parse_stdout(completed)

        self.assertEqual(completed.returncode, cli.EXIT_PASS)
        self.assertEqual(completed.stderr, "")
        self.assertTrue(report["ok"])
        self.assertEqual(report["code"], "manifest_valid")
        self.assertEqual(report["profile"], cli.PROFILE)
        self.assertEqual(report["report_version"], cli.REPORT_VERSION)
        self.assertEqual(len(report["checks"]), 9)
        self.assertEqual(len(report["report_id"]), 64)

    def test_valid_output_is_deterministic(self):
        first = self.run_cli(
            "--manifest",
            str(CANONICAL_MANIFEST),
        )
        second = self.run_cli(
            "--manifest",
            str(CANONICAL_MANIFEST),
        )

        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.stderr, second.stderr)

    def test_pretty_output_preserves_logical_report(self):
        compact = self.run_cli(
            "--manifest",
            str(CANONICAL_MANIFEST),
        )
        pretty = self.run_cli(
            "--manifest",
            str(CANONICAL_MANIFEST),
            "--pretty",
        )

        self.assertEqual(compact.returncode, 0)
        self.assertEqual(pretty.returncode, 0)
        self.assertEqual(
            json.loads(compact.stdout),
            json.loads(pretty.stdout),
        )
        self.assertGreater(len(pretty.stdout.splitlines()), 1)

    def test_missing_manifest_path_is_usage_failure(self):
        missing = self.temp_path / "not-present.json"
        completed = self.run_cli("--manifest", str(missing))
        report = self.parse_stdout(completed)

        self.assertEqual(completed.returncode, cli.EXIT_USAGE)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "manifest_not_found")
        self.assertNotIn(str(missing), completed.stdout)

    def test_invalid_json_is_verification_failure(self):
        path = self.temp_path / "invalid.json"
        path.write_text("{", encoding="utf-8")

        completed = self.run_cli("--manifest", str(path))
        report = self.parse_stdout(completed)

        self.assertEqual(completed.returncode, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "invalid_json")
        self.assertEqual(len(report["manifest_sha256"]), 64)

    def test_invariant_failure_is_verification_failure(self):
        value = json.loads(CANONICAL_MANIFEST.read_text(encoding="utf-8"))
        value["mining"]["active"] = True

        path = self.temp_path / "unsafe.json"
        path.write_text(
            json.dumps(value, sort_keys=True),
            encoding="utf-8",
        )

        completed = self.run_cli("--manifest", str(path))
        report = self.parse_stdout(completed)

        self.assertEqual(completed.returncode, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "invariant_violation")
        self.assertFalse(report["ok"])
        self.assertEqual(report["detail"], "expected:mining.active")

    def test_manifest_argument_is_required(self):
        completed = self.run_cli()

        self.assertEqual(completed.returncode, cli.EXIT_USAGE)
        self.assertEqual(completed.stdout, "")
        self.assertIn("required", completed.stderr.lower())

    def test_internal_exception_is_sanitized(self):
        secret_exception_text = "must-not-be-emitted"

        with mock.patch.object(
            cli,
            "verify_manifest",
            side_effect=RuntimeError(secret_exception_text),
        ):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = cli.main(
                    ["--manifest", "unused-public-path.json"]
                )

        rendered = output.getvalue()
        report = json.loads(rendered)

        self.assertEqual(exit_code, cli.EXIT_INTERNAL)
        self.assertEqual(report["code"], "internal_error")
        self.assertEqual(report["detail"], "unexpected_internal_error")
        self.assertNotIn(secret_exception_text, rendered)


if __name__ == "__main__":
    unittest.main()
