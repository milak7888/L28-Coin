"""Deterministic CLI for the offline L28 node-role scenario-suite verifier."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
import stat
import sys
from typing import Any, Sequence

try:
    from .node_role_scenario_suite import (
        MAX_SUITE_BYTES,
        STABLE_CODES,
        NodeRoleScenarioSuiteResult,
        verify_scenario_suite_json,
    )
except ImportError:  # pragma: no cover - direct module execution compatibility
    from node_role_scenario_suite import (
        MAX_SUITE_BYTES,
        STABLE_CODES,
        NodeRoleScenarioSuiteResult,
        verify_scenario_suite_json,
    )


CLI_VERSION = "l28-node-role-scenario-suite-cli/v0.1"
PROFILE = "l28-node-role-scenario-suite-verification/v0.1"
REPORT_VERSION = "l28-node-role-scenario-suite-report/v0.1"
REPORT_DOMAIN = b"l28-node-role-scenario-suite-report/v0.1"
EXIT_PASS = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3
CLI_CODES = tuple(STABLE_CODES) + ("usage_error", "cli_internal_error")
REPORT_FIELDS = frozenset(
    {
        "ok",
        "code",
        "detail",
        "profile",
        "report_version",
        "cli_version",
        "suite_version",
        "scenario_version",
        "model_version",
        "transcript_version",
        "verifier_version",
        "case_count",
        "roles",
        "suite_sha256",
        "core_covered_transitions",
        "core_missing_transitions",
        "p2p_covered_transitions",
        "p2p_missing_transitions",
        "core_reserved_rejections",
        "core_missing_reserved_rejections",
        "p2p_reserved_rejections",
        "p2p_missing_reserved_rejections",
        "cases",
        "checks",
        "report_id",
    }
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_report_id(report: dict[str, Any]) -> str:
    body = {key: value for key, value in report.items() if key != "report_id"}
    return hashlib.sha256(REPORT_DOMAIN + _canonical_bytes(body)).hexdigest()


def build_report(result: NodeRoleScenarioSuiteResult) -> dict[str, Any]:
    report: dict[str, Any] = {
        "ok": result.ok,
        "code": result.code,
        "detail": result.detail,
        "profile": PROFILE,
        "report_version": REPORT_VERSION,
        "cli_version": CLI_VERSION,
        "suite_version": result.suite_version,
        "scenario_version": result.scenario_version,
        "model_version": result.model_version,
        "transcript_version": result.transcript_version,
        "verifier_version": result.verifier_version,
        "case_count": result.case_count,
        "roles": list(result.roles),
        "suite_sha256": result.suite_sha256,
        "core_covered_transitions": list(result.core_covered_transitions),
        "core_missing_transitions": list(result.core_missing_transitions),
        "p2p_covered_transitions": list(result.p2p_covered_transitions),
        "p2p_missing_transitions": list(result.p2p_missing_transitions),
        "core_reserved_rejections": list(result.core_reserved_rejections),
        "core_missing_reserved_rejections": list(
            result.core_missing_reserved_rejections
        ),
        "p2p_reserved_rejections": list(result.p2p_reserved_rejections),
        "p2p_missing_reserved_rejections": list(
            result.p2p_missing_reserved_rejections
        ),
        "cases": [asdict(case) for case in result.cases],
        "checks": list(result.checks),
    }
    report["report_id"] = compute_report_id(report)
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


def _failure_result(code: str, detail: str) -> NodeRoleScenarioSuiteResult:
    return NodeRoleScenarioSuiteResult(
        ok=False,
        code=code,
        case_count=0,
        roles=(),
        suite_sha256="",
        core_covered_transitions=(),
        core_missing_transitions=(),
        p2p_covered_transitions=(),
        p2p_missing_transitions=(),
        core_reserved_rejections=(),
        core_missing_reserved_rejections=(),
        p2p_reserved_rejections=(),
        p2p_missing_reserved_rejections=(),
        cases=(),
        checks=(),
        detail=detail,
    )


def _read_explicit_regular_file(path_value: str) -> bytes:
    try:
        before = os.lstat(path_value)
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError("suite_file_unavailable") from exc

    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ValueError("suite_path_not_regular_file")
    if before.st_size > MAX_SUITE_BYTES:
        raise OverflowError("suite_file_too_large")

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    try:
        descriptor = os.open(path_value, flags)
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError("suite_file_unavailable") from exc

    try:
        after = os.fstat(descriptor)
        if (
            not stat.S_ISREG(after.st_mode)
            or after.st_dev != before.st_dev
            or after.st_ino != before.st_ino
        ):
            raise ValueError("suite_path_changed")
        if after.st_size > MAX_SUITE_BYTES:
            raise OverflowError("suite_file_too_large")

        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65_536, MAX_SUITE_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_SUITE_BYTES:
                raise OverflowError("suite_file_too_large")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def verify_suite_path(path_value: str) -> NodeRoleScenarioSuiteResult:
    try:
        payload = _read_explicit_regular_file(path_value)
    except OverflowError:
        return _failure_result("suite_too_large", "suite_file_too_large")
    except ValueError as exc:
        detail = str(exc)
        if detail not in {
            "suite_file_unavailable",
            "suite_path_not_regular_file",
            "suite_path_changed",
        }:
            detail = "suite_file_unavailable"
        return _failure_result("invalid_json", detail)
    except Exception:
        return _failure_result("internal_error", "internal_failure")

    return verify_scenario_suite_json(payload)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="l28-node-role-scenario-suite",
        description="Verify an explicit offline L28 node-role scenario suite.",
    )
    parser.add_argument(
        "--suite",
        required=True,
        help="Explicit path to the scenario-suite JSON file.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the deterministic JSON report.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        try:
            args = _parser().parse_args(argv)
        except SystemExit as exc:
            return EXIT_USAGE if int(exc.code or 0) != 0 else EXIT_PASS

        result = verify_suite_path(args.suite)
        emit_report(build_report(result), args.pretty)

        if result.ok:
            return EXIT_PASS
        if result.code == "internal_error":
            return EXIT_INTERNAL
        return EXIT_FAILURE

    except Exception:
        result = _failure_result("cli_internal_error", "internal_failure")
        try:
            emit_report(build_report(result), False)
        except Exception:
            pass
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
