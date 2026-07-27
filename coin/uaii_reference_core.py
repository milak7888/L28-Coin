# SPDX-License-Identifier: Apache-2.0
"""UAII reference core — Foundation 58 pipeline with Foundation 60/62/63 limits.

Sole public entry: process_uaii_request.
Delegates Protocol transaction validation only to coin.tx_validation.validate_transaction.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

from . import tx_validation
from .uaii_json import (
    UaiiJsonError,
    canon_uaii,
    decode_uaii_json,
    enforce_uaii_property_names,
    serialize_uaii_response,
)
from .uaii_resource_limits import (
    LimitFailure,
    enforce_l5_canon_bytes,
    measured_l6_fallback_envelope,
    walk_enforce_l1_l4,
)

# Authorization flags for this bounded implementation milestone
execution_authorized = False
implementation_authorized = True
spend_authorized = False
ledger_mutated = False

INTERFACE_PROFILE = "l28-universal-ai-access-interface/v0.1"
UAII_CLOCK_SKEW_TOLERANCE_SECONDS = 300
MAX_TX_AMOUNT = 10_000_000_000

OPERATIONS = (
    "discover_capabilities",
    "get_protocol_status",
    "get_balance",
    "create_quote",
    "create_unsigned_payment_request",
    "validate_payment",
    "get_payment_receipt",
)

ENVELOPE_FIELDS = (
    "interface_profile",
    "operation",
    "request_id",
    "created_at",
    "expires_at",
    "nonce",
    "execution_authorized",
    "params",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
ENV_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
RESERVED_IDENTITIES = frozenset({"COINBASE", "__MINT__"})

SECRET_KEYS = frozenset(
    {
        "private_key",
        "secret_key",
        "seed",
        "seed_phrase",
        "mnemonic",
        "password",
        "passphrase",
        "credential",
        "api_key",
        "authorization_bearer",
        "signing_key",
        "keystore",
        "wallet_secret",
    }
)

QUOTE_FIELDS = (
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

PAYMENT_FIELDS = (
    "payment_request_profile",
    "quote_id",
    "payer_identity",
    "payee_identity",
    "amount",
    "currency",
    "purpose",
    "service_id",
    "service_terms_hash",
    "payment_nonce",
    "payment_expires_at",
    "quote_expires_at",
    "quote_nonce",
    "spend_authorized",
    "execution_authorized",
)

PROPOSED_TRANSFER_FIELDS = ("sender", "receiver", "amount", "timestamp", "nonce")

CORRELATION_FIELDS = (
    "correlation_profile",
    "uaii_interface_profile",
    "uaii_object_kind",
    "uaii_object_id",
    "m2m_protocol",
    "m2m_protocol_version",
    "m2m_message_id",
)
UAII_OBJECT_KINDS = frozenset(
    {"quote", "unsigned_payment_request", "payment_receipt"}
)

CAPABILITIES = (
    ("uaii.discover_capabilities", "discover_capabilities", "supported"),
    ("uaii.get_protocol_status", "get_protocol_status", "supported"),
    ("uaii.get_balance", "get_balance", "supported"),
    ("uaii.create_quote", "create_quote", "supported"),
    ("uaii.create_unsigned_payment_request", "create_unsigned_payment_request", "supported"),
    ("uaii.validate_payment", "validate_payment", "supported"),
    ("uaii.get_payment_receipt", "get_payment_receipt", "supported"),
    ("uaii.signing", "*", "forbidden"),
    ("uaii.broadcast", "*", "forbidden"),
    ("uaii.autonomous_spend", "*", "forbidden"),
    ("adapter.mcp", "*", "deferred"),
    ("adapter.rest_openapi", "*", "deferred"),
    ("adapter.python_sdk", "*", "deferred"),
    ("adapter.typescript_sdk", "*", "deferred"),
)

ADAPTER_IDS = ("mcp", "rest_openapi", "python_sdk", "typescript_sdk")


class UaiiCoreError(Exception):
    def __init__(
        self,
        code: str,
        *,
        interface_profile: str = "",
        operation: str = "",
        request_id: str = "",
    ) -> None:
        self.code = code
        self.interface_profile = interface_profile
        self.operation = operation
        self.request_id = request_id
        super().__init__(code)


def _hex_lower(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest_obj(obj: Any) -> str:
    return _hex_lower(canon_uaii(obj))


def _ordered_dict(fields: tuple[str, ...], values: Mapping[str, Any]) -> dict[str, Any]:
    return {k: values[k] for k in fields}


def _is_exact_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_keys_order(obj: Any, fields: tuple[str, ...], *, code: str = "schema_invalid") -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise UaiiCoreError(code)
    if tuple(obj.keys()) != fields:
        raise UaiiCoreError(code)
    return obj


def _scan_secrets(value: Any) -> None:
    stack: list[Any] = [value]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for key, item in cur.items():
                if key in SECRET_KEYS or ENV_KEY_RE.fullmatch(key) is not None:
                    raise UaiiCoreError("secret_material_forbidden")
                stack.append(item)
        elif isinstance(cur, list):
            stack.extend(cur)


def _check_nonce_string(value: Any, *, code: str = "nonce_invalid") -> str:
    if not isinstance(value, str):
        raise UaiiCoreError(code)
    raw = value.encode("utf-8")
    if len(raw) < 1 or len(raw) > 256 or "\0" in value:
        raise UaiiCoreError(code)
    return value


def _check_hex64(value: Any, *, code: str = "schema_invalid") -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise UaiiCoreError(code)
    return value


def _check_identity(value: Any, *, empty_code: str = "identity_invalid") -> str:
    if not isinstance(value, str) or value == "":
        raise UaiiCoreError(empty_code)
    if value in RESERVED_IDENTITIES:
        raise UaiiCoreError("reserved_identity_forbidden")
    return value


def _response(
    *,
    ok: bool,
    code: str,
    interface_profile: str,
    operation: str,
    request_id: str,
    result: dict[str, Any],
    report_id: str,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "code": code,
        "interface_profile": interface_profile,
        "operation": operation,
        "request_id": request_id,
        "result": result,
        "execution_authorized": False,
        "report_id": report_id,
        "detail": "",
    }


def _finalize_response(
    envelope: dict[str, Any],
    *,
    interface_profile: str,
    operation: str,
    request_id: str,
) -> dict[str, Any]:
    raw = serialize_uaii_response(envelope)
    if len(raw) <= 16384:
        return envelope
    fallback, _measured = measured_l6_fallback_envelope(
        interface_profile=interface_profile,
        operation=operation,
        request_id=request_id,
    )
    return fallback


def _ledger_state_id(binding: Mapping[str, Any]) -> str:
    ordered = {
        "binding_profile": binding["binding_profile"],
        "protocol_version": binding["protocol_version"],
        "currency": binding["currency"],
        "max_supply": binding["max_supply"],
        "emission_ceiling": binding["emission_ceiling"],
        "historical_mined": binding["historical_mined"],
        "canonical_height": binding["canonical_height"],
        "issued_supply": binding["issued_supply"],
        "canonical_issuance_ready": binding["canonical_issuance_ready"],
        "accepted_tx_count": binding["accepted_tx_count"],
    }
    material = b"L28-UAII-V0.1-LEDGER-STATE\x00" + canon_uaii(ordered)
    return _hex_lower(material)


def uaii_m2m_correlation_id(corr: Mapping[str, Any]) -> str:
    """Foundation 57 §7.4 / F58 §7.2 correlation id (calculation only; not emitted)."""
    if not isinstance(corr, Mapping) or tuple(corr.keys()) != CORRELATION_FIELDS:
        raise UaiiCoreError("schema_invalid")
    if corr["correlation_profile"] != "l28-uaii-m2m-correlation/v0.1":
        raise UaiiCoreError("schema_invalid")
    if corr["uaii_interface_profile"] != INTERFACE_PROFILE:
        raise UaiiCoreError("schema_invalid")
    if corr["uaii_object_kind"] not in UAII_OBJECT_KINDS:
        raise UaiiCoreError("uaii_m2m_mapping_mismatch")
    if not isinstance(corr["uaii_object_id"], str) or HEX64_RE.fullmatch(corr["uaii_object_id"]) is None:
        raise UaiiCoreError("schema_invalid")
    if corr["m2m_protocol"] != "L28-M2M":
        raise UaiiCoreError("schema_invalid")
    if corr["m2m_protocol_version"] != "0.1":
        raise UaiiCoreError("schema_invalid")
    if not isinstance(corr["m2m_message_id"], str) or HEX64_RE.fullmatch(corr["m2m_message_id"]) is None:
        raise UaiiCoreError("schema_invalid")
    if corr["m2m_message_id"] == corr["uaii_object_id"]:
        raise UaiiCoreError("uaii_m2m_id_collision")
    ordered = {k: corr[k] for k in CORRELATION_FIELDS}
    return _hex_lower(b"L28-UAII-V0.1-M2M-CORRELATION\x00" + canon_uaii(ordered))


def _replay_key(*, operation: str, nonce: str) -> str:
    material = {
        "replay_profile": "l28-uaii-replay/v0.1",
        "interface_profile": INTERFACE_PROFILE,
        "operation": operation,
        "nonce": nonce,
    }
    return _hex_lower(b"L28-UAII-V0.1-REPLAY\x00" + canon_uaii(material))


def _ctx_get(context: Any, name: str) -> Any:
    if context is None:
        return None
    if isinstance(context, Mapping):
        return context.get(name)
    return getattr(context, name, None)


def _require_t_eval(context: Any) -> int:
    t_eval = _ctx_get(context, "t_eval")
    if not _is_exact_int(t_eval):
        raise UaiiCoreError("internal_error")
    return int(t_eval)


def _envelope_time_checks(request: Mapping[str, Any], t_eval: int) -> None:
    created_at = request["created_at"]
    expires_at = request["expires_at"]
    if created_at > t_eval + UAII_CLOCK_SKEW_TOLERANCE_SECONDS:
        raise UaiiCoreError("request_not_yet_valid")
    if t_eval > expires_at + UAII_CLOCK_SKEW_TOLERANCE_SECONDS:
        raise UaiiCoreError("request_expired")


def _envelope_replay_check(context: Any, *, operation: str, nonce: str, expires_at: int, t_eval: int) -> None:
    replay_state = _ctx_get(context, "replay_state")
    if replay_state is None:
        raise UaiiCoreError("replay_state_unavailable")
    key = _replay_key(operation=operation, nonce=nonce)
    retention_deadline = expires_at + UAII_CLOCK_SKEW_TOLERANCE_SECONDS
    if isinstance(replay_state, Mapping):
        lookup = replay_state.get("lookup")
    else:
        lookup = getattr(replay_state, "lookup", None)
    if not callable(lookup):
        raise UaiiCoreError("replay_state_unavailable")
    status = lookup(key)
    if status == "unavailable" or status is None:
        raise UaiiCoreError("replay_state_unavailable")
    if status == "present" and t_eval <= retention_deadline:
        raise UaiiCoreError("nonce_replay")
    if status not in ("absent", "present", "evicted"):
        raise UaiiCoreError("replay_state_unavailable")


def _read_ledger_binding(context: Any) -> dict[str, Any]:
    ledger_state = _ctx_get(context, "ledger_state")
    if ledger_state is None:
        raise UaiiCoreError("ledger_state_unavailable")
    if isinstance(ledger_state, Mapping):
        reader = ledger_state.get("read_binding")
    else:
        reader = getattr(ledger_state, "read_binding", None)
    if not callable(reader):
        raise UaiiCoreError("ledger_state_unavailable")
    try:
        raw = reader()
    except Exception as exc:
        raise UaiiCoreError("ledger_state_unavailable") from exc
    if not isinstance(raw, Mapping):
        raise UaiiCoreError("ledger_state_unavailable")
    binding = {
        "binding_profile": "l28-uaii-ledger-state-binding/v0.1",
        "protocol_version": "1.0.0",
        "currency": "L28",
        "max_supply": 28000000,
        "emission_ceiling": 11130000,
        "historical_mined": 2824584,
        "canonical_height": raw.get("canonical_height"),
        "issued_supply": raw.get("issued_supply"),
        "canonical_issuance_ready": raw.get("canonical_issuance_ready"),
        "accepted_tx_count": raw.get("accepted_tx_count"),
    }
    if not _is_exact_int(binding["canonical_height"]) or binding["canonical_height"] < 0:
        raise UaiiCoreError("ledger_state_unavailable")
    if not _is_exact_int(binding["issued_supply"]) or binding["issued_supply"] < 0:
        raise UaiiCoreError("ledger_state_unavailable")
    if binding["canonical_issuance_ready"] is not True:
        raise UaiiCoreError("ledger_state_unavailable")
    if not _is_exact_int(binding["accepted_tx_count"]) or binding["accepted_tx_count"] < 0:
        raise UaiiCoreError("ledger_state_unavailable")
    return binding


def _read_balance(context: Any, address: str) -> int:
    ledger_state = _ctx_get(context, "ledger_state")
    if ledger_state is None:
        raise UaiiCoreError("ledger_state_unavailable")
    if isinstance(ledger_state, Mapping):
        getter = ledger_state.get("get_balance")
    else:
        getter = getattr(ledger_state, "get_balance", None)
    if not callable(getter):
        raise UaiiCoreError("ledger_state_unavailable")
    try:
        bal = getter(address)
    except Exception as exc:
        raise UaiiCoreError("ledger_state_unavailable") from exc
    if not _is_exact_int(bal) or bal < 0:
        raise UaiiCoreError("ledger_state_unavailable")
    return int(bal)


def _validate_quote_object(quote: Any) -> dict[str, Any]:
    q = _require_keys_order(quote, QUOTE_FIELDS)
    if q["quote_profile"] != "l28-uaii-quote/v0.1":
        raise UaiiCoreError("schema_invalid")
    if not isinstance(q["service_params"], dict) or not isinstance(q["service_terms"], dict):
        raise UaiiCoreError("schema_invalid")
    if q["currency"] != "L28":
        raise UaiiCoreError("schema_invalid")
    if q["rejectable"] is not True:
        raise UaiiCoreError("schema_invalid")
    if q["spend_authorized"] is not False or q["execution_authorized"] is not False:
        raise UaiiCoreError("schema_invalid")
    if not _is_exact_int(q["amount"]) or not _is_exact_int(q["max_amount"]):
        raise UaiiCoreError("schema_invalid")
    if not _is_exact_int(q["quote_expires_at"]):
        raise UaiiCoreError("schema_invalid")
    terms_hash = _digest_obj(q["service_terms"])
    if q["service_terms_hash"] != terms_hash:
        raise UaiiCoreError("schema_invalid")
    return q


def _validate_payment_object(payment: Any) -> dict[str, Any]:
    p = _require_keys_order(payment, PAYMENT_FIELDS)
    if p["payment_request_profile"] != "l28-uaii-unsigned-payment-request/v0.1":
        raise UaiiCoreError("schema_invalid")
    if p["currency"] != "L28":
        raise UaiiCoreError("schema_invalid")
    if p["spend_authorized"] is not False or p["execution_authorized"] is not False:
        raise UaiiCoreError("schema_invalid")
    for key in ("amount", "payment_expires_at", "quote_expires_at"):
        if not _is_exact_int(p[key]):
            raise UaiiCoreError("schema_invalid")
    return p


def _op_discover_capabilities(params: Mapping[str, Any], _context: Any) -> tuple[str, dict[str, Any]]:
    p = _require_keys_order(params, ("include_adapter_declarations",))
    if not isinstance(p["include_adapter_declarations"], bool):
        raise UaiiCoreError("schema_invalid")
    caps = [
        {
            "capability_id": cid,
            "operation": op,
            "status": status,
            "description": cid,
        }
        for cid, op, status in CAPABILITIES
    ]
    adapters: list[dict[str, Any]] = []
    if p["include_adapter_declarations"]:
        adapters = [
            {
                "adapter_id": aid,
                "adapter_status": "deferred",
                "canonical_profile": INTERFACE_PROFILE,
                "must_preserve_field_order": True,
                "must_preserve_codes": True,
                "must_delegate_settlement_validation": True,
                "may_override_economics": False,
            }
            for aid in ADAPTER_IDS
        ]
    result = {
        "interface_profile": INTERFACE_PROFILE,
        "protocol_version": "1.0.0",
        "m2m_protocol": "L28-M2M",
        "m2m_protocol_version": "0.1",
        "currency": "L28",
        "operations": list(OPERATIONS),
        "capabilities": caps,
        "adapter_declarations": adapters,
        "execution_authorized": False,
        "signing_supported": False,
        "broadcast_supported": False,
        "autonomous_spend_supported": False,
    }
    return "capabilities_ok", result


def _op_get_protocol_status(params: Mapping[str, Any], _context: Any) -> tuple[str, dict[str, Any]]:
    _require_keys_order(params, ())
    result = {
        "protocol_version": "1.0.0",
        "protocol_status": "FROZEN",
        "max_supply": 28000000,
        "emission_ceiling": 11130000,
        "historical_mined": 2824584,
        "halving_interval": 210000,
        "max_coinbase_reward": 28,
        "reward_schedule": [28, 14, 7, 3, 1],
        "currency": "L28",
        "architecture": "blockless_ledger",
        "validation_authority": "coin.tx_validation.validate_transaction",
        "execution_authorized": False,
    }
    return "protocol_status_ok", result


def _op_get_balance(params: Mapping[str, Any], context: Any) -> tuple[str, dict[str, Any]]:
    p = _require_keys_order(params, ("address", "require_canonical_height"))
    address = p["address"]
    if not isinstance(address, str) or address == "":
        raise UaiiCoreError("address_invalid")
    if address in RESERVED_IDENTITIES:
        raise UaiiCoreError("reserved_identity_forbidden")
    if not isinstance(p["require_canonical_height"], bool):
        raise UaiiCoreError("schema_invalid")
    binding = _read_ledger_binding(context)
    if p["require_canonical_height"] is True and not _is_exact_int(binding["canonical_height"]):
        raise UaiiCoreError("canonical_height_unavailable")
    balance = _read_balance(context, address)
    result = {
        "address": address,
        "balance": balance,
        "currency": "L28",
        "canonical_height": binding["canonical_height"],
        "ledger_state_id": _ledger_state_id(binding),
        "execution_authorized": False,
    }
    return "", result  # get_balance success code waived


def _op_create_quote(params: Mapping[str, Any], request: Mapping[str, Any], _context: Any) -> tuple[str, dict[str, Any]]:
    fields = (
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
    )
    p = _require_keys_order(params, fields)
    payer = _check_identity(p["payer_identity"])
    payee = _check_identity(p["payee_identity"])
    if payer == payee:
        raise UaiiCoreError("quote_party_invalid")
    if not isinstance(p["service_id"], str) or p["service_id"] == "":
        raise UaiiCoreError("service_id_invalid")
    if not isinstance(p["service_params"], dict):
        raise UaiiCoreError("schema_invalid")
    if not _is_exact_int(p["amount"]) or p["amount"] <= 0 or p["amount"] > MAX_TX_AMOUNT:
        raise UaiiCoreError("amount_invalid")
    if p["currency"] != "L28":
        raise UaiiCoreError("currency_invalid")
    if not isinstance(p["purpose"], str) or p["purpose"] == "":
        raise UaiiCoreError("schema_invalid")
    if not _is_exact_int(p["quote_expires_at"]):
        raise UaiiCoreError("quote_expiration_invalid")
    if not (p["quote_expires_at"] > request["created_at"] and p["quote_expires_at"] <= request["expires_at"]):
        raise UaiiCoreError("quote_expiration_invalid")
    quote_nonce = _check_nonce_string(p["quote_nonce"])
    if not _is_exact_int(p["max_amount"]) or p["max_amount"] <= 0 or p["max_amount"] < p["amount"]:
        raise UaiiCoreError("amount_invalid")
    if p["rejectable"] is not True:
        raise UaiiCoreError("rejectable_invalid")
    if not isinstance(p["service_terms"], dict):
        raise UaiiCoreError("schema_invalid")
    terms_hash = _digest_obj(p["service_terms"])
    quote = {
        "quote_profile": "l28-uaii-quote/v0.1",
        "payer_identity": payer,
        "payee_identity": payee,
        "service_id": p["service_id"],
        "service_params": p["service_params"],
        "amount": p["amount"],
        "currency": "L28",
        "purpose": p["purpose"],
        "quote_expires_at": p["quote_expires_at"],
        "quote_nonce": quote_nonce,
        "max_amount": p["max_amount"],
        "rejectable": True,
        "service_terms": p["service_terms"],
        "service_terms_hash": terms_hash,
        "spend_authorized": False,
        "execution_authorized": False,
    }
    quote_id = _digest_obj(quote)
    result = {
        "quote": quote,
        "quote_id": quote_id,
        "execution_authorized": False,
        "spend_authorized": False,
    }
    return "quote_created", result


def _op_create_unsigned_payment_request(
    params: Mapping[str, Any], request: Mapping[str, Any], context: Any
) -> tuple[str, dict[str, Any]]:
    fields = (
        "quote",
        "quote_id",
        "payer_identity",
        "payee_identity",
        "amount",
        "currency",
        "purpose",
        "service_id",
        "payment_nonce",
        "payment_expires_at",
    )
    p = _require_keys_order(params, fields)
    quote = _validate_quote_object(p["quote"])
    quote_id = _check_hex64(p["quote_id"])
    if quote_id != _digest_obj(quote):
        raise UaiiCoreError("quote_binding_invalid")
    if p["payer_identity"] != quote["payer_identity"]:
        raise UaiiCoreError("quote_binding_invalid")
    if p["payee_identity"] != quote["payee_identity"]:
        raise UaiiCoreError("quote_binding_invalid")
    if p["amount"] != quote["amount"]:
        raise UaiiCoreError("quote_binding_invalid")
    if p["currency"] != "L28":
        raise UaiiCoreError("currency_invalid")
    if p["currency"] != quote["currency"]:
        raise UaiiCoreError("quote_binding_invalid")
    if p["purpose"] != quote["purpose"] or p["service_id"] != quote["service_id"]:
        raise UaiiCoreError("quote_binding_invalid")
    t_eval = _require_t_eval(context)
    if t_eval >= quote["quote_expires_at"]:
        raise UaiiCoreError("quote_expired")
    payment_nonce = _check_nonce_string(p["payment_nonce"])
    if payment_nonce == quote["quote_nonce"]:
        raise UaiiCoreError("nonce_reuse_invalid")
    if not _is_exact_int(p["payment_expires_at"]):
        raise UaiiCoreError("payment_expiration_invalid")
    pe = p["payment_expires_at"]
    if not (
        pe > request["created_at"]
        and pe <= request["expires_at"]
        and pe <= quote["quote_expires_at"]
    ):
        raise UaiiCoreError("payment_expiration_invalid")
    payment = {
        "payment_request_profile": "l28-uaii-unsigned-payment-request/v0.1",
        "quote_id": quote_id,
        "payer_identity": quote["payer_identity"],
        "payee_identity": quote["payee_identity"],
        "amount": quote["amount"],
        "currency": "L28",
        "purpose": quote["purpose"],
        "service_id": quote["service_id"],
        "service_terms_hash": quote["service_terms_hash"],
        "payment_nonce": payment_nonce,
        "payment_expires_at": pe,
        "quote_expires_at": quote["quote_expires_at"],
        "quote_nonce": quote["quote_nonce"],
        "spend_authorized": False,
        "execution_authorized": False,
    }
    payment_request_id = _digest_obj(payment)
    result = {
        "unsigned_payment_request": payment,
        "payment_request_id": payment_request_id,
        "execution_authorized": False,
        "spend_authorized": False,
    }
    return "unsigned_payment_request_created", result


def _delegate_validate_transaction(context: Any, transfer: Mapping[str, Any]) -> tuple[bool, str]:
    protocol_validate = _ctx_get(context, "protocol_validate")
    if protocol_validate is None:
        raise UaiiCoreError("payment_validation_failed")
    if isinstance(protocol_validate, Mapping):
        fn = protocol_validate.get("validate")
        balance_lookup = protocol_validate.get("current_balance_lookup")
        seen_lookup = protocol_validate.get("seen_tx_lookup")
    else:
        fn = getattr(protocol_validate, "validate", None)
        balance_lookup = getattr(protocol_validate, "current_balance_lookup", None)
        seen_lookup = getattr(protocol_validate, "seen_tx_lookup", None)
    # Always use validate_transaction semantics; allow thin wrappers that call it.
    if callable(fn):
        try:
            ok, tx_id, _reason = fn(dict(transfer))
        except Exception as exc:
            raise UaiiCoreError("payment_validation_failed") from exc
        return bool(ok), str(tx_id or "")
    if not callable(balance_lookup) or not callable(seen_lookup):
        raise UaiiCoreError("payment_validation_failed")
    ok, tx_id, _reason = tx_validation.validate_transaction(
        dict(transfer),
        policy=tx_validation.TxPolicy(),
        current_balance_lookup=balance_lookup,
        seen_tx_lookup=seen_lookup,
        verify_signature=None,
    )
    return bool(ok), str(tx_id or "")


def _op_validate_payment(params: Mapping[str, Any], context: Any) -> tuple[str, dict[str, Any]]:
    fields = (
        "quote",
        "quote_id",
        "unsigned_payment_request",
        "payment_request_id",
        "proposed_transfer",
        "check_ledger_balance",
    )
    p = _require_keys_order(params, fields)
    quote = _validate_quote_object(p["quote"])
    quote_id = _check_hex64(p["quote_id"])
    if quote_id != _digest_obj(quote):
        raise UaiiCoreError("quote_binding_invalid")
    payment = _validate_payment_object(p["unsigned_payment_request"])
    payment_request_id = _check_hex64(p["payment_request_id"])
    if payment_request_id != _digest_obj(payment):
        raise UaiiCoreError("payment_binding_invalid")
    if payment["quote_id"] != quote_id:
        raise UaiiCoreError("payment_binding_invalid")
    for key in ("payer_identity", "payee_identity", "amount", "currency", "purpose", "service_id"):
        if payment[key] != quote[key if key != "currency" else "currency"]:
            raise UaiiCoreError("quote_binding_invalid")
    if payment["service_terms_hash"] != quote["service_terms_hash"]:
        raise UaiiCoreError("payment_binding_invalid")
    if payment["quote_expires_at"] != quote["quote_expires_at"] or payment["quote_nonce"] != quote["quote_nonce"]:
        raise UaiiCoreError("payment_binding_invalid")
    t_eval = _require_t_eval(context)
    if t_eval >= quote["quote_expires_at"]:
        raise UaiiCoreError("quote_expired")
    if t_eval >= payment["payment_expires_at"]:
        raise UaiiCoreError("payment_expired")
    if payment["payment_nonce"] == quote["quote_nonce"]:
        raise UaiiCoreError("nonce_reuse_invalid")
    _check_nonce_string(payment["payment_nonce"])
    if not isinstance(p["check_ledger_balance"], bool):
        raise UaiiCoreError("schema_invalid")
    proposed = p["proposed_transfer"]
    invoked = False
    vt_ok = False
    proposed_tx_id = ""
    if not isinstance(proposed, dict):
        raise UaiiCoreError("schema_invalid")
    if proposed:
        pt = _require_keys_order(proposed, PROPOSED_TRANSFER_FIELDS)
        if pt["sender"] != payment["payer_identity"] or pt["receiver"] != payment["payee_identity"]:
            raise UaiiCoreError("payment_binding_invalid")
        if pt["amount"] != payment["amount"]:
            raise UaiiCoreError("payment_binding_invalid")
        if not _is_exact_int(pt["timestamp"]) or not _is_exact_int(pt["nonce"]):
            raise UaiiCoreError("schema_invalid")
        invoked = True
        ok, proposed_tx_id = _delegate_validate_transaction(context, pt)
        vt_ok = ok
        if not ok:
            raise UaiiCoreError("payment_validation_failed")
    if p["check_ledger_balance"] is True:
        bal = _read_balance(context, payment["payer_identity"])
        if bal < payment["amount"]:
            raise UaiiCoreError("insufficient_balance")
    result = {
        "payment_valid": True,
        "quote_id": quote_id,
        "payment_request_id": payment_request_id,
        "payer_identity": payment["payer_identity"],
        "payee_identity": payment["payee_identity"],
        "amount": payment["amount"],
        "currency": "L28",
        "validate_transaction_invoked": invoked,
        "validate_transaction_ok": vt_ok,
        "proposed_tx_id": proposed_tx_id,
        "ledger_mutated": False,
        "execution_authorized": False,
        "spend_authorized": False,
    }
    return "payment_validation_ok", result


def _op_get_payment_receipt(params: Mapping[str, Any], _context: Any) -> tuple[str, dict[str, Any]]:
    fields = (
        "quote_id",
        "payment_request_id",
        "payer_identity",
        "payee_identity",
        "amount",
        "currency",
        "service_id",
        "service_result_hash",
        "l28_tx_id",
        "l28_sender",
        "l28_receiver",
        "l28_amount",
        "l28_timestamp",
        "verification_status",
        "completed_at",
        "receipt_nonce",
    )
    p = _require_keys_order(params, fields)
    quote_id = _check_hex64(p["quote_id"])
    payment_request_id = _check_hex64(p["payment_request_id"])
    payer = _check_identity(p["payer_identity"])
    payee = _check_identity(p["payee_identity"])
    if not _is_exact_int(p["amount"]) or p["amount"] <= 0 or p["amount"] > MAX_TX_AMOUNT:
        raise UaiiCoreError("amount_invalid")
    if p["currency"] != "L28":
        raise UaiiCoreError("currency_invalid")
    if not isinstance(p["service_id"], str) or p["service_id"] == "":
        raise UaiiCoreError("service_id_invalid")
    service_result_hash = _check_hex64(p["service_result_hash"])
    l28_tx_id = _check_hex64(p["l28_tx_id"], code="settlement_citation_invalid")
    if p["l28_sender"] != payer or p["l28_receiver"] != payee:
        raise UaiiCoreError("receipt_binding_invalid")
    if p["l28_amount"] != p["amount"]:
        raise UaiiCoreError("receipt_binding_invalid")
    if not _is_exact_int(p["l28_timestamp"]):
        raise UaiiCoreError("settlement_citation_invalid")
    if p["verification_status"] != "verified":
        raise UaiiCoreError("verification_status_invalid")
    if not _is_exact_int(p["completed_at"]):
        raise UaiiCoreError("schema_invalid")
    receipt_nonce = _check_nonce_string(p["receipt_nonce"])
    receipt = {
        "receipt_profile": "l28-uaii-payment-receipt/v0.1",
        "quote_id": quote_id,
        "payment_request_id": payment_request_id,
        "payer_identity": payer,
        "payee_identity": payee,
        "amount": p["amount"],
        "currency": "L28",
        "service_id": p["service_id"],
        "service_result_hash": service_result_hash,
        "l28_tx_id": l28_tx_id,
        "l28_sender": payer,
        "l28_receiver": payee,
        "l28_amount": p["amount"],
        "l28_timestamp": p["l28_timestamp"],
        "verification_status": "verified",
        "completed_at": p["completed_at"],
        "receipt_nonce": receipt_nonce,
        "completion_assertion": "provider_asserted_complete",
        "execution_authorized": False,
    }
    receipt_id = _digest_obj(receipt)
    result = {
        "receipt": receipt,
        "receipt_id": receipt_id,
        "execution_authorized": False,
    }
    return "payment_receipt_ok", result


def process_uaii_request(request_bytes: str | bytes, context: Any = None) -> dict[str, Any]:
    """Authoritative Foundation 58 UAII request processor."""
    interface_profile = ""
    operation = ""
    request_id = ""
    try:
        # Outer 1–3 (+ Unicode scalar validation inside decode)
        request = decode_uaii_json(request_bytes)

        # Post-Outer-3 / pre-Outer-4: L1–L4
        try:
            walk_enforce_l1_l4(request)
        except LimitFailure as exc:
            raise UaiiCoreError(exc.code) from exc
        except UaiiJsonError as exc:
            raise UaiiCoreError(exc.code) from exc

        # Outer 4 — secrets
        _scan_secrets(request)

        # Foundation 56 §3.2 property-name grammar (after secrets; before profile/schema)
        try:
            enforce_uaii_property_names(request)
        except UaiiJsonError as exc:
            raise UaiiCoreError(exc.code) from exc

        # Outer 5–8 — profile / operation / envelope schema / nonce grammar
        if not isinstance(request.get("interface_profile"), str):
            raise UaiiCoreError("interface_profile_unsupported")
        interface_profile = request["interface_profile"]
        if interface_profile != INTERFACE_PROFILE:
            raise UaiiCoreError(
                "interface_profile_unsupported",
                interface_profile=interface_profile,
            )

        if not isinstance(request.get("operation"), str):
            raise UaiiCoreError("operation_unsupported", interface_profile=interface_profile)
        operation = request["operation"]
        if operation not in OPERATIONS:
            raise UaiiCoreError(
                "operation_unsupported",
                interface_profile=interface_profile,
                operation=operation,
            )

        env = _require_keys_order(request, ENVELOPE_FIELDS)
        if env["execution_authorized"] is not False:
            raise UaiiCoreError(
                "execution_authorized_invalid",
                interface_profile=interface_profile,
                operation=operation,
            )
        if not isinstance(env["request_id"], str) or HEX64_RE.fullmatch(env["request_id"]) is None:
            raise UaiiCoreError(
                "schema_invalid",
                interface_profile=interface_profile,
                operation=operation,
            )
        request_id = env["request_id"]
        if not _is_exact_int(env["created_at"]) or env["created_at"] < 0:
            raise UaiiCoreError(
                "schema_invalid",
                interface_profile=interface_profile,
                operation=operation,
                request_id=request_id,
            )
        if not _is_exact_int(env["expires_at"]) or env["expires_at"] <= env["created_at"]:
            raise UaiiCoreError(
                "schema_invalid",
                interface_profile=interface_profile,
                operation=operation,
                request_id=request_id,
            )
        _check_nonce_string(env["nonce"])
        if not isinstance(env["params"], dict):
            raise UaiiCoreError(
                "schema_invalid",
                interface_profile=interface_profile,
                operation=operation,
                request_id=request_id,
            )

        # Outer 9–10 — CanonUaii + L5
        try:
            canon = canon_uaii(request)
            enforce_l5_canon_bytes(canon)
        except LimitFailure as exc:
            raise UaiiCoreError(
                exc.code,
                interface_profile=interface_profile,
                operation=operation,
                request_id=request_id,
            ) from exc
        except UaiiJsonError as exc:
            raise UaiiCoreError(
                exc.code,
                interface_profile=interface_profile,
                operation=operation,
                request_id=request_id,
            ) from exc

        # Outer 13–14 — time + replay (envelope)
        t_eval = _require_t_eval(context)
        _envelope_time_checks(request, t_eval)
        _envelope_replay_check(
            context,
            operation=operation,
            nonce=env["nonce"],
            expires_at=env["expires_at"],
            t_eval=t_eval,
        )

        # Outer 11–16 — operation-local
        params = env["params"]
        if operation == "discover_capabilities":
            code, result = _op_discover_capabilities(params, context)
        elif operation == "get_protocol_status":
            code, result = _op_get_protocol_status(params, context)
        elif operation == "get_balance":
            code, result = _op_get_balance(params, context)
        elif operation == "create_quote":
            code, result = _op_create_quote(params, request, context)
        elif operation == "create_unsigned_payment_request":
            code, result = _op_create_unsigned_payment_request(params, request, context)
        elif operation == "validate_payment":
            code, result = _op_validate_payment(params, context)
        elif operation == "get_payment_receipt":
            code, result = _op_get_payment_receipt(params, context)
        else:
            raise UaiiCoreError("operation_unsupported", interface_profile=interface_profile)

        report_id = _hex_lower(canon)
        envelope = _response(
            ok=True,
            code=code,
            interface_profile=INTERFACE_PROFILE,
            operation=operation,
            request_id=request_id,
            result=result,
            report_id=report_id,
        )
        return _finalize_response(
            envelope,
            interface_profile=INTERFACE_PROFILE,
            operation=operation,
            request_id=request_id,
        )

    except UaiiJsonError as exc:
        fail = _response(
            ok=False,
            code=exc.code,
            interface_profile=interface_profile,
            operation=operation,
            request_id=request_id,
            result={},
            report_id="",
        )
        return _finalize_response(
            fail,
            interface_profile=interface_profile,
            operation=operation,
            request_id=request_id,
        )
    except LimitFailure as exc:
        fail = _response(
            ok=False,
            code=exc.code,
            interface_profile=interface_profile,
            operation=operation,
            request_id=request_id,
            result={},
            report_id="",
        )
        return _finalize_response(
            fail,
            interface_profile=interface_profile,
            operation=operation,
            request_id=request_id,
        )
    except UaiiCoreError as exc:
        ip = exc.interface_profile or interface_profile
        op = exc.operation or operation
        rid = exc.request_id or request_id
        if exc.code == "interface_profile_unsupported" and ip and ip != INTERFACE_PROFILE:
            # echo recovered typed profile string
            pass
        elif exc.code != "interface_profile_unsupported" and ip == INTERFACE_PROFILE:
            pass
        fail = _response(
            ok=False,
            code=exc.code,
            interface_profile=ip if ip else "",
            operation=op if op else "",
            request_id=rid if rid else "",
            result={},
            report_id="",
        )
        return _finalize_response(fail, interface_profile=ip, operation=op, request_id=rid)
    except Exception:
        fail = _response(
            ok=False,
            code="internal_error",
            interface_profile=interface_profile if interface_profile == INTERFACE_PROFILE else interface_profile,
            operation=operation,
            request_id=request_id,
            result={},
            report_id="",
        )
        return _finalize_response(
            fail,
            interface_profile=interface_profile,
            operation=operation,
            request_id=request_id,
        )
