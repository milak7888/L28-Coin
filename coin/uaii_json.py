# SPDX-License-Identifier: Apache-2.0
"""UAII exact-order JSON decode/canonicalize/serialize (Foundation 62/63).

MUST NOT use M2M sorted canonicalization (coin.m2m_verifier) for UAII objects.
"""

from __future__ import annotations

import json
import re
from typing import Any

MAX_RECEIVED_REQUEST_BYTES = 16384
# Foundation 56 §3.2 property-name grammar
PROPERTY_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class UaiiJsonError(Exception):
    """Fail-closed decode/domain error with a stable UAII code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _DuplicateKey(Exception):
    pass


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise _DuplicateKey(key)
        out[key] = value
    return out


def _reject_constant(name: str) -> Any:
    raise ValueError("non_finite")


def _reject_float(_s: str) -> Any:
    raise ValueError("float_forbidden")


def strict_utf8_bytes(text: str) -> bytes:
    """Encode Unicode text as strict UTF-8; lone/non-scalar surrogates fail."""
    try:
        return text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise UaiiJsonError("encoding_invalid") from exc


def _validate_unicode_scalars(value: Any) -> None:
    """Reject any string that cannot form strict UTF-8 (lone surrogates, etc.)."""
    stack: list[Any] = [value]
    while stack:
        cur = stack.pop()
        if isinstance(cur, str):
            strict_utf8_bytes(cur)
        elif isinstance(cur, dict):
            for k, v in cur.items():
                if not isinstance(k, str):
                    raise UaiiJsonError("json_invalid")
                strict_utf8_bytes(k)
                stack.append(v)
        elif isinstance(cur, list):
            stack.extend(reversed(cur))
        elif isinstance(cur, bool) or cur is None or isinstance(cur, int):
            continue
        elif isinstance(cur, float):
            raise UaiiJsonError("json_invalid")
        else:
            raise UaiiJsonError("json_invalid")


def enforce_uaii_property_names(value: Any) -> None:
    """Reject property names that violate Foundation 56 §3.2 (`schema_invalid`).

    Call after duplicate-key rejection and secret-material scan so those
    codes retain precedence over grammar failures.
    """
    stack: list[Any] = [value]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for key, item in cur.items():
                if not isinstance(key, str) or PROPERTY_NAME_RE.fullmatch(key) is None:
                    raise UaiiJsonError("schema_invalid")
                stack.append(item)
        elif isinstance(cur, list):
            stack.extend(cur)


def decode_uaii_json(request_bytes: str | bytes) -> dict[str, Any]:
    """Decode a UAII request into a top-level object.

    Precedence: type → received size → strict UTF-8 → JSON/duplicates/top-level
    → Unicode-scalar validation on the decoded tree.
    """
    if isinstance(request_bytes, bytes):
        if len(request_bytes) > MAX_RECEIVED_REQUEST_BYTES:
            raise UaiiJsonError("input_too_large")
        try:
            text = request_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UaiiJsonError("encoding_invalid") from exc
    elif isinstance(request_bytes, str):
        try:
            encoded = request_bytes.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise UaiiJsonError("encoding_invalid") from exc
        if len(encoded) > MAX_RECEIVED_REQUEST_BYTES:
            raise UaiiJsonError("input_too_large")
        text = request_bytes
    else:
        raise UaiiJsonError("input_type_invalid")

    if text.startswith("\ufeff"):
        raise UaiiJsonError("encoding_invalid")

    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
            parse_float=_reject_float,
        )
    except _DuplicateKey as exc:
        raise UaiiJsonError("duplicate_key") from exc
    except UaiiJsonError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise UaiiJsonError("json_invalid") from exc

    if not isinstance(value, dict):
        raise UaiiJsonError("invalid_top_level")

    _validate_unicode_scalars(value)
    return value


def canon_uaii(obj: Any) -> bytes:
    """Foundation 56 §3.2 exact-order UAII canonicalization."""
    _validate_unicode_scalars(obj)
    try:
        text = json.dumps(
            obj,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise UaiiJsonError("json_invalid") from exc
    return strict_utf8_bytes(text)


def serialize_uaii_response(envelope: dict[str, Any]) -> bytes:
    """Serialize a Foundation 56 §3.4 response envelope with UAII compact rules."""
    return canon_uaii(envelope)
