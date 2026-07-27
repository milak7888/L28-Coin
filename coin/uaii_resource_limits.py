# SPDX-License-Identifier: Apache-2.0
"""UAII Foundation 60 resource limits (Foundation 62/63 implementation)."""

from __future__ import annotations

from typing import Any

from .uaii_json import serialize_uaii_response, strict_utf8_bytes

F60_L1_MAX_DEPTH = 32
F60_L2_MAX_OBJECT_MEMBERS = 256
F60_L3_MAX_ARRAY_ELEMENTS = 256
F60_L4_MAX_STRING_UTF8_BYTES = 4096
F60_L5_MAX_CANON_REQUEST_BYTES = 16384
F60_L6_MAX_SERIALIZED_RESPONSE_BYTES = 16384
MAX_RECEIVED_REQUEST_BYTES = 16384
NONCE_MIN_BYTES = 1
NONCE_MAX_BYTES = 256

NONCE_FIELD_NAMES = frozenset(
    {"nonce", "quote_nonce", "payment_nonce", "receipt_nonce"}
)


class LimitFailure(Exception):
    """Resource-limit, nonce-at-walk, or out-of-domain structural failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def walk_enforce_l1_l4(root: Any) -> None:
    """Iterative DFS enforcement of F60-L1…L4 (and nonce carve-out).

    Root depth is 1. Empty containers contribute depth. Object members are
    counted after duplicate-key rejection (caller responsibility).

    Direct Python-object cycles are rejected as `json_invalid` (outside the
    accepted JSON domain). Shared but acyclic references are allowed.
    """
    # Stack ops: ("visit", value, depth, parent_key) | ("exit", container, _, _)
    stack: list[tuple[str, Any, int, str | None]] = [("visit", root, 1, None)]
    visiting: set[int] = set()

    while stack:
        op, value, depth, parent_key = stack.pop()

        if op == "exit":
            visiting.discard(id(value))
            continue

        if isinstance(value, dict):
            vid = id(value)
            if vid in visiting:
                raise LimitFailure("json_invalid")
            if depth > F60_L1_MAX_DEPTH:
                raise LimitFailure("resource_limit_exceeded")
            if len(value) > F60_L2_MAX_OBJECT_MEMBERS:
                raise LimitFailure("resource_limit_exceeded")
            visiting.add(vid)
            stack.append(("exit", value, depth, None))
            items = list(value.items())
            for key, child in reversed(items):
                stack.append(("visit", child, depth + 1, key))
            continue

        if isinstance(value, list):
            vid = id(value)
            if vid in visiting:
                raise LimitFailure("json_invalid")
            if depth > F60_L1_MAX_DEPTH:
                raise LimitFailure("resource_limit_exceeded")
            if len(value) > F60_L3_MAX_ARRAY_ELEMENTS:
                raise LimitFailure("resource_limit_exceeded")
            visiting.add(vid)
            stack.append(("exit", value, depth, None))
            for child in reversed(value):
                stack.append(("visit", child, depth + 1, None))
            continue

        if isinstance(value, str):
            raw = strict_utf8_bytes(value)
            nbytes = len(raw)
            if parent_key in NONCE_FIELD_NAMES:
                if nbytes < NONCE_MIN_BYTES or nbytes > NONCE_MAX_BYTES or "\0" in value:
                    raise LimitFailure("nonce_invalid")
            elif nbytes > F60_L4_MAX_STRING_UTF8_BYTES:
                raise LimitFailure("resource_limit_exceeded")
            continue

        # primitives do not add depth beyond their container


def enforce_l5_canon_bytes(canon_bytes: bytes) -> None:
    if len(canon_bytes) > F60_L5_MAX_CANON_REQUEST_BYTES:
        raise LimitFailure("resource_limit_exceeded")


def enforce_l6_response_bytes(response_bytes: bytes) -> None:
    if len(response_bytes) > F60_L6_MAX_SERIALIZED_RESPONSE_BYTES:
        raise LimitFailure("resource_limit_exceeded")


def build_l6_fallback_envelope(
    *,
    interface_profile: str = "",
    operation: str = "",
    request_id: str = "",
) -> dict[str, Any]:
    """Fixed non-recursive F60 §7.3 / F62 §7 fail-closed envelope."""
    return {
        "ok": False,
        "code": "resource_limit_exceeded",
        "interface_profile": interface_profile if isinstance(interface_profile, str) else "",
        "operation": operation if isinstance(operation, str) else "",
        "request_id": request_id if isinstance(request_id, str) else "",
        "result": {},
        "execution_authorized": False,
        "report_id": "",
        "detail": "",
    }


def measured_l6_fallback_envelope(
    *,
    interface_profile: str = "",
    operation: str = "",
    request_id: str = "",
) -> tuple[dict[str, Any], bytes]:
    """Build fallback and independently measure serialized size."""
    envelope = build_l6_fallback_envelope(
        interface_profile=interface_profile,
        operation=operation,
        request_id=request_id,
    )
    raw = serialize_uaii_response(envelope)
    if len(raw) > F60_L6_MAX_SERIALIZED_RESPONSE_BYTES:
        # Defective fallback — must not recurse or truncate.
        raise LimitFailure("resource_limit_exceeded")
    return envelope, raw
