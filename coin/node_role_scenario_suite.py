"""Offline, inert scenario-suite verification for public L28 node roles.

This module accepts only caller-supplied JSON data.  It performs no file,
network, ledger, wallet, mining, or runtime-node operations.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

try:
    from .node_role_model import (
        CORE_ALLOWED_TRANSITIONS,
        CORE_RESERVED_STATES,
        CORE_ROLE,
        MODEL_VERSION,
        P2P_ALLOWED_TRANSITIONS,
        P2P_RESERVED_STATES,
        P2P_ROLE,
    )
    from .node_role_scenario import (
        SCENARIO_VERSION,
        NodeRoleScenarioRunner,
    )
    from .node_role_transcript import TRANSCRIPT_VERSION
except ImportError:  # pragma: no cover - direct module execution compatibility
    from node_role_model import (
        CORE_ALLOWED_TRANSITIONS,
        CORE_RESERVED_STATES,
        CORE_ROLE,
        MODEL_VERSION,
        P2P_ALLOWED_TRANSITIONS,
        P2P_RESERVED_STATES,
        P2P_ROLE,
    )
    from node_role_scenario import SCENARIO_VERSION, NodeRoleScenarioRunner
    from node_role_transcript import TRANSCRIPT_VERSION


SUITE_VERSION = "l28-node-role-scenario-suite/v0.1"
VERIFIER_VERSION = "l28-node-role-scenario-suite-verifier/v0.1"
MAX_SUITE_BYTES = 1_048_576
MAX_CASES = 64
MAX_CASE_ID_LENGTH = 64
SUPPORTED_ROLES = (CORE_ROLE, P2P_ROLE)
TOP_LEVEL_FIELDS = frozenset(
    {
        "suite_version",
        "scenario_version",
        "model_version",
        "transcript_version",
        "cases",
    }
)
CASE_FIELDS = frozenset({"case_id", "scenario"})
CASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
STABLE_CODES = (
    "suite_valid",
    "input_type_invalid",
    "suite_too_large",
    "invalid_encoding",
    "invalid_json",
    "duplicate_key",
    "schema_error",
    "version_unsupported",
    "case_count_invalid",
    "case_id_invalid",
    "duplicate_case_id",
    "scenario_failed",
    "role_coverage_incomplete",
    "transition_coverage_incomplete",
    "reserved_coverage_incomplete",
    "internal_error",
)
SUCCESS_CHECKS = (
    "identity",
    "schema",
    "case_bounds",
    "case_identity",
    "scenario_execution",
    "transcript_self_verification",
    "role_coverage",
    "transition_coverage",
    "reserved_state_coverage",
    "semantic_commitment",
)


class _DuplicateKey(ValueError):
    pass


class _SuiteError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class NodeRoleScenarioCaseResult:
    case_id: str
    ok: bool
    code: str
    role: str
    final_state: str
    request_count: int
    scenario_sha256: str
    transcript_sha256: str
    covered_transitions: tuple[str, ...]
    reserved_rejections: tuple[str, ...]


@dataclass(frozen=True)
class NodeRoleScenarioSuiteResult:
    ok: bool
    code: str
    case_count: int
    roles: tuple[str, ...]
    suite_sha256: str
    core_covered_transitions: tuple[str, ...]
    core_missing_transitions: tuple[str, ...]
    p2p_covered_transitions: tuple[str, ...]
    p2p_missing_transitions: tuple[str, ...]
    core_reserved_rejections: tuple[str, ...]
    core_missing_reserved_rejections: tuple[str, ...]
    p2p_reserved_rejections: tuple[str, ...]
    p2p_missing_reserved_rejections: tuple[str, ...]
    cases: tuple[NodeRoleScenarioCaseResult, ...]
    checks: tuple[str, ...]
    detail: str = ""
    suite_version: str = SUITE_VERSION
    scenario_version: str = SCENARIO_VERSION
    model_version: str = MODEL_VERSION
    transcript_version: str = TRANSCRIPT_VERSION
    verifier_version: str = VERIFIER_VERSION


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise ValueError("non-finite number")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _transition_name(previous_state: str, requested_state: str) -> str:
    return f"{previous_state}->{requested_state}"


def _transition_names(transitions: frozenset[tuple[str, str]]) -> frozenset[str]:
    return frozenset(_transition_name(previous, requested) for previous, requested in transitions)


CORE_REQUIRED_TRANSITIONS = _transition_names(CORE_ALLOWED_TRANSITIONS)
P2P_REQUIRED_TRANSITIONS = _transition_names(P2P_ALLOWED_TRANSITIONS)


def _result(
    *,
    ok: bool,
    code: str,
    detail: str = "",
    suite_sha256: str = "",
    cases: tuple[NodeRoleScenarioCaseResult, ...] = (),
    roles: tuple[str, ...] = (),
    core_covered: frozenset[str] = frozenset(),
    p2p_covered: frozenset[str] = frozenset(),
    core_reserved: frozenset[str] = frozenset(),
    p2p_reserved: frozenset[str] = frozenset(),
    checks: tuple[str, ...] = (),
) -> NodeRoleScenarioSuiteResult:
    return NodeRoleScenarioSuiteResult(
        ok=ok,
        code=code,
        case_count=len(cases),
        roles=roles,
        suite_sha256=suite_sha256,
        core_covered_transitions=tuple(sorted(core_covered)),
        core_missing_transitions=tuple(sorted(CORE_REQUIRED_TRANSITIONS - core_covered)),
        p2p_covered_transitions=tuple(sorted(p2p_covered)),
        p2p_missing_transitions=tuple(sorted(P2P_REQUIRED_TRANSITIONS - p2p_covered)),
        core_reserved_rejections=tuple(sorted(core_reserved)),
        core_missing_reserved_rejections=tuple(sorted(CORE_RESERVED_STATES - core_reserved)),
        p2p_reserved_rejections=tuple(sorted(p2p_reserved)),
        p2p_missing_reserved_rejections=tuple(sorted(P2P_RESERVED_STATES - p2p_reserved)),
        cases=cases,
        checks=checks,
        detail=detail,
    )


def _decode(payload: str | bytes) -> tuple[bytes, str]:
    if isinstance(payload, str):
        try:
            raw = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _SuiteError("invalid_encoding", "input_not_utf8") from exc
        text = payload
    elif isinstance(payload, bytes):
        raw = payload
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _SuiteError("invalid_encoding", "input_not_utf8") from exc
    else:
        raise _SuiteError("input_type_invalid", "input_must_be_text_or_bytes")

    if len(raw) > MAX_SUITE_BYTES:
        raise _SuiteError("suite_too_large", "input_exceeds_maximum")
    return raw, text


def _parse(payload: str | bytes) -> dict[str, Any]:
    _, text = _decode(payload)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise _SuiteError("duplicate_key", "duplicate_object_key") from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise _SuiteError("invalid_json", "input_not_valid_json") from exc

    if type(value) is not dict:
        raise _SuiteError("schema_error", "top_level_must_be_object")
    return value


def _validate_top_level(value: dict[str, Any]) -> list[Any]:
    if frozenset(value) != TOP_LEVEL_FIELDS:
        raise _SuiteError("schema_error", "top_level_fields_invalid")

    versions = (
        ("suite_version", SUITE_VERSION),
        ("scenario_version", SCENARIO_VERSION),
        ("model_version", MODEL_VERSION),
        ("transcript_version", TRANSCRIPT_VERSION),
    )
    for field_name, expected in versions:
        if type(value[field_name]) is not str:
            raise _SuiteError("schema_error", "version_field_type_invalid")
        if value[field_name] != expected:
            raise _SuiteError("version_unsupported", "version_value_unsupported")

    cases = value["cases"]
    if type(cases) is not list:
        raise _SuiteError("schema_error", "cases_must_be_array")
    if not 1 <= len(cases) <= MAX_CASES:
        raise _SuiteError("case_count_invalid", "case_count_out_of_bounds")
    return cases


def _validate_case(value: Any, seen_ids: set[str]) -> tuple[str, dict[str, Any]]:
    if type(value) is not dict or frozenset(value) != CASE_FIELDS:
        raise _SuiteError("schema_error", "case_fields_invalid")

    case_id = value["case_id"]
    if (
        type(case_id) is not str
        or not case_id
        or len(case_id) > MAX_CASE_ID_LENGTH
        or CASE_ID_RE.fullmatch(case_id) is None
    ):
        raise _SuiteError("case_id_invalid", "case_identifier_invalid")
    if case_id in seen_ids:
        raise _SuiteError("duplicate_case_id", "case_identifier_duplicate")
    seen_ids.add(case_id)

    scenario = value["scenario"]
    if type(scenario) is not dict:
        raise _SuiteError("schema_error", "scenario_must_be_object")
    return case_id, scenario


def _run_case(case_id: str, scenario: dict[str, Any]) -> NodeRoleScenarioCaseResult:
    scenario_bytes = _canonical_bytes(scenario)
    expected_sha256 = hashlib.sha256(scenario_bytes).hexdigest()
    scenario_result = NodeRoleScenarioRunner.run_json(scenario_bytes)

    if (
        not scenario_result.ok
        or scenario_result.code != "scenario_valid"
        or scenario_result.final_state != "STOPPED"
        or scenario_result.scenario_sha256 != expected_sha256
        or scenario_result.transcript_verification_code != "transcript_valid"
    ):
        raise _SuiteError("scenario_failed", "scenario_case_failed")

    role = scenario_result.role
    if role not in SUPPORTED_ROLES or scenario.get("role") != role:
        raise _SuiteError("scenario_failed", "scenario_role_mismatch")

    reserved_states = CORE_RESERVED_STATES if role == CORE_ROLE else P2P_RESERVED_STATES
    covered: set[str] = set()
    reserved: set[str] = set()

    for step in scenario_result.steps:
        if step.ok and step.code == "transitioned":
            covered.add(_transition_name(step.previous_state, step.requested_state))
        elif (
            not step.ok
            and step.code == "reserved_state_unreachable"
            and step.requested_state in reserved_states
            and step.resulting_state == step.previous_state
        ):
            reserved.add(step.requested_state)

    return NodeRoleScenarioCaseResult(
        case_id=case_id,
        ok=True,
        code="scenario_valid",
        role=role,
        final_state=scenario_result.final_state,
        request_count=scenario_result.request_count,
        scenario_sha256=scenario_result.scenario_sha256,
        transcript_sha256=scenario_result.transcript_sha256,
        covered_transitions=tuple(sorted(covered)),
        reserved_rejections=tuple(sorted(reserved)),
    )


class NodeRoleScenarioSuiteVerifier:
    @classmethod
    def verify_json(cls, payload: str | bytes) -> NodeRoleScenarioSuiteResult:
        del cls
        try:
            value = _parse(payload)
            raw_cases = _validate_top_level(value)
            suite_sha256 = hashlib.sha256(_canonical_bytes(value)).hexdigest()

            seen_ids: set[str] = set()
            case_results: list[NodeRoleScenarioCaseResult] = []
            roles_seen: set[str] = set()
            core_covered: set[str] = set()
            p2p_covered: set[str] = set()
            core_reserved: set[str] = set()
            p2p_reserved: set[str] = set()

            for raw_case in raw_cases:
                case_id, scenario = _validate_case(raw_case, seen_ids)
                case_result = _run_case(case_id, scenario)
                case_results.append(case_result)
                roles_seen.add(case_result.role)

                if case_result.role == CORE_ROLE:
                    core_covered.update(case_result.covered_transitions)
                    core_reserved.update(case_result.reserved_rejections)
                else:
                    p2p_covered.update(case_result.covered_transitions)
                    p2p_reserved.update(case_result.reserved_rejections)

            frozen_cases = tuple(case_results)
            roles = tuple(role for role in SUPPORTED_ROLES if role in roles_seen)
            frozen_core_covered = frozenset(core_covered)
            frozen_p2p_covered = frozenset(p2p_covered)
            frozen_core_reserved = frozenset(core_reserved)
            frozen_p2p_reserved = frozenset(p2p_reserved)

            common = dict(
                suite_sha256=suite_sha256,
                cases=frozen_cases,
                roles=roles,
                core_covered=frozen_core_covered,
                p2p_covered=frozen_p2p_covered,
                core_reserved=frozen_core_reserved,
                p2p_reserved=frozen_p2p_reserved,
            )

            if roles_seen != set(SUPPORTED_ROLES):
                return _result(
                    ok=False,
                    code="role_coverage_incomplete",
                    detail="both_roles_required",
                    **common,
                )

            if (
                frozen_core_covered != CORE_REQUIRED_TRANSITIONS
                or frozen_p2p_covered != P2P_REQUIRED_TRANSITIONS
            ):
                return _result(
                    ok=False,
                    code="transition_coverage_incomplete",
                    detail="allowed_transition_coverage_incomplete",
                    **common,
                )

            if (
                frozen_core_reserved != CORE_RESERVED_STATES
                or frozen_p2p_reserved != P2P_RESERVED_STATES
            ):
                return _result(
                    ok=False,
                    code="reserved_coverage_incomplete",
                    detail="reserved_rejection_coverage_incomplete",
                    **common,
                )

            return _result(
                ok=True,
                code="suite_valid",
                checks=SUCCESS_CHECKS,
                **common,
            )

        except _SuiteError as exc:
            return _result(ok=False, code=exc.code, detail=exc.detail)
        except Exception:
            return _result(ok=False, code="internal_error", detail="internal_failure")


def verify_scenario_suite_json(payload: str | bytes) -> NodeRoleScenarioSuiteResult:
    return NodeRoleScenarioSuiteVerifier.verify_json(payload)
