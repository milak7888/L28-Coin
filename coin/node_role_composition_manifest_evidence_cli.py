"""Deterministic CLI for offline node-role composition-manifest evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from typing import Any, Sequence, TextIO

from .node_role_composition_manifest_evidence import (
    EVIDENCE_VERSION,
    MAX_EVIDENCE_BYTES,
    STABLE_CODES,
    VERIFIER_VERSION,
    NodeRoleCompositionManifestEvidenceResult,
    verify_node_role_composition_manifest_evidence_json,
)


CLI_VERSION = "l28-node-role-composition-manifest-evidence-cli/v0.1"
REPORT_VERSION = "l28-node-role-composition-manifest-evidence-report/v0.1"
PROFILE = "l28-node-role-composition-manifest-evidence-verification/v0.1"
REPORT_DOMAIN = b"l28-node-role-composition-manifest-evidence-report/v0.1"
EXIT_PASS = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3

CLI_CODES = tuple(STABLE_CODES) + (
    "evidence_file_unavailable",
    "evidence_path_not_regular_file",
    "evidence_path_changed",
    "usage_error",
    "cli_internal_error",
)

REPORT_FIELDS = frozenset(
    {
        "ok",
        "code",
        "detail",
        "profile",
        "report_version",
        "cli_version",
        "evidence_version",
        "manifest_version",
        "source_report_version",
        "verifier_version",
        "evidence_sha256",
        "manifest_sha256",
        "source_report_id",
        "component_ids",
        "roles",
        "trust_boundary_ids",
        "checks",
        "report_id",
    }
)


class _UsageError(ValueError):
    """Raised instead of allowing argparse to emit uncontrolled output."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        del message
        raise _UsageError("invalid command usage")


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_report_id(report: dict[str, Any]) -> str:
    """Compute the domain-separated identifier for a logical CLI report."""

    body = dict(report)
    body.pop("report_id", None)
    return hashlib.sha256(REPORT_DOMAIN + _canonical_json(body)).hexdigest()


def build_report(
    result: NodeRoleCompositionManifestEvidenceResult,
) -> dict[str, Any]:
    """Build the exact deterministic public report."""

    report: dict[str, Any] = {
        "ok": result.ok,
        "code": result.code,
        "detail": result.detail,
        "profile": PROFILE,
        "report_version": REPORT_VERSION,
        "cli_version": CLI_VERSION,
        "evidence_version": result.evidence_version,
        "manifest_version": result.manifest_version,
        "source_report_version": result.report_version,
        "verifier_version": result.verifier_version,
        "evidence_sha256": result.evidence_sha256,
        "manifest_sha256": result.manifest_sha256,
        "source_report_id": result.report_id,
        "component_ids": list(result.component_ids),
        "roles": list(result.roles),
        "trust_boundary_ids": list(result.trust_boundary_ids),
        "checks": list(result.checks),
    }
    report["report_id"] = compute_report_id(report)
    if frozenset(report) != REPORT_FIELDS:
        raise RuntimeError("internal report schema mismatch")
    return report


def emit_report(
    report: dict[str, Any],
    pretty: bool = False,
    stream: TextIO | None = None,
) -> None:
    """Emit exactly one deterministic JSON report."""

    destination = sys.stdout if stream is None else stream
    if pretty:
        text = json.dumps(
            report,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
    else:
        text = _canonical_json(report).decode("utf-8")
    destination.write(text)
    destination.write("\n")


def _failure(
    code: str, detail: str
) -> NodeRoleCompositionManifestEvidenceResult:
    return NodeRoleCompositionManifestEvidenceResult(
        ok=False,
        code=code,
        evidence_sha256="",
        manifest_sha256="",
        report_id="",
        component_ids=(),
        roles=(),
        trust_boundary_ids=(),
        checks=(),
        detail=detail,
    )


def _same_file(before: os.stat_result, after: os.stat_result) -> bool:
    return before.st_dev == after.st_dev and before.st_ino == after.st_ino


def verify_evidence_path(path_value: str) -> NodeRoleCompositionManifestEvidenceResult:
    """Verify one explicit regular-file evidence path without discovery or mutation."""

    if not isinstance(path_value, str) or not path_value:
        return _failure("evidence_file_unavailable", "evidence file is unavailable")

    try:
        before = os.lstat(path_value)
    except OSError:
        return _failure("evidence_file_unavailable", "evidence file is unavailable")

    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        return _failure(
            "evidence_path_not_regular_file",
            "evidence path must identify a regular file",
        )
    if before.st_size > MAX_EVIDENCE_BYTES:
        return _failure("evidence_too_large", "input_exceeds_maximum")

    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    try:
        descriptor = os.open(path_value, flags)
    except OSError:
        return _failure("evidence_file_unavailable", "evidence file is unavailable")

    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            return _failure(
                "evidence_path_not_regular_file",
                "evidence path must identify a regular file",
            )
        if not _same_file(before, opened):
            return _failure("evidence_path_changed", "evidence path changed during read")
        if opened.st_size > MAX_EVIDENCE_BYTES:
            return _failure("evidence_too_large", "input_exceeds_maximum")

        chunks: list[bytes] = []
        remaining = MAX_EVIDENCE_BYTES + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)

        payload = b"".join(chunks)
        if len(payload) > MAX_EVIDENCE_BYTES:
            return _failure("evidence_too_large", "input_exceeds_maximum")

        finished = os.fstat(descriptor)
        if not _same_file(opened, finished) or opened.st_size != finished.st_size:
            return _failure("evidence_path_changed", "evidence changed during read")
    except OSError:
        return _failure("evidence_file_unavailable", "evidence file is unavailable")
    finally:
        os.close(descriptor)

    return verify_node_role_composition_manifest_evidence_json(payload)


def _parser() -> _Parser:
    parser = _Parser(
        add_help=True,
        prog="l28-node-role-composition-manifest-evidence",
    )
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--pretty", action="store_true")
    return parser


def _exit_for(result: NodeRoleCompositionManifestEvidenceResult) -> int:
    if result.ok:
        return EXIT_PASS
    if result.code in {"internal_error", "cli_internal_error"}:
        return EXIT_INTERNAL
    if result.code == "usage_error":
        return EXIT_USAGE
    return EXIT_FAILURE


def main(argv: Sequence[str] | None = None) -> int:
    """Run the deterministic explicit-path evidence CLI."""

    pretty = False
    try:
        arguments = _parser().parse_args(argv)
        pretty = bool(arguments.pretty)
        result = verify_evidence_path(arguments.evidence)
    except _UsageError:
        result = _failure("usage_error", "invalid command usage")
    except SystemExit as exc:
        if exc.code == 0:
            return EXIT_PASS
        result = _failure("usage_error", "invalid command usage")
    except Exception:
        result = _failure("cli_internal_error", "internal command failure")

    try:
        emit_report(build_report(result), pretty=pretty)
    except Exception:
        fallback = _failure("cli_internal_error", "internal command failure")
        emit_report(build_report(fallback), pretty=False)
        return EXIT_INTERNAL

    return _exit_for(result)


if __name__ == "__main__":
    raise SystemExit(main())
