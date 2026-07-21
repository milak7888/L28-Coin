"""Explicit-path CLI for offline authorization-evidence receipt verification."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from .creator_wallet_transfer_intent_authorization_evidence_receipt import (
    MAX_RECEIPT_BYTES,
    REPORT_VERSION,
    CreatorWalletTransferIntentAuthorizationEvidenceReceiptResult,
    verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json,
)

REPORT_DOMAIN = (REPORT_VERSION + "\x00").encode("utf-8")
CLI_CODES = ("invalid_path", "file_too_large", "io_error", "internal_error")
EXIT_OK = 0
EXIT_VERIFICATION = 1
EXIT_USAGE = 2
EXIT_IO = 3
EXIT_INTERNAL = 4


class _CliError(ValueError):
    def __init__(self, code: str, exit_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.exit_code = exit_code


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _report_id(body: dict[str, Any]) -> str:
    return hashlib.sha256(REPORT_DOMAIN + _canonical_bytes(body)).hexdigest()


def _build_report(
    result: CreatorWalletTransferIntentAuthorizationEvidenceReceiptResult,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "report_version": REPORT_VERSION,
        "ok": result.ok,
        "code": result.code,
        "checks": list(result.checks),
        "receipt_id": result.receipt_id,
        "evidence_sha256": result.evidence_sha256,
        "authorization_report_id": result.authorization_report_id,
        "authorization_sha256": result.authorization_sha256,
        "authorization_id": result.authorization_id,
        "runtime_activation": False,
        "wallet_loaded": False,
        "private_key_read": False,
        "signature_created": False,
        "transfer_created": False,
        "ledger_mutated": False,
        "clock_access": False,
        "replay_state_access": False,
        "network_access": False,
        "execution_authorized": False,
    }
    return {"report_id": _report_id(body), **body}


def _failure(
    code: str,
) -> CreatorWalletTransferIntentAuthorizationEvidenceReceiptResult:
    return CreatorWalletTransferIntentAuthorizationEvidenceReceiptResult(False, code)


def _read_explicit_file(path_text: str) -> bytes:
    path = Path(path_text)
    try:
        if path.is_symlink() or not path.is_file():
            raise _CliError("invalid_path", EXIT_IO)
        with path.open("rb") as handle:
            raw = handle.read(MAX_RECEIPT_BYTES + 1)
    except _CliError:
        raise
    except OSError as exc:
        raise _CliError("io_error", EXIT_IO) from exc
    if len(raw) > MAX_RECEIPT_BYTES:
        raise _CliError("file_too_large", EXIT_IO)
    return raw


def verify_creator_wallet_transfer_intent_authorization_evidence_receipt_file(
    path_text: str,
) -> CreatorWalletTransferIntentAuthorizationEvidenceReceiptResult:
    raw = _read_explicit_file(path_text)
    return verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(raw)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="creator-wallet-transfer-intent-authorization-evidence-receipt",
        description="Verify one explicit offline authorization-evidence receipt JSON file.",
    )
    parser.add_argument("receipt_file")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = verify_creator_wallet_transfer_intent_authorization_evidence_receipt_file(
            args.receipt_file
        )
        exit_code = EXIT_OK if result.ok else EXIT_VERIFICATION
        if result.code == "internal_error":
            exit_code = EXIT_INTERNAL
    except _CliError as exc:
        result = _failure(exc.code)
        exit_code = exc.exit_code
    except Exception:
        result = _failure("internal_error")
        exit_code = EXIT_INTERNAL

    report = _build_report(result)
    print(
        json.dumps(
            report,
            ensure_ascii=False,
            allow_nan=False,
            indent=2 if args.pretty else None,
            separators=None if args.pretty else (",", ":"),
            sort_keys=False,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
