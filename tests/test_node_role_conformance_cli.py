import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from coin import node_role_conformance_cli as cli


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PROFILE = ROOT / "docs" / "l28_core_p2p_security_profile_v0.1.json"


class NodeRoleConformanceCliTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads(CANONICAL_PROFILE.read_text(encoding="utf-8"))
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)

    def invoke(self, arguments):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = cli.main(arguments)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def write_profile(self, value, name="profile.json"):
        target = self.root / name
        target.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return target

    def test_valid_profile_cli_success(self):
        exit_code, stdout, stderr = self.invoke(
            ["--profile", str(CANONICAL_PROFILE)]
        )
        report = json.loads(stdout)
        self.assertEqual(exit_code, cli.EXIT_PASS)
        self.assertEqual(stderr, "")
        self.assertTrue(report["ok"])
        self.assertEqual(report["code"], "conformant")
        self.assertEqual(report["profile"], cli.PROFILE)
        self.assertEqual(report["cli_version"], cli.CLI_VERSION)
        self.assertEqual(report["report_version"], cli.REPORT_VERSION)
        self.assertEqual(len(report["report_id"]), 64)
        self.assertTrue(stdout.endswith("\n"))

    def test_valid_output_is_deterministic(self):
        first = self.invoke(["--profile", str(CANONICAL_PROFILE)])
        second = self.invoke(["--profile", str(CANONICAL_PROFILE)])
        self.assertEqual(first, second)

    def test_pretty_output_preserves_logical_report(self):
        compact = self.invoke(["--profile", str(CANONICAL_PROFILE)])
        pretty = self.invoke(["--profile", str(CANONICAL_PROFILE), "--pretty"])
        self.assertEqual(compact[0], pretty[0])
        self.assertEqual(json.loads(compact[1]), json.loads(pretty[1]))
        self.assertIn("\n  ", pretty[1])

    def test_report_id_is_deterministic_and_body_bound(self):
        result = cli._failure_result("usage_error", "arguments:invalid")
        report = cli.build_report(result)
        body = dict(report)
        report_id = body.pop("report_id")
        self.assertEqual(report_id, cli.compute_report_id(body))
        changed = dict(body)
        changed["detail"] = "changed"
        self.assertNotEqual(report_id, cli.compute_report_id(changed))

    def test_profile_argument_is_required(self):
        exit_code, stdout, stderr = self.invoke([])
        report = json.loads(stdout)
        self.assertEqual(exit_code, cli.EXIT_USAGE)
        self.assertEqual(stderr, "")
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "usage_error")
        self.assertEqual(report["detail"], "arguments:invalid")

    def test_unknown_argument_is_usage_failure(self):
        exit_code, stdout, stderr = self.invoke(["--unknown"])
        report = json.loads(stdout)
        self.assertEqual(exit_code, cli.EXIT_USAGE)
        self.assertEqual(stderr, "")
        self.assertEqual(report["code"], "usage_error")

    def test_missing_profile_path_is_verification_failure_and_sanitized(self):
        missing = self.root / "sensitive-name.json"
        exit_code, stdout, stderr = self.invoke(["--profile", str(missing)])
        report = json.loads(stdout)
        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertEqual(stderr, "")
        self.assertEqual(report["code"], "profile_read_failed")
        self.assertNotIn(str(missing), stdout)
        self.assertNotIn("sensitive-name", stdout)

    def test_invalid_profile_is_verification_failure(self):
        target = self.root / "invalid.json"
        target.write_text("{", encoding="utf-8")
        exit_code, stdout, stderr = self.invoke(["--profile", str(target)])
        report = json.loads(stdout)
        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertEqual(stderr, "")
        self.assertEqual(report["code"], "profile_json_invalid")

    def test_semantic_mutation_is_verification_failure(self):
        value = copy.deepcopy(self.profile)
        value["future_frame_requirements"]["reason_runtime_limits_undefined"] = "changed"
        target = self.write_profile(value)
        exit_code, stdout, stderr = self.invoke(["--profile", str(target)])
        report = json.loads(stdout)
        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertEqual(stderr, "")
        self.assertEqual(report["code"], "profile_semantic_mismatch")

    def test_core_internal_failure_uses_internal_exit(self):
        with mock.patch.object(
            cli,
            "verify_node_role_profile",
            return_value=cli._failure_result(
                "internal_error", "verification:internal_error"
            ),
        ):
            exit_code, stdout, stderr = self.invoke(
                ["--profile", str(CANONICAL_PROFILE)]
            )
        report = json.loads(stdout)
        self.assertEqual(exit_code, cli.EXIT_INTERNAL)
        self.assertEqual(stderr, "")
        self.assertEqual(report["code"], "internal_error")

    def test_unexpected_cli_exception_is_sanitized(self):
        with mock.patch.object(
            cli,
            "verify_node_role_profile",
            side_effect=RuntimeError("sensitive exception detail"),
        ):
            exit_code, stdout, stderr = self.invoke(
                ["--profile", str(CANONICAL_PROFILE)]
            )
        report = json.loads(stdout)
        self.assertEqual(exit_code, cli.EXIT_INTERNAL)
        self.assertEqual(stderr, "")
        self.assertEqual(report["code"], "cli_internal_error")
        self.assertEqual(report["detail"], "cli:internal_error")
        self.assertNotIn("sensitive", stdout)

    def test_report_fields_are_exact(self):
        exit_code, stdout, _ = self.invoke(["--profile", str(CANONICAL_PROFILE)])
        self.assertEqual(exit_code, cli.EXIT_PASS)
        self.assertEqual(
            set(json.loads(stdout)),
            {
                "checks",
                "cli_version",
                "code",
                "detail",
                "ok",
                "profile",
                "profile_sha256",
                "profile_version",
                "report_id",
                "report_version",
            },
        )


if __name__ == "__main__":
    unittest.main()
