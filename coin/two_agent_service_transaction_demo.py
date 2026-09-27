# SPDX-License-Identifier: Apache-2.0
"""First complete disposable two-agent L28 service transaction.

Agent A requests deterministic structured-text analysis from Agent B, receives a
signed 28 L28 quote, pays through the existing disposable transfer path, Agent B
independently verifies the accepted payment, performs the service, and returns a
signed result plus a signed machine-readable receipt.

This module is deliberately local/offline and disposable. It does not activate
production custody, networking, broadcast, mining, testnet, or production
settlement. Private keys remain function-local/in-memory and are never returned,
printed, serialized, imported, or persisted.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from coin.disposable_offline_transfer_demo import (
    ALICE_INITIAL_BALANCE,
    BOB_INITIAL_BALANCE,
    DEMO_TIMESTAMP,
    TRANSFER_AMOUNT,
    _open_ledger,
    _public_key_hex,
    _require_protected_economics,
    apply_transfer,
    build_signed_transfer,
    classify_transfer,
    public_identity,
)
from coin.tx_validation import compute_tx_id
from coin.uaii_json import UaiiJsonError, canon_uaii

DEMO_PROFILE = "l28-two-agent-service-transaction/v0.1"
SERVICE_ID = "l28.service.structured_text_analysis/v0.1"
ASSET_ID = "L28"
PRICE_L28 = 28
CREATED_AT = DEMO_TIMESTAMP
EXPIRES_AT = CREATED_AT + 600
MAX_INPUT_CHARS = 4096
TOP_TERM_LIMIT = 5

REQUEST_SIGN_DOMAIN = b"L28-TWO-AGENT-SERVICE/v0.1/REQUEST\x00"
QUOTE_SIGN_DOMAIN = b"L28-TWO-AGENT-SERVICE/v0.1/QUOTE\x00"
PAYMENT_AUTH_SIGN_DOMAIN = b"L28-TWO-AGENT-SERVICE/v0.1/PAYMENT-AUTH\x00"
RESULT_SIGN_DOMAIN = b"L28-TWO-AGENT-SERVICE/v0.1/RESULT\x00"
RECEIPT_SIGN_DOMAIN = b"L28-TWO-AGENT-SERVICE/v0.1/RECEIPT\x00"

REQUEST_BODY_FIELDS = (
    "profile",
    "message_type",
    "service_id",
    "payer_identity",
    "payer_public_key",
    "provider_identity",
    "input",
    "created_at",
    "nonce",
)
QUOTE_BODY_FIELDS = (
    "profile",
    "message_type",
    "request_id",
    "service_id",
    "payer_identity",
    "provider_identity",
    "provider_public_key",
    "amount",
    "asset_id",
    "created_at",
    "expires_at",
    "nonce",
)
PAYMENT_AUTH_BODY_FIELDS = (
    "profile",
    "message_type",
    "request_id",
    "quote_id",
    "service_id",
    "payer_identity",
    "payer_public_key",
    "provider_identity",
    "amount",
    "asset_id",
    "payment_tx_id",
    "created_at",
    "nonce",
)
RESULT_BODY_FIELDS = (
    "profile",
    "message_type",
    "request_id",
    "quote_id",
    "payment_tx_id",
    "service_id",
    "input_digest",
    "output",
    "provider_identity",
    "provider_public_key",
    "created_at",
)
RECEIPT_BODY_FIELDS = (
    "receipt_profile",
    "payer_identity",
    "provider_identity",
    "request_id",
    "quote_id",
    "service_result_id",
    "payment_tx_id",
    "amount",
    "asset_id",
    "payment_verified",
    "service_executed",
    "provider_public_key",
    "created_at",
)

WORD_RE = re.compile(r"[A-Za-z0-9']+")
SENTENCE_END_RE = re.compile(r"[.!?]+")


class DemoError(Exception):
    """Fail-closed public error for the disposable service transaction."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _canon(value: Any) -> bytes:
    try:
        return canon_uaii(value)
    except (UaiiJsonError, TypeError, ValueError, OverflowError) as exc:
        raise DemoError("schema_invalid") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _require_exact_fields(obj: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(obj, dict) or tuple(obj.keys()) != fields:
        raise DemoError("schema_invalid")
    return obj


def _artifact_body(artifact: Mapping[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    try:
        return {name: artifact[name] for name in fields}
    except (KeyError, TypeError) as exc:
        raise DemoError("schema_invalid") from exc


def _sign_domain(private_key: Ed25519PrivateKey, domain: bytes, body: Mapping[str, Any]) -> str:
    return private_key.sign(domain + _canon(dict(body))).hex()


def _verify_domain(
    *,
    domain: bytes,
    body: Mapping[str, Any],
    public_key_hex: str,
    signature_hex: str,
) -> None:
    try:
        public_raw = bytes.fromhex(public_key_hex)
        signature_raw = bytes.fromhex(signature_hex)
    except (TypeError, ValueError) as exc:
        raise DemoError("signature_invalid") from exc
    if len(public_raw) != 32 or len(signature_raw) != 64:
        raise DemoError("signature_invalid")
    try:
        Ed25519PublicKey.from_public_bytes(public_raw).verify(
            signature_raw,
            domain + _canon(dict(body)),
        )
    except (InvalidSignature, ValueError) as exc:
        raise DemoError("signature_invalid") from exc


def _validate_input_text(text: Any) -> str:
    if not isinstance(text, str) or not text or len(text) > MAX_INPUT_CHARS:
        raise DemoError("input_invalid")
    return text


def _public_identity_for_key(private_key: Ed25519PrivateKey) -> tuple[str, str]:
    public_hex = _public_key_hex(private_key)
    return public_identity(public_hex), public_hex


def build_service_request(
    payer_key: Ed25519PrivateKey,
    *,
    provider_identity: str,
    input_text: str,
) -> dict[str, Any]:
    text = _validate_input_text(input_text)
    payer_identity, payer_public_key = _public_identity_for_key(payer_key)
    body = {
        "profile": DEMO_PROFILE,
        "message_type": "service_request",
        "service_id": SERVICE_ID,
        "payer_identity": payer_identity,
        "payer_public_key": payer_public_key,
        "provider_identity": provider_identity,
        "input": {"text": text},
        "created_at": CREATED_AT,
        "nonce": "request-001",
    }
    _require_exact_fields(body, REQUEST_BODY_FIELDS)
    request_id = _digest(body)
    signature = _sign_domain(payer_key, REQUEST_SIGN_DOMAIN, body)
    return {**body, "request_id": request_id, "signature": signature}


def verify_service_request(request: Mapping[str, Any]) -> dict[str, Any]:
    body = _artifact_body(request, REQUEST_BODY_FIELDS)
    if body["profile"] != DEMO_PROFILE or body["message_type"] != "service_request":
        raise DemoError("schema_invalid")
    if body["service_id"] != SERVICE_ID:
        raise DemoError("service_invalid")
    _validate_input_text(body.get("input", {}).get("text") if isinstance(body.get("input"), dict) else None)
    if body["payer_identity"] != public_identity(body["payer_public_key"]):
        raise DemoError("identity_mismatch")
    request_id = request.get("request_id")
    signature = request.get("signature")
    if not isinstance(request_id, str) or request_id != _digest(body):
        raise DemoError("digest_mismatch")
    if not isinstance(signature, str):
        raise DemoError("signature_invalid")
    _verify_domain(
        domain=REQUEST_SIGN_DOMAIN,
        body=body,
        public_key_hex=body["payer_public_key"],
        signature_hex=signature,
    )
    return dict(body)


def build_service_quote(
    provider_key: Ed25519PrivateKey,
    *,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    verified_request = verify_service_request(request)
    provider_identity, provider_public_key = _public_identity_for_key(provider_key)
    if verified_request["provider_identity"] != provider_identity:
        raise DemoError("identity_mismatch")
    body = {
        "profile": DEMO_PROFILE,
        "message_type": "service_quote",
        "request_id": request["request_id"],
        "service_id": SERVICE_ID,
        "payer_identity": verified_request["payer_identity"],
        "provider_identity": provider_identity,
        "provider_public_key": provider_public_key,
        "amount": PRICE_L28,
        "asset_id": ASSET_ID,
        "created_at": CREATED_AT,
        "expires_at": EXPIRES_AT,
        "nonce": "quote-001",
    }
    _require_exact_fields(body, QUOTE_BODY_FIELDS)
    quote_id = _digest(body)
    signature = _sign_domain(provider_key, QUOTE_SIGN_DOMAIN, body)
    return {**body, "quote_id": quote_id, "signature": signature}


def verify_service_quote(
    quote: Mapping[str, Any],
    *,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    verified_request = verify_service_request(request)
    body = _artifact_body(quote, QUOTE_BODY_FIELDS)
    if body["profile"] != DEMO_PROFILE or body["message_type"] != "service_quote":
        raise DemoError("schema_invalid")
    if body["service_id"] != SERVICE_ID or body["asset_id"] != ASSET_ID:
        raise DemoError("service_invalid")
    if body["amount"] != PRICE_L28:
        raise DemoError("amount_mismatch")
    if body["request_id"] != request["request_id"]:
        raise DemoError("quote_request_mismatch")
    if body["payer_identity"] != verified_request["payer_identity"]:
        raise DemoError("identity_mismatch")
    if body["provider_identity"] != verified_request["provider_identity"]:
        raise DemoError("identity_mismatch")
    if body["provider_identity"] != public_identity(body["provider_public_key"]):
        raise DemoError("identity_mismatch")
    quote_id = quote.get("quote_id")
    signature = quote.get("signature")
    if not isinstance(quote_id, str) or quote_id != _digest(body):
        raise DemoError("digest_mismatch")
    if not isinstance(signature, str):
        raise DemoError("signature_invalid")
    _verify_domain(
        domain=QUOTE_SIGN_DOMAIN,
        body=body,
        public_key_hex=body["provider_public_key"],
        signature_hex=signature,
    )
    return dict(body)


def build_payment_authorization(
    payer_key: Ed25519PrivateKey,
    *,
    request: Mapping[str, Any],
    quote: Mapping[str, Any],
    payment_tx: Mapping[str, Any],
) -> dict[str, Any]:
    verified_request = verify_service_request(request)
    verified_quote = verify_service_quote(quote, request=request)
    payer_identity, payer_public_key = _public_identity_for_key(payer_key)
    if payer_identity != verified_request["payer_identity"]:
        raise DemoError("identity_mismatch")
    body = {
        "profile": DEMO_PROFILE,
        "message_type": "payment_authorization",
        "request_id": request["request_id"],
        "quote_id": quote["quote_id"],
        "service_id": SERVICE_ID,
        "payer_identity": payer_identity,
        "payer_public_key": payer_public_key,
        "provider_identity": verified_quote["provider_identity"],
        "amount": verified_quote["amount"],
        "asset_id": ASSET_ID,
        "payment_tx_id": payment_tx.get("id", ""),
        "created_at": CREATED_AT,
        "nonce": "payment-auth-001",
    }
    _require_exact_fields(body, PAYMENT_AUTH_BODY_FIELDS)
    authorization_id = _digest(body)
    signature = _sign_domain(payer_key, PAYMENT_AUTH_SIGN_DOMAIN, body)
    return {**body, "authorization_id": authorization_id, "signature": signature}


def verify_payment_intent_binding(
    *,
    request: Mapping[str, Any],
    quote: Mapping[str, Any],
    payment_tx: Mapping[str, Any],
    payment_authorization: Mapping[str, Any],
) -> bool:
    verified_request = verify_service_request(request)
    verified_quote = verify_service_quote(quote, request=request)
    body = _artifact_body(payment_authorization, PAYMENT_AUTH_BODY_FIELDS)
    if body["profile"] != DEMO_PROFILE or body["message_type"] != "payment_authorization":
        raise DemoError("schema_invalid")
    authorization_id = payment_authorization.get("authorization_id")
    signature = payment_authorization.get("signature")
    if not isinstance(authorization_id, str) or authorization_id != _digest(body):
        raise DemoError("digest_mismatch")
    if not isinstance(signature, str):
        raise DemoError("signature_invalid")
    if body["payer_identity"] != public_identity(body["payer_public_key"]):
        raise DemoError("identity_mismatch")
    _verify_domain(
        domain=PAYMENT_AUTH_SIGN_DOMAIN,
        body=body,
        public_key_hex=body["payer_public_key"],
        signature_hex=signature,
    )
    expected = {
        "request_id": request["request_id"],
        "quote_id": quote["quote_id"],
        "service_id": SERVICE_ID,
        "payer_identity": verified_request["payer_identity"],
        "provider_identity": verified_quote["provider_identity"],
        "amount": verified_quote["amount"],
        "asset_id": ASSET_ID,
        "payment_tx_id": payment_tx.get("id"),
    }
    for key, value in expected.items():
        if body.get(key) != value:
            raise DemoError("payment_binding_invalid")
    if payment_tx.get("id") != compute_tx_id(dict(payment_tx)):
        raise DemoError("payment_binding_invalid")
    if payment_tx.get("sender") != expected["payer_identity"]:
        raise DemoError("payment_binding_invalid")
    if payment_tx.get("receiver") != expected["provider_identity"]:
        raise DemoError("payment_binding_invalid")
    if payment_tx.get("amount") != expected["amount"]:
        raise DemoError("payment_binding_invalid")
    return True


def verify_accepted_payment(
    ledger: Any,
    *,
    request: Mapping[str, Any],
    quote: Mapping[str, Any],
    payment_tx: Mapping[str, Any],
    payment_authorization: Mapping[str, Any],
) -> bool:
    verify_payment_intent_binding(
        request=request,
        quote=quote,
        payment_tx=payment_tx,
        payment_authorization=payment_authorization,
    )
    tx_id = payment_tx["id"]
    stored = ledger.get_transaction(tx_id)
    if stored is None or stored != dict(payment_tx):
        raise DemoError("payment_not_accepted")
    if not bool(ledger._seen_tx_lookup(tx_id)):
        raise DemoError("payment_not_accepted")
    if ledger.get_balance(payment_tx["sender"]) != 72:
        raise DemoError("payment_not_accepted")
    if ledger.get_balance(payment_tx["receiver"]) != 28:
        raise DemoError("payment_not_accepted")
    if int(getattr(ledger, "total_transactions", 0)) != 1:
        raise DemoError("payment_not_accepted_exactly_once")
    return True


def structured_text_analysis(input_text: str) -> dict[str, Any]:
    text = _validate_input_text(input_text)
    words = [match.group(0).lower() for match in WORD_RE.finditer(text)]
    counts = Counter(words)
    top = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:TOP_TERM_LIMIT]
    stripped = text.strip()
    sentence_marks = len(SENTENCE_END_RE.findall(stripped))
    sentence_count = sentence_marks if sentence_marks > 0 else (1 if stripped else 0)
    return {
        "character_count": len(text),
        "word_count": len(words),
        "unique_word_count": len(counts),
        "sentence_count": sentence_count,
        "top_terms": [{"term": term, "count": count} for term, count in top],
        "input_digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def _perform_paid_service(input_text: str, *, payment_verified: bool) -> dict[str, Any]:
    if payment_verified is not True:
        raise DemoError("payment_not_verified")
    return structured_text_analysis(input_text)


def build_service_result(
    provider_key: Ed25519PrivateKey,
    *,
    request: Mapping[str, Any],
    quote: Mapping[str, Any],
    payment_tx_id: str,
    output: Mapping[str, Any],
) -> dict[str, Any]:
    verified_request = verify_service_request(request)
    verified_quote = verify_service_quote(quote, request=request)
    provider_identity, provider_public_key = _public_identity_for_key(provider_key)
    if provider_identity != verified_quote["provider_identity"]:
        raise DemoError("identity_mismatch")
    body = {
        "profile": DEMO_PROFILE,
        "message_type": "service_result",
        "request_id": request["request_id"],
        "quote_id": quote["quote_id"],
        "payment_tx_id": payment_tx_id,
        "service_id": SERVICE_ID,
        "input_digest": output.get("input_digest"),
        "output": dict(output),
        "provider_identity": provider_identity,
        "provider_public_key": provider_public_key,
        "created_at": CREATED_AT,
    }
    _require_exact_fields(body, RESULT_BODY_FIELDS)
    if body["input_digest"] != hashlib.sha256(
        verified_request["input"]["text"].encode("utf-8")
    ).hexdigest():
        raise DemoError("output_mismatch")
    result_id = _digest(body)
    signature = _sign_domain(provider_key, RESULT_SIGN_DOMAIN, body)
    return {**body, "service_result_id": result_id, "signature": signature}


def verify_service_result(
    result: Mapping[str, Any],
    *,
    request: Mapping[str, Any],
    quote: Mapping[str, Any],
    payment_tx_id: str,
) -> dict[str, Any]:
    verified_request = verify_service_request(request)
    verified_quote = verify_service_quote(quote, request=request)
    body = _artifact_body(result, RESULT_BODY_FIELDS)
    if body["profile"] != DEMO_PROFILE or body["message_type"] != "service_result":
        raise DemoError("schema_invalid")
    if body["request_id"] != request["request_id"] or body["quote_id"] != quote["quote_id"]:
        raise DemoError("digest_mismatch")
    if body["payment_tx_id"] != payment_tx_id or body["service_id"] != SERVICE_ID:
        raise DemoError("payment_binding_invalid")
    if body["provider_identity"] != verified_quote["provider_identity"]:
        raise DemoError("identity_mismatch")
    if body["provider_identity"] != public_identity(body["provider_public_key"]):
        raise DemoError("identity_mismatch")
    expected_output = structured_text_analysis(verified_request["input"]["text"])
    if body["output"] != expected_output or body["input_digest"] != expected_output["input_digest"]:
        raise DemoError("output_mismatch")
    result_id = result.get("service_result_id")
    signature = result.get("signature")
    if not isinstance(result_id, str) or result_id != _digest(body):
        raise DemoError("digest_mismatch")
    if not isinstance(signature, str):
        raise DemoError("signature_invalid")
    _verify_domain(
        domain=RESULT_SIGN_DOMAIN,
        body=body,
        public_key_hex=body["provider_public_key"],
        signature_hex=signature,
    )
    return dict(body)


def build_service_receipt(
    provider_key: Ed25519PrivateKey,
    *,
    request: Mapping[str, Any],
    quote: Mapping[str, Any],
    service_result: Mapping[str, Any],
    payment_tx_id: str,
) -> dict[str, Any]:
    verified_request = verify_service_request(request)
    verified_quote = verify_service_quote(quote, request=request)
    verify_service_result(
        service_result,
        request=request,
        quote=quote,
        payment_tx_id=payment_tx_id,
    )
    provider_identity, provider_public_key = _public_identity_for_key(provider_key)
    if provider_identity != verified_quote["provider_identity"]:
        raise DemoError("identity_mismatch")
    body = {
        "receipt_profile": "l28-two-agent-service-receipt/v0.1",
        "payer_identity": verified_request["payer_identity"],
        "provider_identity": provider_identity,
        "request_id": request["request_id"],
        "quote_id": quote["quote_id"],
        "service_result_id": service_result["service_result_id"],
        "payment_tx_id": payment_tx_id,
        "amount": verified_quote["amount"],
        "asset_id": ASSET_ID,
        "payment_verified": True,
        "service_executed": True,
        "provider_public_key": provider_public_key,
        "created_at": CREATED_AT,
    }
    _require_exact_fields(body, RECEIPT_BODY_FIELDS)
    receipt_id = _digest(body)
    signature = _sign_domain(provider_key, RECEIPT_SIGN_DOMAIN, body)
    return {**body, "receipt_id": receipt_id, "signature": signature}


def verify_service_receipt(
    receipt: Mapping[str, Any],
    *,
    request: Mapping[str, Any],
    quote: Mapping[str, Any],
    service_result: Mapping[str, Any],
    payment_tx_id: str,
) -> dict[str, Any]:
    verified_request = verify_service_request(request)
    verified_quote = verify_service_quote(quote, request=request)
    verify_service_result(
        service_result,
        request=request,
        quote=quote,
        payment_tx_id=payment_tx_id,
    )
    body = _artifact_body(receipt, RECEIPT_BODY_FIELDS)
    if body["receipt_profile"] != "l28-two-agent-service-receipt/v0.1":
        raise DemoError("schema_invalid")
    exact = {
        "payer_identity": verified_request["payer_identity"],
        "provider_identity": verified_quote["provider_identity"],
        "request_id": request["request_id"],
        "quote_id": quote["quote_id"],
        "service_result_id": service_result["service_result_id"],
        "payment_tx_id": payment_tx_id,
        "amount": PRICE_L28,
        "asset_id": ASSET_ID,
        "payment_verified": True,
        "service_executed": True,
    }
    for key, value in exact.items():
        if body.get(key) != value:
            raise DemoError("receipt_binding_invalid")
    if body["provider_identity"] != public_identity(body["provider_public_key"]):
        raise DemoError("identity_mismatch")
    receipt_id = receipt.get("receipt_id")
    signature = receipt.get("signature")
    if not isinstance(receipt_id, str) or receipt_id != _digest(body):
        raise DemoError("digest_mismatch")
    if not isinstance(signature, str):
        raise DemoError("signature_invalid")
    _verify_domain(
        domain=RECEIPT_SIGN_DOMAIN,
        body=body,
        public_key_hex=body["provider_public_key"],
        signature_hex=signature,
    )
    return dict(body)


def _candidate_binding_rejected(
    *,
    request: Mapping[str, Any],
    quote: Mapping[str, Any],
    payment_tx: Mapping[str, Any],
    payment_authorization: Mapping[str, Any],
) -> bool:
    try:
        verify_payment_intent_binding(
            request=request,
            quote=quote,
            payment_tx=payment_tx,
            payment_authorization=payment_authorization,
        )
    except DemoError:
        return True
    return False


async def _run_transaction(
    *,
    ledger: Any,
    payer_key: Ed25519PrivateKey,
    provider_key: Ed25519PrivateKey,
    wrong_key: Ed25519PrivateKey,
    input_text: str,
) -> dict[str, Any]:
    payer_identity, _payer_public_key = _public_identity_for_key(payer_key)
    provider_identity, _provider_public_key = _public_identity_for_key(provider_key)
    wrong_identity, _wrong_public_key = _public_identity_for_key(wrong_key)

    ledger.balances[payer_identity] = ALICE_INITIAL_BALANCE
    ledger.balances[provider_identity] = BOB_INITIAL_BALANCE

    payer_before = ledger.get_balance(payer_identity)
    provider_before = ledger.get_balance(provider_identity)

    request = build_service_request(
        payer_key,
        provider_identity=provider_identity,
        input_text=input_text,
    )
    quote = build_service_quote(provider_key, request=request)

    payment_tx = build_signed_transfer(
        payer_key,
        receiver=provider_identity,
        amount=TRANSFER_AMOUNT,
        timestamp=DEMO_TIMESTAMP,
        nonce=100,
    )
    payment_authorization = build_payment_authorization(
        payer_key,
        request=request,
        quote=quote,
        payment_tx=payment_tx,
    )
    verify_payment_intent_binding(
        request=request,
        quote=quote,
        payment_tx=payment_tx,
        payment_authorization=payment_authorization,
    )

    canonical_ok, payment_tx_id, canonical_reason = classify_transfer(ledger, payment_tx)
    if not canonical_ok or canonical_reason != "ok" or payment_tx_id != payment_tx["id"]:
        raise DemoError("canonical_validation_failed")
    if not await apply_transfer(ledger, payment_tx):
        raise DemoError("payment_apply_failed")

    payment_verified = verify_accepted_payment(
        ledger,
        request=request,
        quote=quote,
        payment_tx=payment_tx,
        payment_authorization=payment_authorization,
    )
    output = _perform_paid_service(input_text, payment_verified=payment_verified)
    service_result = build_service_result(
        provider_key,
        request=request,
        quote=quote,
        payment_tx_id=payment_tx_id,
        output=output,
    )
    verify_service_result(
        service_result,
        request=request,
        quote=quote,
        payment_tx_id=payment_tx_id,
    )
    receipt = build_service_receipt(
        provider_key,
        request=request,
        quote=quote,
        service_result=service_result,
        payment_tx_id=payment_tx_id,
    )
    verify_service_receipt(
        receipt,
        request=request,
        quote=quote,
        service_result=service_result,
        payment_tx_id=payment_tx_id,
    )

    payer_after = ledger.get_balance(payer_identity)
    provider_after = ledger.get_balance(provider_identity)
    if (payer_before, provider_before, payer_after, provider_after) != (100, 0, 72, 28):
        raise DemoError("balance_transition_mismatch")

    # Invalid signature: protocol validation and ledger application both fail closed.
    invalid_signature = build_signed_transfer(
        payer_key,
        receiver=provider_identity,
        amount=TRANSFER_AMOUNT,
        timestamp=DEMO_TIMESTAMP,
        nonce=101,
    )
    invalid_signature["signature"] = "00" * 64
    invalid_signature["id"] = compute_tx_id(invalid_signature)
    bad_ok, _bad_id, bad_reason = classify_transfer(ledger, invalid_signature)
    invalid_payment_rejected = (
        bad_ok is False
        and bad_reason == "bad_signature"
        and await apply_transfer(ledger, invalid_signature) is False
    )

    # Replay: exact accepted transfer cannot apply twice.
    replay_ok, _replay_id, replay_reason = classify_transfer(ledger, payment_tx)
    replay_rejected = (
        replay_ok is False
        and replay_reason == "replay"
        and await apply_transfer(ledger, payment_tx) is False
    )

    # Wrong amount: service-binding layer rejects before ledger mutation.
    wrong_amount_tx = build_signed_transfer(
        payer_key,
        receiver=provider_identity,
        amount=PRICE_L28 - 1,
        timestamp=DEMO_TIMESTAMP,
        nonce=102,
    )
    wrong_amount_auth = build_payment_authorization(
        payer_key,
        request=request,
        quote=quote,
        payment_tx=wrong_amount_tx,
    )
    wrong_amount_rejected = _candidate_binding_rejected(
        request=request,
        quote=quote,
        payment_tx=wrong_amount_tx,
        payment_authorization=wrong_amount_auth,
    )

    # Wrong payee: signed candidate is valid L28 material but not payment for this quote.
    wrong_party_tx = build_signed_transfer(
        payer_key,
        receiver=wrong_identity,
        amount=PRICE_L28,
        timestamp=DEMO_TIMESTAMP,
        nonce=103,
    )
    wrong_party_auth = build_payment_authorization(
        payer_key,
        request=request,
        quote=quote,
        payment_tx=wrong_party_tx,
    )
    wrong_party_rejected = _candidate_binding_rejected(
        request=request,
        quote=quote,
        payment_tx=wrong_party_tx,
        payment_authorization=wrong_party_auth,
    )

    # Quote mismatch: signed authorization cannot be rebound to another quote id.
    quote_mismatch_auth = dict(payment_authorization)
    quote_mismatch_auth["quote_id"] = "00" * 32
    mismatch_body = _artifact_body(quote_mismatch_auth, PAYMENT_AUTH_BODY_FIELDS)
    quote_mismatch_auth["authorization_id"] = _digest(mismatch_body)
    quote_mismatch_auth["signature"] = _sign_domain(
        payer_key,
        PAYMENT_AUTH_SIGN_DOMAIN,
        mismatch_body,
    )
    quote_mismatch_rejected = _candidate_binding_rejected(
        request=request,
        quote=quote,
        payment_tx=payment_tx,
        payment_authorization=quote_mismatch_auth,
    )

    try:
        _perform_paid_service(input_text, payment_verified=False)
    except DemoError as exc:
        unpaid_work_blocked = exc.code == "payment_not_verified"
    else:
        unpaid_work_blocked = False

    tampered_result = deepcopy(service_result)
    tampered_result["output"] = dict(tampered_result["output"])
    tampered_result["output"]["word_count"] = int(tampered_result["output"]["word_count"]) + 1
    try:
        verify_service_result(
            tampered_result,
            request=request,
            quote=quote,
            payment_tx_id=payment_tx_id,
        )
    except DemoError:
        tampered_result_rejected = True
    else:
        tampered_result_rejected = False

    tampered_receipt = deepcopy(receipt)
    tampered_receipt["signature"] = "00" * 64
    try:
        verify_service_receipt(
            tampered_receipt,
            request=request,
            quote=quote,
            service_result=service_result,
            payment_tx_id=payment_tx_id,
        )
    except DemoError:
        tampered_receipt_rejected = True
    else:
        tampered_receipt_rejected = False

    if (ledger.get_balance(payer_identity), ledger.get_balance(provider_identity)) != (72, 28):
        raise DemoError("negative_case_mutated_balance")
    if int(getattr(ledger, "total_transactions", 0)) != 1:
        raise DemoError("negative_case_mutated_ledger")
    if int(getattr(ledger, "issued_supply", 0)) != 0 or int(getattr(ledger, "mint_height", 0)) != 0:
        raise DemoError("canonical_issuance_mutated")

    if not all(
        (
            invalid_payment_rejected,
            replay_rejected,
            wrong_amount_rejected,
            wrong_party_rejected,
            quote_mismatch_rejected,
            unpaid_work_blocked,
            tampered_result_rejected,
            tampered_receipt_rejected,
        )
    ):
        raise DemoError("negative_case_failed")

    return {
        "demo_profile": DEMO_PROFILE,
        "request_created": True,
        "request_id": request["request_id"],
        "quote_created": True,
        "quote_id": quote["quote_id"],
        "quoted_amount": PRICE_L28,
        "asset_id": ASSET_ID,
        "payment_tx_id": payment_tx_id,
        "canonical_validation": "PASS",
        "payment_applied": True,
        "payment_verified": True,
        "agent_a_balance_before": payer_before,
        "agent_b_balance_before": provider_before,
        "agent_a_balance_after": payer_after,
        "agent_b_balance_after": provider_after,
        "service_id": SERVICE_ID,
        "service_executed": True,
        "service_output": output,
        "service_result_id": service_result["service_result_id"],
        "service_result_verified": True,
        "receipt_created": True,
        "receipt_id": receipt["receipt_id"],
        "receipt_verified": True,
        "invalid_payment_rejected": True,
        "replay_rejected": True,
        "wrong_amount_rejected": True,
        "wrong_party_rejected": True,
        "quote_mismatch_rejected": True,
        "unpaid_work_blocked": True,
        "tampered_result_rejected": True,
        "tampered_receipt_rejected": True,
        "canonical_history_touched": False,
        "public_network_used": False,
        "production_keys_used": False,
    }


def execute_two_agent_service_transaction(input_text: str) -> dict[str, Any]:
    """Run the complete local disposable Agent A → Agent B purchase workflow."""

    text = _validate_input_text(input_text)
    _require_protected_economics()

    payer_key = Ed25519PrivateKey.generate()
    provider_key = Ed25519PrivateKey.generate()
    wrong_key = Ed25519PrivateKey.generate()

    with tempfile.TemporaryDirectory(prefix="l28-two-agent-service-") as data_dir:
        ledger = _open_ledger(data_dir)
        result = asyncio.run(
            _run_transaction(
                ledger=ledger,
                payer_key=payer_key,
                provider_key=provider_key,
                wrong_key=wrong_key,
                input_text=text,
            )
        )

    _require_protected_economics()
    del payer_key, provider_key, wrong_key
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m coin.two_agent_service_transaction_demo",
        description="Run the isolated two-agent L28 service transaction demo.",
    )
    parser.add_argument(
        "--input",
        default="L28 enables machine payments between autonomous systems.",
        help="Text to analyze after disposable L28 payment verification.",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        result = execute_two_agent_service_transaction(args.input)
    except DemoError as exc:
        sys.stderr.write(exc.code + "\n")
        return 1
    sys.stdout.write(
        json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
