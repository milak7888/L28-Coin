# SPDX-License-Identifier: Apache-2.0
"""
Offline tests for Foundation 8 M2M replay/idempotency registry.

All SQLite files use TemporaryDirectory paths outside the repository.
"""
from __future__ import annotations

import ast
import json
import os
import sqlite3
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from coin.m2m_replay_registry import (
    SCHEMA_VERSION,
    STABLE_CODES,
    ReplayRegistry,
    ReplayRegistryError,
    exchange_hash_for,
    transcript_fingerprint_for,
)
from coin.m2m_transcript_validator import verify_transcript

ROOT = Path(__file__).resolve().parents[1]
VECTOR_PATH = ROOT / "docs" / "m2m" / "test_vectors_replay_v0.1.json"
TRANSCRIPT_PATH = ROOT / "docs" / "m2m" / "test_vectors_transcript_v0.1.json"
RUNTIME_PATH = ROOT / "coin" / "m2m_replay_registry.py"

FORBIDDEN_IMPORT_NAMES = frozenset({"Ed25519PrivateKey", "from_private_bytes"})
FORBIDDEN_STORAGE_TOKENS = (
    "private_key",
    "signature",
    "sender_public_key",
    "recipient_public_key",
    "sender_identity",
    "recipient_identity",
    "payload",
    "l28_test_account",
    "service_id",
)


def _collect_keys(obj: Any, out: Set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(str(k))
            _collect_keys(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_keys(item, out)


class TestM2MReplayRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.replay_doc = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
        cls.transcript_doc = json.loads(TRANSCRIPT_PATH.read_text(encoding="utf-8"))
        cls.transcripts = {
            **{v["vector_id"]: v for v in cls.transcript_doc["valid_transcripts"]},
            **{v["vector_id"]: v for v in cls.transcript_doc["invalid_transcripts"]},
        }
        cls.vectors = {v["vector_id"]: v for v in cls.replay_doc["replay_vectors"]}

    def _envelopes(self, transcript_vector_id: str) -> List[Dict[str, Any]]:
        return list(self.transcripts[transcript_vector_id]["envelopes"])

    def _db_path(self, tmp: str, name: str = "replay.sqlite3") -> Path:
        return Path(tmp) / name

    def test_metadata(self):
        self.assertTrue(self.replay_doc["test_only"])
        self.assertFalse(self.replay_doc["live"])
        self.assertFalse(self.replay_doc["accepted_settlement"])
        self.assertFalse(self.replay_doc["private_material_committed"])
        self.assertEqual(len(self.vectors), 12)

    def test_stable_codes(self):
        required = {
            "recorded_new",
            "recorded_extension",
            "already_recorded",
            "already_recorded_prefix",
            "verification_failed",
            "exchange_fork",
            "message_replay",
            "terminal_exchange_extension",
            "invalid_registry_path",
            "registry_path_not_absolute",
            "registry_inside_repository",
            "registry_symlink_rejected",
            "registry_not_regular_file",
            "registry_not_found",
            "registry_already_exists",
            "schema_version_mismatch",
            "registry_integrity_error",
            "registry_corrupt",
            "registry_locked",
            "registry_io_error",
            "internal_error",
        }
        self.assertTrue(required.issubset(STABLE_CODES))

    def test_explicit_creation_and_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            with self.assertRaises(ReplayRegistryError) as ctx:
                ReplayRegistry(path, create=False)
            self.assertEqual(ctx.exception.code, "registry_not_found")
            with ReplayRegistry(path, create=True) as reg:
                self.assertEqual(reg.count_exchanges(), 0)
            mode = stat.S_IMODE(os.stat(path).st_mode)
            if os.name == "posix":
                self.assertEqual(mode, 0o600)
            # Re-open existing.
            with ReplayRegistry(path, create=False) as reg2:
                self.assertEqual(reg2.count_messages(), 0)

    def test_absolute_path_and_repo_rejection(self):
        with self.assertRaises(ReplayRegistryError) as ctx:
            ReplayRegistry("relative.sqlite3", create=True)
        self.assertEqual(ctx.exception.code, "registry_path_not_absolute")
        inside = ROOT / "replay_forbidden.sqlite3"
        with self.assertRaises(ReplayRegistryError) as ctx2:
            ReplayRegistry(inside, create=True)
        self.assertEqual(ctx2.exception.code, "registry_inside_repository")
        self.assertFalse(inside.exists())

    def test_symlink_directory_fifo_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "real.sqlite3"
            link = Path(tmp) / "link.sqlite3"
            with ReplayRegistry(target, create=True):
                pass
            os.symlink(target.name, link)
            with self.assertRaises(ReplayRegistryError) as ctx:
                ReplayRegistry(link, create=False)
            self.assertEqual(ctx.exception.code, "registry_symlink_rejected")

            with self.assertRaises(ReplayRegistryError) as ctx2:
                ReplayRegistry(Path(tmp), create=False)
            self.assertEqual(ctx2.exception.code, "registry_not_regular_file")

            fifo = Path(tmp) / "pipe.fifo"
            try:
                os.mkfifo(fifo)
            except (AttributeError, OSError):
                self.skipTest("mkfifo unavailable")
            with self.assertRaises(ReplayRegistryError) as ctx3:
                ReplayRegistry(fifo, create=False)
            self.assertEqual(ctx3.exception.code, "registry_not_regular_file")

    def test_non_sqlite_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            path.write_text("not-a-database", encoding="utf-8")
            with self.assertRaises(ReplayRegistryError) as ctx:
                ReplayRegistry(path, create=True)
            self.assertEqual(ctx.exception.code, "registry_already_exists")

    def _run_vector(self, vector_id: str) -> None:
        vec = self.vectors[vector_id]
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            reg: Optional[ReplayRegistry] = None
            try:
                for step in vec["operations"]:
                    op = step["op"]
                    if op == "check_and_record":
                        if reg is None:
                            reg = ReplayRegistry(path, create=True)
                        envelopes = self._envelopes(step["source_transcript_vector_id"])
                        before = json.dumps(envelopes, sort_keys=True)
                        result = reg.check_and_record(
                            envelopes,
                            require_terminal=bool(step.get("require_terminal", False)),
                        )
                        after = json.dumps(envelopes, sort_keys=True)
                        self.assertEqual(before, after)
                        self.assertEqual(result.code, step["expected_code"])
                        self.assertEqual(result.newly_recorded, step["expected_newly_recorded"])
                        self.assertEqual(result.new_messages, step["expected_new_messages"])
                        if "expected_verification_code" in step:
                            self.assertEqual(
                                result.verification_code,
                                step["expected_verification_code"],
                            )
                    elif op == "inject_foreign_message_binding":
                        assert reg is not None
                        # Mutate the open connection without re-opening (integrity would fail).
                        conn = reg._conn
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
                    elif op == "force_stored_state_terminal":
                        assert reg is not None
                        # Update terminal flag on open connection; extension check uses stored state.
                        reg._conn.execute(
                            "UPDATE exchanges SET state = ?",
                            (step["state"],),
                        )
                    elif op == "concurrent_duplicate":
                        if reg is not None:
                            reg.close()
                            reg = None
                        envelopes = self._envelopes(step["source_transcript_vector_id"])
                        results: List[Any] = []

                        def worker() -> None:
                            with ReplayRegistry(path, create=True) as local:
                                results.append(
                                    local.check_and_record(
                                        envelopes,
                                        require_terminal=bool(step.get("require_terminal", False)),
                                    )
                                )

                        # Ensure DB exists first.
                        with ReplayRegistry(path, create=True):
                            pass
                        t1 = threading.Thread(target=worker)
                        t2 = threading.Thread(target=worker)
                        t1.start()
                        t2.start()
                        t1.join()
                        t2.join()
                        codes = sorted(r.code for r in results)
                        self.assertEqual(codes, sorted(step["expected_codes"]))
                        self.assertEqual(
                            sum(1 for r in results if r.newly_recorded),
                            step["expected_newly_recorded_sum"],
                        )
                        reg = ReplayRegistry(path, create=False)
                    elif op == "create_then_corrupt_schema_version":
                        with ReplayRegistry(path, create=True):
                            pass
                        conn = sqlite3.connect(str(path))
                        try:
                            conn.execute(
                                "UPDATE registry_metadata SET value = ? WHERE key = 'schema_version'",
                                ("999",),
                            )
                            conn.commit()
                        finally:
                            conn.close()
                        with self.assertRaises(ReplayRegistryError) as ctx:
                            ReplayRegistry(path, create=False)
                        self.assertEqual(ctx.exception.code, step["expected_open_code"])
                        return
                    elif op == "create_record_then_corrupt_count":
                        with ReplayRegistry(path, create=True) as local:
                            local.check_and_record(
                                self._envelopes(step["source_transcript_vector_id"]),
                                require_terminal=False,
                            )
                        conn = sqlite3.connect(str(path))
                        try:
                            conn.execute("UPDATE exchanges SET message_count = 99")
                            conn.commit()
                        finally:
                            conn.close()
                        with self.assertRaises(ReplayRegistryError) as ctx:
                            ReplayRegistry(path, create=False)
                        self.assertEqual(ctx.exception.code, step["expected_open_code"])
                        return
                    else:
                        self.fail(f"unknown op {op}")

                if vec.get("expected_final_exchange_count") is not None:
                    assert reg is not None
                    self.assertEqual(reg.count_exchanges(), vec["expected_final_exchange_count"])
                    self.assertEqual(reg.count_messages(), vec["expected_final_message_count"])
            finally:
                if reg is not None:
                    reg.close()
                # No leftover WAL/SHM beside temp dir cleanup.
                for suffix in ("-wal", "-shm"):
                    self.assertFalse((Path(str(path) + suffix)).exists())

    def test_vector_new_transcript(self):
        self._run_vector("replay_new_transcript")

    def test_vector_exact_repeat(self):
        self._run_vector("replay_exact_repeat")

    def test_vector_partial_then_extension(self):
        self._run_vector("replay_partial_then_extension")

    def test_vector_complete_then_old_prefix(self):
        self._run_vector("replay_complete_then_old_prefix")

    def test_vector_fork(self):
        self._run_vector("replay_fork")

    def test_vector_cross_exchange(self):
        self._run_vector("replay_cross_exchange_message")

    def test_vector_terminal_exact_repeat(self):
        self._run_vector("replay_terminal_exact_repeat")

    def test_vector_terminal_extension(self):
        self._run_vector("replay_terminal_extension_rejection")

    def test_vector_invalid_writes_nothing(self):
        self._run_vector("replay_invalid_writes_nothing")

    def test_vector_concurrent_duplicate(self):
        self._run_vector("replay_concurrent_duplicate")

    def test_vector_wrong_schema(self):
        self._run_vector("replay_wrong_schema_version")

    def test_vector_corrupted_state(self):
        self._run_vector("replay_corrupted_state")

    def test_fingerprint_and_hash_helpers(self):
        envs = self._envelopes("valid_partial_quoted")
        tr = verify_transcript(envs)
        self.assertTrue(tr.ok)
        assert tr.exchange_id is not None
        ids = [e["message_id"] for e in envs]
        eh = exchange_hash_for(tr.exchange_id)
        fp = transcript_fingerprint_for(ids)
        self.assertEqual(len(eh), 64)
        self.assertEqual(len(fp), 64)
        self.assertNotEqual(eh, tr.exchange_id)

    def test_no_sensitive_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            with ReplayRegistry(path, create=True) as reg:
                reg.check_and_record(
                    self._envelopes("valid_happy_path_completed"),
                    require_terminal=True,
                )
            raw = path.read_bytes()
            # Ensure raw transcript markers are absent from DB bytes.
            for token in FORBIDDEN_STORAGE_TOKENS:
                self.assertNotIn(token.encode("utf-8"), raw)
            # Ensure raw exchange id string is not stored.
            tx = self._envelopes("valid_happy_path_completed")[0]["transaction_id"]
            self.assertNotIn(tx.encode("utf-8"), raw)

    def test_json_entry_point(self):
        envs = self._envelopes("valid_partial_quoted")
        raw = json.dumps(envs, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            with ReplayRegistry(path, create=True) as reg:
                result = reg.check_and_record_json(raw, require_terminal=False)
                self.assertEqual(result.code, "recorded_new")
                again = reg.check_and_record_json(raw, require_terminal=False)
                self.assertEqual(again.code, "already_recorded")

    def test_rollback_leaves_no_partial_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._db_path(tmp)
            with ReplayRegistry(path, create=True) as reg:
                # Invalid signature writes nothing.
                bad = self._envelopes("invalid_bad_signature")
                result = reg.check_and_record(bad)
                self.assertEqual(result.code, "verification_failed")
                self.assertEqual(reg.count_exchanges(), 0)
                self.assertEqual(reg.count_messages(), 0)

    def test_ast_no_private_key_apis(self):
        tree = ast.parse(RUNTIME_PATH.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in FORBIDDEN_IMPORT_NAMES:
                        self.fail(f"imports {alias.name}")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"generate", "sign"}:
                    self.fail(f"calls {node.func.attr}()")
        self.assertNotIn("Ed25519PrivateKey", RUNTIME_PATH.read_text(encoding="utf-8"))

    def test_vector_keys_no_private_material(self):
        keys: Set[str] = set()
        _collect_keys(self.replay_doc, keys)
        forbidden = {
            "private_key",
            "seed",
            "seed_phrase",
            "mnemonic",
            "wallet_credential",
            "wallet_secret",
            "signing_secret",
            "secret_key",
        }
        offenders = sorted(k for k in keys if k.lower() in forbidden)
        self.assertEqual(offenders, [])

    def test_no_repo_data_side_effects(self):
        data_dir = ROOT / "data"
        self.assertFalse(data_dir.exists() and any(data_dir.rglob("shard_*.jsonl")))
        self.assertFalse(any(ROOT.glob("*.sqlite3")))
        self.assertEqual(SCHEMA_VERSION, 1)


if __name__ == "__main__":
    unittest.main()
