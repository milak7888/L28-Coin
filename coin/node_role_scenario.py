"""Offline inert L28 node-role scenario execution.

This module converts an explicit sequence of requested states into a completed
Foundation 22 transcript by applying the immutable Foundation 21 role model.
It performs no filesystem, network, ledger, wallet, mining, signing, or
runtime-node operations.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Final

from .node_role_model import (
    MODEL_VERSION,
    CoreNodeRoleModel,
    P2PNodeRoleModel,
)
from .node_role_transcript import (
    CORE_ROLE,
    P2P_ROLE,
    TRANSCRIPT_VERSION,
    verify_transcript_json,
)


SCENARIO_VERSION: Final = "l28-node-role-scenario/v0.1"
RUNNER_VERSION: Final = "l28-node-role-scenario-runner/v0.1"
MAX_SCENARIO_BYTES: Final = 131_072
MAX_REQUESTS: Final = 256
MAX_STATE_TEXT_LENGTH: Final = 128
SUPPORTED_ROLES: Final = (CORE_ROLE, P2P_ROLE)

STABLE_CODES: Final = (
    "scenario_valid",
    "input_type_invalid",
    "scenario_too_large",
    "invalid_encoding",
    "invalid_json",
    "duplicate_key",
    "schema_error",
    "version_unsupported",
    "role_invalid",
    "request_count_invalid",
    "terminal_state_required",
    "transcript_verification_failed",
    "internal_error",
)

TOP_LEVEL_FIELDS: Final = frozenset(
    {
        "scenario_version",
        "model_version",
        "transcript_version",
        "role",
        "requested_states",
    }
)

SUCCESS_CHECKS: Final = (
    "identity",
    "schema",
    "request_bounds",
    "immutable_replay",
    "reserved_states",
    "terminal_state",
    "transcript_construction",
    "transcript_self_verification",
    "semantic_commitment",
)


class _DuplicateKey(ValueError):
    pass


class _ScenarioError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class NodeRoleScenarioStep:
    sequence: int
    previous_state: str
    requested_state: str
    resulting_state: str
    ok: bool
    code: str


@dataclass(frozen=True)
class NodeRoleScenarioResult:
    ok: bool
    code: str
    role: str
    final_state: str
    request_count: int
    scenario_sha256: str
    transcript_sha256: str
    transcript_verification_code: str
    transcript_json: str
    steps: tuple[NodeRoleScenarioStep, ...]
    checks: tuple[str, ...]
    detail: str = ""
    scenario_version: str = SCENARIO_VERSION
    model_version: str = MODEL_VERSION
    transcript_version: str = TRANSCRIPT_VERSION
    runner_version: str = RUNNER_VERSION


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(value)


def _decode_payload(payload: str | bytes) -> str:
    if isinstance(payload, bytes):
        if len(payload) > MAX_SCENARIO_BYTES:
            raise _ScenarioError("scenario_too_large")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _ScenarioError("invalid_encoding") from exc

    if isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _ScenarioError("invalid_encoding") from exc
        if len(encoded) > MAX_SCENARIO_BYTES:
            raise _ScenarioError("scenario_too_large")
        return payload

    raise _ScenarioError("input_type_invalid")


def _parse_json(payload: str | bytes) -> Any:
    text = _decode_payload(payload)
    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
        )
    except _DuplicateKey as exc:
        raise _ScenarioError("duplicate_key") from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise _ScenarioError("invalid_json") from exc


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise _ScenarioError("schema_error") from exc


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_exact_document(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _ScenarioError("schema_error")
    if frozenset(value) != TOP_LEVEL_FIELDS:
        raise _ScenarioError("schema_error")
    return value


def _require_text(value: Any) -> str:
    if not isinstance(value, str):
        raise _ScenarioError("schema_error")
    if not value or len(value) > MAX_STATE_TEXT_LENGTH:
        raise _ScenarioError("schema_error")
    return value


def _failure(
    *,
    code: str,
    role: str = "",
    final_state: str = "",
    request_count: int = 0,
    scenario_sha256: str = "",
    transcript_sha256: str = "",
    transcript_verification_code: str = "",
    transcript_json: str = "",
    steps: tuple[NodeRoleScenarioStep, ...] = (),
    detail: str = "",
) -> NodeRoleScenarioResult:
    return NodeRoleScenarioResult(
        ok=False,
        code=code,
        role=role,
        final_state=final_state,
        request_count=request_count,
        scenario_sha256=scenario_sha256,
        transcript_sha256=transcript_sha256,
        transcript_verification_code=transcript_verification_code,
        transcript_json=transcript_json,
        steps=steps,
        checks=(),
        detail=detail,
    )


class NodeRoleScenarioRunner:
    """Pure-data runner that produces a self-verified inert transcript."""

    @classmethod
    def run_json(cls, payload: str | bytes) -> NodeRoleScenarioResult:
        role = ""
        final_state = ""
        request_count = 0
        scenario_sha256 = ""
        transcript_sha256 = ""
        transcript_verification_code = ""
        transcript_json = ""
        steps: tuple[NodeRoleScenarioStep, ...] = ()

        try:
            value = _parse_json(payload)
            scenario_json = _canonical_json(value)
            scenario_sha256 = _sha256_text(scenario_json)
            document = _require_exact_document(value)

            if document["scenario_version"] != SCENARIO_VERSION:
                raise _ScenarioError("version_unsupported")
            if document["model_version"] != MODEL_VERSION:
                raise _ScenarioError("version_unsupported")
            if document["transcript_version"] != TRANSCRIPT_VERSION:
                raise _ScenarioError("version_unsupported")

            role = _require_text(document["role"])
            if role not in SUPPORTED_ROLES:
                raise _ScenarioError("role_invalid")

            requested_values = document["requested_states"]
            if not isinstance(requested_values, list):
                raise _ScenarioError("schema_error")

            request_count = len(requested_values)
            if request_count < 1 or request_count > MAX_REQUESTS:
                raise _ScenarioError("request_count_invalid")

            requested_states = tuple(
                _require_text(requested_state)
                for requested_state in requested_values
            )

            model: CoreNodeRoleModel | P2PNodeRoleModel
            if role == CORE_ROLE:
                model = CoreNodeRoleModel()
            else:
                model = P2PNodeRoleModel()

            generated_steps: list[NodeRoleScenarioStep] = []

            for sequence, requested_state in enumerate(requested_states):
                previous_state = model.state
                next_model, transition = model.transition(requested_state)

                step = NodeRoleScenarioStep(
                    sequence=sequence,
                    previous_state=previous_state,
                    requested_state=requested_state,
                    resulting_state=transition.resulting_state,
                    ok=transition.ok,
                    code=transition.code,
                )
                generated_steps.append(step)
                model = next_model

            steps = tuple(generated_steps)
            final_state = model.state

            transcript = {
                "transcript_version": TRANSCRIPT_VERSION,
                "model_version": MODEL_VERSION,
                "role": role,
                "initial_state": "CREATED",
                "transitions": [
                    {
                        "sequence": step.sequence,
                        "previous_state": step.previous_state,
                        "requested_state": step.requested_state,
                        "resulting_state": step.resulting_state,
                        "ok": step.ok,
                        "code": step.code,
                    }
                    for step in steps
                ],
                "final_state": final_state,
            }
            transcript_json = _canonical_json(transcript)

            transcript_result = verify_transcript_json(transcript_json)
            transcript_sha256 = transcript_result.transcript_sha256
            transcript_verification_code = transcript_result.code

            if final_state != "STOPPED":
                raise _ScenarioError("terminal_state_required")
            if not transcript_result.ok:
                raise _ScenarioError("transcript_verification_failed")

            return NodeRoleScenarioResult(
                ok=True,
                code="scenario_valid",
                role=role,
                final_state=final_state,
                request_count=request_count,
                scenario_sha256=scenario_sha256,
                transcript_sha256=transcript_sha256,
                transcript_verification_code=transcript_verification_code,
                transcript_json=transcript_json,
                steps=steps,
                checks=SUCCESS_CHECKS,
            )

        except _ScenarioError as exc:
            return _failure(
                code=exc.code,
                role=role,
                final_state=final_state,
                request_count=request_count,
                scenario_sha256=scenario_sha256,
                transcript_sha256=transcript_sha256,
                transcript_verification_code=transcript_verification_code,
                transcript_json=transcript_json,
                steps=steps,
                detail=exc.detail,
            )
        except Exception:
            return _failure(
                code="internal_error",
                role=role,
                final_state=final_state,
                request_count=request_count,
                scenario_sha256=scenario_sha256,
                transcript_sha256=transcript_sha256,
                transcript_verification_code=transcript_verification_code,
                transcript_json=transcript_json,
                steps=steps,
            )


def run_scenario_json(payload: str | bytes) -> NodeRoleScenarioResult:
    """Run one explicit inert scenario without discovering external state."""

    return NodeRoleScenarioRunner.run_json(payload)
