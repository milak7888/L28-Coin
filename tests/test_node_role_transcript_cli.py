"""Tests for the offline node-role transcript CLI."""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from coin import node_role_transcript as transcript
from coin import node_role_transcript_cli as cli


def _entry(
    sequence: int,
    previous_state: str,
    requested_state: str,
    resulting_state: str,
) -> dict[str, object]:
    return {
        "sequence": sequence,
        "previous_state": previous_state,
        "requested_state": requested_state,
        "resulting_state": resulting_state,
        "ok": True,
        "code": "transitioned",
    }


def _valid_document(role: str = transcript.CORE_ROLE) -> dict[str, object]:
    if role == transcript.CORE_ROLE:
        transitions = [
            _entry(0, "CREATED", "PAUSED", "PAUSED"),
            _entry(1, "PAUSED", "STOPPED", "STOPPED"),
        ]
    else:
        transitions = [
            _entry(0, "CREATED", "CONFIGURED", "CONFIGURED"),
            _entry(1, "CONFIGURED", "PAUSED", "PAUSED"),
            _entry(2, "PAUSED", "STOPPED", "STOPPED"),
        ]

    return {
        "transcript_version": transcript.TRANSCRIPT_VERSION,
        "model_version": transcript.MODEL_VERSION,
        "role": role,
        "initial_state": "CREATED",
        "transitions": transitions,
        "final_state": "STOPPED",
    }


class NodeRoleTranscriptCliTests(unittest.TestCase):
    def _write_document(
        self,
        directory: str,
        document: object,
        name: str = "transcript.json",
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
            for role in (transcript.CORE_ROLE, transcript.P2P_ROLE):
                with self.subTest(role=role):
                    path = self._write_document(
                        directory,
                        _valid_document(role),
                        name=f"{role}.json",
                    )
                    exit_code, report, _ = self._run(
                        ["--transcript", str(path)]
                    )

                    self.assertEqual(exit_code, cli.EXIT_PASS)
                    self.assertTrue(report["ok"])
                    self.assertEqual(report["code"], "transcript_valid")
                    self.assertEqual(report["role"], role)
                    self.assertEqual(report["final_state"], "STOPPED")

    def test_valid_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_document(directory, _valid_document())

            first_code, first_report, first_text = self._run(
                ["--transcript", str(path)]
            )
            second_code, second_report, second_text = self._run(
                ["--transcript", str(path)]
            )

        self.assertEqual(first_code, cli.EXIT_PASS)
        self.assertEqual(second_code, cli.EXIT_PASS)
        self.assertEqual(first_report, second_report)
        self.assertEqual(first_text, second_text)

    def test_pretty_output_preserves_logical_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_document(directory, _valid_document())
            compact_code, compact_report, compact_text = self._run(
                ["--transcript", str(path)]
            )
            pretty_code, pretty_report, pretty_text = self._run(
                ["--transcript", str(path), "--pretty"]
            )

        self.assertEqual(compact_code, cli.EXIT_PASS)
        self.assertEqual(pretty_code, cli.EXIT_PASS)
        self.assertEqual(compact_report, pretty_report)
        self.assertNotEqual(compact_text, pretty_text)

    def test_report_fields_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_document(directory, _valid_document())
            exit_code, report, _ = self._run(
                ["--transcript", str(path)]
            )

        self.assertEqual(exit_code, cli.EXIT_PASS)
        self.assertEqual(frozenset(report), cli.REPORT_FIELDS)
        self.assertEqual(report["profile"], cli.PROFILE)
        self.assertEqual(report["report_version"], cli.REPORT_VERSION)
        self.assertEqual(report["cli_version"], cli.CLI_VERSION)
        self.assertEqual(report["transcript_version"], transcript.TRANSCRIPT_VERSION)
        self.assertEqual(report["model_version"], transcript.MODEL_VERSION)
        self.assertEqual(report["verifier_version"], transcript.VERIFIER_VERSION)

    def test_report_id_is_deterministic_and_body_bound(self) -> None:
        result = transcript.verify_transcript_json(
            json.dumps(_valid_document())
        )
        report = cli.build_report(result)

        self.assertEqual(report["report_id"], cli.compute_report_id(report))

        mutated = dict(report)
        mutated["role"] = transcript.P2P_ROLE
        self.assertNotEqual(
            report["report_id"],
            cli.compute_report_id(mutated),
        )

    def test_invalid_transcript_is_verification_failure(self) -> None:
        document = _valid_document()
        document["final_state"] = "PAUSED"

        with tempfile.TemporaryDirectory() as directory:
            path = self._write_document(directory, document)
            exit_code, report, _ = self._run(
                ["--transcript", str(path)]
            )

        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "final_state_mismatch")

    def test_missing_path_is_sanitized_verification_failure(self) -> None:
        missing = "/definitely/not/present/private-transcript.json"
        exit_code, report, text = self._run(
            ["--transcript", missing]
        )

        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "path_invalid")
        self.assertNotIn(missing, text)

    def test_transcript_argument_is_required(self) -> None:
        exit_code, report, _ = self._run([])

        self.assertEqual(exit_code, cli.EXIT_USAGE)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "usage_error")

    def test_unknown_argument_is_usage_failure(self) -> None:
        exit_code, report, _ = self._run(["--unknown"])

        self.assertEqual(exit_code, cli.EXIT_USAGE)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "usage_error")

    def test_oversized_file_is_rejected_before_reading_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.json"
            path.write_bytes(b"{" + (b" " * transcript.MAX_TRANSCRIPT_BYTES))

            exit_code, report, _ = self._run(
                ["--transcript", str(path)]
            )

        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "transcript_too_large")
        self.assertEqual(report["transcript_sha256"], "")

    def test_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = self._write_document(directory, _valid_document())
            link = Path(directory) / "link.json"

            try:
                link.symlink_to(target)
            except (NotImplementedError, OSError):
                self.skipTest("symlinks are unavailable")

            exit_code, report, _ = self._run(
                ["--transcript", str(link)]
            )

        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "path_invalid")

    def test_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            exit_code, report, _ = self._run(
                ["--transcript", directory]
            )

        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "path_invalid")

    def test_core_internal_result_uses_internal_exit(self) -> None:
        result = transcript.NodeRoleTranscriptResult(
            ok=False,
            code="internal_error",
            role="",
            initial_state="",
            final_state="",
            transition_count=0,
            transcript_sha256="",
            checks=(),
        )

        with mock.patch.object(
            cli,
            "verify_transcript_path",
            return_value=result,
        ):
            exit_code, report, _ = self._run(
                ["--transcript", "unused"]
            )

        self.assertEqual(exit_code, cli.EXIT_INTERNAL)
        self.assertEqual(report["code"], "internal_error")
        self.assertEqual(report["detail"], "")

    def test_unexpected_cli_exception_is_sanitized(self) -> None:
        with mock.patch.object(
            cli,
            "verify_transcript_path",
            side_effect=RuntimeError("sensitive internal information"),
        ):
            exit_code, report, text = self._run(
                ["--transcript", "unused"]
            )

        self.assertEqual(exit_code, cli.EXIT_INTERNAL)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "internal_error")
        self.assertEqual(report["detail"], "")
        self.assertNotIn("sensitive", text)

    def test_production_cli_has_main_entrypoint_and_no_network_imports(self) -> None:
        path = Path(cli.__file__)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))

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
                imports.update(
                    alias.name.split(".", 1)[0] for alias in node.names
                )
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
