"""Explicit-path CLI for offline creator-wallet control-proof evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from typing import Any, Sequence

from .creator_wallet_control_proof_evidence import (
    EVIDENCE_REPORT_VERSION,
    MAX_EVIDENCE_BYTES,
    CreatorWalletControlProofEvidenceResult,
    verify_creator_wallet_control_proof_evidence_json,
)

REPORT_DOMAIN = b"l28-creator-wallet-control-proof-evidence-cli-report/v0.1\x00"

EXIT_OK = 0
EXIT_VERIFICATION = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3


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


def _report_for(
    result: CreatorWalletControlProofEvidenceResult,
) -> dict[str, Any]:
    body = {
        "report_version": EVIDENCE_REPORT_VERSION,
        "ok": bool(result.ok),
        "code": str(result.code),
        "checks": list(result.checks),
        "evidence_sha256": str(result.evidence_sha256),
    }
    return {**body, "report_id": _report_id(body)}


def _failure_report(code: str) -> dict[str, Any]:
    body = {
        "report_version": EVIDENCE_REPORT_VERSION,
        "ok": False,
        "code": code,
        "checks": [],
        "evidence_sha256": "",
    }
    return {**body, "report_id": _report_id(body)}


def _emit(report: dict[str, Any], *, pretty: bool) -> None:
    if pretty:
        text = json.dumps(
            report,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        )
    else:
        text = _canonical_bytes(report).decode("utf-8")
    sys.stdout.write(text + "\n")


def _read_explicit_regular_file(path_text: str) -> tuple[bytes | None, str | None]:
    try:
        metadata = os.lstat(path_text)
    except OSError:
        return None, "path_invalid"

    if not stat.S_ISREG(metadata.st_mode):
        return None, "path_invalid"

    if metadata.st_size > MAX_EVIDENCE_BYTES:
        return None, "evidence_too_large"

    try:
        with open(path_text, "rb") as handle:
            payload = handle.read(MAX_EVIDENCE_BYTES + 1)
    except OSError:
        return None, "path_invalid"

    if len(payload) > MAX_EVIDENCE_BYTES:
        return None, "evidence_too_large"

    return payload, None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="creator-wallet-control-proof-evidence",
        description="Verify one explicit offline creator-wallet control-proof evidence file.",
    )
    parser.add_argument("evidence_file")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        payload, path_code = _read_explicit_regular_file(args.evidence_file)
        if path_code is not None:
            _emit(_failure_report(path_code), pretty=args.pretty)
            return EXIT_VERIFICATION

        assert payload is not None
        result = verify_creator_wallet_control_proof_evidence_json(payload)
        _emit(_report_for(result), pretty=args.pretty)

        if result.ok:
            return EXIT_OK
        if result.code == "internal_error":
            return EXIT_INTERNAL
        return EXIT_VERIFICATION
    except Exception:
        _emit(_failure_report("internal_error"), pretty=args.pretty)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
