from __future__ import annotations

import ast
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from coin import node_role_composition_manifest_evidence as evidence
from coin import node_role_composition_manifest_evidence_cli as cli
from test_node_role_composition_manifest_evidence import _json, _valid_evidence


def _run(argv: list[str]) -> tuple[int, dict[str, object], str]:
    stream = io.StringIO()
    with redirect_stdout(stream):
        code = cli.main(argv)
    text = stream.getvalue()
    return code, json.loads(text), text


class NodeRoleCompositionManifestEvidenceCliTests(unittest.TestCase):
    def _write_evidence(self, directory: str, name: str = "evidence.json") -> str:
        path = Path(directory) / name
        path.write_text(_json(_valid_evidence()), encoding="utf-8")
        return str(path)

    def test_valid_evidence_cli_success(self) -> None:
        with TemporaryDirectory() as directory:
            code, report, _ = _run(["--evidence", self._write_evidence(directory)])

        self.assertEqual(code, cli.EXIT_PASS)
        self.assertTrue(report["ok"])
        self.assertEqual(report["code"], "evidence_valid")

    def test_valid_output_is_deterministic_and_pretty_is_logically_equal(self) -> None:
        with TemporaryDirectory() as directory:
            path = self._write_evidence(directory)
            first = _run(["--evidence", path])
            second = _run(["--evidence", path])
            _, pretty, pretty_text = _run(["--evidence", path, "--pretty"])

        self.assertEqual(first, second)
        self.assertEqual(first[1], pretty)
        self.assertIn("\n  ", pretty_text)

    def test_report_fields_are_exact_and_report_id_is_body_bound(self) -> None:
        with TemporaryDirectory() as directory:
            _, report, _ = _run(["--evidence", self._write_evidence(directory)])

        self.assertEqual(frozenset(report), cli.REPORT_FIELDS)
        self.assertEqual(report["report_id"], cli.compute_report_id(report))
        changed = dict(report)
        changed["code"] = "changed"
        self.assertNotEqual(report["report_id"], cli.compute_report_id(changed))

    def test_usage_failures_are_sanitized(self) -> None:
        for argv in ([], ["--unknown"]):
            with self.subTest(argv=argv):
                code, report, _ = _run(list(argv))
                self.assertEqual(code, cli.EXIT_USAGE)
                self.assertEqual(report["code"], "usage_error")
                self.assertFalse(report["ok"])

    def test_missing_directory_and_symlink_paths_are_rejected(self) -> None:
        code, report, _ = _run(["--evidence", "not-present.json"])
        self.assertEqual(code, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "evidence_file_unavailable")

        with TemporaryDirectory() as directory:
            code, report, _ = _run(["--evidence", directory])
            self.assertEqual(code, cli.EXIT_FAILURE)
            self.assertEqual(report["code"], "evidence_path_not_regular_file")

            source = self._write_evidence(directory)
            link = Path(directory) / "evidence-link.json"
            link.symlink_to(source)
            code, report, _ = _run(["--evidence", str(link)])

        self.assertEqual(code, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "evidence_path_not_regular_file")

    def test_oversized_file_is_rejected_before_verification(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "oversized.json"
            path.write_bytes(b"x" * (evidence.MAX_EVIDENCE_BYTES + 1))
            code, report, _ = _run(["--evidence", str(path)])

        self.assertEqual(code, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "evidence_too_large")
        self.assertEqual(report["detail"], "input_exceeds_maximum")

    def test_invalid_evidence_is_verification_failure(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("{}", encoding="utf-8")
            code, report, _ = _run(["--evidence", str(path)])

        self.assertEqual(code, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "schema_error")

    def test_core_internal_result_uses_internal_exit(self) -> None:
        result = evidence.NodeRoleCompositionManifestEvidenceResult(
            ok=False,
            code="internal_error",
            evidence_sha256="",
            manifest_sha256="",
            report_id="",
            component_ids=(),
            roles=(),
            trust_boundary_ids=(),
            checks=(),
            detail="internal_failure",
        )
        with mock.patch.object(cli, "verify_evidence_path", return_value=result):
            code, report, _ = _run(["--evidence", "unused.json"])

        self.assertEqual(code, cli.EXIT_INTERNAL)
        self.assertEqual(report["code"], "internal_error")

    def test_unexpected_cli_exception_is_sanitized(self) -> None:
        with mock.patch.object(
            cli, "verify_evidence_path", side_effect=RuntimeError("private detail")
        ):
            code, report, _ = _run(["--evidence", "unused.json"])

        self.assertEqual(code, cli.EXIT_INTERNAL)
        self.assertEqual(report["code"], "cli_internal_error")
        self.assertEqual(report["detail"], "internal command failure")

    def test_production_cli_has_main_entrypoint_and_no_network_imports(self) -> None:
        path = Path("coin/node_role_composition_manifest_evidence_cli.py")
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )

        self.assertIn("def main(", source)
        self.assertIn('if __name__ == "__main__":', source)
        self.assertFalse(
            imports.intersection(
                {
                    "socket", "subprocess", "threading", "multiprocessing",
                    "requests", "urllib", "http", "ssl", "asyncio",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
