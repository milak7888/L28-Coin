# SPDX-License-Identifier: Apache-2.0
"""
L28 M2M offline conformance CLI (Foundation 7).

Reads one explicitly selected local transcript (file or stdin), runs the
Foundation 6 transcript validator, and emits exactly one deterministic JSON
report to stdout.

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
MAX_INPUT_BYTES = 1_048_576

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3

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


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_report_id(body_without_id: Mapping[str, Any]) -> str:
    """
    Deterministic report integrity identifier.

    report_id = SHA-256(L28-M2M-V0.1-REPORT\\x00 || Canon(report body without report_id))
    Not a signature, attestation, settlement proof, or trust claim.
    """
    return _sha256_hex(DOMAIN_REPORT + canonical_bytes(dict(body_without_id)))


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


def emit_report(report: Mapping[str, Any], *, pretty: bool) -> None:
    if pretty:
        text = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False)
    else:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    sys.stdout.write(text + "\n")


def _usage_message() -> str:
    return (
        "usage: python -m coin.m2m_conformance_cli "
        "(--input PATH | --stdin) [--require-terminal] [--pretty] | --version\n"
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

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse already wrote usage to stderr for -h / bad args.
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
        # Neither or both (mutex should prevent both; neither is the main case).
        sys.stderr.write(_usage_message())
        return EXIT_USAGE

    require_terminal = bool(args.require_terminal)
    pretty = bool(args.pretty)

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


if __name__ == "__main__":
    raise SystemExit(main())
