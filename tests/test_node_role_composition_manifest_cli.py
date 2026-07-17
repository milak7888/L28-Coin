from __future__ import annotations

import ast
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from coin import node_role_composition_manifest as composition
from coin import node_role_composition_manifest_cli as cli
from test_node_role_composition_manifest import _json, _valid_manifest


def _run(argv: list[str]) -> tuple[int, dict[str, object]]:
    output = io.StringIO()
    with redirect_stdout(output):
        exit_code = cli.main(argv)
    lines = output.getvalue().splitlines()
    if not lines:
        raise AssertionError("CLI emitted no report")
    return exit_code, json.loads("\n".join(lines))


class NodeRoleCompositionManifestCliTests(unittest.TestCase):
    def _write_manifest(self, directory: str, *, pretty: bool = False) -> str:
        path = Path(directory, "manifest.json")
        path.write_text(_json(_valid_manifest(), pretty=pretty), encoding="utf-8")
        return str(path)

    def test_valid_manifest_cli_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_manifest(directory)
            exit_code, report = _run(["--manifest", path])
        self.assertEqual(exit_code, cli.EXIT_PASS)
        self.assertTrue(report["ok"])
        self.assertEqual(report["code"], "manifest_valid")
        self.assertEqual(report["profile"], cli.PROFILE)

    def test_valid_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_manifest(directory)
            first = _run(["--manifest", path])
            second = _run(["--manifest", path])
        self.assertEqual(first, second)

    def test_pretty_output_preserves_logical_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_manifest(directory, pretty=True)
            compact = _run(["--manifest", path])
            pretty = _run(["--manifest", path, "--pretty"])
        self.assertEqual(compact, pretty)

    def test_report_fields_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_manifest(directory)
            _, report = _run(["--manifest", path])
        self.assertEqual(frozenset(report), cli.REPORT_FIELDS)
        self.assertEqual(report["report_version"], cli.REPORT_VERSION)
        self.assertEqual(report["cli_version"], cli.CLI_VERSION)
        self.assertEqual(report["manifest_version"], composition.MANIFEST_VERSION)
        self.assertEqual(report["security_profile_sha256"], composition.SECURITY_PROFILE_SHA256)
        self.assertEqual(report["component_ids"], ["core-primary", "p2p-boundary"])
        self.assertEqual(report["trust_boundary_ids"], [
            "peer_to_p2p", "p2p_to_core", "core_to_persistence", "checkpoint_to_core"
        ])

    def test_report_id_is_deterministic_and_body_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_manifest(directory)
            _, report = _run(["--manifest", path])
        self.assertEqual(report["report_id"], cli.compute_report_id(report))
        changed = dict(report)
        changed["component_ids"] = ["changed"]
        self.assertNotEqual(report["report_id"], cli.compute_report_id(changed))

    def test_manifest_argument_is_required(self) -> None:
        exit_code, report = _run([])
        self.assertEqual(exit_code, cli.EXIT_USAGE)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "usage_error")

    def test_unknown_argument_is_usage_failure(self) -> None:
        exit_code, report = _run(["--unknown"])
        self.assertEqual(exit_code, cli.EXIT_USAGE)
        self.assertEqual(report["code"], "usage_error")

    def test_missing_path_is_sanitized_verification_failure(self) -> None:
        exit_code, report = _run(["--manifest", "/missing/private/manifest.json"])
        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "manifest_file_unavailable")
        self.assertNotIn("/missing/private", json.dumps(report))

    def test_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            exit_code, report = _run(["--manifest", directory])
        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "manifest_path_not_regular_file")

    def test_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = self._write_manifest(directory)
            link = Path(directory, "manifest-link.json")
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            exit_code, report = _run(["--manifest", str(link)])
        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "manifest_path_not_regular_file")

    def test_oversized_file_is_rejected_before_payload_verification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "large.json")
            path.write_bytes(b" " * (composition.MAX_MANIFEST_BYTES + 1))
            with mock.patch.object(cli, "verify_node_role_composition_manifest_json") as verifier:
                exit_code, report = _run(["--manifest", str(path)])
            verifier.assert_not_called()
        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "manifest_too_large")

    def test_invalid_manifest_is_verification_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "invalid.json")
            path.write_text("{}", encoding="utf-8")
            exit_code, report = _run(["--manifest", str(path)])
        self.assertEqual(exit_code, cli.EXIT_FAILURE)
        self.assertEqual(report["code"], "schema_error")

    def test_core_internal_result_uses_internal_exit(self) -> None:
        failure = composition.NodeRoleCompositionManifestResult(
            ok=False,
            code="internal_error",
            manifest_sha256="",
            security_profile_sha256="",
            evidence_sha256="",
            evidence_report_id="",
            component_ids=(),
            roles=(),
            trust_boundary_ids=(),
            checks=(),
            detail="internal verification failure",
        )
        with mock.patch.object(cli, "verify_manifest_path", return_value=failure):
            exit_code, report = _run(["--manifest", "ignored"])
        self.assertEqual(exit_code, cli.EXIT_INTERNAL)
        self.assertEqual(report["code"], "internal_error")

    def test_unexpected_cli_exception_is_sanitized(self) -> None:
        with mock.patch.object(cli, "verify_manifest_path", side_effect=RuntimeError("secret")):
            exit_code, report = _run(["--manifest", "ignored"])
        self.assertEqual(exit_code, cli.EXIT_INTERNAL)
        self.assertEqual(report["code"], "cli_internal_error")
        self.assertEqual(report["detail"], "internal command failure")
        self.assertNotIn("secret", json.dumps(report))

    def test_production_cli_has_main_entrypoint_and_no_network_imports(self) -> None:
        path = Path(cli.__file__)
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add((node.module or "").split(".")[0])
        self.assertTrue(imports.isdisjoint({
            "socket", "subprocess", "threading", "multiprocessing", "urllib", "http"
        }))
        self.assertIn('if __name__ == "__main__":', text)


if __name__ == "__main__":
    unittest.main()
