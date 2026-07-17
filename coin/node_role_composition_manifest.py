"""Offline inert L28 node-role composition-manifest verification.

This module verifies caller-supplied pure data.  It does not construct nodes,
discover files, access a network or ledger, or authorize activation.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from . import node_role_model as role_model
from . import node_role_scenario_suite_evidence as evidence_core
from . import node_role_scenario_suite_evidence_cli as evidence_cli


MANIFEST_VERSION = "l28-node-role-composition-manifest/v0.1"
VERIFIER_VERSION = "l28-node-role-composition-manifest-verifier/v0.1"
SECURITY_PROFILE_VERSION = "l28-core-p2p-security/v0.1"
SECURITY_PROFILE_SHA256 = (
    "61e787f9f665d76a704d5e6dca8bccc6a80bb3ed231ac741fb5b7497383b04f6"
)
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_COMPONENT_ID_LENGTH = 64
COMPONENT_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

STABLE_CODES = (
    "manifest_valid",
    "input_type_invalid",
    "manifest_too_large",
    "invalid_encoding",
    "invalid_json",
    "duplicate_key",
    "schema_error",
    "version_unsupported",
    "security_profile_mismatch",
    "component_invalid",
    "capability_invalid",
    "trust_boundary_invalid",
    "runtime_configuration_present",
    "evidence_invalid",
    "evidence_report_invalid",
    "evidence_binding_invalid",
    "internal_error",
)

SUCCESS_CHECKS = (
    "identity",
    "schema",
    "security_profile_binding",
    "components",
    "capabilities",
    "trust_boundaries",
    "runtime_absence",
    "evidence_verification",
    "evidence_report",
    "evidence_binding",
    "semantic_commitment",
)

TOP_LEVEL_FIELDS = frozenset(
    {
        "manifest_version",
        "security_profile",
        "components",
        "trust_boundaries",
        "runtime_configuration",
        "evidence",
        "evidence_report",
    }
)
SECURITY_PROFILE_FIELDS = frozenset({"profile_version", "sha256"})
COMPONENT_FIELDS = frozenset(
    {"component_id", "role", "initial_state", "trust", "owns", "prohibited"}
)
TRUST_BOUNDARY_FIELDS = frozenset(
    {"id", "input_trust", "required_controls"}
)
RUNTIME_CONFIGURATION_FIELDS = frozenset(
    {
        "endpoints",
        "listeners",
        "peers",
        "credentials",
        "automatic_discovery",
        "activation_authorized",
    }
)

ROLE_DECLARATIONS: dict[str, dict[str, object]] = {
    role_model.CORE_ROLE: {
        "trust": "native_policy_coordinator",
        "owns": (
            "lifecycle_policy",
            "native_validation_coordination",
            "issuance_readiness_policy",
            "persistence_authorization",
            "checkpoint_admission_policy",
        ),
        "prohibited": (
            "network_listen",
            "network_connect",
            "peer_discovery",
            "participant_signing",
            "wallet_custody",
            "automatic_historical_state_discovery",
            "automatic_canonical_designation",
            "automatic_creator_reward_routing",
        ),
    },
    role_model.P2P_ROLE: {
        "trust": "untrusted_transport_boundary",
        "owns": (
            "bounded_frame_decoding",
            "peer_session_policy",
            "peer_replay_policy",
            "candidate_forwarding",
            "transport_pause_and_shutdown",
        ),
        "prohibited": (
            "native_ledger_mutation",
            "mint_authorization",
            "issued_supply_change",
            "checkpoint_canonicalization",
            "core_decision_override",
            "participant_signing",
            "wallet_custody",
            "private_historical_state_loading",
            "wrapped_asset_identity_substitution",
        ),
    },
}

TRUST_BOUNDARY_DECLARATIONS: dict[str, dict[str, object]] = {
    "peer_to_p2p": {
        "input_trust": "untrusted",
        "required_controls": (
            "predecode_size_limit",
            "deterministic_decode",
            "network_and_protocol_binding",
            "peer_identity_evidence",
            "nonce_and_replay_validation",
            "timestamp_and_expiry_validation",
        ),
    },
    "p2p_to_core": {
        "input_trust": "normalized_but_untrusted",
        "required_controls": (
            "immutable_candidate_projection",
            "native_transaction_validation",
            "signature_verification",
            "issuance_and_supply_invariants",
            "checkpoint_policy_when_applicable",
            "no_transport_decision_override",
        ),
    },
    "core_to_persistence": {
        "input_trust": "validated_candidate_only",
        "required_controls": (
            "atomic_commit_boundary",
            "deterministic_identity",
            "replay_state_consistency",
            "failure_before_partial_mutation",
            "auditable_result",
        ),
    },
    "checkpoint_to_core": {
        "input_trust": "untrusted_evidence",
        "required_controls": (
            "explicit_caller_supplied_input",
            "duplicate_key_rejection",
            "schema_and_version_validation",
            "hash_size_and_count_commitments",
            "parent_graph_and_supply_checks",
            "enforced_provenance",
            "separate_canonical_authorization",
        ),
    },
}


class _DuplicateKey(ValueError):
    pass


class _ManifestError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class NodeRoleCompositionManifestResult:
    ok: bool
    code: str
    manifest_sha256: str
    security_profile_sha256: str
    evidence_sha256: str
    evidence_report_id: str
    component_ids: tuple[str, ...]
    roles: tuple[str, ...]
    trust_boundary_ids: tuple[str, ...]
    checks: tuple[str, ...]
    detail: str = ""
    manifest_version: str = MANIFEST_VERSION
    security_profile_version: str = SECURITY_PROFILE_VERSION
    evidence_version: str = evidence_core.EVIDENCE_VERSION
    evidence_report_version: str = evidence_cli.REPORT_VERSION
    verifier_version: str = VERIFIER_VERSION


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_composition_manifest_sha256(manifest: object) -> str:
    """Return the SHA-256 of the canonical logical manifest."""

    return hashlib.sha256(_canonical_json(manifest)).hexdigest()


def _object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(value)


def parse_node_role_composition_manifest_json(
    payload: str | bytes,
) -> dict[str, Any]:
    """Parse bounded UTF-8 JSON with duplicate keys and nonfinite values rejected."""

    if not isinstance(payload, (str, bytes)):
        raise _ManifestError("input_type_invalid", "manifest must be text or bytes")

    if isinstance(payload, bytes):
        if len(payload) > MAX_MANIFEST_BYTES:
            raise _ManifestError("manifest_too_large", "manifest exceeds size limit")
        try:
            text = payload.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise _ManifestError("invalid_encoding", "manifest is not valid UTF-8") from exc
    else:
        try:
            encoded = payload.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise _ManifestError("invalid_encoding", "manifest is not valid UTF-8") from exc
        if len(encoded) > MAX_MANIFEST_BYTES:
            raise _ManifestError("manifest_too_large", "manifest exceeds size limit")
        text = payload

    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_no_duplicates,
            parse_constant=_reject_nonfinite,
        )
    except _DuplicateKey as exc:
        raise _ManifestError("duplicate_key", "manifest contains a duplicate key") from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise _ManifestError("invalid_json", "manifest is not valid strict JSON") from exc

    if not isinstance(value, dict):
        raise _ManifestError("schema_error", "manifest must be a JSON object")
    return value


def _require_exact_fields(
    value: object,
    fields: frozenset[str],
    label: str,
    code: str = "schema_error",
) -> dict[str, Any]:
    if not isinstance(value, dict) or frozenset(value) != fields:
        raise _ManifestError(code, f"{label} fields are not exact")
    return value


def _require_string(value: object, label: str, code: str) -> str:
    if not isinstance(value, str) or not value:
        raise _ManifestError(code, f"{label} must be a nonempty string")
    return value


def _require_string_list(value: object, label: str, code: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise _ManifestError(code, f"{label} must be a string array")
    if len(set(value)) != len(value):
        raise _ManifestError(code, f"{label} contains duplicates")
    return tuple(value)


def _validate_security_profile(manifest: dict[str, Any]) -> None:
    binding = _require_exact_fields(
        manifest["security_profile"],
        SECURITY_PROFILE_FIELDS,
        "security profile binding",
        "security_profile_mismatch",
    )
    if binding["profile_version"] != SECURITY_PROFILE_VERSION:
        raise _ManifestError(
            "security_profile_mismatch", "security profile version does not match"
        )
    digest = binding["sha256"]
    if (
        not isinstance(digest, str)
        or HEX64_RE.fullmatch(digest) is None
        or digest != SECURITY_PROFILE_SHA256
    ):
        raise _ManifestError(
            "security_profile_mismatch", "security profile commitment does not match"
        )


def _validate_components(manifest: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    components = manifest["components"]
    if not isinstance(components, list) or len(components) != len(ROLE_DECLARATIONS):
        raise _ManifestError(
            "component_invalid", "exactly one component per required role is required"
        )

    component_ids: list[str] = []
    roles: list[str] = []
    for index, item in enumerate(components):
        component = _require_exact_fields(
            item, COMPONENT_FIELDS, f"component {index}", "component_invalid"
        )
        component_id = _require_string(
            component["component_id"], "component identifier", "component_invalid"
        )
        if (
            len(component_id) > MAX_COMPONENT_ID_LENGTH
            or COMPONENT_ID_RE.fullmatch(component_id) is None
        ):
            raise _ManifestError(
                "component_invalid", "component identifier is not canonical"
            )
        role = _require_string(component["role"], "component role", "component_invalid")
        if role not in ROLE_DECLARATIONS:
            raise _ManifestError("component_invalid", "component role is unknown")
        if role in roles:
            raise _ManifestError("component_invalid", "component role is duplicated")
        if component["initial_state"] != "CREATED":
            raise _ManifestError(
                "component_invalid", "component initial state must be CREATED"
            )
        expected = ROLE_DECLARATIONS[role]
        if component["trust"] != expected["trust"]:
            raise _ManifestError("capability_invalid", "component trust does not match")
        owns = _require_string_list(
            component["owns"], "owned capabilities", "capability_invalid"
        )
        prohibited = _require_string_list(
            component["prohibited"], "prohibited capabilities", "capability_invalid"
        )
        if owns != expected["owns"] or prohibited != expected["prohibited"]:
            raise _ManifestError(
                "capability_invalid", "component capabilities do not match the profile"
            )
        component_ids.append(component_id)
        roles.append(role)

    if len(set(component_ids)) != len(component_ids):
        raise _ManifestError("component_invalid", "component identifiers are not unique")
    if set(roles) != set(ROLE_DECLARATIONS):
        raise _ManifestError("component_invalid", "required role composition is incomplete")
    return tuple(component_ids), tuple(roles)


def _validate_trust_boundaries(manifest: dict[str, Any]) -> tuple[str, ...]:
    boundaries = manifest["trust_boundaries"]
    if not isinstance(boundaries, list) or len(boundaries) != len(
        TRUST_BOUNDARY_DECLARATIONS
    ):
        raise _ManifestError(
            "trust_boundary_invalid", "all public trust boundaries are required"
        )

    identifiers: list[str] = []
    for index, item in enumerate(boundaries):
        boundary = _require_exact_fields(
            item,
            TRUST_BOUNDARY_FIELDS,
            f"trust boundary {index}",
            "trust_boundary_invalid",
        )
        identifier = _require_string(
            boundary["id"], "trust boundary identifier", "trust_boundary_invalid"
        )
        expected = TRUST_BOUNDARY_DECLARATIONS.get(identifier)
        if expected is None:
            raise _ManifestError(
                "trust_boundary_invalid", "trust boundary identifier is unknown"
            )
        if boundary["input_trust"] != expected["input_trust"]:
            raise _ManifestError(
                "trust_boundary_invalid", "trust boundary input trust does not match"
            )
        controls = _require_string_list(
            boundary["required_controls"],
            "required controls",
            "trust_boundary_invalid",
        )
        if controls != expected["required_controls"]:
            raise _ManifestError(
                "trust_boundary_invalid", "trust boundary controls do not match"
            )
        identifiers.append(identifier)

    if len(set(identifiers)) != len(identifiers) or set(identifiers) != set(
        TRUST_BOUNDARY_DECLARATIONS
    ):
        raise _ManifestError(
            "trust_boundary_invalid", "trust boundary declarations are incomplete"
        )
    return tuple(identifiers)


def _validate_runtime_absence(manifest: dict[str, Any]) -> None:
    runtime = _require_exact_fields(
        manifest["runtime_configuration"],
        RUNTIME_CONFIGURATION_FIELDS,
        "runtime configuration",
        "runtime_configuration_present",
    )
    for field in ("endpoints", "listeners", "peers", "credentials"):
        if type(runtime[field]) is not list or runtime[field]:
            raise _ManifestError(
                "runtime_configuration_present", f"runtime {field} must be empty"
            )
    for field in ("automatic_discovery", "activation_authorized"):
        if type(runtime[field]) is not bool or runtime[field] is not False:
            raise _ManifestError(
                "runtime_configuration_present", f"runtime {field} must be false"
            )


def _validate_evidence(
    manifest: dict[str, Any],
) -> evidence_core.NodeRoleScenarioSuiteEvidenceResult:
    evidence = manifest["evidence"]
    report = manifest["evidence_report"]
    if not isinstance(evidence, dict):
        raise _ManifestError("evidence_invalid", "evidence must be an object")
    if not isinstance(report, dict):
        raise _ManifestError(
            "evidence_report_invalid", "evidence report must be an object"
        )

    result = evidence_core.verify_scenario_suite_evidence_json(_canonical_json(evidence))
    if not result.ok:
        raise _ManifestError("evidence_invalid", "Foundation 25 evidence is invalid")
    expected_report = evidence_cli.build_report(result)
    if report != expected_report:
        raise _ManifestError(
            "evidence_binding_invalid",
            "Foundation 25 evidence report does not match the evidence",
        )
    if report.get("report_id") != result.report_id and report.get(
        "source_report_id"
    ) != result.report_id:
        raise _ManifestError(
            "evidence_binding_invalid", "Foundation 25 source report binding is invalid"
        )
    return result


def _failure(code: str, detail: str) -> NodeRoleCompositionManifestResult:
    return NodeRoleCompositionManifestResult(
        ok=False,
        code=code,
        manifest_sha256="",
        security_profile_sha256="",
        evidence_sha256="",
        evidence_report_id="",
        component_ids=(),
        roles=(),
        trust_boundary_ids=(),
        checks=(),
        detail=detail,
    )


class NodeRoleCompositionManifestVerifier:
    @classmethod
    def verify_json(cls, payload: str | bytes) -> NodeRoleCompositionManifestResult:
        try:
            manifest = parse_node_role_composition_manifest_json(payload)
            _require_exact_fields(manifest, TOP_LEVEL_FIELDS, "manifest")
            if manifest["manifest_version"] != MANIFEST_VERSION:
                raise _ManifestError(
                    "version_unsupported", "manifest version is unsupported"
                )
            _validate_security_profile(manifest)
            component_ids, roles = _validate_components(manifest)
            boundary_ids = _validate_trust_boundaries(manifest)
            _validate_runtime_absence(manifest)
            evidence_result = _validate_evidence(manifest)
            manifest_sha256 = compute_composition_manifest_sha256(manifest)
            return NodeRoleCompositionManifestResult(
                ok=True,
                code="manifest_valid",
                manifest_sha256=manifest_sha256,
                security_profile_sha256=SECURITY_PROFILE_SHA256,
                evidence_sha256=evidence_result.evidence_sha256,
                evidence_report_id=manifest["evidence_report"]["report_id"],
                component_ids=component_ids,
                roles=roles,
                trust_boundary_ids=boundary_ids,
                checks=SUCCESS_CHECKS,
            )
        except _ManifestError as exc:
            return _failure(exc.code, exc.detail)
        except Exception:
            return _failure("internal_error", "internal verification failure")


def verify_node_role_composition_manifest_json(
    payload: str | bytes,
) -> NodeRoleCompositionManifestResult:
    """Verify one offline inert node-role composition manifest."""

    return NodeRoleCompositionManifestVerifier.verify_json(payload)
