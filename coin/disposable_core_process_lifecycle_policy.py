# SPDX-License-Identifier: Apache-2.0
"""Offline disposable Core lifecycle policy evaluator (Foundation 45 / F44).

Evaluates whether an inert Foundation 21 CoreNodeRoleModel transition is
permitted under a caller-supplied frozen Foundation 39 identity projection.
Does not spawn processes, open sockets, persist state, or activate a testnet.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from .disposable_network_identity_genesis_binding import (
    ENVIRONMENT as DISPOSABLE_ENVIRONMENT,
    NETWORK_ID,
    PROTOCOL_VERSION,
)
from .node_role_model import (
    CORE_ROLE,
    CoreNodeRoleModel,
    MODEL_VERSION,
)

PROFILE = "l28-disposable-core-process-lifecycle-policy/v0.1"
MAX_REQUEST_BYTES = 4096

FORBIDDEN_ENVIRONMENTS = frozenset({"MAIN", "CANONICAL", "HISTORICAL", "PRODUCTION"})

REQUEST_FIELDS = (
    "policy_version",
    "environment",
    "identity_evidence",
    "current_state",
    "requested_state",
    "execution_authorized",
)

IDENTITY_EVIDENCE_FIELDS = (
    "ok",
    "code",
    "network_id",
    "chain_id",
    "genesis_digest",
    "protocol_version",
    "execution_authorized",
    "report_id",
)

STABLE_CODES = (
    "transitioned",
    "state_invalid",
    "reserved_state_unreachable",
    "transition_not_allowed",
    "input_type_invalid",
    "input_too_large",
    "encoding_invalid",
    "json_invalid",
    "duplicate_key",
    "invalid_top_level",
    "schema_invalid",
    "policy_version_unsupported",
    "environment_invalid",
    "historical_import_forbidden",
    "identity_evidence_invalid",
    "execution_authorized_invalid",
    "internal_error",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class _DuplicateKey(ValueError):
    pass


class _PolicyError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CoreLifecyclePolicyResult:
    ok: bool
    code: str
    role: str = CORE_ROLE
    previous_state: str = ""
    requested_state: str = ""
    resulting_state: str = ""
    model_version: str = MODEL_VERSION
    policy_version: str = PROFILE
    network_id: str = ""
    chain_id: str = ""
    genesis_digest: str = ""
    protocol_version: str = ""
    identity_report_id: str = ""
    execution_authorized: bool = False
    detail: str = ""


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise _PolicyError("json_invalid")


def _failure(
    code: str,
    *,
    previous_state: str = "",
    requested_state: str = "",
    resulting_state: str = "",
) -> CoreLifecyclePolicyResult:
    return CoreLifecyclePolicyResult(
        False,
        code,
        previous_state=previous_state,
        requested_state=requested_state,
        resulting_state=resulting_state or previous_state,
        execution_authorized=False,
        detail="",
    )


def _success(
    *,
    previous_state: str,
    requested_state: str,
    resulting_state: str,
    evidence: Mapping[str, Any],
) -> CoreLifecyclePolicyResult:
    return CoreLifecyclePolicyResult(
        True,
        "transitioned",
        previous_state=previous_state,
        requested_state=requested_state,
        resulting_state=resulting_state,
        network_id=str(evidence["network_id"]),
        chain_id=str(evidence["chain_id"]),
        genesis_digest=str(evidence["genesis_digest"]),
        protocol_version=str(evidence["protocol_version"]),
        identity_report_id=str(evidence["report_id"]),
        execution_authorized=False,
        detail="",
    )


def _decode(payload: str | bytes) -> str:
    if isinstance(payload, bytes):
        if len(payload) > MAX_REQUEST_BYTES:
            raise _PolicyError("input_too_large")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _PolicyError("encoding_invalid") from exc
    if isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _PolicyError("encoding_invalid") from exc
        if len(encoded) > MAX_REQUEST_BYTES:
            raise _PolicyError("input_too_large")
        return payload
    raise _PolicyError("input_type_invalid")


def _parse(payload: str | bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            _decode(payload),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise _PolicyError("duplicate_key") from exc
    except _PolicyError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _PolicyError("json_invalid") from exc
    if not isinstance(value, dict):
        raise _PolicyError("invalid_top_level")
    return value


def _require_hex64(value: Any) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise _PolicyError("identity_evidence_invalid")
    return value


def _validate_identity_evidence(evidence: Any) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise _PolicyError("identity_evidence_invalid")
    if tuple(evidence.keys()) != IDENTITY_EVIDENCE_FIELDS:
        raise _PolicyError("identity_evidence_invalid")

    ok = evidence["ok"]
    if isinstance(ok, bool) is False:
        raise _PolicyError("identity_evidence_invalid")
    if evidence["execution_authorized"] is not False:
        if not isinstance(evidence["execution_authorized"], bool):
            raise _PolicyError("execution_authorized_invalid")
        raise _PolicyError("execution_authorized_invalid")

    if ok is not True:
        raise _PolicyError("identity_evidence_invalid")
    if evidence["code"] != "ok":
        raise _PolicyError("identity_evidence_invalid")
    if evidence["network_id"] != NETWORK_ID:
        raise _PolicyError("identity_evidence_invalid")
    if evidence["protocol_version"] != PROTOCOL_VERSION:
        raise _PolicyError("identity_evidence_invalid")

    chain_id = evidence["chain_id"]
    if not isinstance(chain_id, str) or not chain_id:
        raise _PolicyError("identity_evidence_invalid")

    _require_hex64(evidence["genesis_digest"])
    _require_hex64(evidence["report_id"])
    return evidence


def _apply_transition(
    *,
    current_state: str,
    requested_state: str,
    model: CoreNodeRoleModel | None,
) -> tuple[str, str, str, str]:
    """Return (code, previous, requested, resulting) using Foundation 21."""
    if model is not None:
        if model.state != current_state:
            raise _PolicyError("state_invalid")
        active = model
    else:
        try:
            active = CoreNodeRoleModel._from_valid_state(current_state)
        except ValueError as exc:
            raise _PolicyError("state_invalid") from exc

    _next, result = active.transition(requested_state)
    return (
        result.code,
        result.previous_state,
        result.requested_state,
        result.resulting_state,
    )


def _evaluate_parsed(request: Mapping[str, Any], *, model: CoreNodeRoleModel | None) -> CoreLifecyclePolicyResult:
    if tuple(request.keys()) != REQUEST_FIELDS:
        raise _PolicyError("schema_invalid")

    if not isinstance(request["policy_version"], str):
        raise _PolicyError("schema_invalid")
    if request["policy_version"] != PROFILE:
        raise _PolicyError("policy_version_unsupported")

    environment = request["environment"]
    if not isinstance(environment, str):
        raise _PolicyError("schema_invalid")
    if environment in FORBIDDEN_ENVIRONMENTS:
        raise _PolicyError("historical_import_forbidden")
    if environment != DISPOSABLE_ENVIRONMENT:
        raise _PolicyError("environment_invalid")

    if request["execution_authorized"] is not False:
        raise _PolicyError("execution_authorized_invalid")

    if not isinstance(request["current_state"], str):
        raise _PolicyError("schema_invalid")
    if not isinstance(request["requested_state"], str):
        raise _PolicyError("schema_invalid")

    evidence = _validate_identity_evidence(request["identity_evidence"])
    current_state = request["current_state"]
    requested_state = request["requested_state"]

    code, previous, requested, resulting = _apply_transition(
        current_state=current_state,
        requested_state=requested_state,
        model=model,
    )
    if code != "transitioned":
        return _failure(
            code,
            previous_state=previous,
            requested_state=requested,
            resulting_state=resulting,
        )
    return _success(
        previous_state=previous,
        requested_state=requested,
        resulting_state=resulting,
        evidence=evidence,
    )


def evaluate_core_lifecycle_policy_json(
    payload: str | bytes,
    *,
    model: CoreNodeRoleModel | None = None,
) -> CoreLifecyclePolicyResult:
    try:
        request = _parse(payload)
        return _evaluate_parsed(request, model=model)
    except _PolicyError as exc:
        return _failure(exc.code)
    except Exception:
        return _failure("internal_error")


def evaluate_core_lifecycle_policy(
    *,
    identity_evidence: Mapping[str, Any],
    current_state: str,
    requested_state: str,
    model: CoreNodeRoleModel | None = None,
) -> CoreLifecyclePolicyResult:
    """Offline helper. Implies DISPOSABLE_TEST and request execution_authorized=false."""
    try:
        if not isinstance(current_state, str) or not isinstance(requested_state, str):
            raise _PolicyError("schema_invalid")
        request = {
            "policy_version": PROFILE,
            "environment": DISPOSABLE_ENVIRONMENT,
            "identity_evidence": dict(identity_evidence),
            "current_state": current_state,
            "requested_state": requested_state,
            "execution_authorized": False,
        }
        return _evaluate_parsed(request, model=model)
    except _PolicyError as exc:
        return _failure(
            exc.code,
            previous_state=current_state if isinstance(current_state, str) else "",
            requested_state=requested_state if isinstance(requested_state, str) else "",
        )
    except Exception:
        return _failure("internal_error")
