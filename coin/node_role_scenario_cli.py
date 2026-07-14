"""Deterministic CLI for offline inert L28 node-role scenarios."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
import stat
import sys
from typing import Any, Mapping, Sequence

from .node_role_scenario import (
    MAX_SCENARIO_BYTES,
    MODEL_VERSION,
    RUNNER_VERSION,
    SCENARIO_VERSION,
    TRANSCRIPT_VERSION,
    NodeRoleScenarioResult,
    run_scenario_json,
)


CLI_VERSION = "l28-node-role-scenario-cli/v0.1"
PROFILE = "l28-node-role-scenario-execution/v0.1"
REPORT_VERSION = "l28-node-role-scenario-report/v0.1"
REPORT_DOMAIN = b"l28-node-role-scenario-report/v0.1"

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
        "scenario_version",
        "model_version",
        "transcript_version",
        "runner_version",
        "role",
        "final_state",
        "request_count",
        "scenario_sha256",
        "transcript_sha256",
        "transcript_verification_code",
        "transcript",
        "steps",
        "checks",
        "report_id",
    }
)


class _UsageError(ValueError):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _UsageError(message)


def _empty_result(code: str) -> NodeRoleScenarioResult:
    return NodeRoleScenarioResult(
        ok=False,
        code=code,
        role="",
        final_state="",
        request_count=0,
        scenario_sha256="",
        transcript_sha256="",
        transcript_verification_code="",
        transcript_json="",
        steps=(),
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


def build_report(result: NodeRoleScenarioResult) -> dict[str, Any]:
    parsed_transcript: Any = None
    if result.transcript_json:
        parsed_transcript = json.loads(result.transcript_json)

    report: dict[str, Any] = {
        "ok": result.ok,
        "code": result.code,
        "detail": result.detail,
        "profile": PROFILE,
        "report_version": REPORT_VERSION,
        "cli_version": CLI_VERSION,
        "scenario_version": result.scenario_version,
        "model_version": result.model_version,
        "transcript_version": result.transcript_version,
        "runner_version": result.runner_version,
        "role": result.role,
        "final_state": result.final_state,
        "request_count": result.request_count,
        "scenario_sha256": result.scenario_sha256,
        "transcript_sha256": result.transcript_sha256,
        "transcript_verification_code": result.transcript_verification_code,
        "transcript": parsed_transcript,
        "steps": [asdict(step) for step in result.steps],
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


def run_scenario_path(path_value: str) -> NodeRoleScenarioResult:
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
        if metadata.st_size > MAX_SCENARIO_BYTES:
            return _empty_result("scenario_too_large")

        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = -1
            payload = handle.read(MAX_SCENARIO_BYTES + 1)
    except (OSError, TypeError, ValueError):
        return _empty_result("path_invalid")
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass

    return run_scenario_json(payload)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="python3 -m coin.node_role_scenario_cli",
        description=(
            "Run one explicitly supplied inert L28 node-role scenario."
        ),
    )
    parser.add_argument(
        "--scenario",
        required=True,
        help="Explicit path to the scenario JSON file.",
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
        result = run_scenario_path(arguments.scenario)
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
