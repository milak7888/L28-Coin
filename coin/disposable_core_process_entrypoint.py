# SPDX-License-Identifier: Apache-2.0
"""Offline disposable Core process entrypoint preflight evaluator (Foundation 47 / F46).

Evaluates an immutable offline preflight request under frozen Foundation 39 and
Foundation 45 evidence projections plus a sandbox descriptor. Does not spawn
processes, open network listeners, touch the filesystem, or activate a testnet.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from .disposable_network_identity_genesis_binding import (
    DATA_DIR_TAG,
    ENVIRONMENT as DISPOSABLE_ENVIRONMENT,
    NETWORK_ID,
    PROTOCOL_VERSION,
)
from .node_role_model import (
    CORE_RESERVED_STATES,
    CORE_ROLE,
    MODEL_VERSION,
)

PROFILE = "l28-disposable-core-process-entrypoint/v0.1"
LIFECYCLE_POLICY_VERSION = "l28-disposable-core-process-lifecycle-policy/v0.1"
MAX_REQUEST_BYTES = 8192
ZERO_INSTANCE_ID = "0" * 64
INSTANCE_MODE = "single_core_disposable"
FORBIDDEN_ENVIRONMENTS = frozenset({"MAIN", "CANONICAL", "HISTORICAL", "PRODUCTION"})
FORBIDDEN_PATH_SEGMENTS = frozenset(
    {"MAIN", "CANONICAL", "HISTORICAL", "PRODUCTION", "shared"}
)

REQUEST_FIELDS = (
    "entrypoint_version",
    "environment",
    "identity_evidence",
    "lifecycle_policy_evidence",
    "sandbox",
    "process_intent",
    "execution_authorized",
    "process_launch_authorized",
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

LIFECYCLE_EVIDENCE_FIELDS = (
    "ok",
    "code",
    "role",
    "previous_state",
    "requested_state",
    "resulting_state",
    "model_version",
    "policy_version",
    "network_id",
    "chain_id",
    "genesis_digest",
    "protocol_version",
    "identity_report_id",
    "execution_authorized",
    "detail",
)

SANDBOX_FIELDS = (
    "data_dir_tag",
    "environment",
    "network_id",
    "chain_id",
    "genesis_digest",
    "instance_id",
    "exclusive_ownership",
    "path_lexeme",
)

PROCESS_INTENT_FIELDS = (
    "offline",
    "transport_enabled",
    "instance_mode",
)

STABLE_CODES = (
    "preflight_ok",
    "input_type_invalid",
    "input_too_large",
    "encoding_invalid",
    "json_invalid",
    "duplicate_key",
    "invalid_top_level",
    "schema_invalid",
    "entrypoint_version_unsupported",
    "environment_invalid",
    "historical_import_forbidden",
    "execution_authorized_invalid",
    "process_launch_authorized_invalid",
    "identity_evidence_invalid",
    "lifecycle_policy_evidence_invalid",
    "evidence_mismatch",
    "lifecycle_state_invalid",
    "reserved_state_unreachable",
    "sandbox_descriptor_invalid",
    "ownership_collision",
    "process_intent_invalid",
    "internal_error",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class _DuplicateKey(ValueError):
    pass


class _PreflightError(ValueError):
    def __init__(
        self,
        code: str,
        *,
        entrypoint_version: str = "",
        environment: str = "",
        lifecycle_resulting_state: str = "",
    ) -> None:
        super().__init__(code)
        self.code = code
        self.entrypoint_version = entrypoint_version
        self.environment = environment
        self.lifecycle_resulting_state = lifecycle_resulting_state


@dataclass(frozen=True)
class CoreEntrypointResult:
    ok: bool
    code: str
    entrypoint_version: str = ""
    environment: str = ""
    network_id: str = ""
    chain_id: str = ""
    genesis_digest: str = ""
    protocol_version: str = ""
    identity_report_id: str = ""
    lifecycle_policy_version: str = ""
    lifecycle_resulting_state: str = ""
    sandbox_instance_id: str = ""
    preflight_ok: bool = False
    process_launch_authorized: bool = False
    execution_authorized: bool = False
    report_id: str = ""
    detail: str = ""


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise _PreflightError("json_invalid")


def _failure(
    code: str,
    *,
    entrypoint_version: str = "",
    environment: str = "",
    lifecycle_resulting_state: str = "",
) -> CoreEntrypointResult:
    return CoreEntrypointResult(
        False,
        code,
        entrypoint_version=entrypoint_version,
        environment=environment,
        lifecycle_resulting_state=lifecycle_resulting_state,
        preflight_ok=False,
        process_launch_authorized=False,
        execution_authorized=False,
        report_id="",
        detail="",
    )


def _canonical_report_id(request: Mapping[str, Any]) -> str:
    payload = json.dumps(
        request,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _success(
    *,
    request: Mapping[str, Any],
    identity: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    sandbox: Mapping[str, Any],
) -> CoreEntrypointResult:
    return CoreEntrypointResult(
        True,
        "preflight_ok",
        entrypoint_version=PROFILE,
        environment=DISPOSABLE_ENVIRONMENT,
        network_id=str(identity["network_id"]),
        chain_id=str(identity["chain_id"]),
        genesis_digest=str(identity["genesis_digest"]),
        protocol_version=str(identity["protocol_version"]),
        identity_report_id=str(identity["report_id"]),
        lifecycle_policy_version=str(lifecycle["policy_version"]),
        lifecycle_resulting_state=str(lifecycle["resulting_state"]),
        sandbox_instance_id=str(sandbox["instance_id"]),
        preflight_ok=True,
        process_launch_authorized=False,
        execution_authorized=False,
        report_id=_canonical_report_id(request),
        detail="",
    )


def _decode(payload: str | bytes) -> str:
    if isinstance(payload, bytes):
        if len(payload) > MAX_REQUEST_BYTES:
            raise _PreflightError("input_too_large")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _PreflightError("encoding_invalid") from exc
    if isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _PreflightError("encoding_invalid") from exc
        if len(encoded) > MAX_REQUEST_BYTES:
            raise _PreflightError("input_too_large")
        return payload
    raise _PreflightError("input_type_invalid")


def _parse(payload: str | bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            _decode(payload),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise _PreflightError("duplicate_key") from exc
    except _PreflightError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _PreflightError("json_invalid") from exc
    if not isinstance(value, dict):
        raise _PreflightError("invalid_top_level")
    return value


def _require_hex64(value: Any, *, code: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise _PreflightError(code)
    return value


def _contains_admission_authorized(value: Any) -> bool:
    if isinstance(value, dict):
        if "admission_authorized" in value:
            return True
        return any(_contains_admission_authorized(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_admission_authorized(item) for item in value)
    return False


def _path_segments(path_lexeme: str) -> list[str]:
    normalized = path_lexeme.replace("\\", "/")
    return [part for part in normalized.split("/") if part not in ("", ".")]


def _validate_path_lexeme(path_lexeme: str) -> None:
    if not isinstance(path_lexeme, str) or not path_lexeme or path_lexeme.strip() == "":
        raise _PreflightError("sandbox_descriptor_invalid")
    if path_lexeme in {"/", "\\"}:
        raise _PreflightError("sandbox_descriptor_invalid")
    if path_lexeme in {".", "./"}:
        raise _PreflightError("sandbox_descriptor_invalid")
    if (
        path_lexeme == "~"
        or path_lexeme.startswith("~/")
        or path_lexeme.startswith("~\\")
        or path_lexeme.startswith("%USERPROFILE%")
        or path_lexeme.startswith("$HOME")
    ):
        raise _PreflightError("sandbox_descriptor_invalid")
    raw_parts = path_lexeme.replace("\\", "/").split("/")
    if ".." in raw_parts:
        raise _PreflightError("sandbox_descriptor_invalid")
    segments = _path_segments(path_lexeme)
    if DATA_DIR_TAG not in segments:
        raise _PreflightError("sandbox_descriptor_invalid")
    if any(segment in FORBIDDEN_PATH_SEGMENTS for segment in segments):
        raise _PreflightError("sandbox_descriptor_invalid")


def _validate_identity_evidence(evidence: Any) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise _PreflightError("identity_evidence_invalid")
    if tuple(evidence.keys()) != IDENTITY_EVIDENCE_FIELDS:
        raise _PreflightError("identity_evidence_invalid")
    if not isinstance(evidence["ok"], bool):
        raise _PreflightError("identity_evidence_invalid")
    if evidence["execution_authorized"] is not False:
        raise _PreflightError("identity_evidence_invalid")
    if evidence["ok"] is not True:
        raise _PreflightError("identity_evidence_invalid")
    if evidence["code"] != "ok":
        raise _PreflightError("identity_evidence_invalid")
    if evidence["network_id"] != NETWORK_ID:
        raise _PreflightError("identity_evidence_invalid")
    if evidence["protocol_version"] != PROTOCOL_VERSION:
        raise _PreflightError("identity_evidence_invalid")
    _require_hex64(evidence["chain_id"], code="identity_evidence_invalid")
    _require_hex64(evidence["genesis_digest"], code="identity_evidence_invalid")
    _require_hex64(evidence["report_id"], code="identity_evidence_invalid")
    return evidence


def _validate_lifecycle_structure(evidence: Any) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise _PreflightError("lifecycle_policy_evidence_invalid")
    if tuple(evidence.keys()) != LIFECYCLE_EVIDENCE_FIELDS:
        raise _PreflightError("lifecycle_policy_evidence_invalid")
    if not isinstance(evidence["ok"], bool):
        raise _PreflightError("lifecycle_policy_evidence_invalid")
    if evidence["ok"] is not True:
        raise _PreflightError("lifecycle_policy_evidence_invalid")
    if evidence["code"] != "transitioned":
        raise _PreflightError("lifecycle_policy_evidence_invalid")
    if evidence["role"] != CORE_ROLE:
        raise _PreflightError("lifecycle_policy_evidence_invalid")
    for key in ("previous_state", "requested_state", "resulting_state"):
        value = evidence[key]
        if not isinstance(value, str) or not value:
            raise _PreflightError("lifecycle_policy_evidence_invalid")
    if evidence["model_version"] != MODEL_VERSION:
        raise _PreflightError("lifecycle_policy_evidence_invalid")
    if evidence["policy_version"] != LIFECYCLE_POLICY_VERSION:
        raise _PreflightError("lifecycle_policy_evidence_invalid")
    if evidence["network_id"] != NETWORK_ID:
        raise _PreflightError("lifecycle_policy_evidence_invalid")
    _require_hex64(evidence["chain_id"], code="lifecycle_policy_evidence_invalid")
    _require_hex64(evidence["genesis_digest"], code="lifecycle_policy_evidence_invalid")
    if evidence["protocol_version"] != PROTOCOL_VERSION:
        raise _PreflightError("lifecycle_policy_evidence_invalid")
    _require_hex64(evidence["identity_report_id"], code="lifecycle_policy_evidence_invalid")
    if evidence["execution_authorized"] is not False:
        raise _PreflightError("lifecycle_policy_evidence_invalid")
    if evidence["detail"] != "":
        raise _PreflightError("lifecycle_policy_evidence_invalid")
    return evidence


def _classify_lifecycle_states(
    evidence: Mapping[str, Any],
    *,
    entrypoint_version: str,
    environment: str,
) -> None:
    states = (
        evidence["previous_state"],
        evidence["requested_state"],
        evidence["resulting_state"],
    )
    for state in states:
        if state in CORE_RESERVED_STATES:
            raise _PreflightError(
                "reserved_state_unreachable",
                entrypoint_version=entrypoint_version,
                environment=environment,
                lifecycle_resulting_state=str(state),
            )
    if states != ("CREATED", "DISPOSABLE_TEST_READY", "DISPOSABLE_TEST_READY"):
        offender = ""
        expected = ("CREATED", "DISPOSABLE_TEST_READY", "DISPOSABLE_TEST_READY")
        for actual, want in zip(states, expected, strict=True):
            if actual != want:
                offender = str(actual)
                break
        raise _PreflightError(
            "lifecycle_state_invalid",
            entrypoint_version=entrypoint_version,
            environment=environment,
            lifecycle_resulting_state=offender,
        )


def _validate_sandbox_structure(sandbox: Any) -> dict[str, Any]:
    if not isinstance(sandbox, dict):
        raise _PreflightError("sandbox_descriptor_invalid")
    if tuple(sandbox.keys()) != SANDBOX_FIELDS:
        raise _PreflightError("sandbox_descriptor_invalid")
    if sandbox["data_dir_tag"] != DATA_DIR_TAG:
        raise _PreflightError("sandbox_descriptor_invalid")
    if sandbox["environment"] != DISPOSABLE_ENVIRONMENT:
        raise _PreflightError("sandbox_descriptor_invalid")
    if sandbox["network_id"] != NETWORK_ID:
        raise _PreflightError("sandbox_descriptor_invalid")
    _require_hex64(sandbox["chain_id"], code="sandbox_descriptor_invalid")
    _require_hex64(sandbox["genesis_digest"], code="sandbox_descriptor_invalid")
    _require_hex64(sandbox["instance_id"], code="sandbox_descriptor_invalid")
    if not isinstance(sandbox["exclusive_ownership"], bool):
        raise _PreflightError("sandbox_descriptor_invalid")
    if not isinstance(sandbox["path_lexeme"], str):
        raise _PreflightError("sandbox_descriptor_invalid")
    _validate_path_lexeme(sandbox["path_lexeme"])
    return sandbox


def _validate_ownership(sandbox: Mapping[str, Any]) -> None:
    if sandbox["exclusive_ownership"] is False:
        raise _PreflightError("ownership_collision")
    if sandbox["instance_id"] == ZERO_INSTANCE_ID:
        raise _PreflightError("ownership_collision")
    if sandbox["exclusive_ownership"] is not True:
        raise _PreflightError("ownership_collision")


def _validate_process_intent(intent: Any) -> dict[str, Any]:
    if not isinstance(intent, dict):
        raise _PreflightError("process_intent_invalid")
    if tuple(intent.keys()) != PROCESS_INTENT_FIELDS:
        raise _PreflightError("process_intent_invalid")
    if intent["offline"] is not True:
        raise _PreflightError("process_intent_invalid")
    if intent["transport_enabled"] is not False:
        raise _PreflightError("process_intent_invalid")
    if intent["instance_mode"] != INSTANCE_MODE:
        raise _PreflightError("process_intent_invalid")
    return intent


def _evaluate_parsed(request: Mapping[str, Any]) -> CoreEntrypointResult:
    # Step 5 — top-level schema (nested content validated in later steps).
    if tuple(request.keys()) != REQUEST_FIELDS:
        raise _PreflightError("schema_invalid")

    entrypoint_version = request["entrypoint_version"]
    if not isinstance(entrypoint_version, str):
        raise _PreflightError("schema_invalid")
    environment = request["environment"]
    if not isinstance(environment, str):
        raise _PreflightError("schema_invalid")
    if not isinstance(request["identity_evidence"], dict):
        raise _PreflightError("schema_invalid")
    if not isinstance(request["lifecycle_policy_evidence"], dict):
        raise _PreflightError("schema_invalid")
    if not isinstance(request["sandbox"], dict):
        raise _PreflightError("schema_invalid")
    if not isinstance(request["process_intent"], dict):
        raise _PreflightError("schema_invalid")
    if not isinstance(request["execution_authorized"], bool):
        raise _PreflightError("schema_invalid")
    if not isinstance(request["process_launch_authorized"], bool):
        raise _PreflightError("schema_invalid")

    # Step 6
    if entrypoint_version != PROFILE:
        raise _PreflightError(
            "entrypoint_version_unsupported",
            entrypoint_version=entrypoint_version,
        )
    recovered_version = PROFILE

    # Steps 7–8
    if environment in FORBIDDEN_ENVIRONMENTS:
        raise _PreflightError(
            "historical_import_forbidden",
            entrypoint_version=recovered_version,
            environment=environment,
        )
    if environment != DISPOSABLE_ENVIRONMENT:
        raise _PreflightError(
            "environment_invalid",
            entrypoint_version=recovered_version,
            environment=environment,
        )

    # Steps 9–10
    if request["execution_authorized"] is not False:
        raise _PreflightError(
            "execution_authorized_invalid",
            entrypoint_version=recovered_version,
            environment=environment,
        )
    if request["process_launch_authorized"] is not False:
        raise _PreflightError(
            "process_launch_authorized_invalid",
            entrypoint_version=recovered_version,
            environment=environment,
        )

    # Step 11
    if _contains_admission_authorized(request):
        raise _PreflightError(
            "schema_invalid",
            entrypoint_version=recovered_version,
            environment=environment,
        )

    # Step 12
    try:
        identity = _validate_identity_evidence(request["identity_evidence"])
    except _PreflightError as exc:
        raise _PreflightError(
            exc.code,
            entrypoint_version=recovered_version,
            environment=environment,
        ) from exc

    # Step 13
    try:
        lifecycle = _validate_lifecycle_structure(request["lifecycle_policy_evidence"])
    except _PreflightError as exc:
        raise _PreflightError(
            exc.code,
            entrypoint_version=recovered_version,
            environment=environment,
        ) from exc

    # Steps 14–15
    _classify_lifecycle_states(
        lifecycle,
        entrypoint_version=recovered_version,
        environment=environment,
    )

    # Step 16
    try:
        sandbox = _validate_sandbox_structure(request["sandbox"])
    except _PreflightError as exc:
        raise _PreflightError(
            exc.code,
            entrypoint_version=recovered_version,
            environment=environment,
        ) from exc

    # Step 17
    try:
        _validate_ownership(sandbox)
    except _PreflightError as exc:
        raise _PreflightError(
            exc.code,
            entrypoint_version=recovered_version,
            environment=environment,
        ) from exc

    # Step 18
    if not (
        identity["network_id"]
        == lifecycle["network_id"]
        == sandbox["network_id"]
        == NETWORK_ID
        and identity["chain_id"] == lifecycle["chain_id"] == sandbox["chain_id"]
        and identity["genesis_digest"]
        == lifecycle["genesis_digest"]
        == sandbox["genesis_digest"]
        and identity["protocol_version"]
        == lifecycle["protocol_version"]
        == PROTOCOL_VERSION
        and lifecycle["identity_report_id"] == identity["report_id"]
        and sandbox["environment"] == DISPOSABLE_ENVIRONMENT
        and environment == DISPOSABLE_ENVIRONMENT
    ):
        raise _PreflightError(
            "evidence_mismatch",
            entrypoint_version=recovered_version,
            environment=environment,
        )

    # Step 19
    try:
        _validate_process_intent(request["process_intent"])
    except _PreflightError as exc:
        raise _PreflightError(
            exc.code,
            entrypoint_version=recovered_version,
            environment=environment,
        ) from exc

    # Step 21
    return _success(
        request=request,
        identity=identity,
        lifecycle=lifecycle,
        sandbox=sandbox,
    )


def evaluate_core_entrypoint_preflight_json(
    payload: str | bytes,
) -> CoreEntrypointResult:
    try:
        request = _parse(payload)
        return _evaluate_parsed(request)
    except _PreflightError as exc:
        return _failure(
            exc.code,
            entrypoint_version=exc.entrypoint_version,
            environment=exc.environment,
            lifecycle_resulting_state=exc.lifecycle_resulting_state,
        )
    except Exception:
        return _failure("internal_error")
