"""Deterministic CLI for offline L28 node-role transcript verification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from typing import Any, Mapping, Sequence

from .node_role_transcript import (
    MAX_TRANSCRIPT_BYTES,
    MODEL_VERSION,
    TRANSCRIPT_VERSION,
    VERIFIER_VERSION,
    NodeRoleTranscriptResult,
    verify_transcript_json,
)


CLI_VERSION = "l28-node-role-transcript-cli/v0.1"
PROFILE = "l28-node-role-transcript-verification/v0.1"
REPORT_VERSION = "l28-node-role-transcript-report/v0.1"
REPORT_DOMAIN = b"l28-node-role-transcript-report/v0.1"

EXIT_PASS = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3

REPORT_FIELDS = frozenset(
    {
        "ok",
        "code",
        "detail",
        "profile",
        "report_version",
        "cli_version",
        "transcript_version",
        "model_version",
        "verifier_version",
        "role",
        "initial_state",
        "final_state",
        "transition_count",
        "transcript_sha256",
        "checks",
        "report_id",
    }
)


class _UsageError(ValueError):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _UsageError(message)


def _empty_result(code: str) -> NodeRoleTranscriptResult:
    return NodeRoleTranscriptResult(
        ok=False,
        code=code,
        role="",
        initial_state="",
        final_state="",
        transition_count=0,
        transcript_sha256="",
        checks=(),
        detail="",
    )


def _canonical_report_bytes(report: Mapping[str, Any]) -> bytes:
    body = {
        key: value
        for key, value in report.items()
        if key != "report_id"
    }
    return json.dumps(
        body,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def compute_report_id(report: Mapping[str, Any]) -> str:
    preimage = REPORT_DOMAIN + b"\x00" + _canonical_report_bytes(report)
    return hashlib.sha256(preimage).hexdigest()


def build_report(result: NodeRoleTranscriptResult) -> dict[str, Any]:
    report: dict[str, Any] = {
        "ok": result.ok,
        "code": result.code,
        "detail": result.detail,
        "profile": PROFILE,
        "report_version": REPORT_VERSION,
        "cli_version": CLI_VERSION,
        "transcript_version": result.transcript_version,
        "model_version": result.model_version,
        "verifier_version": result.verifier_version,
        "role": result.role,
        "initial_state": result.initial_state,
        "final_state": result.final_state,
        "transition_count": result.transition_count,
        "transcript_sha256": result.transcript_sha256,
        "checks": list(result.checks),
    }
    report["report_id"] = compute_report_id(report)
    return report


def emit_report(report: Mapping[str, Any], *, pretty: bool = False) -> None:
    if pretty:
        output = json.dumps(
            report,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
    else:
        output = json.dumps(
            report,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    sys.stdout.write(output)
    sys.stdout.write("\n")


def verify_transcript_path(path_value: str) -> NodeRoleTranscriptResult:
    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0)

    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if nofollow:
        flags |= nofollow
    elif os.path.islink(path_value):
        return _empty_result("path_invalid")

    try:
        descriptor = os.open(path_value, flags)
    except (OSError, TypeError, ValueError):
        return _empty_result("path_invalid")

    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            return _empty_result("path_invalid")
        if metadata.st_size > MAX_TRANSCRIPT_BYTES:
            return _empty_result("transcript_too_large")

        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = -1
            payload = handle.read(MAX_TRANSCRIPT_BYTES + 1)
    except (OSError, TypeError, ValueError):
        return _empty_result("path_invalid")
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass

    return verify_transcript_json(payload)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="python3 -m coin.node_role_transcript_cli",
        description=(
            "Verify one explicitly supplied inert L28 node-role transcript."
        ),
    )
    parser.add_argument(
        "--transcript",
        required=True,
        help="Explicit path to the transcript JSON file.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the deterministic JSON report.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _build_parser().parse_args(argv)
    except _UsageError:
        emit_report(build_report(_empty_result("usage_error")))
        return EXIT_USAGE

    try:
        result = verify_transcript_path(arguments.transcript)
        report = build_report(result)
        emit_report(report, pretty=arguments.pretty)
    except Exception:
        emit_report(build_report(_empty_result("internal_error")))
        return EXIT_INTERNAL

    if result.ok:
        return EXIT_PASS
    if result.code == "internal_error":
        return EXIT_INTERNAL
    return EXIT_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())
