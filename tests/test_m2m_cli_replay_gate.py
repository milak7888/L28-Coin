# SPDX-License-Identifier: Apache-2.0
"""
Offline subprocess tests for Foundation 9 M2M CLI replay admission gate.

TEST-ONLY. All registry files use TemporaryDirectory paths outside the repository.
Does not sign, write report products, access private files, or perform network operations.
"""
from __future__ import annotations

import ast
import json
import os
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from coin.m2m_conformance_cli import (
    ADMISSION_PROFILE,
    ADMISSION_REPORT_VERSION,
    CLI_VERSION,
    compute_admission_report_id,
    compute_report_id,
)
from coin.m2m_replay_registry import ReplayRegistry

ROOT = Path(__file__).resolve().parents[1]
ADMISSION_VECTORS = ROOT / "docs" / "m2m" / "test_vectors_admission_v0.1.json"
REPORT_VECTORS = ROOT / "docs" / "m2m" / "test_vectors_report_v0.1.json"
TRANSCRIPT_VECTORS = ROOT / "docs" / "m2m" / "test_vectors_transcript_v0.1.json"
CLI_MODULE = "coin.m2m_conformance_cli"
CLI_PATH = ROOT / "coin" / "m2m_conformance_cli.py"

FORBIDDEN_IMPORT_NAMES = frozenset({"Ed25519PrivateKey", "from_private_bytes"})
FORBIDDEN_VECTOR_KEYS = frozenset(
    {
        "private_key",
        "seed",
        "seed_phrase",
        "mnemonic",
        "wallet_credential",
        "wallet_secret",
        "signing_secret",
        "secret_key",
    }
)
LEAK_MARKERS = (
    "hostname",
    "username",
    "getpass",
    "platform",
    "pid",
    "/Users/",
    "C:\\\\",
    "sqlite",
    "SQL",
    "Traceback",
    "Exception",
)


def _collect_keys(obj: Any, out: Set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(str(k))
            _collect_keys(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_keys(item, out)


def _run(
    args: Sequence[str],
    *,
    input_bytes: Optional[bytes] = None,
) -> Tuple[int, str, str]:
    cmd = [sys.executable, "-m", CLI_MODULE, *args]
    completed = subprocess.run(
        cmd,
        input=input_bytes,
        capture_output=True,
        cwd=str(ROOT),
    )
    return (
        completed.returncode,
        completed.stdout.decode("utf-8"),
        completed.stderr.decode("utf-8"),
    )


def _parse_single_json_object(stdout: str) -> Dict[str, Any]:
    assert stdout.endswith("\n"), "stdout must end with one newline"
    decoder = json.JSONDecoder()
    obj, end = decoder.raw_decode(stdout)
    rest = stdout[end:]
    assert rest == "\n", f"unexpected trailing stdout: {rest!r}"
    assert isinstance(obj, dict)
    return obj


def _registry_args(mode: Optional[str], db_path: Path) -> List[str]:
    if mode == "create":
        return ["--create-replay-registry", str(db_path)]
    if mode == "open":
        return ["--replay-registry", str(db_path)]
    return []


def _count_rows(db_path: Path) -> Tuple[int, int]:
    conn = sqlite3.connect(str(db_path))
    try:
        ex = int(conn.execute("SELECT COUNT(*) FROM exchanges").fetchone()[0])
        msg = int(conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0])
        return ex, msg
    finally:
        conn.close()


class TestM2MCLIReplayGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.admission_doc = json.loads(ADMISSION_VECTORS.read_text(encoding="utf-8"))
        cls.report_doc = json.loads(REPORT_VECTORS.read_text(encoding="utf-8"))
        cls.transcript_doc = json.loads(TRANSCRIPT_VECTORS.read_text(encoding="utf-8"))
        cls.vectors = {v["vector_id"]: v for v in cls.admission_doc["admission_vectors"]}
        cls.report_by_id = {v["vector_id"]: v for v in cls.report_doc["report_vectors"]}
        cls.transcripts = {
            **{v["vector_id"]: v for v in cls.transcript_doc["valid_transcripts"]},
            **{v["vector_id"]: v for v in cls.transcript_doc["invalid_transcripts"]},
        }

    def _envelopes_bytes(self, transcript_vector_id: str) -> bytes:
        vec = self.transcripts[transcript_vector_id]
        return json.dumps(vec["envelopes"], separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )

    def _db_path(self, tmp: str, name: str = "replay.sqlite3") -> Path:
        return Path(tmp) / name

    def _invoke_cli(
        self,
        *,
        tmp: str,
        step: Dict[str, Any],
        db_path: Path,
        transcript_path: Path,
    ) -> Tuple[int, Dict[str, Any], str, str]:
        raw = self._envelopes_bytes(step["source_transcript_vector_id"])
        transcript_path.write_bytes(raw)
        mode = step.get("registry_mode")
        if step.get("registry_path_suffix"):
            db_path = Path(tmp) / step["registry_path_suffix"]
        flags = list(step.get("flags", []))
        args = ["--input", str(transcript_path)] + flags + _registry_args(mode, db_path)
        code, out, err = _run(args)
        report = _parse_single_json_object(out) if out else {}
        return code, report, out, err

    def _run_vector(self, vector_id: str) -> None:
        vec = self.vectors[vector_id]
        with tempfile.TemporaryDirectory() as tmp:
            db_path = self._db_path(tmp)
            transcript_path = Path(tmp) / "transcript.json"
            ex_before, msg_before = 0, 0
            db_bytes_before: Optional[bytes] = None
            for step in vec["operations"]:
                op = step["op"]
                if op == "cli_invoke":
                    if db_path.exists():
                        ex_before, msg_before = _count_rows(db_path)
                        db_bytes_before = db_path.read_bytes()
                    code, report, out, err = self._invoke_cli(
                        tmp=tmp,
                        step=step,
                        db_path=db_path,
                        transcript_path=transcript_path,
                    )
                    self.assertEqual(code, step["expected_exit_code"], out)
                    if step.get("expected_profile"):
                        self.assertEqual(report.get("profile"), step["expected_profile"])
                    if step.get("expected_report_version"):
                        self.assertEqual(
                            report.get("report_version"), step["expected_report_version"]
                        )
                    if step.get("expected_code") is not None:
                        self.assertEqual(report.get("code"), step["expected_code"])
                    if "expected_registry_code" in step:
                        self.assertEqual(report.get("registry_code"), step["expected_registry_code"])
                    if step.get("expected_admitted") is not None:
                        self.assertEqual(report.get("admitted"), step["expected_admitted"])
                    if step.get("expected_newly_recorded") is not None:
                        self.assertEqual(
                            report.get("newly_recorded"), step["expected_newly_recorded"]
                        )
                    if step.get("expected_new_messages") is not None:
                        self.assertEqual(report.get("new_messages"), step["expected_new_messages"])
                    if step.get("expected_registry_file_exists") is False:
                        self.assertFalse(db_path.exists())
                    if step.get("expected_registry_bytes_unchanged"):
                        assert db_bytes_before is not None
                        self.assertEqual(db_path.read_bytes(), db_bytes_before)
                    if db_path.exists():
                        ex_after, msg_after = _count_rows(db_path)
                        self.assertEqual(
                            ex_after - ex_before, step.get("expected_exchange_count_delta", 0)
                        )
                        self.assertEqual(
                            msg_after - msg_before, step.get("expected_message_count_delta", 0)
                        )
                    if step.get("expected_profile") == ADMISSION_PROFILE:
                        if report.get("admitted") is not None:
                            self.assertEqual(report.get("admitted"), report.get("newly_recorded"))
                        if code == 0:
                            self.assertTrue(report.get("newly_recorded"))
                            self.assertTrue(report.get("admitted"))
                        if code == 4:
                            self.assertFalse(report.get("newly_recorded"))
                            self.assertFalse(report.get("admitted"))
                        if code != 0:
                            self.assertFalse(report.get("admitted"))
                    if vec.get("source_report_vector_id"):
                        expected = self.report_by_id[vec["source_report_vector_id"]][
                            "expected_report"
                        ]
                        self.assertEqual(report, expected)
                elif op == "inject_foreign_message_binding":
                    conn = sqlite3.connect(str(db_path))
                    try:
                        conn.execute("PRAGMA foreign_keys=OFF")
                        foreign = "0" * 64
                        conn.execute(
                            "INSERT INTO exchanges(exchange_hash, transcript_fingerprint, head_message_id, state, message_count) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (foreign, "1" * 64, "foreign_head", "requested", 1),
                        )
                        mid = conn.execute(
                            "SELECT message_id FROM messages ORDER BY ordinal ASC LIMIT 1"
                        ).fetchone()[0]
                        conn.execute(
                            "UPDATE messages SET exchange_hash = ? WHERE message_id = ?",
                            (foreign, mid),
                        )
                        conn.commit()
                    finally:
                        conn.close()
                elif op == "force_stored_state_terminal":
                    conn = sqlite3.connect(str(db_path))
                    try:
                        conn.execute(
                            "UPDATE exchanges SET state = ?",
                            (step["state"],),
                        )
                        conn.commit()
                    finally:
                        conn.close()
                elif op == "corrupt_schema_version":
                    conn = sqlite3.connect(str(db_path))
                    try:
                        conn.execute(
                            "UPDATE registry_metadata SET value = ? WHERE key = 'schema_version'",
                            ("999",),
                        )
                        conn.commit()
                    finally:
                        conn.close()
                elif op == "corrupt_message_count":
                    conn = sqlite3.connect(str(db_path))
                    try:
                        conn.execute("UPDATE exchanges SET message_count = 99")
                        conn.commit()
                    finally:
                        conn.close()
                else:
                    self.fail(f"unknown op {op}")

    def test_admission_vector_metadata(self):
        self.assertTrue(self.admission_doc["test_only"])
        self.assertFalse(self.admission_doc["live"])
        self.assertFalse(self.admission_doc["accepted_settlement"])
        self.assertFalse(self.admission_doc["private_material_committed"])
        self.assertEqual(len(self.vectors), 15)

    def test_vector_create_record_new(self):
        self._run_vector("admission_create_record_new")

    def test_vector_exact_repeat(self):
        self._run_vector("admission_exact_repeat")

    def test_vector_partial_then_extension(self):
        self._run_vector("admission_partial_then_extension")

    def test_vector_complete_then_old_prefix(self):
        self._run_vector("admission_complete_then_old_prefix")

    def test_vector_exchange_fork(self):
        self._run_vector("admission_exchange_fork")

    def test_vector_cross_exchange_corrupt_open(self):
        self._run_vector("admission_cross_exchange_corrupt_open")

    def test_vector_terminal_exact_repeat(self):
        self._run_vector("admission_terminal_exact_repeat")

    def test_vector_terminal_extension_rejection(self):
        self._run_vector("admission_terminal_extension_rejection")

    def test_vector_invalid_no_create(self):
        self._run_vector("admission_invalid_no_create")

    def test_vector_invalid_no_mutate(self):
        self._run_vector("admission_invalid_no_mutate")

    def test_vector_missing_existing_registry(self):
        self._run_vector("admission_missing_existing_registry")

    def test_vector_create_path_exists(self):
        self._run_vector("admission_create_path_exists")

    def test_vector_schema_mismatch(self):
        self._run_vector("admission_schema_mismatch")

    def test_vector_corrupted_registry(self):
        self._run_vector("admission_corrupted_registry")

    def test_vector_no_registry_backward_compat(self):
        self._run_vector("admission_no_registry_backward_compat")

    def test_open_existing_registry(self):
        raw = self._envelopes_bytes("valid_partial_quoted")
        with tempfile.TemporaryDirectory() as tmp:
            db = self._db_path(tmp)
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            c1, _, _ = _run(
                ["--input", str(path), "--create-replay-registry", str(db)]
            )
            c2, out, err = _run(["--input", str(path), "--replay-registry", str(db)])
        self.assertEqual(c1, 0)
        self.assertEqual(err, "")
        self.assertEqual(c2, 4)
        report = _parse_single_json_object(out)
        self.assertEqual(report["registry_code"], "already_recorded")

    def test_explicit_creation(self):
        raw = self._envelopes_bytes("valid_partial_quoted")
        with tempfile.TemporaryDirectory() as tmp:
            db = self._db_path(tmp)
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            code, out, err = _run(
                ["--input", str(path), "--create-replay-registry", str(db)]
            )
            self.assertEqual(code, 0)
            self.assertEqual(err, "")
            self.assertTrue(db.exists())
            report = _parse_single_json_object(out)
            self.assertEqual(report["registry_code"], "recorded_new")

    def test_relative_registry_path_rejected(self):
        raw = self._envelopes_bytes("valid_partial_quoted")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            code, out, err = _run(
                ["--input", str(path), "--create-replay-registry", "relative.sqlite3"]
            )
        self.assertEqual(code, 2)
        report = _parse_single_json_object(out)
        self.assertEqual(report["registry_code"], "registry_path_not_absolute")
        self.assertNotIn("relative.sqlite3", out + err)

    def test_inside_repo_registry_rejected(self):
        raw = self._envelopes_bytes("valid_partial_quoted")
        inside = str(ROOT / "forbidden_replay.sqlite3")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            code, out, err = _run(
                ["--input", str(path), "--create-replay-registry", inside]
            )
        self.assertEqual(code, 2)
        report = _parse_single_json_object(out)
        self.assertEqual(report["registry_code"], "registry_inside_repository")
        self.assertFalse(Path(inside).exists())
        self.assertNotIn(inside, out + err)

    def test_symlink_registry_rejected(self):
        raw = self._envelopes_bytes("valid_partial_quoted")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "real.sqlite3"
            link = Path(tmp) / "link.sqlite3"
            with ReplayRegistry(target, create=True):
                pass
            os.symlink(target.name, link)
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            code, out, err = _run(["--input", str(path), "--replay-registry", str(link)])
        self.assertEqual(code, 2)
        report = _parse_single_json_object(out)
        self.assertEqual(report["registry_code"], "registry_symlink_rejected")
        self.assertNotIn(str(link), out + err)

    def test_directory_registry_rejected(self):
        raw = self._envelopes_bytes("valid_partial_quoted")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            code, out, err = _run(["--input", str(path), "--replay-registry", tmp])
        self.assertEqual(code, 2)
        report = _parse_single_json_object(out)
        self.assertEqual(report["registry_code"], "registry_not_regular_file")

    def test_fifo_registry_rejected(self):
        raw = self._envelopes_bytes("valid_partial_quoted")
        with tempfile.TemporaryDirectory() as tmp:
            fifo = Path(tmp) / "pipe.fifo"
            try:
                os.mkfifo(fifo)
            except (AttributeError, OSError):
                self.skipTest("mkfifo unavailable")
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            code, out, err = _run(["--input", str(path), "--replay-registry", str(fifo)])
        self.assertEqual(code, 2)
        report = _parse_single_json_object(out)
        self.assertEqual(report["registry_code"], "registry_not_regular_file")

    def test_both_registry_options_rejected(self):
        code, out, err = _run(
            [
                "--input",
                "/tmp/x",
                "--replay-registry",
                "/tmp/a",
                "--create-replay-registry",
                "/tmp/b",
            ]
        )
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("usage:", err.lower())

    def test_admission_report_schema(self):
        raw = self._envelopes_bytes("valid_happy_path_completed")
        with tempfile.TemporaryDirectory() as tmp:
            db = self._db_path(tmp)
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            code, out, err = _run(
                [
                    "--input",
                    str(path),
                    "--require-terminal",
                    "--create-replay-registry",
                    str(db),
                ]
            )
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        report = _parse_single_json_object(out)
        self.assertEqual(report["report_version"], ADMISSION_REPORT_VERSION)
        self.assertEqual(report["profile"], ADMISSION_PROFILE)
        required = {
            "ok",
            "code",
            "state",
            "exchange_id",
            "verified_messages",
            "failed_index",
            "envelope_code",
            "settlement_transaction_id",
            "require_terminal",
            "input_mode",
            "input_size_bytes",
            "input_sha256",
            "conformance_report_id",
            "admitted",
            "registry_code",
            "newly_recorded",
            "new_messages",
            "exchange_hash",
            "transcript_fingerprint",
            "head_message_id",
            "registry_message_count",
            "report_id",
        }
        self.assertTrue(required.issubset(report.keys()))

    def test_conformance_report_id_recomputation(self):
        raw = self._envelopes_bytes("valid_happy_path_completed")
        with tempfile.TemporaryDirectory() as tmp:
            db = self._db_path(tmp)
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            _, out, _ = _run(
                [
                    "--input",
                    str(path),
                    "--require-terminal",
                    "--create-replay-registry",
                    str(db),
                ]
            )
        report = _parse_single_json_object(out)
        expected_conf = self.report_by_id["report_valid_completed_file"]["expected_report"]
        self.assertEqual(report["conformance_report_id"], expected_conf["report_id"])

    def test_admission_report_id_recomputation(self):
        raw = self._envelopes_bytes("valid_happy_path_completed")
        with tempfile.TemporaryDirectory() as tmp:
            db = self._db_path(tmp)
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            _, out, _ = _run(
                [
                    "--input",
                    str(path),
                    "--require-terminal",
                    "--create-replay-registry",
                    str(db),
                ]
            )
        report = _parse_single_json_object(out)
        body = {k: v for k, v in report.items() if k != "report_id"}
        self.assertEqual(compute_admission_report_id(body), report["report_id"])

    def test_deterministic_repeated_outputs(self):
        raw = self._envelopes_bytes("valid_happy_path_completed")
        with tempfile.TemporaryDirectory() as tmp:
            db = self._db_path(tmp)
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            args = [
                "--input",
                str(path),
                "--require-terminal",
                "--create-replay-registry",
                str(db),
            ]
            c1, o1, e1 = _run(args)
            c2, o2, e2 = _run(
                ["--input", str(path), "--require-terminal", "--replay-registry", str(db)]
            )
            c3, o3, e3 = _run(
                ["--input", str(path), "--require-terminal", "--replay-registry", str(db)]
            )
        self.assertEqual(c1, 0)
        self.assertEqual(c2, 4)
        self.assertEqual(o2, o3)
        self.assertEqual(e1, "")
        self.assertEqual(e2, "")
        self.assertEqual(e3, "")

    def test_no_path_time_host_pid_sql_exception_leakage(self):
        raw = self._envelopes_bytes("valid_partial_quoted")
        with tempfile.TemporaryDirectory() as tmp:
            db = self._db_path(tmp)
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            code, out, err = _run(
                ["--input", str(path), "--create-replay-registry", str(db)]
            )
        self.assertEqual(code, 0)
        blob = out + err
        self.assertNotIn(str(path), blob)
        self.assertNotIn(str(db), blob)
        self.assertNotIn(str(tmp), blob)
        report = _parse_single_json_object(out)
        for key in ("created_at", "timestamp", "hostname", "pid", "platform", "path"):
            self.assertNotIn(key, report)
        for marker in LEAK_MARKERS:
            self.assertNotIn(marker, blob)

    def test_exactly_one_stdout_json_object(self):
        raw = self._envelopes_bytes("valid_partial_quoted")
        with tempfile.TemporaryDirectory() as tmp:
            db = self._db_path(tmp)
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            _, out, _ = _run(
                ["--input", str(path), "--create-replay-registry", str(db)]
            )
        _parse_single_json_object(out)

    def test_stderr_contract_registry_mode(self):
        raw = self._envelopes_bytes("valid_partial_quoted")
        with tempfile.TemporaryDirectory() as tmp:
            db = self._db_path(tmp)
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            _, _, err = _run(["--input", str(path), "--create-replay-registry", str(db)])
        self.assertEqual(err, "")

    def test_no_registry_foundation7_byte_for_byte_all_report_vectors(self):
        for vec in self.report_doc["report_vectors"]:
            vector_id = vec["vector_id"]
            with self.subTest(vector_id=vector_id):
                flags = list(vec.get("flags", []))
                expected_report = vec["expected_report"]
                expected_code = vec["expected_exit_code"]
                if vec.get("source_transcript_vector_id"):
                    raw = self._envelopes_bytes(vec["source_transcript_vector_id"])
                elif vec.get("inline_input_utf8"):
                    raw = vec["inline_input_utf8"].encode("utf-8")
                elif vec.get("oversized_bytes"):
                    raw = None
                else:
                    continue

                if vec["input_mode"] == "stdin":
                    code, out, err = _run(["--stdin"] + flags, input_bytes=raw)
                else:
                    with tempfile.TemporaryDirectory() as tmp:
                        path = Path(tmp) / "t.json"
                        if raw is None:
                            with open(path, "wb") as fh:
                                fh.write(b"[" + b"0" * 1_048_576 + b"]")
                        else:
                            path.write_bytes(raw)
                        code, out, err = _run(["--input", str(path)] + flags)

                if expected_code == 2 and vec.get("oversized_bytes"):
                    self.assertEqual(err, "")
                if expected_code == 2 and vec["vector_id"] == "report_input_not_found_template":
                    self.assertEqual(err, "")
                report = _parse_single_json_object(out) if out else {}
                self.assertEqual(code, expected_code, vector_id)
                if out:
                    self.assertEqual(report, expected_report, vector_id)

    def test_no_registry_version_unchanged(self):
        code, out, err = _run(["--version"])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(out, CLI_VERSION + "\n")

    def test_no_registry_import_side_effect(self):
        tree = ast.parse(CLI_PATH.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module == "coin.m2m_replay_registry":
                self.fail("module-level replay registry import")
            if isinstance(node, ast.Import) and any(
                alias.name == "coin.m2m_replay_registry" for alias in node.names
            ):
                self.fail("module-level replay registry import")

    def test_admitted_iff_newly_recorded_registry_mode(self):
        scenarios = [
            ("valid_happy_path_completed", ["--require-terminal"], 0, True),
            ("valid_happy_path_completed", ["--require-terminal"], 4, False),
        ]
        raw = self._envelopes_bytes("valid_happy_path_completed")
        with tempfile.TemporaryDirectory() as tmp:
            db = self._db_path(tmp)
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            _run(
                [
                    "--input",
                    str(path),
                    "--require-terminal",
                    "--create-replay-registry",
                    str(db),
                ]
            )
            _, out1, _ = _run(
                [
                    "--input",
                    str(path),
                    "--require-terminal",
                    "--create-replay-registry",
                    str(db),
                ]
            )
            _, out2, _ = _run(
                [
                    "--input",
                    str(path),
                    "--require-terminal",
                    "--replay-registry",
                    str(db),
                ]
            )
        for out in (out1, out2):
            report = _parse_single_json_object(out)
            self.assertEqual(report.get("admitted"), report.get("newly_recorded"))

    def test_exit_zero_iff_newly_recorded_registry_mode(self):
        raw = self._envelopes_bytes("valid_happy_path_completed")
        with tempfile.TemporaryDirectory() as tmp:
            db = self._db_path(tmp)
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            c_new, out_new, _ = _run(
                [
                    "--input",
                    str(path),
                    "--require-terminal",
                    "--create-replay-registry",
                    str(db),
                ]
            )
            c_idem, out_idem, _ = _run(
                [
                    "--input",
                    str(path),
                    "--require-terminal",
                    "--replay-registry",
                    str(db),
                ]
            )
        self.assertEqual(c_new, 0)
        self.assertTrue(_parse_single_json_object(out_new)["newly_recorded"])
        self.assertEqual(c_idem, 4)
        self.assertFalse(_parse_single_json_object(out_idem)["newly_recorded"])

    def test_ast_no_private_key_apis(self):
        tree = ast.parse(CLI_PATH.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in FORBIDDEN_IMPORT_NAMES:
                        self.fail(f"imports {alias.name}")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"generate", "sign"}:
                    self.fail(f"calls {node.func.attr}()")
        src = CLI_PATH.read_text(encoding="utf-8")
        self.assertNotRegex(src, r"import\s+.*Ed25519PrivateKey")

    def test_vector_keys_no_private_material(self):
        keys: Set[str] = set()
        _collect_keys(self.admission_doc, keys)
        offenders = sorted(k for k in keys if k.lower() in FORBIDDEN_VECTOR_KEYS)
        self.assertEqual(offenders, [])

    def test_no_repo_database_or_report_files(self):
        data_dir = ROOT / "data"
        self.assertFalse(data_dir.exists() and any(data_dir.rglob("shard_*.jsonl")))
        self.assertFalse(any(ROOT.glob("*.sqlite3")))
        stray = list(ROOT.glob("l28-m2m-conformance-report*"))
        self.assertEqual(stray, [])
        stray_adm = list(ROOT.glob("l28-m2m-admission-report*"))
        self.assertEqual(stray_adm, [])

    def test_conformance_report_id_matches_internal_report(self):
        raw = self._envelopes_bytes("valid_partial_quoted")
        with tempfile.TemporaryDirectory() as tmp:
            db = self._db_path(tmp)
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            _, out_reg, _ = _run(["--input", str(path), "--create-replay-registry", str(db)])
            _, out_no, _ = _run(["--input", str(path)])
        reg = _parse_single_json_object(out_reg)
        plain = _parse_single_json_object(out_no)
        plain_body = {k: v for k, v in plain.items() if k != "report_id"}
        self.assertEqual(reg["conformance_report_id"], plain["report_id"])
        self.assertEqual(reg["conformance_report_id"], compute_report_id(plain_body))


if __name__ == "__main__":
    unittest.main()
