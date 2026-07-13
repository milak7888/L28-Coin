# SPDX-License-Identifier: Apache-2.0
"""
L28 M2M offline replay-registry backup and recovery CLI (Foundation 12).

Explicit backup and restore subcommands with one deterministic JSON report on stdout.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Mapping, Optional

from coin.m2m_registry_backup import (
    PROFILE,
    REPORT_VERSION,
    STABLE_CODES,
    RegistryBackupResult,
    compute_backup_report_id,
    create_registry_backup,
    restore_registry_backup,
)

CLI_VERSION = "l28-m2m-registry-backup-cli/v0.1"

EXIT_PASS = 0
EXIT_USAGE = 2
EXIT_FAILURE = 3

REPORT_FIELD_ORDER = (
    "report_version",
    "profile",
    "ok",
    "code",
    "operation",
    "destination_created",
    "schema_version",
    "exchange_count",
    "message_count",
    "logical_registry_digest",
    "input_audit_report_id",
    "output_audit_report_id",
    "artifact_sha256",
    "artifact_size_bytes",
    "report_id",
)


def build_report(result: RegistryBackupResult) -> Dict[str, Any]:
    body = {
        "report_version": REPORT_VERSION,
        "profile": PROFILE,
        "ok": bool(result.ok),
        "code": result.code,
        "operation": result.operation,
        "destination_created": bool(result.destination_created),
        "schema_version": result.schema_version,
        "exchange_count": int(result.exchange_count),
        "message_count": int(result.message_count),
        "logical_registry_digest": result.logical_registry_digest,
        "input_audit_report_id": result.input_audit_report_id,
        "output_audit_report_id": result.output_audit_report_id,
        "artifact_sha256": result.artifact_sha256,
        "artifact_size_bytes": int(result.artifact_size_bytes),
    }
    report = dict(body)
    report["report_id"] = compute_backup_report_id(body)
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


def _exit_for_result(result: RegistryBackupResult) -> int:
    if result.ok and result.destination_created:
        if result.code in {"backup_created", "restore_created"}:
            return EXIT_PASS
    from coin.m2m_registry_backup import _EXIT_USAGE_CODES

    if result.code in _EXIT_USAGE_CODES:
        return EXIT_USAGE
    return EXIT_FAILURE


def _usage_message() -> str:
    return (
        "usage: python -m coin.m2m_registry_backup_cli backup "
        "--source ABSOLUTE_PATH --destination ABSOLUTE_PATH [--pretty]\n"
        "       python -m coin.m2m_registry_backup_cli restore "
        "--backup ABSOLUTE_PATH --destination ABSOLUTE_PATH [--pretty]\n"
        "       python -m coin.m2m_registry_backup_cli --version\n"
    )


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m coin.m2m_registry_backup_cli",
        description="Offline L28 M2M replay registry backup and verified recovery CLI.",
        add_help=True,
    )
    subparsers = parser.add_subparsers(dest="command")

    backup_parser = subparsers.add_parser("backup", help="Create a verified registry backup")
    backup_parser.add_argument(
        "--source",
        metavar="ABSOLUTE_PATH",
        required=True,
        help="Existing healthy replay registry outside the repository",
    )
    backup_parser.add_argument(
        "--destination",
        metavar="ABSOLUTE_PATH",
        required=True,
        help="New backup destination outside the repository",
    )
    backup_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON report (content unchanged)",
    )

    restore_parser = subparsers.add_parser("restore", help="Restore a verified registry backup")
    restore_parser.add_argument(
        "--backup",
        metavar="ABSOLUTE_PATH",
        required=True,
        help="Existing healthy backup registry outside the repository",
    )
    restore_parser.add_argument(
        "--destination",
        metavar="ABSOLUTE_PATH",
        required=True,
        help="New restored registry destination outside the repository",
    )
    restore_parser.add_argument(
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
        if args.command is not None:
            sys.stderr.write(_usage_message())
            return EXIT_USAGE
        sys.stdout.write(CLI_VERSION + "\n")
        return EXIT_PASS

    if args.command == "backup":
        result = create_registry_backup(args.source, args.destination)
    elif args.command == "restore":
        result = restore_registry_backup(args.backup, args.destination)
    else:
        sys.stderr.write(_usage_message())
        return EXIT_USAGE

    if result.code not in STABLE_CODES:
        result = RegistryBackupResult(
            ok=False,
            code="internal_error",
            operation=args.command or "backup",
            report_id=compute_backup_report_id(
                {
                    "report_version": REPORT_VERSION,
                    "profile": PROFILE,
                    "ok": False,
                    "code": "internal_error",
                    "operation": args.command or "backup",
                    "destination_created": False,
                    "schema_version": None,
                    "exchange_count": 0,
                    "message_count": 0,
                    "logical_registry_digest": None,
                    "input_audit_report_id": None,
                    "output_audit_report_id": None,
                    "artifact_sha256": None,
                    "artifact_size_bytes": 0,
                }
            ),
        )
    report = build_report(result)
    emit_report(report, pretty=bool(getattr(args, "pretty", False)))
    return _exit_for_result(result)


if __name__ == "__main__":
    raise SystemExit(main())
