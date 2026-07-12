# SPDX-License-Identifier: Apache-2.0
"""
L28 M2M offline conformance CLI (Foundation 7) with optional replay admission gate
(Foundation 9).

Reads one explicitly selected local transcript (file or stdin), runs the
Foundation 6 transcript validator, and emits exactly one deterministic JSON
report to stdout. Optional registry mode integrates Foundation 8 replay/idempotency.

Verify-only. No signing, wallet, network, ledger, or report-file writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from typing import Any, Dict, Mapping, Optional, Tuple

from coin.m2m_transcript_validator import verify_transcript_json
from coin.m2m_verifier import canonical_bytes

CLI_VERSION = "l28-m2m-conformance-cli/v0.1"
REPORT_VERSION = "l28-m2m-conformance-report/v0.1"
PROFILE = "l28-m2m-transcript/v0.1"
DOMAIN_REPORT = b"L28-M2M-V0.1-REPORT\x00"

ADMISSION_REPORT_VERSION = "l28-m2m-admission-report/v0.1"
ADMISSION_PROFILE = "l28-m2m-replay-admission/v0.1"
DOMAIN_ADMISSION_REPORT = b"L28-M2M-V0.1-ADMISSION-REPORT\x00"

MAX_INPUT_BYTES = 1_048_576

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3
EXIT_IDEMPOTENT = 4

CLI_CODES = frozenset(
    {
        "usage_error",
        "input_not_found",
        "input_not_regular_file",
        "input_symlink_rejected",
        "stdin_is_tty",
        "input_read_error",
        "input_too_large",
        "internal_error",
    }
)

REPORT_FIELD_ORDER = (
    "report_version",
    "profile",
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
    "report_id",
)

ADMISSION_REPORT_FIELD_ORDER = (
    "report_version",
    "profile",
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
)

_REGISTRY_EXIT2_CODES = frozenset(
    {
        "invalid_registry_path",
        "registry_path_not_absolute",
        "registry_inside_repository",
        "registry_symlink_rejected",
        "registry_not_regular_file",
        "registry_not_found",
        "registry_already_exists",
        "registry_io_error",
        "registry_locked",
    }
)

_REGISTRY_EXIT1_CODES = frozenset(
    {
        "exchange_fork",
        "message_replay",
        "terminal_exchange_extension",
        "verification_failed",
    }
)

_REGISTRY_EXIT0_CODES = frozenset({"recorded_new", "recorded_extension"})

_REGISTRY_EXIT4_CODES = frozenset({"already_recorded", "already_recorded_prefix"})


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_report_id(body_without_id: Mapping[str, Any]) -> str:
    """
    Deterministic report integrity identifier.

    report_id = SHA-256(L28-M2M-V0.1-REPORT\\x00 || Canon(report body without report_id))
    Not a signature, attestation, settlement proof, or trust claim.
    """
    return _sha256_hex(DOMAIN_REPORT + canonical_bytes(dict(body_without_id)))


def compute_admission_report_id(body_without_id: Mapping[str, Any]) -> str:
    """
    Deterministic admission report integrity identifier.

    report_id = SHA-256(L28-M2M-V0.1-ADMISSION-REPORT\\x00 || Canon(body without report_id))
    Not a signature, settlement proof, service completion proof, or authorization to spend.
    """
    return _sha256_hex(DOMAIN_ADMISSION_REPORT + canonical_bytes(dict(body_without_id)))


def build_report(
    *,
    ok: bool,
    code: str,
    state: Optional[str],
    exchange_id: Optional[str],
    verified_messages: int,
    failed_index: Optional[int],
    envelope_code: Optional[str],
    settlement_transaction_id: Optional[str],
    require_terminal: bool,
    input_mode: Optional[str],
    input_size_bytes: Optional[int],
    input_sha256: Optional[str],
) -> Dict[str, Any]:
    body = {
        "report_version": REPORT_VERSION,
        "profile": PROFILE,
        "ok": ok,
        "code": code,
        "state": state,
        "exchange_id": exchange_id,
        "verified_messages": verified_messages,
        "failed_index": failed_index,
        "envelope_code": envelope_code,
        "settlement_transaction_id": settlement_transaction_id,
        "require_terminal": require_terminal,
        "input_mode": input_mode,
        "input_size_bytes": input_size_bytes,
        "input_sha256": input_sha256,
    }
    report = dict(body)
    report["report_id"] = compute_report_id(body)
    # Ensure schema completeness / stable key set.
    for key in REPORT_FIELD_ORDER:
        if key not in report:
            report[key] = None
    return report


def build_admission_report(
    *,
    conformance_body: Mapping[str, Any],
    conformance_report_id: str,
    ok: bool,
    admitted: bool,
    registry_code: Optional[str],
    newly_recorded: bool,
    new_messages: int,
    exchange_hash: Optional[str],
    transcript_fingerprint: Optional[str],
    head_message_id: Optional[str],
    registry_message_count: Optional[int],
) -> Dict[str, Any]:
    body = {
        "report_version": ADMISSION_REPORT_VERSION,
        "profile": ADMISSION_PROFILE,
        "ok": ok,
        "code": conformance_body["code"],
        "state": conformance_body["state"],
        "exchange_id": conformance_body["exchange_id"],
        "verified_messages": conformance_body["verified_messages"],
        "failed_index": conformance_body["failed_index"],
        "envelope_code": conformance_body["envelope_code"],
        "settlement_transaction_id": conformance_body["settlement_transaction_id"],
        "require_terminal": conformance_body["require_terminal"],
        "input_mode": conformance_body["input_mode"],
        "input_size_bytes": conformance_body["input_size_bytes"],
        "input_sha256": conformance_body["input_sha256"],
        "conformance_report_id": conformance_report_id,
        "admitted": admitted,
        "registry_code": registry_code,
        "newly_recorded": newly_recorded,
        "new_messages": new_messages,
        "exchange_hash": exchange_hash,
        "transcript_fingerprint": transcript_fingerprint,
        "head_message_id": head_message_id,
        "registry_message_count": registry_message_count,
    }
    report = dict(body)
    report["report_id"] = compute_admission_report_id(body)
    for key in ADMISSION_REPORT_FIELD_ORDER:
        if key not in report:
            report[key] = None
    return report


def emit_report(report: Mapping[str, Any], *, pretty: bool) -> None:
    if pretty:
        text = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False)
    else:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    sys.stdout.write(text + "\n")


def _usage_message() -> str:
    return (
        "usage: python -m coin.m2m_conformance_cli "
        "(--input PATH | --stdin) [--require-terminal] [--pretty] "
        "[--replay-registry ABSOLUTE_PATH | --create-replay-registry ABSOLUTE_PATH] "
        "| --version\n"
    )


def read_input_file(path: str) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Read an explicitly named regular file safely.

    Returns (raw_bytes, error_code). error_code is a CLI code on failure.
    Does not follow/accept symlinks. Does not include path details in errors.
    """
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return None, "input_not_found"
    except OSError:
        return None, "input_read_error"

    if stat.S_ISLNK(st.st_mode):
        return None, "input_symlink_rejected"
    if not stat.S_ISREG(st.st_mode):
        return None, "input_not_regular_file"

    try:
        with open(path, "rb") as fh:
            raw = fh.read(MAX_INPUT_BYTES + 1)
    except OSError:
        return None, "input_read_error"

    if len(raw) > MAX_INPUT_BYTES:
        return None, "input_too_large"
    return raw, None


def read_input_stdin() -> Tuple[Optional[bytes], Optional[str]]:
    if sys.stdin.isatty():
        return None, "stdin_is_tty"
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    except OSError:
        return None, "input_read_error"
    if len(raw) > MAX_INPUT_BYTES:
        return None, "input_too_large"
    return raw, None


def _exit_for_transcript(code: str, envelope_code: Optional[str]) -> int:
    if envelope_code == "verification_backend_unavailable":
        return EXIT_INTERNAL
    if code == "internal_error":
        return EXIT_INTERNAL
    return EXIT_FAIL


def _exit_for_registry_code(code: str) -> int:
    if code in _REGISTRY_EXIT0_CODES:
        return EXIT_PASS
    if code in _REGISTRY_EXIT4_CODES:
        return EXIT_IDEMPOTENT
    if code in _REGISTRY_EXIT1_CODES:
        return EXIT_FAIL
    if code in _REGISTRY_EXIT2_CODES:
        return EXIT_USAGE
    return EXIT_INTERNAL


def _conformance_body_from_result(
    *,
    result_ok: bool,
    code: str,
    state: Optional[str],
    exchange_id: Optional[str],
    verified_messages: int,
    failed_index: Optional[int],
    envelope_code: Optional[str],
    settlement_transaction_id: Optional[str],
    require_terminal: bool,
    input_mode: str,
    input_size_bytes: int,
    input_sha256: str,
) -> Dict[str, Any]:
    return {
        "report_version": REPORT_VERSION,
        "profile": PROFILE,
        "ok": bool(result_ok),
        "code": code,
        "state": state,
        "exchange_id": exchange_id,
        "verified_messages": int(verified_messages),
        "failed_index": failed_index,
        "envelope_code": envelope_code,
        "settlement_transaction_id": settlement_transaction_id,
        "require_terminal": require_terminal,
        "input_mode": input_mode,
        "input_size_bytes": input_size_bytes,
        "input_sha256": input_sha256,
    }


def _emit_admission_from_conformance_body(
    *,
    conformance_body: Mapping[str, Any],
    ok: bool,
    admitted: bool,
    registry_code: Optional[str],
    newly_recorded: bool,
    new_messages: int,
    exchange_hash: Optional[str],
    transcript_fingerprint: Optional[str],
    head_message_id: Optional[str],
    registry_message_count: Optional[int],
    pretty: bool,
) -> Dict[str, Any]:
    conformance_report_id = compute_report_id(conformance_body)
    report = build_admission_report(
        conformance_body=conformance_body,
        conformance_report_id=conformance_report_id,
        ok=ok,
        admitted=admitted,
        registry_code=registry_code,
        newly_recorded=newly_recorded,
        new_messages=new_messages,
        exchange_hash=exchange_hash,
        transcript_fingerprint=transcript_fingerprint,
        head_message_id=head_message_id,
        registry_message_count=registry_message_count,
    )
    emit_report(report, pretty=pretty)
    return report


def _precheck_create_registry_path(path: str) -> Optional[str]:
    """Return stable registry error code if create-mode precheck fails."""
    try:
        os.lstat(path)
    except FileNotFoundError:
        return None
    except OSError:
        return "registry_io_error"
    return "registry_already_exists"


def _open_replay_registry(path: str, *, create: bool) -> Tuple[Any, Optional[str]]:
    """
    Open or create a replay registry after conformance success.

    Returns (registry, error_code). error_code is a stable registry code on failure.
    """
    if create:
        precheck = _precheck_create_registry_path(path)
        if precheck is not None:
            return None, precheck

    from coin.m2m_replay_registry import ReplayRegistry, ReplayRegistryError

    try:
        registry = ReplayRegistry(path, create=create)
    except ReplayRegistryError as exc:
        return None, exc.code
    except Exception:
        return None, "internal_error"
    return registry, None


def run_conformance(
    *,
    raw: bytes,
    input_mode: str,
    require_terminal: bool,
    pretty: bool,
) -> int:
    input_sha = _sha256_hex(raw)
    size = len(raw)
    try:
        result = verify_transcript_json(raw, require_terminal=require_terminal)
    except Exception:
        report = build_report(
            ok=False,
            code="internal_error",
            state=None,
            exchange_id=None,
            verified_messages=0,
            failed_index=None,
            envelope_code=None,
            settlement_transaction_id=None,
            require_terminal=require_terminal,
            input_mode=input_mode,
            input_size_bytes=size,
            input_sha256=input_sha,
        )
        emit_report(report, pretty=pretty)
        return EXIT_INTERNAL

    report = build_report(
        ok=bool(result.ok),
        code=str(result.code),
        state=result.state,
        exchange_id=result.exchange_id,
        verified_messages=int(result.verified_messages),
        failed_index=result.failed_index,
        envelope_code=result.envelope_code,
        settlement_transaction_id=result.settlement_transaction_id,
        require_terminal=require_terminal,
        input_mode=input_mode,
        input_size_bytes=size,
        input_sha256=input_sha,
    )
    emit_report(report, pretty=pretty)
    if result.ok:
        return EXIT_PASS
    return _exit_for_transcript(result.code, result.envelope_code)


def emit_cli_failure(
    *,
    code: str,
    require_terminal: bool,
    input_mode: Optional[str],
    input_size_bytes: Optional[int],
    input_sha256: Optional[str],
    pretty: bool,
) -> int:
    if code not in CLI_CODES:
        code = "internal_error"
    report = build_report(
        ok=False,
        code=code,
        state=None,
        exchange_id=None,
        verified_messages=0,
        failed_index=None,
        envelope_code=None,
        settlement_transaction_id=None,
        require_terminal=require_terminal,
        input_mode=input_mode,
        input_size_bytes=input_size_bytes,
        input_sha256=input_sha256,
    )
    emit_report(report, pretty=pretty)
    if code == "internal_error":
        return EXIT_INTERNAL
    return EXIT_USAGE


def emit_admission_cli_failure(
    *,
    code: str,
    require_terminal: bool,
    input_mode: Optional[str],
    input_size_bytes: Optional[int],
    input_sha256: Optional[str],
    pretty: bool,
) -> int:
    if code not in CLI_CODES:
        code = "internal_error"
    conformance_body = {
        "report_version": REPORT_VERSION,
        "profile": PROFILE,
        "ok": False,
        "code": code,
        "state": None,
        "exchange_id": None,
        "verified_messages": 0,
        "failed_index": None,
        "envelope_code": None,
        "settlement_transaction_id": None,
        "require_terminal": require_terminal,
        "input_mode": input_mode,
        "input_size_bytes": input_size_bytes,
        "input_sha256": input_sha256,
    }
    _emit_admission_from_conformance_body(
        conformance_body=conformance_body,
        ok=False,
        admitted=False,
        registry_code=None,
        newly_recorded=False,
        new_messages=0,
        exchange_hash=None,
        transcript_fingerprint=None,
        head_message_id=None,
        registry_message_count=None,
        pretty=pretty,
    )
    if code == "internal_error":
        return EXIT_INTERNAL
    return EXIT_USAGE


def run_admission_gate(
    *,
    raw: bytes,
    input_mode: str,
    require_terminal: bool,
    pretty: bool,
    registry_path: str,
    registry_create: bool,
) -> int:
    input_sha = _sha256_hex(raw)
    size = len(raw)

    try:
        result = verify_transcript_json(raw, require_terminal=require_terminal)
    except Exception:
        conformance_body = _conformance_body_from_result(
            result_ok=False,
            code="internal_error",
            state=None,
            exchange_id=None,
            verified_messages=0,
            failed_index=None,
            envelope_code=None,
            settlement_transaction_id=None,
            require_terminal=require_terminal,
            input_mode=input_mode,
            input_size_bytes=size,
            input_sha256=input_sha,
        )
        _emit_admission_from_conformance_body(
            conformance_body=conformance_body,
            ok=False,
            admitted=False,
            registry_code=None,
            newly_recorded=False,
            new_messages=0,
            exchange_hash=None,
            transcript_fingerprint=None,
            head_message_id=None,
            registry_message_count=None,
            pretty=pretty,
        )
        return EXIT_INTERNAL

    conformance_body = _conformance_body_from_result(
        result_ok=bool(result.ok),
        code=str(result.code),
        state=result.state,
        exchange_id=result.exchange_id,
        verified_messages=int(result.verified_messages),
        failed_index=result.failed_index,
        envelope_code=result.envelope_code,
        settlement_transaction_id=result.settlement_transaction_id,
        require_terminal=require_terminal,
        input_mode=input_mode,
        input_size_bytes=size,
        input_sha256=input_sha,
    )

    if not result.ok:
        _emit_admission_from_conformance_body(
            conformance_body=conformance_body,
            ok=False,
            admitted=False,
            registry_code=None,
            newly_recorded=False,
            new_messages=0,
            exchange_hash=None,
            transcript_fingerprint=None,
            head_message_id=None,
            registry_message_count=None,
            pretty=pretty,
        )
        return _exit_for_transcript(result.code, result.envelope_code)

    registry, open_code = _open_replay_registry(registry_path, create=registry_create)
    if open_code is not None:
        _emit_admission_from_conformance_body(
            conformance_body=conformance_body,
            ok=False,
            admitted=False,
            registry_code=open_code,
            newly_recorded=False,
            new_messages=0,
            exchange_hash=None,
            transcript_fingerprint=None,
            head_message_id=None,
            registry_message_count=None,
            pretty=pretty,
        )
        return _exit_for_registry_code(open_code)

    assert registry is not None
    try:
        replay_result = registry.check_and_record_json(raw, require_terminal=require_terminal)
    finally:
        registry.close()

    admitted = bool(replay_result.newly_recorded)
    admission_ok = bool(replay_result.ok)
    report = _emit_admission_from_conformance_body(
        conformance_body=conformance_body,
        ok=admission_ok,
        admitted=admitted,
        registry_code=replay_result.code,
        newly_recorded=bool(replay_result.newly_recorded),
        new_messages=int(replay_result.new_messages),
        exchange_hash=replay_result.exchange_hash,
        transcript_fingerprint=replay_result.transcript_fingerprint,
        head_message_id=replay_result.head_message_id,
        registry_message_count=int(replay_result.message_count),
        pretty=pretty,
    )
    _ = report
    return _exit_for_registry_code(replay_result.code)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m coin.m2m_conformance_cli",
        description="Offline L28 M2M transcript conformance CLI (verify-only).",
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
    reg = parser.add_mutually_exclusive_group(required=False)
    reg.add_argument(
        "--replay-registry",
        metavar="ABSOLUTE_PATH",
        help="Open an existing replay registry at an absolute path outside the repository",
    )
    reg.add_argument(
        "--create-replay-registry",
        metavar="ABSOLUTE_PATH",
        help="Create a new replay registry at an absolute path outside the repository",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse already wrote usage to stderr for -h / bad args.
        code = exc.code
        if code in (0, None):
            return 0
        return EXIT_USAGE

    registry_path: Optional[str] = None
    registry_create = False
    if args.replay_registry is not None:
        registry_path = args.replay_registry
        registry_create = False
    elif args.create_replay_registry is not None:
        registry_path = args.create_replay_registry
        registry_create = True
    registry_mode = registry_path is not None

    if args.version:
        if (
            args.input is not None
            or args.stdin
            or args.require_terminal
            or registry_mode
        ):
            sys.stderr.write(_usage_message())
            return EXIT_USAGE
        sys.stdout.write(CLI_VERSION + "\n")
        return EXIT_PASS

    if bool(args.input) == bool(args.stdin):
        # Neither or both (mutex should prevent both; neither is the main case).
        sys.stderr.write(_usage_message())
        return EXIT_USAGE

    require_terminal = bool(args.require_terminal)
    pretty = bool(args.pretty)

    if not registry_mode:
        if args.stdin:
            raw, err = read_input_stdin()
            if err is not None:
                return emit_cli_failure(
                    code=err,
                    require_terminal=require_terminal,
                    input_mode="stdin",
                    input_size_bytes=None,
                    input_sha256=None,
                    pretty=pretty,
                )
            assert raw is not None
            return run_conformance(
                raw=raw,
                input_mode="stdin",
                require_terminal=require_terminal,
                pretty=pretty,
            )

        # File mode.
        path = args.input
        assert isinstance(path, str)
        raw, err = read_input_file(path)
        if err is not None:
            return emit_cli_failure(
                code=err,
                require_terminal=require_terminal,
                input_mode="file",
                input_size_bytes=None,
                input_sha256=None,
                pretty=pretty,
            )
        assert raw is not None
        return run_conformance(
            raw=raw,
            input_mode="file",
            require_terminal=require_terminal,
            pretty=pretty,
        )

    assert registry_path is not None
    if args.stdin:
        raw, err = read_input_stdin()
        if err is not None:
            return emit_admission_cli_failure(
                code=err,
                require_terminal=require_terminal,
                input_mode="stdin",
                input_size_bytes=None,
                input_sha256=None,
                pretty=pretty,
            )
        assert raw is not None
        return run_admission_gate(
            raw=raw,
            input_mode="stdin",
            require_terminal=require_terminal,
            pretty=pretty,
            registry_path=registry_path,
            registry_create=registry_create,
        )

    path = args.input
    assert isinstance(path, str)
    raw, err = read_input_file(path)
    if err is not None:
        return emit_admission_cli_failure(
            code=err,
            require_terminal=require_terminal,
            input_mode="file",
            input_size_bytes=None,
            input_sha256=None,
            pretty=pretty,
        )
    assert raw is not None
    return run_admission_gate(
        raw=raw,
        input_mode="file",
        require_terminal=require_terminal,
        pretty=pretty,
        registry_path=registry_path,
        registry_create=registry_create,
    )


if __name__ == "__main__":
    raise SystemExit(main())
