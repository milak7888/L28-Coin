# SPDX-License-Identifier: Apache-2.0
"""Isolated Agent Purchase Demo v0.1.

Local in-process workflow: Agent A buys one verifiable SHA-256 service from
Agent B and receives a Foundation 64/67 signed receipt. Disposable Ed25519 keys
remain function-local; private material is never returned, logged, or persisted.

Composes existing CanonUaii digests and signed-receipt primitives. Does not
modify UAII schemas, call ledgers, submit transactions, or use a public network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Callable, Mapping
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from coin.uaii_json import UaiiJsonError, canon_uaii
from coin.uaii_signed_receipt import (
    ASSET_L28,
    PURPOSE_SIGNED_RECEIPT,
    RECEIPT_PROFILE,
    SIGNER_ALGORITHM_PROFILE,
    UNSIGNED_FACTS_FIELDS,
    F64ReceiptSchemaError,
    public_key_id_for_raw,
    required_signer_identity,
    sign_unsigned_receipt_facts,
    verify_signed_receipt_facts,
)

DEMO_PROFILE = "l28-isolated-agent-purchase-demo/v0.1"
DEMO_VERSION = "0.1"
SERVICE_ID = "l28.demo.sha256.v0.1"
QUOTE_PROFILE = "l28-uaii-quote/v0.1"
DEMO_PRICE_AMOUNT = 1
DEMO_PRICE_UNIT = "demo_units_non_monetary"
DEMO_PURPOSE = "isolated_agent_purchase_demo_v0.1"

QUOTE_SIGN_DOMAIN = b"L28-DEMO-V0.1-QUOTE\x00"
APPROVAL_SIGN_DOMAIN = b"L28-DEMO-V0.1-SIM-APPROVAL\x00"
DELIVERY_SIGN_DOMAIN = b"L28-DEMO-V0.1-DELIVERY\x00"

# Fixed demo timeline — no system clock.
DEMO_CREATED_AT = 1_700_000_000
DEMO_EXPIRES_AT = 1_700_000_600

BUYER_IDENTITY = "demo-agent-a-buyer"
SELLER_IDENTITY = "demo-agent-b-seller"

RESULT_FIELDS = (
    "demo_profile",
    "demo_version",
    "demo_completed",
    "service_output_verified",
    "receipt_signature_verified",
    "simulation_only",
    "real_payment_executed",
    "settlement_finalized",
    "transaction_submitted",
    "ledger_mutated",
    "persistent_state_created",
    "public_network_used",
    "service_id",
    "buyer_public_identity",
    "seller_public_identity",
    "buyer_public_key",
    "seller_public_key",
    "buyer_public_key_id",
    "seller_public_key_id",
    "request",
    "request_digest",
    "quote",
    "quote_id",
    "quote_signature",
    "simulated_approval",
    "simulated_approval_signature",
    "delivery",
    "delivery_signature",
    "output_digest",
    "signed_receipt",
)

REQUEST_FIELDS = (
    "demo_profile",
    "service_id",
    "buyer_public_identity",
    "seller_public_identity",
    "input",
)

QUOTE_BODY_FIELDS = (
    "quote_profile",
    "payer_identity",
    "payee_identity",
    "service_id",
    "service_params",
    "amount",
    "currency",
    "purpose",
    "quote_expires_at",
    "quote_nonce",
    "max_amount",
    "rejectable",
    "service_terms",
    "service_terms_hash",
    "spend_authorized",
    "execution_authorized",
)

APPROVAL_FIELDS = (
    "demo_profile",
    "quote_id",
    "buyer_public_identity",
    "simulation_only",
    "real_payment_executed",
    "spend_authorized",
    "settlement_authorized",
    "transaction_submitted",
    "ledger_mutated",
)

DELIVERY_FIELDS = (
    "demo_profile",
    "quote_id",
    "service_id",
    "request_digest",
    "output",
    "output_digest",
)


class DemoError(Exception):
    """Fail-closed demo boundary error."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _digest_obj(obj: Any) -> str:
    try:
        return hashlib.sha256(canon_uaii(obj)).hexdigest()
    except UaiiJsonError as exc:
        raise DemoError("schema_invalid") from exc


def _require_keys_order(obj: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(obj, dict) or tuple(obj.keys()) != fields:
        raise DemoError("schema_invalid")
    return obj


def _require_mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DemoError("schema_invalid")
    return value


def _canonical_request_input(input_value: Any) -> dict[str, Any]:
    if isinstance(input_value, str):
        if input_value == "":
            raise DemoError("schema_invalid")
        return {"text": input_value}
    if isinstance(input_value, Mapping):
        if len(input_value) == 0:
            raise DemoError("schema_invalid")
        # Exact-order copy; reject nested non-JSON-safe values via canon later.
        return {str(k): input_value[k] for k in input_value.keys()}
    raise DemoError("schema_invalid")


def _service_output(canonical_input: Mapping[str, Any]) -> str:
    return hashlib.sha256(canon_uaii(dict(canonical_input))).hexdigest()


def _sign_domain(
    *,
    domain: bytes,
    payload: Mapping[str, Any],
    sign_bytes: Callable[[bytes], bytes],
    public_key_hex: str,
) -> str:
    message = domain + canon_uaii(dict(payload))
    try:
        signature_raw = sign_bytes(message)
    except Exception as exc:  # noqa: BLE001 — fail closed at signer boundary
        raise DemoError("signature_invalid") from exc
    if not isinstance(signature_raw, (bytes, bytearray)) or len(signature_raw) != 64:
        raise DemoError("signature_invalid")
    signature_hex = bytes(signature_raw).hex()
    _verify_domain(
        domain=domain,
        payload=payload,
        signature_hex=signature_hex,
        public_key_hex=public_key_hex,
    )
    return signature_hex


def _verify_domain(
    *,
    domain: bytes,
    payload: Mapping[str, Any],
    signature_hex: str,
    public_key_hex: str,
) -> None:
    try:
        pk = bytes.fromhex(public_key_hex)
        sig = bytes.fromhex(signature_hex)
    except ValueError as exc:
        raise DemoError("signature_invalid") from exc
    if len(pk) != 32 or len(sig) != 64:
        raise DemoError("signature_invalid")
    message = domain + canon_uaii(dict(payload))
    try:
        Ed25519PublicKey.from_public_bytes(pk).verify(sig, message)
    except (InvalidSignature, ValueError) as exc:
        raise DemoError("signature_invalid") from exc


def _build_quote(
    *,
    request_digest: str,
    buyer_identity: str,
    seller_identity: str,
) -> tuple[dict[str, Any], str]:
    service_params = {
        "request_digest": request_digest,
        "demo_profile": DEMO_PROFILE,
    }
    service_terms = {
        "demo_profile": DEMO_PROFILE,
        "simulation_only": True,
        "non_monetary_test_only": True,
        "demo_price_unit": DEMO_PRICE_UNIT,
        "real_payment_executed": False,
        "service_id": SERVICE_ID,
        "request_digest": request_digest,
    }
    terms_hash = _digest_obj(service_terms)
    quote = {
        "quote_profile": QUOTE_PROFILE,
        "payer_identity": buyer_identity,
        "payee_identity": seller_identity,
        "service_id": SERVICE_ID,
        "service_params": service_params,
        "amount": DEMO_PRICE_AMOUNT,
        "currency": ASSET_L28,
        "purpose": DEMO_PURPOSE,
        "quote_expires_at": DEMO_EXPIRES_AT,
        "quote_nonce": "demo-quote-nonce-v0.1",
        "max_amount": DEMO_PRICE_AMOUNT,
        "rejectable": True,
        "service_terms": service_terms,
        "service_terms_hash": terms_hash,
        "spend_authorized": False,
        "execution_authorized": False,
    }
    _require_keys_order(quote, QUOTE_BODY_FIELDS)
    return quote, _digest_obj(quote)


def _build_unsigned_receipt(
    *,
    request_digest: str,
    quote_id: str,
    service_result_id: str,
    buyer_identity: str,
    seller_identity: str,
    seller_public_key_hex: str,
    seller_public_key_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    unsigned = {
        "receipt_profile": RECEIPT_PROFILE,
        "prior_receipt_id": None,
        "correlation_id": correlation_id,
        "request_id": request_digest,
        "quote_id": quote_id,
        "service_result_id": service_result_id,
        "payer_public_identity": buyer_identity,
        "provider_public_identity": seller_identity,
        "asset_id": ASSET_L28,
        "amount": DEMO_PRICE_AMOUNT,
        "purpose": PURPOSE_SIGNED_RECEIPT,
        "created_at": DEMO_CREATED_AT,
        "expires_at": DEMO_EXPIRES_AT,
        "receipt_nonce": "demo-receipt-nonce-v0.1",
        "transaction_id": "",
        "settlement_status": "service_result_signed",
        "signer_algorithm_profile": SIGNER_ALGORITHM_PROFILE,
        "signer_public_key_id": seller_public_key_id,
        "signer_public_key": seller_public_key_hex,
        "signing_authorized": False,
        "spend_authorized": False,
        "settlement_authorized": False,
        "ledger_mutated": False,
        "execution_authorized": False,
    }
    return {k: unsigned[k] for k in UNSIGNED_FACTS_FIELDS}


def _public_result(**values: Any) -> dict[str, Any]:
    result = {k: values[k] for k in RESULT_FIELDS}
    if tuple(result.keys()) != RESULT_FIELDS:
        raise DemoError("schema_invalid")
    return result


def verify_isolated_agent_purchase_demo_result(result: Any) -> dict[str, Any]:
    """Independently recompute digests and verify public signatures only."""
    obj = _require_keys_order(result, RESULT_FIELDS)
    if obj["demo_profile"] != DEMO_PROFILE or obj["demo_version"] != DEMO_VERSION:
        raise DemoError("schema_invalid")
    if obj["service_id"] != SERVICE_ID:
        raise DemoError("schema_invalid")
    for flag in (
        "simulation_only",
        "demo_completed",
        "service_output_verified",
        "receipt_signature_verified",
    ):
        if obj[flag] is not True:
            raise DemoError("verification_failed")
    for flag in (
        "real_payment_executed",
        "settlement_finalized",
        "transaction_submitted",
        "ledger_mutated",
        "persistent_state_created",
        "public_network_used",
    ):
        if obj[flag] is not False:
            raise DemoError("verification_failed")

    request = _require_keys_order(obj["request"], REQUEST_FIELDS)
    if _digest_obj(request) != obj["request_digest"]:
        raise DemoError("digest_mismatch")
    if request["service_id"] != SERVICE_ID:
        raise DemoError("schema_invalid")
    if request["buyer_public_identity"] != obj["buyer_public_identity"]:
        raise DemoError("identity_mismatch")
    if request["seller_public_identity"] != obj["seller_public_identity"]:
        raise DemoError("identity_mismatch")

    quote = _require_keys_order(obj["quote"], QUOTE_BODY_FIELDS)
    if _digest_obj(quote) != obj["quote_id"]:
        raise DemoError("digest_mismatch")
    if quote["service_id"] != SERVICE_ID:
        raise DemoError("schema_invalid")
    if quote["payer_identity"] != obj["buyer_public_identity"]:
        raise DemoError("identity_mismatch")
    if quote["payee_identity"] != obj["seller_public_identity"]:
        raise DemoError("identity_mismatch")
    terms = quote["service_terms"]
    if not isinstance(terms, Mapping):
        raise DemoError("schema_invalid")
    if terms.get("simulation_only") is not True:
        raise DemoError("verification_failed")
    if terms.get("non_monetary_test_only") is not True:
        raise DemoError("verification_failed")
    if terms.get("demo_price_unit") != DEMO_PRICE_UNIT:
        raise DemoError("verification_failed")
    if quote["spend_authorized"] is not False or quote["execution_authorized"] is not False:
        raise DemoError("verification_failed")
    if quote["service_params"].get("request_digest") != obj["request_digest"]:
        raise DemoError("digest_mismatch")

    _verify_domain(
        domain=QUOTE_SIGN_DOMAIN,
        payload=quote,
        signature_hex=obj["quote_signature"],
        public_key_hex=obj["seller_public_key"],
    )

    approval = _require_keys_order(obj["simulated_approval"], APPROVAL_FIELDS)
    if approval["quote_id"] != obj["quote_id"]:
        raise DemoError("digest_mismatch")
    if approval["buyer_public_identity"] != obj["buyer_public_identity"]:
        raise DemoError("identity_mismatch")
    if approval["simulation_only"] is not True:
        raise DemoError("verification_failed")
    for flag in (
        "real_payment_executed",
        "spend_authorized",
        "settlement_authorized",
        "transaction_submitted",
        "ledger_mutated",
    ):
        if approval[flag] is not False:
            raise DemoError("verification_failed")
    _verify_domain(
        domain=APPROVAL_SIGN_DOMAIN,
        payload=approval,
        signature_hex=obj["simulated_approval_signature"],
        public_key_hex=obj["buyer_public_key"],
    )

    delivery = _require_keys_order(obj["delivery"], DELIVERY_FIELDS)
    if delivery["quote_id"] != obj["quote_id"]:
        raise DemoError("digest_mismatch")
    if delivery["request_digest"] != obj["request_digest"]:
        raise DemoError("digest_mismatch")
    if delivery["service_id"] != SERVICE_ID:
        raise DemoError("schema_invalid")
    expected_output = _service_output(request["input"])
    if delivery["output"] != expected_output or obj["output_digest"] != expected_output:
        raise DemoError("output_mismatch")
    if delivery["output_digest"] != expected_output:
        raise DemoError("output_mismatch")
    _verify_domain(
        domain=DELIVERY_SIGN_DOMAIN,
        payload=delivery,
        signature_hex=obj["delivery_signature"],
        public_key_hex=obj["seller_public_key"],
    )

    try:
        verified_receipt = verify_signed_receipt_facts(obj["signed_receipt"])
    except F64ReceiptSchemaError as exc:
        raise DemoError(exc.code) from exc
    if verified_receipt["quote_id"] != obj["quote_id"]:
        raise DemoError("digest_mismatch")
    if verified_receipt["request_id"] != obj["request_digest"]:
        raise DemoError("digest_mismatch")
    if verified_receipt["service_result_id"] != _digest_obj(delivery):
        raise DemoError("digest_mismatch")
    if verified_receipt["payer_public_identity"] != obj["buyer_public_identity"]:
        raise DemoError("identity_mismatch")
    if verified_receipt["provider_public_identity"] != obj["seller_public_identity"]:
        raise DemoError("identity_mismatch")
    if verified_receipt["signer_public_key"] != obj["seller_public_key"]:
        raise DemoError("identity_mismatch")
    if verified_receipt["settlement_status"] != "service_result_signed":
        raise DemoError("verification_failed")
    if verified_receipt["transaction_id"] != "":
        raise DemoError("verification_failed")
    for flag in (
        "signing_authorized",
        "spend_authorized",
        "settlement_authorized",
        "ledger_mutated",
        "execution_authorized",
    ):
        if verified_receipt[flag] is not False:
            raise DemoError("verification_failed")

    return {
        "ok": True,
        "code": "demo_verified",
        "service_output_verified": True,
        "receipt_signature_verified": True,
        "simulation_only": True,
        "real_payment_executed": False,
        "ledger_mutated": False,
    }


def run_isolated_agent_purchase_demo(
    *,
    request_input: Any = "l28-demo-input-v0.1",
    buyer_signer: Callable[[bytes], bytes] | None = None,
    seller_signer: Callable[[bytes], bytes] | None = None,
    buyer_public_key_hex: str | None = None,
    seller_public_key_hex: str | None = None,
    buyer_public_identity: str = BUYER_IDENTITY,
    seller_public_identity: str = SELLER_IDENTITY,
) -> dict[str, Any]:
    """Run the full Agent A → Agent B purchase workflow in one local process.

    When signers are omitted, disposable in-memory Ed25519 keys are generated
    for this call only. Private keys never appear in the returned object.
    """
    if buyer_public_identity == "" or seller_public_identity == "":
        raise DemoError("identity_invalid")
    if buyer_public_identity == seller_public_identity:
        raise DemoError("identity_invalid")
    if (buyer_signer is None) ^ (buyer_public_key_hex is None):
        raise DemoError("schema_invalid")
    if (seller_signer is None) ^ (seller_public_key_hex is None):
        raise DemoError("schema_invalid")

    buyer_key: Ed25519PrivateKey | None = None
    seller_key: Ed25519PrivateKey | None = None
    if buyer_signer is None:
        buyer_key = Ed25519PrivateKey.generate()
        buyer_public_key_hex = buyer_key.public_key().public_bytes_raw().hex()
        buyer_signer = buyer_key.sign
    if seller_signer is None:
        seller_key = Ed25519PrivateKey.generate()
        seller_public_key_hex = seller_key.public_key().public_bytes_raw().hex()
        seller_signer = seller_key.sign

    assert buyer_public_key_hex is not None
    assert seller_public_key_hex is not None
    assert buyer_signer is not None
    assert seller_signer is not None

    try:
        buyer_pk_raw = bytes.fromhex(buyer_public_key_hex)
        seller_pk_raw = bytes.fromhex(seller_public_key_hex)
    except ValueError as exc:
        raise DemoError("schema_invalid") from exc
    if len(buyer_pk_raw) != 32 or len(seller_pk_raw) != 32:
        raise DemoError("schema_invalid")
    buyer_public_key_id = public_key_id_for_raw(buyer_pk_raw)
    seller_public_key_id = public_key_id_for_raw(seller_pk_raw)

    canonical_input = _canonical_request_input(request_input)
    request = {
        "demo_profile": DEMO_PROFILE,
        "service_id": SERVICE_ID,
        "buyer_public_identity": buyer_public_identity,
        "seller_public_identity": seller_public_identity,
        "input": canonical_input,
    }
    _require_keys_order(request, REQUEST_FIELDS)
    request_digest = _digest_obj(request)

    quote, quote_id = _build_quote(
        request_digest=request_digest,
        buyer_identity=buyer_public_identity,
        seller_identity=seller_public_identity,
    )
    quote_signature = _sign_domain(
        domain=QUOTE_SIGN_DOMAIN,
        payload=quote,
        sign_bytes=seller_signer,
        public_key_hex=seller_public_key_hex,
    )

    approval = {
        "demo_profile": DEMO_PROFILE,
        "quote_id": quote_id,
        "buyer_public_identity": buyer_public_identity,
        "simulation_only": True,
        "real_payment_executed": False,
        "spend_authorized": False,
        "settlement_authorized": False,
        "transaction_submitted": False,
        "ledger_mutated": False,
    }
    _require_keys_order(approval, APPROVAL_FIELDS)
    approval_signature = _sign_domain(
        domain=APPROVAL_SIGN_DOMAIN,
        payload=approval,
        sign_bytes=buyer_signer,
        public_key_hex=buyer_public_key_hex,
    )

    output_digest = _service_output(canonical_input)
    delivery = {
        "demo_profile": DEMO_PROFILE,
        "quote_id": quote_id,
        "service_id": SERVICE_ID,
        "request_digest": request_digest,
        "output": output_digest,
        "output_digest": output_digest,
    }
    _require_keys_order(delivery, DELIVERY_FIELDS)
    delivery_signature = _sign_domain(
        domain=DELIVERY_SIGN_DOMAIN,
        payload=delivery,
        sign_bytes=seller_signer,
        public_key_hex=seller_public_key_hex,
    )
    service_result_id = _digest_obj(delivery)
    correlation_id = _digest_obj(
        {
            "demo_profile": DEMO_PROFILE,
            "request_digest": request_digest,
            "quote_id": quote_id,
            "service_result_id": service_result_id,
        }
    )

    unsigned = _build_unsigned_receipt(
        request_digest=request_digest,
        quote_id=quote_id,
        service_result_id=service_result_id,
        buyer_identity=buyer_public_identity,
        seller_identity=seller_public_identity,
        seller_public_key_hex=seller_public_key_hex,
        seller_public_key_id=seller_public_key_id,
        correlation_id=correlation_id,
    )
    try:
        signed_receipt = sign_unsigned_receipt_facts(
            unsigned,
            sign_signable_bytes=seller_signer,
            expected_signer_identity=required_signer_identity(unsigned),
        )
        verified = verify_signed_receipt_facts(signed_receipt)
    except F64ReceiptSchemaError as exc:
        raise DemoError(exc.code) from exc

    # Drop local private key references before returning public artifacts.
    buyer_key = None
    seller_key = None
    del buyer_key, seller_key

    result = _public_result(
        demo_profile=DEMO_PROFILE,
        demo_version=DEMO_VERSION,
        demo_completed=True,
        service_output_verified=verified["receipt_id"] == signed_receipt["receipt_id"]
        and output_digest == delivery["output"],
        receipt_signature_verified=True,
        simulation_only=True,
        real_payment_executed=False,
        settlement_finalized=False,
        transaction_submitted=False,
        ledger_mutated=False,
        persistent_state_created=False,
        public_network_used=False,
        service_id=SERVICE_ID,
        buyer_public_identity=buyer_public_identity,
        seller_public_identity=seller_public_identity,
        buyer_public_key=buyer_public_key_hex,
        seller_public_key=seller_public_key_hex,
        buyer_public_key_id=buyer_public_key_id,
        seller_public_key_id=seller_public_key_id,
        request=request,
        request_digest=request_digest,
        quote=quote,
        quote_id=quote_id,
        quote_signature=quote_signature,
        simulated_approval=approval,
        simulated_approval_signature=approval_signature,
        delivery=delivery,
        delivery_signature=delivery_signature,
        output_digest=output_digest,
        signed_receipt=signed_receipt,
    )
    # Independent re-verification of public material only.
    verify_isolated_agent_purchase_demo_result(result)
    return result


CLI_SCHEMA = "l28.isolated-agent-purchase-demo"
CLI_SCHEMA_VERSION = "0.2"
DEFAULT_DEMO_INPUT = "l28-demo-input-v0.1"

CLI_ERROR_MESSAGES = {
    "invalid_argument": "Invalid command-line arguments.",
    "schema_invalid": "Demo input or artifact schema is invalid.",
    "identity_invalid": "Buyer and seller identities are invalid.",
    "identity_mismatch": "Public identity binding mismatch.",
    "digest_mismatch": "Public digest binding mismatch.",
    "output_mismatch": "Service output does not match canonical request.",
    "signature_invalid": "Public signature verification failed.",
    "verification_failed": "Independent demo verification failed.",
    "demo_failed": "Demo generation failed.",
}

CLI_ENVELOPE_COMPLETED_FIELDS = ("schema", "schema_version", "status", "result")
CLI_ENVELOPE_ERROR_FIELDS = ("schema", "schema_version", "status", "error")
CLI_ERROR_FIELDS = ("code", "message")


def _safe_public_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "demo_profile": result["demo_profile"],
        "demo_version": result["demo_version"],
        "demo_completed": result["demo_completed"],
        "service_output_verified": result["service_output_verified"],
        "receipt_signature_verified": result["receipt_signature_verified"],
        "simulation_only": result["simulation_only"],
        "real_payment_executed": result["real_payment_executed"],
        "settlement_finalized": result["settlement_finalized"],
        "transaction_submitted": result["transaction_submitted"],
        "ledger_mutated": result["ledger_mutated"],
        "persistent_state_created": result["persistent_state_created"],
        "public_network_used": result["public_network_used"],
        "service_id": result["service_id"],
        "buyer_public_identity": result["buyer_public_identity"],
        "seller_public_identity": result["seller_public_identity"],
        "request_digest": result["request_digest"],
        "quote_id": result["quote_id"],
        "output_digest": result["output_digest"],
        "receipt_id": result["signed_receipt"]["receipt_id"],
    }


def _cli_error_message(code: str) -> str:
    return CLI_ERROR_MESSAGES.get(code, CLI_ERROR_MESSAGES["demo_failed"])


def build_cli_completed_envelope(result: Mapping[str, Any]) -> dict[str, Any]:
    envelope = {
        "schema": CLI_SCHEMA,
        "schema_version": CLI_SCHEMA_VERSION,
        "status": "completed",
        "result": dict(result),
    }
    if tuple(envelope.keys()) != CLI_ENVELOPE_COMPLETED_FIELDS:
        raise DemoError("schema_invalid")
    return envelope


def build_cli_error_envelope(*, code: str) -> dict[str, Any]:
    safe_code = code if code in CLI_ERROR_MESSAGES else "demo_failed"
    error = {
        "code": safe_code,
        "message": _cli_error_message(safe_code),
    }
    if tuple(error.keys()) != CLI_ERROR_FIELDS:
        raise DemoError("schema_invalid")
    envelope = {
        "schema": CLI_SCHEMA,
        "schema_version": CLI_SCHEMA_VERSION,
        "status": "error",
        "error": error,
    }
    if tuple(envelope.keys()) != CLI_ENVELOPE_ERROR_FIELDS:
        raise DemoError("schema_invalid")
    return envelope


def _dumps_json(payload: Mapping[str, Any], *, pretty: bool) -> str:
    if pretty:
        return json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=False,
            indent=2,
        )
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=False,
        separators=(",", ":"),
    )


def _emit_json(payload: Mapping[str, Any], *, pretty: bool) -> None:
    sys.stdout.write(_dumps_json(payload, pretty=pretty))
    sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> int:
    """Offline public CLI entry point (simulation only; no funds)."""
    argv_list = list(sys.argv[1:] if argv is None else argv)
    want_json = "--json" in argv_list
    want_pretty = "--pretty" in argv_list

    parser = argparse.ArgumentParser(
        prog="python -m coin.isolated_agent_purchase_demo",
        description=(
            "Offline public CLI for Isolated Agent Purchase Demo "
            "(simulation only; no funds)."
        ),
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_DEMO_INPUT,
        help="Deterministic public demo input text (default: safe fixed demo input).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit exactly one machine-readable JSON document on stdout.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Indent JSON stdout (use with --json for the stable envelope).",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Independently verify service output and receipt signature before success.",
    )

    class _ArgError(Exception):
        pass

    def _parser_error(message: str) -> None:
        raise _ArgError(message)

    parser.error = _parser_error  # type: ignore[method-assign]

    try:
        args = parser.parse_args(argv_list)
    except _ArgError:
        if want_json:
            _emit_json(
                build_cli_error_envelope(code="invalid_argument"),
                pretty=want_pretty,
            )
        else:
            print("invalid_argument", file=sys.stderr)
        return 2

    try:
        result = run_isolated_agent_purchase_demo(request_input=args.input)
        if args.verify:
            check = verify_isolated_agent_purchase_demo_result(result)
            if (
                check.get("service_output_verified") is not True
                or check.get("receipt_signature_verified") is not True
                or check.get("ok") is not True
            ):
                raise DemoError("verification_failed")
    except DemoError as exc:
        code = exc.code if exc.code in CLI_ERROR_MESSAGES else "demo_failed"
        if args.json:
            _emit_json(build_cli_error_envelope(code=code), pretty=args.pretty)
        else:
            print(code, file=sys.stderr)
        return 1

    if args.json:
        _emit_json(build_cli_completed_envelope(result), pretty=args.pretty)
    else:
        # Backward-compatible human/summary JSON (v0.1).
        _emit_json(_safe_public_summary(result), pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
