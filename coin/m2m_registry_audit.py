# SPDX-License-Identifier: Apache-2.0
"""
L28 M2M offline replay-registry auditor (Foundation 10).

Strictly read-only inspection of an existing Foundation 8 SQLite replay registry.
Does not create, modify, repair, migrate, or admit anything.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from coin.m2m_replay_registry import SCHEMA_VERSION, transcript_fingerprint_for
from coin.m2m_transcript_validator import NONTERMINAL_STATES, TERMINAL_STATES
from coin.m2m_verifier import canonical_bytes

DOMAIN_LOGICAL = b"L28-M2M-V0.1-REGISTRY-LOGICAL\x00"
BUSY_TIMEOUT_MS = 5000
MAX_REGISTRY_FILE_BYTES = 8_388_608
MAX_REGISTRY_EXCHANGES = 4096
MAX_REGISTRY_MESSAGES = 262_144
_REPO_ROOT = Path(__file__).resolve().parents[1]

APPLICATION_TABLES = ("registry_metadata", "exchanges", "messages")

EXPECTED_COLUMNS: Dict[str, Tuple[str, ...]] = {
    "registry_metadata": ("key", "value"),
    "exchanges": (
        "exchange_hash",
        "transcript_fingerprint",
        "head_message_id",
        "state",
        "message_count",
    ),
    "messages": (
        "message_id",
        "exchange_hash",
        "ordinal",
        "previous_message_id",
    ),
}

VALID_STATES = TERMINAL_STATES | NONTERMINAL_STATES

STABLE_CODES = frozenset(
    {
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
)

_HEX64 = frozenset("0123456789abcdef")


@dataclass(frozen=True)
class RegistryAuditResult:
    ok: bool
    code: str
    schema_version: Optional[int] = None
    exchange_count: int = 0
    message_count: int = 0
    terminal_exchange_count: int = 0
    nonterminal_exchange_count: int = 0
    logical_registry_digest: Optional[str] = None
    failed_check: Optional[str] = None


def _result(
    *,
    ok: bool,
    code: str,
    schema_version: Optional[int] = None,
    exchange_count: int = 0,
    message_count: int = 0,
    terminal_exchange_count: int = 0,
    nonterminal_exchange_count: int = 0,
    logical_registry_digest: Optional[str] = None,
    failed_check: Optional[str] = None,
) -> RegistryAuditResult:
    if code not in STABLE_CODES:
        code = "internal_error"
    return RegistryAuditResult(
        ok=ok,
        code=code,
        schema_version=schema_version,
        exchange_count=exchange_count,
        message_count=message_count,
        terminal_exchange_count=terminal_exchange_count,
        nonterminal_exchange_count=nonterminal_exchange_count,
        logical_registry_digest=logical_registry_digest,
        failed_check=failed_check,
    )


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in _HEX64 for c in value)


def _is_exact_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _verify_regular_file(path: Path) -> Tuple[Optional[str], Optional[str]]:
    """Re-verify the registry path immediately before SQLite open."""
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return "registry_not_found", "path_validation"
    except OSError:
        return "registry_unreadable", "path_validation"
    if stat.S_ISLNK(st.st_mode):
        return "unsafe_registry_path", "path_validation"
    if not stat.S_ISREG(st.st_mode):
        return "unsafe_registry_path", "path_validation"
    if st.st_size > MAX_REGISTRY_FILE_BYTES:
        return "registry_unreadable", "registry_bounds"
    return None, None


def _validate_audit_path(path: Union[str, Path]) -> Tuple[Optional[Path], Optional[str], Optional[str]]:
    """
    Validate an existing registry path for read-only audit.

    Returns (resolved_path, code, failed_check) where code is set on failure.
    """
    if not isinstance(path, (str, Path)):
        return None, "invalid_registry_path", "path_validation"
    raw = Path(path)
    if not raw.is_absolute():
        return None, "invalid_registry_path", "path_validation"

    parent = raw.parent
    if not parent.exists() or not parent.is_dir():
        return None, "invalid_registry_path", "path_validation"
    try:
        if parent.is_symlink():
            return None, "unsafe_registry_path", "path_validation"
    except OSError:
        return None, "registry_unreadable", "path_validation"

    try:
        resolved_parent = parent.resolve(strict=True)
        candidate = (resolved_parent / raw.name).resolve(strict=False)
        repo = _REPO_ROOT.resolve(strict=True)
    except OSError:
        return None, "registry_unreadable", "path_validation"

    try:
        candidate.relative_to(repo)
        return None, "unsafe_registry_path", "path_validation"
    except ValueError:
        pass

    try:
        st = os.lstat(raw)
    except FileNotFoundError:
        return None, "registry_not_found", "path_validation"
    except OSError:
        return None, "registry_unreadable", "path_validation"

    if stat.S_ISLNK(st.st_mode):
        return None, "unsafe_registry_path", "path_validation"
    if not stat.S_ISREG(st.st_mode):
        return None, "unsafe_registry_path", "path_validation"
    if st.st_size > MAX_REGISTRY_FILE_BYTES:
        return None, "registry_unreadable", "registry_bounds"

    return Path(os.path.join(str(resolved_parent), raw.name)), None, None


def _open_readonly(path: Path) -> Tuple[Optional[sqlite3.Connection], Optional[str], Optional[str]]:
    code, failed = _verify_regular_file(path)
    if code is not None:
        return None, code, failed

    try:
        conn = sqlite3.connect(
            f"file:{path}?mode=ro&immutable=1",
            uri=True,
            timeout=BUSY_TIMEOUT_MS / 1000.0,
        )
    except sqlite3.Error:
        return None, "registry_unreadable", "unreadable_database"
    except OSError:
        return None, "registry_unreadable", "unreadable_database"

    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute(f"PRAGMA busy_timeout={int(BUSY_TIMEOUT_MS)}")
        databases = conn.execute("PRAGMA database_list").fetchall()
        if len(databases) != 1:
            return None, "registry_schema_mismatch", "attached_database"
        # Probe readability without mutating journal mode or other settings.
        conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
    except sqlite3.Error:
        try:
            conn.close()
        except sqlite3.Error:
            pass
        return None, "registry_unreadable", "unreadable_database"
    return conn, None, None


def _table_columns(cur: sqlite3.Cursor, table: str) -> Optional[List[str]]:
    cur.execute(f"PRAGMA table_info({table})")
    rows = cur.fetchall()
    if not rows:
        return None
    return [str(row[1]) for row in rows]


def _validate_schema(cur: sqlite3.Cursor) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    cur.execute(
        "SELECT type, name FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' AND type IN ('view', 'trigger')"
    )
    if cur.fetchall():
        return None, "registry_schema_mismatch", "schema_objects"

    cur.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND sql GLOB '*VIRTUAL TABLE*'"
    )
    if cur.fetchall():
        return None, "registry_schema_mismatch", "schema_objects"

    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = sorted(str(row[0]) for row in cur.fetchall())
    expected = sorted(APPLICATION_TABLES)
    if tables != expected:
        return None, "registry_schema_mismatch", "schema_tables"

    for table, cols in EXPECTED_COLUMNS.items():
        found = _table_columns(cur, table)
        if found is None or tuple(found) != cols:
            return None, "registry_schema_mismatch", "schema_columns"

    cur.execute(
        "SELECT value FROM registry_metadata WHERE key = 'schema_version'"
    )
    meta = cur.fetchone()
    if meta is None:
        return None, "registry_schema_mismatch", "schema_version"
    try:
        version = int(meta[0])
    except (TypeError, ValueError):
        return None, "registry_schema_mismatch", "schema_version"
    if version != SCHEMA_VERSION:
        return None, "registry_schema_mismatch", "schema_version"
    return version, None, None


def _logical_digest_body(
    *,
    schema_version: int,
    exchanges: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    normalized_exchanges: List[Dict[str, Any]] = []
    for ex in sorted(exchanges, key=lambda row: str(row["exchange_hash"])):
        messages = list(ex["messages"])
        normalized_exchanges.append(
            {
                "exchange_hash": str(ex["exchange_hash"]),
                "transcript_fingerprint": str(ex["transcript_fingerprint"]),
                "head_message_id": str(ex["head_message_id"]),
                "state": str(ex["state"]),
                "message_count": int(ex["message_count"]),
                "messages": [
                    {
                        "message_id": str(msg["message_id"]),
                        "ordinal": int(msg["ordinal"]),
                        "previous_message_id": msg["previous_message_id"],
                    }
                    for msg in messages
                ],
            }
        )
    return {
        "schema_version": int(schema_version),
        "exchanges": normalized_exchanges,
    }


def compute_logical_registry_digest(
    *,
    schema_version: int,
    exchanges: Sequence[Mapping[str, Any]],
) -> str:
    """
  Deterministic logical digest over normalized hash-only registry rows.

  logical_registry_digest =
      SHA-256(
          L28-M2M-V0.1-REGISTRY-LOGICAL\\x00
          || Canon({
               "schema_version": <int>,
               "exchanges": [
                 {
                   "exchange_hash": <hex64>,
                   "transcript_fingerprint": <hex64>,
                   "head_message_id": <hex64>,
                   "state": <str>,
                   "message_count": <int>,
                   "messages": [
                     {
                       "message_id": <hex64>,
                       "ordinal": <int>,
                       "previous_message_id": <hex64|null>
                     }, ...
                   ]
                 }, ...  # sorted by exchange_hash ascending
               ]
             })
    """
    body = _logical_digest_body(schema_version=schema_version, exchanges=exchanges)
    return hashlib.sha256(DOMAIN_LOGICAL + canonical_bytes(body)).hexdigest()


def _audit_connection(conn: sqlite3.Connection) -> RegistryAuditResult:
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA integrity_check")
        row = cur.fetchone()
        if row is None or str(row[0]).lower() != "ok":
            return _result(
                ok=False,
                code="registry_integrity_error",
                failed_check="integrity_check",
            )

        schema_version, code, failed = _validate_schema(cur)
        if code is not None:
            return _result(ok=False, code=code, failed_check=failed)

        assert schema_version is not None

        cur.execute("PRAGMA foreign_key_check")
        if cur.fetchone() is not None:
            return _result(
                ok=False,
                code="registry_foreign_key_error",
                schema_version=schema_version,
                failed_check="foreign_key_check",
            )

        cur.execute(
            "SELECT exchange_hash, transcript_fingerprint, head_message_id, state, message_count "
            "FROM exchanges ORDER BY exchange_hash ASC"
        )
        exchange_rows = cur.fetchall()
        if len(exchange_rows) > MAX_REGISTRY_EXCHANGES:
            return _result(
                ok=False,
                code="registry_invariant_error",
                schema_version=schema_version,
                failed_check="registry_bounds",
            )

        cur.execute("SELECT COUNT(*) FROM messages")
        total_message_rows = int(cur.fetchone()[0])
        if total_message_rows > MAX_REGISTRY_MESSAGES:
            return _result(
                ok=False,
                code="registry_invariant_error",
                schema_version=schema_version,
                exchange_count=len(exchange_rows),
                message_count=total_message_rows,
                failed_check="registry_bounds",
            )

        cur.execute(
            "SELECT message_id, exchange_hash, ordinal, previous_message_id FROM messages"
        )
        all_messages = cur.fetchall()
        messages_by_exchange: Dict[str, List[sqlite3.Row]] = {}
        message_owner: Dict[str, str] = {}
        for msg in all_messages:
            mid = str(msg["message_id"])
            eh = str(msg["exchange_hash"])
            if not _is_hex64(mid):
                return _result(
                    ok=False,
                    code="registry_invariant_error",
                    schema_version=schema_version,
                    failed_check="malformed_message_id",
                )
            if mid in message_owner and message_owner[mid] != eh:
                return _result(
                    ok=False,
                    code="registry_invariant_error",
                    schema_version=schema_version,
                    failed_check="message_exchange_binding",
                )
            message_owner[mid] = eh
            messages_by_exchange.setdefault(eh, []).append(msg)

        digest_exchanges: List[Dict[str, Any]] = []
        terminal_count = 0
        nonterminal_count = 0
        total_messages = 0

        for ex in exchange_rows:
            eh = str(ex["exchange_hash"])
            fp = str(ex["transcript_fingerprint"])
            head = str(ex["head_message_id"])
            state = str(ex["state"])
            if not _is_exact_int(ex["message_count"]):
                return _result(
                    ok=False,
                    code="registry_invariant_error",
                    schema_version=schema_version,
                    failed_check="exchange_message_count",
                )
            count = int(ex["message_count"])
            if count < 0:
                return _result(
                    ok=False,
                    code="registry_invariant_error",
                    schema_version=schema_version,
                    failed_check="exchange_message_count",
                )

            if not _is_hex64(eh):
                return _result(
                    ok=False,
                    code="registry_invariant_error",
                    schema_version=schema_version,
                    failed_check="malformed_exchange_hash",
                )
            if not _is_hex64(fp):
                return _result(
                    ok=False,
                    code="registry_invariant_error",
                    schema_version=schema_version,
                    failed_check="malformed_fingerprint",
                )
            if not _is_hex64(head):
                return _result(
                    ok=False,
                    code="registry_invariant_error",
                    schema_version=schema_version,
                    failed_check="malformed_message_id",
                )
            if state not in VALID_STATES:
                return _result(
                    ok=False,
                    code="registry_invariant_error",
                    schema_version=schema_version,
                    failed_check="invalid_state",
                )
            if state in TERMINAL_STATES:
                terminal_count += 1
            else:
                nonterminal_count += 1

            msgs = messages_by_exchange.get(eh, [])
            msgs_sorted = sorted(msgs, key=lambda r: int(r["ordinal"]))
            if len(msgs_sorted) != count:
                return _result(
                    ok=False,
                    code="registry_invariant_error",
                    schema_version=schema_version,
                    exchange_count=len(exchange_rows),
                    message_count=len(all_messages),
                    terminal_exchange_count=terminal_count,
                    nonterminal_exchange_count=nonterminal_count,
                    failed_check="exchange_message_count",
                )
            if count == 0:
                return _result(
                    ok=False,
                    code="registry_invariant_error",
                    schema_version=schema_version,
                    exchange_count=len(exchange_rows),
                    message_count=len(all_messages),
                    failed_check="exchange_empty_messages",
                )

            ids: List[str] = []
            normalized_messages: List[Dict[str, Any]] = []
            for i, msg in enumerate(msgs_sorted):
                if int(msg["ordinal"]) != i:
                    return _result(
                        ok=False,
                        code="registry_invariant_error",
                        schema_version=schema_version,
                        failed_check="ordinal_continuity",
                    )
                mid = str(msg["message_id"])
                prev = msg["previous_message_id"]
                if prev is not None:
                    prev = str(prev)
                    if not _is_hex64(prev):
                        return _result(
                            ok=False,
                            code="registry_invariant_error",
                            schema_version=schema_version,
                            failed_check="malformed_message_id",
                        )
                if i == 0:
                    if prev is not None:
                        return _result(
                            ok=False,
                            code="registry_invariant_error",
                            schema_version=schema_version,
                            failed_check="previous_message_chain",
                        )
                else:
                    if prev != ids[i - 1]:
                        return _result(
                            ok=False,
                            code="registry_invariant_error",
                            schema_version=schema_version,
                            failed_check="previous_message_chain",
                        )
                ids.append(mid)
                normalized_messages.append(
                    {
                        "message_id": mid,
                        "ordinal": i,
                        "previous_message_id": prev,
                    }
                )

            if ids[-1] != head:
                return _result(
                    ok=False,
                    code="registry_invariant_error",
                    schema_version=schema_version,
                    failed_check="head_message_id",
                )
            if transcript_fingerprint_for(ids) != fp:
                return _result(
                    ok=False,
                    code="registry_invariant_error",
                    schema_version=schema_version,
                    failed_check="transcript_fingerprint",
                )

            total_messages += count
            digest_exchanges.append(
                {
                    "exchange_hash": eh,
                    "transcript_fingerprint": fp,
                    "head_message_id": head,
                    "state": state,
                    "message_count": count,
                    "messages": normalized_messages,
                }
            )

        # Messages referencing missing exchanges.
        exchange_hashes = {str(ex["exchange_hash"]) for ex in exchange_rows}
        for msg in all_messages:
            eh = str(msg["exchange_hash"])
            if eh not in exchange_hashes:
                return _result(
                    ok=False,
                    code="registry_invariant_error",
                    schema_version=schema_version,
                    failed_check="message_exchange_binding",
                )

        digest = compute_logical_registry_digest(
            schema_version=schema_version,
            exchanges=digest_exchanges,
        )
        return _result(
            ok=True,
            code="registry_healthy",
            schema_version=schema_version,
            exchange_count=len(exchange_rows),
            message_count=len(all_messages),
            terminal_exchange_count=terminal_count,
            nonterminal_exchange_count=nonterminal_count,
            logical_registry_digest=digest,
            failed_check=None,
        )
    except sqlite3.Error:
        return _result(
            ok=False,
            code="registry_unreadable",
            failed_check="unreadable_database",
        )
    except Exception:
        return _result(ok=False, code="internal_error", failed_check="internal_error")


def audit_registry(path: Union[str, Path]) -> RegistryAuditResult:
    """
    Read-only audit of an existing Foundation 8 replay registry.

    Never creates, modifies, repairs, migrates, or admits registry state.
    Requires a quiescent registry; does not guarantee a coherent snapshot under
    concurrent writers and does not attest to before/after file stability.
    """
    resolved, code, failed = _validate_audit_path(path)
    if code is not None:
        return _result(ok=False, code=code, failed_check=failed)

    assert resolved is not None
    conn, open_code, open_failed = _open_readonly(resolved)
    if open_code is not None:
        return _result(ok=False, code=open_code, failed_check=open_failed)

    assert conn is not None
    try:
        return _audit_connection(conn)
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


__all__ = [
    "DOMAIN_LOGICAL",
    "EXPECTED_COLUMNS",
    "MAX_REGISTRY_EXCHANGES",
    "MAX_REGISTRY_FILE_BYTES",
    "MAX_REGISTRY_MESSAGES",
    "RegistryAuditResult",
    "STABLE_CODES",
    "audit_registry",
    "compute_logical_registry_digest",
]
