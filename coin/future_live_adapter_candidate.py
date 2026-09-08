# SPDX-License-Identifier: Apache-2.0
"""Non-activating candidate for future live-adapter implementation review."""


LIFECYCLE_PHASES = (
    "PROCESS_OBJECT_CONSTRUCTION",
    "PROCESS_START_SUPERVISION",
    "CHILD_BOOTSTRAP_WINDOW",
    "ACTIVE_EXECUTION",
    "CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL",
    "RELEASED",
)
DEADLINE_COVERAGE = (
    "RESOURCE_CONSTRUCTION",
    "STARTUP_SUPERVISION",
    "CHILD_BOOTSTRAP",
    "ACTIVE_WORK",
    "CLEANUP_INITIATION",
)
DEADLINE_DESCRIPTOR = (
    "SINGLE_BOUNDED_DEADLINE_DATA_ONLY",
    DEADLINE_COVERAGE,
    ("bounded", True),
    ("timer_implemented", False),
)

F163_READY_STATUS = "READY_FOR_FUTURE_LIVE_ADAPTER_IMPLEMENTATION_REVIEW"
F163_PROFILE = "l28-foundation163-live-adapter-implementation-readiness-gate/v0.1"
F163_BASELINE = "1e5266bca2c5c7263a9d067e8d5da58b59d8f338"
PREPARED_STATE = "PREPARED_NON_ACTIVATING_LIVE_ADAPTER_CANDIDATE"
UNPREPARED_STATE = "NOT_PREPARED"

NEW_AUTHORIZATION_REQUIRED = True
SEPARATE_SECURITY_REVIEW_REQUIRED = True
SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED = True
F159_RETRY_FORBIDDEN = True
OLD_AUTHORIZATION_REUSABLE = False
F161_EXECUTION_AUTHORIZED = False
F162_EXECUTION_AUTHORIZED = False
F163_EXECUTION_AUTHORIZED = False
F164_EXECUTION_AUTHORIZED = False
EXECUTION_AUTHORIZED = False

REQUIRED_F163_AUTHORITY = {
    "NEW_AUTHORIZATION_REQUIRED": True,
    "SEPARATE_SECURITY_REVIEW_REQUIRED": True,
    "SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED": True,
    "F159_RETRY_FORBIDDEN": True,
    "F157_F158_F159_CONSUMPTION_STATE_REUSABLE": False,
    "F161_EXECUTION_AUTHORIZED": False,
    "F162_EXECUTION_AUTHORIZED": False,
    "F163_EXECUTION_AUTHORIZED": False,
}
REQUIRED_F163_DIMENSIONS = (
    "A_RESOURCE_PROVENANCE",
    "B_PARENT_OWNERSHIP",
    "C_LIFECYCLE_ORDERING",
    "D_STARTUP_PRECONDITIONS",
    "E_BOOTSTRAP_RETENTION",
    "F_DEADLINE_COVERAGE",
    "G_FAILURE_PROPAGATION",
    "H_CLEANUP_TERMINALIZATION",
    "I_AUTHORIZATION_SEPARATION",
    "J_PROTOCOL_AUTHORITY_FIREWALL",
    "K_CAPABILITY_FIREWALL",
    "L_HISTORICAL_PRESERVATION",
    "M_LIVE_IMPLEMENTATION_REVIEW_READINESS",
)
REQUIRED_F163_OFFLINE_BOUNDARY = {
    "NO_EXECUTION_OCCURRED": True,
    "PROCESSES_STARTED": False,
    "THREADS_STARTED": False,
    "SOCKETS_OPENED": False,
    "NETWORK_TRAFFIC_USED": False,
    "AUTHORIZATION_GRANTED": False,
    "AUTHORIZATION_CONSUMED": False,
}
REQUIRED_PROTECTED_AUTHORITY = {
    "issuance": False,
    "supply": False,
    "height": False,
    "validation": False,
    "consensus": False,
    "history": False,
    "ledger": False,
    "settlement": False,
    "signing": False,
    "wallet": False,
    "bitcoin_authority": False,
}
REQUIRED_F163_PROTECTED_INVARIANTS = {
    "protocol_version": "1.0.0",
    "protocol_sha256": (
        "eabd5f2a11916781e6a047e5b2c2188fe4e0f1eae2fdcdc2f68e4c19193c397d"
    ),
    "canonical_validator": "coin.tx_validation.validate_transaction",
    "tx_validation_sha256": (
        "ac36bd95c932733a60ffc3acbb10b8a9f57e09c9533d0b64ff83affa876f3004"
    ),
    "economics_history_genesis_supply_snapshot_or_allocation_changed": False,
    "ledger_height_signer_or_bitcoin_boundary_changed": False,
}
REQUIRED_F163_SOURCE_BINDINGS = {
    "f158_helper": (
        "tests/foundation158_corrected_one_shot_execution_helper.py",
        "56d3a8b796ff245cf29124886c0da64b3ab605a640fc45d14a0a26e20ea8e9b6",
    ),
    "f158_consumption_marker": (
        "docs/l28_foundation158_corrected_one_shot_execution_state_v1.0.json",
        "1a9343a8ca2835c9125c2f80c6a3a91275bd6d498a27ee0039d603417b666605",
    ),
    "f160_model": (
        "tests/foundation160_spawn_bootstrap_lifetime_model.py",
        "89c27177420a7fe4a6f8016498e2b44e923e75106013670fa724bf0186d31b2c",
    ),
    "f160_gate": (
        "docs/l28_foundation160_spawn_bootstrap_lifetime_gate_v0.1.json",
        "408fe4264253a2940b93a051cdace49fda325019c8178def003ff695632e23d5",
    ),
    "f161_helper": (
        "tests/foundation161_future_runtime_lifecycle_helper.py",
        "ddbb09e794ae284c836d67b3ad6755b30930b6dee5819018325910dcce9540b3",
    ),
    "f161_tests": (
        "tests/test_foundation161_future_runtime_lifecycle_helper.py",
        "69c9eb9cf3471e85fb18f12560d01a78d7c7a0ea679b0b5795b073b9a4b502cf",
    ),
    "f161_gate": (
        "docs/l28_foundation161_future_runtime_lifecycle_gate_v0.1.json",
        "24e839fc0707c64ea4c0d957730368bb404e1f45b16d842cd383d1ba76de0e8c",
    ),
    "f161_design": (
        "docs/foundation161_future_runtime_lifecycle_design_v0.1.md",
        "f4e8a24eb0e840a8d03ca15f45587260f8dcc31dd1f64100614b6aca46ad3d95",
    ),
    "f162_boundary": (
        "tests/foundation162_future_live_adapter_boundary.py",
        "a58d4c5929e38d4a40fc0544ce8035be417da39f9bb60c8d6ffc55df0df7d47a",
    ),
    "f162_tests": (
        "tests/test_foundation162_future_live_adapter_boundary.py",
        "7b26785f2c3f09d715d2278da9ca56f9f96c184c55bec9cb27069963c1474eb1",
    ),
    "f162_gate": (
        "docs/l28_foundation162_future_live_adapter_security_gate_v0.1.json",
        "112008e5b4fc2d14b0b7239038f21006493f668ffff21f224e2633377bc8c8fc",
    ),
    "f162_design": (
        "docs/foundation162_future_live_adapter_security_design_v0.1.md",
        "f6ff6647309cdd92a9ffcb6fd0d9ee02a1d8914c693b1accf744b564e6030900",
    ),
}


class AdapterCandidateFailure(RuntimeError):
    """Deterministic fail-closed candidate error."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


class FutureLiveAdapterCandidate:
    """Binds and plans against opaque resources without activating them."""

    def __init__(self):
        self._lifecycle_owner = None
        self._security_boundary = None
        self._f163_readiness_gate = None
        self._f163_readiness_snapshot = None
        self._ready = None
        self._result_channel = None
        self._children = ()
        self._startup_supervisors = ()
        self._deadline_descriptor = None
        self._child_terminal = {}
        self._supervisor_quiescent = {}
        self._planned_phase_index = 0
        self._frozen = False
        self._provenance_verified = False

    @property
    def lifecycle_owner(self):
        return self._lifecycle_owner

    @property
    def security_boundary(self):
        return self._security_boundary

    @property
    def ready(self):
        return self._ready

    @property
    def result_channel(self):
        return self._result_channel

    @property
    def children(self):
        return self._children

    @property
    def startup_supervisors(self):
        return self._startup_supervisors

    @property
    def deadline_descriptor(self):
        return self._deadline_descriptor

    @property
    def frozen(self):
        return self._frozen

    @property
    def provenance_verified(self):
        return self._provenance_verified

    @property
    def planned_phase(self):
        return LIFECYCLE_PHASES[self._planned_phase_index]

    @property
    def execution_authorized(self):
        return False

    def register_and_freeze(
        self,
        lifecycle_owner,
        security_boundary,
        f163_readiness_gate,
        ready,
        result_channel,
        children,
        startup_supervisors,
        deadline_descriptor,
    ):
        if self._frozen:
            raise AdapterCandidateFailure("CANDIDATE_ALREADY_FROZEN")
        self._validate_complete_resources(
            lifecycle_owner,
            security_boundary,
            f163_readiness_gate,
            ready,
            result_channel,
            children,
            startup_supervisors,
            deadline_descriptor,
        )
        self._validate_f163_gate(f163_readiness_gate)
        self._validate_owner_and_boundary(
            lifecycle_owner,
            security_boundary,
            ready,
            result_channel,
            children,
            startup_supervisors,
        )

        (
            self._lifecycle_owner,
            self._security_boundary,
            self._f163_readiness_gate,
            self._f163_readiness_snapshot,
            self._ready,
            self._result_channel,
            self._children,
            self._startup_supervisors,
            self._deadline_descriptor,
            self._child_terminal,
            self._supervisor_quiescent,
            self._frozen,
            self._provenance_verified,
        ) = (
            lifecycle_owner,
            security_boundary,
            f163_readiness_gate,
            self._freeze_data(f163_readiness_gate),
            ready,
            result_channel,
            children,
            startup_supervisors,
            deadline_descriptor,
            {id(child): False for child in children},
            {id(supervisor): False for supervisor in startup_supervisors},
            True,
            True,
        )

    @staticmethod
    def _validate_complete_resources(
        lifecycle_owner,
        security_boundary,
        f163_readiness_gate,
        ready,
        result_channel,
        children,
        startup_supervisors,
        deadline_descriptor,
    ):
        if lifecycle_owner is None:
            raise AdapterCandidateFailure("F161_LIFECYCLE_OWNER_REQUIRED")
        if security_boundary is None:
            raise AdapterCandidateFailure("F162_SECURITY_BOUNDARY_REQUIRED")
        if f163_readiness_gate is None:
            raise AdapterCandidateFailure("F163_READINESS_GATE_REQUIRED")
        if ready is None:
            raise AdapterCandidateFailure("READY_REFERENCE_REQUIRED")
        if result_channel is None:
            raise AdapterCandidateFailure("RESULT_CHANNEL_REFERENCE_REQUIRED")
        if not isinstance(children, tuple) or not children:
            raise AdapterCandidateFailure("EXACT_CHILD_COLLECTION_REQUIRED")
        if not isinstance(startup_supervisors, tuple) or not startup_supervisors:
            raise AdapterCandidateFailure("EXACT_SUPERVISOR_COLLECTION_REQUIRED")
        if any(child is None for child in children):
            raise AdapterCandidateFailure("INVALID_CHILD_REFERENCE")
        if any(supervisor is None for supervisor in startup_supervisors):
            raise AdapterCandidateFailure("INVALID_SUPERVISOR_REFERENCE")
        if deadline_descriptor is None:
            raise AdapterCandidateFailure("BOUNDED_DEADLINE_DESCRIPTOR_REQUIRED")
        if deadline_descriptor != DEADLINE_DESCRIPTOR:
            raise AdapterCandidateFailure("INVALID_DEADLINE_DESCRIPTOR")
        exact_resources = (
            lifecycle_owner,
            security_boundary,
            ready,
            result_channel,
        ) + children + startup_supervisors
        if len({id(resource) for resource in exact_resources}) != len(
            exact_resources
        ):
            raise AdapterCandidateFailure("DUPLICATE_RESOURCE_IDENTITY")

    @staticmethod
    def _validate_f163_gate(gate):
        if not isinstance(gate, dict):
            raise AdapterCandidateFailure("F163_READINESS_GATE_MAPPING_REQUIRED")
        if gate.get("profile") != F163_PROFILE:
            raise AdapterCandidateFailure("F163_READINESS_PROFILE_REQUIRED")
        if gate.get("baseline_commit") != F163_BASELINE:
            raise AdapterCandidateFailure("F163_BASELINE_BINDING_REQUIRED")
        bindings = gate.get("source_bindings")
        if not isinstance(bindings, dict) or set(bindings) != set(
            REQUIRED_F163_SOURCE_BINDINGS
        ):
            raise AdapterCandidateFailure("F163_SOURCE_BINDINGS_REQUIRED")
        for name, (path, digest) in REQUIRED_F163_SOURCE_BINDINGS.items():
            if bindings.get(name) != {"path": path, "sha256": digest}:
                raise AdapterCandidateFailure("F163_SOURCE_BINDING_MISMATCH")
        if gate.get("status") != F163_READY_STATUS:
            raise AdapterCandidateFailure("F163_READINESS_STATUS_REQUIRED")
        readiness = gate.get("implementation_readiness")
        if readiness != {
            "READY_FOR_FUTURE_LIVE_ADAPTER_IMPLEMENTATION_REVIEW": True,
            "EXECUTION_AUTHORIZED": False,
            "RUNTIME_AUTHORIZED": False,
            "TESTNET_AUTHORIZED": False,
            "PRODUCTION_READY": False,
        }:
            raise AdapterCandidateFailure("F163_READINESS_BOUNDARY_INVALID")
        if gate.get("authority") != REQUIRED_F163_AUTHORITY:
            raise AdapterCandidateFailure("F163_AUTHORITY_FIREWALL_INVALID")
        historical = gate.get("historical_state")
        if historical != {
            "F159_RESULT": "ABORT",
            "ROOT_CAUSE": "NOT_PROVEN",
            "SEMLOCK_EVIDENCE_CLASSIFICATION": (
                "OPERATOR_OBSERVED_NOT_MACHINE_PERSISTED"
            ),
            "F159_RETRY_FORBIDDEN": True,
        }:
            raise AdapterCandidateFailure("F163_HISTORICAL_STATE_INVALID")
        dimensions = gate.get("readiness_dimensions")
        if not isinstance(dimensions, dict) or set(dimensions) != set(
            REQUIRED_F163_DIMENSIONS
        ):
            raise AdapterCandidateFailure("F163_READINESS_DIMENSIONS_REQUIRED")
        if any(
            not isinstance(evidence, dict) or evidence.get("result") != "PASS"
            for evidence in dimensions.values()
        ):
            raise AdapterCandidateFailure("F163_READINESS_DIMENSION_NOT_PASS")
        if gate.get("offline_boundary") != REQUIRED_F163_OFFLINE_BOUNDARY:
            raise AdapterCandidateFailure("F163_OFFLINE_BOUNDARY_INVALID")
        if gate.get("protected_authority") != REQUIRED_PROTECTED_AUTHORITY:
            raise AdapterCandidateFailure("F163_PROTECTED_AUTHORITY_INVALID")
        if gate.get("protected_invariants") != REQUIRED_F163_PROTECTED_INVARIANTS:
            raise AdapterCandidateFailure("F163_PROTECTED_INVARIANTS_INVALID")

    @classmethod
    def _freeze_data(cls, value):
        if isinstance(value, dict):
            return tuple(
                sorted((key, cls._freeze_data(item)) for key, item in value.items())
            )
        if isinstance(value, (list, tuple)):
            return tuple(cls._freeze_data(item) for item in value)
        if value is None or isinstance(value, (bool, int, str)):
            return value
        raise AdapterCandidateFailure("UNSUPPORTED_READINESS_GATE_VALUE")

    @classmethod
    def _validate_owner_and_boundary(
        cls,
        owner,
        boundary,
        ready,
        result_channel,
        children,
        supervisors,
    ):
        if getattr(owner, "released", True):
            raise AdapterCandidateFailure("ACTIVE_F161_PARENT_OWNERSHIP_REQUIRED")
        if getattr(owner, "phase", None) != LIFECYCLE_PHASES[0]:
            raise AdapterCandidateFailure("F161_CONSTRUCTION_PHASE_REQUIRED")
        if getattr(owner, "ready", None) is not ready:
            raise AdapterCandidateFailure("F161_READY_OWNERSHIP_MISMATCH")
        if getattr(owner, "result_channel", None) is not result_channel:
            raise AdapterCandidateFailure("F161_RESULT_OWNERSHIP_MISMATCH")
        cls._require_identity_sequence(
            getattr(owner, "children", None),
            children,
            "F161_CHILD_OWNERSHIP_MISMATCH",
        )
        cls._require_identity_sequence(
            getattr(owner, "startup_supervisors", None),
            supervisors,
            "F161_SUPERVISOR_OWNERSHIP_MISMATCH",
        )

        if getattr(boundary, "registered", False) is not True:
            raise AdapterCandidateFailure("F162_REGISTERED_BOUNDARY_REQUIRED")
        if getattr(boundary, "resource_set_frozen", False) is not True:
            raise AdapterCandidateFailure("F162_FROZEN_BOUNDARY_REQUIRED")
        if getattr(boundary, "provenance_verified", False) is not True:
            raise AdapterCandidateFailure("F162_PROVENANCE_REQUIRED")
        if getattr(boundary, "execution_authorized", True) is not False:
            raise AdapterCandidateFailure("F162_EXECUTION_AUTHORITY_FORBIDDEN")
        if getattr(boundary, "lifecycle_helper", None) is not owner:
            raise AdapterCandidateFailure("F162_OWNER_IDENTITY_MISMATCH")
        if getattr(boundary, "ready", None) is not ready:
            raise AdapterCandidateFailure("F162_READY_PROVENANCE_MISMATCH")
        if getattr(boundary, "result_channel", None) is not result_channel:
            raise AdapterCandidateFailure("F162_RESULT_PROVENANCE_MISMATCH")
        cls._require_identity_sequence(
            getattr(boundary, "children", None),
            children,
            "F162_CHILD_PROVENANCE_MISMATCH",
        )
        cls._require_identity_sequence(
            getattr(boundary, "startup_supervisors", None),
            supervisors,
            "F162_SUPERVISOR_PROVENANCE_MISMATCH",
        )

    @staticmethod
    def _require_identity_sequence(registered, supplied, code):
        if not isinstance(registered, tuple) or len(registered) != len(supplied):
            raise AdapterCandidateFailure(code)
        if any(
            owned is not candidate
            for owned, candidate in zip(registered, supplied, strict=True)
        ):
            raise AdapterCandidateFailure(code)

    def _require_frozen_integrity(self):
        if not self._frozen:
            raise AdapterCandidateFailure("FROZEN_CANDIDATE_REQUIRED")
        if self._freeze_data(self._f163_readiness_gate) != (
            self._f163_readiness_snapshot
        ):
            raise AdapterCandidateFailure("F163_READINESS_GATE_MUTATED")

    def preparation_state(self):
        self._require_frozen_integrity()
        return {
            "state": PREPARED_STATE,
            "planned_phase": self.planned_phase,
            "resources_frozen": True,
            "provenance_verified": True,
            "execution_authorized": False,
            "runtime_authorized": False,
        }

    def attempt_resource_replacement(self, resource_role, replacement):
        self._require_frozen_integrity()
        if resource_role not in {
            "lifecycle_owner",
            "security_boundary",
            "f163_readiness_gate",
            "ready",
            "result_channel",
            "child",
            "startup_supervisor",
            "deadline_descriptor",
        }:
            raise AdapterCandidateFailure("UNKNOWN_RESOURCE_ROLE")
        if replacement is None:
            raise AdapterCandidateFailure("INVALID_REPLACEMENT_REFERENCE")
        raise AdapterCandidateFailure("FROZEN_CANDIDATE_IMMUTABLE")

    def plan_lifecycle_transition(self, next_phase):
        self._require_frozen_integrity()
        if self.planned_phase == "RELEASED":
            raise AdapterCandidateFailure("PLANNED_LIFECYCLE_ALREADY_RELEASED")
        expected = LIFECYCLE_PHASES[self._planned_phase_index + 1]
        if next_phase != expected:
            raise AdapterCandidateFailure("INVALID_PLANNED_LIFECYCLE_TRANSITION")
        if next_phase == "RELEASED":
            raise AdapterCandidateFailure("RELEASE_PLAN_REQUIRED")
        current = self.planned_phase
        self._planned_phase_index += 1
        return {
            "plan": "LIFECYCLE_TRANSITION_DATA_ONLY",
            "from": current,
            "to": next_phase,
            "runtime_change_applied": False,
            "execution_authorized": False,
        }

    def record_child_terminal_state(self, child):
        self._require_frozen_integrity()
        self._require_exact_child(child)
        if self._child_terminal[id(child)]:
            raise AdapterCandidateFailure("CHILD_TERMINAL_STATE_ALREADY_RECORDED")
        self._child_terminal[id(child)] = True

    def record_supervisor_quiescent_state(self, supervisor):
        self._require_frozen_integrity()
        self._require_exact_supervisor(supervisor)
        if self._supervisor_quiescent[id(supervisor)]:
            raise AdapterCandidateFailure("SUPERVISOR_STATE_ALREADY_RECORDED")
        self._supervisor_quiescent[id(supervisor)] = True

    def _require_exact_child(self, child):
        if not any(child is registered for registered in self._children):
            raise AdapterCandidateFailure("UNKNOWN_CHILD_REFERENCE")

    def _require_exact_supervisor(self, supervisor):
        if not any(
            supervisor is registered for registered in self._startup_supervisors
        ):
            raise AdapterCandidateFailure("UNKNOWN_SUPERVISOR_REFERENCE")

    def cleanup_eligibility(self):
        self._require_frozen_integrity()
        if self.planned_phase != "CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL":
            raise AdapterCandidateFailure("CLEANUP_PHASE_PLAN_REQUIRED")
        if any(not state for state in self._child_terminal.values()):
            raise AdapterCandidateFailure("LIVE_CHILD_PREVENTS_CLEANUP_ELIGIBILITY")
        if any(not state for state in self._supervisor_quiescent.values()):
            raise AdapterCandidateFailure(
                "ACTIVE_SUPERVISOR_PREVENTS_CLEANUP_ELIGIBILITY"
            )
        return {
            "state": "ELIGIBLE_FOR_DATA_ONLY_RELEASE_PLAN",
            "cleanup_action_performed": False,
            "resources_released": False,
            "execution_authorized": False,
        }

    def plan_release_after_cleanup(self):
        eligibility = self.cleanup_eligibility()
        self._planned_phase_index += 1
        return {
            "plan": "RELEASE_DATA_ONLY",
            "from": "CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL",
            "to": "RELEASED",
            "cleanup_action_performed": eligibility["cleanup_action_performed"],
            "resources_released": False,
            "execution_authorized": False,
        }

    def authority_state(self):
        return {
            "NEW_AUTHORIZATION_REQUIRED": NEW_AUTHORIZATION_REQUIRED,
            "SEPARATE_SECURITY_REVIEW_REQUIRED": SEPARATE_SECURITY_REVIEW_REQUIRED,
            "SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED": (
                SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED
            ),
            "F159_RETRY_FORBIDDEN": F159_RETRY_FORBIDDEN,
            "OLD_AUTHORIZATION_REUSABLE": OLD_AUTHORIZATION_REUSABLE,
            "F161_EXECUTION_AUTHORIZED": F161_EXECUTION_AUTHORIZED,
            "F162_EXECUTION_AUTHORIZED": F162_EXECUTION_AUTHORIZED,
            "F163_EXECUTION_AUTHORIZED": F163_EXECUTION_AUTHORIZED,
            "F164_EXECUTION_AUTHORIZED": F164_EXECUTION_AUTHORIZED,
        }
