# SPDX-License-Identifier: Apache-2.0
"""Offline-only security model for a future live-resource adapter boundary."""


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

TERMINAL_STATES = (
    "SUCCESS",
    "EXECUTION_ABORT",
    "CLEANUP_FAILURE",
    "TERMINALIZATION_FAILURE",
)

NEW_AUTHORIZATION_REQUIRED = True
SEPARATE_SECURITY_REVIEW_REQUIRED = True
SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED = True
F159_RETRY_FORBIDDEN = True
F157_F158_F159_CONSUMPTION_STATE_REUSABLE = False
F161_EXECUTION_AUTHORIZED = False
F162_EXECUTION_AUTHORIZED = False


class AdapterBoundaryFailure(RuntimeError):
    """Deterministic fail-closed boundary error."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


class FutureLiveAdapterBoundary:
    """Validates opaque resources already owned by an injected F161 helper."""

    def __init__(self):
        self._lifecycle_helper = None
        self._ready = None
        self._result_channel = None
        self._children = ()
        self._startup_supervisors = ()
        self._registered = False
        self._frozen = False
        self._provenance_verified = False
        self._resources_released = False
        self._terminal_state = None

    @property
    def registered(self):
        return self._registered

    @property
    def resource_set_frozen(self):
        return self._frozen

    @property
    def provenance_verified(self):
        return self._provenance_verified

    @property
    def lifecycle_helper(self):
        return self._lifecycle_helper

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
    def phase(self):
        if not self._registered:
            return None
        return self._lifecycle_helper.phase

    @property
    def terminal_state(self):
        return self._terminal_state

    @property
    def resources_released(self):
        return self._resources_released

    @property
    def hypothetical_start_eligible(self):
        if not (self._registered and self._frozen and self._provenance_verified):
            return False
        if self._lifecycle_helper.released:
            return False
        return self.phase not in (
            "CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL",
            "RELEASED",
        )

    @property
    def execution_authorized(self):
        return False

    def register_parent_owned_resources(
        self,
        lifecycle_helper,
        ready,
        result_channel,
        children,
        startup_supervisors,
    ):
        if self._frozen or self._registered:
            raise AdapterBoundaryFailure("RESOURCE_SET_ALREADY_FROZEN")
        if lifecycle_helper is None:
            raise AdapterBoundaryFailure("F161_PARENT_OWNERSHIP_REQUIRED")
        required_methods = (
            "transition_to",
            "record_child_arguments_released",
            "mark_child_terminal",
            "mark_supervisor_quiescent",
            "release_resources",
        )
        if any(
            not callable(getattr(lifecycle_helper, method, None))
            for method in required_methods
        ):
            raise AdapterBoundaryFailure("F161_LIFECYCLE_INTERFACE_REQUIRED")
        if ready is None:
            raise AdapterBoundaryFailure("READY_REFERENCE_REQUIRED")
        if result_channel is None:
            raise AdapterBoundaryFailure("RESULT_CHANNEL_REFERENCE_REQUIRED")
        if not isinstance(children, tuple) or not children:
            raise AdapterBoundaryFailure("EXACT_CHILD_COLLECTION_REQUIRED")
        if not isinstance(startup_supervisors, tuple) or not startup_supervisors:
            raise AdapterBoundaryFailure("EXACT_SUPERVISOR_COLLECTION_REQUIRED")
        if any(resource is None for resource in children):
            raise AdapterBoundaryFailure("INVALID_CHILD_REFERENCE")
        if any(resource is None for resource in startup_supervisors):
            raise AdapterBoundaryFailure("INVALID_SUPERVISOR_REFERENCE")

        resources = (ready, result_channel) + children + startup_supervisors
        if len({id(resource) for resource in resources}) != len(resources):
            raise AdapterBoundaryFailure("DUPLICATE_RESOURCE_IDENTITY")
        if getattr(lifecycle_helper, "released", True):
            raise AdapterBoundaryFailure("ACTIVE_F161_PARENT_OWNERSHIP_REQUIRED")
        if getattr(lifecycle_helper, "phase", None) != LIFECYCLE_PHASES[0]:
            raise AdapterBoundaryFailure("F161_CONSTRUCTION_PHASE_REQUIRED")
        if getattr(lifecycle_helper, "ready", None) is not ready:
            raise AdapterBoundaryFailure("READY_PROVENANCE_MISMATCH")
        if getattr(lifecycle_helper, "result_channel", None) is not result_channel:
            raise AdapterBoundaryFailure("RESULT_CHANNEL_PROVENANCE_MISMATCH")
        owned_children = getattr(lifecycle_helper, "children", None)
        owned_supervisors = getattr(lifecycle_helper, "startup_supervisors", None)
        if not isinstance(owned_children, tuple) or not isinstance(
            owned_supervisors, tuple
        ):
            raise AdapterBoundaryFailure("F161_OWNED_COLLECTIONS_REQUIRED")
        if not self._same_identity_sequence(owned_children, children):
            raise AdapterBoundaryFailure("CHILD_PROVENANCE_MISMATCH")
        if not self._same_identity_sequence(
            owned_supervisors,
            startup_supervisors,
        ):
            raise AdapterBoundaryFailure("SUPERVISOR_PROVENANCE_MISMATCH")

        (
            self._lifecycle_helper,
            self._ready,
            self._result_channel,
            self._children,
            self._startup_supervisors,
            self._registered,
            self._frozen,
            self._provenance_verified,
        ) = (
            lifecycle_helper,
            ready,
            result_channel,
            children,
            startup_supervisors,
            True,
            True,
            True,
        )

    @staticmethod
    def _same_identity_sequence(owned, supplied):
        return len(owned) == len(supplied) and all(
            registered is candidate
            for registered, candidate in zip(owned, supplied, strict=True)
        )

    def _require_registered(self):
        if not self._registered:
            raise AdapterBoundaryFailure("COMPLETE_RESOURCE_REGISTRATION_REQUIRED")

    def _require_exact_child(self, child):
        self._require_registered()
        if not any(child is registered for registered in self._children):
            raise AdapterBoundaryFailure("UNKNOWN_CHILD_REFERENCE")

    def _require_exact_supervisor(self, supervisor):
        self._require_registered()
        if not any(
            supervisor is registered for registered in self._startup_supervisors
        ):
            raise AdapterBoundaryFailure("UNKNOWN_SUPERVISOR_REFERENCE")

    def attempt_resource_replacement(self, resource_role, replacement):
        self._require_registered()
        if resource_role not in {
            "ready",
            "result_channel",
            "child",
            "startup_supervisor",
        }:
            raise AdapterBoundaryFailure("UNKNOWN_RESOURCE_ROLE")
        if replacement is None:
            raise AdapterBoundaryFailure("INVALID_REPLACEMENT_REFERENCE")
        raise AdapterBoundaryFailure("RESOURCE_SET_FROZEN")

    def transition_to(self, next_phase):
        self._require_registered()
        if self.phase == "RELEASED":
            raise AdapterBoundaryFailure("LIFECYCLE_ALREADY_RELEASED")
        current_index = LIFECYCLE_PHASES.index(self.phase)
        expected = LIFECYCLE_PHASES[current_index + 1]
        if next_phase != expected:
            raise AdapterBoundaryFailure("INVALID_LIFECYCLE_TRANSITION")
        if next_phase == "RELEASED":
            raise AdapterBoundaryFailure("RELEASE_OPERATION_REQUIRED")
        self._lifecycle_helper.transition_to(next_phase)

    def record_child_arguments_released(self, child):
        self._require_exact_child(child)
        self._lifecycle_helper.record_child_arguments_released(child)

    def mark_child_terminal(self, child):
        self._require_exact_child(child)
        self._lifecycle_helper.mark_child_terminal(child)

    def mark_supervisor_quiescent(self, supervisor):
        self._require_exact_supervisor(supervisor)
        self._lifecycle_helper.mark_supervisor_quiescent(supervisor)

    def release_owned_resources(self):
        self._require_registered()
        self._lifecycle_helper.release_resources()
        (
            self._ready,
            self._result_channel,
            self._children,
            self._startup_supervisors,
            self._resources_released,
        ) = (None, None, (), (), True)

    def record_terminal_state(self, terminal_state):
        if terminal_state not in TERMINAL_STATES:
            raise AdapterBoundaryFailure("UNKNOWN_TERMINAL_STATE")
        if self._terminal_state is not None:
            raise AdapterBoundaryFailure("TERMINAL_STATE_ALREADY_RECORDED")
        self._terminal_state = terminal_state

    def deadline_contract(self):
        return {
            "single_bounded_deadline_required": True,
            "coverage": DEADLINE_COVERAGE,
            "timer_implemented": False,
        }

    def authority_contract(self):
        return {
            "NEW_AUTHORIZATION_REQUIRED": NEW_AUTHORIZATION_REQUIRED,
            "SEPARATE_SECURITY_REVIEW_REQUIRED": SEPARATE_SECURITY_REVIEW_REQUIRED,
            "SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED": (
                SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED
            ),
            "F159_RETRY_FORBIDDEN": F159_RETRY_FORBIDDEN,
            "F157_F158_F159_CONSUMPTION_STATE_REUSABLE": (
                F157_F158_F159_CONSUMPTION_STATE_REUSABLE
            ),
            "F161_EXECUTION_AUTHORIZED": F161_EXECUTION_AUTHORIZED,
            "F162_EXECUTION_AUTHORIZED": F162_EXECUTION_AUTHORIZED,
        }
