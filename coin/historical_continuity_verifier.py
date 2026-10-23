"""Offline, read-only verifier for the L28 historical-continuity manifest."""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Tuple


PROFILE = "l28-historical-continuity/v0.1"
EXPECTED_STATUS = "audit_evidence_only"
MAX_MANIFEST_BYTES = 1_048_576

# Code-owned reference, never loaded from the candidate manifest at runtime.
# Economics: PROJECT_RULES/Protocol; historical claims: frozen Foundation16
# audit + manifest at d7b6270. Raw/snapshot fingerprints, sizes, counts and
# heights independently rechecked against the operator-specified public bytes.
# Pinning a recorded claim (e.g. consolidation hash or claimed timestamp) is
# NOT independent proof of the underlying event, ownership or consensus.
PINNED_MANIFEST_REFERENCES = (
    ("activation.canonical_continuation_proven", False),
    ("activation.canonical_issuance_initialized", False),
    ("activation.historical_ledger_copied_to_public_repository", False),
    ("activation.network_started", False),
    ("activation.new_ledger_created", False),
    ("activation.wallet_spendability_proven", False),
    ("audit_date", "2026-07-14"),
    ("consolidation.all_records_target_verified_creator", True),
    ("consolidation.creator_live_balance_proven", False),
    ("consolidation.genesis_reward_excluded", True),
    ("consolidation.records", 205),
    ("consolidation.reward_units", 72095),
    ("consolidation.sha256", "78de2831a5f1631c79e2a5f5b702887be149a1517b32ff9d3edb35c7b59f73d7"),
    ("consolidation.total_amount", 2018660),
    ("consolidation.unconsolidated_genesis_reward", 28),
    ("consolidation.writer_execution_provenance", False),
    ("consolidation.writer_source_recovered", False),
    ("economics.derived_unlocked_amount", 2324584),
    ("economics.derived_unlocked_is_live_spendable_proof", False),
    ("economics.historical_declared_supply", 2824584),
    ("economics.missing_height_count", 28782),
    ("economics.missing_height_implied_amount", 805896),
    ("economics.physical_recorded_reward_total", 2018688),
    ("economics.treasury_attestation_records", 2),
    ("economics.treasury_economic_commitments_counted", 1),
    ("economics.treasury_lock_commitment", 500000),
    ("identity.architecture", "native_blockless_dag_coin"),
    ("identity.asset", "L28"),
    ("identity.emission_schedule_ceiling", 11130000),
    ("identity.hard_cap", 28000000),
    ("identity.historical_supply_must_not_be_reminted", True),
    ("identity.smart_contract_identity", False),
    ("manifest_version", "l28-historical-continuity/v0.1"),
    ("mining.accepted_coinbase_receiver_must_match_declared_miner", True),
    ("mining.active", False),
    ("mining.automatic_creator_reward_routing", False),
    ("mining.canonical_pow_formula_defined_in_v1", False),
    ("mining.difficulty_18_is_consensus", False),
    ("mining.winning_proof_binding_implemented", False),
    ("parent_graph.cycle_detected_on_final_path", False),
    ("parent_graph.dag_leaf_count", 20694),
    ("parent_graph.final_lock_parent_path_length", 4),
    ("parent_graph.first_root", 1),
    ("parent_graph.parent_in_snapshot", 51426),
    ("parent_graph.parent_only_in_raw_dag", 20671),
    ("parent_graph.snapshot_self_contained", False),
    ("preserved_snapshot.claimed_timestamp", "2025-11-15T13:08:38.085676Z"),
    ("preserved_snapshot.final_entry_hash", "589034a1c80f6ba8f5d6b90baf0cf247b0b71a0b63e677f1b89028be643156d4"),
    ("preserved_snapshot.final_entry_height", 100879),
    ("preserved_snapshot.issuance_records", 72096),
    ("preserved_snapshot.last_issuance_height", 100877),
    ("preserved_snapshot.physical_records", 72098),
    ("preserved_snapshot.public_timestamp_independently_proven", False),
    ("preserved_snapshot.sha256", "6580333e4dba688f242d82a9ea7253369b7723273b3392dc6d8ae9b78d9b2d11"),
    ("preserved_snapshot.size_bytes", 30658355),
    ("preserved_snapshot.special_records", 2),
    ("protocol_baseline", "1.0.0"),
    ("raw_dag.extra_candidates_not_selected", 30167),
    ("raw_dag.future_parents", 0),
    ("raw_dag.missing_parents", 0),
    ("raw_dag.physical_records", 102263),
    ("raw_dag.sha256", "1ba544052cee098cea265add04c8fb0ff0562897803ba829b201293745aad669"),
    ("raw_dag.size_bytes", 40707627),
    ("raw_dag.unique_represented_heights", 72096),
    ("reconstruction.appendage", "two_chained_SYSTEM_TREASURY_LOCK_attestations"),
    ("reconstruction.deterministic_content_and_order_confirmed", True),
    ("reconstruction.ordering", "ascending_height"),
    ("reconstruction.selection", "first_physical_raw_candidate_per_represented_height"),
    ("reconstruction.serialization", "python_json_dumps_default"),
    ("status", "audit_evidence_only"),
)
REFERENCE_NEXT_CANONICAL_HEIGHT = 100878


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


def _validate_pinned_references(manifest: Mapping[str, Any]) -> None:
    # Closed schema prevents aliases/extensions from smuggling contradictory
    # supply, height, provenance or authority claims into a successful report.
    root_keys: set[str] = set()
    groups: dict[str, set[str]] = {}
    for dotted, expected in PINNED_MANIFEST_REFERENCES:
        parts = dotted.split(".")
        root_keys.add(parts[0])
        if len(parts) == 2:
            groups.setdefault(parts[0], set()).add(parts[1])
        actual = _path_value(manifest, dotted)
        if type(actual) is not type(expected):
            raise _SchemaError(f"type:{dotted}")
        if actual != expected:
            raise _InvariantError(f"pinned_reference:{dotted}")
    if set(manifest) != root_keys:
        raise _SchemaError("unexpected_manifest_fields")
    for group, keys in groups.items():
        if type(manifest[group]) is not dict or set(manifest[group]) != keys:
            raise _SchemaError(f"unexpected_fields:{group}")
    # The manifest stores last issuance height, not a live next-height state.
    _expect_equation(
        _strict_int(manifest, "preserved_snapshot.last_issuance_height") + 1,
        REFERENCE_NEXT_CANONICAL_HEIGHT,
        "reference_next_canonical_height",
    )


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

    _validate_pinned_references(manifest)
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
    except (UnicodeDecodeError, ValueError, RecursionError):
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


# This is an evidence profile, not a consensus policy or ledger bootstrap.
POW_PROFILE = "l28-historical-pow-evidence/v0.1"
RAW_SHA256 = "1ba544052cee098cea265add04c8fb0ff0562897803ba829b201293745aad669"
SNAPSHOT_SHA256 = "6580333e4dba688f242d82a9ea7253369b7723273b3392dc6d8ae9b78d9b2d11"
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_RECORD_BYTES = 8192
MAX_RECORDS = 110_000
POW_CODES = frozenset({
    "pow_evidence_valid", "artifact_path_error", "artifact_read_error",
    "artifact_not_regular", "artifact_too_large", "artifact_hash_mismatch",
    "record_too_large", "record_limit", "invalid_record_json",
    "duplicate_record_key", "record_schema_error", "duplicate_record",
    "record_count_mismatch", "pow_count_mismatch", "pow_hash_mismatch",
    "parent_missing", "parent_height_mismatch", "recorded_difficulty_invalid",
    "selected_record_mismatch",
})
_ISSUANCE_FIELDS = frozenset({
    "entry_height", "hash", "prev", "payload", "current_supply", "reward",
    "qubits", "poi_q", "poi_v", "validator_s", "ts",
})


class _PowError(ValueError):
    """Only fixed codes, never input content, reach evidence reports."""


def _pow_require(condition: bool, code: str = "record_schema_error") -> None:
    if not condition:
        raise _PowError(code)


def _bounded_json(value: Any, depth: int = 0) -> None:
    _pow_require(depth <= 16)
    if type(value) is dict:
        _pow_require(len(value) <= 256)
        for key, child in value.items():
            _pow_require(type(key) is str and len(key) <= 1024)
            _bounded_json(child, depth + 1)
    elif type(value) is list:
        _pow_require(len(value) <= 256)
        for child in value:
            _bounded_json(child, depth + 1)
    elif type(value) is str:
        _pow_require(len(value) <= 4096 and not any(
            0xD800 <= ord(char) <= 0xDFFF for char in value
        ))
    elif type(value) is float:
        _pow_require(math.isfinite(value))
    elif type(value) is int:
        _pow_require(abs(value) <= 2**63 - 1)
    else:
        _pow_require(value is None or type(value) is bool)


def _hex64(value: Any) -> bool:
    return type(value) is str and len(value) == 64 and set(value) <= _HEX64


def _record_core(record: Any) -> None:
    _pow_require(type(record) is dict)
    _bounded_json(record)
    _pow_require(type(record.get("entry_height")) is int
                 and record["entry_height"] >= 0)
    _pow_require(_hex64(record.get("hash")) and _hex64(record.get("prev")))


def _issuance_shape(record: dict, *, pow_record: bool) -> None:
    expected = _ISSUANCE_FIELDS | ({"difficulty"} if pow_record else set())
    _pow_require(set(record) == expected and type(record["payload"]) is dict)
    for key in ("current_supply", "reward", "poi_q", "poi_v", "validator_s", "ts"):
        _pow_require(type(record[key]) in (int, float) and record[key] >= 0)
    _pow_require(type(record["qubits"]) is int and record["qubits"] >= 0)


def _pow_preimage(record: dict) -> bytes:
    """Reconstruct stored evidence only; never search for a nonce."""
    _record_core(record)
    _issuance_shape(record, pow_record=True)
    payload = record["payload"]
    _pow_require(set(payload) == {"type", "miner", "timestamp", "nonce"})
    _pow_require(payload["type"] == "mining")
    for key in ("miner", "timestamp"):
        _pow_require(type(payload[key]) is str and bool(payload[key]))
    _pow_require(type(payload["nonce"]) is int and payload["nonce"] >= 0)
    _pow_require(type(record["difficulty"]) is int and record["difficulty"] == 4,
                 "recorded_difficulty_invalid")
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False)
    return (str(record["entry_height"]) + record["prev"] + rendered
            + str(payload["nonce"])).encode("utf-8")


def _verify_pow_record(record: dict, raw_index: Mapping[str, dict]) -> str:
    """Shared record checks, independently testable without artifact pins."""
    calculated = hashlib.sha256(_pow_preimage(record)).hexdigest()
    _pow_require(calculated == record["hash"], "pow_hash_mismatch")
    _pow_require(calculated.startswith("0" * record["difficulty"]),
                 "recorded_difficulty_invalid")
    parent = raw_index.get(record["prev"])
    _pow_require(parent is not None, "parent_missing")
    _record_core(parent)
    _pow_require(parent["hash"] == record["prev"], "parent_missing")
    _pow_require(record["entry_height"] == parent["entry_height"] + 1,
                 "parent_height_mismatch")
    return calculated


def _read_pow_artifact(path: os.PathLike[str] | str) -> bytes:
    # Open once, disallow final symlinks, avoid blocking on FIFO/device inputs,
    # then validate the opened descriptor. Parse only these fingerprinted bytes.
    try:
        name = os.fspath(path)
        if not isinstance(name, str) or not name:
            raise _PowError("artifact_path_error")
        fd = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as source:
            info = os.fstat(source.fileno())
            _pow_require(stat.S_ISREG(info.st_mode), "artifact_not_regular")
            _pow_require(info.st_size <= MAX_ARTIFACT_BYTES, "artifact_too_large")
            data = source.read(MAX_ARTIFACT_BYTES + 1)
            _pow_require(len(data) <= MAX_ARTIFACT_BYTES, "artifact_too_large")
            return data
    except (TypeError, ValueError) as exc:
        if isinstance(exc, _PowError):
            raise
        raise _PowError("artifact_path_error") from None
    except OSError:
        raise _PowError("artifact_read_error") from None


def _parse_pow_records(data: bytes) -> dict[str, dict]:
    index: dict[str, dict] = {}
    # LF is the JSONL separator; do not silently skip empty/malformed records.
    lines = data.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    _pow_require(len(lines) <= MAX_RECORDS, "record_limit")
    for line in lines:
        _pow_require(len(line) <= MAX_RECORD_BYTES, "record_too_large")
        try:
            record = json.loads(line.decode("utf-8"),
                                object_pairs_hook=_pairs_no_duplicates)
        except _DuplicateKey:
            raise _PowError("duplicate_record_key") from None
        except (UnicodeError, ValueError, RecursionError):
            raise _PowError("invalid_record_json") from None
        _record_core(record)
        _pow_require(record["hash"] not in index, "duplicate_record")
        index[record["hash"]] = record
    return index


def _verify_selected_pow(record: dict, raw: Mapping[str, dict]) -> None:
    _record_core(record)
    original = raw.get(record["hash"])
    # JSON comparison distinguishes Boolean/int and int/float values.
    _pow_require(original is not None and
                 json.dumps(original, sort_keys=True, allow_nan=False) ==
                 json.dumps(record, sort_keys=True, allow_nan=False),
                 "selected_record_mismatch")
    _verify_pow_record(record, raw)


def _verify_pow_indexes(raw: dict[str, dict], snapshot: dict[str, dict]) -> dict:
    _pow_require(len(raw) == 102263 and len(snapshot) == 72098,
                 "record_count_mismatch")
    raw_pow = [r for r in raw.values() if "difficulty" in r]
    selected = [r for r in snapshot.values() if "difficulty" in r]
    _pow_require(len(raw_pow) == 2202 and len(selected) == 817,
                 "pow_count_mismatch")
    for record in raw.values():
        _issuance_shape(record, pow_record="difficulty" in record)
    source_passes = 0
    for record in raw_pow:
        digest = _verify_pow_record(record, raw)
        source_passes += digest.startswith("0" * 12)
    for record in selected:
        _verify_selected_pow(record, raw)
    return {
        "raw_records": len(raw), "snapshot_records": len(snapshot),
        "raw_pow_verified": len(raw_pow), "selected_pow_verified": len(selected),
        "source_difficulty_12_hash_passes": source_passes,
    }


def verify_pow_artifacts(raw_path: os.PathLike[str] | str,
                         snapshot_path: os.PathLike[str] | str) -> dict[str, Any]:
    """Pinned historical evidence only. No caller-supplied trust override."""
    report: dict[str, Any] = {
        "profile": POW_PROFILE, "ok": False, "code": "artifact_read_error",
        "scope": "historical_pow_evidence_only",
        "HASH_VALID": False, "RECORDED_DIFFICULTY_VALID": False,
        "HISTORICAL_POLICY_AUTHENTICATED": False, "CANONICAL_ACCEPTANCE": False,
        "historical_policy_status": "UNPROVEN",
        "canonical_acceptance_status": "BLOCKED",
        "recorded_difficulty": 4, "recovered_source_difficulty": 12,
        "source_policy_status": "MISMATCH_NOT_CONSENSUS_AUTHORITY",
        "limitations": ["outer_economic_fields_not_pow_bound",
                        "non_pow_identities_not_recomputed",
                        "no_issuance_or_spendability_proof"],
    }
    try:
        raw_bytes = _read_pow_artifact(raw_path)
        snapshot_bytes = _read_pow_artifact(snapshot_path)
        report["raw_sha256"] = hashlib.sha256(raw_bytes).hexdigest()
        report["snapshot_sha256"] = hashlib.sha256(snapshot_bytes).hexdigest()
        _pow_require(report["raw_sha256"] == RAW_SHA256 and
                     report["snapshot_sha256"] == SNAPSHOT_SHA256,
                     "artifact_hash_mismatch")
        raw = _parse_pow_records(raw_bytes)
        snapshot = _parse_pow_records(snapshot_bytes)
        report.update(_verify_pow_indexes(raw, snapshot))
    except _PowError as exc:
        code = str(exc)
        report["code"] = code if code in POW_CODES else "record_schema_error"
        return report
    report.update(ok=True, code="pow_evidence_valid", HASH_VALID=True,
                  RECORDED_DIFFICULTY_VALID=True)
    return report


__all__ = [
    "ContinuityVerifyResult",
    "EXPECTED_STATUS",
    "MAX_MANIFEST_BYTES",
    "PROFILE",
    "STABLE_CODES",
    "verify_manifest",
    "verify_pow_artifacts",
]
