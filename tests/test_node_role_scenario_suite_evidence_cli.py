from __future__ import annotations

import ast
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from coin import node_role_model as model
from coin import node_role_scenario as scenario
from coin import node_role_scenario_suite as suite
from coin import node_role_scenario_suite_cli as suite_cli
from coin import node_role_scenario_suite_evidence as evidence
from coin import node_role_scenario_suite_evidence_cli as cli
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

    cases: list[dict[str, object]] = []
    for index, states in enumerate(core_sequences):
        cases.append({
            "case_id": f"core-{index}",
            "scenario": _scenario(model.CORE_ROLE, states),
        })
    for index, states in enumerate(p2p_sequences):
        cases.append({
            "case_id": f"p2p-{index}",
            "scenario": _scenario(model.P2P_ROLE, states),
        })

    return {
        "suite_version": suite.SUITE_VERSION,
        "scenario_version": scenario.SCENARIO_VERSION,
        "model_version": model.MODEL_VERSION,
        "transcript_version": transcript.TRANSCRIPT_VERSION,
        "cases": cases,
    }


def _evidence_value() -> dict[str, object]:
    suite_value = _canonical_suite()
    suite_result = suite.verify_scenario_suite_json(_encoded(suite_value))
    if not suite_result.ok:
        raise AssertionError(suite_result)
    return {
        "evidence_version": evidence.EVIDENCE_VERSION,
        "suite": suite_value,
        "report": suite_cli.build_report(suite_result),
    }


def _encoded(value: object, *, pretty: bool = False) -> bytes:
    if pretty:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )
    else:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    return rendered.encode("utf-8")


def _run_main(arguments: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = cli.main(arguments)
    return code, stdout.getvalue(), stderr.getvalue()


def _write_evidence(directory: Path, value: object | None = None) -> Path:
    path = directory / "evidence.json"
    path.write_bytes(_encoded(_evidence_value() if value is None else value))
    return path


class NodeRoleScenarioSuiteEvidenceCliTests(unittest.TestCase):
    def test_valid_evidence_cli_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = _write_evidence(Path(temporary))
            code, output, errors = _run_main(["--evidence", str(path)])

        self.assertEqual(code, cli.EXIT_PASS)
        self.assertEqual(errors, "")
        report = json.loads(output)
        self.assertTrue(report["ok"])
        self.assertEqual(report["code"], "evidence_valid")
        self.assertEqual(report["case_count"], 12)
        self.assertEqual(report["core_transition_count"], 11)
        self.assertEqual(report["p2p_transition_count"], 8)
        self.assertEqual(report["core_reserved_rejection_count"], 2)
        self.assertEqual(report["p2p_reserved_rejection_count"], 1)
        self.assertEqual(report["report_id"], cli.compute_report_id(report))

    def test_valid_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = _write_evidence(Path(temporary))
            first = _run_main(["--evidence", str(path)])
            second = _run_main(["--evidence", str(path)])
        self.assertEqual(first, second)

    def test_pretty_output_preserves_logical_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = _write_evidence(Path(temporary))
            compact_code, compact, _ = _run_main(["--evidence", str(path)])
            pretty_code, pretty, _ = _run_main(
                ["--evidence", str(path), "--pretty"]
            )
        self.assertEqual(compact_code, cli.EXIT_PASS)
        self.assertEqual(pretty_code, cli.EXIT_PASS)
        self.assertEqual(json.loads(compact), json.loads(pretty))

    def test_report_fields_and_source_binding_are_exact(self) -> None:
        value = _evidence_value()
        source_report = value["report"]
        assert isinstance(source_report, dict)
        with tempfile.TemporaryDirectory() as temporary:
            path = _write_evidence(Path(temporary), value)
            code, output, _ = _run_main(["--evidence", str(path)])

        self.assertEqual(code, cli.EXIT_PASS)
        report = json.loads(output)
        self.assertEqual(frozenset(report), cli.REPORT_FIELDS)
        self.assertEqual(report["source_report_id"], source_report["report_id"])
        self.assertEqual(
            report["source_report_version"],
            suite_cli.REPORT_VERSION,
        )

    def test_report_id_is_deterministic_and_body_bound(self) -> None:
        result = evidence.verify_scenario_suite_evidence_json(
            _encoded(_evidence_value())
        )
        report = cli.build_report(result)
        self.assertEqual(report["report_id"], cli.compute_report_id(report))

        changed = dict(report)
        changed["case_count"] += 1
        self.assertNotEqual(
            report["report_id"],
            cli.compute_report_id(changed),
        )

    def test_invalid_evidence_is_verification_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = _write_evidence(Path(temporary), {})
            code, output, _ = _run_main(["--evidence", str(path)])
        self.assertEqual(code, cli.EXIT_FAILURE)
        report = json.loads(output)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "schema_error")

    def test_incomplete_suite_is_verification_failure(self) -> None:
        value = _evidence_value()
        suite_value = value["suite"]
        assert isinstance(suite_value, dict)
        cases = suite_value["cases"]
        assert isinstance(cases, list)
        cases.pop()

        with tempfile.TemporaryDirectory() as temporary:
            path = _write_evidence(Path(temporary), value)
            code, output, _ = _run_main(["--evidence", str(path)])
        self.assertEqual(code, cli.EXIT_FAILURE)
        self.assertEqual(json.loads(output)["code"], "suite_invalid")

    def test_missing_path_is_sanitized_verification_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "private-name.json"
            code, output, _ = _run_main(["--evidence", str(missing)])
        self.assertEqual(code, cli.EXIT_FAILURE)
        self.assertNotIn("private-name", output)
        report = json.loads(output)
        self.assertEqual(report["code"], "evidence_file_unavailable")

    def test_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code, output, _ = _run_main(["--evidence", temporary])
        self.assertEqual(code, cli.EXIT_FAILURE)
        self.assertEqual(
            json.loads(output)["code"],
            "evidence_path_not_regular_file",
        )

    def test_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            target = _write_evidence(directory)
            link = directory / "evidence-link.json"
            link.symlink_to(target)
            code, output, _ = _run_main(["--evidence", str(link)])
        self.assertEqual(code, cli.EXIT_FAILURE)
        self.assertEqual(
            json.loads(output)["code"],
            "evidence_path_not_regular_file",
        )

    def test_oversized_file_is_rejected_before_payload_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "oversized.json"
            path.write_bytes(b" " * (evidence.MAX_EVIDENCE_BYTES + 1))
            with mock.patch.object(
                cli,
                "verify_scenario_suite_evidence_json",
            ) as verifier:
                code, output, _ = _run_main(["--evidence", str(path)])
        self.assertEqual(code, cli.EXIT_FAILURE)
        self.assertEqual(json.loads(output)["code"], "evidence_too_large")
        verifier.assert_not_called()

    def test_evidence_argument_is_required(self) -> None:
        code, output, errors = _run_main([])
        self.assertEqual(code, cli.EXIT_USAGE)
        self.assertEqual(output, "")
        self.assertIn("--evidence", errors)

    def test_unknown_argument_is_usage_failure(self) -> None:
        code, output, errors = _run_main(
            ["--evidence", "ignored", "--unknown"]
        )
        self.assertEqual(code, cli.EXIT_USAGE)
        self.assertEqual(output, "")
        self.assertIn("unrecognized arguments", errors)

    def test_core_internal_result_uses_internal_exit(self) -> None:
        internal = evidence.NodeRoleScenarioSuiteEvidenceResult(
            ok=False,
            code="internal_error",
            evidence_sha256="",
            suite_sha256="",
            report_id="",
            case_count=0,
            roles=(),
            core_transition_count=0,
            p2p_transition_count=0,
            core_reserved_rejection_count=0,
            p2p_reserved_rejection_count=0,
            checks=(),
            detail="internal_failure",
        )
        with mock.patch.object(cli, "verify_evidence_path", return_value=internal):
            code, output, _ = _run_main(["--evidence", "ignored"])
        self.assertEqual(code, cli.EXIT_INTERNAL)
        self.assertEqual(json.loads(output)["code"], "internal_error")

    def test_unexpected_cli_exception_is_sanitized(self) -> None:
        with mock.patch.object(
            cli,
            "verify_evidence_path",
            side_effect=RuntimeError("private-secret-value"),
        ):
            code, output, _ = _run_main(["--evidence", "ignored"])
        self.assertEqual(code, cli.EXIT_INTERNAL)
        self.assertNotIn("private-secret-value", output)
        report = json.loads(output)
        self.assertEqual(report["code"], "cli_internal_error")
        self.assertEqual(report["detail"], "internal_failure")

    def test_production_cli_has_main_entrypoint_and_no_network_imports(self) -> None:
        path = Path(cli.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            alias.name.split(".")[0]
            for node in tree.body
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertTrue(
            imported.isdisjoint({"http", "requests", "socket", "urllib"})
        )
        self.assertTrue(any(
            isinstance(node, ast.If)
            and "__main__" in ast.unparse(node.test)
            for node in tree.body
        ))


if __name__ == "__main__":
    unittest.main()
