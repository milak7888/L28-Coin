"""Deterministic CLI for offline node-role scenario-suite evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from typing import Any

from .node_role_scenario_suite_evidence import (
    EVIDENCE_VERSION,
    MAX_EVIDENCE_BYTES,
    STABLE_CODES,
    VERIFIER_VERSION,
    NodeRoleScenarioSuiteEvidenceResult,
    verify_scenario_suite_evidence_json,
)


PROFILE = "l28-node-role-scenario-suite-evidence-verification/v0.1"
REPORT_VERSION = "l28-node-role-scenario-suite-evidence-report/v0.1"
CLI_VERSION = "l28-node-role-scenario-suite-evidence-cli/v0.1"
REPORT_DOMAIN = b"l28-node-role-scenario-suite-evidence-report/v0.1"

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

REPORT_FIELDS = frozenset({
    "ok",
    "code",
    "detail",
    "profile",
    "report_version",
    "cli_version",
    "evidence_version",
    "suite_version",
    "source_report_version",
    "verifier_version",
    "evidence_sha256",
    "suite_sha256",
    "source_report_id",
    "case_count",
    "roles",
    "core_transition_count",
    "p2p_transition_count",
    "core_reserved_rejection_count",
    "p2p_reserved_rejection_count",
    "checks",
    "report_id",
})


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_report_id(report: dict[str, Any]) -> str:
    body = dict(report)
    body.pop("report_id", None)
    return hashlib.sha256(REPORT_DOMAIN + b"\x00" + _canonical_bytes(body)).hexdigest()


def build_report(result: NodeRoleScenarioSuiteEvidenceResult) -> dict[str, Any]:
    report: dict[str, Any] = {
        "ok": result.ok,
        "code": result.code,
        "detail": result.detail,
        "profile": PROFILE,
        "report_version": REPORT_VERSION,
        "cli_version": CLI_VERSION,
        "evidence_version": result.evidence_version,
        "suite_version": result.suite_version,
        "source_report_version": result.report_version,
        "verifier_version": result.verifier_version,
        "evidence_sha256": result.evidence_sha256,
        "suite_sha256": result.suite_sha256,
        "source_report_id": result.report_id,
        "case_count": result.case_count,
        "roles": list(result.roles),
        "core_transition_count": result.core_transition_count,
        "p2p_transition_count": result.p2p_transition_count,
        "core_reserved_rejection_count": result.core_reserved_rejection_count,
        "p2p_reserved_rejection_count": result.p2p_reserved_rejection_count,
        "checks": list(result.checks),
    }
    report["report_id"] = compute_report_id(report)
    if frozenset(report) != REPORT_FIELDS:
        raise RuntimeError("report field mismatch")
    return report


def emit_report(report: dict[str, Any], pretty: bool) -> None:
    if pretty:
        rendered = json.dumps(
            report,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        )
    else:
        rendered = _canonical_bytes(report).decode("utf-8")
    sys.stdout.write(rendered + "\n")


def _failure_result(code: str, detail: str) -> NodeRoleScenarioSuiteEvidenceResult:
    return NodeRoleScenarioSuiteEvidenceResult(
        ok=False,
        code=code,
        evidence_sha256="",
        suite_sha256="",
        report_id="",
        case_count=0,
        roles=(),
        core_transition_count=0,
        p2p_transition_count=0,
        core_reserved_rejection_count=0,
        p2p_reserved_rejection_count=0,
        checks=(),
        detail=detail,
    )


def _read_explicit_regular_file(path_value: str) -> bytes:
    try:
        before = os.lstat(path_value)
    except OSError:
        raise ValueError("evidence_file_unavailable") from None

    if not stat.S_ISREG(before.st_mode):
        raise ValueError("evidence_path_not_regular_file")
    if before.st_size > MAX_EVIDENCE_BYTES:
        raise ValueError("evidence_too_large")

    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    try:
        descriptor = os.open(path_value, flags)
    except OSError:
        raise ValueError("evidence_file_unavailable") from None

    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError("evidence_path_not_regular_file")
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError("evidence_path_changed")
        if opened.st_size > MAX_EVIDENCE_BYTES:
            raise ValueError("evidence_too_large")

        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65536, MAX_EVIDENCE_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_EVIDENCE_BYTES:
                raise ValueError("evidence_too_large")
        payload = b"".join(chunks)
    finally:
        os.close(descriptor)

    try:
        after = os.lstat(path_value)
    except OSError:
        raise ValueError("evidence_path_changed") from None
    if (after.st_dev, after.st_ino) != (opened.st_dev, opened.st_ino):
        raise ValueError("evidence_path_changed")
    return payload


def verify_evidence_path(path_value: str) -> NodeRoleScenarioSuiteEvidenceResult:
    try:
        payload = _read_explicit_regular_file(path_value)
    except ValueError as exc:
        code = str(exc)
        if code not in CLI_CODES:
            return _failure_result("internal_error", "internal_failure")
        detail_by_code = {
            "evidence_file_unavailable": "evidence_file_unavailable",
            "evidence_path_not_regular_file": "evidence_path_not_regular_file",
            "evidence_path_changed": "evidence_path_changed",
            "evidence_too_large": "input_exceeds_maximum",
        }
        return _failure_result(code, detail_by_code[code])
    except Exception:
        return _failure_result("internal_error", "internal_failure")

    return verify_scenario_suite_evidence_json(payload)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="l28-node-role-scenario-suite-evidence",
        description="Verify explicit offline L28 scenario-suite evidence.",
    )
    parser.add_argument(
        "--evidence",
        required=True,
        help="Explicit path to the scenario-suite evidence JSON file.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the deterministic JSON report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        result = verify_evidence_path(args.evidence)
        report = build_report(result)
        emit_report(report, args.pretty)
    except Exception:
        result = _failure_result("cli_internal_error", "internal_failure")
        report = build_report(result)
        emit_report(report, False)
        return EXIT_INTERNAL

    if result.ok:
        return EXIT_PASS
    if result.code in {"internal_error", "cli_internal_error"}:
        return EXIT_INTERNAL
    return EXIT_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CLI_CODES",
    "CLI_VERSION",
    "EXIT_FAILURE",
    "EXIT_INTERNAL",
    "EXIT_PASS",
    "EXIT_USAGE",
    "PROFILE",
    "REPORT_FIELDS",
    "REPORT_VERSION",
    "build_report",
    "compute_report_id",
    "emit_report",
    "main",
    "verify_evidence_path",
]
