# SPDX-License-Identifier: Apache-2.0
"""
L28 M2M offline replay-registry backup and verified recovery (Foundation 12).

Creates and restores standalone SQLite replay-registry artifacts with audit gates.
Does not modify sources, activate registries, or provide online snapshot service.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from coin.m2m_registry_audit import (
    MAX_REGISTRY_FILE_BYTES,
    RegistryAuditResult,
    audit_registry,
)
from coin.m2m_registry_audit_cli import compute_report_id as compute_audit_report_id
from coin.m2m_replay_registry import SCHEMA_VERSION
from coin.m2m_verifier import canonical_bytes

DOMAIN_BACKUP_REPORT = b"L28-M2M-V0.1-REGISTRY-BACKUP-REPORT\x00"
REPORT_VERSION = "l28-m2m-registry-backup-report/v0.1"
PROFILE = "l28-m2m-replay-registry-backup/v0.1"
BUSY_TIMEOUT_MS = 5000
_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEMP_PREFIX = ".m2m-registry-work-"
_TEMP_SUFFIX = ".tmp"

STABLE_CODES = frozenset(
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

_EXIT_USAGE_CODES = frozenset(
    {
        "invalid_source_path",
        "source_not_found",
        "invalid_backup_path",
        "backup_not_found",
        "invalid_destination_path",
        "destination_exists",
        "unsafe_path",
        "same_file",
    }
)


@dataclass(frozen=True)
class RegistryBackupResult:
    ok: bool
    code: str
    operation: str
    destination_created: bool = False
    schema_version: Optional[int] = None
    exchange_count: int = 0
    message_count: int = 0
    logical_registry_digest: Optional[str] = None
    input_audit_report_id: Optional[str] = None
    output_audit_report_id: Optional[str] = None
    artifact_sha256: Optional[str] = None
    artifact_size_bytes: int = 0
    report_id: Optional[str] = None


def _result(
    *,
    ok: bool,
    code: str,
    operation: str,
    destination_created: bool = False,
    schema_version: Optional[int] = None,
    exchange_count: int = 0,
    message_count: int = 0,
    logical_registry_digest: Optional[str] = None,
    input_audit_report_id: Optional[str] = None,
    output_audit_report_id: Optional[str] = None,
    artifact_sha256: Optional[str] = None,
    artifact_size_bytes: int = 0,
) -> RegistryBackupResult:
    if code not in STABLE_CODES:
        code = "internal_error"
    body = _report_body(
        ok=ok,
        code=code,
        operation=operation,
        destination_created=destination_created,
        schema_version=schema_version,
        exchange_count=exchange_count,
        message_count=message_count,
        logical_registry_digest=logical_registry_digest,
        input_audit_report_id=input_audit_report_id,
        output_audit_report_id=output_audit_report_id,
        artifact_sha256=artifact_sha256,
        artifact_size_bytes=artifact_size_bytes,
    )
    report_id = compute_backup_report_id(body)
    return RegistryBackupResult(
        ok=ok,
        code=code,
        operation=operation,
        destination_created=destination_created,
        schema_version=schema_version,
        exchange_count=exchange_count,
        message_count=message_count,
        logical_registry_digest=logical_registry_digest,
        input_audit_report_id=input_audit_report_id,
        output_audit_report_id=output_audit_report_id,
        artifact_sha256=artifact_sha256,
        artifact_size_bytes=artifact_size_bytes,
        report_id=report_id,
    )


def _report_body(
    *,
    ok: bool,
    code: str,
    operation: str,
    destination_created: bool,
    schema_version: Optional[int],
    exchange_count: int,
    message_count: int,
    logical_registry_digest: Optional[str],
    input_audit_report_id: Optional[str],
    output_audit_report_id: Optional[str],
    artifact_sha256: Optional[str],
    artifact_size_bytes: int,
) -> Dict[str, Any]:
    return {
        "report_version": REPORT_VERSION,
        "profile": PROFILE,
        "ok": bool(ok),
        "code": code,
        "operation": operation,
        "destination_created": bool(destination_created),
        "schema_version": schema_version,
        "exchange_count": int(exchange_count),
        "message_count": int(message_count),
        "logical_registry_digest": logical_registry_digest,
        "input_audit_report_id": input_audit_report_id,
        "output_audit_report_id": output_audit_report_id,
        "artifact_sha256": artifact_sha256,
        "artifact_size_bytes": int(artifact_size_bytes),
    }


def compute_backup_report_id(body_without_id: Dict[str, Any]) -> str:
    return hashlib.sha256(
        DOMAIN_BACKUP_REPORT + canonical_bytes(dict(body_without_id))
    ).hexdigest()


def _audit_report_id(audit: RegistryAuditResult) -> str:
    from coin.m2m_registry_audit_cli import PROFILE, REPORT_VERSION

    body = {
        "report_version": REPORT_VERSION,
        "profile": PROFILE,
        "ok": bool(audit.ok),
        "code": audit.code,
        "schema_version": audit.schema_version,
        "exchange_count": int(audit.exchange_count),
        "message_count": int(audit.message_count),
        "terminal_exchange_count": int(audit.terminal_exchange_count),
        "nonterminal_exchange_count": int(audit.nonterminal_exchange_count),
        "logical_registry_digest": audit.logical_registry_digest,
        "failed_check": audit.failed_check,
    }
    return compute_audit_report_id(body)


@dataclass(frozen=True)
class _FileIdentity:
    size: int
    mtime_ns: int
    mode: int
    inode: int
    dev: int
    sha256: str


def _file_identity(path: Path) -> Optional[_FileIdentity]:
    try:
        st = os.lstat(path)
        if not stat.S_ISREG(st.st_mode):
            return None
        data = path.read_bytes()
        if len(data) > MAX_REGISTRY_FILE_BYTES:
            return None
        return _FileIdentity(
            size=st.st_size,
            mtime_ns=st.st_mtime_ns,
            mode=stat.S_IMODE(st.st_mode),
            inode=st.st_ino,
            dev=st.st_dev,
            sha256=hashlib.sha256(data).hexdigest(),
        )
    except OSError:
        return None


def _same_file(path_a: Path, path_b: Path) -> bool:
    try:
        sta = os.lstat(path_a)
        stb = os.lstat(path_b)
    except OSError:
        return False
    if not stat.S_ISREG(sta.st_mode) or not stat.S_ISREG(stb.st_mode):
        return False
    return sta.st_dev == stb.st_dev and sta.st_ino == stb.st_ino


def _resolve_outside_repo(raw: Path) -> Tuple[Optional[Path], Optional[str]]:
    if not raw.is_absolute():
        return None, "invalid_destination_path"
    parent = raw.parent
    if not parent.exists() or not parent.is_dir():
        return None, "invalid_destination_path"
    try:
        if parent.is_symlink():
            return None, "unsafe_path"
        resolved_parent = parent.resolve(strict=True)
        candidate = (resolved_parent / raw.name).resolve(strict=False)
        repo = _REPO_ROOT.resolve(strict=True)
    except OSError:
        return None, "unsafe_path"
    try:
        candidate.relative_to(repo)
        return None, "unsafe_path"
    except ValueError:
        pass
    return Path(os.path.join(str(resolved_parent), raw.name)), None


def _validate_existing_input(
    path: Union[str, Path],
    *,
    not_found_code: str,
    invalid_code: str,
) -> Tuple[Optional[Path], Optional[str]]:
    if not isinstance(path, (str, Path)):
        return None, invalid_code
    raw = Path(path)
    if not raw.is_absolute():
        return None, invalid_code
    resolved, err = _resolve_outside_repo(raw)
    if err is not None:
        return None, err
    assert resolved is not None
    try:
        st = os.lstat(resolved)
    except FileNotFoundError:
        return None, not_found_code
    except OSError:
        return None, "unsafe_path"
    if stat.S_ISLNK(st.st_mode):
        return None, "unsafe_path"
    if not stat.S_ISREG(st.st_mode):
        return None, "unsafe_path"
    if st.st_size > MAX_REGISTRY_FILE_BYTES:
        return None, "registry_resource_limit"
    return resolved, None


def _validate_new_destination(
    path: Union[str, Path],
    *,
    peer: Optional[Path] = None,
) -> Tuple[Optional[Path], Optional[str]]:
    if not isinstance(path, (str, Path)):
        return None, "invalid_destination_path"
    raw = Path(path)
    if not raw.is_absolute():
        return None, "invalid_destination_path"
    resolved, err = _resolve_outside_repo(raw)
    if err is not None:
        return None, err
    assert resolved is not None
    if peer is not None and _same_file(resolved, peer):
        return None, "same_file"
    try:
        os.lstat(resolved)
        return None, "destination_exists"
    except FileNotFoundError:
        pass
    except OSError:
        return None, "unsafe_path"
    return resolved, None


def _temp_path_in(parent: Path) -> Path:
    name = _TEMP_PREFIX + secrets.token_hex(16) + _TEMP_SUFFIX
    return parent / name


def _remove_path(path: Path) -> None:
    try:
        if path.exists() or path.is_symlink():
            path.unlink()
    except OSError:
        pass
    for suffix in ("-journal", "-wal", "-shm"):
        sidecar = Path(str(path) + suffix)
        try:
            if sidecar.exists() or sidecar.is_symlink():
                sidecar.unlink()
        except OSError:
            pass


def _fsync_file(path: Path) -> bool:
    try:
        with open(path, "rb") as fh:
            os.fsync(fh.fileno())
        return True
    except OSError:
        return False


def _fsync_parent_dir(path: Path) -> bool:
    try:
        fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return True
    except OSError:
        return False


def _set_mode_0600(path: Path) -> bool:
    try:
        os.chmod(path, 0o600)
        return True
    except OSError:
        return False


def _open_backup_source(path: Path) -> Tuple[Optional[sqlite3.Connection], Optional[str]]:
    try:
        conn = sqlite3.connect(
            f"file:{path}?mode=ro",
            uri=True,
            timeout=BUSY_TIMEOUT_MS / 1000.0,
        )
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute(f"PRAGMA busy_timeout={int(BUSY_TIMEOUT_MS)}")
        conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
        return conn, None
    except sqlite3.Error:
        return None, "backup_failed"
    except OSError:
        return None, "backup_failed"


def _sqlite_backup(source: Path, dest: Path) -> Optional[str]:
    source_conn, err = _open_backup_source(source)
    if err is not None:
        return err
    assert source_conn is not None
    dest_conn: Optional[sqlite3.Connection] = None
    try:
        dest_conn = sqlite3.connect(str(dest))
        source_conn.backup(dest_conn)
        dest_conn.commit()
        return None
    except sqlite3.Error:
        return "backup_failed"
    except OSError:
        return "backup_failed"
    finally:
        try:
            if dest_conn is not None:
                dest_conn.close()
        except sqlite3.Error:
            pass
        try:
            source_conn.close()
        except sqlite3.Error:
            pass


def _copy_exact_bytes(source: Path, dest: Path) -> Optional[str]:
    try:
        size = source.stat().st_size
        if size > MAX_REGISTRY_FILE_BYTES:
            return "registry_resource_limit"
        data = source.read_bytes()
        if len(data) != size:
            return "restore_failed"
        dest.write_bytes(data)
        return None
    except OSError:
        return "restore_failed"


def _audit_healthy(audit: RegistryAuditResult) -> bool:
    return bool(audit.ok and audit.code == "registry_healthy")


def _audit_failure_code(operation: str) -> str:
    if operation == "backup":
        return "source_audit_failed"
    return "backup_audit_failed"


def _output_audit_failure_code(operation: str) -> str:
    if operation == "backup":
        return "backup_audit_failed"
    return "restore_audit_failed"


def _logical_state_equal(a: RegistryAuditResult, b: RegistryAuditResult) -> bool:
    return (
        a.schema_version == b.schema_version
        and a.exchange_count == b.exchange_count
        and a.message_count == b.message_count
        and a.logical_registry_digest == b.logical_registry_digest
    )


@dataclass(frozen=True)
class _PublishedIdentity:
    dev: int
    inode: int


def _inode_identity(path: Path) -> Optional[Tuple[int, int]]:
    try:
        st = os.lstat(path)
        return st.st_dev, st.st_ino
    except OSError:
        return None


def _remove_published_if_unchanged(dest: Path, published: _PublishedIdentity) -> None:
    ident = _inode_identity(dest)
    if ident == (published.dev, published.inode):
        _remove_path(dest)


def _rollback_publication(
    temp: Path,
    dest: Path,
    published: _PublishedIdentity,
    *,
    temp_unlinked: bool,
) -> None:
    _remove_published_if_unchanged(dest, published)
    if not temp_unlinked:
        ident = _inode_identity(temp)
        if ident == (published.dev, published.inode):
            try:
                temp.unlink()
            except OSError:
                pass


def _publish_atomic(
    temp: Path, dest: Path
) -> Tuple[Optional[str], Optional[_PublishedIdentity]]:
    """
    Publish using atomic hard-link creation.

    ``os.link(temp, dest, follow_symlinks=False)`` fails closed with
    ``FileExistsError`` when the destination name already exists, including
    symlinks. Never uses ``os.rename`` or ``os.replace``.
    """
    try:
        os.link(temp, dest, follow_symlinks=False)
    except FileExistsError:
        _remove_path(temp)
        return "destination_exists", None
    except OSError:
        _remove_path(temp)
        return "publish_failed", None

    try:
        st = os.lstat(dest)
        published = _PublishedIdentity(dev=st.st_dev, inode=st.st_ino)
    except OSError:
        _remove_path(temp)
        return "publish_failed", None

    if not _fsync_parent_dir(dest):
        _rollback_publication(temp, dest, published, temp_unlinked=False)
        return "publish_failed", None

    try:
        temp.unlink()
    except OSError:
        _rollback_publication(temp, dest, published, temp_unlinked=False)
        return "publish_failed", published

    if not _fsync_parent_dir(dest):
        _remove_published_if_unchanged(dest, published)
        return "publish_failed", published

    return None, published


def create_registry_backup(
    source_path: Union[str, Path],
    destination_path: Union[str, Path],
) -> RegistryBackupResult:
    operation = "backup"
    source, src_err = _validate_existing_input(
        source_path,
        not_found_code="source_not_found",
        invalid_code="invalid_source_path",
    )
    if src_err is not None:
        return _result(ok=False, code=src_err, operation=operation)

    dest, dst_err = _validate_new_destination(destination_path, peer=source)
    if dst_err is not None:
        return _result(ok=False, code=dst_err, operation=operation)

    assert source is not None and dest is not None

    source_audit = audit_registry(source)
    if not _audit_healthy(source_audit):
        code = _audit_failure_code(operation)
        if source_audit.code == "registry_schema_mismatch":
            code = "unsupported_registry_schema"
        return _result(
            ok=False,
            code=code,
            operation=operation,
            input_audit_report_id=_audit_report_id(source_audit),
        )

    before = _file_identity(source)
    if before is None:
        return _result(ok=False, code="source_audit_failed", operation=operation)

    temp: Optional[Path] = _temp_path_in(dest.parent)
    _remove_path(temp)
    try:
        err = _sqlite_backup(source, temp)
        if err is not None:
            return _result(ok=False, code=err, operation=operation)

        if not _set_mode_0600(temp) or not _fsync_file(temp):
            return _result(ok=False, code="backup_failed", operation=operation)

        temp_audit = audit_registry(temp)
        if not _audit_healthy(temp_audit):
            code = _output_audit_failure_code(operation)
            if temp_audit.code == "registry_schema_mismatch":
                code = "unsupported_registry_schema"
            return _result(
                ok=False,
                code=code,
                operation=operation,
                input_audit_report_id=_audit_report_id(source_audit),
                output_audit_report_id=_audit_report_id(temp_audit),
            )

        if not _logical_state_equal(source_audit, temp_audit):
            return _result(
                ok=False,
                code="logical_registry_mismatch",
                operation=operation,
                input_audit_report_id=_audit_report_id(source_audit),
                output_audit_report_id=_audit_report_id(temp_audit),
            )

        after = _file_identity(source)
        if after is None or (
            after.size != before.size
            or after.mtime_ns != before.mtime_ns
            or after.inode != before.inode
            or after.dev != before.dev
            or after.sha256 != before.sha256
            or after.mode != before.mode
        ):
            return _result(
                ok=False,
                code="source_changed",
                operation=operation,
                input_audit_report_id=_audit_report_id(source_audit),
                output_audit_report_id=_audit_report_id(temp_audit),
            )

        pub_err, published = _publish_atomic(temp, dest)
        if pub_err is not None:
            return _result(
                ok=False,
                code=pub_err,
                operation=operation,
                input_audit_report_id=_audit_report_id(source_audit),
                output_audit_report_id=_audit_report_id(temp_audit),
            )
        temp = None

        final_audit = audit_registry(dest)
        if not _audit_healthy(final_audit):
            if published is not None:
                _remove_published_if_unchanged(dest, published)
            return _result(
                ok=False,
                code="backup_audit_failed",
                operation=operation,
                input_audit_report_id=_audit_report_id(source_audit),
                output_audit_report_id=_audit_report_id(final_audit),
            )

        artifact = _file_identity(dest)
        if artifact is None:
            if published is not None:
                _remove_published_if_unchanged(dest, published)
            return _result(ok=False, code="backup_failed", operation=operation)

        return _result(
            ok=True,
            code="backup_created",
            operation=operation,
            destination_created=True,
            schema_version=final_audit.schema_version,
            exchange_count=final_audit.exchange_count,
            message_count=final_audit.message_count,
            logical_registry_digest=final_audit.logical_registry_digest,
            input_audit_report_id=_audit_report_id(source_audit),
            output_audit_report_id=_audit_report_id(final_audit),
            artifact_sha256=artifact.sha256,
            artifact_size_bytes=artifact.size,
        )
    finally:
        if temp is not None:
            _remove_path(temp)


def restore_registry_backup(
    backup_path: Union[str, Path],
    destination_path: Union[str, Path],
) -> RegistryBackupResult:
    operation = "restore"
    backup, bak_err = _validate_existing_input(
        backup_path,
        not_found_code="backup_not_found",
        invalid_code="invalid_backup_path",
    )
    if bak_err is not None:
        return _result(ok=False, code=bak_err, operation=operation)

    dest, dst_err = _validate_new_destination(destination_path, peer=backup)
    if dst_err is not None:
        return _result(ok=False, code=dst_err, operation=operation)

    assert backup is not None and dest is not None

    backup_audit = audit_registry(backup)
    if not _audit_healthy(backup_audit):
        code = _audit_failure_code(operation)
        if backup_audit.code == "registry_schema_mismatch":
            code = "unsupported_registry_schema"
        return _result(
            ok=False,
            code=code,
            operation=operation,
            input_audit_report_id=_audit_report_id(backup_audit),
        )

    before = _file_identity(backup)
    if before is None:
        return _result(ok=False, code="backup_audit_failed", operation=operation)

    temp: Optional[Path] = _temp_path_in(dest.parent)
    _remove_path(temp)
    try:
        err = _copy_exact_bytes(backup, temp)
        if err is not None:
            return _result(ok=False, code=err, operation=operation)

        if not _set_mode_0600(temp) or not _fsync_file(temp):
            return _result(ok=False, code="restore_failed", operation=operation)

        temp_audit = audit_registry(temp)
        if not _audit_healthy(temp_audit):
            code = _output_audit_failure_code(operation)
            if temp_audit.code == "registry_schema_mismatch":
                code = "unsupported_registry_schema"
            return _result(
                ok=False,
                code=code,
                operation=operation,
                input_audit_report_id=_audit_report_id(backup_audit),
                output_audit_report_id=_audit_report_id(temp_audit),
            )

        if not _logical_state_equal(backup_audit, temp_audit):
            return _result(
                ok=False,
                code="logical_registry_mismatch",
                operation=operation,
                input_audit_report_id=_audit_report_id(backup_audit),
                output_audit_report_id=_audit_report_id(temp_audit),
            )

        temp_identity = _file_identity(temp)
        if temp_identity is None or temp_identity.sha256 != before.sha256:
            return _result(
                ok=False,
                code="artifact_hash_mismatch",
                operation=operation,
                input_audit_report_id=_audit_report_id(backup_audit),
                output_audit_report_id=_audit_report_id(temp_audit),
            )

        after = _file_identity(backup)
        if after is None or (
            after.size != before.size
            or after.mtime_ns != before.mtime_ns
            or after.inode != before.inode
            or after.dev != before.dev
            or after.sha256 != before.sha256
            or after.mode != before.mode
        ):
            return _result(
                ok=False,
                code="backup_changed",
                operation=operation,
                input_audit_report_id=_audit_report_id(backup_audit),
                output_audit_report_id=_audit_report_id(temp_audit),
            )

        pub_err, published = _publish_atomic(temp, dest)
        if pub_err is not None:
            return _result(
                ok=False,
                code=pub_err,
                operation=operation,
                input_audit_report_id=_audit_report_id(backup_audit),
                output_audit_report_id=_audit_report_id(temp_audit),
            )
        temp = None

        final_audit = audit_registry(dest)
        if not _audit_healthy(final_audit):
            if published is not None:
                _remove_published_if_unchanged(dest, published)
            return _result(
                ok=False,
                code="restore_audit_failed",
                operation=operation,
                input_audit_report_id=_audit_report_id(backup_audit),
                output_audit_report_id=_audit_report_id(final_audit),
            )

        if not _logical_state_equal(backup_audit, final_audit):
            if published is not None:
                _remove_published_if_unchanged(dest, published)
            return _result(
                ok=False,
                code="logical_registry_mismatch",
                operation=operation,
                input_audit_report_id=_audit_report_id(backup_audit),
                output_audit_report_id=_audit_report_id(final_audit),
            )

        artifact = _file_identity(dest)
        if artifact is None or artifact.sha256 != before.sha256:
            if published is not None:
                _remove_published_if_unchanged(dest, published)
            return _result(
                ok=False,
                code="artifact_hash_mismatch",
                operation=operation,
                input_audit_report_id=_audit_report_id(backup_audit),
                output_audit_report_id=_audit_report_id(final_audit),
            )

        return _result(
            ok=True,
            code="restore_created",
            operation=operation,
            destination_created=True,
            schema_version=final_audit.schema_version,
            exchange_count=final_audit.exchange_count,
            message_count=final_audit.message_count,
            logical_registry_digest=final_audit.logical_registry_digest,
            input_audit_report_id=_audit_report_id(backup_audit),
            output_audit_report_id=_audit_report_id(final_audit),
            artifact_sha256=artifact.sha256,
            artifact_size_bytes=artifact.size,
        )
    finally:
        if temp is not None:
            _remove_path(temp)


__all__ = [
    "DOMAIN_BACKUP_REPORT",
    "PROFILE",
    "REPORT_VERSION",
    "RegistryBackupResult",
    "STABLE_CODES",
    "compute_backup_report_id",
    "create_registry_backup",
    "restore_registry_backup",
]
