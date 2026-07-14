"""Offline, read-only verifier for the L28 historical-continuity manifest."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Tuple


PROFILE = "l28-historical-continuity/v0.1"
EXPECTED_STATUS = "audit_evidence_only"
MAX_MANIFEST_BYTES = 1_048_576

STABLE_CODES = frozenset(
    {
        "manifest_valid",
        "invalid_manifest_path",
        "manifest_not_found",
        "manifest_symlink_rejected",
        "manifest_not_regular_file",
        "manifest_too_large",
        "manifest_read_error",
        "invalid_json",
        "duplicate_json_key",
        "manifest_not_object",
        "unsupported_manifest_version",
        "invalid_manifest_status",
        "schema_error",
        "invariant_violation",
    }
)

_HEX64 = frozenset("0123456789abcdef")
_MISSING = object()


@dataclass(frozen=True)
class ContinuityVerifyResult:
    """Stable result returned by :func:`verify_manifest`."""

    ok: bool
    code: str
    manifest_sha256: str = ""
    manifest_version: str = ""
    checks: Tuple[str, ...] = ()
    detail: str = ""


class _DuplicateKey(ValueError):
    pass


class _SchemaError(ValueError):
    pass


class _InvariantError(ValueError):
    pass


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _failure(
    code: str,
    *,
    digest: str = "",
    version: str = "",
    detail: str = "",
) -> ContinuityVerifyResult:
    if code not in STABLE_CODES:
        code = "schema_error"
        detail = "unstable_internal_code"
    return ContinuityVerifyResult(
        ok=False,
        code=code,
        manifest_sha256=digest,
        manifest_version=version,
        detail=detail,
    )


def _path_value(root: Mapping[str, Any], dotted: str) -> Any:
    value: Any = root
    for component in dotted.split("."):
        if not isinstance(value, Mapping) or component not in value:
            raise _SchemaError(f"missing:{dotted}")
        value = value[component]
    return value


def _strict_int(root: Mapping[str, Any], dotted: str) -> int:
    value = _path_value(root, dotted)
    if type(value) is not int:
        raise _SchemaError(f"integer:{dotted}")
    return value


def _strict_bool(root: Mapping[str, Any], dotted: str) -> bool:
    value = _path_value(root, dotted)
    if type(value) is not bool:
        raise _SchemaError(f"boolean:{dotted}")
    return value


def _strict_string(root: Mapping[str, Any], dotted: str) -> str:
    value = _path_value(root, dotted)
    if not isinstance(value, str) or not value:
        raise _SchemaError(f"string:{dotted}")
    return value


def _expect(root: Mapping[str, Any], dotted: str, expected: Any) -> None:
    value = _path_value(root, dotted)
    if type(value) is not type(expected) or value != expected:
        raise _InvariantError(f"expected:{dotted}")


def _expect_hex64(root: Mapping[str, Any], dotted: str) -> None:
    value = _strict_string(root, dotted)
    if len(value) != 64 or any(character not in _HEX64 for character in value):
        raise _SchemaError(f"hex64:{dotted}")


def _expect_equation(actual: int, expected: int, name: str) -> None:
    if actual != expected:
        raise _InvariantError(name)


def _validate_manifest(
    manifest: Mapping[str, Any],
) -> tuple[str, tuple[str, ...]]:
    version_value = manifest.get("manifest_version", _MISSING)
    if not isinstance(version_value, str):
        raise _SchemaError("string:manifest_version")
    if version_value != PROFILE:
        raise _InvariantError("unsupported_manifest_version")

    status_value = manifest.get("status", _MISSING)
    if not isinstance(status_value, str):
        raise _SchemaError("string:status")
    if status_value != EXPECTED_STATUS:
        raise _InvariantError("invalid_manifest_status")

    checks: list[str] = []

    _expect(manifest, "protocol_baseline", "1.0.0")
    _expect(manifest, "identity.asset", "L28")
    _expect(manifest, "identity.architecture", "native_blockless_dag_coin")
    _expect(manifest, "identity.smart_contract_identity", False)
    _expect(manifest, "identity.hard_cap", 28_000_000)
    _expect(manifest, "identity.emission_schedule_ceiling", 11_130_000)
    _expect(manifest, "identity.historical_supply_must_not_be_reminted", True)
    checks.append("identity")

    snapshot_physical = _strict_int(
        manifest, "preserved_snapshot.physical_records"
    )
    snapshot_issuance = _strict_int(
        manifest, "preserved_snapshot.issuance_records"
    )
    snapshot_special = _strict_int(
        manifest, "preserved_snapshot.special_records"
    )
    _expect_hex64(manifest, "preserved_snapshot.sha256")
    _expect_hex64(manifest, "preserved_snapshot.final_entry_hash")
    _expect(manifest, "preserved_snapshot.public_timestamp_independently_proven", False)
    _expect_equation(
        snapshot_physical,
        snapshot_issuance + snapshot_special,
        "snapshot_record_partition",
    )
    checks.append("snapshot")

    raw_physical = _strict_int(manifest, "raw_dag.physical_records")
    raw_heights = _strict_int(manifest, "raw_dag.unique_represented_heights")
    raw_extra = _strict_int(manifest, "raw_dag.extra_candidates_not_selected")
    _expect_hex64(manifest, "raw_dag.sha256")
    _expect(manifest, "raw_dag.missing_parents", 0)
    _expect(manifest, "raw_dag.future_parents", 0)
    _expect_equation(
        raw_physical,
        snapshot_issuance + raw_extra,
        "raw_candidate_partition",
    )
    _expect_equation(
        raw_heights,
        snapshot_issuance,
        "represented_height_count",
    )
    checks.append("raw_dag")

    _expect(
        manifest,
        "reconstruction.selection",
        "first_physical_raw_candidate_per_represented_height",
    )
    _expect(manifest, "reconstruction.ordering", "ascending_height")
    _expect(
        manifest,
        "reconstruction.serialization",
        "python_json_dumps_default",
    )
    _expect(
        manifest,
        "reconstruction.appendage",
        "two_chained_SYSTEM_TREASURY_LOCK_attestations",
    )
    _expect(
        manifest,
        "reconstruction.deterministic_content_and_order_confirmed",
        True,
    )
    checks.append("reconstruction")

    first_root = _strict_int(manifest, "parent_graph.first_root")
    parent_snapshot = _strict_int(
        manifest, "parent_graph.parent_in_snapshot"
    )
    parent_raw = _strict_int(
        manifest, "parent_graph.parent_only_in_raw_dag"
    )
    _expect(manifest, "parent_graph.snapshot_self_contained", False)
    _expect(manifest, "parent_graph.cycle_detected_on_final_path", False)
    _expect_equation(
        first_root + parent_snapshot + parent_raw,
        snapshot_physical,
        "parent_resolution_partition",
    )
    checks.append("parent_graph")

    declared = _strict_int(
        manifest, "economics.historical_declared_supply"
    )
    recorded = _strict_int(
        manifest, "economics.physical_recorded_reward_total"
    )
    missing_count = _strict_int(
        manifest, "economics.missing_height_count"
    )
    missing_amount = _strict_int(
        manifest, "economics.missing_height_implied_amount"
    )
    lock_amount = _strict_int(
        manifest, "economics.treasury_lock_commitment"
    )
    unlocked = _strict_int(
        manifest, "economics.derived_unlocked_amount"
    )
    _expect_equation(recorded, snapshot_issuance * 28, "recorded_rewards")
    _expect_equation(missing_amount, missing_count * 28, "missing_height_amount")
    _expect_equation(declared, recorded + missing_amount, "declared_supply")
    _expect_equation(unlocked, declared - lock_amount, "derived_unlocked")
    _expect(manifest, "economics.treasury_attestation_records", 2)
    _expect(manifest, "economics.treasury_economic_commitments_counted", 1)
    _expect(
        manifest,
        "economics.derived_unlocked_is_live_spendable_proof",
        False,
    )
    checks.append("economics")

    consolidated = _strict_int(manifest, "consolidation.total_amount")
    reward_units = _strict_int(manifest, "consolidation.reward_units")
    genesis_reward = _strict_int(
        manifest, "consolidation.unconsolidated_genesis_reward"
    )
    _expect_hex64(manifest, "consolidation.sha256")
    _expect_equation(consolidated, reward_units * 28, "consolidated_rewards")
    _expect_equation(
        consolidated + genesis_reward,
        recorded,
        "consolidation_remainder",
    )
    _expect(manifest, "consolidation.genesis_reward_excluded", True)
    _expect(manifest, "consolidation.all_records_target_verified_creator", True)
    _expect(manifest, "consolidation.creator_live_balance_proven", False)
    _expect(manifest, "consolidation.writer_source_recovered", False)
    _expect(manifest, "consolidation.writer_execution_provenance", False)
    checks.append("consolidation")

    _expect(manifest, "mining.active", False)
    _expect(manifest, "mining.canonical_pow_formula_defined_in_v1", False)
    _expect(manifest, "mining.difficulty_18_is_consensus", False)
    _expect(manifest, "mining.automatic_creator_reward_routing", False)
    _expect(
        manifest,
        "mining.accepted_coinbase_receiver_must_match_declared_miner",
        True,
    )
    _expect(manifest, "mining.winning_proof_binding_implemented", False)
    checks.append("mining")

    for field in (
        "new_ledger_created",
        "historical_ledger_copied_to_public_repository",
        "canonical_continuation_proven",
        "canonical_issuance_initialized",
        "network_started",
        "wallet_spendability_proven",
    ):
        if _strict_bool(manifest, f"activation.{field}") is not False:
            raise _InvariantError(f"activation:{field}")
    checks.append("activation")

    return version_value, tuple(checks)


def verify_manifest(path: os.PathLike[str] | str) -> ContinuityVerifyResult:
    """Verify one explicitly supplied manifest without writing or discovery."""

    try:
        raw_path = os.fspath(path)
    except TypeError:
        return _failure("invalid_manifest_path")

    if not isinstance(raw_path, str) or not raw_path:
        return _failure("invalid_manifest_path")

    manifest_path = Path(raw_path)

    try:
        if manifest_path.is_symlink():
            return _failure("manifest_symlink_rejected")
        metadata = manifest_path.stat()
    except FileNotFoundError:
        return _failure("manifest_not_found")
    except OSError:
        return _failure("manifest_read_error")

    if not stat.S_ISREG(metadata.st_mode):
        return _failure("manifest_not_regular_file")
    if metadata.st_size > MAX_MANIFEST_BYTES:
        return _failure("manifest_too_large")

    try:
        raw = manifest_path.read_bytes()
    except OSError:
        return _failure("manifest_read_error")

    digest = hashlib.sha256(raw).hexdigest()

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs_no_duplicates,
        )
    except _DuplicateKey:
        return _failure("duplicate_json_key", digest=digest)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _failure("invalid_json", digest=digest)

    if not isinstance(value, dict):
        return _failure("manifest_not_object", digest=digest)

    version = value.get("manifest_version", "")
    version_text = version if isinstance(version, str) else ""

    try:
        validated_version, checks = _validate_manifest(value)
    except _SchemaError as exc:
        return _failure(
            "schema_error",
            digest=digest,
            version=version_text,
            detail=str(exc),
        )
    except _InvariantError as exc:
        detail = str(exc)
        if detail == "unsupported_manifest_version":
            code = "unsupported_manifest_version"
        elif detail == "invalid_manifest_status":
            code = "invalid_manifest_status"
        else:
            code = "invariant_violation"
        return _failure(
            code,
            digest=digest,
            version=version_text,
            detail=detail,
        )

    return ContinuityVerifyResult(
        ok=True,
        code="manifest_valid",
        manifest_sha256=digest,
        manifest_version=validated_version,
        checks=checks,
    )


__all__ = [
    "ContinuityVerifyResult",
    "EXPECTED_STATUS",
    "MAX_MANIFEST_BYTES",
    "PROFILE",
    "STABLE_CODES",
    "verify_manifest",
]
