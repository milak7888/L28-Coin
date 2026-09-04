# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


PROFILE = "l28-option-a-halt-on-conflict/v0.1"
POLICY_ID = "OPTION_A_HALT_ON_CONFLICT"
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

NETWORK_AUTHORIZED = False
SOCKET_AUTHORIZED = False
RUNTIME_AUTHORIZED = False
LEDGER_MUTATION_AUTHORIZED = False
CANONICAL_HEIGHT_OVERRIDE_AUTHORIZED = False
ISSUANCE_AUTHORITY = False
SUPPLY_AUTHORITY = False
VALIDATION_AUTHORITY = False
HISTORY_AUTHORITY = False
SETTLEMENT_AUTHORITY = False
AUTOMATIC_REORG_ALLOWED = False
CONFIRMATION_COUNT_DEFINED = False
MAX_REORG_DEPTH_DEFINED = False
FORK__WINNER_DEFINED = False


class OptionAPolicyError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class HistoryEntry:
    height: int
    block_id: str
    parent_id: str


@dataclass(frozen=True)
class CandidateHistory:
    source_id: str
    network_id: str
    genesis_hash: str
    entries: tuple[HistoryEntry, ...]
    evidence_only: bool = True
    canonical_authority: bool = False
    ledger_mutation_authority: bool = False


@dataclass(frozen=True)
class OptionAAssessment:
    code: str
    conflict: bool
    divergence_height: int | None
    local_length: int
    peer_length: int
    halt_sync: bool
    retain_current_local_canonical_state: bool
    candidate_apply_authorized: bool = False
    automatic_reorg_authorized: bool = False
    winner_selected: bool = False
    confirmation_claimed: bool = False
    canonical_height_override_authorized: bool = False
    ledger_mutation_authorized: bool = False
    issuance_authority: bool = False
    supply_authority: bool = False
    validation_authority: bool = False
    history_authority: bool = False
    settlement_authority: bool = False


@dataclass(frozen=True)
class OptionAPolicyState:
    status: str
    code: str
    halt_height: int | None = None
    canonical_state_changed: bool = False
    ledger_mutated: bool = False


@dataclass(frozen=True)
class ResumeDecision:
    allowed: bool
    code: str
    canonical_state_changed: bool = False


def _token(value: Any, code: str) -> str:
    if (
        not isinstance(value, str)
        or SAFE_TOKEN_RE.fullmatch(value) is None
    ):
        raise OptionAPolicyError(code)
    return value


def validate_history(history: Any) -> bool:
    if not isinstance(history, CandidateHistory):
        raise OptionAPolicyError("history_required")

    _token(history.source_id, "source_id_invalid")
    _token(history.network_id, "network_id_invalid")
    _token(history.genesis_hash, "genesis_hash_invalid")

    if history.evidence_only is not True:
        raise OptionAPolicyError("evidence_only_required")

    if (
        history.canonical_authority is not False
        or history.ledger_mutation_authority is not False
    ):
        raise OptionAPolicyError("candidate_authority_invalid")

    if not isinstance(history.entries, tuple) or not history.entries:
        raise OptionAPolicyError("required_history_state_missing")

    previous = None

    for index, entry in enumerate(history.entries):
        if not isinstance(entry, HistoryEntry):
            raise OptionAPolicyError("history_entry_invalid")

        if type(entry.height) is not int or entry.height != index:
            raise OptionAPolicyError("history_height_invalid")

        block_id = _token(entry.block_id, "block_id_invalid")
        parent_id = _token(entry.parent_id, "parent_id_invalid")

        if index == 0:
            if parent_id != "GENESIS":
                raise OptionAPolicyError("genesis_parent_invalid")
        else:
            if previous is None or parent_id != previous:
                raise OptionAPolicyError("history_link_invalid")

        previous = block_id

    return True


def assess_option_a(
    local_history: CandidateHistory,
    peer_history: CandidateHistory,
) -> OptionAAssessment:
    validate_history(local_history)
    validate_history(peer_history)

    if local_history.source_id != "LOCAL_CORE":
        raise OptionAPolicyError("local_core_history_required")

    if peer_history.source_id == "LOCAL_CORE":
        raise OptionAPolicyError("peer_history_required")

    if (
        local_history.network_id != peer_history.network_id
        or local_history.genesis_hash != peer_history.genesis_hash
    ):
        raise OptionAPolicyError("history_binding_mismatch")

    local = local_history.entries
    peer = peer_history.entries
    common = min(len(local), len(peer))

    divergence = None

    for index in range(common):
        if local[index].block_id != peer[index].block_id:
            divergence = index
            break

    if divergence is not None:
        return OptionAAssessment(
            code="HALT_SYNC_CONFLICT",
            conflict=True,
            divergence_height=divergence,
            local_length=len(local),
            peer_length=len(peer),
            halt_sync=True,
            retain_current_local_canonical_state=True,
        )

    if len(peer) < len(local):
        code = "STALE_NONAUTHORITATIVE_EVIDENCE"
    elif len(peer) == len(local):
        code = "NO_CONFLICT_EQUAL_HISTORY"
    else:
        code = "EXTENSION_EVIDENCE_ONLY"

    return OptionAAssessment(
        code=code,
        conflict=False,
        divergence_height=None,
        local_length=len(local),
        peer_length=len(peer),
        halt_sync=False,
        retain_current_local_canonical_state=True,
    )


def detect_equivocation(
    first: CandidateHistory,
    second: CandidateHistory,
) -> bool:
    return assess_peer_equivocation(first, second).conflict


def assess_peer_equivocation(
    first: CandidateHistory,
    second: CandidateHistory,
) -> OptionAAssessment:
    validate_history(first)
    validate_history(second)

    if first.source_id != second.source_id:
        raise OptionAPolicyError("same_peer_required")

    if (
        first.network_id != second.network_id
        or first.genesis_hash != second.genesis_hash
    ):
        raise OptionAPolicyError("history_binding_mismatch")

    common = min(len(first.entries), len(second.entries))

    for index in range(common):
        if (
            first.entries[index].block_id
            != second.entries[index].block_id
        ):
            return OptionAAssessment(
                code="HALT_SYNC_PEER_EQUIVOCATION",
                conflict=True,
                divergence_height=index,
                local_length=len(first.entries),
                peer_length=len(second.entries),
                halt_sync=True,
                retain_current_local_canonical_state=True,
            )

    return OptionAAssessment(
        code="NO_PEER_EQUIVOCATION",
        conflict=False,
        divergence_height=None,
        local_length=len(first.entries),
        peer_length=len(second.entries),
        halt_sync=False,
        retain_current_local_canonical_state=True,
    )


def _validate_policy_state(state: Any) -> OptionAPolicyState:
    if not isinstance(state, OptionAPolicyState):
        raise OptionAPolicyError("policy_state_required")

    if (
        state.canonical_state_changed is not False
        or state.ledger_mutated is not False
    ):
        raise OptionAPolicyError("policy_state_mutation_invalid")

    if (
        type(state.status) is not str
        or state.status not in {"SYNCING", "HALTED_CONFLICT"}
    ):
        raise OptionAPolicyError("policy_state_invalid")

    return state


def _validate_assessment(assessment: Any) -> OptionAAssessment:
    if not isinstance(assessment, OptionAAssessment):
        raise OptionAPolicyError("assessment_required")

    authority_fields = (
        assessment.candidate_apply_authorized,
        assessment.automatic_reorg_authorized,
        assessment.winner_selected,
        assessment.confirmation_claimed,
        assessment.canonical_height_override_authorized,
        assessment.ledger_mutation_authorized,
        assessment.issuance_authority,
        assessment.supply_authority,
        assessment.validation_authority,
        assessment.history_authority,
        assessment.settlement_authority,
    )

    if any(value is not False for value in authority_fields):
        raise OptionAPolicyError("assessment_authority_invalid")

    if assessment.retain_current_local_canonical_state is not True:
        raise OptionAPolicyError("assessment_retain_state_required")

    if (
        type(assessment.code) is not str
        or type(assessment.conflict) is not bool
        or type(assessment.halt_sync) is not bool
        or type(assessment.local_length) is not int
        or type(assessment.peer_length) is not int
        or assessment.local_length < 1
        or assessment.peer_length < 1
    ):
        raise OptionAPolicyError("assessment_invariant_invalid")

    if assessment.conflict:
        if (
            assessment.code not in {
                "HALT_SYNC_CONFLICT",
                "HALT_SYNC_PEER_EQUIVOCATION",
            }
            or assessment.halt_sync is not True
            or type(assessment.divergence_height) is not int
            or assessment.divergence_height < 0
            or assessment.divergence_height
            >= min(assessment.local_length, assessment.peer_length)
        ):
            raise OptionAPolicyError("assessment_invariant_invalid")
    elif (
        assessment.code not in {
            "NO_CONFLICT_EQUAL_HISTORY",
            "STALE_NONAUTHORITATIVE_EVIDENCE",
            "EXTENSION_EVIDENCE_ONLY",
            "NO_PEER_EQUIVOCATION",
        }
        or assessment.halt_sync is not False
        or assessment.divergence_height is not None
    ):
        raise OptionAPolicyError("assessment_invariant_invalid")

    return assessment


def transition_sync_state(
    state: OptionAPolicyState,
    assessment: OptionAAssessment,
) -> OptionAPolicyState:
    state = _validate_policy_state(state)
    assessment = _validate_assessment(assessment)

    if state.status == "HALTED_CONFLICT":
        return OptionAPolicyState(
            status="HALTED_CONFLICT",
            code="HALT_STICKY_GOVERNED_RESOLUTION_REQUIRED",
            halt_height=state.halt_height,
        )

    if assessment.conflict:
        return OptionAPolicyState(
            status="HALTED_CONFLICT",
            code="HALTED_BY_OPTION_A",
            halt_height=assessment.divergence_height,
        )

    return OptionAPolicyState(
        status="SYNCING",
        code="NO_CANONICAL_TRANSITION_AUTHORIZED",
    )


def request_resume(
    state: OptionAPolicyState,
) -> ResumeDecision:
    state = _validate_policy_state(state)

    if state.status == "HALTED_CONFLICT":
        return ResumeDecision(
            allowed=False,
            code="GOVERNED_DETERMINISTIC_RESOLUTION_RULE_REQUIRED",
        )

    if state.status == "SYNCING":
        return ResumeDecision(
            allowed=False,
            code="RESUME_NOT_APPLICABLE",
        )

    raise OptionAPolicyError("policy_state_invalid")
