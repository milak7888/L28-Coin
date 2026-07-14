"""Tests for the offline inert node-role scenario CLI."""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from coin import node_role_scenario as scenario
from coin import node_role_scenario_cli as cli


def _document(role: str = scenario.CORE_ROLE) -> dict[str, object]:
    requested_states = (
        ["PAUSED", "STOPPED"]
        if role == scenario.CORE_ROLE
        else ["CONFIGURED", "PAUSED", "STOPPED"]
    )
    return {
        "scenario_version": scenario.SCENARIO_VERSION,
        "model_version": scenario.MODEL_VERSION,
        "transcript_version": scenario.TRANSCRIPT_VERSION,
        "role": role,
        "requested_states": requested_states,
    }


class NodeRoleScenarioCliTests(unittest.TestCase):
    def _write_document(
        self,
        directory: str,
        document: object,
        name: str = "scenario.json",
    ) -> Path:
        path = Path(directory) / name
        path.write_text(
            json.dumps(document, separators=(",", ":"), sort_keys=True),
            encoding="utf-8",
        )
        return path

    def _run(
        self,
        arguments: list[str],
    ) -> tuple[int, dict[str, object], str]:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = cli.main(arguments)
        text = output.getvalue()
        return exit_code, json.loads(text), text

    def test_valid_core_and_p2p_cli_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for role in (scenario.CORE_ROLE, scenario.P2P_ROLE):
                with self.subTest(role=role):
                    path = self._write_document(
                        directory,
                        _document(role),
                        name=f"{role}.json",
                    )
                    exit_code, report, _ = self._run(
                        ["--scenario", str(path)]
                    )

                    self.assertEqual(exit_code, cli.EXIT_PASS)
                    self.assertTrue(report["ok"])
                    self.assertEqual(report["code"], "scenario_valid")
                    self.assertEqual(report["role"], role)
                    self.assertEqual(report["final_state"], "STOPPED")
                    self.assertEqual(
                        report["transcript_verification_code"],
                        "transcript_valid",
                    )
                    self.assertIsInstance(report["transcript"], dict)
                    self.assertEqual(report["transcript"]["role"], role)

    def test_valid_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_document(directory, _document())
            first_code, first_report, first_text = self._run(
                ["--scenario", str(path)]
            )
            second_code, second_report, second_text = self._run(
                ["--scenario", str(path)]
            )

        self.assertEqual(first_code, cli.EXIT_PASS)
        self.assertEqual(second_code, cli.EXIT_PASS)
        self.assertEqual(first_report, second_report)
        self.assertEqual(first_text, second_text)

    def test_pretty_output_preserves_logical_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_document(directory, _document())
            compact_code, compact_report, compact_text = self._run(
                ["--scenario", str(path)]
            )
            pretty_code, pretty_report, pretty_text = self._run(
                ["--scenario", str(path), "--pretty"]
            )

        self.assertEqual(compact_code, cli.EXIT_PASS)
        self.assertEqual(pretty_code, cli.EXIT_PASS)
        self.assertEqual(compact_report, pretty_report)
        self.assertNotEqual(compact_text, pretty_text)

    def test_report_fields_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_document(directory, _document())
            exit_code, report, _ = self._run(
                ["--scenario", str(path)]
            )

        self.assertEqual(exit_code, cli.EXIT_PASS)
        self.assertEqual(frozenset(report), cli.REPORT_FIELDS)
        self.assertEqual(report["profile"], cli.PROFILE)
        self.assertEqual(report["report_version"], cli.REPORT_VERSION)
        self.assertEqual(report["cli_version"], cli.CLI_VERSION)
        self.assertEqual(report["scenario_version"], scenario.SCENARIO_VERSION)
        self.assertEqual(report["model_version"], scenario.MODEL_VERSION)
        self.assertEqual(report["transcript_version"], scenario.TRANSCRIPT_VERSION)
        self.assertEqual(report["runner_version"], scenario.RUNNER_VERSION)

    def test_report_id_is_deterministic_and_body_bound(self) -> None:
        result = scenario.run_scenario_json(json.dumps(_document()))
        report = cli.build_report(result)

        self.assertEqual(report["report_id"], cli.compute_report_id(report))

        mutated = dict(report)
        mutated["role"] = scenario.P2P_ROLE
        self.assertNotEqual(
            report["report_id"],
            cli.compute_report_id(mutated),
        )

    def test_incomplete_scenario_is_verification_failure(self) -> None:
        document = _document()
        document["requested_states"] = ["PAUSED"]

        with tempfile.TemporaryDirectory() as directory:
            path = self._write_document(directory, document)
            exit_code, report, _ = self._run(
                ["--scenario", str(path)]
            )

        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "terminal_state_required")
        self.assertEqual(report["final_state"], "PAUSED")
        self.assertIsInstance(report["transcript"], dict)

    def test_missing_path_is_sanitized_verification_failure(self) -> None:
        missing = "/definitely/not/present/private-scenario.json"
        exit_code, report, text = self._run(["--scenario", missing])

        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "path_invalid")
        self.assertNotIn(missing, text)

    def test_scenario_argument_is_required(self) -> None:
        exit_code, report, _ = self._run([])

        self.assertEqual(exit_code, cli.EXIT_USAGE)
        self.assertEqual(report["code"], "usage_error")

    def test_unknown_argument_is_usage_failure(self) -> None:
        exit_code, report, _ = self._run(["--unknown"])

        self.assertEqual(exit_code, cli.EXIT_USAGE)
        self.assertEqual(report["code"], "usage_error")

    def test_oversized_file_is_rejected_before_payload_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.json"
            path.write_bytes(b"{" + (b" " * scenario.MAX_SCENARIO_BYTES))
            exit_code, report, _ = self._run(
                ["--scenario", str(path)]
            )

        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "scenario_too_large")
        self.assertEqual(report["scenario_sha256"], "")

    def test_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = self._write_document(directory, _document())
            link = Path(directory) / "link.json"
            try:
                link.symlink_to(target)
            except (NotImplementedError, OSError):
                self.skipTest("symlinks are unavailable")

            exit_code, report, _ = self._run(
                ["--scenario", str(link)]
            )

        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "path_invalid")

    def test_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            exit_code, report, _ = self._run(
                ["--scenario", directory]
            )

        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "path_invalid")

    def test_core_internal_result_uses_internal_exit(self) -> None:
        result = scenario.NodeRoleScenarioResult(
            ok=False,
            code="internal_error",
            role="",
            final_state="",
            request_count=0,
            scenario_sha256="",
            transcript_sha256="",
            transcript_verification_code="",
            transcript_json="",
            steps=(),
            checks=(),
        )

        with mock.patch.object(cli, "run_scenario_path", return_value=result):
            exit_code, report, _ = self._run(
                ["--scenario", "unused"]
            )

        self.assertEqual(exit_code, cli.EXIT_INTERNAL)
        self.assertEqual(report["code"], "internal_error")
        self.assertEqual(report["detail"], "")

    def test_unexpected_cli_exception_is_sanitized(self) -> None:
        with mock.patch.object(
            cli,
            "run_scenario_path",
            side_effect=RuntimeError("sensitive internal information"),
        ):
            exit_code, report, text = self._run(
                ["--scenario", "unused"]
            )

        self.assertEqual(exit_code, cli.EXIT_INTERNAL)
        self.assertEqual(report["code"], "internal_error")
        self.assertEqual(report["detail"], "")
        self.assertNotIn("sensitive", text)

    def test_production_cli_has_main_entrypoint_and_no_network_imports(self) -> None:
        path = Path(cli.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        forbidden = {
            "asyncio",
            "http",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        }
        imports = set()
        main_guard = False

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.lstrip(".").split(".", 1)[0])
            elif isinstance(node, ast.If):
                if (
                    isinstance(node.test, ast.Compare)
                    and ast.unparse(node.test) == "__name__ == '__main__'"
                ):
                    main_guard = True

        self.assertFalse(imports & forbidden)
        self.assertTrue(main_guard)


if __name__ == "__main__":
    unittest.main()
