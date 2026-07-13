# SPDX-License-Identifier: Apache-2.0
"""
L28 M2M offline end-to-end reference workflow (Foundation 14).

Verify-only integration of transcript validation, replay admission, audit,
backup, restore, and logical-state comparison inside one disposable temporary
directory. Does not sign, store private keys, access wallets, query ledgers,
or persist operational state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple, Union

from coin.m2m_conformance_cli import MAX_INPUT_BYTES, read_input_file, read_input_stdin
from coin.m2m_registry_audit import RegistryAuditResult, audit_registry
from coin.m2m_registry_backup import create_registry_backup, restore_registry_backup
from coin.m2m_replay_registry import ReplayRegistry, ReplayRegistryError
from coin.m2m_transcript_validator import verify_transcript_json
from coin.m2m_verifier import canonical_bytes

CLI_VERSION = "l28-m2m-reference-workflow/v0.1"
REPORT_VERSION = "l28-m2m-reference-workflow-report/v0.1"
PROFILE = "l28-m2m-reference-workflow/v0.1"
DOMAIN_REPORT = b"L28-M2M-V0.1-REFERENCE-WORKFLOW-REPORT\x00"

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3

_REPO_ROOT = Path(__file__).resolve().parents[1]

STAGE_ORDER = (
    "transcript_validation",
    "initial_admission",
    "source_idempotency",
    "source_audit",
    "backup",
    "restore",
    "restored_audit",
    "restored_idempotency",
    "logical_state_comparison",
)

APPROVED_INPUT_MODES = frozenset({"api", "file", "stdin"})
MAX_INPUT_MODE_LEN = 16
_FORBIDDEN_INPUT_MODE_MARKERS = (
    "/",
    "\\",
    "..",
    "secret",
    "token",
    "password",
    "bearer",
    "sk-",
)

STABLE_CODES = frozenset(
    {
        "workflow_verified",
        "invalid_input",
        "input_too_large",
        "conformance_failed",
        "terminal_required",
        "initial_admission_failed",
        "source_idempotency_failed",
        "source_audit_failed",
        "backup_failed",
        "restore_failed",
        "restored_audit_failed",
        "restored_idempotency_failed",
        "logical_state_mismatch",
        "unsafe_temporary_directory",
        "verification_backend_unavailable",
        "internal_error",
    }
)

REPORT_FIELD_ORDER = (
    "report_version",
    "profile",
    "ok",
    "code",
    "failed_stage",
    "component_code",
    "state",
    "verified_messages",
    "require_terminal",
    "input_mode",
    "input_size_bytes",
    "input_sha256",
    "logical_registry_digest",
    "exchange_count",
    "message_count",
    "stage_codes",
    "report_id",
)


@dataclass(frozen=True)
class ReferenceWorkflowResult:
    ok: bool
    code: str
    failed_stage: Optional[str]
    component_code: Optional[str]
    state: Optional[str]
    verified_messages: int
    require_terminal: bool
    input_mode: Optional[str]
    input_size_bytes: int
    input_sha256: str
    logical_registry_digest: Optional[str]
    exchange_count: int
    message_count: int
    stage_codes: Mapping[str, Optional[str]]
    report_id: str


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _empty_stage_codes() -> Dict[str, Optional[str]]:
    return {stage: None for stage in STAGE_ORDER}


def _path_inside_repo(path: Path) -> bool:
    try:
        path.resolve(strict=True).relative_to(_REPO_ROOT.resolve(strict=True))
        return True
    except (ValueError, OSError):
        return False


def _assert_safe_temp_root() -> Optional[str]:
    candidates: list[Path] = []
    tmpdir = os.environ.get("TMPDIR")
    if tmpdir:
        candidates.append(Path(tmpdir))
    candidates.append(Path(tempfile.gettempdir()))
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve(strict=False)
        except OSError:
            return "unsafe_temporary_directory"
        if _path_inside_repo(resolved):
            return "unsafe_temporary_directory"
    return None


def _input_mode_is_valid(value: Any) -> bool:
    if type(value) is not str:
        return False
    if not value or len(value) > MAX_INPUT_MODE_LEN:
        return False
    if value not in APPROVED_INPUT_MODES:
        return False
    lowered = value.lower()
    for marker in _FORBIDDEN_INPUT_MODE_MARKERS:
        if marker in lowered:
            return False
    return True


def _require_terminal_is_valid(value: Any) -> bool:
    return type(value) is bool


def compute_report_id(body_without_id: Mapping[str, Any]) -> str:
    return _sha256_hex(DOMAIN_REPORT + canonical_bytes(dict(body_without_id)))


def _workflow_code_for_transcript(
    *,
    transcript_code: str,
    envelope_code: Optional[str],
    require_terminal: bool,
) -> Tuple[str, str]:
    component = transcript_code
    if envelope_code == "verification_backend_unavailable":
        return "verification_backend_unavailable", component
    if transcript_code == "internal_error":
        return "internal_error", component
    if require_terminal and transcript_code in {
        "incomplete_transcript",
        "invalid_incomplete_when_terminal_required",
        "invalid_terminal_state",
    }:
        return "terminal_required", component
    return "conformance_failed", component


def _build_report_body(
    *,
    ok: bool,
    code: str,
    failed_stage: Optional[str],
    component_code: Optional[str],
    state: Optional[str],
    verified_messages: int,
    require_terminal: bool,
    input_mode: Optional[str],
    input_size_bytes: int,
    input_sha256: str,
    logical_registry_digest: Optional[str],
    exchange_count: int,
    message_count: int,
    stage_codes: Mapping[str, Optional[str]],
) -> Dict[str, Any]:
    if code not in STABLE_CODES:
        code = "internal_error"
        ok = False
    body = {
        "report_version": REPORT_VERSION,
        "profile": PROFILE,
        "ok": bool(ok),
        "code": code,
        "failed_stage": failed_stage,
        "component_code": component_code,
        "state": state,
        "verified_messages": int(verified_messages),
        "require_terminal": bool(require_terminal),
        "input_mode": input_mode,
        "input_size_bytes": int(input_size_bytes),
        "input_sha256": input_sha256,
        "logical_registry_digest": logical_registry_digest,
        "exchange_count": int(exchange_count),
        "message_count": int(message_count),
        "stage_codes": {stage: stage_codes.get(stage) for stage in STAGE_ORDER},
    }
    report = dict(body)
    report["report_id"] = compute_report_id(body)
    for key in REPORT_FIELD_ORDER:
        if key not in report:
            report[key] = None
    return report


def build_report(result: ReferenceWorkflowResult) -> Dict[str, Any]:
    return _build_report_body(
        ok=result.ok,
        code=result.code,
        failed_stage=result.failed_stage,
        component_code=result.component_code,
        state=result.state,
        verified_messages=result.verified_messages,
        require_terminal=result.require_terminal,
        input_mode=result.input_mode,
        input_size_bytes=result.input_size_bytes,
        input_sha256=result.input_sha256,
        logical_registry_digest=result.logical_registry_digest,
        exchange_count=result.exchange_count,
        message_count=result.message_count,
        stage_codes=result.stage_codes,
    )


def _result_from_body(body: Dict[str, Any]) -> ReferenceWorkflowResult:
    mode = body.get("input_mode")
    return ReferenceWorkflowResult(
        ok=bool(body["ok"]),
        code=str(body["code"]),
        failed_stage=body.get("failed_stage"),
        component_code=body.get("component_code"),
        state=body.get("state"),
        verified_messages=int(body["verified_messages"]),
        require_terminal=body["require_terminal"] is True,
        input_mode=mode if type(mode) is str else None,
        input_size_bytes=int(body["input_size_bytes"]),
        input_sha256=str(body["input_sha256"]),
        logical_registry_digest=body.get("logical_registry_digest"),
        exchange_count=int(body["exchange_count"]),
        message_count=int(body["message_count"]),
        stage_codes=dict(body["stage_codes"]),
        report_id=str(body["report_id"]),
    )


def _failure(
    *,
    code: str,
    failed_stage: str,
    component_code: str,
    stage_codes: Dict[str, Optional[str]],
    state: Optional[str],
    verified_messages: int,
    require_terminal: bool,
    input_mode: Optional[str],
    input_size_bytes: int,
    input_sha256: str,
    logical_registry_digest: Optional[str] = None,
    exchange_count: int = 0,
    message_count: int = 0,
) -> ReferenceWorkflowResult:
    body = _build_report_body(
        ok=False,
        code=code,
        failed_stage=failed_stage,
        component_code=component_code,
        state=state,
        verified_messages=verified_messages,
        require_terminal=require_terminal,
        input_mode=input_mode,
        input_size_bytes=input_size_bytes,
        input_sha256=input_sha256,
        logical_registry_digest=logical_registry_digest,
        exchange_count=exchange_count,
        message_count=message_count,
        stage_codes=stage_codes,
    )
    return _result_from_body(body)


def _parameter_validation_failure(
    *,
    input_size_bytes: int,
    input_sha256: str,
) -> ReferenceWorkflowResult:
    body = _build_report_body(
        ok=False,
        code="internal_error",
        failed_stage=None,
        component_code="internal_error",
        state=None,
        verified_messages=0,
        require_terminal=False,
        input_mode=None,
        input_size_bytes=input_size_bytes,
        input_sha256=input_sha256,
        logical_registry_digest=None,
        exchange_count=0,
        message_count=0,
        stage_codes=_empty_stage_codes(),
    )
    return _result_from_body(body)


def _logical_states_equal(a: RegistryAuditResult, b: RegistryAuditResult) -> bool:
    return (
        a.schema_version == b.schema_version
        and a.exchange_count == b.exchange_count
        and a.message_count == b.message_count
        and a.logical_registry_digest == b.logical_registry_digest
        and a.logical_registry_digest is not None
    )


def _admit_json(
    registry_path: Path,
    *,
    raw: bytes,
    require_terminal: bool,
    create: bool,
) -> Tuple[Optional[str], Optional[str]]:
    registry = ReplayRegistry(registry_path, create=create)
    try:
        replay = registry.check_and_record_json(raw, require_terminal=require_terminal)
    except ReplayRegistryError as exc:
        return None, exc.code
    except Exception:
        return None, "internal_error"
    finally:
        registry.close()
    return replay.code, None


def run_reference_workflow_json(
    raw: Union[str, bytes],
    *,
    require_terminal: bool = False,
    input_mode: str = "api",
) -> ReferenceWorkflowResult:
    if isinstance(raw, str):
        raw_bytes = raw.encode("utf-8")
    else:
        raw_bytes = bytes(raw)

    input_size = len(raw_bytes)
    input_sha = _sha256_hex(raw_bytes)

    if not _require_terminal_is_valid(require_terminal) or not _input_mode_is_valid(input_mode):
        return _parameter_validation_failure(
            input_size_bytes=input_size,
            input_sha256=input_sha,
        )

    stage_codes = _empty_stage_codes()

    if input_size > MAX_INPUT_BYTES:
        return _failure(
            code="input_too_large",
            failed_stage="transcript_validation",
            component_code="input_too_large",
            stage_codes=stage_codes,
            state=None,
            verified_messages=0,
            require_terminal=require_terminal,
            input_mode=input_mode,
            input_size_bytes=input_size,
            input_sha256=input_sha,
        )

    try:
        transcript = verify_transcript_json(raw_bytes, require_terminal=require_terminal)
    except Exception:
        return _failure(
            code="internal_error",
            failed_stage="transcript_validation",
            component_code="internal_error",
            stage_codes=stage_codes,
            state=None,
            verified_messages=0,
            require_terminal=require_terminal,
            input_mode=input_mode,
            input_size_bytes=input_size,
            input_sha256=input_sha,
        )

    if not transcript.ok:
        workflow_code, component = _workflow_code_for_transcript(
            transcript_code=str(transcript.code),
            envelope_code=transcript.envelope_code,
            require_terminal=require_terminal,
        )
        if transcript.envelope_code is not None:
            component = str(transcript.envelope_code)
        stage_codes["transcript_validation"] = str(transcript.code)
        return _failure(
            code=workflow_code,
            failed_stage="transcript_validation",
            component_code=component,
            stage_codes=stage_codes,
            state=transcript.state,
            verified_messages=int(transcript.verified_messages),
            require_terminal=require_terminal,
            input_mode=input_mode,
            input_size_bytes=input_size,
            input_sha256=input_sha,
        )

    stage_codes["transcript_validation"] = str(transcript.code)
    verified_messages = int(transcript.verified_messages)
    state = transcript.state

    unsafe = _assert_safe_temp_root()
    if unsafe is not None:
        return _failure(
            code=unsafe,
            failed_stage="initial_admission",
            component_code=unsafe,
            stage_codes=stage_codes,
            state=state,
            verified_messages=verified_messages,
            require_terminal=require_terminal,
            input_mode=input_mode,
            input_size_bytes=input_size,
            input_sha256=input_sha,
        )

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp).resolve()
            if _path_inside_repo(tmp_path):
                return _failure(
                    code="unsafe_temporary_directory",
                    failed_stage="initial_admission",
                    component_code="unsafe_temporary_directory",
                    stage_codes=stage_codes,
                    state=state,
                    verified_messages=verified_messages,
                    require_terminal=require_terminal,
                    input_mode=input_mode,
                    input_size_bytes=input_size,
                    input_sha256=input_sha,
                )

            source_path = (tmp_path / "source-registry.sqlite").resolve()
            backup_path = (tmp_path / "backup-registry.sqlite").resolve()
            restored_path = (tmp_path / "restored-registry.sqlite").resolve()

            initial_code, initial_err = _admit_json(
                source_path,
                raw=raw_bytes,
                require_terminal=require_terminal,
                create=True,
            )
            if initial_err is not None:
                stage_codes["initial_admission"] = initial_err
                return _failure(
                    code="initial_admission_failed",
                    failed_stage="initial_admission",
                    component_code=initial_err,
                    stage_codes=stage_codes,
                    state=state,
                    verified_messages=verified_messages,
                    require_terminal=require_terminal,
                    input_mode=input_mode,
                    input_size_bytes=input_size,
                    input_sha256=input_sha,
                )
            stage_codes["initial_admission"] = initial_code
            if initial_code != "recorded_new":
                return _failure(
                    code="initial_admission_failed",
                    failed_stage="initial_admission",
                    component_code=str(initial_code),
                    stage_codes=stage_codes,
                    state=state,
                    verified_messages=verified_messages,
                    require_terminal=require_terminal,
                    input_mode=input_mode,
                    input_size_bytes=input_size,
                    input_sha256=input_sha,
                )

            repeat_code, repeat_err = _admit_json(
                source_path,
                raw=raw_bytes,
                require_terminal=require_terminal,
                create=False,
            )
            if repeat_err is not None:
                stage_codes["source_idempotency"] = repeat_err
                return _failure(
                    code="source_idempotency_failed",
                    failed_stage="source_idempotency",
                    component_code=repeat_err,
                    stage_codes=stage_codes,
                    state=state,
                    verified_messages=verified_messages,
                    require_terminal=require_terminal,
                    input_mode=input_mode,
                    input_size_bytes=input_size,
                    input_sha256=input_sha,
                )
            stage_codes["source_idempotency"] = repeat_code
            if repeat_code != "already_recorded":
                return _failure(
                    code="source_idempotency_failed",
                    failed_stage="source_idempotency",
                    component_code=str(repeat_code),
                    stage_codes=stage_codes,
                    state=state,
                    verified_messages=verified_messages,
                    require_terminal=require_terminal,
                    input_mode=input_mode,
                    input_size_bytes=input_size,
                    input_sha256=input_sha,
                )

            source_audit = audit_registry(source_path)
            stage_codes["source_audit"] = source_audit.code
            if source_audit.code != "registry_healthy":
                return _failure(
                    code="source_audit_failed",
                    failed_stage="source_audit",
                    component_code=source_audit.code,
                    stage_codes=stage_codes,
                    state=state,
                    verified_messages=verified_messages,
                    require_terminal=require_terminal,
                    input_mode=input_mode,
                    input_size_bytes=input_size,
                    input_sha256=input_sha,
                    logical_registry_digest=source_audit.logical_registry_digest,
                    exchange_count=source_audit.exchange_count,
                    message_count=source_audit.message_count,
                )

            backup_result = create_registry_backup(source_path, backup_path)
            stage_codes["backup"] = backup_result.code
            if backup_result.code != "backup_created":
                return _failure(
                    code="backup_failed",
                    failed_stage="backup",
                    component_code=backup_result.code,
                    stage_codes=stage_codes,
                    state=state,
                    verified_messages=verified_messages,
                    require_terminal=require_terminal,
                    input_mode=input_mode,
                    input_size_bytes=input_size,
                    input_sha256=input_sha,
                    logical_registry_digest=source_audit.logical_registry_digest,
                    exchange_count=source_audit.exchange_count,
                    message_count=source_audit.message_count,
                )

            restore_result = restore_registry_backup(backup_path, restored_path)
            stage_codes["restore"] = restore_result.code
            if restore_result.code != "restore_created":
                return _failure(
                    code="restore_failed",
                    failed_stage="restore",
                    component_code=restore_result.code,
                    stage_codes=stage_codes,
                    state=state,
                    verified_messages=verified_messages,
                    require_terminal=require_terminal,
                    input_mode=input_mode,
                    input_size_bytes=input_size,
                    input_sha256=input_sha,
                    logical_registry_digest=source_audit.logical_registry_digest,
                    exchange_count=source_audit.exchange_count,
                    message_count=source_audit.message_count,
                )

            restored_audit = audit_registry(restored_path)
            stage_codes["restored_audit"] = restored_audit.code
            if restored_audit.code != "registry_healthy":
                return _failure(
                    code="restored_audit_failed",
                    failed_stage="restored_audit",
                    component_code=restored_audit.code,
                    stage_codes=stage_codes,
                    state=state,
                    verified_messages=verified_messages,
                    require_terminal=require_terminal,
                    input_mode=input_mode,
                    input_size_bytes=input_size,
                    input_sha256=input_sha,
                    logical_registry_digest=restored_audit.logical_registry_digest,
                    exchange_count=restored_audit.exchange_count,
                    message_count=restored_audit.message_count,
                )

            restored_repeat_code, restored_repeat_err = _admit_json(
                restored_path,
                raw=raw_bytes,
                require_terminal=require_terminal,
                create=False,
            )
            if restored_repeat_err is not None:
                stage_codes["restored_idempotency"] = restored_repeat_err
                return _failure(
                    code="restored_idempotency_failed",
                    failed_stage="restored_idempotency",
                    component_code=restored_repeat_err,
                    stage_codes=stage_codes,
                    state=state,
                    verified_messages=verified_messages,
                    require_terminal=require_terminal,
                    input_mode=input_mode,
                    input_size_bytes=input_size,
                    input_sha256=input_sha,
                    logical_registry_digest=restored_audit.logical_registry_digest,
                    exchange_count=restored_audit.exchange_count,
                    message_count=restored_audit.message_count,
                )
            stage_codes["restored_idempotency"] = restored_repeat_code
            if restored_repeat_code != "already_recorded":
                return _failure(
                    code="restored_idempotency_failed",
                    failed_stage="restored_idempotency",
                    component_code=str(restored_repeat_code),
                    stage_codes=stage_codes,
                    state=state,
                    verified_messages=verified_messages,
                    require_terminal=require_terminal,
                    input_mode=input_mode,
                    input_size_bytes=input_size,
                    input_sha256=input_sha,
                    logical_registry_digest=restored_audit.logical_registry_digest,
                    exchange_count=restored_audit.exchange_count,
                    message_count=restored_audit.message_count,
                )

            if not _logical_states_equal(source_audit, restored_audit):
                stage_codes["logical_state_comparison"] = "logical_state_mismatch"
                return _failure(
                    code="logical_state_mismatch",
                    failed_stage="logical_state_comparison",
                    component_code="logical_state_mismatch",
                    stage_codes=stage_codes,
                    state=state,
                    verified_messages=verified_messages,
                    require_terminal=require_terminal,
                    input_mode=input_mode,
                    input_size_bytes=input_size,
                    input_sha256=input_sha,
                    logical_registry_digest=restored_audit.logical_registry_digest,
                    exchange_count=restored_audit.exchange_count,
                    message_count=restored_audit.message_count,
                )

            stage_codes["logical_state_comparison"] = "ok"
            body = _build_report_body(
                ok=True,
                code="workflow_verified",
                failed_stage=None,
                component_code="workflow_verified",
                state=state,
                verified_messages=verified_messages,
                require_terminal=require_terminal,
                input_mode=input_mode,
                input_size_bytes=input_size,
                input_sha256=input_sha,
                logical_registry_digest=restored_audit.logical_registry_digest,
                exchange_count=restored_audit.exchange_count,
                message_count=restored_audit.message_count,
                stage_codes=stage_codes,
            )
            return _result_from_body(body)
    except Exception:
        return _failure(
            code="internal_error",
            failed_stage="initial_admission",
            component_code="internal_error",
            stage_codes=stage_codes,
            state=state,
            verified_messages=verified_messages,
            require_terminal=require_terminal,
            input_mode=input_mode,
            input_size_bytes=input_size,
            input_sha256=input_sha,
        )


def emit_report(report: Mapping[str, Any], *, pretty: bool) -> None:
    if pretty:
        text = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False)
    else:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    sys.stdout.write(text + "\n")


def _exit_for_result(result: ReferenceWorkflowResult) -> int:
    if result.ok and result.code == "workflow_verified":
        return EXIT_PASS
    if result.code in {
        "unsafe_temporary_directory",
        "verification_backend_unavailable",
        "internal_error",
    }:
        return EXIT_INTERNAL
    if result.code in {"invalid_input", "input_too_large"} and result.input_mode in {
        "file",
        "stdin",
    }:
        return EXIT_USAGE
    if result.code in {
        "conformance_failed",
        "terminal_required",
        "initial_admission_failed",
        "source_idempotency_failed",
        "source_audit_failed",
        "backup_failed",
        "restore_failed",
        "restored_audit_failed",
        "restored_idempotency_failed",
        "logical_state_mismatch",
    }:
        return EXIT_FAIL
    return EXIT_INTERNAL


def _usage_message() -> str:
    return (
        "usage: python -m coin.m2m_reference_workflow "
        "--input PATH [--require-terminal] [--pretty]\n"
        "       python -m coin.m2m_reference_workflow "
        "--stdin [--require-terminal] [--pretty]\n"
        "       python -m coin.m2m_reference_workflow --version\n"
    )


def _cli_failure_report(
    *,
    code: str,
    require_terminal: bool,
    input_mode: Optional[str],
    input_size_bytes: Optional[int],
    input_sha256: Optional[str],
) -> ReferenceWorkflowResult:
    if code not in STABLE_CODES:
        code = "internal_error"
    stage_codes = _empty_stage_codes()
    body = _build_report_body(
        ok=False,
        code=code,
        failed_stage="transcript_validation",
        component_code=code,
        state=None,
        verified_messages=0,
        require_terminal=require_terminal is True,
        input_mode=input_mode if _input_mode_is_valid(input_mode) else None,
        input_size_bytes=int(input_size_bytes or 0),
        input_sha256=input_sha256 or _sha256_hex(b""),
        logical_registry_digest=None,
        exchange_count=0,
        message_count=0,
        stage_codes=stage_codes,
    )
    return _result_from_body(body)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m coin.m2m_reference_workflow",
        description="Offline L28 M2M end-to-end reference workflow (verify-only).",
        add_help=True,
    )
    src = parser.add_mutually_exclusive_group(required=False)
    src.add_argument("--input", metavar="PATH", help="Read transcript from a regular local file")
    src.add_argument("--stdin", action="store_true", help="Read transcript from standard input")
    parser.add_argument(
        "--require-terminal",
        action="store_true",
        help="Require a terminal transcript state",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON report (content unchanged)",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print CLI version and exit",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        if code in (0, None):
            return 0
        return EXIT_USAGE

    if args.version:
        if args.input is not None or args.stdin or args.require_terminal:
            sys.stderr.write(_usage_message())
            return EXIT_USAGE
        sys.stdout.write(CLI_VERSION + "\n")
        return EXIT_PASS

    if bool(args.input) == bool(args.stdin):
        sys.stderr.write(_usage_message())
        return EXIT_USAGE

    pretty = bool(args.pretty)
    require_terminal = args.require_terminal
    if type(require_terminal) is not bool:
        result = _parameter_validation_failure(
            input_size_bytes=0,
            input_sha256=_sha256_hex(b""),
        )
        emit_report(build_report(result), pretty=pretty)
        return EXIT_INTERNAL

    if args.stdin:
        raw, err = read_input_stdin()
        input_mode = "stdin"
    else:
        raw, err = read_input_file(args.input)
        input_mode = "file"

    if err is not None:
        mapped = {
            "input_not_found": "invalid_input",
            "input_not_regular_file": "invalid_input",
            "input_symlink_rejected": "invalid_input",
            "input_read_error": "invalid_input",
            "stdin_is_tty": "invalid_input",
            "input_too_large": "input_too_large",
            "internal_error": "internal_error",
        }.get(err, "invalid_input")
        result = _cli_failure_report(
            code=mapped,
            require_terminal=require_terminal,
            input_mode=input_mode,
            input_size_bytes=len(raw) if raw is not None else 0,
            input_sha256=_sha256_hex(raw) if raw is not None else _sha256_hex(b""),
        )
        emit_report(build_report(result), pretty=pretty)
        return _exit_for_result(result)

    assert raw is not None
    result = run_reference_workflow_json(
        raw,
        require_terminal=require_terminal,
        input_mode=input_mode,
    )
    emit_report(build_report(result), pretty=pretty)
    return _exit_for_result(result)


if __name__ == "__main__":
    raise SystemExit(main())
