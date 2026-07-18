"""CLI for the offline creator-wallet control-proof verifier."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .creator_wallet_control_proof import (
    MAX_PROOF_BYTES,
    STABLE_CODES,
    verify_creator_wallet_control_proof_json,
)


REPORT_VERSION = "l28-creator-wallet-control-proof-report/v0.1"
REPORT_DOMAIN = b"l28-creator-wallet-control-proof-report/v0.1\x00"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _report_id(report: dict[str, Any]) -> str:
    body = {key: value for key, value in report.items() if key != "report_id"}
    return hashlib.sha256(REPORT_DOMAIN + _canonical_bytes(body)).hexdigest()


def _build_report(*, ok: bool, code: str, checks: Sequence[str], proof_sha256: str) -> dict[str, Any]:
    report = {
        "report_version": REPORT_VERSION,
        "ok": ok,
        "code": code,
        "checks": list(checks),
        "proof_sha256": proof_sha256,
        "stable_codes": list(STABLE_CODES),
        "runtime_activation": False,
        "wallet_loaded": False,
        "private_key_read": False,
        "signature_created": False,
        "transfer_created": False,
        "ledger_mutated": False,
        "network_access": False,
    }
    return {"report_id": _report_id(report), **report}


def _read_explicit_file(path_text: str) -> tuple[bytes | None, str]:
    try:
        path = Path(path_text)
        if path.is_symlink():
            return None, "path_not_regular_file"
        if not path.exists():
            return None, "path_not_regular_file"
        if not path.is_file():
            return None, "path_not_regular_file"
        if path.stat().st_size > MAX_PROOF_BYTES:
            return None, "proof_too_large"
        raw = path.read_bytes()
        if len(raw) > MAX_PROOF_BYTES:
            return None, "proof_too_large"
        return raw, "ok"
    except Exception:
        return None, "path_not_regular_file"


def verify_creator_wallet_control_proof_file(
    path_text: str,
    *,
    expected_challenge_id: str,
) -> dict[str, Any]:
    raw, read_code = _read_explicit_file(path_text)
    if raw is None:
        return _build_report(
            ok=False,
            code=read_code,
            checks=(),
            proof_sha256="",
        )
    result = verify_creator_wallet_control_proof_json(
        raw,
        expected_challenge_id=expected_challenge_id,
    )
    return _build_report(
        ok=result.ok,
        code=result.code,
        checks=result.checks,
        proof_sha256=result.proof_sha256,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="creator-wallet-control-proof",
        description="Verify one explicit offline creator-wallet control-proof file.",
    )
    parser.add_argument("proof_file")
    parser.add_argument("--challenge-id", required=True)
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    try:
        report = verify_creator_wallet_control_proof_file(
            args.proof_file,
            expected_challenge_id=args.challenge_id,
        )
        output = json.dumps(
            report,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2 if args.pretty else None,
            separators=None if args.pretty else (",", ":"),
        )
        print(output)
        if report["ok"]:
            return 0
        if report["code"] == "internal_error":
            return 2
        return 1
    except Exception:
        report = _build_report(
            ok=False,
            code="internal_error",
            checks=(),
            proof_sha256="",
        )
        print(
            json.dumps(
                report,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 2
