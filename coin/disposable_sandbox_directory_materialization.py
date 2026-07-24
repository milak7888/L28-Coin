# SPDX-License-Identifier: Apache-2.0
"""Governed disposable sandbox directory materializer (Foundation 51 / F50).

Materializes exactly one disposable directory under a caller-supplied trusted
root from frozen Foundation 49 creation-plan success evidence and an explicit
Foundation 50 materialization-authority binding.

Does not call Foundation 49 evaluation APIs, spawn processes, open network
listeners, wipe unrelated paths, or activate a testnet.
"""

from __future__ import annotations

import errno
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

PROFILE = "l28-disposable-sandbox-directory-materialization/v0.1"
PLAN_PROFILE = "l28-disposable-sandbox-directory-creation/v0.1"
MAX_REQUEST_BYTES = 8192
ZERO_INSTANCE_ID = "0" * 64
DIR_MODE = 0o700
FORBIDDEN_ENVIRONMENTS = frozenset({"MAIN", "CANONICAL", "HISTORICAL", "PRODUCTION"})
CHILD_NAME_RE = re.compile(r"^[0-9a-z-]+$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

REQUEST_FIELDS = (
    "materialization_profile",
    "environment",
    "plan_evidence",
    "materialization_authority",
    "trusted_root",
    "execution_authorized",
    "process_launch_authorized",
)

AUTHORITY_FIELDS = (
    "materialization_authorized",
    "trusted_root",
    "sandbox_instance_id",
    "data_dir_tag",
    "plan_report_id",
    "attempt_id",
    "not_after_unix",
)

PLAN_EVIDENCE_FIELDS = (
    "ok",
    "code",
    "creation_profile",
    "environment",
    "network_id",
    "chain_id",
    "genesis_digest",
    "protocol_version",
    "preflight_report_id",
    "sandbox_instance_id",
    "path_lexeme",
    "creation_plan_ok",
    "process_launch_authorized",
    "execution_authorized",
    "report_id",
    "detail",
)

FORBIDDEN_AUTHORITY_FIELDS = frozenset(
    {
        "admission_authorized",
        "filesystem_create_authorized",
        "wipe_authorized",
        "cleanup_authorized",
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
    "materialization_ok",
    "input_type_invalid",
    "input_too_large",
    "encoding_invalid",
    "json_invalid",
    "duplicate_key",
    "invalid_top_level",
    "schema_invalid",
    "materialization_profile_unsupported",
    "environment_invalid",
    "historical_import_forbidden",
    "execution_authorized_invalid",
    "process_launch_authorized_invalid",
    "materialization_authority_invalid",
    "materialization_authority_mismatch",
    "materialization_authority_expired",
    "plan_evidence_invalid",
    "trusted_root_invalid",
    "plan_binding_invalid",
    "traversal_rejected",
    "containment_failure",
    "symlink_rejected",
    "substitution_ambiguous",
    "target_collision",
    "exclusive_create_failed",
    "permission_verification_failed",
    "post_create_verification_failed",
    "rollback_failed",
    "internal_error",
)


class _DuplicateKey(ValueError):
    pass


class _MaterializeError(ValueError):
    def __init__(
        self,
        code: str,
        *,
        materialization_profile: str = "",
        environment: str = "",
    ) -> None:
        super().__init__(code)
        self.code = code
        self.materialization_profile = materialization_profile
        self.environment = environment


@dataclass(frozen=True)
class SandboxMaterializationResult:
    ok: bool
    code: str
    materialization_profile: str = ""
    environment: str = ""
    network_id: str = ""
    chain_id: str = ""
    genesis_digest: str = ""
    protocol_version: str = ""
    plan_report_id: str = ""
    sandbox_instance_id: str = ""
    data_dir_tag: str = ""
    path_lexeme: str = ""
    child_name: str = ""
    materialization_path: str = ""
    materialization_ok: bool = False
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
    raise _MaterializeError("json_invalid")


def _failure(
    code: str,
    *,
    materialization_profile: str = "",
    environment: str = "",
) -> SandboxMaterializationResult:
    return SandboxMaterializationResult(
        False,
        code,
        materialization_profile=materialization_profile,
        environment=environment,
        materialization_ok=False,
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
    plan: Mapping[str, Any],
    child_name: str,
    materialization_path: str,
) -> SandboxMaterializationResult:
    return SandboxMaterializationResult(
        True,
        "materialization_ok",
        materialization_profile=PROFILE,
        environment=DISPOSABLE_ENVIRONMENT,
        network_id=str(plan["network_id"]),
        chain_id=str(plan["chain_id"]),
        genesis_digest=str(plan["genesis_digest"]),
        protocol_version=str(plan["protocol_version"]),
        plan_report_id=str(plan["report_id"]),
        sandbox_instance_id=str(plan["sandbox_instance_id"]),
        data_dir_tag=DATA_DIR_TAG,
        path_lexeme=str(plan["path_lexeme"]),
        child_name=child_name,
        materialization_path=materialization_path,
        materialization_ok=True,
        process_launch_authorized=False,
        execution_authorized=False,
        report_id=_canonical_report_id(request),
        detail="",
    )


def _decode(payload: str | bytes) -> str:
    if isinstance(payload, bytes):
        if len(payload) > MAX_REQUEST_BYTES:
            raise _MaterializeError("input_too_large")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _MaterializeError("encoding_invalid") from exc
    if isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _MaterializeError("encoding_invalid") from exc
        if len(encoded) > MAX_REQUEST_BYTES:
            raise _MaterializeError("input_too_large")
        return payload
    raise _MaterializeError("input_type_invalid")


def _parse(payload: str | bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            _decode(payload),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise _MaterializeError("duplicate_key") from exc
    except _MaterializeError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _MaterializeError("json_invalid") from exc
    if not isinstance(value, dict):
        raise _MaterializeError("invalid_top_level")
    return value


def _require_hex64(value: Any, *, code: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise _MaterializeError(code)
    return value


def _contains_forbidden_authority(value: Any) -> bool:
    if isinstance(value, dict):
        if any(field in value for field in FORBIDDEN_AUTHORITY_FIELDS):
            return True
        return any(_contains_forbidden_authority(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_authority(item) for item in value)
    return False


def _validate_lexical_trusted_root(path: str) -> str:
    if not isinstance(path, str) or path == "":
        raise _MaterializeError("trusted_root_invalid")
    if "\0" in path:
        raise _MaterializeError("trusted_root_invalid")
    if path.startswith("~") or "$" in path:
        raise _MaterializeError("trusted_root_invalid")
    if "\\" in path:
        raise _MaterializeError("trusted_root_invalid")
    if not path.startswith("/"):
        raise _MaterializeError("trusted_root_invalid")
    if path != "/" and path.endswith("/"):
        raise _MaterializeError("trusted_root_invalid")
    if "//" in path:
        raise _MaterializeError("trusted_root_invalid")
    segments = path.split("/")[1:] if path != "/" else []
    for segment in segments:
        if segment in ("", ".", ".."):
            raise _MaterializeError("trusted_root_invalid")
    return path


def _validate_authority_formats(authority: Any) -> dict[str, Any]:
    if not isinstance(authority, dict):
        raise _MaterializeError("materialization_authority_invalid")
    if tuple(authority.keys()) != AUTHORITY_FIELDS:
        raise _MaterializeError("materialization_authority_invalid")
    if not isinstance(authority["materialization_authorized"], bool):
        raise _MaterializeError("materialization_authority_invalid")
    if authority["materialization_authorized"] is not True:
        raise _MaterializeError("materialization_authority_invalid")
    if not isinstance(authority["trusted_root"], str):
        raise _MaterializeError("materialization_authority_invalid")
    _require_hex64(
        authority["sandbox_instance_id"], code="materialization_authority_invalid"
    )
    if not isinstance(authority["data_dir_tag"], str):
        raise _MaterializeError("materialization_authority_invalid")
    _require_hex64(authority["plan_report_id"], code="materialization_authority_invalid")
    _require_hex64(authority["attempt_id"], code="materialization_authority_invalid")
    not_after = authority["not_after_unix"]
    if isinstance(not_after, bool) or not isinstance(not_after, int) or not_after < 0:
        raise _MaterializeError("materialization_authority_invalid")
    return authority


def _validate_plan_evidence(evidence: Any) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise _MaterializeError("plan_evidence_invalid")
    if tuple(evidence.keys()) != PLAN_EVIDENCE_FIELDS:
        raise _MaterializeError("plan_evidence_invalid")
    if evidence["ok"] is not True:
        raise _MaterializeError("plan_evidence_invalid")
    if evidence["code"] != "creation_plan_ok":
        raise _MaterializeError("plan_evidence_invalid")
    if evidence["creation_profile"] != PLAN_PROFILE:
        raise _MaterializeError("plan_evidence_invalid")
    if evidence["environment"] != DISPOSABLE_ENVIRONMENT:
        raise _MaterializeError("plan_evidence_invalid")
    if evidence["network_id"] != NETWORK_ID:
        raise _MaterializeError("plan_evidence_invalid")
    _require_hex64(evidence["chain_id"], code="plan_evidence_invalid")
    _require_hex64(evidence["genesis_digest"], code="plan_evidence_invalid")
    if evidence["protocol_version"] != PROTOCOL_VERSION:
        raise _MaterializeError("plan_evidence_invalid")
    _require_hex64(evidence["preflight_report_id"], code="plan_evidence_invalid")
    instance_id = _require_hex64(
        evidence["sandbox_instance_id"], code="plan_evidence_invalid"
    )
    if instance_id == ZERO_INSTANCE_ID:
        raise _MaterializeError("plan_evidence_invalid")
    path_lexeme = evidence["path_lexeme"]
    if not isinstance(path_lexeme, str) or path_lexeme.strip() == "":
        raise _MaterializeError("plan_evidence_invalid")
    if evidence["creation_plan_ok"] is not True:
        raise _MaterializeError("plan_evidence_invalid")
    if evidence["process_launch_authorized"] is not False:
        raise _MaterializeError("plan_evidence_invalid")
    if evidence["execution_authorized"] is not False:
        raise _MaterializeError("plan_evidence_invalid")
    _require_hex64(evidence["report_id"], code="plan_evidence_invalid")
    if evidence["detail"] != "":
        raise _MaterializeError("plan_evidence_invalid")
    return evidence


def _prefix_paths(absolute: str) -> list[str]:
    if absolute == "/":
        return ["/"]
    parts = absolute.split("/")[1:]
    out = ["/"]
    current = ""
    for part in parts:
        current = f"{current}/{part}"
        out.append(current)
    return out


def _validate_trusted_root_filesystem(trusted_root: str) -> os.stat_result:
    try:
        for prefix in _prefix_paths(trusted_root):
            st = os.lstat(prefix)
            if stat.S_ISLNK(st.st_mode):
                raise _MaterializeError("trusted_root_invalid")
        st_root = os.lstat(trusted_root)
    except OSError as exc:
        raise _MaterializeError("trusted_root_invalid") from exc
    if not stat.S_ISDIR(st_root.st_mode):
        raise _MaterializeError("trusted_root_invalid")
    if stat.S_ISLNK(st_root.st_mode):
        raise _MaterializeError("trusted_root_invalid")
    return st_root


def _derive_child_name(instance_id: str) -> str:
    child_name = f"{DATA_DIR_TAG}-{instance_id}"
    if CHILD_NAME_RE.fullmatch(child_name) is None:
        raise _MaterializeError("plan_binding_invalid")
    if any(ch in child_name for ch in ("/", "\\", "\0")):
        raise _MaterializeError("plan_binding_invalid")
    if child_name in (".", "..") or "." in child_name:
        # tag-instance uses hyphens only; '.' would be invalid under CHILD_NAME_RE
        raise _MaterializeError("plan_binding_invalid")
    return child_name


def _materialization_path_for(trusted_root: str, child_name: str) -> str:
    if trusted_root == "/":
        return f"/{child_name}"
    return f"{trusted_root}/{child_name}"


def _validate_derived_path(child_name: str, materialization_path: str) -> None:
    if "\0" in child_name or "\0" in materialization_path:
        raise _MaterializeError("traversal_rejected")
    if "/" in child_name or "\\" in child_name:
        raise _MaterializeError("traversal_rejected")
    if child_name in (".", "..") or child_name.startswith(".") or ".." in child_name:
        raise _MaterializeError("traversal_rejected")
    if "//" in materialization_path or "\\" in materialization_path:
        raise _MaterializeError("traversal_rejected")


def _assert_direct_child(
    trusted_root: str,
    materialization_path: str,
    child_name: str,
    root_stat: os.stat_result,
) -> None:
    expected = _materialization_path_for(trusted_root, child_name)
    if materialization_path != expected:
        raise _MaterializeError("containment_failure")
    parent = os.path.dirname(materialization_path) or "/"
    if parent != trusted_root:
        raise _MaterializeError("containment_failure")
    try:
        parent_stat = os.lstat(parent)
    except OSError as exc:
        raise _MaterializeError("containment_failure") from exc
    if (parent_stat.st_ino, parent_stat.st_dev) != (root_stat.st_ino, root_stat.st_dev):
        raise _MaterializeError("containment_failure")


def _precreate_substitution_check(
    trusted_root: str,
    root_stat: os.stat_result,
) -> None:
    """Detect trusted-root inode/device substitution before create (derived-path step)."""
    try:
        st = os.lstat(trusted_root)
    except OSError as exc:
        raise _MaterializeError("substitution_ambiguous") from exc
    if st.st_dev != root_stat.st_dev or st.st_ino != root_stat.st_ino:
        raise _MaterializeError("substitution_ambiguous")


def _precreate_symlink_check(materialization_path: str) -> bool:
    """Return True if path is absent. Symlink → symlink_rejected; other exist left for collision."""
    try:
        st = os.lstat(materialization_path)
    except FileNotFoundError:
        return True
    except OSError as exc:
        raise _MaterializeError("exclusive_create_failed") from exc
    if stat.S_ISLNK(st.st_mode):
        raise _MaterializeError("symlink_rejected")
    return False


def _precreate_collision_check(materialization_path: str, *, absent: bool) -> None:
    if absent:
        return
    raise _MaterializeError("target_collision")


def _rollback_created(path: str) -> None:
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise _MaterializeError("rollback_failed") from exc
    if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
        raise _MaterializeError("rollback_failed")
    try:
        os.rmdir(path)
    except OSError as exc:
        raise _MaterializeError("rollback_failed") from exc


def _fail_after_create(code: str, path: str) -> None:
    try:
        _rollback_created(path)
    except _MaterializeError as exc:
        if exc.code == "rollback_failed":
            raise
        raise _MaterializeError("rollback_failed") from exc
    raise _MaterializeError(code)


def _verify_created(
    *,
    materialization_path: str,
    child_name: str,
    trusted_root: str,
    root_stat: os.stat_result,
) -> None:
    try:
        flags = os.O_RDONLY
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        if nofollow:
            flags |= nofollow
        fd = os.open(materialization_path, flags)
    except OSError as exc:
        _fail_after_create("permission_verification_failed", materialization_path)
        raise  # pragma: no cover
    try:
        st = os.fstat(fd)
    finally:
        os.close(fd)

    mode = stat.S_IMODE(st.st_mode)
    if not stat.S_ISDIR(st.st_mode) or mode != DIR_MODE:
        _fail_after_create("permission_verification_failed", materialization_path)
    if hasattr(os, "geteuid") and st.st_uid != os.geteuid():
        _fail_after_create("permission_verification_failed", materialization_path)

    try:
        lst = os.lstat(materialization_path)
    except OSError:
        _fail_after_create("symlink_rejected", materialization_path)
        raise  # pragma: no cover
    if stat.S_ISLNK(lst.st_mode):
        _fail_after_create("symlink_rejected", materialization_path)

    if st.st_dev != root_stat.st_dev:
        _fail_after_create("substitution_ambiguous", materialization_path)

    if os.path.basename(materialization_path) != child_name:
        _fail_after_create("post_create_verification_failed", materialization_path)
    parent = os.path.dirname(materialization_path) or "/"
    if parent != trusted_root:
        _fail_after_create("post_create_verification_failed", materialization_path)
    try:
        parent_stat = os.lstat(parent)
    except OSError:
        _fail_after_create("post_create_verification_failed", materialization_path)
        raise  # pragma: no cover
    if (parent_stat.st_ino, parent_stat.st_dev) != (root_stat.st_ino, root_stat.st_dev):
        _fail_after_create("post_create_verification_failed", materialization_path)


def _exclusive_create(materialization_path: str) -> None:
    try:
        os.mkdir(materialization_path, DIR_MODE)
    except FileExistsError as exc:
        raise _MaterializeError("target_collision") from exc
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            raise _MaterializeError("target_collision") from exc
        raise _MaterializeError("exclusive_create_failed") from exc
    try:
        os.chmod(materialization_path, DIR_MODE)
    except OSError as exc:
        _fail_after_create("permission_verification_failed", materialization_path)
        raise  # pragma: no cover


def _evaluate_parsed(request: Mapping[str, Any]) -> SandboxMaterializationResult:
    # Step 5 — top-level schema shape.
    if tuple(request.keys()) != REQUEST_FIELDS:
        raise _MaterializeError("schema_invalid")

    materialization_profile = request["materialization_profile"]
    if not isinstance(materialization_profile, str):
        raise _MaterializeError("schema_invalid")
    environment = request["environment"]
    if not isinstance(environment, str):
        raise _MaterializeError("schema_invalid")
    if not isinstance(request["plan_evidence"], dict):
        raise _MaterializeError("schema_invalid")
    if not isinstance(request["materialization_authority"], dict):
        raise _MaterializeError("schema_invalid")
    if not isinstance(request["trusted_root"], str):
        raise _MaterializeError("schema_invalid")
    if not isinstance(request["execution_authorized"], bool):
        raise _MaterializeError("schema_invalid")
    if not isinstance(request["process_launch_authorized"], bool):
        raise _MaterializeError("schema_invalid")

    # Step 6
    if materialization_profile != PROFILE:
        raise _MaterializeError(
            "materialization_profile_unsupported",
            materialization_profile=materialization_profile,
        )
    recovered_profile = PROFILE

    # Steps 7–8
    if environment in FORBIDDEN_ENVIRONMENTS:
        raise _MaterializeError(
            "historical_import_forbidden",
            materialization_profile=recovered_profile,
            environment=environment,
        )
    if environment != DISPOSABLE_ENVIRONMENT:
        raise _MaterializeError(
            "environment_invalid",
            materialization_profile=recovered_profile,
            environment=environment,
        )

    # Steps 9–10
    if request["execution_authorized"] is not False:
        raise _MaterializeError(
            "execution_authorized_invalid",
            materialization_profile=recovered_profile,
            environment=environment,
        )
    if request["process_launch_authorized"] is not False:
        raise _MaterializeError(
            "process_launch_authorized_invalid",
            materialization_profile=recovered_profile,
            environment=environment,
        )

    # Step 11
    if _contains_forbidden_authority(request):
        raise _MaterializeError(
            "schema_invalid",
            materialization_profile=recovered_profile,
            environment=environment,
        )

    def _wrap(code: str) -> _MaterializeError:
        return _MaterializeError(
            code,
            materialization_profile=recovered_profile,
            environment=environment,
        )

    # Step 12
    try:
        authority = _validate_authority_formats(request["materialization_authority"])
    except _MaterializeError as exc:
        raise _wrap(exc.code) from exc

    # Step 13
    try:
        trusted_root = _validate_lexical_trusted_root(request["trusted_root"])
    except _MaterializeError as exc:
        raise _wrap(exc.code) from exc
    if authority["trusted_root"] != trusted_root:
        raise _wrap("materialization_authority_mismatch")

    # Step 14 — accepted wall-clock freshness product decision.
    if int(time.time()) >= int(authority["not_after_unix"]):
        raise _wrap("materialization_authority_expired")

    # Step 15
    try:
        plan = _validate_plan_evidence(request["plan_evidence"])
    except _MaterializeError as exc:
        raise _wrap(exc.code) from exc

    # Step 16
    if (
        authority["sandbox_instance_id"] != plan["sandbox_instance_id"]
        or authority["data_dir_tag"] != DATA_DIR_TAG
        or authority["plan_report_id"] != plan["report_id"]
    ):
        raise _wrap("materialization_authority_mismatch")

    # Step 17
    try:
        root_stat = _validate_trusted_root_filesystem(trusted_root)
    except _MaterializeError as exc:
        raise _wrap(exc.code) from exc

    # Step 18
    try:
        child_name = _derive_child_name(str(plan["sandbox_instance_id"]))
        materialization_path = _materialization_path_for(trusted_root, child_name)
    except _MaterializeError as exc:
        raise _wrap(exc.code) from exc

    # Step 19
    try:
        _validate_derived_path(child_name, materialization_path)
    except _MaterializeError as exc:
        raise _wrap(exc.code) from exc

    # Steps 20–23
    try:
        _assert_direct_child(
            trusted_root, materialization_path, child_name, root_stat
        )
        absent = _precreate_symlink_check(materialization_path)
        _precreate_substitution_check(trusted_root, root_stat)
        _precreate_collision_check(materialization_path, absent=absent)
    except _MaterializeError as exc:
        raise _wrap(exc.code) from exc

    # Step 24 (collision also raised from mkdir)
    try:
        _exclusive_create(materialization_path)
    except _MaterializeError as exc:
        raise _wrap(exc.code) from exc

    # Steps 25–26
    try:
        _verify_created(
            materialization_path=materialization_path,
            child_name=child_name,
            trusted_root=trusted_root,
            root_stat=root_stat,
        )
    except _MaterializeError as exc:
        raise _wrap(exc.code) from exc

    return _success(
        request=request,
        plan=plan,
        child_name=child_name,
        materialization_path=materialization_path,
    )


def materialize_disposable_sandbox_directory_json(
    payload: str | bytes,
) -> SandboxMaterializationResult:
    try:
        request = _parse(payload)
        return _evaluate_parsed(request)
    except _MaterializeError as exc:
        return _failure(
            exc.code,
            materialization_profile=exc.materialization_profile,
            environment=exc.environment,
        )
    except Exception:
        return _failure("internal_error")
