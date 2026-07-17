from __future__ import annotations

import ast
from contextlib import redirect_stderr, redirect_stdout
import copy
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from coin import node_role_model as model
from coin import node_role_scenario as scenario
from coin import node_role_scenario_suite as suite
from coin import node_role_scenario_suite_cli as cli
from coin import node_role_transcript as transcript


def _scenario(role: str, requested_states: list[str]) -> dict[str, object]:
    return {
        "scenario_version": scenario.SCENARIO_VERSION,
        "model_version": model.MODEL_VERSION,
        "transcript_version": transcript.TRANSCRIPT_VERSION,
        "role": role,
        "requested_states": requested_states,
    }


def _canonical_suite() -> dict[str, object]:
    core_sequences = [
        [
            "CANONICAL_READY_RESERVED",
            "RUNNING_RESERVED",
            "EVIDENCE_ONLY",
            "PAUSED",
            "STOPPED",
        ],
        ["DISPOSABLE_TEST_READY", "PAUSED", "STOPPED"],
        ["PAUSED", "STOPPED"],
        ["FAILED", "STOPPED"],
        ["EVIDENCE_ONLY", "FAILED", "STOPPED"],
        ["DISPOSABLE_TEST_READY", "FAILED", "STOPPED"],
        ["PAUSED", "FAILED", "STOPPED"],
    ]
    p2p_sequences = [
        ["LISTENING_RESERVED", "CONFIGURED", "PAUSED", "STOPPED"],
        ["PAUSED", "STOPPED"],
        ["FAILED", "STOPPED"],
        ["CONFIGURED", "FAILED", "STOPPED"],
        ["PAUSED", "FAILED", "STOPPED"],
    ]
    cases = []
    for index, states in enumerate(core_sequences):
        cases.append(
            {
                "case_id": f"core-{index}",
                "scenario": _scenario(model.CORE_ROLE, states),
            }
        )
    for index, states in enumerate(p2p_sequences):
        cases.append(
            {
                "case_id": f"p2p-{index}",
                "scenario": _scenario(model.P2P_ROLE, states),
            }
        )
    return {
        "suite_version": suite.SUITE_VERSION,
        "scenario_version": scenario.SCENARIO_VERSION,
        "model_version": model.MODEL_VERSION,
        "transcript_version": transcript.TRANSCRIPT_VERSION,
        "cases": cases,
    }


def _encoded(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _run_main(arguments: list[str]) -> tuple[int, dict[str, object] | None, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = cli.main(arguments)
    output = stdout.getvalue()
    report = json.loads(output) if output else None
    return exit_code, report, stderr.getvalue()


class NodeRoleScenarioSuiteCliTests(unittest.TestCase):
    def _write_suite(self, directory: str, value: object | None = None) -> Path:
        path = Path(directory) / "suite.json"
        path.write_text(
            _encoded(_canonical_suite() if value is None else value),
            encoding="utf-8",
        )
        return path

    def test_valid_suite_cli_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_suite(directory)
            exit_code, report, stderr = _run_main(["--suite", str(path)])

        self.assertEqual(exit_code, cli.EXIT_PASS)
        self.assertEqual(stderr, "")
        self.assertIsNotNone(report)
        self.assertTrue(report["ok"])
        self.assertEqual(report["code"], "suite_valid")
        self.assertEqual(report["case_count"], 12)
        self.assertEqual(report["roles"], [model.CORE_ROLE, model.P2P_ROLE])

    def test_valid_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_suite(directory)
            first = _run_main(["--suite", str(path)])
            second = _run_main(["--suite", str(path)])

        self.assertEqual(first, second)

    def test_pretty_output_preserves_logical_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_suite(directory)
            compact = _run_main(["--suite", str(path)])
            pretty = _run_main(["--suite", str(path), "--pretty"])

        self.assertEqual(compact[0], cli.EXIT_PASS)
        self.assertEqual(pretty[0], cli.EXIT_PASS)
        self.assertEqual(compact[1], pretty[1])

    def test_suite_argument_is_required(self) -> None:
        exit_code, report, stderr = _run_main([])

        self.assertEqual(exit_code, cli.EXIT_USAGE)
        self.assertIsNone(report)
        self.assertIn("--suite", stderr)

    def test_unknown_argument_is_usage_failure(self) -> None:
        exit_code, report, stderr = _run_main(["--unknown"])

        self.assertEqual(exit_code, cli.EXIT_USAGE)
        self.assertIsNone(report)
        self.assertTrue(stderr)

    def test_incomplete_suite_is_verification_failure(self) -> None:
        value = _canonical_suite()
        value["cases"] = [
            item for item in value["cases"]
            if item["scenario"]["role"] == model.CORE_ROLE
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_suite(directory, value)
            exit_code, report, _ = _run_main(["--suite", str(path)])

        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "role_coverage_incomplete")

    def test_missing_path_is_sanitized_verification_failure(self) -> None:
        path = "/definitely/not/a/real/l28-suite-secret.json"
        exit_code, report, _ = _run_main(["--suite", path])

        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "invalid_json")
        self.assertEqual(report["detail"], "suite_file_unavailable")
        self.assertNotIn(path, json.dumps(report))

    def test_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            exit_code, report, _ = _run_main(["--suite", directory])

        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertEqual(report["detail"], "suite_path_not_regular_file")

    def test_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = self._write_suite(directory)
            link = Path(directory) / "suite-link.json"
            os.symlink(target, link)
            exit_code, report, _ = _run_main(["--suite", str(link)])

        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertEqual(report["detail"], "suite_path_not_regular_file")

    def test_oversized_file_is_rejected_before_payload_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.json"
            path.write_bytes(b" " * (suite.MAX_SUITE_BYTES + 1))
            with mock.patch.object(
                cli,
                "verify_scenario_suite_json",
                side_effect=AssertionError("payload parser must not run"),
            ):
                result = cli.verify_suite_path(str(path))

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "suite_too_large")
        self.assertEqual(result.detail, "suite_file_too_large")

    def test_report_fields_are_exact(self) -> None:
        result = suite.verify_scenario_suite_json(_encoded(_canonical_suite()))
        report = cli.build_report(result)

        self.assertEqual(frozenset(report), cli.REPORT_FIELDS)
        self.assertEqual(report["profile"], cli.PROFILE)
        self.assertEqual(report["report_version"], cli.REPORT_VERSION)
        self.assertEqual(report["cli_version"], cli.CLI_VERSION)
        self.assertEqual(len(report["cases"]), 12)

    def test_report_id_is_deterministic_and_body_bound(self) -> None:
        result = suite.verify_scenario_suite_json(_encoded(_canonical_suite()))
        report = cli.build_report(result)

        self.assertEqual(report["report_id"], cli.compute_report_id(report))
        self.assertEqual(report, cli.build_report(result))

        mutated = copy.deepcopy(report)
        mutated["case_count"] += 1
        self.assertNotEqual(
            report["report_id"],
            cli.compute_report_id(mutated),
        )

    def test_core_internal_result_uses_internal_exit(self) -> None:
        valid = suite.verify_scenario_suite_json(_encoded(_canonical_suite()))
        internal = replace(
            valid,
            ok=False,
            code="internal_error",
            detail="internal_failure",
            checks=(),
        )
        with mock.patch.object(cli, "verify_suite_path", return_value=internal):
            exit_code, report, _ = _run_main(["--suite", "ignored.json"])

        self.assertEqual(exit_code, cli.EXIT_INTERNAL)
        self.assertEqual(report["code"], "internal_error")

    def test_unexpected_cli_exception_is_sanitized(self) -> None:
        with mock.patch.object(
            cli,
            "verify_suite_path",
            side_effect=RuntimeError("private secret"),
        ):
            exit_code, report, _ = _run_main(["--suite", "ignored.json"])

        self.assertEqual(exit_code, cli.EXIT_INTERNAL)
        self.assertEqual(report["code"], "cli_internal_error")
        self.assertEqual(report["detail"], "internal_failure")
        self.assertNotIn("private secret", json.dumps(report))

    def test_production_cli_has_main_entrypoint_and_no_network_imports(self) -> None:
        path = Path(cli.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports: set[str] = set()
        calls: set[str] = set()
        main_guard = False

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
            elif isinstance(node, ast.If):
                rendered = ast.unparse(node.test)
                if "__name__" in rendered and "__main__" in rendered:
                    main_guard = True

        self.assertTrue(main_guard)
        self.assertFalse(
            imports
            & {
                "asyncio",
                "http",
                "requests",
                "socket",
                "subprocess",
                "urllib",
            }
        )
        self.assertFalse(calls & {"connect", "listen", "glob", "rglob", "walk"})


if __name__ == "__main__":
    unittest.main()
