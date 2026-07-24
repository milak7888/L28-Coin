# SPDX-License-Identifier: Apache-2.0
"""Offline disposable sandbox directory creation-plan evaluator (Foundation 49 / F48).

Evaluates an immutable offline creation-plan request bound to a frozen Foundation
47 preflight-success projection. Does not create, inspect, or wipe directories,
spawn processes, open network listeners, or activate a testnet.
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

PROFILE = "l28-disposable-sandbox-directory-creation/v0.1"
ENTRYPOINT_PROFILE = "l28-disposable-core-process-entrypoint/v0.1"
LIFECYCLE_POLICY_VERSION = "l28-disposable-core-process-lifecycle-policy/v0.1"
MAX_REQUEST_BYTES = 8192
ZERO_INSTANCE_ID = "0" * 64
FORBIDDEN_ENVIRONMENTS = frozenset({"MAIN", "CANONICAL", "HISTORICAL", "PRODUCTION"})

REQUEST_FIELDS = (
    "creation_profile",
    "environment",
    "preflight_evidence",
    "sandbox",
    "creation_intent",
    "execution_authorized",
    "process_launch_authorized",
)

PREFLIGHT_EVIDENCE_FIELDS = (
    "ok",
    "code",
    "entrypoint_version",
    "environment",
    "network_id",
    "chain_id",
    "genesis_digest",
    "protocol_version",
    "identity_report_id",
    "lifecycle_policy_version",
    "lifecycle_resulting_state",
    "sandbox_instance_id",
    "preflight_ok",
    "process_launch_authorized",
    "execution_authorized",
    "report_id",
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

CREATION_INTENT_FIELDS = (
    "create_mode",
    "existing_path_policy",
    "symlink_policy",
    "cleanup_ownership",
    "deferred_filesystem_obligations",
)

STABLE_CODES = (
    "creation_plan_ok",
    "input_type_invalid",
    "input_too_large",
    "encoding_invalid",
    "json_invalid",
    "duplicate_key",
    "invalid_top_level",
    "schema_invalid",
    "creation_profile_unsupported",
    "environment_invalid",
    "historical_import_forbidden",
    "execution_authorized_invalid",
    "process_launch_authorized_invalid",
    "preflight_evidence_invalid",
    "sandbox_plan_invalid",
    "creation_intent_invalid",
    "evidence_mismatch",
    "internal_error",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class _DuplicateKey(ValueError):
    pass


class _PlanError(ValueError):
    def __init__(
        self,
        code: str,
        *,
        creation_profile: str = "",
        environment: str = "",
    ) -> None:
        super().__init__(code)
        self.code = code
        self.creation_profile = creation_profile
        self.environment = environment


@dataclass(frozen=True)
class SandboxCreationPlanResult:
    ok: bool
    code: str
    creation_profile: str = ""
    environment: str = ""
    network_id: str = ""
    chain_id: str = ""
    genesis_digest: str = ""
    protocol_version: str = ""
    preflight_report_id: str = ""
    sandbox_instance_id: str = ""
    path_lexeme: str = ""
    creation_plan_ok: bool = False
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
    raise _PlanError("json_invalid")


def _failure(
    code: str,
    *,
    creation_profile: str = "",
    environment: str = "",
) -> SandboxCreationPlanResult:
    return SandboxCreationPlanResult(
        False,
        code,
        creation_profile=creation_profile,
        environment=environment,
        creation_plan_ok=False,
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
    preflight: Mapping[str, Any],
    sandbox: Mapping[str, Any],
) -> SandboxCreationPlanResult:
    return SandboxCreationPlanResult(
        True,
        "creation_plan_ok",
        creation_profile=PROFILE,
        environment=DISPOSABLE_ENVIRONMENT,
        network_id=str(preflight["network_id"]),
        chain_id=str(preflight["chain_id"]),
        genesis_digest=str(preflight["genesis_digest"]),
        protocol_version=str(preflight["protocol_version"]),
        preflight_report_id=str(preflight["report_id"]),
        sandbox_instance_id=str(sandbox["instance_id"]),
        path_lexeme=str(sandbox["path_lexeme"]),
        creation_plan_ok=True,
        process_launch_authorized=False,
        execution_authorized=False,
        report_id=_canonical_report_id(request),
        detail="",
    )


def _decode(payload: str | bytes) -> str:
    if isinstance(payload, bytes):
        if len(payload) > MAX_REQUEST_BYTES:
            raise _PlanError("input_too_large")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _PlanError("encoding_invalid") from exc
    if isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _PlanError("encoding_invalid") from exc
        if len(encoded) > MAX_REQUEST_BYTES:
            raise _PlanError("input_too_large")
        return payload
    raise _PlanError("input_type_invalid")


def _parse(payload: str | bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            _decode(payload),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise _PlanError("duplicate_key") from exc
    except _PlanError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _PlanError("json_invalid") from exc
    if not isinstance(value, dict):
        raise _PlanError("invalid_top_level")
    return value


def _require_hex64(value: Any, *, code: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise _PlanError(code)
    return value


def _contains_forbidden_authority(value: Any, field: str) -> bool:
    if isinstance(value, dict):
        if field in value:
            return True
        return any(_contains_forbidden_authority(item, field) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_authority(item, field) for item in value)
    return False


def _validate_preflight_evidence(evidence: Any) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise _PlanError("preflight_evidence_invalid")
    if tuple(evidence.keys()) != PREFLIGHT_EVIDENCE_FIELDS:
        raise _PlanError("preflight_evidence_invalid")
    if not isinstance(evidence["ok"], bool):
        raise _PlanError("preflight_evidence_invalid")
    if evidence["ok"] is not True:
        raise _PlanError("preflight_evidence_invalid")
    if evidence["code"] != "preflight_ok":
        raise _PlanError("preflight_evidence_invalid")
    if evidence["entrypoint_version"] != ENTRYPOINT_PROFILE:
        raise _PlanError("preflight_evidence_invalid")
    if evidence["environment"] != DISPOSABLE_ENVIRONMENT:
        raise _PlanError("preflight_evidence_invalid")
    if evidence["network_id"] != NETWORK_ID:
        raise _PlanError("preflight_evidence_invalid")
    _require_hex64(evidence["chain_id"], code="preflight_evidence_invalid")
    _require_hex64(evidence["genesis_digest"], code="preflight_evidence_invalid")
    if evidence["protocol_version"] != PROTOCOL_VERSION:
        raise _PlanError("preflight_evidence_invalid")
    _require_hex64(evidence["identity_report_id"], code="preflight_evidence_invalid")
    if evidence["lifecycle_policy_version"] != LIFECYCLE_POLICY_VERSION:
        raise _PlanError("preflight_evidence_invalid")
    if evidence["lifecycle_resulting_state"] != "DISPOSABLE_TEST_READY":
        raise _PlanError("preflight_evidence_invalid")
    instance_id = _require_hex64(
        evidence["sandbox_instance_id"], code="preflight_evidence_invalid"
    )
    if instance_id == ZERO_INSTANCE_ID:
        raise _PlanError("preflight_evidence_invalid")
    if evidence["preflight_ok"] is not True:
        raise _PlanError("preflight_evidence_invalid")
    if evidence["process_launch_authorized"] is not False:
        raise _PlanError("preflight_evidence_invalid")
    if evidence["execution_authorized"] is not False:
        raise _PlanError("preflight_evidence_invalid")
    _require_hex64(evidence["report_id"], code="preflight_evidence_invalid")
    if evidence["detail"] != "":
        raise _PlanError("preflight_evidence_invalid")
    return evidence


def _validate_sandbox_plan(sandbox: Any) -> dict[str, Any]:
    if not isinstance(sandbox, dict):
        raise _PlanError("sandbox_plan_invalid")
    if tuple(sandbox.keys()) != SANDBOX_FIELDS:
        raise _PlanError("sandbox_plan_invalid")
    if sandbox["data_dir_tag"] != DATA_DIR_TAG:
        raise _PlanError("sandbox_plan_invalid")
    if sandbox["environment"] != DISPOSABLE_ENVIRONMENT:
        raise _PlanError("sandbox_plan_invalid")
    if sandbox["network_id"] != NETWORK_ID:
        raise _PlanError("sandbox_plan_invalid")
    _require_hex64(sandbox["chain_id"], code="sandbox_plan_invalid")
    _require_hex64(sandbox["genesis_digest"], code="sandbox_plan_invalid")
    instance_id = _require_hex64(sandbox["instance_id"], code="sandbox_plan_invalid")
    if instance_id == ZERO_INSTANCE_ID:
        raise _PlanError("sandbox_plan_invalid")
    if sandbox["exclusive_ownership"] is not True:
        raise _PlanError("sandbox_plan_invalid")
    path_lexeme = sandbox["path_lexeme"]
    if not isinstance(path_lexeme, str) or path_lexeme.strip() == "":
        raise _PlanError("sandbox_plan_invalid")
    return sandbox


def _validate_creation_intent(intent: Any) -> dict[str, Any]:
    if not isinstance(intent, dict):
        raise _PlanError("creation_intent_invalid")
    if tuple(intent.keys()) != CREATION_INTENT_FIELDS:
        raise _PlanError("creation_intent_invalid")
    if intent["create_mode"] != "exclusive_create_new":
        raise _PlanError("creation_intent_invalid")
    if intent["existing_path_policy"] != "reject":
        raise _PlanError("creation_intent_invalid")
    if intent["symlink_policy"] != "reject":
        raise _PlanError("creation_intent_invalid")
    if intent["cleanup_ownership"] != "tagged_disposable_only":
        raise _PlanError("creation_intent_invalid")
    if intent["deferred_filesystem_obligations"] is not True:
        raise _PlanError("creation_intent_invalid")
    return intent


def _validate_evidence_binding(
    preflight: Mapping[str, Any],
    sandbox: Mapping[str, Any],
) -> None:
    if not (
        sandbox["chain_id"] == preflight["chain_id"]
        and sandbox["genesis_digest"] == preflight["genesis_digest"]
        and sandbox["instance_id"] == preflight["sandbox_instance_id"]
        and sandbox["network_id"] == preflight["network_id"] == NETWORK_ID
        and sandbox["environment"]
        == preflight["environment"]
        == DISPOSABLE_ENVIRONMENT
        and sandbox["data_dir_tag"] == DATA_DIR_TAG
        and preflight["protocol_version"] == PROTOCOL_VERSION
    ):
        raise _PlanError("evidence_mismatch")


def _evaluate_parsed(request: Mapping[str, Any]) -> SandboxCreationPlanResult:
    # Step 5 — top-level schema (nested content validated in later steps).
    if tuple(request.keys()) != REQUEST_FIELDS:
        raise _PlanError("schema_invalid")

    creation_profile = request["creation_profile"]
    if not isinstance(creation_profile, str):
        raise _PlanError("schema_invalid")
    environment = request["environment"]
    if not isinstance(environment, str):
        raise _PlanError("schema_invalid")
    if not isinstance(request["preflight_evidence"], dict):
        raise _PlanError("schema_invalid")
    if not isinstance(request["sandbox"], dict):
        raise _PlanError("schema_invalid")
    if not isinstance(request["creation_intent"], dict):
        raise _PlanError("schema_invalid")
    if not isinstance(request["execution_authorized"], bool):
        raise _PlanError("schema_invalid")
    if not isinstance(request["process_launch_authorized"], bool):
        raise _PlanError("schema_invalid")

    # Step 6
    if creation_profile != PROFILE:
        raise _PlanError(
            "creation_profile_unsupported",
            creation_profile=creation_profile,
        )
    recovered_profile = PROFILE

    # Steps 7–8
    if environment in FORBIDDEN_ENVIRONMENTS:
        raise _PlanError(
            "historical_import_forbidden",
            creation_profile=recovered_profile,
            environment=environment,
        )
    if environment != DISPOSABLE_ENVIRONMENT:
        raise _PlanError(
            "environment_invalid",
            creation_profile=recovered_profile,
            environment=environment,
        )

    # Steps 9–10
    if request["execution_authorized"] is not False:
        raise _PlanError(
            "execution_authorized_invalid",
            creation_profile=recovered_profile,
            environment=environment,
        )
    if request["process_launch_authorized"] is not False:
        raise _PlanError(
            "process_launch_authorized_invalid",
            creation_profile=recovered_profile,
            environment=environment,
        )

    # Steps 11–12
    if _contains_forbidden_authority(request, "admission_authorized"):
        raise _PlanError(
            "schema_invalid",
            creation_profile=recovered_profile,
            environment=environment,
        )
    if _contains_forbidden_authority(request, "filesystem_create_authorized"):
        raise _PlanError(
            "schema_invalid",
            creation_profile=recovered_profile,
            environment=environment,
        )

    # Step 13
    try:
        preflight = _validate_preflight_evidence(request["preflight_evidence"])
    except _PlanError as exc:
        raise _PlanError(
            exc.code,
            creation_profile=recovered_profile,
            environment=environment,
        ) from exc

    # Step 14
    try:
        sandbox = _validate_sandbox_plan(request["sandbox"])
    except _PlanError as exc:
        raise _PlanError(
            exc.code,
            creation_profile=recovered_profile,
            environment=environment,
        ) from exc

    # Step 15
    try:
        _validate_creation_intent(request["creation_intent"])
    except _PlanError as exc:
        raise _PlanError(
            exc.code,
            creation_profile=recovered_profile,
            environment=environment,
        ) from exc

    # Step 16
    try:
        _validate_evidence_binding(preflight, sandbox)
    except _PlanError as exc:
        raise _PlanError(
            exc.code,
            creation_profile=recovered_profile,
            environment=environment,
        ) from exc

    # Step 18
    return _success(request=request, preflight=preflight, sandbox=sandbox)


def evaluate_sandbox_directory_creation_plan_json(
    payload: str | bytes,
) -> SandboxCreationPlanResult:
    try:
        request = _parse(payload)
        return _evaluate_parsed(request)
    except _PlanError as exc:
        return _failure(
            exc.code,
            creation_profile=exc.creation_profile,
            environment=exc.environment,
        )
    except Exception:
        return _failure("internal_error")
