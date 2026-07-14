"""Offline conformance verification for the L28 Core/P2P role profile."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROFILE = "l28-core-p2p-security/v0.1"
EXPECTED_STATUS = "specification_only_non_activation"
EXPECTED_ARCHITECTURE = "l28-core-p2p-architecture/v0.1"
EXPECTED_SEMANTIC_SHA256 = "2ebc1e597c561c3ac41fa4fd48f3571cc7381d1283d8833cb121d9a49d46d340"
MAX_PROFILE_BYTES = 64 * 1024

STABLE_CODES = (
    "conformant",
    "path_required",
    "path_invalid",
    "path_symlink",
    "path_not_file",
    "profile_too_large",
    "profile_read_failed",
    "profile_encoding_invalid",
    "profile_json_invalid",
    "profile_duplicate_key",
    "profile_schema_invalid",
    "profile_version_unsupported",
    "profile_status_invalid",
    "profile_invariant_failed",
    "profile_semantic_mismatch",
    "internal_error",
)

CHECKS = (
    "identity",
    "roles",
    "core_lifecycle",
    "p2p_lifecycle",
    "trust_boundaries",
    "future_frame",
    "failure_codes",
    "threats",
    "observability",
    "non_activation",
    "acceptance",
    "semantic_commitment",
)

_TOP_LEVEL_KEYS = {
    "profile_version",
    "status",
    "architecture",
    "roles",
    "core_lifecycle",
    "p2p_lifecycle",
    "trust_boundaries",
    "future_frame_requirements",
    "stable_failure_codes",
    "threats",
    "observability",
    "foundation19_prohibitions",
    "acceptance_checks",
}
_ROLE_NAMES = {"CoreL28Node", "L28P2PNode"}
_CORE_RESERVED = {"CANONICAL_READY_RESERVED", "RUNNING_RESERVED"}
_P2P_RESERVED = {"LISTENING_RESERVED"}
_TRUST_BOUNDARY_IDS = {
    "peer_to_p2p",
    "p2p_to_core",
    "core_to_persistence",
    "checkpoint_to_core",
}
_FRAME_FIELDS = {
    "protocol_version",
    "network_id",
    "message_type",
    "message_id",
    "peer_identity_evidence",
    "nonce",
    "timestamp",
    "expiry",
    "payload_length",
    "payload_digest",
}
_PROHIBITION_KEYS = {
    "runtime_node_class_added",
    "runtime_class_renamed",
    "network_listener_started",
    "outbound_connection_started",
    "ledger_initialized",
    "ledger_migrated",
    "checkpoint_declared_canonical",
    "mining_started",
    "wallet_or_signing_started",
    "bridge_started",
    "deployment_started",
}


@dataclass(frozen=True)
class NodeRoleConformanceResult:
    ok: bool
    code: str
    detail: str
    profile_version: str
    profile_sha256: str
    checks: tuple[str, ...]


class _DuplicateKey(ValueError):
    pass


class _ConformanceError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_nonfinite(_: str) -> None:
    raise ValueError("non-finite JSON number")


def _fail(code: str, detail: str, digest: str = "") -> NodeRoleConformanceResult:
    return NodeRoleConformanceResult(False, code, detail, "", digest, ())


def _exact_object(value: Any, keys: set[str], location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _ConformanceError("profile_schema_invalid", f"{location}:object_required")
    if set(value) != keys:
        raise _ConformanceError("profile_schema_invalid", f"{location}:keys_invalid")
    return value


def _string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise _ConformanceError("profile_schema_invalid", f"{location}:string_required")
    return value


def _boolean(value: Any, location: str) -> bool:
    if not isinstance(value, bool):
        raise _ConformanceError("profile_schema_invalid", f"{location}:boolean_required")
    return value


def _string_list(value: Any, location: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise _ConformanceError("profile_schema_invalid", f"{location}:list_required")
    if any(not isinstance(item, str) or not item for item in value):
        raise _ConformanceError("profile_schema_invalid", f"{location}:string_items_required")
    if len(value) != len(set(value)):
        raise _ConformanceError("profile_invariant_failed", f"{location}:duplicate_item")
    return value


def _validate_roles(value: Any) -> None:
    roles = _exact_object(value, _ROLE_NAMES, "roles")
    for role_name in sorted(_ROLE_NAMES):
        role = _exact_object(
            roles[role_name], {"trust", "owns", "prohibited"}, f"roles.{role_name}"
        )
        _string(role["trust"], f"roles.{role_name}.trust")
        owns = set(_string_list(role["owns"], f"roles.{role_name}.owns"))
        prohibited = set(
            _string_list(role["prohibited"], f"roles.{role_name}.prohibited")
        )
        if owns & prohibited:
            raise _ConformanceError(
                "profile_invariant_failed", f"roles.{role_name}:capability_overlap"
            )


def _validate_lifecycle(
    value: Any,
    *,
    location: str,
    activation_field: str,
    expected_reserved: set[str],
) -> None:
    lifecycle = _exact_object(
        value,
        {"states", "reserved_unreachable_states", "allowed_transitions", activation_field},
        location,
    )
    states = set(_string_list(lifecycle["states"], f"{location}.states"))
    reserved = set(
        _string_list(
            lifecycle["reserved_unreachable_states"],
            f"{location}.reserved_unreachable_states",
        )
    )
    if reserved != expected_reserved or not reserved <= states:
        raise _ConformanceError(
            "profile_invariant_failed", f"{location}:reserved_states_invalid"
        )
    transitions_value = lifecycle["allowed_transitions"]
    if not isinstance(transitions_value, list) or not transitions_value:
        raise _ConformanceError(
            "profile_schema_invalid", f"{location}.allowed_transitions:list_required"
        )
    transitions: list[tuple[str, str]] = []
    for transition in transitions_value:
        if not isinstance(transition, list) or len(transition) != 2:
            raise _ConformanceError(
                "profile_schema_invalid", f"{location}.allowed_transitions:pair_required"
            )
        source, destination = transition
        if not isinstance(source, str) or not isinstance(destination, str):
            raise _ConformanceError(
                "profile_schema_invalid", f"{location}.allowed_transitions:string_pair_required"
            )
        if source not in states or destination not in states:
            raise _ConformanceError(
                "profile_invariant_failed", f"{location}.allowed_transitions:unknown_state"
            )
        if destination in reserved:
            raise _ConformanceError(
                "profile_invariant_failed", f"{location}:reserved_state_reachable"
            )
        transitions.append((source, destination))
    if len(transitions) != len(set(transitions)):
        raise _ConformanceError(
            "profile_invariant_failed", f"{location}.allowed_transitions:duplicate"
        )
    if _boolean(lifecycle[activation_field], f"{location}.{activation_field}") is not False:
        raise _ConformanceError(
            "profile_invariant_failed", f"{location}.{activation_field}:must_be_false"
        )


def _validate_trust_boundaries(value: Any) -> None:
    if not isinstance(value, list) or not value:
        raise _ConformanceError("profile_schema_invalid", "trust_boundaries:list_required")
    seen: set[str] = set()
    for index, boundary_value in enumerate(value):
        location = f"trust_boundaries[{index}]"
        boundary = _exact_object(
            boundary_value, {"id", "input_trust", "required_controls"}, location
        )
        boundary_id = _string(boundary["id"], f"{location}.id")
        _string(boundary["input_trust"], f"{location}.input_trust")
        _string_list(boundary["required_controls"], f"{location}.required_controls")
        if boundary_id in seen:
            raise _ConformanceError(
                "profile_invariant_failed", "trust_boundaries:duplicate_id"
            )
        seen.add(boundary_id)
    if seen != _TRUST_BOUNDARY_IDS:
        raise _ConformanceError(
            "profile_invariant_failed", "trust_boundaries:membership_invalid"
        )


def _validate_frame(value: Any) -> None:
    frame = _exact_object(
        value,
        {
            "required_fields",
            "deterministic_encoding_required",
            "duplicate_fields_rejected",
            "unknown_critical_fields_rejected",
            "explicit_resource_limits_required",
            "foundation19_runtime_limits_defined",
            "reason_runtime_limits_undefined",
        },
        "future_frame_requirements",
    )
    if set(_string_list(frame["required_fields"], "future_frame_requirements.required_fields")) != _FRAME_FIELDS:
        raise _ConformanceError(
            "profile_invariant_failed", "future_frame_requirements.required_fields:invalid"
        )
    for field in (
        "deterministic_encoding_required",
        "duplicate_fields_rejected",
        "unknown_critical_fields_rejected",
        "explicit_resource_limits_required",
    ):
        if _boolean(frame[field], f"future_frame_requirements.{field}") is not True:
            raise _ConformanceError(
                "profile_invariant_failed", f"future_frame_requirements.{field}:must_be_true"
            )
    if _boolean(
        frame["foundation19_runtime_limits_defined"],
        "future_frame_requirements.foundation19_runtime_limits_defined",
    ) is not False:
        raise _ConformanceError(
            "profile_invariant_failed",
            "future_frame_requirements.foundation19_runtime_limits_defined:must_be_false",
        )
    _string(
        frame["reason_runtime_limits_undefined"],
        "future_frame_requirements.reason_runtime_limits_undefined",
    )


def _validate_observability(value: Any) -> None:
    observability = _exact_object(
        value,
        {
            "deterministic_reports_required",
            "content_bound_report_ids_required",
            "allowed_categories",
            "prohibited_categories",
        },
        "observability",
    )
    if _boolean(
        observability["deterministic_reports_required"],
        "observability.deterministic_reports_required",
    ) is not True:
        raise _ConformanceError(
            "profile_invariant_failed", "observability:deterministic_reports_required"
        )
    if _boolean(
        observability["content_bound_report_ids_required"],
        "observability.content_bound_report_ids_required",
    ) is not True:
        raise _ConformanceError(
            "profile_invariant_failed", "observability:content_bound_report_ids_required"
        )
    allowed = set(
        _string_list(observability["allowed_categories"], "observability.allowed_categories")
    )
    prohibited = set(
        _string_list(
            observability["prohibited_categories"], "observability.prohibited_categories"
        )
    )
    if allowed & prohibited:
        raise _ConformanceError(
            "profile_invariant_failed", "observability:category_overlap"
        )


def _canonical_semantic_sha256(value: Any) -> str:
    canonical = json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _validate_profile(value: Any) -> None:
    profile = _exact_object(value, _TOP_LEVEL_KEYS, "profile")
    if _string(profile["profile_version"], "profile_version") != PROFILE:
        raise _ConformanceError("profile_version_unsupported", "profile_version:unsupported")
    if _string(profile["status"], "status") != EXPECTED_STATUS:
        raise _ConformanceError("profile_status_invalid", "status:invalid")
    if _string(profile["architecture"], "architecture") != EXPECTED_ARCHITECTURE:
        raise _ConformanceError("profile_invariant_failed", "architecture:invalid")
    _validate_roles(profile["roles"])
    _validate_lifecycle(
        profile["core_lifecycle"],
        location="core_lifecycle",
        activation_field="canonical_activation_transition_present",
        expected_reserved=_CORE_RESERVED,
    )
    _validate_lifecycle(
        profile["p2p_lifecycle"],
        location="p2p_lifecycle",
        activation_field="network_activation_transition_present",
        expected_reserved=_P2P_RESERVED,
    )
    _validate_trust_boundaries(profile["trust_boundaries"])
    _validate_frame(profile["future_frame_requirements"])
    _string_list(profile["stable_failure_codes"], "stable_failure_codes")
    _string_list(profile["threats"], "threats")
    _validate_observability(profile["observability"])
    prohibitions = _exact_object(
        profile["foundation19_prohibitions"],
        _PROHIBITION_KEYS,
        "foundation19_prohibitions",
    )
    for key in sorted(_PROHIBITION_KEYS):
        if _boolean(prohibitions[key], f"foundation19_prohibitions.{key}") is not False:
            raise _ConformanceError(
                "profile_invariant_failed", f"foundation19_prohibitions.{key}:must_be_false"
            )
    _string_list(profile["acceptance_checks"], "acceptance_checks")
    if _canonical_semantic_sha256(profile) != EXPECTED_SEMANTIC_SHA256:
        raise _ConformanceError(
            "profile_semantic_mismatch", "profile:semantic_commitment_mismatch"
        )


def _read_profile(profile_path: str | os.PathLike[str]) -> tuple[bytes, str]:
    try:
        raw_path = os.fspath(profile_path)
    except TypeError as exc:
        raise _ConformanceError("path_invalid", "profile_path:invalid") from exc
    if not isinstance(raw_path, str):
        raise _ConformanceError("path_invalid", "profile_path:invalid")
    if not raw_path:
        raise _ConformanceError("path_required", "profile_path:required")
    path = Path(raw_path)
    if path.is_symlink():
        raise _ConformanceError("path_symlink", "profile_path:symlink_rejected")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise _ConformanceError("profile_read_failed", "profile_path:unreadable") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise _ConformanceError("path_not_file", "profile_path:regular_file_required")
        if metadata.st_size > MAX_PROFILE_BYTES:
            raise _ConformanceError("profile_too_large", "profile:too_large")
        chunks: list[bytes] = []
        remaining = MAX_PROFILE_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(remaining, 65536))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
    except _ConformanceError:
        raise
    except OSError as exc:
        raise _ConformanceError("profile_read_failed", "profile:read_failed") from exc
    finally:
        os.close(descriptor)
    if len(raw) > MAX_PROFILE_BYTES:
        raise _ConformanceError("profile_too_large", "profile:too_large")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise _ConformanceError("profile_encoding_invalid", "profile:utf8_required") from exc
    return raw, text


def verify_node_role_profile(
    profile_path: str | os.PathLike[str] | None,
) -> NodeRoleConformanceResult:
    """Verify one explicitly supplied Foundation 19 role-security profile."""

    if profile_path is None:
        return _fail("path_required", "profile_path:required")
    digest = ""
    try:
        raw, text = _read_profile(profile_path)
        digest = hashlib.sha256(raw).hexdigest()
        try:
            value = json.loads(
                text,
                object_pairs_hook=_pairs_no_duplicates,
                parse_constant=_reject_nonfinite,
            )
        except _DuplicateKey:
            return _fail("profile_duplicate_key", "profile:duplicate_key", digest)
        except (json.JSONDecodeError, RecursionError, ValueError):
            return _fail("profile_json_invalid", "profile:invalid_json", digest)
        _validate_profile(value)
        return NodeRoleConformanceResult(True, "conformant", "", PROFILE, digest, CHECKS)
    except _ConformanceError as exc:
        return _fail(exc.code, exc.detail, digest)
    except Exception:
        return _fail("internal_error", "verification:internal_error", digest)
