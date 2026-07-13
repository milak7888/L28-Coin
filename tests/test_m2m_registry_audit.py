# SPDX-License-Identifier: Apache-2.0
"""
Offline tests for Foundation 10 M2M replay-registry audit.

All SQLite files use TemporaryDirectory paths outside the repository.
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
from unittest.mock import patch

from coin.m2m_registry_audit import (
    DOMAIN_LOGICAL,
    MAX_REGISTRY_EXCHANGES,
    MAX_REGISTRY_FILE_BYTES,
    RegistryAuditResult,
    STABLE_CODES,
    audit_registry,
    compute_logical_registry_digest,
)
from coin.m2m_registry_audit_cli import (
    CLI_VERSION,
    PROFILE,
    REPORT_VERSION,
    compute_report_id,
)
from coin.m2m_replay_registry import ReplayRegistry

ROOT = Path(__file__).resolve().parents[1]
VECTOR_PATH = ROOT / "docs" / "m2m" / "test_vectors_registry_audit_v0.1.json"
TRANSCRIPT_PATH = ROOT / "docs" / "m2m" / "test_vectors_transcript_v0.1.json"
AUDIT_PATH = ROOT / "coin" / "m2m_registry_audit.py"
CLI_PATH = ROOT / "coin" / "m2m_registry_audit_cli.py"
CLI_MODULE = "coin.m2m_registry_audit_cli"

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
    "Traceback",
    "Exception",
    "sqlite",
    "SQL",
    "INSERT",
    "UPDATE",
    "DELETE",
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


class TestM2MRegistryAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit_doc = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
        cls.transcript_doc = json.loads(TRANSCRIPT_PATH.read_text(encoding="utf-8"))
        cls.vectors = {v["vector_id"]: v for v in cls.audit_doc["audit_vectors"]}
        cls.transcripts = {
            **{v["vector_id"]: v for v in cls.transcript_doc["valid_transcripts"]},
            **{v["vector_id"]: v for v in cls.transcript_doc["invalid_transcripts"]},
        }

    def _db_path(self, tmp: str, name: str = "audit.sqlite3") -> Path:
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
        first = True
        reg = ReplayRegistry(path, create=True)
        try:
            for tid in transcript_vector_ids:
                reg.check_and_record(
                    self._envelopes(tid),
                    require_terminal=require_terminal,
                )
                first = False
        finally:
            reg.close()

    def _audit_cli(self, path: Path, *, pretty: bool = False) -> Tuple[int, Dict[str, Any], str, str]:
        args = ["--registry", str(path)]
        if pretty:
            args.append("--pretty")
        code, out, err = _run(args)
        report = _parse_single_json_object(out) if out else {}
        return code, report, out, err

    def _assert_unchanged(self, path: Path, before: Tuple[bytes, int, int, int]) -> None:
        after = _file_snapshot(path)
        self.assertEqual(after, before)
        for suffix in ("-wal", "-shm", "-journal"):
            self.assertFalse(Path(str(path) + suffix).exists())

    def _setup_registry(self, tmp: str, setup: str, vec: Dict[str, Any]) -> Path:
        path = self._db_path(tmp)
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
        if setup == "extra_table":
            self._create_empty(path)
            conn = sqlite3.connect(str(path))
            try:
                conn.execute("CREATE TABLE extra_audit_table (id INTEGER)")
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
        if setup == "head_mismatch":
            self._record(path, "valid_partial_quoted")
            conn = sqlite3.connect(str(path))
            try:
                conn.execute("UPDATE exchanges SET head_message_id = ?", ("a" * 64,))
                conn.commit()
            finally:
                conn.close()
            return path
        if setup == "fingerprint_mismatch":
            self._record(path, "valid_partial_quoted")
            conn = sqlite3.connect(str(path))
            try:
                conn.execute(
                    "UPDATE exchanges SET transcript_fingerprint = ?",
                    ("b" * 64,),
                )
                conn.commit()
            finally:
                conn.close()
            return path
        if setup == "previous_chain_mismatch":
            self._record(path, "valid_partial_quoted")
            conn = sqlite3.connect(str(path))
            try:
                conn.execute(
                    "UPDATE messages SET previous_message_id = ? WHERE ordinal = 1",
                    ("c" * 64,),
                )
                conn.commit()
            finally:
                conn.close()
            return path
        if setup == "invalid_state":
            self._record(path, "valid_partial_quoted")
            conn = sqlite3.connect(str(path))
            try:
                conn.execute("UPDATE exchanges SET state = 'not_a_real_state'")
                conn.commit()
            finally:
                conn.close()
            return path
        self.fail(f"unknown setup {setup}")

    def _run_vector(self, vector_id: str) -> None:
        vec = self.vectors[vector_id]
        setup = vec.get("setup")
        with tempfile.TemporaryDirectory() as tmp:
            if setup == "missing_path":
                path = Path(tmp) / "missing.sqlite3"
            elif setup == "relative_path":
                path = Path("relative.sqlite3")
            elif setup == "inside_repository":
                path = ROOT / "forbidden_audit.sqlite3"
            else:
                path = self._setup_registry(tmp, setup, vec)

            before: Optional[Tuple[bytes, int, int, int]] = None
            if path.exists() and path.is_file():
                before = _file_snapshot(path)

            code, report, out, err = self._audit_cli(path)
            self.assertEqual(code, vec["expected_exit_code"], out)
            self.assertEqual(report.get("code"), vec["expected_code"])
            self.assertEqual(report.get("ok"), vec["expected_ok"])
            if "expected_exchange_count" in vec:
                self.assertEqual(report.get("exchange_count"), vec["expected_exchange_count"])
            if "expected_message_count" in vec:
                self.assertEqual(report.get("message_count"), vec["expected_message_count"])
            if "expected_terminal_exchange_count" in vec:
                self.assertEqual(
                    report.get("terminal_exchange_count"),
                    vec["expected_terminal_exchange_count"],
                )
            if "expected_nonterminal_exchange_count" in vec:
                self.assertEqual(
                    report.get("nonterminal_exchange_count"),
                    vec["expected_nonterminal_exchange_count"],
                )
            if "expected_failed_check" in vec:
                self.assertEqual(report.get("failed_check"), vec["expected_failed_check"])
            self.assertEqual(err, "")
            self.assertEqual(report.get("profile"), PROFILE)
            self.assertEqual(report.get("report_version"), REPORT_VERSION)
            if before is not None:
                self._assert_unchanged(path, before)

    def test_vector_metadata(self):
        self.assertTrue(self.audit_doc["test_only"])
        self.assertFalse(self.audit_doc["live"])
        self.assertEqual(len(self.vectors), 16)

    def test_stable_codes(self):
        required = {
            "registry_healthy",
            "invalid_registry_path",
            "registry_not_found",
            "unsafe_registry_path",
            "registry_unreadable",
            "registry_schema_mismatch",
            "registry_integrity_error",
            "registry_foreign_key_error",
            "registry_invariant_error",
            "internal_error",
        }
        self.assertTrue(required.issubset(STABLE_CODES))

    def test_vector_healthy_empty(self):
        self._run_vector("audit_healthy_empty")

    def test_vector_healthy_one_exchange(self):
        self._run_vector("audit_healthy_one_exchange")

    def test_vector_healthy_extended(self):
        self._run_vector("audit_healthy_extended")

    def test_vector_healthy_terminal(self):
        self._run_vector("audit_healthy_terminal")

    def test_vector_missing_registry(self):
        self._run_vector("audit_missing_registry")

    def test_vector_relative_path(self):
        self._run_vector("audit_relative_path")

    def test_vector_inside_repository(self):
        self._run_vector("audit_inside_repository")

    def test_vector_non_sqlite(self):
        self._run_vector("audit_non_sqlite")

    def test_vector_wrong_schema_version(self):
        self._run_vector("audit_wrong_schema_version")

    def test_vector_extra_table(self):
        self._run_vector("audit_extra_table")

    def test_vector_foreign_key_violation(self):
        self._run_vector("audit_foreign_key_violation")

    def test_vector_message_count_mismatch(self):
        self._run_vector("audit_message_count_mismatch")

    def test_vector_head_mismatch(self):
        self._run_vector("audit_head_mismatch")

    def test_vector_fingerprint_mismatch(self):
        self._run_vector("audit_fingerprint_mismatch")

    def test_vector_previous_chain_mismatch(self):
        self._run_vector("audit_previous_chain_mismatch")

    def test_vector_invalid_state(self):
        self._run_vector("audit_invalid_state")

    def test_deterministic_repeated_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            self._record(path, "valid_partial_quoted")
            before = _file_snapshot(path)
            c1, out1, err1 = _run(["--registry", str(path)])
            c2, out2, err2 = _run(["--registry", str(path)])
            self.assertEqual(c1, 0)
            self.assertEqual(c2, 0)
            self.assertEqual(err1, "")
            self.assertEqual(err2, "")
            self.assertEqual(out1, out2)
            self._assert_unchanged(path, before)

    def test_compact_and_pretty_equivalent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            self._record(path, "valid_partial_quoted")
            c1, out1, e1 = _run(["--registry", str(path)])
            c2, out2, e2 = _run(["--registry", str(path), "--pretty"])
        self.assertEqual(e1, "")
        self.assertEqual(e2, "")
        self.assertEqual(c1, 0)
        self.assertEqual(c2, 0)
        self.assertEqual(_parse_single_json_object(out1), _parse_single_json_object(out2))
        self.assertNotIn("\n  ", out1)
        self.assertIn("\n  ", out2)

    def test_logical_digest_recomputation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            self._record(path, "valid_partial_quoted")
            r1 = audit_registry(path)
            r2 = audit_registry(path)
        self.assertTrue(r1.ok)
        assert r1.logical_registry_digest is not None
        self.assertEqual(r1.logical_registry_digest, r2.logical_registry_digest)
        empty = compute_logical_registry_digest(schema_version=1, exchanges=[])
        self.assertEqual(len(empty), 64)

    def test_report_id_recomputation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            self._record(path, "valid_partial_quoted")
            _, out, _ = _run(["--registry", str(path)])
        report = _parse_single_json_object(out)
        body = {k: v for k, v in report.items() if k != "report_id"}
        self.assertEqual(compute_report_id(body), report["report_id"])

    def test_symlink_directory_fifo_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = self._db_path(tmp, "real.sqlite3")
            self._create_empty(target)
            link = self._db_path(tmp, "link.sqlite3")
            os.symlink(target.name, link)
            code, report, _, err = self._audit_cli(link)
            self.assertEqual(code, 2)
            self.assertEqual(report["code"], "unsafe_registry_path")
            self.assertEqual(err, "")
            self.assertNotIn(str(link), json.dumps(report))

            code2, report2, _, _ = self._audit_cli(Path(tmp))
            self.assertEqual(code2, 2)
            self.assertEqual(report2["code"], "unsafe_registry_path")

            fifo = self._db_path(tmp, "pipe.fifo")
            try:
                os.mkfifo(fifo)
            except (AttributeError, OSError):
                self.skipTest("mkfifo unavailable")
            code3, report3, _, _ = self._audit_cli(fifo)
            self.assertEqual(code3, 2)
            self.assertEqual(report3["code"], "unsafe_registry_path")

    def test_ordinal_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            self._record(path, "valid_partial_quoted")
            conn = sqlite3.connect(str(path))
            try:
                conn.execute("UPDATE messages SET ordinal = 5 WHERE ordinal = 1")
                conn.commit()
            finally:
                conn.close()
            result = audit_registry(path)
        self.assertEqual(result.code, "registry_invariant_error")
        self.assertEqual(result.failed_check, "ordinal_continuity")

    def test_malformed_hash_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            self._record(path, "valid_partial_quoted")
            conn = sqlite3.connect(str(path))
            try:
                conn.execute(
                    "UPDATE exchanges SET transcript_fingerprint = ?",
                    ("Z" * 64,),
                )
                conn.commit()
            finally:
                conn.close()
            result = audit_registry(path)
        self.assertEqual(result.code, "registry_invariant_error")
        self.assertEqual(result.failed_check, "malformed_fingerprint")

    def test_missing_column_schema_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            self._create_empty(path)
            conn = sqlite3.connect(str(path))
            try:
                conn.execute("ALTER TABLE exchanges RENAME TO exchanges_old")
                conn.execute(
                    "CREATE TABLE exchanges (exchange_hash TEXT PRIMARY KEY NOT NULL, state TEXT NOT NULL)"
                )
                conn.commit()
            finally:
                conn.close()
            result = audit_registry(path)
        self.assertEqual(result.code, "registry_schema_mismatch")
        self.assertIn(result.failed_check, ("schema_tables", "schema_columns"))

    def test_no_path_sql_exception_leakage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            self._record(path, "valid_partial_quoted")
            code, out, err = _run(["--registry", str(path)])
        self.assertEqual(code, 0)
        blob = out + err
        self.assertNotIn(str(path), blob)
        self.assertNotIn(str(tmp), blob)
        for marker in LEAK_MARKERS:
            self.assertNotIn(marker, blob)

    def test_no_registry_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            self._record(path, "valid_happy_path_completed", require_terminal=True)
            before = _file_snapshot(path)
            result = audit_registry(path)
            _run(["--registry", str(path)])
            after = _file_snapshot(path)
        self.assertTrue(result.ok)
        self.assertEqual(before, after)

    def test_no_sqlite_sidecar_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            self._create_empty(path)
            _run(["--registry", str(path)])
            for suffix in ("-wal", "-shm", "-journal"):
                self.assertFalse(Path(str(path) + suffix).exists())

    def test_version_output(self):
        code, out, err = _run(["--version"])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(out, CLI_VERSION + "\n")

    def test_missing_registry_argument_usage(self):
        code, out, err = _run([])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("usage:", err.lower())

    def test_exactly_one_stdout_json_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            self._create_empty(path)
            _, out, _ = _run(["--registry", str(path)])
        _parse_single_json_object(out)

    def test_domain_logical_constant(self):
        self.assertEqual(DOMAIN_LOGICAL, b"L28-M2M-V0.1-REGISTRY-LOGICAL\x00")

    def test_api_does_not_import_replay_registry_class(self):
        src = AUDIT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("ReplayRegistry", src)

    def test_ast_no_private_key_apis(self):
        for path in (AUDIT_PATH, CLI_PATH):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name in FORBIDDEN_IMPORT_NAMES:
                            self.fail(f"{path.name} imports {alias.name}")
        self.assertNotIn("Ed25519PrivateKey", AUDIT_PATH.read_text(encoding="utf-8"))
        self.assertNotIn("Ed25519PrivateKey", CLI_PATH.read_text(encoding="utf-8"))

    def test_vector_keys_no_private_material(self):
        keys: Set[str] = set()
        _collect_keys(self.audit_doc, keys)
        offenders = sorted(k for k in keys if k.lower() in FORBIDDEN_VECTOR_KEYS)
        self.assertEqual(offenders, [])

    def test_no_repo_database_or_report_files(self):
        self.assertFalse(any(ROOT.glob("*.sqlite3")))
        self.assertFalse(any(ROOT.glob("l28-m2m-registry-audit-report*")))

    def test_grill_symlink_replacement_rejected_at_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = self._db_path(tmp, "real.sqlite3")
            audited = self._db_path(tmp, "audited.sqlite3")
            self._create_empty(audited)
            self.assertTrue(audit_registry(audited).ok)
            os.remove(audited)
            os.symlink(real.name, audited)
            result = audit_registry(audited)
        self.assertEqual(result.code, "unsafe_registry_path")
        self.assertEqual(result.failed_check, "path_validation")

    def test_grill_oversized_registry_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            path.write_bytes(b"SQLite format 3\x00" + (b"\x00" * (MAX_REGISTRY_FILE_BYTES - 16 + 1)))
            result = audit_registry(path)
        self.assertEqual(result.code, "registry_unreadable")
        self.assertEqual(result.failed_check, "registry_bounds")

    def test_grill_rejects_view_objects(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            self._create_empty(path)
            conn = sqlite3.connect(str(path))
            try:
                conn.execute(
                    "CREATE VIEW leaked_metadata AS SELECT key, value FROM registry_metadata"
                )
                conn.commit()
            finally:
                conn.close()
            result = audit_registry(path)
        self.assertEqual(result.code, "registry_schema_mismatch")
        self.assertEqual(result.failed_check, "schema_objects")

    def test_grill_rejects_trigger_objects(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            self._create_empty(path)
            conn = sqlite3.connect(str(path))
            try:
                conn.execute(
                    "CREATE TRIGGER audit_trap AFTER INSERT ON messages BEGIN SELECT 1; END"
                )
                conn.commit()
            finally:
                conn.close()
            result = audit_registry(path)
        self.assertEqual(result.code, "registry_schema_mismatch")
        self.assertEqual(result.failed_check, "schema_objects")

    def test_grill_rejects_virtual_table_objects(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            self._create_empty(path)
            conn = sqlite3.connect(str(path))
            try:
                conn.execute("CREATE VIRTUAL TABLE evil USING fts5(content)")
                conn.commit()
            finally:
                conn.close()
            result = audit_registry(path)
        self.assertEqual(result.code, "registry_schema_mismatch")
        self.assertEqual(result.failed_check, "schema_objects")

    def test_grill_exchange_count_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            self._record(path, "valid_partial_quoted")
            with patch("coin.m2m_registry_audit.MAX_REGISTRY_EXCHANGES", 0):
                result = audit_registry(path)
        self.assertEqual(result.code, "registry_invariant_error")
        self.assertEqual(result.failed_check, "registry_bounds")

    def test_grill_unhealthy_never_ok_or_exit_zero(self):
        scenarios = [
            ("audit_non_sqlite", None),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bad = self._db_path(tmp, "bad.bin")
            bad.write_text("not-a-database", encoding="utf-8")
            code, report, _, _ = self._audit_cli(bad)
            self.assertNotEqual(code, 0)
            self.assertFalse(report["ok"])
            self.assertNotEqual(report["code"], "registry_healthy")

    def test_grill_path_failure_exit_two_integrity_exit_three(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.sqlite3"
            code_missing, report_missing, _, _ = self._audit_cli(missing)
            self.assertEqual(code_missing, 2)
            self.assertEqual(report_missing["code"], "registry_not_found")

            path = self._db_path(tmp)
            self._record(path, "valid_partial_quoted")
            conn = sqlite3.connect(str(path))
            try:
                conn.execute("UPDATE exchanges SET message_count = 99")
                conn.commit()
            finally:
                conn.close()
            code_bad, report_bad, _, _ = self._audit_cli(path)
        self.assertEqual(code_bad, 3)
        self.assertEqual(report_bad["code"], "registry_invariant_error")

    def test_grill_report_excludes_stored_identifiers(self):
        envelopes = self._envelopes("valid_partial_quoted")
        message_ids = [e["message_id"] for e in envelopes]
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            self._record(path, "valid_partial_quoted")
            _, out, _ = _run(["--registry", str(path)])
        report = _parse_single_json_object(out)
        blob = json.dumps(report)
        for mid in message_ids:
            self.assertNotIn(mid, blob)
        self.assertNotIn("transaction_id", blob)
        self.assertNotIn("sender_public_key", blob)

    def test_grill_immutable_readonly_open_uri(self):
        src = AUDIT_PATH.read_text(encoding="utf-8")
        self.assertIn("mode=ro&immutable=1", src)
        self.assertIn("PRAGMA query_only=ON", src)
        self.assertIn("PRAGMA trusted_schema=OFF", src)


if __name__ == "__main__":
    unittest.main()
