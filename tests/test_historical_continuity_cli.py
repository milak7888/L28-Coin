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


class ManifestIntegrityCliTests(unittest.TestCase):
    def run_candidate(self, candidate, path):
        path.write_text(json.dumps(candidate), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-B", "-m", "coin.historical_continuity_cli",
             "--manifest", str(path)], cwd=ROOT, capture_output=True, text=True,
            check=False, timeout=15,
        )
        report = json.loads(result.stdout)
        self.assertFalse(report["ARTIFACT_BYTES_VERIFIED"])
        self.assertFalse(report["CANONICAL_ACCEPTANCE"])
        self.assertFalse(report["HISTORICAL_POLICY_AUTHENTICATED"])
        self.assertEqual(report["verification_scope"], "pinned_manifest_metadata_only")
        self.assertEqual(report["reference_next_canonical_height"], 100878)
        report_id = report.pop("report_id")
        self.assertEqual(report_id, cli.compute_report_id(report))
        return result, report

    def test_integrity_cli_all_22_reproduced_leaf_false_passes(self):
        manifest = json.loads(CANONICAL_MANIFEST.read_bytes())
        both = ["audit_date", "consolidation.records", "parent_graph.dag_leaf_count",
                "parent_graph.final_lock_parent_path_length",
                "preserved_snapshot.claimed_timestamp", "preserved_snapshot.final_entry_height",
                "preserved_snapshot.last_issuance_height", "preserved_snapshot.size_bytes",
                "raw_dag.size_bytes"]
        alter_only = ["consolidation.sha256", "preserved_snapshot.final_entry_hash",
                      "preserved_snapshot.sha256", "raw_dag.sha256"]
        cases = [(field, action) for field in both for action in ["alter", "delete"]]
        cases += [(field, "alter") for field in alter_only]
        self.assertEqual(len(cases), 22)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            for dotted, action in cases:
                with self.subTest(field=dotted, action=action):
                    candidate = copy.deepcopy(manifest)
                    parts = dotted.split(".")
                    parent = candidate if len(parts) == 1 else candidate[parts[0]]
                    old = parent[parts[-1]]
                    if action == "delete":
                        del parent[parts[-1]]
                    else:
                        parent[parts[-1]] = old + 1 if type(old) is int else "f" * 64
                    result, report = self.run_candidate(candidate, path)
                    self.assertEqual(result.returncode, 1)
                    self.assertFalse(report["MANIFEST_METADATA_VALID"])

    def test_integrity_cli_positive_and_correlated_supply_treasury_counts(self):
        manifest = json.loads(CANONICAL_MANIFEST.read_bytes())
        changes = [
            {"economics.treasury_lock_commitment": 1,
             "economics.derived_unlocked_amount": 2824583},
            {"economics.missing_height_count": 28783,
             "economics.missing_height_implied_amount": 805924,
             "economics.historical_declared_supply": 2824612,
             "economics.derived_unlocked_amount": 2324612},
            {"raw_dag.physical_records": 102264,
             "raw_dag.extra_candidates_not_selected": 30168},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            result, report = self.run_candidate(manifest, path)
            self.assertEqual(result.returncode, 0)
            self.assertTrue(report["MANIFEST_METADATA_VALID"])
            for updates in changes:
                candidate = copy.deepcopy(manifest)
                for dotted, value in updates.items():
                    group, field = dotted.split(".")
                    candidate[group][field] = value
                result, report = self.run_candidate(candidate, path)
                self.assertEqual(result.returncode, 1)
                self.assertFalse(report["MANIFEST_METADATA_VALID"])


class HistoricalPowCliTests(unittest.TestCase):
    def run_pow_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, "-B", "-m", "coin.historical_continuity_cli", *arguments],
            cwd=ROOT, capture_output=True, text=True, timeout=15, check=False,
        )

    def test_pow_cli_requires_both_paths_and_exclusive_mode(self):
        for args in [("--raw-dag", "raw"), ("--snapshot", "snapshot"),
                     ("--manifest", "manifest", "--snapshot", "snapshot"),
                     ("--manifest", "manifest", "--raw-dag", "raw", "--snapshot", "snapshot")]:
            with self.subTest(args=args):
                result = self.run_pow_cli(*args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")

    def test_pow_cli_adversarial_inputs_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "raw.jsonl"
            snapshot = Path(directory) / "snapshot.jsonl"
            snapshot.write_bytes(b'{}\n')
            for data in [b'', b'{}\n', b'{', b'\xff', b'{"hash":"forged"}\n',
                         b'{"nonce":1,"nonce":2}\n', b'{}\n{}\n']:
                raw.write_bytes(data)
                result = self.run_pow_cli("--raw-dag", str(raw), "--snapshot", str(snapshot))
                report = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stderr, "")
                self.assertEqual(report["code"], "artifact_hash_mismatch")
                for flag in ["HASH_VALID", "RECORDED_DIFFICULTY_VALID",
                             "HISTORICAL_POLICY_AUTHENTICATED", "CANONICAL_ACCEPTANCE"]:
                    self.assertIs(report[flag], False)
                identifier = report.pop("report_id")
                self.assertEqual(identifier, cli.compute_report_id(report))

    def test_pow_cli_internal_failure_is_sanitized_and_blocked(self):
        with mock.patch.object(cli, "verify_pow_artifacts", side_effect=RuntimeError("not-for-output")):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = cli.main(["--raw-dag", "raw", "--snapshot", "snapshot"])
        report = json.loads(output.getvalue())
        self.assertEqual(status, 3)
        self.assertFalse(report["CANONICAL_ACCEPTANCE"])
        self.assertFalse(report["HASH_VALID"])
        self.assertNotIn("not-for-output", output.getvalue())


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
