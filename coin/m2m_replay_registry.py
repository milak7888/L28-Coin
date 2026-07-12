# SPDX-License-Identifier: Apache-2.0
"""
L28 M2M offline replay and idempotency registry (Foundation 8).

Local, explicit, hash-only SQLite registry that prevents a valid signed M2M
transcript from causing repeated processing across separate local executions.

Not an L28 ledger, consensus system, wallet, or settlement authority.
Does not integrate with the Foundation 7 CLI in this milestone.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import stat
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List, Mapping, Optional, Sequence, Union

from coin.m2m_transcript_validator import (
    TERMINAL_STATES,
    verify_transcript,
    verify_transcript_json,
)
from coin.m2m_verifier import canonical_bytes, parse_m2m_json_value

SCHEMA_VERSION = 1
BUSY_TIMEOUT_MS = 5000
DOMAIN_EXCHANGE = b"L28-M2M-V0.1-REPLAY-EXCHANGE\x00"
DOMAIN_TRANSCRIPT = b"L28-M2M-V0.1-REPLAY-TRANSCRIPT\x00"

# Resolved repository root used only to reject registries inside the checkout.
_REPO_ROOT = Path(__file__).resolve().parents[1]

STABLE_CODES = frozenset(
    {
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
)


class ReplayRegistryError(Exception):
    """Fail-closed registry error with a stable public code."""

    def __init__(self, code: str) -> None:
        if code not in STABLE_CODES:
            code = "internal_error"
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ReplayResult:
    ok: bool
    code: str
    newly_recorded: bool
    new_messages: int
    state: Optional[str] = None
    exchange_hash: Optional[str] = None
    transcript_fingerprint: Optional[str] = None
    head_message_id: Optional[str] = None
    message_count: int = 0
    verification_code: Optional[str] = None


def _result(
    *,
    ok: bool,
    code: str,
    newly_recorded: bool = False,
    new_messages: int = 0,
    state: Optional[str] = None,
    exchange_hash: Optional[str] = None,
    transcript_fingerprint: Optional[str] = None,
    head_message_id: Optional[str] = None,
    message_count: int = 0,
    verification_code: Optional[str] = None,
) -> ReplayResult:
    if code not in STABLE_CODES:
        code = "internal_error"
    return ReplayResult(
        ok=ok,
        code=code,
        newly_recorded=newly_recorded,
        new_messages=new_messages,
        state=state,
        exchange_hash=exchange_hash,
        transcript_fingerprint=transcript_fingerprint,
        head_message_id=head_message_id,
        message_count=message_count,
        verification_code=verification_code,
    )


def exchange_hash_for(exchange_id: str) -> str:
    if not isinstance(exchange_id, str) or exchange_id == "":
        raise ReplayRegistryError("internal_error")
    return hashlib.sha256(DOMAIN_EXCHANGE + exchange_id.encode("utf-8")).hexdigest()


def transcript_fingerprint_for(message_ids: Sequence[str]) -> str:
    ids = list(message_ids)
    for mid in ids:
        if not isinstance(mid, str) or mid == "":
            raise ReplayRegistryError("internal_error")
    return hashlib.sha256(DOMAIN_TRANSCRIPT + canonical_bytes(ids)).hexdigest()


def _validate_registry_path(path: Union[str, Path], *, create: bool) -> Path:
    if not isinstance(path, (str, Path)):
        raise ReplayRegistryError("invalid_registry_path")
    raw = Path(path)
    if not raw.is_absolute():
        raise ReplayRegistryError("registry_path_not_absolute")

    # Reject any symlink in the final path component via lstat when present.
    try:
        st = os.lstat(raw)
        exists = True
    except FileNotFoundError:
        exists = False
        st = None
    except OSError as exc:
        raise ReplayRegistryError("registry_io_error") from exc

    if exists:
        assert st is not None
        if stat.S_ISLNK(st.st_mode):
            raise ReplayRegistryError("registry_symlink_rejected")
        if not stat.S_ISREG(st.st_mode):
            raise ReplayRegistryError("registry_not_regular_file")

    # Parent must exist and must not be reached through a final-path symlink trick;
    # also reject registry paths inside the repository checkout.
    parent = raw.parent
    if not parent.exists() or not parent.is_dir():
        raise ReplayRegistryError("invalid_registry_path")
    try:
        if parent.is_symlink():
            raise ReplayRegistryError("registry_symlink_rejected")
    except OSError as exc:
        raise ReplayRegistryError("registry_io_error") from exc

    try:
        resolved_parent = parent.resolve(strict=True)
        candidate = (resolved_parent / raw.name).resolve(strict=False)
        repo = _REPO_ROOT.resolve(strict=True)
    except OSError as exc:
        raise ReplayRegistryError("registry_io_error") from exc

    try:
        candidate.relative_to(repo)
        raise ReplayRegistryError("registry_inside_repository")
    except ValueError:
        pass

    if not exists and not create:
        raise ReplayRegistryError("registry_not_found")

    return Path(os.path.join(str(resolved_parent), raw.name))


def _map_db_error(exc: BaseException) -> str:
    if isinstance(exc, sqlite3.OperationalError):
        msg = str(exc).lower()
        if "locked" in msg or "busy" in msg:
            return "registry_locked"
        return "registry_io_error"
    if isinstance(exc, sqlite3.DatabaseError):
        return "registry_corrupt"
    if isinstance(exc, sqlite3.IntegrityError):
        return "registry_integrity_error"
    return "internal_error"


class ReplayRegistry:
    """
    Explicit local SQLite replay/idempotency registry.

    Creation requires create=True. Paths must be absolute and outside the
    L28-Coin repository. Stores only hashed exchange identifiers and message IDs.
    """

    def __init__(self, path: Union[str, Path], *, create: bool = False) -> None:
        self._lock = threading.RLock()
        self._closed = False
        self._path = _validate_registry_path(path, create=create)
        self._created_new = False

        existed = self._path.exists()
        if existed and create:
            # Existing path: open if SQLite registry; never replace a foreign file.
            pass
        if not existed and create:
            self._created_new = True

        try:
            if existed:
                # Probe whether this is a usable SQLite DB before connecting for real.
                try:
                    probe = sqlite3.connect(
                        f"file:{self._path}?mode=ro",
                        uri=True,
                        timeout=BUSY_TIMEOUT_MS / 1000.0,
                    )
                    try:
                        probe.execute("SELECT 1 FROM sqlite_master LIMIT 1")
                    finally:
                        probe.close()
                except sqlite3.Error as exc:
                    if create:
                        raise ReplayRegistryError("registry_already_exists") from exc
                    raise ReplayRegistryError("registry_corrupt") from exc

            self._conn = sqlite3.connect(
                str(self._path),
                timeout=BUSY_TIMEOUT_MS / 1000.0,
                isolation_level=None,  # manual transactions
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
            self._configure_connection()
            if self._created_new:
                self._initialize_schema()
                try:
                    os.chmod(self._path, 0o600)
                except OSError as exc:
                    self._conn.close()
                    raise ReplayRegistryError("registry_io_error") from exc
            self._validate_open_state()
        except ReplayRegistryError:
            raise
        except sqlite3.Error as exc:
            raise ReplayRegistryError(_map_db_error(exc)) from exc
        except OSError as exc:
            raise ReplayRegistryError("registry_io_error") from exc

    def _configure_connection(self) -> None:
        cur = self._conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute(f"PRAGMA busy_timeout={int(BUSY_TIMEOUT_MS)}")
        cur.execute("PRAGMA journal_mode=DELETE")
        cur.execute("PRAGMA synchronous=FULL")

    def _initialize_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            cur.execute(
                """
                CREATE TABLE registry_metadata (
                    key TEXT PRIMARY KEY NOT NULL,
                    value TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE exchanges (
                    exchange_hash TEXT PRIMARY KEY NOT NULL,
                    transcript_fingerprint TEXT NOT NULL,
                    head_message_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    message_count INTEGER NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE messages (
                    message_id TEXT PRIMARY KEY NOT NULL,
                    exchange_hash TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    previous_message_id TEXT,
                    FOREIGN KEY(exchange_hash) REFERENCES exchanges(exchange_hash),
                    UNIQUE(exchange_hash, ordinal)
                )
                """
            )
            cur.execute(
                "INSERT INTO registry_metadata(key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
            cur.execute("COMMIT")
        except Exception:
            cur.execute("ROLLBACK")
            raise

    def _validate_open_state(self) -> None:
        cur = self._conn.cursor()
        try:
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA integrity_check")
            row = cur.fetchone()
            if row is None or str(row[0]).lower() != "ok":
                raise ReplayRegistryError("registry_corrupt")

            cur.execute(
                "SELECT value FROM registry_metadata WHERE key = 'schema_version'"
            )
            meta = cur.fetchone()
            if meta is None:
                raise ReplayRegistryError("registry_integrity_error")
            try:
                version = int(meta["value"])
            except (TypeError, ValueError) as exc:
                raise ReplayRegistryError("schema_version_mismatch") from exc
            if version != SCHEMA_VERSION:
                raise ReplayRegistryError("schema_version_mismatch")

            # Required tables/columns.
            for table in ("registry_metadata", "exchanges", "messages"):
                cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                )
                if cur.fetchone() is None:
                    raise ReplayRegistryError("registry_integrity_error")

            cur.execute("PRAGMA foreign_key_check")
            if cur.fetchone() is not None:
                raise ReplayRegistryError("registry_integrity_error")

            cur.execute(
                "SELECT exchange_hash, transcript_fingerprint, head_message_id, state, message_count "
                "FROM exchanges"
            )
            exchanges = cur.fetchall()
            for ex in exchanges:
                eh = ex["exchange_hash"]
                cur.execute(
                    "SELECT message_id, ordinal, previous_message_id "
                    "FROM messages WHERE exchange_hash = ? ORDER BY ordinal ASC",
                    (eh,),
                )
                msgs = cur.fetchall()
                if len(msgs) != int(ex["message_count"]):
                    raise ReplayRegistryError("registry_integrity_error")
                if not msgs:
                    raise ReplayRegistryError("registry_integrity_error")
                ids: List[str] = []
                for i, msg in enumerate(msgs):
                    if int(msg["ordinal"]) != i:
                        raise ReplayRegistryError("registry_integrity_error")
                    ids.append(msg["message_id"])
                    if i == 0:
                        if msg["previous_message_id"] is not None:
                            raise ReplayRegistryError("registry_integrity_error")
                    else:
                        if msg["previous_message_id"] != ids[i - 1]:
                            raise ReplayRegistryError("registry_integrity_error")
                if ids[-1] != ex["head_message_id"]:
                    raise ReplayRegistryError("registry_integrity_error")
                if transcript_fingerprint_for(ids) != ex["transcript_fingerprint"]:
                    raise ReplayRegistryError("registry_integrity_error")
        except ReplayRegistryError:
            raise
        except sqlite3.Error as exc:
            raise ReplayRegistryError(_map_db_error(exc)) from exc

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            try:
                self._conn.close()
            except sqlite3.Error:
                pass

    def __enter__(self) -> "ReplayRegistry":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _ensure_open(self) -> None:
        if self._closed:
            raise ReplayRegistryError("registry_io_error")

    def check_and_record(
        self,
        envelopes: Sequence[Mapping[str, Any]],
        *,
        require_terminal: bool = False,
    ) -> ReplayResult:
        try:
            self._ensure_open()
            # Verify fully before any write transaction.
            tr = verify_transcript(envelopes, require_terminal=require_terminal)
            if not tr.ok:
                return _result(
                    ok=False,
                    code="verification_failed",
                    verification_code=tr.code,
                )
            if tr.state is None or tr.exchange_id is None:
                return _result(ok=False, code="internal_error")

            message_ids: List[str] = []
            previous_ids: List[Optional[str]] = []
            for env in envelopes:
                if not isinstance(env, Mapping):
                    return _result(ok=False, code="internal_error")
                mid = env.get("message_id")
                if not isinstance(mid, str) or mid == "":
                    return _result(ok=False, code="internal_error")
                prev = env.get("previous_message_id")
                if prev is not None and (not isinstance(prev, str) or prev == ""):
                    return _result(ok=False, code="internal_error")
                message_ids.append(mid)
                previous_ids.append(prev)

            exchange_hash = exchange_hash_for(tr.exchange_id)
            fingerprint = transcript_fingerprint_for(message_ids)
            state = tr.state
            n = len(message_ids)

            with self._lock:
                return self._check_and_record_locked(
                    exchange_hash=exchange_hash,
                    fingerprint=fingerprint,
                    state=state,
                    message_ids=message_ids,
                    previous_ids=previous_ids,
                )
        except ReplayRegistryError as exc:
            return _result(ok=False, code=exc.code)
        except Exception:
            return _result(ok=False, code="internal_error")

    def _load_exchange(
        self, cur: sqlite3.Cursor, exchange_hash: str
    ) -> Optional[sqlite3.Row]:
        cur.execute(
            "SELECT exchange_hash, transcript_fingerprint, head_message_id, state, message_count "
            "FROM exchanges WHERE exchange_hash = ?",
            (exchange_hash,),
        )
        return cur.fetchone()

    def _idempotent_from_existing(
        self,
        *,
        existing: sqlite3.Row,
        stored_ids: Sequence[str],
        message_ids: Sequence[str],
        exchange_hash: str,
        fingerprint: str,
        state: str,
    ) -> Optional[ReplayResult]:
        stored_count = int(existing["message_count"])
        stored_state = str(existing["state"])
        n = len(message_ids)
        shared = min(n, stored_count)
        for i in range(shared):
            if message_ids[i] != stored_ids[i]:
                return _result(
                    ok=False,
                    code="exchange_fork",
                    exchange_hash=exchange_hash,
                    transcript_fingerprint=fingerprint,
                    head_message_id=message_ids[-1],
                    message_count=n,
                    state=state,
                )
        if n == stored_count:
            return _result(
                ok=True,
                code="already_recorded",
                newly_recorded=False,
                new_messages=0,
                state=stored_state,
                exchange_hash=exchange_hash,
                transcript_fingerprint=str(existing["transcript_fingerprint"]),
                head_message_id=str(existing["head_message_id"]),
                message_count=stored_count,
            )
        if n < stored_count:
            return _result(
                ok=True,
                code="already_recorded_prefix",
                newly_recorded=False,
                new_messages=0,
                state=stored_state,
                exchange_hash=exchange_hash,
                transcript_fingerprint=str(existing["transcript_fingerprint"]),
                head_message_id=str(existing["head_message_id"]),
                message_count=stored_count,
            )
        return None

    def _check_and_record_locked(
        self,
        *,
        exchange_hash: str,
        fingerprint: str,
        state: str,
        message_ids: List[str],
        previous_ids: List[Optional[str]],
    ) -> ReplayResult:
        n = len(message_ids)
        cur = self._conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
        except sqlite3.Error as exc:
            return _result(ok=False, code=_map_db_error(exc))

        try:
            for mid in message_ids:
                cur.execute(
                    "SELECT exchange_hash FROM messages WHERE message_id = ?",
                    (mid,),
                )
                row = cur.fetchone()
                if row is not None and row["exchange_hash"] != exchange_hash:
                    cur.execute("ROLLBACK")
                    return _result(
                        ok=False,
                        code="message_replay",
                        exchange_hash=exchange_hash,
                        transcript_fingerprint=fingerprint,
                        head_message_id=message_ids[-1],
                        message_count=n,
                        state=state,
                    )

            existing = self._load_exchange(cur, exchange_hash)

            if existing is None:
                for mid in message_ids:
                    cur.execute("SELECT 1 FROM messages WHERE message_id = ?", (mid,))
                    if cur.fetchone() is not None:
                        cur.execute("ROLLBACK")
                        return _result(
                            ok=False,
                            code="message_replay",
                            exchange_hash=exchange_hash,
                            transcript_fingerprint=fingerprint,
                            head_message_id=message_ids[-1],
                            message_count=n,
                            state=state,
                        )
                try:
                    cur.execute(
                        "INSERT INTO exchanges(exchange_hash, transcript_fingerprint, head_message_id, state, message_count) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (exchange_hash, fingerprint, message_ids[-1], state, n),
                    )
                    for i, mid in enumerate(message_ids):
                        cur.execute(
                            "INSERT INTO messages(message_id, exchange_hash, ordinal, previous_message_id) "
                            "VALUES (?, ?, ?, ?)",
                            (mid, exchange_hash, i, previous_ids[i]),
                        )
                    cur.execute("COMMIT")
                except sqlite3.IntegrityError:
                    # Concurrent winner already recorded; re-read under a fresh view.
                    cur.execute("ROLLBACK")
                    cur.execute("BEGIN IMMEDIATE")
                    existing2 = self._load_exchange(cur, exchange_hash)
                    if existing2 is None:
                        cur.execute("ROLLBACK")
                        return _result(ok=False, code="registry_integrity_error")
                    cur.execute(
                        "SELECT message_id FROM messages WHERE exchange_hash = ? ORDER BY ordinal ASC",
                        (exchange_hash,),
                    )
                    stored_ids = [r["message_id"] for r in cur.fetchall()]
                    cur.execute("ROLLBACK")
                    idemp = self._idempotent_from_existing(
                        existing=existing2,
                        stored_ids=stored_ids,
                        message_ids=message_ids,
                        exchange_hash=exchange_hash,
                        fingerprint=fingerprint,
                        state=state,
                    )
                    if idemp is not None:
                        return idemp
                    return _result(ok=False, code="registry_integrity_error")
                return _result(
                    ok=True,
                    code="recorded_new",
                    newly_recorded=True,
                    new_messages=n,
                    state=state,
                    exchange_hash=exchange_hash,
                    transcript_fingerprint=fingerprint,
                    head_message_id=message_ids[-1],
                    message_count=n,
                )

            cur.execute(
                "SELECT message_id FROM messages WHERE exchange_hash = ? ORDER BY ordinal ASC",
                (exchange_hash,),
            )
            stored_ids = [r["message_id"] for r in cur.fetchall()]
            if len(stored_ids) != int(existing["message_count"]):
                cur.execute("ROLLBACK")
                return _result(ok=False, code="registry_integrity_error")

            idemp = self._idempotent_from_existing(
                existing=existing,
                stored_ids=stored_ids,
                message_ids=message_ids,
                exchange_hash=exchange_hash,
                fingerprint=fingerprint,
                state=state,
            )
            if idemp is not None:
                cur.execute("ROLLBACK")
                return idemp

            stored_count = int(existing["message_count"])
            stored_state = str(existing["state"])
            if stored_state in TERMINAL_STATES:
                cur.execute("ROLLBACK")
                return _result(
                    ok=False,
                    code="terminal_exchange_extension",
                    exchange_hash=exchange_hash,
                    transcript_fingerprint=fingerprint,
                    head_message_id=message_ids[-1],
                    message_count=n,
                    state=state,
                )

            suffix_ids = message_ids[stored_count:]
            suffix_prev = previous_ids[stored_count:]
            for i, mid in enumerate(suffix_ids):
                ordinal = stored_count + i
                cur.execute(
                    "INSERT INTO messages(message_id, exchange_hash, ordinal, previous_message_id) "
                    "VALUES (?, ?, ?, ?)",
                    (mid, exchange_hash, ordinal, suffix_prev[i]),
                )
            cur.execute(
                "UPDATE exchanges SET transcript_fingerprint = ?, head_message_id = ?, state = ?, message_count = ? "
                "WHERE exchange_hash = ?",
                (fingerprint, message_ids[-1], state, n, exchange_hash),
            )
            cur.execute("COMMIT")
            return _result(
                ok=True,
                code="recorded_extension",
                newly_recorded=True,
                new_messages=len(suffix_ids),
                state=state,
                exchange_hash=exchange_hash,
                transcript_fingerprint=fingerprint,
                head_message_id=message_ids[-1],
                message_count=n,
            )
        except ReplayRegistryError as exc:
            try:
                cur.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            return _result(ok=False, code=exc.code)
        except sqlite3.Error as exc:
            try:
                cur.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            return _result(ok=False, code=_map_db_error(exc))
        except Exception:
            try:
                cur.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            return _result(ok=False, code="internal_error")

    def check_and_record_json(
        self,
        raw: Union[str, bytes],
        *,
        require_terminal: bool = False,
    ) -> ReplayResult:
        try:
            self._ensure_open()
            tr = verify_transcript_json(raw, require_terminal=require_terminal)
            if not tr.ok:
                return _result(
                    ok=False,
                    code="verification_failed",
                    verification_code=tr.code,
                )
            value = parse_m2m_json_value(raw)
            if not isinstance(value, list):
                return _result(
                    ok=False,
                    code="verification_failed",
                    verification_code="transcript_not_array",
                )
            return self.check_and_record(value, require_terminal=require_terminal)
        except ReplayRegistryError as exc:
            return _result(ok=False, code=exc.code)
        except Exception:
            return _result(ok=False, code="internal_error")

    def count_exchanges(self) -> int:
        self._ensure_open()
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM exchanges")
        return int(cur.fetchone()["c"])

    def count_messages(self) -> int:
        self._ensure_open()
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM messages")
        return int(cur.fetchone()["c"])


__all__ = [
    "BUSY_TIMEOUT_MS",
    "DOMAIN_EXCHANGE",
    "DOMAIN_TRANSCRIPT",
    "ReplayRegistry",
    "ReplayRegistryError",
    "ReplayResult",
    "SCHEMA_VERSION",
    "STABLE_CODES",
    "exchange_hash_for",
    "transcript_fingerprint_for",
]
