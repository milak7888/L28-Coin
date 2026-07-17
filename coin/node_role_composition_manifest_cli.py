"""Deterministic CLI for offline node-role composition manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from typing import Any, Sequence, TextIO

from .node_role_composition_manifest import (
    MAX_MANIFEST_BYTES,
    MANIFEST_VERSION,
    NodeRoleCompositionManifestResult,
    SECURITY_PROFILE_VERSION,
    STABLE_CODES,
    verify_node_role_composition_manifest_json,
)


CLI_VERSION = "l28-node-role-composition-manifest-cli/v0.1"
REPORT_VERSION = "l28-node-role-composition-manifest-report/v0.1"
PROFILE = "l28-node-role-composition-manifest-verification/v0.1"
REPORT_DOMAIN = b"l28-node-role-composition-manifest-report/v0.1"
EXIT_PASS = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3
CLI_CODES = tuple(STABLE_CODES) + (
    "manifest_file_unavailable",
    "manifest_path_not_regular_file",
    "manifest_path_changed",
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
        "manifest_version",
        "security_profile_version",
        "evidence_version",
        "evidence_report_version",
        "verifier_version",
        "manifest_sha256",
        "security_profile_sha256",
        "evidence_sha256",
        "evidence_report_id",
        "component_ids",
        "roles",
        "trust_boundary_ids",
        "checks",
        "report_id",
    }
)


class _UsageError(ValueError):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _UsageError(message)


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_report_id(report: dict[str, Any]) -> str:
    """Compute the domain-separated identifier for a logical report."""

    body = dict(report)
    body.pop("report_id", None)
    return hashlib.sha256(REPORT_DOMAIN + _canonical_json(body)).hexdigest()


def build_report(result: NodeRoleCompositionManifestResult) -> dict[str, Any]:
    """Build the exact deterministic public report for a verification result."""

    report: dict[str, Any] = {
        "ok": result.ok,
        "code": result.code,
        "detail": result.detail,
        "profile": PROFILE,
        "report_version": REPORT_VERSION,
        "cli_version": CLI_VERSION,
        "manifest_version": result.manifest_version,
        "security_profile_version": result.security_profile_version,
        "evidence_version": result.evidence_version,
        "evidence_report_version": result.evidence_report_version,
        "verifier_version": result.verifier_version,
        "manifest_sha256": result.manifest_sha256,
        "security_profile_sha256": result.security_profile_sha256,
        "evidence_sha256": result.evidence_sha256,
        "evidence_report_id": result.evidence_report_id,
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
    """Emit exactly one JSON report."""

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


def _failure(code: str, detail: str) -> NodeRoleCompositionManifestResult:
    return NodeRoleCompositionManifestResult(
        ok=False,
        code=code,
        manifest_sha256="",
        security_profile_sha256="",
        evidence_sha256="",
        evidence_report_id="",
        component_ids=(),
        roles=(),
        trust_boundary_ids=(),
        checks=(),
        detail=detail,
    )


def _same_file(before: os.stat_result, after: os.stat_result) -> bool:
    return before.st_dev == after.st_dev and before.st_ino == after.st_ino


def verify_manifest_path(path_value: str) -> NodeRoleCompositionManifestResult:
    """Verify one explicit regular-file path without discovery or mutation."""

    if not isinstance(path_value, str) or not path_value:
        return _failure("manifest_file_unavailable", "manifest file is unavailable")
    try:
        before = os.lstat(path_value)
    except OSError:
        return _failure("manifest_file_unavailable", "manifest file is unavailable")
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        return _failure(
            "manifest_path_not_regular_file",
            "manifest path must identify a regular file",
        )
    if before.st_size > MAX_MANIFEST_BYTES:
        return _failure("manifest_too_large", "manifest exceeds size limit")

    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path_value, flags)
    except OSError:
        return _failure("manifest_file_unavailable", "manifest file is unavailable")
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            return _failure(
                "manifest_path_not_regular_file",
                "manifest path must identify a regular file",
            )
        if not _same_file(before, opened):
            return _failure("manifest_path_changed", "manifest path changed during read")
        if opened.st_size > MAX_MANIFEST_BYTES:
            return _failure("manifest_too_large", "manifest exceeds size limit")

        chunks: list[bytes] = []
        remaining = MAX_MANIFEST_BYTES + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) > MAX_MANIFEST_BYTES:
            return _failure("manifest_too_large", "manifest exceeds size limit")
        finished = os.fstat(descriptor)
        if not _same_file(opened, finished) or opened.st_size != finished.st_size:
            return _failure("manifest_path_changed", "manifest changed during read")
    except OSError:
        return _failure("manifest_file_unavailable", "manifest file is unavailable")
    finally:
        os.close(descriptor)
    return verify_node_role_composition_manifest_json(payload)


def _parser() -> _Parser:
    parser = _Parser(add_help=True, prog="l28-node-role-composition-manifest")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--pretty", action="store_true")
    return parser


def _exit_for(result: NodeRoleCompositionManifestResult) -> int:
    if result.ok:
        return EXIT_PASS
    if result.code in {"internal_error", "cli_internal_error"}:
        return EXIT_INTERNAL
    if result.code == "usage_error":
        return EXIT_USAGE
    return EXIT_FAILURE


def main(argv: Sequence[str] | None = None) -> int:
    """Run the deterministic explicit-path CLI."""

    pretty = False
    try:
        arguments = _parser().parse_args(argv)
        pretty = bool(arguments.pretty)
        result = verify_manifest_path(arguments.manifest)
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
