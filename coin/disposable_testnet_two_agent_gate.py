# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .disposable_testnet_m2 import DisposableLocalTipAuthority
from .disposable_testnet_p2p_conformance import (
    OFFLINE_CONFORMANCE_MAX_FRAME_BYTES,
    DisposableP2PConformanceError,
    assess_offline_frame,
    evaluate_peer_tip_evidence,
    nonce_replay_key,
    plan_single_writer_sync,
    prepare_p2p_conformance_boundary,
)
from .disposable_testnet_runtime_boundary import (
    DisposableRuntimeBinding,
    DisposableRuntimeBoundaryError,
    validate_runtime_binding,
)


PROFILE = "l28-isolated-two-agent-security-gate/v0.1"
READINESS = "READY_FOR_EXPLICIT_ISOLATED_TWO_AGENT_NETWORK_AUTHORIZATION"

LOOPBACK_HOST = "127.0.0.1"
AGENT_A = "agent-a"
AGENT_B = "agent-b"
WRITER_AGENT = AGENT_A

TEST_PORT_A = 28428
TEST_PORT_B = 28429

PRODUCTION_PEER_AUTHENTICATION_DEFINED = False
PRODUCTION_TRUSTED_TIME_DEFINED = False
PRODUCTION_RESOURCE_LIMITS_DEFINED = False
CONFIRMATION_POLICY_DEFINED = False
REORG_POLICY_DEFINED = False

NETWORK_AUTHORIZED = False
SOCKET_AUTHORIZED = False
LISTEN_AUTHORIZED = False
CONNECT_AUTHORIZED = False
PROCESS_START_AUTHORIZED = False
P2P_RUNTIME_AUTHORIZED = False
RPC_AUTHORIZED = False
LEDGER_MUTATION_AUTHORIZED = False
CANONICAL_HEIGHT_OVERRIDE_AUTHORIZED = False
WALLET_CREATION_AUTHORIZED = False
KEY_GENERATION_AUTHORIZED = False
SIGNING_AUTHORIZED = False
MINING_AUTHORIZED = False
BROADCAST_AUTHORIZED = False
REAL_VALUE_AUTHORIZED = False
HISTORICAL_STATE_IMPORT_AUTHORIZED = False
TESTNET_START_AUTHORIZED = False
SETTLEMENT_AUTHORIZED = False

STABLE_GATE_CODES = (
    "gate_valid",
    "topology_agent_count_invalid",
    "topology_agent_identity_invalid",
    "loopback_scope_invalid",
    "topology_port_invalid",
    "topology_port_collision",
    "writer_assignment_invalid",
    "resource_limit_invalid",
    "activation_authority_invalid",
    "fixture_identity_invalid",
    "session_agent_invalid",
    "session_direction_invalid",
    "reconnect_limit_exceeded",
    "session_message_limit_exceeded",
    "experiment_payload_too_large",
    "runtime_binding_invalid",
)


class TwoAgentSecurityGateError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class AgentEndpointSpec:
    agent_id: str
    host: str
    port: int
    role: str
    designated_single_writer: bool
    peer_evidence_only: bool
    runtime_write_authorized: bool = False
    canonical_height_override_authorized: bool = False
    issuance_authority: bool = False
    supply_authority: bool = False
    settlement_authority: bool = False


@dataclass(frozen=True)
class ExperimentResourceLimits:
    max_frame_bytes: int
    max_payload_bytes: int
    max_messages_per_session: int
    max_sessions: int
    max_reconnects: int
    production_limits: bool = False


@dataclass(frozen=True)
class TwoAgentExperimentPlan:
    profile: str
    readiness: str
    network_id: str
    genesis_hash: str
    config_hash: str
    writer_agent_id: str
    agents: tuple[AgentEndpointSpec, ...]
    limits: ExperimentResourceLimits
    max_agents: int = 2
    loopback_only: bool = True
    public_fixture_identity_only: bool = True
    production_peer_authentication_defined: bool = False
    trusted_production_time_defined: bool = False
    production_resource_limits_defined: bool = False
    network_authorized: bool = False
    socket_authorized: bool = False
    listen_authorized: bool = False
    connect_authorized: bool = False
    process_start_authorized: bool = False
    p2p_runtime_authorized: bool = False
    rpc_authorized: bool = False
    ledger_mutation_authorized: bool = False
    canonical_height_override_authorized: bool = False
    wallet_creation_authorized: bool = False
    key_generation_authorized: bool = False
    signing_authorized: bool = False
    mining_authorized: bool = False
    broadcast_authorized: bool = False
    real_value_authorized: bool = False
    historical_state_import_authorized: bool = False
    testnet_start_authorized: bool = False
    settlement_authorized: bool = False


@dataclass(frozen=True)
class OfflineSessionPlan:
    session_id: str
    initiator: str
    responder: str
    reconnect_index: int
    max_messages: int
    network_authorized: bool = False
    socket_authorized: bool = False
    execute_authorized: bool = False
    production_authentication: bool = False


@dataclass(frozen=True)
class OfflineTranscriptResult:
    ok: bool
    code: str
    session_id: str
    admitted_count: int
    rejected_index: int | None
    disconnect_planned: bool
    seen_message_ids: tuple[str, ...]
    seen_nonce_keys: tuple[str, ...]
    network_activity_performed: bool = False
    ledger_mutated: bool = False
    local_tip_changed: bool = False
    settlement_performed: bool = False


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise TwoAgentSecurityGateError(
            "gate_encoding_invalid"
        ) from exc


def _digest(domain: bytes, value: Any) -> str:
    return hashlib.sha256(
        domain + bytes([0]) + _canonical_bytes(value)
    ).hexdigest()


def _validate_runtime_context(
    binding: DisposableRuntimeBinding,
    tip: DisposableLocalTipAuthority,
) -> None:
    try:
        validate_runtime_binding(binding, tip)
    except DisposableRuntimeBoundaryError as exc:
        raise TwoAgentSecurityGateError(
            "runtime_binding_invalid:" + exc.code
        ) from exc


def build_fixture_identity_evidence(
    agent_id: str,
) -> dict[str, Any]:
    if agent_id not in {AGENT_A, AGENT_B}:
        raise TwoAgentSecurityGateError(
            "fixture_identity_invalid"
        )

    digest = _digest(
        b"L28-FOUNDATION142-PUBLIC-FIXTURE-IDENTITY-V0.1",
        {
            "agent_id": agent_id,
            "purpose": "isolated-two-agent-test-fixture",
        },
    )

    return {
        "kind": "foundation142_public_fixture_identity",
        "agent_id": agent_id,
        "public_fixture_digest": digest,
        "secret_based": False,
        "production_authentication": False,
    }


def validate_fixture_identity_evidence(
    value: Any,
    *,
    expected_agent_id: str,
) -> bool:
    if expected_agent_id not in {AGENT_A, AGENT_B}:
        raise TwoAgentSecurityGateError(
            "fixture_identity_invalid"
        )

    if not isinstance(value, Mapping):
        raise TwoAgentSecurityGateError(
            "fixture_identity_invalid"
        )

    expected_fields = {
        "kind",
        "agent_id",
        "public_fixture_digest",
        "secret_based",
        "production_authentication",
    }

    if set(value.keys()) != expected_fields:
        raise TwoAgentSecurityGateError(
            "fixture_identity_invalid"
        )

    expected = build_fixture_identity_evidence(
        expected_agent_id
    )

    if dict(value) != expected:
        raise TwoAgentSecurityGateError(
            "fixture_identity_invalid"
        )

    return True


def build_two_agent_experiment_plan(
    binding: DisposableRuntimeBinding,
    tip: DisposableLocalTipAuthority,
) -> TwoAgentExperimentPlan:
    _validate_runtime_context(binding, tip)

    try:
        p2p = prepare_p2p_conformance_boundary(
            binding,
            tip,
        )
    except DisposableP2PConformanceError as exc:
        raise TwoAgentSecurityGateError(
            "p2p_boundary_invalid:" + exc.code
        ) from exc

    if p2p["lifecycle_state"] != "CONFIGURED":
        raise TwoAgentSecurityGateError(
            "p2p_boundary_invalid"
        )

    agents = (
        AgentEndpointSpec(
            agent_id=AGENT_A,
            host=LOOPBACK_HOST,
            port=TEST_PORT_A,
            role="DESIGNATED_LOCAL_CORE_WRITER",
            designated_single_writer=True,
            peer_evidence_only=False,
        ),
        AgentEndpointSpec(
            agent_id=AGENT_B,
            host=LOOPBACK_HOST,
            port=TEST_PORT_B,
            role="PEER_EVIDENCE_ONLY",
            designated_single_writer=False,
            peer_evidence_only=True,
        ),
    )

    limits = ExperimentResourceLimits(
        max_frame_bytes=OFFLINE_CONFORMANCE_MAX_FRAME_BYTES,
        max_payload_bytes=2048,
        max_messages_per_session=32,
        max_sessions=2,
        max_reconnects=1,
    )

    plan = TwoAgentExperimentPlan(
        profile=PROFILE,
        readiness=READINESS,
        network_id=binding.network_id,
        genesis_hash=binding.genesis_hash,
        config_hash=binding.config_hash,
        writer_agent_id=WRITER_AGENT,
        agents=agents,
        limits=limits,
    )

    validate_two_agent_experiment_plan(
        plan,
        binding,
        tip,
    )

    return plan


def validate_two_agent_experiment_plan(
    plan: TwoAgentExperimentPlan,
    binding: DisposableRuntimeBinding,
    tip: DisposableLocalTipAuthority,
) -> bool:
    _validate_runtime_context(binding, tip)

    if not isinstance(plan, TwoAgentExperimentPlan):
        raise TwoAgentSecurityGateError(
            "topology_agent_count_invalid"
        )

    if plan.profile != PROFILE or plan.readiness != READINESS:
        raise TwoAgentSecurityGateError(
            "topology_agent_identity_invalid"
        )

    if (
        plan.network_id != binding.network_id
        or plan.genesis_hash != binding.genesis_hash
        or plan.config_hash != binding.config_hash
    ):
        raise TwoAgentSecurityGateError(
            "runtime_binding_invalid"
        )

    if plan.max_agents != 2 or len(plan.agents) != 2:
        raise TwoAgentSecurityGateError(
            "topology_agent_count_invalid"
        )

    ids = {agent.agent_id for agent in plan.agents}

    if ids != {AGENT_A, AGENT_B}:
        raise TwoAgentSecurityGateError(
            "topology_agent_identity_invalid"
        )

    ports: list[int] = []
    writers: list[str] = []

    for agent in plan.agents:
        if agent.host != LOOPBACK_HOST:
            raise TwoAgentSecurityGateError(
                "loopback_scope_invalid"
            )

        if (
            type(agent.port) is not int
            or agent.port < 1024
            or agent.port > 65535
        ):
            raise TwoAgentSecurityGateError(
                "topology_port_invalid"
            )

        ports.append(agent.port)

        if agent.designated_single_writer:
            writers.append(agent.agent_id)

        if (
            agent.runtime_write_authorized is not False
            or agent.canonical_height_override_authorized is not False
            or agent.issuance_authority is not False
            or agent.supply_authority is not False
            or agent.settlement_authority is not False
        ):
            raise TwoAgentSecurityGateError(
                "activation_authority_invalid"
            )

    if len(set(ports)) != len(ports):
        raise TwoAgentSecurityGateError(
            "topology_port_collision"
        )

    if writers != [WRITER_AGENT]:
        raise TwoAgentSecurityGateError(
            "writer_assignment_invalid"
        )

    by_id = {
        agent.agent_id: agent
        for agent in plan.agents
    }

    if by_id[AGENT_A].peer_evidence_only is not False:
        raise TwoAgentSecurityGateError(
            "writer_assignment_invalid"
        )

    if by_id[AGENT_B].peer_evidence_only is not True:
        raise TwoAgentSecurityGateError(
            "writer_assignment_invalid"
        )

    limits = plan.limits

    if (
        type(limits.max_frame_bytes) is not int
        or limits.max_frame_bytes <= 0
        or limits.max_frame_bytes > OFFLINE_CONFORMANCE_MAX_FRAME_BYTES
        or type(limits.max_payload_bytes) is not int
        or limits.max_payload_bytes <= 0
        or limits.max_payload_bytes > limits.max_frame_bytes
        or type(limits.max_messages_per_session) is not int
        or limits.max_messages_per_session <= 0
        or limits.max_messages_per_session > 64
        or limits.max_sessions != 2
        or limits.max_reconnects != 1
        or limits.production_limits is not False
    ):
        raise TwoAgentSecurityGateError(
            "resource_limit_invalid"
        )

    authority_values = (
        plan.network_authorized,
        plan.socket_authorized,
        plan.listen_authorized,
        plan.connect_authorized,
        plan.process_start_authorized,
        plan.p2p_runtime_authorized,
        plan.rpc_authorized,
        plan.ledger_mutation_authorized,
        plan.canonical_height_override_authorized,
        plan.wallet_creation_authorized,
        plan.key_generation_authorized,
        plan.signing_authorized,
        plan.mining_authorized,
        plan.broadcast_authorized,
        plan.real_value_authorized,
        plan.historical_state_import_authorized,
        plan.testnet_start_authorized,
        plan.settlement_authorized,
    )

    if any(value is not False for value in authority_values):
        raise TwoAgentSecurityGateError(
            "activation_authority_invalid"
        )

    if (
        plan.loopback_only is not True
        or plan.public_fixture_identity_only is not True
        or plan.production_peer_authentication_defined is not False
        or plan.trusted_production_time_defined is not False
        or plan.production_resource_limits_defined is not False
    ):
        raise TwoAgentSecurityGateError(
            "activation_authority_invalid"
        )

    return True


def plan_offline_session(
    plan: TwoAgentExperimentPlan,
    binding: DisposableRuntimeBinding,
    tip: DisposableLocalTipAuthority,
    *,
    initiator: str,
    responder: str,
    reconnect_index: Any = 0,
) -> OfflineSessionPlan:
    validate_two_agent_experiment_plan(
        plan,
        binding,
        tip,
    )

    ids = {agent.agent_id for agent in plan.agents}

    if initiator not in ids or responder not in ids:
        raise TwoAgentSecurityGateError(
            "session_agent_invalid"
        )

    if initiator == responder:
        raise TwoAgentSecurityGateError(
            "session_direction_invalid"
        )

    if (
        type(reconnect_index) is not int
        or reconnect_index < 0
        or reconnect_index > plan.limits.max_reconnects
    ):
        raise TwoAgentSecurityGateError(
            "reconnect_limit_exceeded"
        )

    session_id = _digest(
        b"L28-FOUNDATION142-OFFLINE-SESSION-V0.1",
        {
            "network_id": plan.network_id,
            "genesis_hash": plan.genesis_hash,
            "config_hash": plan.config_hash,
            "initiator": initiator,
            "responder": responder,
            "reconnect_index": reconnect_index,
        },
    )

    return OfflineSessionPlan(
        session_id=session_id,
        initiator=initiator,
        responder=responder,
        reconnect_index=reconnect_index,
        max_messages=plan.limits.max_messages_per_session,
    )


def validate_offline_session_plan(
    session: OfflineSessionPlan,
    plan: TwoAgentExperimentPlan,
) -> bool:
    if not isinstance(session, OfflineSessionPlan):
        raise TwoAgentSecurityGateError(
            "session_agent_invalid"
        )

    ids = {agent.agent_id for agent in plan.agents}

    if (
        session.initiator not in ids
        or session.responder not in ids
    ):
        raise TwoAgentSecurityGateError(
            "session_agent_invalid"
        )

    if session.initiator == session.responder:
        raise TwoAgentSecurityGateError(
            "session_direction_invalid"
        )

    if (
        session.reconnect_index < 0
        or session.reconnect_index > plan.limits.max_reconnects
    ):
        raise TwoAgentSecurityGateError(
            "reconnect_limit_exceeded"
        )

    if (
        session.network_authorized is not False
        or session.socket_authorized is not False
        or session.execute_authorized is not False
        or session.production_authentication is not False
    ):
        raise TwoAgentSecurityGateError(
            "activation_authority_invalid"
        )

    return True


def plan_experiment_lifecycle(
    plan: TwoAgentExperimentPlan,
) -> dict[str, Any]:
    return {
        "profile": "l28-foundation142-lifecycle-plan/v0.1",
        "preauthorization_sequence": [
            "VERIFY_RUNTIME_BINDING",
            "VERIFY_LOOPBACK_SCOPE",
            "VERIFY_PUBLIC_FIXTURE_IDENTITIES",
            "VERIFY_EXPERIMENT_LIMITS",
            "VERIFY_REPLAY_POLICY",
            "READY_FOR_EXPLICIT_AUTHORIZATION",
        ],
        "future_authorized_startup_order": [
            AGENT_A,
            AGENT_B,
        ],
        "future_authorized_shutdown_order": [
            AGENT_B,
            AGENT_A,
        ],
        "reset_after_shutdown_required": True,
        "reset_scope": "DISPOSABLE_TEST_STATE_ONLY",
        "execute_authorized": False,
        "process_start_authorized": False,
        "network_authorized": False,
        "socket_authorized": False,
        "testnet_start_authorized": False,
    }


def plan_propagation_trial(
    plan: TwoAgentExperimentPlan,
) -> dict[str, Any]:
    return {
        "profile": "l28-foundation142-propagation-trial-plan/v0.1",
        "scenarios": [
            "HELLO_BIDIRECTIONAL",
            "TIP_EVIDENCE_PEER_TO_WRITER",
            "CANDIDATE_EVIDENCE_PEER_TO_WRITER",
            "WRONG_NETWORK_ABORT",
            "WRONG_GENESIS_ABORT",
            "WRONG_CONFIG_ABORT",
            "OVERSIZED_FRAME_ABORT",
            "MESSAGE_REPLAY_ABORT",
            "NONCE_REPLAY_ACROSS_RECONNECT_ABORT",
            "STALE_RUNTIME_BINDING_ABORT",
            "DISCONNECT_RECONNECT_WITH_REPLAY_STATE",
        ],
        "success_criteria": [
            "ONLY_BOUND_FRAMES_ADMITTED",
            "NO_TRANSPORT_LEDGER_MUTATION",
            "NO_PEER_CANONICAL_HEIGHT_OVERRIDE",
            "NO_ISSUANCE_OR_SUPPLY_AUTHORITY",
            "NO_REAL_VALUE_STATE",
            "BOUNDED_SESSION_COUNTS",
            "CLEAN_SHUTDOWN_AND_RESET_REQUIRED",
        ],
        "abort_on_first_security_failure": True,
        "propagation_execution_authorized": False,
        "network_authorized": False,
        "confirmation_policy_defined": False,
        "reorg_policy_defined": False,
    }


def evaluate_offline_transcript(
    session: OfflineSessionPlan,
    plan: TwoAgentExperimentPlan,
    binding: DisposableRuntimeBinding,
    tip: DisposableLocalTipAuthority,
    frames: Any,
    *,
    now_ts: Any,
    prior_seen_message_ids: frozenset[str] | set[str] = frozenset(),
    prior_seen_nonce_keys: frozenset[str] | set[str] = frozenset(),
) -> OfflineTranscriptResult:
    validate_two_agent_experiment_plan(
        plan,
        binding,
        tip,
    )
    validate_offline_session_plan(
        session,
        plan,
    )

    if not isinstance(frames, (list, tuple)):
        raise TwoAgentSecurityGateError(
            "session_message_limit_exceeded"
        )

    if len(frames) > session.max_messages:
        return OfflineTranscriptResult(
            ok=False,
            code="session_message_limit_exceeded",
            session_id=session.session_id,
            admitted_count=0,
            rejected_index=0,
            disconnect_planned=True,
            seen_message_ids=tuple(
                sorted(prior_seen_message_ids)
            ),
            seen_nonce_keys=tuple(
                sorted(prior_seen_nonce_keys)
            ),
        )

    seen_messages = set(prior_seen_message_ids)
    seen_nonces = set(prior_seen_nonce_keys)
    admitted = 0

    for index, frame in enumerate(frames):
        result = assess_offline_frame(
            frame,
            binding,
            tip,
            now_ts=now_ts,
            seen_message_ids=seen_messages,
            seen_nonce_keys=seen_nonces,
        )

        if not result.ok:
            return OfflineTranscriptResult(
                ok=False,
                code=result.code,
                session_id=session.session_id,
                admitted_count=admitted,
                rejected_index=index,
                disconnect_planned=True,
                seen_message_ids=tuple(
                    sorted(seen_messages)
                ),
                seen_nonce_keys=tuple(
                    sorted(seen_nonces)
                ),
            )

        normalized = result.normalized_frame

        if normalized is None:
            raise TwoAgentSecurityGateError(
                "runtime_binding_invalid"
            )

        if (
            type(normalized["payload_length"]) is not int
            or normalized["payload_length"]
            > plan.limits.max_payload_bytes
        ):
            return OfflineTranscriptResult(
                ok=False,
                code="experiment_payload_too_large",
                session_id=session.session_id,
                admitted_count=admitted,
                rejected_index=index,
                disconnect_planned=True,
                seen_message_ids=tuple(
                    sorted(seen_messages)
                ),
                seen_nonce_keys=tuple(
                    sorted(seen_nonces)
                ),
            )

        seen_messages.add(
            normalized["message_id"]
        )
        seen_nonces.add(
            nonce_replay_key(normalized)
        )
        admitted += 1

    return OfflineTranscriptResult(
        ok=True,
        code="offline_transcript_admitted",
        session_id=session.session_id,
        admitted_count=admitted,
        rejected_index=None,
        disconnect_planned=False,
        seen_message_ids=tuple(sorted(seen_messages)),
        seen_nonce_keys=tuple(sorted(seen_nonces)),
    )


def evaluate_peer_tip_for_experiment(
    plan: TwoAgentExperimentPlan,
    binding: DisposableRuntimeBinding,
    tip: DisposableLocalTipAuthority,
    *,
    peer_height: Any,
) -> dict[str, Any]:
    validate_two_agent_experiment_plan(
        plan,
        binding,
        tip,
    )

    try:
        assessment = evaluate_peer_tip_evidence(
            binding,
            tip,
            peer_height=peer_height,
        )
        sync = plan_single_writer_sync(
            assessment
        )
    except DisposableP2PConformanceError as exc:
        raise TwoAgentSecurityGateError(
            "peer_tip_invalid:" + exc.code
        ) from exc

    return {
        "relation": assessment.relation,
        "local_height": assessment.local_height,
        "peer_height": assessment.peer_height,
        "sync_action": sync["action"],
        "request_start": sync["request_start"],
        "request_end": sync["request_end"],
        "single_writer": sync["single_writer"],
        "peer_tip_authoritative": False,
        "peer_can_mutate_local_tip": False,
        "peer_can_override_canonical_height": False,
        "automatic_apply": False,
        "ledger_mutation_authorized": False,
        "confirmation_policy_defined": False,
        "reorg_policy_defined": False,
    }


def build_authorization_readiness_report(
    plan: TwoAgentExperimentPlan,
    binding: DisposableRuntimeBinding,
    tip: DisposableLocalTipAuthority,
) -> dict[str, Any]:
    validate_two_agent_experiment_plan(
        plan,
        binding,
        tip,
    )

    return {
        "profile": PROFILE,
        "readiness": READINESS,
        "two_agents_exact": True,
        "loopback_scope_defined": True,
        "public_fixture_identity_binding_defined": True,
        "deterministic_experiment_limits_defined": True,
        "session_and_replay_rules_defined": True,
        "startup_shutdown_reset_plan_defined": True,
        "propagation_success_abort_criteria_defined": True,
        "single_writer_core_only": True,
        "peer_evidence_only": True,
        "production_peer_authentication_defined": False,
        "trusted_production_time_defined": False,
        "production_resource_limits_defined": False,
        "confirmation_policy_defined": False,
        "reorg_policy_defined": False,
        "separate_explicit_operator_authorization_required": True,
        "network_authorized": False,
        "socket_authorized": False,
        "p2p_runtime_authorized": False,
        "testnet_start_authorized": False,
        "settlement_authorized": False,
    }
