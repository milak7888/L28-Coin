"""Deterministic CLI for offline L28 historical-continuity verification."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Any, Mapping, Optional, Sequence

from .historical_continuity_verifier import (
    ContinuityVerifyResult,
    STABLE_CODES,
    verify_manifest,
)


CLI_VERSION = "0.1"
PROFILE = "l28-historical-continuity-cli/v0.1"
REPORT_VERSION = "l28-historical-continuity-report/v0.1"
REPORT_DOMAIN = b"L28-HISTORICAL-CONTINUITY-REPORT-V0.1\x00"

EXIT_PASS = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3

_PATH_FAILURE_CODES = frozenset(
    {
        "invalid_manifest_path",
        "manifest_not_found",
        "manifest_symlink_rejected",
        "manifest_not_regular_file",
        "manifest_too_large",
        "manifest_read_error",
    }
)

CLI_CODES = STABLE_CODES | frozenset({"internal_error"})


def compute_report_id(body: Mapping[str, Any]) -> str:
    """Compute a deterministic identifier over the report body."""

    canonical = json.dumps(
        body,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(REPORT_DOMAIN + canonical).hexdigest()


def build_report(result: ContinuityVerifyResult) -> dict[str, Any]:
    """Build the stable machine-readable report for one verifier result."""

    body: dict[str, Any] = {
        "profile": PROFILE,
        "report_version": REPORT_VERSION,
        "ok": bool(result.ok),
        "code": str(result.code),
        "manifest_version": str(result.manifest_version),
        "manifest_sha256": str(result.manifest_sha256),
        "checks": list(result.checks),
        "detail": str(result.detail),
    }
    return {
        **body,
        "report_id": compute_report_id(body),
    }


def _internal_report() -> dict[str, Any]:
    result = ContinuityVerifyResult(
        ok=False,
        code="internal_error",
        detail="unexpected_internal_error",
    )
    return build_report(result)


def emit_report(report: Mapping[str, Any], *, pretty: bool) -> None:
    """Write exactly one JSON report to standard output."""

    if pretty:
        rendered = json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    else:
        rendered = json.dumps(
            report,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    sys.stdout.write(rendered + "\n")


def _exit_code(result: ContinuityVerifyResult) -> int:
    if result.ok and result.code == "manifest_valid":
        return EXIT_PASS
    if result.code in _PATH_FAILURE_CODES:
        return EXIT_USAGE
    return EXIT_FAILURE


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m coin.historical_continuity_cli",
        description=(
            "Offline, read-only verification of an explicitly supplied "
            "L28 historical-continuity manifest."
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Explicit path to the public continuity manifest.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the deterministic JSON report.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {CLI_VERSION}",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)

    try:
        result = verify_manifest(args.manifest)
        report = build_report(result)
        exit_code = _exit_code(result)
    except Exception:
        report = _internal_report()
        exit_code = EXIT_INTERNAL

    emit_report(report, pretty=bool(args.pretty))
    return exit_code


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
    "REPORT_VERSION",
    "build_report",
    "compute_report_id",
    "emit_report",
    "main",
]
