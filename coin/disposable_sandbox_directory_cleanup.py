# SPDX-License-Identifier: Apache-2.0
"""Governed disposable sandbox directory cleanup (Foundation 53 / F52).

Removes exactly one successful Foundation 51-materialized disposable sandbox
directory under a caller-supplied trusted root, after process-stop proof and
fail-closed authority binding.

Consumes frozen Foundation 51 success evidence structurally only. Does not call
Foundation 51 materialization APIs, recurse-delete via library tree wipe helpers,
spawn processes, or activate a testnet.
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

PROFILE = "l28-disposable-sandbox-directory-cleanup/v0.1"
MATERIALIZATION_PROFILE = "l28-disposable-sandbox-directory-materialization/v0.1"
MAX_REQUEST_BYTES = 8192
ZERO_INSTANCE_ID = "0" * 64
MAX_TREE_ENTRIES = 4096
MAX_TREE_DEPTH = 64
FORBIDDEN_ENVIRONMENTS = frozenset({"MAIN", "CANONICAL", "HISTORICAL", "PRODUCTION"})
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

REQUEST_FIELDS = (
    "cleanup_profile",
    "environment",
    "materialization_evidence",
    "cleanup_authority",
    "process_stop_evidence",
    "trusted_root",
    "execution_authorized",
    "process_launch_authorized",
)

AUTHORITY_FIELDS = (
    "cleanup_authorized",
    "trusted_root",
    "sandbox_instance_id",
    "data_dir_tag",
    "materialization_report_id",
    "attempt_id",
    "not_after_unix",
)

MATERIALIZATION_EVIDENCE_FIELDS = (
    "ok",
    "code",
    "materialization_profile",
    "environment",
    "network_id",
    "chain_id",
    "genesis_digest",
    "protocol_version",
    "plan_report_id",
    "sandbox_instance_id",
    "data_dir_tag",
    "path_lexeme",
    "child_name",
    "materialization_path",
    "materialization_ok",
    "process_launch_authorized",
    "execution_authorized",
    "report_id",
    "detail",
)

STOP_NEVER_STARTED_FIELDS = ("mode", "sandbox_instance_id")
STOP_STOPPED_FIELDS = (
    "mode",
    "sandbox_instance_id",
    "listeners_cleared",
    "stop_report_id",
)

FORBIDDEN_AUTHORITY_FIELDS = frozenset(
    {
        "admission_authorized",
        "filesystem_create_authorized",
        "materialization_authorized",
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
    "cleanup_ok",
    "input_type_invalid",
    "input_too_large",
    "encoding_invalid",
    "json_invalid",
    "duplicate_key",
    "invalid_top_level",
    "schema_invalid",
    "cleanup_profile_unsupported",
    "environment_invalid",
    "historical_import_forbidden",
    "execution_authorized_invalid",
    "process_launch_authorized_invalid",
    "cleanup_authority_invalid",
    "cleanup_authority_mismatch",
    "cleanup_authority_expired",
    "process_stop_evidence_invalid",
    "materialization_evidence_invalid",
    "trusted_root_invalid",
    "target_identity_invalid",
    "traversal_rejected",
    "containment_failure",
    "symlink_rejected",
    "substitution_ambiguous",
    "untagged_or_protected_path",
    "target_absent",
    "tree_limit_exceeded",
    "exclusive_cleanup_failed",
    "cleanup_partial_failed",
    "post_cleanup_verification_failed",
    "internal_error",
)


class _DuplicateKey(ValueError):
    pass


class _CleanupError(ValueError):
    def __init__(
        self,
        code: str,
        *,
        cleanup_profile: str = "",
        environment: str = "",
    ) -> None:
        super().__init__(code)
        self.code = code
        self.cleanup_profile = cleanup_profile
        self.environment = environment


@dataclass(frozen=True)
class SandboxCleanupResult:
    ok: bool
    code: str
    cleanup_profile: str = ""
    environment: str = ""
    network_id: str = ""
    chain_id: str = ""
    genesis_digest: str = ""
    protocol_version: str = ""
    materialization_report_id: str = ""
    sandbox_instance_id: str = ""
    data_dir_tag: str = ""
    child_name: str = ""
    cleanup_path: str = ""
    cleanup_ok: bool = False
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
    raise _CleanupError("json_invalid")


def _failure(
    code: str,
    *,
    cleanup_profile: str = "",
    environment: str = "",
) -> SandboxCleanupResult:
    return SandboxCleanupResult(
        False,
        code,
        cleanup_profile=cleanup_profile,
        environment=environment,
        cleanup_ok=False,
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
    evidence: Mapping[str, Any],
    child_name: str,
    cleanup_path: str,
) -> SandboxCleanupResult:
    return SandboxCleanupResult(
        True,
        "cleanup_ok",
        cleanup_profile=PROFILE,
        environment=DISPOSABLE_ENVIRONMENT,
        network_id=str(evidence["network_id"]),
        chain_id=str(evidence["chain_id"]),
        genesis_digest=str(evidence["genesis_digest"]),
        protocol_version=str(evidence["protocol_version"]),
        materialization_report_id=str(evidence["report_id"]),
        sandbox_instance_id=str(evidence["sandbox_instance_id"]),
        data_dir_tag=DATA_DIR_TAG,
        child_name=child_name,
        cleanup_path=cleanup_path,
        cleanup_ok=True,
        process_launch_authorized=False,
        execution_authorized=False,
        report_id=_canonical_report_id(request),
        detail="",
    )


def _decode(payload: str | bytes) -> str:
    if isinstance(payload, bytes):
        if len(payload) > MAX_REQUEST_BYTES:
            raise _CleanupError("input_too_large")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _CleanupError("encoding_invalid") from exc
    if isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _CleanupError("encoding_invalid") from exc
        if len(encoded) > MAX_REQUEST_BYTES:
            raise _CleanupError("input_too_large")
        return payload
    raise _CleanupError("input_type_invalid")


def _parse(payload: str | bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            _decode(payload),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise _CleanupError("duplicate_key") from exc
    except _CleanupError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _CleanupError("json_invalid") from exc
    if not isinstance(value, dict):
        raise _CleanupError("invalid_top_level")
    return value


def _require_hex64(value: Any, *, code: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise _CleanupError(code)
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
        raise _CleanupError("trusted_root_invalid")
    if "\0" in path:
        raise _CleanupError("trusted_root_invalid")
    if path.startswith("~") or "$" in path:
        raise _CleanupError("trusted_root_invalid")
    if "\\" in path:
        raise _CleanupError("trusted_root_invalid")
    if not path.startswith("/"):
        raise _CleanupError("trusted_root_invalid")
    if path != "/" and path.endswith("/"):
        raise _CleanupError("trusted_root_invalid")
    if "//" in path:
        raise _CleanupError("trusted_root_invalid")
    segments = path.split("/")[1:] if path != "/" else []
    for segment in segments:
        if segment in ("", ".", ".."):
            raise _CleanupError("trusted_root_invalid")
    return path


def _validate_lexical_abs_path(path: str, *, code: str) -> str:
    if not isinstance(path, str) or path == "" or "\0" in path:
        raise _CleanupError(code)
    if not path.startswith("/") or "\\" in path or "//" in path:
        raise _CleanupError(code)
    if path != "/" and path.endswith("/"):
        raise _CleanupError(code)
    segments = path.split("/")[1:] if path != "/" else []
    for segment in segments:
        if segment in ("", ".", ".."):
            raise _CleanupError(code)
    return path


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


def _validate_authority_formats(authority: Any) -> dict[str, Any]:
    if not isinstance(authority, dict):
        raise _CleanupError("cleanup_authority_invalid")
    if tuple(authority.keys()) != AUTHORITY_FIELDS:
        raise _CleanupError("cleanup_authority_invalid")
    if authority["cleanup_authorized"] is not True:
        raise _CleanupError("cleanup_authority_invalid")
    if not isinstance(authority["trusted_root"], str):
        raise _CleanupError("cleanup_authority_invalid")
    _require_hex64(
        authority["sandbox_instance_id"], code="cleanup_authority_invalid"
    )
    if not isinstance(authority["data_dir_tag"], str):
        raise _CleanupError("cleanup_authority_invalid")
    _require_hex64(
        authority["materialization_report_id"], code="cleanup_authority_invalid"
    )
    _require_hex64(authority["attempt_id"], code="cleanup_authority_invalid")
    not_after = authority["not_after_unix"]
    if isinstance(not_after, bool) or not isinstance(not_after, int) or not_after < 0:
        raise _CleanupError("cleanup_authority_invalid")
    return authority


def _validate_process_stop(evidence: Any) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise _CleanupError("process_stop_evidence_invalid")
    mode = evidence.get("mode")
    if mode == "never_started":
        if tuple(evidence.keys()) != STOP_NEVER_STARTED_FIELDS:
            raise _CleanupError("process_stop_evidence_invalid")
        _require_hex64(
            evidence["sandbox_instance_id"], code="process_stop_evidence_invalid"
        )
        return evidence
    if mode == "stopped":
        if tuple(evidence.keys()) != STOP_STOPPED_FIELDS:
            raise _CleanupError("process_stop_evidence_invalid")
        _require_hex64(
            evidence["sandbox_instance_id"], code="process_stop_evidence_invalid"
        )
        if evidence["listeners_cleared"] is not True:
            raise _CleanupError("process_stop_evidence_invalid")
        _require_hex64(evidence["stop_report_id"], code="process_stop_evidence_invalid")
        return evidence
    raise _CleanupError("process_stop_evidence_invalid")


def _validate_materialization_evidence(evidence: Any) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise _CleanupError("materialization_evidence_invalid")
    if tuple(evidence.keys()) != MATERIALIZATION_EVIDENCE_FIELDS:
        raise _CleanupError("materialization_evidence_invalid")
    if evidence["ok"] is not True:
        raise _CleanupError("materialization_evidence_invalid")
    if evidence["code"] != "materialization_ok":
        raise _CleanupError("materialization_evidence_invalid")
    if evidence["materialization_profile"] != MATERIALIZATION_PROFILE:
        raise _CleanupError("materialization_evidence_invalid")
    if evidence["environment"] != DISPOSABLE_ENVIRONMENT:
        raise _CleanupError("materialization_evidence_invalid")
    if evidence["network_id"] != NETWORK_ID:
        raise _CleanupError("materialization_evidence_invalid")
    _require_hex64(evidence["chain_id"], code="materialization_evidence_invalid")
    _require_hex64(evidence["genesis_digest"], code="materialization_evidence_invalid")
    if evidence["protocol_version"] != PROTOCOL_VERSION:
        raise _CleanupError("materialization_evidence_invalid")
    _require_hex64(evidence["plan_report_id"], code="materialization_evidence_invalid")
    instance_id = _require_hex64(
        evidence["sandbox_instance_id"], code="materialization_evidence_invalid"
    )
    if instance_id == ZERO_INSTANCE_ID:
        raise _CleanupError("materialization_evidence_invalid")
    if evidence["data_dir_tag"] != DATA_DIR_TAG:
        raise _CleanupError("materialization_evidence_invalid")
    path_lexeme = evidence["path_lexeme"]
    if not isinstance(path_lexeme, str) or path_lexeme.strip() == "":
        raise _CleanupError("materialization_evidence_invalid")
    expected_child = f"{DATA_DIR_TAG}-{instance_id}"
    if evidence["child_name"] != expected_child:
        raise _CleanupError("materialization_evidence_invalid")
    _validate_lexical_abs_path(
        str(evidence["materialization_path"]), code="materialization_evidence_invalid"
    )
    if evidence["materialization_ok"] is not True:
        raise _CleanupError("materialization_evidence_invalid")
    if evidence["process_launch_authorized"] is not False:
        raise _CleanupError("materialization_evidence_invalid")
    if evidence["execution_authorized"] is not False:
        raise _CleanupError("materialization_evidence_invalid")
    _require_hex64(evidence["report_id"], code="materialization_evidence_invalid")
    if evidence["detail"] != "":
        raise _CleanupError("materialization_evidence_invalid")
    return evidence


def _validate_trusted_root_filesystem(trusted_root: str) -> os.stat_result:
    try:
        for prefix in _prefix_paths(trusted_root):
            st = os.lstat(prefix)
            if stat.S_ISLNK(st.st_mode):
                raise _CleanupError("trusted_root_invalid")
        st_root = os.lstat(trusted_root)
    except OSError as exc:
        raise _CleanupError("trusted_root_invalid") from exc
    if not stat.S_ISDIR(st_root.st_mode) or stat.S_ISLNK(st_root.st_mode):
        raise _CleanupError("trusted_root_invalid")
    return st_root


def _materialization_path_for(trusted_root: str, child_name: str) -> str:
    if trusted_root == "/":
        return f"/{child_name}"
    return f"{trusted_root}/{child_name}"


def _validate_derived_path(child_name: str, materialization_path: str) -> None:
    if "\0" in child_name or "\0" in materialization_path:
        raise _CleanupError("traversal_rejected")
    if "/" in child_name or "\\" in child_name:
        raise _CleanupError("traversal_rejected")
    if child_name in (".", "..") or child_name.startswith(".") or ".." in child_name:
        raise _CleanupError("traversal_rejected")
    if "//" in materialization_path or "\\" in materialization_path:
        raise _CleanupError("traversal_rejected")


def _assert_direct_child(
    trusted_root: str,
    materialization_path: str,
    _child_name: str,
    root_stat: os.stat_result,
) -> None:
    parent = os.path.dirname(materialization_path) or "/"
    if parent != trusted_root:
        raise _CleanupError("containment_failure")
    try:
        parent_stat = os.lstat(parent)
    except OSError as exc:
        raise _CleanupError("containment_failure") from exc
    if (parent_stat.st_ino, parent_stat.st_dev) != (root_stat.st_ino, root_stat.st_dev):
        raise _CleanupError("containment_failure")


def _assert_tagged_disposable(
    child_name: str,
    materialization_path: str,
    trusted_root: str,
) -> None:
    if materialization_path == trusted_root:
        raise _CleanupError("untagged_or_protected_path")
    if not child_name.startswith(f"{DATA_DIR_TAG}-"):
        raise _CleanupError("untagged_or_protected_path")
    base = os.path.basename(materialization_path)
    if base != child_name:
        raise _CleanupError("untagged_or_protected_path")
    # Refuse continuity/archive-shaped basenames even if earlier binds matched.
    if "continuity" in base or "archive" in base or base.endswith(".json"):
        raise _CleanupError("untagged_or_protected_path")


def _is_special(mode: int) -> bool:
    return not (stat.S_ISREG(mode) or stat.S_ISDIR(mode) or stat.S_ISLNK(mode))


def _survey_tree(target: str, root_dev: int) -> list[tuple[str, bool]]:
    """Return bottom-up list of (path, is_dir) for deletable entries under target.

    Includes the target directory itself last. Raises survey codes only.
    """
    entries: list[tuple[str, int, bool]] = []  # path, depth, is_dir
    stack: list[tuple[str, int]] = [(target, 0)]
    seen = 0

    while stack:
        current, depth = stack.pop()
        if depth > MAX_TREE_DEPTH:
            raise _CleanupError("tree_limit_exceeded")
        try:
            st = os.lstat(current)
        except OSError as exc:
            raise _CleanupError("substitution_ambiguous") from exc
        if st.st_dev != root_dev:
            raise _CleanupError("substitution_ambiguous")
        if stat.S_ISLNK(st.st_mode) or _is_special(st.st_mode):
            raise _CleanupError("symlink_rejected")
        seen += 1
        if seen > MAX_TREE_ENTRIES:
            raise _CleanupError("tree_limit_exceeded")
        if stat.S_ISDIR(st.st_mode):
            try:
                names = os.listdir(current)
            except OSError as exc:
                raise _CleanupError("substitution_ambiguous") from exc
            child_paths = [os.path.join(current, name) for name in names]
            entries.append((current, depth, True))
            for child in child_paths:
                stack.append((child, depth + 1))
        elif stat.S_ISREG(st.st_mode):
            entries.append((current, depth, False))
        else:
            raise _CleanupError("symlink_rejected")

    # Bottom-up: deeper first; at same depth files before directories.
    entries.sort(key=lambda item: (-item[1], item[2]))
    return [(path, is_dir) for path, _depth, is_dir in entries]


def _post_cleanup_verify(
    *,
    target: str,
    trusted_root: str,
    root_stat: os.stat_result,
    deletion_began: bool,
) -> None:
    target_present = False
    try:
        os.lstat(target)
        target_present = True
    except FileNotFoundError:
        target_present = False
    except OSError as exc:
        if deletion_began:
            raise _CleanupError("cleanup_partial_failed") from exc
        raise _CleanupError("post_cleanup_verification_failed") from exc

    if target_present:
        if deletion_began:
            raise _CleanupError("cleanup_partial_failed")
        raise _CleanupError("post_cleanup_verification_failed")

    try:
        st = os.lstat(trusted_root)
    except OSError as exc:
        raise _CleanupError("post_cleanup_verification_failed") from exc
    if (st.st_ino, st.st_dev) != (root_stat.st_ino, root_stat.st_dev):
        raise _CleanupError("post_cleanup_verification_failed")
    if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
        raise _CleanupError("post_cleanup_verification_failed")


def _evaluate_parsed(request: Mapping[str, Any]) -> SandboxCleanupResult:
    if tuple(request.keys()) != REQUEST_FIELDS:
        raise _CleanupError("schema_invalid")

    cleanup_profile = request["cleanup_profile"]
    if not isinstance(cleanup_profile, str):
        raise _CleanupError("schema_invalid")
    environment = request["environment"]
    if not isinstance(environment, str):
        raise _CleanupError("schema_invalid")
    if not isinstance(request["materialization_evidence"], dict):
        raise _CleanupError("schema_invalid")
    if not isinstance(request["cleanup_authority"], dict):
        raise _CleanupError("schema_invalid")
    if not isinstance(request["process_stop_evidence"], dict):
        raise _CleanupError("schema_invalid")
    if not isinstance(request["trusted_root"], str):
        raise _CleanupError("schema_invalid")
    if not isinstance(request["execution_authorized"], bool):
        raise _CleanupError("schema_invalid")
    if not isinstance(request["process_launch_authorized"], bool):
        raise _CleanupError("schema_invalid")

    if cleanup_profile != PROFILE:
        raise _CleanupError(
            "cleanup_profile_unsupported",
            cleanup_profile=cleanup_profile,
        )
    recovered_profile = PROFILE

    if environment in FORBIDDEN_ENVIRONMENTS:
        raise _CleanupError(
            "historical_import_forbidden",
            cleanup_profile=recovered_profile,
            environment=environment,
        )
    if environment != DISPOSABLE_ENVIRONMENT:
        raise _CleanupError(
            "environment_invalid",
            cleanup_profile=recovered_profile,
            environment=environment,
        )

    if request["execution_authorized"] is not False:
        raise _CleanupError(
            "execution_authorized_invalid",
            cleanup_profile=recovered_profile,
            environment=environment,
        )
    if request["process_launch_authorized"] is not False:
        raise _CleanupError(
            "process_launch_authorized_invalid",
            cleanup_profile=recovered_profile,
            environment=environment,
        )

    if _contains_forbidden_authority(request):
        raise _CleanupError(
            "schema_invalid",
            cleanup_profile=recovered_profile,
            environment=environment,
        )

    def _wrap(code: str) -> _CleanupError:
        return _CleanupError(
            code,
            cleanup_profile=recovered_profile,
            environment=environment,
        )

    try:
        authority = _validate_authority_formats(request["cleanup_authority"])
    except _CleanupError as exc:
        raise _wrap(exc.code) from exc

    try:
        trusted_root = _validate_lexical_trusted_root(request["trusted_root"])
    except _CleanupError as exc:
        raise _wrap(exc.code) from exc
    if authority["trusted_root"] != trusted_root:
        raise _wrap("cleanup_authority_mismatch")

    if int(time.time()) >= int(authority["not_after_unix"]):
        raise _wrap("cleanup_authority_expired")

    try:
        stop = _validate_process_stop(request["process_stop_evidence"])
    except _CleanupError as exc:
        raise _wrap(exc.code) from exc

    try:
        evidence = _validate_materialization_evidence(
            request["materialization_evidence"]
        )
    except _CleanupError as exc:
        raise _wrap(exc.code) from exc

    if (
        authority["sandbox_instance_id"] != evidence["sandbox_instance_id"]
        or authority["data_dir_tag"] != DATA_DIR_TAG
        or authority["materialization_report_id"] != evidence["report_id"]
    ):
        raise _wrap("cleanup_authority_mismatch")
    if stop["sandbox_instance_id"] != evidence["sandbox_instance_id"]:
        raise _wrap("process_stop_evidence_invalid")

    try:
        root_stat = _validate_trusted_root_filesystem(trusted_root)
    except _CleanupError as exc:
        raise _wrap(exc.code) from exc

    child_name = str(evidence["child_name"])
    materialization_path = str(evidence["materialization_path"])
    expected_path = _materialization_path_for(trusted_root, child_name)
    if materialization_path != expected_path:
        raise _wrap("target_identity_invalid")
    if child_name != f"{DATA_DIR_TAG}-{evidence['sandbox_instance_id']}":
        raise _wrap("target_identity_invalid")

    try:
        _validate_derived_path(child_name, materialization_path)
    except _CleanupError as exc:
        raise _wrap(exc.code) from exc

    try:
        _assert_direct_child(
            trusted_root, materialization_path, child_name, root_stat
        )
    except _CleanupError as exc:
        raise _wrap(exc.code) from exc

    # Target prechecks
    try:
        tgt_stat = os.lstat(materialization_path)
    except FileNotFoundError as exc:
        raise _wrap("target_absent") from exc
    except OSError as exc:
        # Pre-delete lstat is not a constrained delete operation.
        raise _wrap("substitution_ambiguous") from exc

    if stat.S_ISLNK(tgt_stat.st_mode):
        raise _wrap("symlink_rejected")
    if tgt_stat.st_dev != root_stat.st_dev:
        raise _wrap("substitution_ambiguous")
    if not stat.S_ISDIR(tgt_stat.st_mode):
        raise _wrap("target_identity_invalid")
    if os.path.basename(materialization_path) != child_name:
        raise _wrap("target_identity_invalid")

    try:
        _assert_tagged_disposable(child_name, materialization_path, trusted_root)
    except _CleanupError as exc:
        raise _wrap(exc.code) from exc

    deletion_began = False
    try:
        # Survey may raise survey codes; delete may raise exclusive/partial
        plan = _survey_tree(materialization_path, root_stat.st_dev)
        for path, is_dir in plan:
            try:
                if is_dir:
                    os.rmdir(path)
                else:
                    os.unlink(path)
                deletion_began = True
            except OSError as exc:
                if deletion_began:
                    raise _CleanupError("cleanup_partial_failed") from exc
                raise _CleanupError("exclusive_cleanup_failed") from exc
        _post_cleanup_verify(
            target=materialization_path,
            trusted_root=trusted_root,
            root_stat=root_stat,
            deletion_began=deletion_began,
        )
    except _CleanupError as exc:
        raise _wrap(exc.code) from exc

    return _success(
        request=request,
        evidence=evidence,
        child_name=child_name,
        cleanup_path=materialization_path,
    )


def cleanup_disposable_sandbox_directory_json(
    payload: str | bytes,
) -> SandboxCleanupResult:
    try:
        request = _parse(payload)
        return _evaluate_parsed(request)
    except _CleanupError as exc:
        return _failure(
            exc.code,
            cleanup_profile=exc.cleanup_profile,
            environment=exc.environment,
        )
    except Exception:
        return _failure("internal_error")
