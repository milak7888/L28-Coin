# SPDX-License-Identifier: Apache-2.0
"""
L28 M2M offline exchange transcript validator (Foundation 6).

Verifies ordered sequences of already-signed M2M envelopes.
Does not sign, spend, submit transactions, query a ledger, or operate a network.
Retains no persistent replay state after returning.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Union

from coin.m2m_verifier import (
    M2MVerifyError,
    parse_m2m_json_value,
    payload_hash_for,
    verify_envelope,
    verify_settlement_citation,
)

MAX_TRANSCRIPT_MESSAGES = 64

TERMINAL_STATES = frozenset(
    {"completed", "rejected", "expired", "cancelled", "failed", "disputed"}
)
NONTERMINAL_STATES = frozenset({"requested", "quoted", "authorized", "settled"})

FAILURE_CODES = frozenset(
    {
        "quote_rejected",
        "quote_expired",
        "authorization_expired",
        "invalid_signature",
        "payload_invalid",
        "settlement_unverified",
        "service_incomplete",
        "duplicate_message",
        "chain_break",
        "cancelled_by_sender",
        "internal_error",
    }
)

STABLE_CODES = frozenset(
    {
        "ok",
        "invalid_json",
        "duplicate_key",
        "transcript_not_array",
        "empty_transcript",
        "transcript_too_large",
        "transcript_element_not_object",
        "envelope_verification_failed",
        "exchange_id_mismatch",
        "first_message_not_request",
        "invalid_first_previous_message",
        "message_chain_broken",
        "duplicate_message_id",
        "duplicate_nonce",
        "timestamp_regression",
        "prior_message_expired",
        "participant_mismatch",
        "role_mismatch",
        "invalid_transition",
        "message_after_terminal",
        "incomplete_transcript",
        "invalid_terminal_state",
        "unauthorized_terminal_transition",
        "quote_reference_mismatch",
        "amount_mismatch",
        "service_terms_mismatch",
        "settlement_participant_mismatch",
        "settlement_citation_invalid",
        "receipt_reference_mismatch",
    }
)


class TranscriptError(Exception):
    """Internal fail-closed transcript error with a stable public code."""

    def __init__(
        self,
        code: str,
        *,
        failed_index: Optional[int] = None,
        envelope_code: Optional[str] = None,
        state: Optional[str] = None,
        exchange_id: Optional[str] = None,
        verified_messages: int = 0,
        settlement_transaction_id: Optional[str] = None,
    ) -> None:
        if code not in STABLE_CODES:
            code = "invalid_json"
        self.code = code
        self.failed_index = failed_index
        self.envelope_code = envelope_code
        self.state = state
        self.exchange_id = exchange_id
        self.verified_messages = verified_messages
        self.settlement_transaction_id = settlement_transaction_id
        super().__init__(code)


@dataclass(frozen=True)
class TranscriptResult:
    ok: bool
    code: str
    state: Optional[str] = None
    exchange_id: Optional[str] = None
    verified_messages: int = 0
    failed_index: Optional[int] = None
    envelope_code: Optional[str] = None
    settlement_transaction_id: Optional[str] = None


def _fail(
    code: str,
    *,
    failed_index: Optional[int] = None,
    envelope_code: Optional[str] = None,
    state: Optional[str] = None,
    exchange_id: Optional[str] = None,
    verified_messages: int = 0,
    settlement_transaction_id: Optional[str] = None,
) -> TranscriptResult:
    if code not in STABLE_CODES:
        code = "invalid_json"
    return TranscriptResult(
        ok=False,
        code=code,
        state=state,
        exchange_id=exchange_id,
        verified_messages=verified_messages,
        failed_index=failed_index,
        envelope_code=envelope_code,
        settlement_transaction_id=settlement_transaction_id,
    )


def _ok(
    *,
    state: str,
    exchange_id: str,
    verified_messages: int,
    settlement_transaction_id: Optional[str] = None,
) -> TranscriptResult:
    return TranscriptResult(
        ok=True,
        code="ok",
        state=state,
        exchange_id=exchange_id,
        verified_messages=verified_messages,
        failed_index=None,
        envelope_code=None,
        settlement_transaction_id=settlement_transaction_id,
    )


def _party_key(env: Mapping[str, Any], side: str) -> str:
    pk = env.get(f"{side}_public_key")
    if isinstance(pk, str) and pk:
        return f"pk:{pk}"
    ident = env.get(f"{side}_identity")
    if isinstance(ident, str) and ident:
        return f"id:{ident}"
    raise TranscriptError("participant_mismatch")


def _exact_int(value: Any) -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise TranscriptError("invalid_transition")
    return value


def _resolve_failure_terminal(
    *,
    current: str,
    sender_role: str,
    failure_code: str,
) -> str:
    """
    Map authenticated failure_notice onto a documented terminal state.

    Directions follow docs/m2m/state_machine.md party/transition tables.
    """
    if failure_code not in FAILURE_CODES:
        raise TranscriptError("invalid_terminal_state")

    if current == "requested":
        if failure_code == "cancelled_by_sender" and sender_role == "requester":
            return "cancelled"
        if failure_code == "quote_rejected" and sender_role == "provider":
            return "rejected"
        if failure_code in {"payload_invalid", "internal_error", "chain_break"}:
            return "failed"
        raise TranscriptError("unauthorized_terminal_transition")

    if current == "quoted":
        if failure_code == "quote_rejected" and sender_role == "requester":
            return "rejected"
        if failure_code == "cancelled_by_sender" and sender_role == "requester":
            return "cancelled"
        if failure_code == "quote_expired":
            return "expired"
        if failure_code in {"payload_invalid", "internal_error", "chain_break"}:
            return "failed"
        raise TranscriptError("unauthorized_terminal_transition")

    if current == "authorized":
        if failure_code == "cancelled_by_sender":
            # Cancellation after authorization is not permitted.
            raise TranscriptError("unauthorized_terminal_transition")
        if failure_code == "authorization_expired":
            return "expired"
        if failure_code in {
            "settlement_unverified",
            "chain_break",
            "payload_invalid",
            "internal_error",
            "invalid_signature",
            "duplicate_message",
        }:
            return "failed"
        raise TranscriptError("unauthorized_terminal_transition")

    if current == "settled":
        if failure_code == "service_incomplete" and sender_role == "provider":
            return "failed"
        raise TranscriptError("unauthorized_terminal_transition")

    # completed/disputed and other terminals cannot accept failure transitions here.
    raise TranscriptError("message_after_terminal")


def _assert_participants(
    env: Mapping[str, Any],
    *,
    requester_key: str,
    provider_key: str,
    expected_sender_role: Optional[str],
    allow_either_sender: bool,
) -> str:
    sender = _party_key(env, "sender")
    recipient = _party_key(env, "recipient")
    parties = {requester_key, provider_key}
    if sender not in parties or recipient not in parties:
        raise TranscriptError("participant_mismatch")
    if sender == recipient:
        raise TranscriptError("role_mismatch")

    if sender == requester_key:
        sender_role = "requester"
        if recipient != provider_key:
            raise TranscriptError("participant_mismatch")
    else:
        sender_role = "provider"
        if recipient != requester_key:
            raise TranscriptError("participant_mismatch")

    if allow_either_sender:
        return sender_role
    if expected_sender_role is None or sender_role != expected_sender_role:
        raise TranscriptError("role_mismatch")
    return sender_role


def verify_transcript(
    envelopes: Sequence[Mapping[str, Any]],
    *,
    require_terminal: bool = False,
) -> TranscriptResult:
    """
    Verify an ordered M2M exchange transcript of already-signed envelopes.

    Does not mutate caller envelopes. Performs no I/O or network access.
    """
    state: Optional[str] = None
    exchange_id: Optional[str] = None
    settlement_tx: Optional[str] = None
    verified = 0

    try:
        if not isinstance(envelopes, Sequence) or isinstance(envelopes, (str, bytes)):
            raise TranscriptError("transcript_not_array")
        n = len(envelopes)
        if n == 0:
            raise TranscriptError("empty_transcript")
        if n > MAX_TRANSCRIPT_MESSAGES:
            raise TranscriptError("transcript_too_large")

        # Work on shallow copies of mappings so caller objects are never mutated.
        working: List[Dict[str, Any]] = []
        for idx, item in enumerate(envelopes):
            if not isinstance(item, Mapping):
                raise TranscriptError("transcript_element_not_object", failed_index=idx)
            working.append(dict(item))

        seen_message_ids: Set[str] = set()
        nonces_by_sender: Dict[str, Set[str]] = {}
        last_created: Optional[int] = None
        last_expires: Optional[int] = None
        last_message_id: Optional[str] = None

        requester_key: Optional[str] = None
        provider_key: Optional[str] = None
        requester_identity: Optional[str] = None
        provider_identity: Optional[str] = None

        request_msg_id: Optional[str] = None
        quote_msg_id: Optional[str] = None
        quote_amount: Optional[int] = None
        quote_service_id: Optional[str] = None
        auth_msg_id: Optional[str] = None
        auth_amount: Optional[int] = None
        payer_identity: Optional[str] = None
        payee_identity: Optional[str] = None
        settle_msg_id: Optional[str] = None
        max_amount: Optional[int] = None

        for idx, env in enumerate(working):
            if state in TERMINAL_STATES:
                raise TranscriptError(
                    "message_after_terminal",
                    failed_index=idx,
                    state=state,
                    exchange_id=exchange_id,
                    verified_messages=verified,
                    settlement_transaction_id=settlement_tx,
                )

            result = verify_envelope(env)
            if not result.ok:
                code = "envelope_verification_failed"
                if env.get("message_type") == "settlement_reference" and result.code in {
                    "altered_settlement_material",
                    "malformed_l28_transaction_id",
                    "missing_field",
                    "null_required_field",
                    "invalid_field_type",
                }:
                    code = "settlement_citation_invalid"
                raise TranscriptError(
                    code,
                    failed_index=idx,
                    envelope_code=result.code,
                    state=state,
                    exchange_id=exchange_id,
                    verified_messages=verified,
                    settlement_transaction_id=settlement_tx,
                )

            message_type = env["message_type"]
            message_id = env["message_id"]
            tx_id = env["transaction_id"]
            created_at = _exact_int(env["created_at"])
            expires_at = _exact_int(env["expires_at"])
            nonce = env["nonce"]
            if not isinstance(nonce, str) or nonce == "":
                raise TranscriptError(
                    "envelope_verification_failed",
                    failed_index=idx,
                    envelope_code="invalid_field_type",
                    state=state,
                    exchange_id=exchange_id,
                    verified_messages=verified,
                )

            if exchange_id is None:
                exchange_id = tx_id
            elif tx_id != exchange_id:
                raise TranscriptError(
                    "exchange_id_mismatch",
                    failed_index=idx,
                    state=state,
                    exchange_id=exchange_id,
                    verified_messages=verified,
                    settlement_transaction_id=settlement_tx,
                )

            if message_id in seen_message_ids:
                raise TranscriptError(
                    "duplicate_message_id",
                    failed_index=idx,
                    state=state,
                    exchange_id=exchange_id,
                    verified_messages=verified,
                    settlement_transaction_id=settlement_tx,
                )

            sender_key = _party_key(env, "sender")
            used = nonces_by_sender.setdefault(sender_key, set())
            if nonce in used:
                raise TranscriptError(
                    "duplicate_nonce",
                    failed_index=idx,
                    state=state,
                    exchange_id=exchange_id,
                    verified_messages=verified,
                    settlement_transaction_id=settlement_tx,
                )

            if idx == 0:
                if message_type != "service_request":
                    raise TranscriptError(
                        "first_message_not_request",
                        failed_index=0,
                        exchange_id=exchange_id,
                    )
                if env.get("previous_message_id") is not None:
                    raise TranscriptError(
                        "invalid_first_previous_message",
                        failed_index=0,
                        exchange_id=exchange_id,
                    )
                requester_key = _party_key(env, "sender")
                provider_key = _party_key(env, "recipient")
                if requester_key == provider_key:
                    raise TranscriptError("role_mismatch", failed_index=0, exchange_id=exchange_id)
                requester_identity = env.get("sender_identity")
                provider_identity = env.get("recipient_identity")
                if not isinstance(requester_identity, str) or not requester_identity:
                    raise TranscriptError("participant_mismatch", failed_index=0, exchange_id=exchange_id)
                if not isinstance(provider_identity, str) or not provider_identity:
                    raise TranscriptError("participant_mismatch", failed_index=0, exchange_id=exchange_id)

                payload = env["payload"]
                max_amount = _exact_int(payload.get("max_amount"))
                if max_amount <= 0:
                    raise TranscriptError("amount_mismatch", failed_index=0, exchange_id=exchange_id)
                if payload.get("currency") != "L28":
                    raise TranscriptError("amount_mismatch", failed_index=0, exchange_id=exchange_id)
                if not isinstance(payload.get("service_id"), str) or not payload["service_id"]:
                    raise TranscriptError("service_terms_mismatch", failed_index=0, exchange_id=exchange_id)
                request_msg_id = message_id
                state = "requested"
            else:
                assert requester_key is not None and provider_key is not None
                assert last_message_id is not None and last_created is not None and last_expires is not None

                if env.get("previous_message_id") != last_message_id:
                    raise TranscriptError(
                        "message_chain_broken",
                        failed_index=idx,
                        state=state,
                        exchange_id=exchange_id,
                        verified_messages=verified,
                        settlement_transaction_id=settlement_tx,
                    )
                if created_at < last_created:
                    raise TranscriptError(
                        "timestamp_regression",
                        failed_index=idx,
                        state=state,
                        exchange_id=exchange_id,
                        verified_messages=verified,
                        settlement_transaction_id=settlement_tx,
                    )
                if created_at > last_expires:
                    raise TranscriptError(
                        "prior_message_expired",
                        failed_index=idx,
                        state=state,
                        exchange_id=exchange_id,
                        verified_messages=verified,
                        settlement_transaction_id=settlement_tx,
                    )

                payload = env["payload"]
                if not isinstance(payload, dict):
                    raise TranscriptError(
                        "envelope_verification_failed",
                        failed_index=idx,
                        envelope_code="invalid_field_type",
                        state=state,
                        exchange_id=exchange_id,
                        verified_messages=verified,
                    )

                if message_type == "service_quote":
                    if state != "requested":
                        raise TranscriptError(
                            "invalid_transition",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    _assert_participants(
                        env,
                        requester_key=requester_key,
                        provider_key=provider_key,
                        expected_sender_role="provider",
                        allow_either_sender=False,
                    )
                    if payload.get("request_message_id") != request_msg_id:
                        raise TranscriptError(
                            "quote_reference_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    amount = _exact_int(payload.get("amount"))
                    if amount <= 0 or max_amount is None or amount > max_amount:
                        raise TranscriptError(
                            "amount_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    if payload.get("currency") != "L28":
                        raise TranscriptError(
                            "amount_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    service_id = payload.get("service_id")
                    if not isinstance(service_id, str) or not service_id:
                        raise TranscriptError(
                            "service_terms_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    terms = payload.get("service_terms")
                    terms_hash = payload.get("service_terms_hash")
                    if not isinstance(terms, dict) or not isinstance(terms_hash, str):
                        raise TranscriptError(
                            "service_terms_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    if payload_hash_for(terms) != terms_hash:
                        raise TranscriptError(
                            "service_terms_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    quote_expires = _exact_int(payload.get("quote_expires_at"))
                    if quote_expires > expires_at:
                        raise TranscriptError(
                            "invalid_transition",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    quote_msg_id = message_id
                    quote_amount = amount
                    quote_service_id = service_id
                    state = "quoted"

                elif message_type == "payment_authorization":
                    if state != "quoted":
                        raise TranscriptError(
                            "invalid_transition",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    _assert_participants(
                        env,
                        requester_key=requester_key,
                        provider_key=provider_key,
                        expected_sender_role="requester",
                        allow_either_sender=False,
                    )
                    if payload.get("quote_message_id") != quote_msg_id:
                        raise TranscriptError(
                            "quote_reference_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    authorized_amount = _exact_int(payload.get("authorized_amount"))
                    if quote_amount is None or authorized_amount != quote_amount:
                        raise TranscriptError(
                            "amount_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    if payload.get("currency") != "L28":
                        raise TranscriptError(
                            "amount_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    if payload.get("settlement_intent") != "l28_transfer":
                        raise TranscriptError(
                            "invalid_transition",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    payer = payload.get("payer_identity")
                    payee = payload.get("payee_identity")
                    if payer != requester_identity or payee != provider_identity:
                        raise TranscriptError(
                            "settlement_participant_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    auth_expires = _exact_int(payload.get("authorization_expires_at"))
                    if auth_expires > expires_at:
                        raise TranscriptError(
                            "invalid_transition",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    auth_msg_id = message_id
                    auth_amount = authorized_amount
                    payer_identity = payer
                    payee_identity = payee
                    state = "authorized"

                elif message_type == "settlement_reference":
                    if state != "authorized":
                        raise TranscriptError(
                            "invalid_transition",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    # Docs: requester or provider may send settlement_reference.
                    _assert_participants(
                        env,
                        requester_key=requester_key,
                        provider_key=provider_key,
                        expected_sender_role=None,
                        allow_either_sender=True,
                    )
                    if payload.get("authorization_message_id") != auth_msg_id:
                        raise TranscriptError(
                            "quote_reference_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    amount = _exact_int(payload.get("amount"))
                    if auth_amount is None or amount != auth_amount:
                        raise TranscriptError(
                            "amount_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    if payload.get("l28_sender") != payer_identity or payload.get("l28_receiver") != payee_identity:
                        raise TranscriptError(
                            "settlement_participant_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    if payload.get("verification_status") != "verified":
                        raise TranscriptError(
                            "settlement_citation_invalid",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                        )
                    citation = verify_settlement_citation(payload)
                    if not citation.ok:
                        raise TranscriptError(
                            "settlement_citation_invalid",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                            envelope_code=citation.code,
                        )
                    settle_msg_id = message_id
                    settlement_tx = citation.l28_transaction_id
                    state = "settled"

                elif message_type == "service_receipt":
                    if state != "settled":
                        raise TranscriptError(
                            "invalid_transition",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                            settlement_transaction_id=settlement_tx,
                        )
                    _assert_participants(
                        env,
                        requester_key=requester_key,
                        provider_key=provider_key,
                        expected_sender_role="provider",
                        allow_either_sender=False,
                    )
                    if payload.get("settlement_message_id") != settle_msg_id:
                        raise TranscriptError(
                            "receipt_reference_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                            settlement_transaction_id=settlement_tx,
                        )
                    if payload.get("l28_tx_id") != settlement_tx:
                        raise TranscriptError(
                            "receipt_reference_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                            settlement_transaction_id=settlement_tx,
                        )
                    if payload.get("service_id") != quote_service_id:
                        raise TranscriptError(
                            "service_terms_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                            settlement_transaction_id=settlement_tx,
                        )
                    if payload.get("completion_assertion") != "provider_asserted_complete":
                        raise TranscriptError(
                            "invalid_transition",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                            settlement_transaction_id=settlement_tx,
                        )
                    if not isinstance(payload.get("result_hash"), str) or not payload["result_hash"]:
                        raise TranscriptError(
                            "service_terms_mismatch",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                            settlement_transaction_id=settlement_tx,
                        )
                    _exact_int(payload.get("completed_at"))
                    state = "completed"

                elif message_type == "failure_notice":
                    if state is None or state in TERMINAL_STATES:
                        raise TranscriptError(
                            "message_after_terminal",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                            settlement_transaction_id=settlement_tx,
                        )
                    sender_role = _assert_participants(
                        env,
                        requester_key=requester_key,
                        provider_key=provider_key,
                        expected_sender_role=None,
                        allow_either_sender=True,
                    )
                    if payload.get("related_message_id") != last_message_id:
                        raise TranscriptError(
                            "message_chain_broken",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                            settlement_transaction_id=settlement_tx,
                        )
                    if payload.get("terminal") is not True:
                        raise TranscriptError(
                            "invalid_terminal_state",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                            settlement_transaction_id=settlement_tx,
                        )
                    failure_code = payload.get("failure_code")
                    if not isinstance(failure_code, str):
                        raise TranscriptError(
                            "invalid_terminal_state",
                            failed_index=idx,
                            state=state,
                            exchange_id=exchange_id,
                            verified_messages=verified,
                            settlement_transaction_id=settlement_tx,
                        )
                    # Failure after settlement does not reverse settlement_tx citation.
                    state = _resolve_failure_terminal(
                        current=state,
                        sender_role=sender_role,
                        failure_code=failure_code,
                    )

                else:
                    raise TranscriptError(
                        "invalid_transition",
                        failed_index=idx,
                        state=state,
                        exchange_id=exchange_id,
                        verified_messages=verified,
                        settlement_transaction_id=settlement_tx,
                    )

            seen_message_ids.add(message_id)
            used.add(nonce)
            last_created = created_at
            last_expires = expires_at
            last_message_id = message_id
            verified = idx + 1

        assert state is not None and exchange_id is not None
        if require_terminal and state not in TERMINAL_STATES:
            return _fail(
                "incomplete_transcript",
                state=state,
                exchange_id=exchange_id,
                verified_messages=verified,
                settlement_transaction_id=settlement_tx,
            )
        return _ok(
            state=state,
            exchange_id=exchange_id,
            verified_messages=verified,
            settlement_transaction_id=settlement_tx,
        )
    except TranscriptError as exc:
        return _fail(
            exc.code,
            failed_index=exc.failed_index,
            envelope_code=exc.envelope_code,
            state=exc.state if exc.state is not None else state,
            exchange_id=exc.exchange_id if exc.exchange_id is not None else exchange_id,
            verified_messages=exc.verified_messages if exc.verified_messages else verified,
            settlement_transaction_id=(
                exc.settlement_transaction_id
                if exc.settlement_transaction_id is not None
                else settlement_tx
            ),
        )


def verify_transcript_json(
    raw: Union[str, bytes],
    *,
    require_terminal: bool = False,
) -> TranscriptResult:
    """
    Primary untrusted-input boundary for transcript verification.

    Accepts one JSON array of envelope objects under the shared L28-M2M JSON profile.
    """
    try:
        value = parse_m2m_json_value(raw)
    except M2MVerifyError as exc:
        code = exc.code
        if code == "duplicate_key":
            return _fail("duplicate_key")
        return _fail("invalid_json")

    if not isinstance(value, list):
        return _fail("transcript_not_array")
    if len(value) == 0:
        return _fail("empty_transcript")
    if len(value) > MAX_TRANSCRIPT_MESSAGES:
        return _fail("transcript_too_large")
    for idx, item in enumerate(value):
        if not isinstance(item, dict):
            return _fail("transcript_element_not_object", failed_index=idx)
    return verify_transcript(value, require_terminal=require_terminal)


__all__ = [
    "MAX_TRANSCRIPT_MESSAGES",
    "STABLE_CODES",
    "TERMINAL_STATES",
    "TranscriptError",
    "TranscriptResult",
    "verify_transcript",
    "verify_transcript_json",
]
