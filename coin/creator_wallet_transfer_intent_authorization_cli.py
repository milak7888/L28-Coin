"""Explicit-path CLI for offline transfer-intent authorization verification."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from .creator_wallet_transfer_intent_authorization import (
    CreatorWalletTransferIntentAuthorizationResult,
    HEX64_RE,
    MAX_AUTHORIZATION_BYTES,
    STABLE_CODES,
    verify_creator_wallet_transfer_intent_authorization_json,
)

REPORT_VERSION = "l28-creator-wallet-transfer-intent-authorization-report/v0.1"
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
    result: CreatorWalletTransferIntentAuthorizationResult,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "report_version": REPORT_VERSION,
        "ok": result.ok,
        "code": result.code,
        "checks": list(result.checks),
        "authorization_sha256": result.authorization_sha256,
        "authorization_id": result.authorization_id,
        "intent_sha256": result.intent_sha256,
        "intent_id": result.intent_id,
        "creator_address": result.creator_address,
        "recipient_address": result.recipient_address,
        "amount": result.amount,
        "expires_at_unix": result.expires_at_unix,
        "control_bundle_sha256": result.control_bundle_sha256,
        "control_bundle_aggregate_commitment": (
            result.control_bundle_aggregate_commitment
        ),
        "stable_codes": list(STABLE_CODES) + list(CLI_CODES),
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


def _failure(code: str) -> CreatorWalletTransferIntentAuthorizationResult:
    return CreatorWalletTransferIntentAuthorizationResult(False, code)


def _read_explicit_file(path_text: str) -> bytes:
    path = Path(path_text)
    try:
        if path.is_symlink() or not path.is_file():
            raise _CliError("invalid_path", EXIT_IO)
        with path.open("rb") as handle:
            raw = handle.read(MAX_AUTHORIZATION_BYTES + 1)
    except _CliError:
        raise
    except OSError as exc:
        raise _CliError("io_error", EXIT_IO) from exc
    if len(raw) > MAX_AUTHORIZATION_BYTES:
        raise _CliError("file_too_large", EXIT_IO)
    return raw


def verify_creator_wallet_transfer_intent_authorization_file(
    path_text: str,
    *,
    expected_control_bundle_sha256: str,
    expected_control_bundle_aggregate_commitment: str,
) -> CreatorWalletTransferIntentAuthorizationResult:
    raw = _read_explicit_file(path_text)
    return verify_creator_wallet_transfer_intent_authorization_json(
        raw,
        expected_control_bundle_sha256=expected_control_bundle_sha256,
        expected_control_bundle_aggregate_commitment=(
            expected_control_bundle_aggregate_commitment
        ),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="creator-wallet-transfer-intent-authorization",
        description="Verify one explicit offline authorization JSON file.",
    )
    parser.add_argument("authorization_file")
    parser.add_argument(
        "--control-bundle-sha256",
        required=True,
        dest="control_bundle_sha256",
    )
    parser.add_argument(
        "--control-bundle-aggregate-commitment",
        required=True,
        dest="control_bundle_aggregate_commitment",
    )
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if (
            HEX64_RE.fullmatch(args.control_bundle_sha256) is None
            or HEX64_RE.fullmatch(
                args.control_bundle_aggregate_commitment
            ) is None
        ):
            result = _failure("invalid_expected_commitment")
            exit_code = EXIT_VERIFICATION
        else:
            result = verify_creator_wallet_transfer_intent_authorization_file(
                args.authorization_file,
                expected_control_bundle_sha256=args.control_bundle_sha256,
                expected_control_bundle_aggregate_commitment=(
                    args.control_bundle_aggregate_commitment
                ),
            )
            exit_code = EXIT_OK if result.ok else EXIT_VERIFICATION
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
