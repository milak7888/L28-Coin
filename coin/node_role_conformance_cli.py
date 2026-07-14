"""Deterministic CLI for offline L28 Core/P2P role conformance."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Any, Sequence, TextIO

from .node_role_conformance import (
    NodeRoleConformanceResult,
    STABLE_CODES,
    verify_node_role_profile,
)


CLI_VERSION = "l28-node-role-conformance-cli/v0.1"
REPORT_VERSION = "l28-node-role-conformance-report/v0.1"
PROFILE = "l28-node-role-conformance/v0.1"
REPORT_DOMAIN = b"L28:NODE-ROLE-CONFORMANCE:REPORT:V0.1\x00"

EXIT_PASS = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3

CLI_CODES = tuple(STABLE_CODES) + (
    "usage_error",
    "cli_internal_error",
)


class _UsageError(ValueError):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _UsageError("invalid_arguments")


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="python3 -m coin.node_role_conformance_cli",
        description="Verify an explicitly supplied L28 Core/P2P security profile offline.",
    )
    parser.add_argument(
        "--profile",
        required=True,
        help="Explicit path to the public Core/P2P security profile.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Indent deterministic JSON output.",
    )
    return parser


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_report_id(report_without_id: dict[str, Any]) -> str:
    """Return the domain-separated identifier for a logical report body."""

    return hashlib.sha256(REPORT_DOMAIN + _canonical_bytes(report_without_id)).hexdigest()


def build_report(result: NodeRoleConformanceResult) -> dict[str, Any]:
    """Build a deterministic, content-bound report from a verifier result."""

    body: dict[str, Any] = {
        "checks": list(result.checks),
        "cli_version": CLI_VERSION,
        "code": result.code,
        "detail": result.detail,
        "ok": result.ok,
        "profile": PROFILE,
        "profile_sha256": result.profile_sha256,
        "profile_version": result.profile_version,
        "report_version": REPORT_VERSION,
    }
    return {**body, "report_id": compute_report_id(body)}


def _failure_result(code: str, detail: str) -> NodeRoleConformanceResult:
    return NodeRoleConformanceResult(False, code, detail, "", "", ())


def emit_report(
    report: dict[str, Any],
    *,
    pretty: bool = False,
    stream: TextIO | None = None,
) -> None:
    """Emit one JSON report and a trailing newline."""

    output = stream if stream is not None else sys.stdout
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
    output.write(rendered)
    output.write("\n")


def _exit_for(result: NodeRoleConformanceResult) -> int:
    if result.ok:
        return EXIT_PASS
    if result.code in {"internal_error", "cli_internal_error"}:
        return EXIT_INTERNAL
    if result.code == "usage_error":
        return EXIT_USAGE
    return EXIT_FAILURE


def main(argv: Sequence[str] | None = None) -> int:
    """Run the offline verifier CLI and return a stable process exit code."""

    pretty = False
    try:
        arguments = _parser().parse_args(argv)
        pretty = bool(arguments.pretty)
    except _UsageError:
        result = _failure_result("usage_error", "arguments:invalid")
        emit_report(build_report(result))
        return EXIT_USAGE
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else EXIT_USAGE

    try:
        result = verify_node_role_profile(arguments.profile)
    except Exception:
        result = _failure_result("cli_internal_error", "cli:internal_error")

    emit_report(build_report(result), pretty=pretty)
    return _exit_for(result)


if __name__ == "__main__":
    raise SystemExit(main())
