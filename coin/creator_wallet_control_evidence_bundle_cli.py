"""Explicit-path CLI for offline creator-wallet control evidence bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat
from typing import Any, Sequence

from .creator_wallet_control_evidence_bundle import (
    BUNDLE_REPORT_VERSION,
    MAX_BUNDLE_BYTES,
    VERIFIER_VERSION,
    CreatorWalletControlEvidenceBundleResult,
    verify_creator_wallet_control_evidence_bundle_json,
)

REPORT_DOMAIN = BUNDLE_REPORT_VERSION.encode("utf-8") + b"\x00"
EXIT_OK = 0
EXIT_VERIFICATION_FAILED = 1
EXIT_USAGE_OR_INPUT = 2
EXIT_INTERNAL = 3

REPORT_BODY_FIELDS = (
    "report_version",
    "verifier_version",
    "ok",
    "code",
    "checks",
    "bundle_sha256",
    "aggregate_commitment",
    "member_count",
    "member_evidence_sha256",
)
REPORT_FIELDS = REPORT_BODY_FIELDS + ("report_id",)


class _CliError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _report_id(body: dict[str, Any]) -> str:
    return hashlib.sha256(REPORT_DOMAIN + _canonical_bytes(body)).hexdigest()


def _build_report(
    result: CreatorWalletControlEvidenceBundleResult,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "report_version": BUNDLE_REPORT_VERSION,
        "verifier_version": VERIFIER_VERSION,
        "ok": result.ok,
        "code": result.code,
        "checks": list(result.checks),
        "bundle_sha256": result.bundle_sha256,
        "aggregate_commitment": result.aggregate_commitment,
        "member_count": len(result.member_evidence_sha256),
        "member_evidence_sha256": list(result.member_evidence_sha256),
    }
    return {**body, "report_id": _report_id(body)}


def _failure_report(code: str) -> dict[str, Any]:
    return _build_report(
        CreatorWalletControlEvidenceBundleResult(ok=False, code=code)
    )


def _read_explicit_regular_file(path_text: str) -> bytes:
    path = Path(path_text)
    try:
        if path.is_symlink():
            raise _CliError("input_path_invalid")
        metadata = path.stat()
    except _CliError:
        raise
    except OSError as exc:
        raise _CliError("input_path_invalid") from exc

    if not stat.S_ISREG(metadata.st_mode):
        raise _CliError("input_path_invalid")
    if metadata.st_size > MAX_BUNDLE_BYTES:
        raise _CliError("input_too_large")

    try:
        with path.open("rb") as handle:
            payload = handle.read(MAX_BUNDLE_BYTES + 1)
    except OSError as exc:
        raise _CliError("input_read_error") from exc

    if len(payload) > MAX_BUNDLE_BYTES:
        raise _CliError("input_too_large")
    return payload


def _emit(report: dict[str, Any], *, pretty: bool) -> None:
    if pretty:
        rendered = json.dumps(report, ensure_ascii=False, indent=2)
    else:
        rendered = json.dumps(
            report,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    print(rendered)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="creator-wallet-control-evidence-bundle",
        description="Verify one explicit offline Foundation 31 bundle file.",
    )
    parser.add_argument("bundle_file")
    parser.add_argument("--pretty", action="store_true")
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = _read_explicit_regular_file(args.bundle_file)
        result = verify_creator_wallet_control_evidence_bundle_json(payload)
        _emit(_build_report(result), pretty=args.pretty)
        return EXIT_OK if result.ok else EXIT_VERIFICATION_FAILED
    except _CliError as exc:
        _emit(_failure_report(exc.code), pretty=args.pretty)
        return EXIT_USAGE_OR_INPUT
    except Exception:
        _emit(_failure_report("internal_error"), pretty=args.pretty)
        return EXIT_INTERNAL


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
