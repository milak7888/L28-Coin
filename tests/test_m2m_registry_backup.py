# SPDX-License-Identifier: Apache-2.0
"""
Offline tests for Foundation 12 M2M replay-registry backup and recovery.

All SQLite/backup/restore files use TemporaryDirectory paths outside the repository.
"""
from __future__ import annotations

import ast
import dataclasses
import errno
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
from unittest.mock import patch

import coin.m2m_registry_backup
from coin.m2m_registry_audit import RegistryAuditResult, audit_registry

from coin.m2m_registry_backup import (
    DOMAIN_BACKUP_REPORT,
    PROFILE,
    REPORT_VERSION,
    STABLE_CODES,
    RegistryBackupResult,
    compute_backup_report_id,
    create_registry_backup,
    restore_registry_backup,
)
from coin.m2m_registry_backup_cli import (
    CLI_VERSION,
    EXIT_FAILURE,
    EXIT_PASS,
    EXIT_USAGE,
    REPORT_FIELD_ORDER,
    build_report,
)
from coin.m2m_replay_registry import ReplayRegistry

ROOT = Path(__file__).resolve().parents[1]
VECTOR_PATH = ROOT / "docs" / "m2m" / "test_vectors_registry_backup_v0.1.json"
TRANSCRIPT_PATH = ROOT / "docs" / "m2m" / "test_vectors_transcript_v0.1.json"
BACKUP_PATH = ROOT / "coin" / "m2m_registry_backup.py"
CLI_PATH = ROOT / "coin" / "m2m_registry_backup_cli.py"
CLI_MODULE = "coin.m2m_registry_backup_cli"

FORBIDDEN_IMPORT_NAMES = frozenset({"Ed25519PrivateKey", "from_private_bytes"})
FORBIDDEN_IMPORT_MODULES = frozenset(
    {
        "subprocess",
        "socket",
        "urllib",
        "http",
        "requests",
        "httpx",
        "aiohttp",
    }
)
FORBIDDEN_CALL_ATTRS = frozenset({"sign", "generate"})
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
    "Traceback",
    "Exception",
    "sqlite",
    "SQL",
    "INSERT",
    "UPDATE",
    "DELETE",
)
EXPECTED_STABLE_CODES = frozenset(
    {
        "backup_created",
        "restore_created",
        "invalid_source_path",
        "source_not_found",
        "invalid_backup_path",
        "backup_not_found",
        "invalid_destination_path",
        "destination_exists",
        "unsafe_path",
        "same_file",
        "source_audit_failed",
        "backup_audit_failed",
        "restore_audit_failed",
        "source_changed",
        "backup_changed",
        "logical_registry_mismatch",
        "artifact_hash_mismatch",
        "unsupported_registry_schema",
        "registry_resource_limit",
        "backup_failed",
        "restore_failed",
        "publish_failed",
        "internal_error",
    }
)


def _collect_keys(obj: Any, out: Set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(str(k))
            _collect_keys(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_keys(item, out)


def _run(args: Sequence[str]) -> Tuple[int, str, str]:
    completed = subprocess.run(
        [sys.executable, "-m", CLI_MODULE, *args],
        capture_output=True,
        cwd=str(ROOT),
    )
    return (
        completed.returncode,
        completed.stdout.decode("utf-8"),
        completed.stderr.decode("utf-8"),
    )


def _parse_single_json_object(stdout: str) -> Dict[str, Any]:
    assert stdout.endswith("\n")
    decoder = json.JSONDecoder()
    obj, end = decoder.raw_decode(stdout)
    rest = stdout[end:]
    assert rest == "\n", f"unexpected trailing stdout: {rest!r}"
    assert isinstance(obj, dict)
    return obj


def _file_snapshot(path: Path) -> Tuple[bytes, int, int, int]:
    st = path.stat()
    return path.read_bytes(), st.st_size, st.st_mtime_ns, stat.S_IMODE(st.st_mode)


def _no_sidecars(path: Path) -> None:
    for suffix in ("-wal", "-shm", "-journal"):
        assert not Path(str(path) + suffix).exists()


class TestM2MRegistryBackup(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.backup_doc = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
        cls.transcript_doc = json.loads(TRANSCRIPT_PATH.read_text(encoding="utf-8"))
        cls.vectors = {v["vector_id"]: v for v in cls.backup_doc["backup_vectors"]}
        cls.transcripts = {
            **{v["vector_id"]: v for v in cls.transcript_doc["valid_transcripts"]},
            **{v["vector_id"]: v for v in cls.transcript_doc["invalid_transcripts"]},
        }

    def _db_path(self, tmp: str, name: str) -> Path:
        return Path(tmp) / name

    def _envelopes(self, transcript_vector_id: str) -> List[Dict[str, Any]]:
        return list(self.transcripts[transcript_vector_id]["envelopes"])

    def _create_empty(self, path: Path) -> None:
        with ReplayRegistry(path, create=True):
            pass

    def _record(self, path: Path, transcript_vector_id: str, *, require_terminal: bool = False) -> None:
        with ReplayRegistry(path, create=True) as reg:
            reg.check_and_record(
                self._envelopes(transcript_vector_id),
                require_terminal=require_terminal,
            )

    def _record_sequence(
        self,
        path: Path,
        transcript_vector_ids: Sequence[str],
        *,
        require_terminal: bool = False,
    ) -> None:
        reg = ReplayRegistry(path, create=True)
        try:
            for tid in transcript_vector_ids:
                reg.check_and_record(
                    self._envelopes(tid),
                    require_terminal=require_terminal,
                )
        finally:
            reg.close()

    def _setup_registry(self, tmp: str, setup: str, vec: Dict[str, Any], *, name: str) -> Path:
        path = self._db_path(tmp, name)
        if setup == "create_empty":
            self._create_empty(path)
            return path
        if setup == "record_transcript":
            self._record(
                path,
                vec["source_transcript_vector_id"],
                require_terminal=bool(vec.get("require_terminal", False)),
            )
            return path
        if setup == "record_sequence":
            self._record_sequence(
                path,
                vec["source_transcript_vector_ids"],
                require_terminal=bool(vec.get("require_terminal", False)),
            )
            return path
        if setup == "non_sqlite_file":
            path.write_text("not-a-database", encoding="utf-8")
            return path
        if setup == "corrupt_schema_version":
            self._record(path, "valid_partial_quoted")
            conn = sqlite3.connect(str(path))
            try:
                conn.execute(
                    "UPDATE registry_metadata SET value = ? WHERE key = 'schema_version'",
                    ("999",),
                )
                conn.commit()
            finally:
                conn.close()
            return path
        if setup == "foreign_key_violation":
            self._record(path, "valid_partial_quoted")
            conn = sqlite3.connect(str(path))
            try:
                conn.execute("PRAGMA foreign_keys=OFF")
                conn.execute(
                    "INSERT INTO messages(message_id, exchange_hash, ordinal, previous_message_id) "
                    "VALUES (?, ?, ?, ?)",
                    ("f" * 64, "0" * 64, 0, None),
                )
                conn.commit()
            finally:
                conn.close()
            return path
        if setup == "message_count_mismatch":
            self._record(path, "valid_partial_quoted")
            conn = sqlite3.connect(str(path))
            try:
                conn.execute("UPDATE exchanges SET message_count = 99")
                conn.commit()
            finally:
                conn.close()
            return path
        if setup == "symlink_source":
            target = self._db_path(tmp, "real_source.sqlite3")
            self._create_empty(target)
            os.symlink(target.name, path)
            return path
        if setup == "symlink_backup":
            target = self._db_path(tmp, "real_backup.sqlite3")
            self._create_empty(target)
            os.symlink(target.name, path)
            return path
        self.fail(f"unknown setup {setup}")

    def _resolve_path_setup(
        self,
        tmp: str,
        setup: str,
        *,
        peer: Optional[Path] = None,
        name: str = "dest.sqlite3",
    ) -> Path:
        if setup == "relative_path":
            return Path("relative.sqlite3")
        if setup == "inside_repository":
            return ROOT / "forbidden_backup.sqlite3"
        if setup == "missing_path":
            return Path(tmp) / "missing.sqlite3"
        if setup == "destination_exists":
            path = self._db_path(tmp, name)
            path.write_text("occupied", encoding="utf-8")
            return path
        if setup == "same_as_source":
            assert peer is not None
            return peer
        if setup == "same_as_backup":
            assert peer is not None
            return peer
        if setup == "directory_path":
            return Path(tmp)
        if setup == "fifo_path":
            fifo = self._db_path(tmp, "pipe.fifo")
            try:
                os.mkfifo(fifo)
            except (AttributeError, OSError):
                self.skipTest("mkfifo unavailable")
            return fifo
        self.fail(f"unknown path setup {setup}")

    def _backup_cli(
        self,
        source: Path,
        destination: Path,
        *,
        pretty: bool = False,
    ) -> Tuple[int, Dict[str, Any], str, str]:
        args = ["backup", "--source", str(source), "--destination", str(destination)]
        if pretty:
            args.append("--pretty")
        code, out, err = _run(args)
        report = _parse_single_json_object(out) if out else {}
        return code, report, out, err

    def _restore_cli(
        self,
        backup: Path,
        destination: Path,
        *,
        pretty: bool = False,
    ) -> Tuple[int, Dict[str, Any], str, str]:
        args = ["restore", "--backup", str(backup), "--destination", str(destination)]
        if pretty:
            args.append("--pretty")
        code, out, err = _run(args)
        report = _parse_single_json_object(out) if out else {}
        return code, report, out, err

    def _assert_unchanged(self, path: Path, before: Tuple[bytes, int, int, int]) -> None:
        after = _file_snapshot(path)
        self.assertEqual(after, before)
        _no_sidecars(path)

    def _assert_report_contract(self, report: Dict[str, Any], vec: Dict[str, Any]) -> None:
        self.assertEqual(report.get("profile"), PROFILE)
        self.assertEqual(report.get("report_version"), REPORT_VERSION)
        self.assertEqual(report.get("code"), vec["expected_code"])
        self.assertEqual(report.get("ok"), vec["expected_ok"])
        self.assertEqual(report.get("operation"), vec["operation"])
        self.assertEqual(
            report.get("destination_created"),
            vec.get("expected_destination_created", False),
        )
        if "expected_exchange_count" in vec:
            self.assertEqual(report.get("exchange_count"), vec["expected_exchange_count"])
        if "expected_message_count" in vec:
            self.assertEqual(report.get("message_count"), vec["expected_message_count"])
        if vec["expected_ok"]:
            self.assertIsNotNone(report.get("logical_registry_digest"))
            self.assertIsNotNone(report.get("artifact_sha256"))
            self.assertGreater(report.get("artifact_size_bytes", 0), 0)
            self.assertIsNotNone(report.get("input_audit_report_id"))
            self.assertIsNotNone(report.get("output_audit_report_id"))
        body = {k: v for k, v in report.items() if k != "report_id"}
        self.assertEqual(compute_backup_report_id(body), report["report_id"])
        for key in REPORT_FIELD_ORDER:
            self.assertIn(key, report)

    def _run_vector(self, vector_id: str) -> None:
        vec = self.vectors[vector_id]
        operation = vec["operation"]
        with tempfile.TemporaryDirectory() as tmp:
            if operation == "backup":
                if vec.get("setup") in {
                    "missing_path",
                    "relative_path",
                    "inside_repository",
                    "directory_path",
                    "fifo_path",
                } and vec.get("path_role") == "source":
                    source = self._resolve_path_setup(tmp, vec["setup"], name="source.sqlite3")
                elif vec.get("setup") == "symlink_source":
                    source = self._setup_registry(tmp, "symlink_source", vec, name="link_source.sqlite3")
                else:
                    source = self._setup_registry(
                        tmp,
                        vec["setup"],
                        vec,
                        name="source.sqlite3",
                    )
                if vec.get("destination_setup") == "same_as_source":
                    destination = source
                elif vec.get("destination_setup"):
                    destination = self._resolve_path_setup(
                        tmp,
                        vec["destination_setup"],
                        peer=source,
                        name="backup.sqlite3",
                    )
                else:
                    destination = self._db_path(tmp, "backup.sqlite3")

                before = _file_snapshot(source) if source.exists() and source.is_file() else None
                code, report, out, err = self._backup_cli(source, destination)
                self.assertEqual(code, vec["expected_exit_code"], out)
                self._assert_report_contract(report, vec)
                self.assertEqual(err, "")
                if before is not None:
                    self._assert_unchanged(source, before)
                if vec["expected_ok"]:
                    self.assertTrue(destination.exists())
                    if os.name == "posix":
                        self.assertEqual(stat.S_IMODE(os.stat(destination).st_mode), 0o600)
                    _no_sidecars(destination)
                elif vec.get("destination_setup") not in {
                    "destination_exists",
                    "same_as_source",
                    "same_as_backup",
                }:
                    self.assertFalse(destination.exists())

            elif operation == "restore":
                if vec.get("source_setup"):
                    source = self._setup_registry(
                        tmp,
                        vec["source_setup"],
                        vec,
                        name="source.sqlite3",
                    )
                    backup = self._db_path(tmp, "backup.sqlite3")
                    pre = create_registry_backup(source, backup)
                    self.assertTrue(pre.ok, pre.code)
                    if vec.get("destination_setup") == "same_as_backup":
                        destination = backup
                    elif vec.get("destination_setup"):
                        destination = self._resolve_path_setup(
                            tmp,
                            vec["destination_setup"],
                            peer=backup,
                            name="restored.sqlite3",
                        )
                    else:
                        destination = self._db_path(tmp, "restored.sqlite3")
                    backup_before = _file_snapshot(backup)
                else:
                    if vec.get("setup") in {
                        "missing_path",
                        "relative_path",
                    } and vec.get("path_role") == "backup":
                        backup = self._resolve_path_setup(tmp, vec["setup"], name="backup.sqlite3")
                    elif vec.get("setup") == "symlink_backup":
                        backup = self._setup_registry(
                            tmp,
                            "symlink_backup",
                            vec,
                            name="link_backup.sqlite3",
                        )
                    else:
                        backup = self._setup_registry(
                            tmp,
                            vec["setup"],
                            vec,
                            name="backup.sqlite3",
                        )
                    destination = self._db_path(tmp, "restored.sqlite3")
                    backup_before = _file_snapshot(backup) if backup.exists() and backup.is_file() else None

                code, report, out, err = self._restore_cli(backup, destination)
                self.assertEqual(code, vec["expected_exit_code"], out)
                self._assert_report_contract(report, vec)
                self.assertEqual(err, "")
                if backup_before is not None:
                    self._assert_unchanged(backup, backup_before)
                if vec["expected_ok"]:
                    self.assertTrue(destination.exists())
                    if os.name == "posix":
                        self.assertEqual(stat.S_IMODE(os.stat(destination).st_mode), 0o600)
                    _no_sidecars(destination)
                elif vec.get("destination_setup") not in {
                    "destination_exists",
                    "same_as_source",
                    "same_as_backup",
                }:
                    self.assertFalse(destination.exists())
            else:
                self.fail(f"unknown operation {operation}")

    def test_vector_metadata(self):
        self.assertTrue(self.backup_doc["test_only"])
        self.assertFalse(self.backup_doc["live"])
        self.assertEqual(self.backup_doc["foundation"], "12")
        self.assertEqual(len(self.vectors), 32)

    def test_stable_codes_exact_set(self):
        self.assertEqual(STABLE_CODES, EXPECTED_STABLE_CODES)
        self.assertEqual(len(STABLE_CODES), 23)

    def test_vector_backup_healthy_empty(self):
        self._run_vector("backup_healthy_empty")

    def test_vector_backup_healthy_one_exchange(self):
        self._run_vector("backup_healthy_one_exchange")

    def test_vector_backup_healthy_extended(self):
        self._run_vector("backup_healthy_extended")

    def test_vector_backup_healthy_terminal(self):
        self._run_vector("backup_healthy_terminal")

    def test_vector_restore_healthy_empty(self):
        self._run_vector("restore_healthy_empty")

    def test_vector_restore_healthy_one_exchange(self):
        self._run_vector("restore_healthy_one_exchange")

    def test_vector_restore_healthy_extended(self):
        self._run_vector("restore_healthy_extended")

    def test_vector_restore_healthy_terminal(self):
        self._run_vector("restore_healthy_terminal")

    def test_vector_backup_missing_source(self):
        self._run_vector("backup_missing_source")

    def test_vector_backup_relative_source(self):
        self._run_vector("backup_relative_source")

    def test_vector_backup_relative_destination(self):
        self._run_vector("backup_relative_destination")

    def test_vector_backup_inside_repository_source(self):
        self._run_vector("backup_inside_repository_source")

    def test_vector_backup_inside_repository_destination(self):
        self._run_vector("backup_inside_repository_destination")

    def test_vector_backup_destination_exists(self):
        self._run_vector("backup_destination_exists")

    def test_vector_backup_same_file(self):
        self._run_vector("backup_same_file")

    def test_vector_backup_symlink_source(self):
        self._run_vector("backup_symlink_source")

    def test_vector_backup_directory_source(self):
        self._run_vector("backup_directory_source")

    def test_vector_backup_fifo_source(self):
        self._run_vector("backup_fifo_source")

    def test_vector_restore_missing_backup(self):
        self._run_vector("restore_missing_backup")

    def test_vector_restore_relative_backup(self):
        self._run_vector("restore_relative_backup")

    def test_vector_restore_relative_destination(self):
        self._run_vector("restore_relative_destination")

    def test_vector_restore_destination_exists(self):
        self._run_vector("restore_destination_exists")

    def test_vector_restore_same_file(self):
        self._run_vector("restore_same_file")

    def test_vector_restore_symlink_backup(self):
        self._run_vector("restore_symlink_backup")

    def test_vector_restore_inside_repository_destination(self):
        self._run_vector("restore_inside_repository_destination")

    def test_vector_backup_non_sqlite_source(self):
        self._run_vector("backup_non_sqlite_source")

    def test_vector_backup_wrong_schema(self):
        self._run_vector("backup_wrong_schema")

    def test_vector_backup_foreign_key_violation(self):
        self._run_vector("backup_foreign_key_violation")

    def test_vector_backup_message_count_mismatch(self):
        self._run_vector("backup_message_count_mismatch")

    def test_vector_restore_non_sqlite_backup(self):
        self._run_vector("restore_non_sqlite_backup")

    def test_vector_restore_wrong_schema(self):
        self._run_vector("restore_wrong_schema")

    def test_vector_restore_corrupt_integrity(self):
        self._run_vector("restore_corrupt_integrity")

    def test_result_immutability(self):
        result = RegistryBackupResult(
            ok=True,
            code="backup_created",
            operation="backup",
            destination_created=True,
            schema_version=1,
            exchange_count=0,
            message_count=0,
            logical_registry_digest="a" * 64,
            input_audit_report_id="b" * 64,
            output_audit_report_id="c" * 64,
            artifact_sha256="d" * 64,
            artifact_size_bytes=1234,
            report_id="e" * 64,
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.ok = False  # type: ignore[misc]

    def test_report_id_recomputation(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._db_path(tmp, "source.sqlite3")
            dest = self._db_path(tmp, "backup.sqlite3")
            self._record(source, "valid_partial_quoted")
            result = create_registry_backup(source, dest)
        self.assertTrue(result.ok)
        report = build_report(result)
        body = {k: v for k, v in report.items() if k != "report_id"}
        self.assertEqual(compute_backup_report_id(body), report["report_id"])
        self.assertEqual(result.report_id, report["report_id"])

    def test_deterministic_repeated_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._db_path(tmp, "source.sqlite3")
            dest1 = self._db_path(tmp, "backup1.sqlite3")
            dest2 = self._db_path(tmp, "backup2.sqlite3")
            self._record(source, "valid_partial_quoted")
            before = _file_snapshot(source)
            c1, out1, err1 = _run(
                ["backup", "--source", str(source), "--destination", str(dest1)]
            )
            c2, out2, err2 = _run(
                ["backup", "--source", str(source), "--destination", str(dest2)]
            )
            self.assertEqual(c1, EXIT_PASS)
            self.assertEqual(c2, EXIT_PASS)
            self.assertEqual(err1, "")
            self.assertEqual(err2, "")
            self.assertEqual(_parse_single_json_object(out1), _parse_single_json_object(out2))
            self._assert_unchanged(source, before)

    def test_compact_and_pretty_equivalent(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._db_path(tmp, "source.sqlite3")
            dest = self._db_path(tmp, "backup.sqlite3")
            self._record(source, "valid_partial_quoted")
            c1, out1, e1 = _run(
                ["backup", "--source", str(source), "--destination", str(dest)]
            )
            dest.unlink()
            c2, out2, e2 = _run(
                [
                    "backup",
                    "--source",
                    str(source),
                    "--destination",
                    str(dest),
                    "--pretty",
                ]
            )
        self.assertEqual(e1, "")
        self.assertEqual(e2, "")
        self.assertEqual(c1, EXIT_PASS)
        self.assertEqual(c2, EXIT_PASS)
        self.assertEqual(_parse_single_json_object(out1), _parse_single_json_object(out2))
        self.assertNotIn("\n  ", out1)
        self.assertIn("\n  ", out2)

    def test_restore_preserves_replay_idempotency(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._db_path(tmp, "source.sqlite3")
            backup = self._db_path(tmp, "backup.sqlite3")
            restored = self._db_path(tmp, "restored.sqlite3")
            envelopes = self._envelopes("valid_partial_quoted")
            with ReplayRegistry(source, create=True) as reg:
                first = reg.check_and_record(envelopes, require_terminal=False)
                self.assertEqual(first.code, "recorded_new")
            self.assertTrue(create_registry_backup(source, backup).ok)
            self.assertTrue(restore_registry_backup(backup, restored).ok)
            with ReplayRegistry(restored, create=False) as reg2:
                again = reg2.check_and_record(envelopes, require_terminal=False)
                self.assertEqual(again.code, "already_recorded")
                self.assertEqual(reg2.count_exchanges(), 1)
                self.assertEqual(reg2.count_messages(), 2)

    def test_restore_terminal_exchange_idempotency(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._db_path(tmp, "source.sqlite3")
            backup = self._db_path(tmp, "backup.sqlite3")
            restored = self._db_path(tmp, "restored.sqlite3")
            envelopes = self._envelopes("valid_terminal_cancelled")
            with ReplayRegistry(source, create=True) as reg:
                first = reg.check_and_record(envelopes, require_terminal=True)
                self.assertEqual(first.code, "recorded_new")
            self.assertTrue(create_registry_backup(source, backup).ok)
            self.assertTrue(restore_registry_backup(backup, restored).ok)
            with ReplayRegistry(restored, create=False) as reg2:
                again = reg2.check_and_record(envelopes, require_terminal=True)
                self.assertEqual(again.code, "already_recorded")

    def test_no_path_sql_exception_leakage(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._db_path(tmp, "source.sqlite3")
            dest = self._db_path(tmp, "backup.sqlite3")
            self._record(source, "valid_partial_quoted")
            code, out, err = _run(
                ["backup", "--source", str(source), "--destination", str(dest)]
            )
        self.assertEqual(code, EXIT_PASS)
        blob = out + err
        self.assertNotIn(str(source), blob)
        self.assertNotIn(str(dest), blob)
        self.assertNotIn(str(tmp), blob)
        for marker in LEAK_MARKERS:
            self.assertNotIn(marker, blob)

    def test_no_sqlite_sidecar_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._db_path(tmp, "source.sqlite3")
            backup = self._db_path(tmp, "backup.sqlite3")
            restored = self._db_path(tmp, "restored.sqlite3")
            self._create_empty(source)
            self.assertTrue(create_registry_backup(source, backup).ok)
            self.assertTrue(restore_registry_backup(backup, restored).ok)
            for path in (source, backup, restored):
                _no_sidecars(path)

    def test_source_and_backup_bytes_unchanged_after_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._db_path(tmp, "source.sqlite3")
            backup = self._db_path(tmp, "backup.sqlite3")
            restored = self._db_path(tmp, "restored.sqlite3")
            self._record_sequence(
                source,
                ["valid_partial_quoted", "valid_happy_path_completed"],
            )
            source_before = _file_snapshot(source)
            backup_before = None
            self.assertTrue(create_registry_backup(source, backup).ok)
            backup_before = _file_snapshot(backup)
            self.assertTrue(restore_registry_backup(backup, restored).ok)
            self._assert_unchanged(source, source_before)
            assert backup_before is not None
            self._assert_unchanged(backup, backup_before)

    def test_version_output(self):
        code, out, err = _run(["--version"])
        self.assertEqual(code, EXIT_PASS)
        self.assertEqual(err, "")
        self.assertEqual(out, CLI_VERSION + "\n")

    def test_missing_subcommand_usage(self):
        code, out, err = _run([])
        self.assertEqual(code, EXIT_USAGE)
        self.assertEqual(out, "")
        self.assertIn("usage:", err.lower())

    def test_version_with_subcommand_usage(self):
        code, out, err = _run(["--version", "backup"])
        self.assertEqual(code, EXIT_USAGE)
        self.assertEqual(out, "")
        self.assertIn("usage:", err.lower())

    def test_exit_codes_path_vs_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.sqlite3"
            dest = Path(tmp) / "backup.sqlite3"
            code_missing, report_missing, _, _ = self._backup_cli(missing, dest)
            self.assertEqual(code_missing, EXIT_USAGE)
            self.assertEqual(report_missing["code"], "source_not_found")

            bad = self._db_path(tmp, "bad.bin")
            bad.write_text("not-a-database", encoding="utf-8")
            code_bad, report_bad, _, _ = self._backup_cli(bad, dest)
        self.assertEqual(code_bad, EXIT_FAILURE)
        self.assertEqual(report_bad["code"], "source_audit_failed")

    def test_domain_backup_report_constant(self):
        self.assertEqual(
            DOMAIN_BACKUP_REPORT,
            b"L28-M2M-V0.1-REGISTRY-BACKUP-REPORT\x00",
        )

    def test_ast_no_forbidden_apis(self):
        for path in (BACKUP_PATH, CLI_PATH):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split(".")[0]
                        if root in FORBIDDEN_IMPORT_MODULES:
                            self.fail(f"{path.name} imports {alias.name}")
                if isinstance(node, ast.ImportFrom):
                    if node.module:
                        root = node.module.split(".")[0]
                        if root in FORBIDDEN_IMPORT_MODULES:
                            self.fail(f"{path.name} imports from {node.module}")
                    for alias in node.names:
                        if alias.name in FORBIDDEN_IMPORT_NAMES:
                            self.fail(f"{path.name} imports {alias.name}")
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr in FORBIDDEN_CALL_ATTRS:
                        self.fail(f"{path.name} calls {node.func.attr}()")
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("Ed25519PrivateKey", text)

    def test_vector_keys_no_private_material(self):
        keys: Set[str] = set()
        _collect_keys(self.backup_doc, keys)
        offenders = sorted(k for k in keys if k.lower() in FORBIDDEN_VECTOR_KEYS)
        self.assertEqual(offenders, [])

    def test_no_repo_database_or_report_files(self):
        self.assertFalse(any(ROOT.glob("*.sqlite3")))
        self.assertFalse(any(ROOT.glob("forbidden_backup.sqlite3")))
        self.assertFalse(any(ROOT.glob("l28-m2m-registry-backup-report*")))

    def test_grill_backup_uses_readonly_not_immutable(self):
        src = BACKUP_PATH.read_text(encoding="utf-8")
        self.assertIn("mode=ro", src)
        self.assertNotIn("immutable=1", src)
        self.assertIn("PRAGMA query_only=ON", src)
        self.assertIn("PRAGMA trusted_schema=OFF", src)

    def test_grill_report_excludes_stored_identifiers(self):
        envelopes = self._envelopes("valid_partial_quoted")
        message_ids = [e["message_id"] for e in envelopes]
        with tempfile.TemporaryDirectory() as tmp:
            source = self._db_path(tmp, "source.sqlite3")
            dest = self._db_path(tmp, "backup.sqlite3")
            self._record(source, "valid_partial_quoted")
            _, out, _ = _run(
                ["backup", "--source", str(source), "--destination", str(dest)]
            )
        report = _parse_single_json_object(out)
        blob = json.dumps(report)
        for mid in message_ids:
            self.assertNotIn(mid, blob)
        self.assertNotIn("transaction_id", blob)
        self.assertNotIn("sender_public_key", blob)


class TestM2MRegistryBackupGrill(unittest.TestCase):
    def _db_path(self, tmp: str, name: str = "registry.sqlite3") -> Path:
        return Path(tmp) / name

    def _create_empty(self, path: Path) -> None:
        with ReplayRegistry(path, create=True):
            pass

    def test_source_changed_during_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._db_path(tmp, "source.sqlite3")
            dest = self._db_path(tmp, "backup.sqlite3")
            self._create_empty(source)
            identities = list(coin.m2m_registry_backup._file_identity(source) for _ in range(2))
            assert identities[0] is not None
            changed = coin.m2m_registry_backup._FileIdentity(
                size=identities[0].size + 1,
                mtime_ns=identities[0].mtime_ns,
                mode=identities[0].mode,
                inode=identities[0].inode,
                dev=identities[0].dev,
                sha256=identities[0].sha256,
            )
            with patch(
                "coin.m2m_registry_backup._file_identity",
                side_effect=[identities[0], changed],
            ):
                result = create_registry_backup(source, dest)
            self.assertFalse(result.ok)
            self.assertEqual(result.code, "source_changed")
            self.assertFalse(dest.exists())

    def test_backup_changed_during_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            backup = self._db_path(tmp, "backup.sqlite3")
            dest = self._db_path(tmp, "restored.sqlite3")
            self._create_empty(backup)
            before = coin.m2m_registry_backup._file_identity(backup)
            assert before is not None
            changed = coin.m2m_registry_backup._FileIdentity(
                size=before.size + 1,
                mtime_ns=before.mtime_ns,
                mode=before.mode,
                inode=before.inode,
                dev=before.dev,
                sha256=before.sha256,
            )
            with patch(
                "coin.m2m_registry_backup._file_identity",
                side_effect=[before, before, changed],
            ):
                result = restore_registry_backup(backup, dest)
            self.assertFalse(result.ok)
            self.assertEqual(result.code, "backup_changed")
            self.assertFalse(dest.exists())

    def test_destination_race_never_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._db_path(tmp, "source.sqlite3")
            dest = self._db_path(tmp, "backup.sqlite3")
            self._create_empty(source)
            sentinel = b"RACE-SENTINEL-BYTES-UNCHANGED"
            real_link = os.link

            def race_link(src: str, dst: str, *, follow_symlinks: bool = True) -> None:
                race_path = Path(dst)
                if not race_path.exists():
                    race_path.write_bytes(sentinel)
                    os.chmod(race_path, 0o644)
                return real_link(src, dst, follow_symlinks=follow_symlinks)

            with patch("coin.m2m_registry_backup.os.link", side_effect=race_link):
                result = create_registry_backup(source, dest)

            self.assertFalse(result.ok)
            self.assertEqual(result.code, "destination_exists")
            self.assertFalse(result.destination_created)
            self.assertEqual(dest.read_bytes(), sentinel)
            st = dest.stat()
            self.assertEqual(stat.S_IMODE(st.st_mode), 0o644)
            race_inode = st.st_ino
            self.assertEqual(list(dest.parent.glob(".m2m-registry-work-*")), [])

            with patch("coin.m2m_registry_backup.os.link", side_effect=race_link):
                result2 = restore_registry_backup(source, dest)
            self.assertEqual(result2.code, "destination_exists")
            self.assertEqual(dest.read_bytes(), sentinel)
            self.assertEqual(dest.stat().st_ino, race_inode)

    def test_no_partial_destination_before_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._db_path(tmp, "source.sqlite3")
            dest = self._db_path(tmp, "backup.sqlite3")
            self._create_empty(source)
            observed: List[bool] = []

            original_publish = coin.m2m_registry_backup._publish_atomic

            def observe_publish(temp: Path, destination: Path):
                observed.append(destination.exists())
                return original_publish(temp, destination)

            with patch(
                "coin.m2m_registry_backup._publish_atomic",
                side_effect=observe_publish,
            ):
                result = create_registry_backup(source, dest)
            self.assertTrue(result.ok)
            self.assertFalse(any(observed))

    def test_publish_uses_link_not_rename_or_replace(self):
        src = BACKUP_PATH.read_text(encoding="utf-8")
        self.assertIn("os.link(", src)
        self.assertNotIn("os.rename(", src)
        self.assertNotIn("os.replace(", src)

    def test_successful_publication_single_destination_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._db_path(tmp, "source.sqlite3")
            dest = self._db_path(tmp, "backup.sqlite3")
            self._create_empty(source)
            result = create_registry_backup(source, dest)
            self.assertTrue(result.ok)
            self.assertTrue(dest.exists())
            self.assertEqual(dest.stat().st_nlink, 1)
            self.assertEqual(list(dest.parent.glob(".m2m-registry-work-*")), [])

    def test_unsupported_hard_link_publication_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._db_path(tmp, "source.sqlite3")
            dest = self._db_path(tmp, "backup.sqlite3")
            self._create_empty(source)

            def fail_link(*_args, **_kwargs):
                raise OSError(errno.ENOTSUP, "link not supported")

            with patch("coin.m2m_registry_backup.os.link", side_effect=fail_link):
                backup_result = create_registry_backup(source, dest)
            self.assertFalse(backup_result.ok)
            self.assertEqual(backup_result.code, "publish_failed")
            self.assertFalse(dest.exists())
            self.assertEqual(list(dest.parent.glob(".m2m-registry-work-*")), [])

            backup = self._db_path(tmp, "existing-backup.sqlite3")
            restored = self._db_path(tmp, "restored.sqlite3")
            self.assertTrue(create_registry_backup(source, backup).ok)
            with patch("coin.m2m_registry_backup.os.link", side_effect=fail_link):
                restore_result = restore_registry_backup(backup, restored)
            self.assertEqual(restore_result.code, "publish_failed")
            self.assertFalse(restored.exists())

    def test_backup_and_restore_share_publish_primitive(self):
        import inspect

        self.assertIn("_publish_atomic(", inspect.getsource(create_registry_backup))
        self.assertIn("_publish_atomic(", inspect.getsource(restore_registry_backup))
        module_src = BACKUP_PATH.read_text(encoding="utf-8")
        self.assertEqual(module_src.count("def _publish_atomic("), 1)

    def test_cleanup_after_backup_copy_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._db_path(tmp, "source.sqlite3")
            dest = self._db_path(tmp, "backup.sqlite3")
            self._create_empty(source)
            parent = dest.parent
            with patch(
                "coin.m2m_registry_backup._sqlite_backup",
                return_value="backup_failed",
            ):
                result = create_registry_backup(source, dest)
            self.assertEqual(result.code, "backup_failed")
            self.assertFalse(dest.exists())
            temps = list(parent.glob(".m2m-registry-work-*"))
            self.assertEqual(temps, [])

    def test_cleanup_after_temp_audit_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._db_path(tmp, "source.sqlite3")
            dest = self._db_path(tmp, "backup.sqlite3")
            self._create_empty(source)
            parent = dest.parent
            healthy = audit_registry(source)
            calls = {"n": 0}

            def audit_side_effect(path: Path):
                calls["n"] += 1
                if calls["n"] == 1:
                    return healthy
                return RegistryAuditResult(
                    ok=False,
                    code="registry_integrity_error",
                    failed_check="injected",
                )

            with patch("coin.m2m_registry_backup.audit_registry", side_effect=audit_side_effect):
                result = create_registry_backup(source, dest)
            self.assertEqual(result.code, "backup_audit_failed")
            self.assertFalse(dest.exists())
            temps = list(parent.glob(".m2m-registry-work-*"))
            self.assertEqual(temps, [])


if __name__ == "__main__":
    unittest.main()
