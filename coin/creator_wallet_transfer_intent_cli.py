"""Explicit-path CLI for offline creator-wallet transfer-intent verification."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from .creator_wallet_transfer_intent import (
    HEX64_RE,
    MAX_INTENT_BYTES,
    STABLE_CODES,
    CreatorWalletTransferIntentResult,
    verify_creator_wallet_transfer_intent_json,
)


REPORT_VERSION = "l28-creator-wallet-transfer-intent-report/v0.1"
REPORT_DOMAIN = b"l28-creator-wallet-transfer-intent-report/v0.1\x00"
REPORT_FIELDS = (
    "report_id",
    "report_version",
    "ok",
    "code",
    "checks",
    "intent_sha256",
    "intent_id",
    "creator_address",
    "recipient_address",
    "amount",
    "expires_at_unix",
    "control_bundle_sha256",
    "control_bundle_aggregate_commitment",
    "stable_codes",
    "runtime_activation",
    "wallet_loaded",
    "private_key_read",
    "signature_created",
    "transfer_created",
    "ledger_mutated",
    "network_access",
    "execution_authorized",
)
CLI_CODES = STABLE_CODES + ("invalid_path", "io_error")
EXIT_OK = 0
EXIT_VERIFICATION = 1
EXIT_USAGE = 2
EXIT_IO = 3
EXIT_INTERNAL = 4


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _report_id(report: dict[str, Any]) -> str:
    return hashlib.sha256(REPORT_DOMAIN + _canonical_bytes(report)).hexdigest()


def _build_report(result: CreatorWalletTransferIntentResult) -> dict[str, Any]:
    body = {
        "report_version": REPORT_VERSION,
        "ok": result.ok,
        "code": result.code,
        "checks": list(result.checks),
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
        "stable_codes": list(CLI_CODES),
        "runtime_activation": False,
        "wallet_loaded": False,
        "private_key_read": False,
        "signature_created": False,
        "transfer_created": False,
        "ledger_mutated": False,
        "network_access": False,
        "execution_authorized": False,
    }
    return {"report_id": _report_id(body), **body}


def _failure(code: str) -> CreatorWalletTransferIntentResult:
    return CreatorWalletTransferIntentResult(False, code)


def _read_explicit_file(path_text: str) -> bytes:
    path = Path(path_text)
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError("invalid path")
        with path.open("rb") as handle:
            payload = handle.read(MAX_INTENT_BYTES + 1)
    except ValueError:
        raise
    except OSError as exc:
        raise OSError("unable to read intent") from exc
    return payload


def verify_creator_wallet_transfer_intent_file(
    path_text: str,
    *,
    expected_control_bundle_sha256: str,
    expected_control_bundle_aggregate_commitment: str,
) -> CreatorWalletTransferIntentResult:
    if (
        not isinstance(expected_control_bundle_sha256, str)
        or not HEX64_RE.fullmatch(expected_control_bundle_sha256)
        or not isinstance(expected_control_bundle_aggregate_commitment, str)
        or not HEX64_RE.fullmatch(expected_control_bundle_aggregate_commitment)
    ):
        return _failure("invalid_expected_commitment")
    try:
        payload = _read_explicit_file(path_text)
    except ValueError:
        return _failure("invalid_path")
    except OSError:
        return _failure("io_error")
    return verify_creator_wallet_transfer_intent_json(
        payload,
        expected_control_bundle_sha256=expected_control_bundle_sha256,
        expected_control_bundle_aggregate_commitment=(
            expected_control_bundle_aggregate_commitment
        ),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="creator-wallet-transfer-intent")
    parser.add_argument("intent_file")
    parser.add_argument("--control-bundle-sha256", required=True)
    parser.add_argument(
        "--control-bundle-aggregate-commitment",
        required=True,
    )
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = verify_creator_wallet_transfer_intent_file(
            args.intent_file,
            expected_control_bundle_sha256=args.control_bundle_sha256,
            expected_control_bundle_aggregate_commitment=(
                args.control_bundle_aggregate_commitment
            ),
        )
        report = _build_report(result)
        print(
            json.dumps(
                report,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=False,
                indent=2 if args.pretty else None,
                separators=None if args.pretty else (",", ":"),
            )
        )
        if result.ok:
            return EXIT_OK
        if result.code in {"invalid_path", "io_error"}:
            return EXIT_IO
        if result.code == "internal_error":
            return EXIT_INTERNAL
        return EXIT_VERIFICATION
    except Exception:
        report = _build_report(_failure("internal_error"))
        print(
            json.dumps(
                report,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=False,
                separators=(",", ":"),
            )
        )
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
