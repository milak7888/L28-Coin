"""Inert in-memory lifecycle models for the public L28 node roles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Self


MODEL_VERSION = "l28-node-role-model/v0.1"
CORE_ROLE = "CoreL28Node"
P2P_ROLE = "L28P2PNode"

STABLE_CODES = (
    "transitioned",
    "state_invalid",
    "reserved_state_unreachable",
    "transition_not_allowed",
)

CORE_STATES = frozenset(
    {
        "CREATED",
        "EVIDENCE_ONLY",
        "DISPOSABLE_TEST_READY",
        "PAUSED",
        "STOPPED",
        "FAILED",
        "CANONICAL_READY_RESERVED",
        "RUNNING_RESERVED",
    }
)
CORE_RESERVED_STATES = frozenset(
    {
        "CANONICAL_READY_RESERVED",
        "RUNNING_RESERVED",
    }
)
CORE_ALLOWED_TRANSITIONS = frozenset(
    {
        ("CREATED", "EVIDENCE_ONLY"),
        ("CREATED", "DISPOSABLE_TEST_READY"),
        ("CREATED", "PAUSED"),
        ("EVIDENCE_ONLY", "PAUSED"),
        ("DISPOSABLE_TEST_READY", "PAUSED"),
        ("PAUSED", "STOPPED"),
        ("CREATED", "FAILED"),
        ("EVIDENCE_ONLY", "FAILED"),
        ("DISPOSABLE_TEST_READY", "FAILED"),
        ("PAUSED", "FAILED"),
        ("FAILED", "STOPPED"),
    }
)

P2P_STATES = frozenset(
    {
        "CREATED",
        "CONFIGURED",
        "PAUSED",
        "STOPPED",
        "FAILED",
        "LISTENING_RESERVED",
    }
)
P2P_RESERVED_STATES = frozenset({"LISTENING_RESERVED"})
P2P_ALLOWED_TRANSITIONS = frozenset(
    {
        ("CREATED", "CONFIGURED"),
        ("CREATED", "PAUSED"),
        ("CONFIGURED", "PAUSED"),
        ("PAUSED", "STOPPED"),
        ("CREATED", "FAILED"),
        ("CONFIGURED", "FAILED"),
        ("PAUSED", "FAILED"),
        ("FAILED", "STOPPED"),
    }
)


@dataclass(frozen=True)
class NodeRoleTransitionResult:
    ok: bool
    code: str
    role: str
    previous_state: str
    requested_state: str
    resulting_state: str
    model_version: str = MODEL_VERSION


def _transition_result(
    *,
    role: str,
    current_state: str,
    requested_state: object,
    states: frozenset[str],
    reserved_states: frozenset[str],
    allowed_transitions: frozenset[tuple[str, str]],
) -> NodeRoleTransitionResult:
    if not isinstance(requested_state, str) or not requested_state:
        return NodeRoleTransitionResult(
            False,
            "state_invalid",
            role,
            current_state,
            "",
            current_state,
        )
    if requested_state in reserved_states:
        return NodeRoleTransitionResult(
            False,
            "reserved_state_unreachable",
            role,
            current_state,
            requested_state,
            current_state,
        )
    if requested_state not in states:
        return NodeRoleTransitionResult(
            False,
            "state_invalid",
            role,
            current_state,
            requested_state,
            current_state,
        )
    if (current_state, requested_state) not in allowed_transitions:
        return NodeRoleTransitionResult(
            False,
            "transition_not_allowed",
            role,
            current_state,
            requested_state,
            current_state,
        )
    return NodeRoleTransitionResult(
        True,
        "transitioned",
        role,
        current_state,
        requested_state,
        requested_state,
    )


@dataclass(frozen=True)
class CoreNodeRoleModel:
    """Immutable, inert lifecycle model for the CoreL28Node role."""

    state: str = field(default="CREATED", init=False)
    role: ClassVar[str] = CORE_ROLE
    states: ClassVar[frozenset[str]] = CORE_STATES
    reserved_states: ClassVar[frozenset[str]] = CORE_RESERVED_STATES
    allowed_transitions: ClassVar[frozenset[tuple[str, str]]] = CORE_ALLOWED_TRANSITIONS

    @classmethod
    def _from_valid_state(cls, state: str) -> Self:
        if state not in cls.states or state in cls.reserved_states:
            raise ValueError("state must be known and non-reserved")
        instance = object.__new__(cls)
        object.__setattr__(instance, "state", state)
        return instance

    def transition(self, requested_state: object) -> tuple[Self, NodeRoleTransitionResult]:
        result = _transition_result(
            role=self.role,
            current_state=self.state,
            requested_state=requested_state,
            states=self.states,
            reserved_states=self.reserved_states,
            allowed_transitions=self.allowed_transitions,
        )
        if not result.ok:
            return self, result
        return self._from_valid_state(result.resulting_state), result


@dataclass(frozen=True)
class P2PNodeRoleModel:
    """Immutable, inert lifecycle model for the L28P2PNode role."""

    state: str = field(default="CREATED", init=False)
    role: ClassVar[str] = P2P_ROLE
    states: ClassVar[frozenset[str]] = P2P_STATES
    reserved_states: ClassVar[frozenset[str]] = P2P_RESERVED_STATES
    allowed_transitions: ClassVar[frozenset[tuple[str, str]]] = P2P_ALLOWED_TRANSITIONS

    @classmethod
    def _from_valid_state(cls, state: str) -> Self:
        if state not in cls.states or state in cls.reserved_states:
            raise ValueError("state must be known and non-reserved")
        instance = object.__new__(cls)
        object.__setattr__(instance, "state", state)
        return instance

    def transition(self, requested_state: object) -> tuple[Self, NodeRoleTransitionResult]:
        result = _transition_result(
            role=self.role,
            current_state=self.state,
            requested_state=requested_state,
            states=self.states,
            reserved_states=self.reserved_states,
            allowed_transitions=self.allowed_transitions,
        )
        if not result.ok:
            return self, result
        return self._from_valid_state(result.resulting_state), result
