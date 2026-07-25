# SPDX-License-Identifier: Apache-2.0
"""Governed disposable sandbox lifecycle integration (Foundation 55 / F54).

Composes Foundation 51 materialization, identity verification, and Foundation 53
cleanup under a single fail-closed lifecycle profile.

Invokes F51 and F53 as subordinate evaluators only. Does not reimplement
exclusive create or constrained delete algorithms, does not accept stopped
process-stop mode, and does not perform F38 post-wipe genesis revalidation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import time
from dataclasses import dataclass
from typing import Any, Mapping

from .disposable_network_identity_genesis_binding import (
    DATA_DIR_TAG,
    ENVIRONMENT as DISPOSABLE_ENVIRONMENT,
    NETWORK_ID,
    PROTOCOL_VERSION,
)
from .disposable_sandbox_directory_cleanup import (
    MATERIALIZATION_EVIDENCE_FIELDS,
    PROFILE as CLEANUP_PROFILE,
    cleanup_disposable_sandbox_directory_json,
)
from .disposable_sandbox_directory_materialization import (
    REQUEST_FIELDS as MATERIALIZATION_REQUEST_FIELDS,
    materialize_disposable_sandbox_directory_json,
)

PROFILE = "l28-disposable-sandbox-lifecycle-integration/v0.1"
MAX_REQUEST_BYTES = 16384
ZERO_INSTANCE_ID = "0" * 64
FORBIDDEN_ENVIRONMENTS = frozenset({"MAIN", "CANONICAL", "HISTORICAL", "PRODUCTION"})
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

REQUEST_FIELDS = (
    "lifecycle_profile",
    "environment",
    "lifecycle_authority",
    "materialization_request",
    "cleanup_handoff",
    "process_stop_evidence",
    "execution_authorized",
    "process_launch_authorized",
)

LIFECYCLE_AUTHORITY_FIELDS = (
    "lifecycle_authorized",
    "trusted_root",
    "sandbox_instance_id",
    "data_dir_tag",
    "attempt_id",
    "not_after_unix",
)

CLEANUP_HANDOFF_FIELDS = (
    "cleanup_authorized",
    "trusted_root",
    "sandbox_instance_id",
    "data_dir_tag",
    "attempt_id",
    "not_after_unix",
)

STOP_NEVER_STARTED_FIELDS = ("mode", "sandbox_instance_id")

FORBIDDEN_AUTHORITY_FIELDS = frozenset(
    {
        "admission_authorized",
        "filesystem_create_authorized",
        "wipe_authorized",
        "process_authorized",
        "node_authorized",
        "miner_authorized",
        "wallet_authorized",
        "network_authorized",
        "transaction_authorized",
        "ledger_authorized",
        "consensus_authorized",
        "deployment_authorized",
        "sovereign_brain_authorized",
        "SovereignBrain",
    }
)

STABLE_CODES = (
    "lifecycle_ok",
    "input_type_invalid",
    "input_too_large",
    "encoding_invalid",
    "json_invalid",
    "duplicate_key",
    "invalid_top_level",
    "schema_invalid",
    "lifecycle_profile_unsupported",
    "environment_invalid",
    "historical_import_forbidden",
    "execution_authorized_invalid",
    "process_launch_authorized_invalid",
    "lifecycle_authority_invalid",
    "lifecycle_authority_mismatch",
    "lifecycle_authority_expired",
    "stage_binding_invalid",
    "materialization_request_invalid",
    "cleanup_handoff_invalid",
    "process_stop_evidence_invalid",
    "stopped_mode_forbidden",
    "materialization_stage_failed",
    "identity_verify_target_absent",
    "identity_verify_symlink_rejected",
    "identity_verify_mismatch",
    "identity_verify_containment_failure",
    "identity_verify_substitution_ambiguous",
    "cleanup_stage_failed",
    "lifecycle_partial_failed",
    "post_lifecycle_verification_failed",
    "internal_error",
)


class _DuplicateKey(ValueError):
    pass


class _LifecycleError(ValueError):
    def __init__(
        self,
        code: str,
        *,
        lifecycle_profile: str = "",
        environment: str = "",
        failed_stage: str = "",
        stage_code: str = "",
        materialization: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.lifecycle_profile = lifecycle_profile
        self.environment = environment
        self.failed_stage = failed_stage
        self.stage_code = stage_code
        self.materialization = materialization


@dataclass(frozen=True)
class SandboxLifecycleResult:
    ok: bool
    code: str
    lifecycle_profile: str = ""
    environment: str = ""
    network_id: str = ""
    chain_id: str = ""
    genesis_digest: str = ""
    protocol_version: str = ""
    sandbox_instance_id: str = ""
    data_dir_tag: str = ""
    child_name: str = ""
    materialization_path: str = ""
    materialization_report_id: str = ""
    cleanup_report_id: str = ""
    failed_stage: str = ""
    stage_code: str = ""
    lifecycle_ok: bool = False
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
    raise _LifecycleError("json_invalid")


def _wire(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")


def _canonical_report_id(request: Mapping[str, Any]) -> str:
    return hashlib.sha256(_wire(request)).hexdigest()


def _failure(
    code: str,
    *,
    lifecycle_profile: str = "",
    environment: str = "",
    failed_stage: str = "",
    stage_code: str = "",
    materialization: Mapping[str, Any] | None = None,
) -> SandboxLifecycleResult:
    mat = materialization or {}
    populated = bool(mat)
    return SandboxLifecycleResult(
        False,
        code,
        lifecycle_profile=lifecycle_profile,
        environment=environment,
        network_id=str(mat.get("network_id", "")) if populated else "",
        chain_id=str(mat.get("chain_id", "")) if populated else "",
        genesis_digest=str(mat.get("genesis_digest", "")) if populated else "",
        protocol_version=str(mat.get("protocol_version", "")) if populated else "",
        sandbox_instance_id=str(mat.get("sandbox_instance_id", "")) if populated else "",
        data_dir_tag=str(mat.get("data_dir_tag", "")) if populated else "",
        child_name=str(mat.get("child_name", "")) if populated else "",
        materialization_path=str(mat.get("materialization_path", "")) if populated else "",
        materialization_report_id=str(mat.get("report_id", "")) if populated else "",
        cleanup_report_id="",
        failed_stage=failed_stage,
        stage_code=stage_code,
        lifecycle_ok=False,
        process_launch_authorized=False,
        execution_authorized=False,
        report_id="",
        detail="",
    )


def _success(
    *,
    request: Mapping[str, Any],
    materialization: Mapping[str, Any],
    cleanup_report_id: str,
) -> SandboxLifecycleResult:
    return SandboxLifecycleResult(
        True,
        "lifecycle_ok",
        lifecycle_profile=PROFILE,
        environment=DISPOSABLE_ENVIRONMENT,
        network_id=str(materialization["network_id"]),
        chain_id=str(materialization["chain_id"]),
        genesis_digest=str(materialization["genesis_digest"]),
        protocol_version=str(materialization["protocol_version"]),
        sandbox_instance_id=str(materialization["sandbox_instance_id"]),
        data_dir_tag=DATA_DIR_TAG,
        child_name=str(materialization["child_name"]),
        materialization_path=str(materialization["materialization_path"]),
        materialization_report_id=str(materialization["report_id"]),
        cleanup_report_id=cleanup_report_id,
        failed_stage="",
        stage_code="",
        lifecycle_ok=True,
        process_launch_authorized=False,
        execution_authorized=False,
        report_id=_canonical_report_id(request),
        detail="",
    )


def _decode(payload: str | bytes) -> str:
    if isinstance(payload, bytes):
        if len(payload) > MAX_REQUEST_BYTES:
            raise _LifecycleError("input_too_large")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _LifecycleError("encoding_invalid") from exc
    if isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _LifecycleError("encoding_invalid") from exc
        if len(encoded) > MAX_REQUEST_BYTES:
            raise _LifecycleError("input_too_large")
        return payload
    raise _LifecycleError("input_type_invalid")


def _parse(payload: str | bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            _decode(payload),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise _LifecycleError("duplicate_key") from exc
    except _LifecycleError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _LifecycleError("json_invalid") from exc
    if not isinstance(value, dict):
        raise _LifecycleError("invalid_top_level")
    return value


def _require_hex64(value: Any, *, code: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise _LifecycleError(code)
    return value


def _validate_lexical_trusted_root(path: str, *, code: str) -> str:
    if not isinstance(path, str) or path == "":
        raise _LifecycleError(code)
    if "\0" in path:
        raise _LifecycleError(code)
    if path.startswith("~") or "$" in path:
        raise _LifecycleError(code)
    if "\\" in path:
        raise _LifecycleError(code)
    if not path.startswith("/"):
        raise _LifecycleError(code)
    if path != "/" and path.endswith("/"):
        raise _LifecycleError(code)
    if "//" in path:
        raise _LifecycleError(code)
    segments = path.split("/")[1:] if path != "/" else []
    for segment in segments:
        if segment in ("", ".", ".."):
            raise _LifecycleError(code)
    return path


def _scan_forbidden(value: Any, *, ctx: str = "") -> bool:
    """Reject §8.6 forbidden fields; allow mat/cleanup authorized only in place."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FORBIDDEN_AUTHORITY_FIELDS:
                return True
            if key == "materialization_authorized" and ctx != "mat_auth":
                return True
            if key == "cleanup_authorized" and ctx != "cleanup_handoff":
                return True
            if key == "materialization_request" and ctx == "":
                if _scan_forbidden(item, ctx="mat_req"):
                    return True
                continue
            if key == "materialization_authority" and ctx == "mat_req":
                if _scan_forbidden(item, ctx="mat_auth"):
                    return True
                continue
            if key == "cleanup_handoff" and ctx == "":
                if _scan_forbidden(item, ctx="cleanup_handoff"):
                    return True
                continue
            if _scan_forbidden(item, ctx=ctx):
                return True
        return False
    if isinstance(value, list):
        return any(_scan_forbidden(item, ctx=ctx) for item in value)
    return False


def _is_special(mode: int) -> bool:
    return not (stat.S_ISREG(mode) or stat.S_ISDIR(mode) or stat.S_ISLNK(mode))


def _materialization_path_for(trusted_root: str, child_name: str) -> str:
    if trusted_root == "/":
        return f"/{child_name}"
    return f"{trusted_root}/{child_name}"


def _result_to_evidence(result: Any) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    for field in MATERIALIZATION_EVIDENCE_FIELDS:
        evidence[field] = getattr(result, field)
    return evidence


def _validate_lifecycle_authority(authority: Any) -> dict[str, Any]:
    if not isinstance(authority, dict):
        raise _LifecycleError("lifecycle_authority_invalid")
    if tuple(authority.keys()) != LIFECYCLE_AUTHORITY_FIELDS:
        raise _LifecycleError("lifecycle_authority_invalid")
    if not isinstance(authority["lifecycle_authorized"], bool):
        raise _LifecycleError("lifecycle_authority_invalid")
    if authority["lifecycle_authorized"] is not True:
        raise _LifecycleError("lifecycle_authority_invalid")
    if not isinstance(authority["trusted_root"], str):
        raise _LifecycleError("lifecycle_authority_invalid")
    _validate_lexical_trusted_root(
        authority["trusted_root"], code="lifecycle_authority_invalid"
    )
    _require_hex64(
        authority["sandbox_instance_id"], code="lifecycle_authority_invalid"
    )
    if authority["sandbox_instance_id"] == ZERO_INSTANCE_ID:
        raise _LifecycleError("lifecycle_authority_invalid")
    if not isinstance(authority["data_dir_tag"], str):
        raise _LifecycleError("lifecycle_authority_invalid")
    if authority["data_dir_tag"] != DATA_DIR_TAG:
        raise _LifecycleError("lifecycle_authority_mismatch")
    _require_hex64(authority["attempt_id"], code="lifecycle_authority_invalid")
    not_after = authority["not_after_unix"]
    if isinstance(not_after, bool) or not isinstance(not_after, int) or not_after < 0:
        raise _LifecycleError("lifecycle_authority_invalid")
    return authority


def _validate_materialization_request_shape(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise _LifecycleError("materialization_request_invalid")
    if tuple(request.keys()) != MATERIALIZATION_REQUEST_FIELDS:
        raise _LifecycleError("materialization_request_invalid")
    if not isinstance(request["materialization_profile"], str):
        raise _LifecycleError("materialization_request_invalid")
    if not isinstance(request["environment"], str):
        raise _LifecycleError("materialization_request_invalid")
    if not isinstance(request["plan_evidence"], dict):
        raise _LifecycleError("materialization_request_invalid")
    if not isinstance(request["materialization_authority"], dict):
        raise _LifecycleError("materialization_request_invalid")
    if not isinstance(request["trusted_root"], str):
        raise _LifecycleError("materialization_request_invalid")
    if not isinstance(request["execution_authorized"], bool):
        raise _LifecycleError("materialization_request_invalid")
    if not isinstance(request["process_launch_authorized"], bool):
        raise _LifecycleError("materialization_request_invalid")
    return request


def _validate_cleanup_handoff(handoff: Any) -> dict[str, Any]:
    if not isinstance(handoff, dict):
        raise _LifecycleError("cleanup_handoff_invalid")
    if tuple(handoff.keys()) != CLEANUP_HANDOFF_FIELDS:
        raise _LifecycleError("cleanup_handoff_invalid")
    if handoff["cleanup_authorized"] is not True:
        raise _LifecycleError("cleanup_handoff_invalid")
    if not isinstance(handoff["trusted_root"], str):
        raise _LifecycleError("cleanup_handoff_invalid")
    _require_hex64(handoff["sandbox_instance_id"], code="cleanup_handoff_invalid")
    if not isinstance(handoff["data_dir_tag"], str):
        raise _LifecycleError("cleanup_handoff_invalid")
    _require_hex64(handoff["attempt_id"], code="cleanup_handoff_invalid")
    not_after = handoff["not_after_unix"]
    if isinstance(not_after, bool) or not isinstance(not_after, int) or not_after < 0:
        raise _LifecycleError("cleanup_handoff_invalid")
    return handoff


def _validate_process_stop(evidence: Any) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise _LifecycleError("process_stop_evidence_invalid")
    mode = evidence.get("mode")
    if mode == "stopped":
        raise _LifecycleError("stopped_mode_forbidden")
    if mode != "never_started":
        raise _LifecycleError("process_stop_evidence_invalid")
    if tuple(evidence.keys()) != STOP_NEVER_STARTED_FIELDS:
        raise _LifecycleError("process_stop_evidence_invalid")
    _require_hex64(
        evidence["sandbox_instance_id"], code="process_stop_evidence_invalid"
    )
    return evidence


def _identity_verify(
    *,
    evidence: Mapping[str, Any],
    trusted_root: str,
    root_stat: os.stat_result,
) -> None:
    child_name = str(evidence["child_name"])
    materialization_path = str(evidence["materialization_path"])
    instance_id = str(evidence["sandbox_instance_id"])
    expected_child = f"{DATA_DIR_TAG}-{instance_id}"
    expected_path = _materialization_path_for(trusted_root, child_name)

    if materialization_path != expected_path or child_name != expected_child:
        raise _LifecycleError(
            "identity_verify_mismatch",
            failed_stage="identity_verify",
            materialization=evidence,
        )

    try:
        tgt_stat = os.lstat(materialization_path)
    except FileNotFoundError as exc:
        raise _LifecycleError(
            "identity_verify_target_absent",
            failed_stage="identity_verify",
            materialization=evidence,
        ) from exc
    except OSError as exc:
        raise _LifecycleError(
            "identity_verify_substitution_ambiguous",
            failed_stage="identity_verify",
            materialization=evidence,
        ) from exc

    if stat.S_ISLNK(tgt_stat.st_mode) or _is_special(tgt_stat.st_mode):
        raise _LifecycleError(
            "identity_verify_symlink_rejected",
            failed_stage="identity_verify",
            materialization=evidence,
        )
    if not stat.S_ISDIR(tgt_stat.st_mode) or os.path.basename(materialization_path) != child_name:
        raise _LifecycleError(
            "identity_verify_mismatch",
            failed_stage="identity_verify",
            materialization=evidence,
        )

    parent = os.path.dirname(materialization_path) or "/"
    if parent != trusted_root:
        raise _LifecycleError(
            "identity_verify_containment_failure",
            failed_stage="identity_verify",
            materialization=evidence,
        )
    try:
        parent_stat = os.lstat(parent)
    except OSError as exc:
        raise _LifecycleError(
            "identity_verify_containment_failure",
            failed_stage="identity_verify",
            materialization=evidence,
        ) from exc
    if (parent_stat.st_ino, parent_stat.st_dev) != (root_stat.st_ino, root_stat.st_dev):
        raise _LifecycleError(
            "identity_verify_containment_failure",
            failed_stage="identity_verify",
            materialization=evidence,
        )
    if tgt_stat.st_dev != root_stat.st_dev:
        raise _LifecycleError(
            "identity_verify_substitution_ambiguous",
            failed_stage="identity_verify",
            materialization=evidence,
        )


def _post_lifecycle_verify(
    *,
    materialization_path: str,
    trusted_root: str,
    root_stat: os.stat_result,
    materialization: Mapping[str, Any],
) -> None:
    try:
        os.lstat(materialization_path)
    except FileNotFoundError:
        pass
    else:
        raise _LifecycleError(
            "post_lifecycle_verification_failed",
            failed_stage="cleanup",
            stage_code="",
            materialization=materialization,
        )
    try:
        st = os.lstat(trusted_root)
    except OSError as exc:
        raise _LifecycleError(
            "post_lifecycle_verification_failed",
            failed_stage="cleanup",
            stage_code="",
            materialization=materialization,
        ) from exc
    if (st.st_ino, st.st_dev) != (root_stat.st_ino, root_stat.st_dev):
        raise _LifecycleError(
            "post_lifecycle_verification_failed",
            failed_stage="cleanup",
            stage_code="",
            materialization=materialization,
        )
    if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
        raise _LifecycleError(
            "post_lifecycle_verification_failed",
            failed_stage="cleanup",
            stage_code="",
            materialization=materialization,
        )


def _evaluate_parsed(request: Mapping[str, Any]) -> SandboxLifecycleResult:
    if tuple(request.keys()) != REQUEST_FIELDS:
        raise _LifecycleError("schema_invalid")

    lifecycle_profile = request["lifecycle_profile"]
    if not isinstance(lifecycle_profile, str):
        raise _LifecycleError("schema_invalid")
    environment = request["environment"]
    if not isinstance(environment, str):
        raise _LifecycleError("schema_invalid")
    if not isinstance(request["lifecycle_authority"], dict):
        raise _LifecycleError("schema_invalid")
    if not isinstance(request["materialization_request"], dict):
        raise _LifecycleError("schema_invalid")
    if not isinstance(request["cleanup_handoff"], dict):
        raise _LifecycleError("schema_invalid")
    if not isinstance(request["process_stop_evidence"], dict):
        raise _LifecycleError("schema_invalid")
    if not isinstance(request["execution_authorized"], bool):
        raise _LifecycleError("schema_invalid")
    if not isinstance(request["process_launch_authorized"], bool):
        raise _LifecycleError("schema_invalid")

    if lifecycle_profile != PROFILE:
        raise _LifecycleError(
            "lifecycle_profile_unsupported",
            lifecycle_profile=lifecycle_profile,
        )
    recovered_profile = PROFILE

    if environment in FORBIDDEN_ENVIRONMENTS:
        raise _LifecycleError(
            "historical_import_forbidden",
            lifecycle_profile=recovered_profile,
            environment=environment,
        )
    if environment != DISPOSABLE_ENVIRONMENT:
        raise _LifecycleError(
            "environment_invalid",
            lifecycle_profile=recovered_profile,
            environment=environment,
        )

    if request["execution_authorized"] is not False:
        raise _LifecycleError(
            "execution_authorized_invalid",
            lifecycle_profile=recovered_profile,
            environment=environment,
        )
    if request["process_launch_authorized"] is not False:
        raise _LifecycleError(
            "process_launch_authorized_invalid",
            lifecycle_profile=recovered_profile,
            environment=environment,
        )

    if _scan_forbidden(request):
        raise _LifecycleError(
            "schema_invalid",
            lifecycle_profile=recovered_profile,
            environment=environment,
        )

    def _wrap(code: str, **kwargs: Any) -> _LifecycleError:
        return _LifecycleError(
            code,
            lifecycle_profile=recovered_profile,
            environment=environment,
            **kwargs,
        )

    try:
        authority = _validate_lifecycle_authority(request["lifecycle_authority"])
    except _LifecycleError as exc:
        raise _wrap(exc.code) from exc

    if int(time.time()) >= int(authority["not_after_unix"]):
        raise _wrap("lifecycle_authority_expired")

    try:
        mat_req = _validate_materialization_request_shape(
            request["materialization_request"]
        )
    except _LifecycleError as exc:
        raise _wrap(exc.code) from exc

    try:
        nested_root = _validate_lexical_trusted_root(
            mat_req["trusted_root"], code="materialization_request_invalid"
        )
    except _LifecycleError as exc:
        raise _wrap(exc.code) from exc

    try:
        handoff = _validate_cleanup_handoff(request["cleanup_handoff"])
    except _LifecycleError as exc:
        raise _wrap(exc.code) from exc

    try:
        stop = _validate_process_stop(request["process_stop_evidence"])
    except _LifecycleError as exc:
        raise _wrap(exc.code) from exc

    # §6.4 cross-stage binds
    mat_auth = mat_req["materialization_authority"]
    plan = mat_req["plan_evidence"]
    if not isinstance(mat_auth, dict) or not isinstance(plan, dict):
        raise _wrap("materialization_request_invalid")

    bound_root = str(authority["trusted_root"])
    bound_instance = str(authority["sandbox_instance_id"])
    bound_tag = str(authority["data_dir_tag"])
    bound_attempt = str(authority["attempt_id"])
    bound_not_after = int(authority["not_after_unix"])

    if bound_root != nested_root:
        raise _wrap("stage_binding_invalid")
    if (
        mat_auth.get("trusted_root") != bound_root
        or mat_auth.get("sandbox_instance_id") != bound_instance
        or mat_auth.get("data_dir_tag") != bound_tag
        or mat_auth.get("attempt_id") != bound_attempt
        or mat_auth.get("not_after_unix") != bound_not_after
    ):
        raise _wrap("stage_binding_invalid")
    if plan.get("sandbox_instance_id") != bound_instance:
        raise _wrap("stage_binding_invalid")
    if (
        handoff["trusted_root"] != bound_root
        or handoff["sandbox_instance_id"] != bound_instance
        or handoff["data_dir_tag"] != bound_tag
        or handoff["attempt_id"] != bound_attempt
        or handoff["not_after_unix"] != bound_not_after
    ):
        raise _wrap("stage_binding_invalid")
    if stop["sandbox_instance_id"] != bound_instance:
        raise _wrap("stage_binding_invalid")

    # Pre-materialize trusted-root snapshot (best-effort; F51 still authoritative).
    try:
        root_stat = os.lstat(bound_root)
    except OSError:
        root_stat = None

    # Materialize stage
    try:
        mat_payload = _wire(mat_req)
    except (TypeError, ValueError) as exc:
        raise _wrap("materialization_request_invalid") from exc

    mat_result = materialize_disposable_sandbox_directory_json(mat_payload)
    if mat_result.code != "materialization_ok" or not mat_result.ok:
        raise _wrap(
            "materialization_stage_failed",
            failed_stage="materialize",
            stage_code=mat_result.code,
        )

    evidence = _result_to_evidence(mat_result)

    if root_stat is None:
        raise _wrap(
            "identity_verify_containment_failure",
            failed_stage="identity_verify",
            materialization=evidence,
        )

    try:
        _identity_verify(
            evidence=evidence, trusted_root=bound_root, root_stat=root_stat
        )
    except _LifecycleError as exc:
        raise _wrap(
            exc.code,
            failed_stage=exc.failed_stage,
            stage_code="",
            materialization=evidence,
        ) from exc

    # Construct F53 cleanup request
    try:
        cleanup_request = {
            "cleanup_profile": CLEANUP_PROFILE,
            "environment": DISPOSABLE_ENVIRONMENT,
            "materialization_evidence": evidence,
            "cleanup_authority": {
                "cleanup_authorized": True,
                "trusted_root": bound_root,
                "sandbox_instance_id": bound_instance,
                "data_dir_tag": bound_tag,
                "materialization_report_id": evidence["report_id"],
                "attempt_id": bound_attempt,
                "not_after_unix": bound_not_after,
            },
            "process_stop_evidence": {
                "mode": "never_started",
                "sandbox_instance_id": bound_instance,
            },
            "trusted_root": bound_root,
            "execution_authorized": False,
            "process_launch_authorized": False,
        }
        cleanup_payload = _wire(cleanup_request)
    except Exception as exc:
        raise _wrap(
            "cleanup_stage_failed",
            failed_stage="cleanup",
            materialization=evidence,
        ) from exc

    cleanup_result = cleanup_disposable_sandbox_directory_json(cleanup_payload)
    if cleanup_result.code != "cleanup_ok" or not cleanup_result.ok:
        raise _wrap(
            "lifecycle_partial_failed",
            failed_stage="cleanup",
            stage_code=cleanup_result.code,
            materialization=evidence,
        )

    try:
        _post_lifecycle_verify(
            materialization_path=str(evidence["materialization_path"]),
            trusted_root=bound_root,
            root_stat=root_stat,
            materialization=evidence,
        )
    except _LifecycleError as exc:
        raise _wrap(
            exc.code,
            failed_stage=exc.failed_stage,
            stage_code="",
            materialization=evidence,
        ) from exc

    return _success(
        request=request,
        materialization=evidence,
        cleanup_report_id=cleanup_result.report_id,
    )


def run_disposable_sandbox_lifecycle_json(
    payload: str | bytes,
) -> SandboxLifecycleResult:
    try:
        request = _parse(payload)
        return _evaluate_parsed(request)
    except _LifecycleError as exc:
        return _failure(
            exc.code,
            lifecycle_profile=exc.lifecycle_profile,
            environment=exc.environment,
            failed_stage=exc.failed_stage,
            stage_code=exc.stage_code,
            materialization=exc.materialization,
        )
    except Exception:
        return _failure("internal_error")
