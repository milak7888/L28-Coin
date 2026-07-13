# SPDX-License-Identifier: Apache-2.0
"""
L28 M2M offline replay-registry audit CLI (Foundation 10).

Strictly read-only inspection of an existing Foundation 8 replay registry with
one deterministic JSON audit report on stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Any, Dict, Mapping, Optional

from coin.m2m_registry_audit import RegistryAuditResult, STABLE_CODES, audit_registry
from coin.m2m_verifier import canonical_bytes

CLI_VERSION = "l28-m2m-registry-audit-cli/v0.1"
REPORT_VERSION = "l28-m2m-registry-audit-report/v0.1"
PROFILE = "l28-m2m-replay-registry-audit/v0.1"
DOMAIN_REPORT = b"L28-M2M-V0.1-REGISTRY-AUDIT-REPORT\x00"

EXIT_PASS = 0
EXIT_USAGE = 2
EXIT_FAILURE = 3

REPORT_FIELD_ORDER = (
    "report_version",
    "profile",
    "ok",
    "code",
    "schema_version",
    "exchange_count",
    "message_count",
    "terminal_exchange_count",
    "nonterminal_exchange_count",
    "logical_registry_digest",
    "failed_check",
    "report_id",
)

_EXIT_USAGE_CODES = frozenset(
    {
        "invalid_registry_path",
        "registry_not_found",
        "unsafe_registry_path",
    }
)


def compute_report_id(body_without_id: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        DOMAIN_REPORT + canonical_bytes(dict(body_without_id))
    ).hexdigest()


def build_report(result: RegistryAuditResult) -> Dict[str, Any]:
    body = {
        "report_version": REPORT_VERSION,
        "profile": PROFILE,
        "ok": bool(result.ok),
        "code": result.code,
        "schema_version": result.schema_version,
        "exchange_count": int(result.exchange_count),
        "message_count": int(result.message_count),
        "terminal_exchange_count": int(result.terminal_exchange_count),
        "nonterminal_exchange_count": int(result.nonterminal_exchange_count),
        "logical_registry_digest": result.logical_registry_digest,
        "failed_check": result.failed_check,
    }
    report = dict(body)
    report["report_id"] = compute_report_id(body)
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


def _exit_for_code(code: str) -> int:
    if code == "registry_healthy":
        return EXIT_PASS
    if code in _EXIT_USAGE_CODES:
        return EXIT_USAGE
    return EXIT_FAILURE


def _usage_message() -> str:
    return (
        "usage: python -m coin.m2m_registry_audit_cli "
        "--registry ABSOLUTE_PATH [--pretty] | --version\n"
    )


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m coin.m2m_registry_audit_cli",
        description="Offline read-only L28 M2M replay registry audit CLI.",
        add_help=True,
    )
    parser.add_argument(
        "--registry",
        metavar="ABSOLUTE_PATH",
        help="Audit an existing replay registry at an absolute path outside the repository",
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
        if args.registry is not None or args.pretty:
            sys.stderr.write(_usage_message())
            return EXIT_USAGE
        sys.stdout.write(CLI_VERSION + "\n")
        return EXIT_PASS

    if not args.registry:
        sys.stderr.write(_usage_message())
        return EXIT_USAGE

    result = audit_registry(args.registry)
    if result.code not in STABLE_CODES:
        result = RegistryAuditResult(
            ok=False,
            code="internal_error",
            failed_check="internal_error",
        )
    report = build_report(result)
    emit_report(report, pretty=bool(args.pretty))
    return _exit_for_code(result.code)


if __name__ == "__main__":
    raise SystemExit(main())
