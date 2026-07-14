"""Offline verification of inert L28 node-role transition transcripts.

This module accepts explicit JSON data and replays its transitions through the
Foundation 21 immutable role models. It performs no filesystem, network,
ledger, wallet, mining, signing, or runtime-node operations.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Final

from .node_role_model import (
    MODEL_VERSION,
    STABLE_CODES as MODEL_STABLE_CODES,
    CoreNodeRoleModel,
    P2PNodeRoleModel,
)


TRANSCRIPT_VERSION: Final = "l28-node-role-transcript/v0.1"
VERIFIER_VERSION: Final = "l28-node-role-transcript-verifier/v0.1"
MAX_TRANSCRIPT_BYTES: Final = 262_144
MAX_TRANSITIONS: Final = 256
MAX_STATE_TEXT_LENGTH: Final = 128

CORE_ROLE: Final = "CoreL28Node"
P2P_ROLE: Final = "L28P2PNode"
SUPPORTED_ROLES: Final = (CORE_ROLE, P2P_ROLE)

STABLE_CODES: Final = (
    "transcript_valid",
    "input_type_invalid",
    "transcript_too_large",
    "invalid_encoding",
    "invalid_json",
    "duplicate_key",
    "schema_error",
    "version_unsupported",
    "role_invalid",
    "initial_state_invalid",
    "transition_count_invalid",
    "sequence_invalid",
    "transition_mismatch",
    "final_state_mismatch",
    "terminal_state_required",
    "internal_error",
)

TOP_LEVEL_FIELDS: Final = frozenset(
    {
        "transcript_version",
        "model_version",
        "role",
        "initial_state",
        "transitions",
        "final_state",
    }
)

ENTRY_FIELDS: Final = frozenset(
    {
        "sequence",
        "previous_state",
        "requested_state",
        "resulting_state",
        "ok",
        "code",
    }
)

SUCCESS_CHECKS: Final = (
    "identity",
    "schema",
    "sequence",
    "replay",
    "reserved_states",
    "terminal_state",
    "semantic_commitment",
)


class _DuplicateKey(ValueError):
    pass


class _TranscriptError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class NodeRoleTranscriptEntry:
    sequence: int
    previous_state: str
    requested_state: str
    resulting_state: str
    ok: bool
    code: str


@dataclass(frozen=True)
class NodeRoleTranscriptResult:
    ok: bool
    code: str
    role: str
    initial_state: str
    final_state: str
    transition_count: int
    transcript_sha256: str
    checks: tuple[str, ...]
    detail: str = ""
    transcript_version: str = TRANSCRIPT_VERSION
    model_version: str = MODEL_VERSION
    verifier_version: str = VERIFIER_VERSION


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(value)


def _decode_payload(payload: str | bytes) -> str:
    if isinstance(payload, bytes):
        if len(payload) > MAX_TRANSCRIPT_BYTES:
            raise _TranscriptError("transcript_too_large")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _TranscriptError("invalid_encoding") from exc

    if isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _TranscriptError("invalid_encoding") from exc
        if len(encoded) > MAX_TRANSCRIPT_BYTES:
            raise _TranscriptError("transcript_too_large")
        return payload

    raise _TranscriptError("input_type_invalid")


def _parse_json(payload: str | bytes) -> Any:
    text = _decode_payload(payload)
    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
        )
    except _DuplicateKey as exc:
        raise _TranscriptError("duplicate_key") from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise _TranscriptError("invalid_json") from exc


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise _TranscriptError("schema_error") from exc


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_exact_fields(
    value: Any,
    expected: frozenset[str],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _TranscriptError("schema_error")
    if frozenset(value) != expected:
        raise _TranscriptError("schema_error")
    return value


def _require_text(value: Any) -> str:
    if not isinstance(value, str):
        raise _TranscriptError("schema_error")
    if not value or len(value) > MAX_STATE_TEXT_LENGTH:
        raise _TranscriptError("schema_error")
    return value


def _require_bool(value: Any) -> bool:
    if type(value) is not bool:
        raise _TranscriptError("schema_error")
    return value


def _require_sequence(value: Any, expected: int) -> int:
    if type(value) is not int or value != expected:
        raise _TranscriptError("sequence_invalid")
    return value


def _parse_entry(value: Any, expected_sequence: int) -> NodeRoleTranscriptEntry:
    item = _require_exact_fields(value, ENTRY_FIELDS)

    code = _require_text(item["code"])
    if code not in MODEL_STABLE_CODES:
        raise _TranscriptError("schema_error")

    return NodeRoleTranscriptEntry(
        sequence=_require_sequence(item["sequence"], expected_sequence),
        previous_state=_require_text(item["previous_state"]),
        requested_state=_require_text(item["requested_state"]),
        resulting_state=_require_text(item["resulting_state"]),
        ok=_require_bool(item["ok"]),
        code=code,
    )


def _failure(
    *,
    code: str,
    role: str = "",
    initial_state: str = "",
    final_state: str = "",
    transition_count: int = 0,
    transcript_sha256: str = "",
    detail: str = "",
) -> NodeRoleTranscriptResult:
    return NodeRoleTranscriptResult(
        ok=False,
        code=code,
        role=role,
        initial_state=initial_state,
        final_state=final_state,
        transition_count=transition_count,
        transcript_sha256=transcript_sha256,
        checks=(),
        detail=detail,
    )


class NodeRoleTranscriptVerifier:
    """Pure-data verifier for completed inert node-role transcripts."""

    @classmethod
    def verify_json(cls, payload: str | bytes) -> NodeRoleTranscriptResult:
        role = ""
        initial_state = ""
        final_state = ""
        transition_count = 0
        transcript_sha256 = ""

        try:
            value = _parse_json(payload)
            transcript_sha256 = _sha256(_canonical_bytes(value))
            document = _require_exact_fields(value, TOP_LEVEL_FIELDS)

            if document["transcript_version"] != TRANSCRIPT_VERSION:
                raise _TranscriptError("version_unsupported")
            if document["model_version"] != MODEL_VERSION:
                raise _TranscriptError("version_unsupported")

            role = _require_text(document["role"])
            if role not in SUPPORTED_ROLES:
                raise _TranscriptError("role_invalid")

            initial_state = _require_text(document["initial_state"])
            if initial_state != "CREATED":
                raise _TranscriptError("initial_state_invalid")

            final_state = _require_text(document["final_state"])

            transition_values = document["transitions"]
            if not isinstance(transition_values, list):
                raise _TranscriptError("schema_error")

            transition_count = len(transition_values)
            if transition_count < 1 or transition_count > MAX_TRANSITIONS:
                raise _TranscriptError("transition_count_invalid")

            entries = tuple(
                _parse_entry(item, sequence)
                for sequence, item in enumerate(transition_values)
            )

            model: CoreNodeRoleModel | P2PNodeRoleModel
            if role == CORE_ROLE:
                model = CoreNodeRoleModel()
            else:
                model = P2PNodeRoleModel()

            for entry in entries:
                if entry.previous_state != model.state:
                    raise _TranscriptError("transition_mismatch")

                next_model, result = model.transition(entry.requested_state)

                declared = (
                    entry.ok,
                    entry.code,
                    role,
                    entry.previous_state,
                    entry.requested_state,
                    entry.resulting_state,
                    MODEL_VERSION,
                )
                observed = (
                    result.ok,
                    result.code,
                    result.role,
                    result.previous_state,
                    result.requested_state,
                    result.resulting_state,
                    result.model_version,
                )

                if declared != observed:
                    raise _TranscriptError("transition_mismatch")

                model = next_model

            if final_state != model.state:
                raise _TranscriptError("final_state_mismatch")
            if final_state != "STOPPED":
                raise _TranscriptError("terminal_state_required")

            return NodeRoleTranscriptResult(
                ok=True,
                code="transcript_valid",
                role=role,
                initial_state=initial_state,
                final_state=final_state,
                transition_count=transition_count,
                transcript_sha256=transcript_sha256,
                checks=SUCCESS_CHECKS,
            )

        except _TranscriptError as exc:
            return _failure(
                code=exc.code,
                role=role,
                initial_state=initial_state,
                final_state=final_state,
                transition_count=transition_count,
                transcript_sha256=transcript_sha256,
                detail=exc.detail,
            )
        except Exception:
            return _failure(
                code="internal_error",
                role=role,
                initial_state=initial_state,
                final_state=final_state,
                transition_count=transition_count,
                transcript_sha256=transcript_sha256,
            )


def verify_transcript_json(
    payload: str | bytes,
) -> NodeRoleTranscriptResult:
    """Verify explicit transcript JSON without discovering external state."""

    return NodeRoleTranscriptVerifier.verify_json(payload)
