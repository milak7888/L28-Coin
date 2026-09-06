# SPDX-License-Identifier: Apache-2.0
"""Capability-free lifecycle helper for future adapter review only."""


F160_REQUIRED_PHASES = (
    "PROCESS_OBJECT_CONSTRUCTION",
    "PROCESS_START_SUPERVISION",
    "CHILD_BOOTSTRAP_WINDOW",
    "ACTIVE_EXECUTION",
    "CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL",
)
REQUIRED_PHASES = F160_REQUIRED_PHASES + ("RELEASED",)

AUTHORIZATION_GRANTED = False
AUTHORIZATION_CONSUMED = False
EXECUTION_CAPABILITY_ADDED = False


class LifecycleFailure(RuntimeError):
    """Deterministic fail-closed lifecycle error."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


class FutureRuntimeLifecycleHelper:
    """Owns opaque resources without creating or operating runtime objects."""

    def __init__(self, ready, result_channel, children, startup_supervisors):
        if ready is None:
            raise LifecycleFailure("READY_REFERENCE_REQUIRED")
        if result_channel is None:
            raise LifecycleFailure("RESULT_CHANNEL_REFERENCE_REQUIRED")
        if not isinstance(children, tuple) or not children:
            raise LifecycleFailure("EXACT_CHILD_COLLECTION_REQUIRED")
        if not isinstance(startup_supervisors, tuple) or not startup_supervisors:
            raise LifecycleFailure("EXACT_SUPERVISOR_COLLECTION_REQUIRED")
        if any(child is None for child in children):
            raise LifecycleFailure("INVALID_CHILD_REFERENCE")
        if any(supervisor is None for supervisor in startup_supervisors):
            raise LifecycleFailure("INVALID_SUPERVISOR_REFERENCE")
        if len({id(child) for child in children}) != len(children):
            raise LifecycleFailure("DUPLICATE_CHILD_REGISTRATION")
        if len({id(supervisor) for supervisor in startup_supervisors}) != len(
            startup_supervisors
        ):
            raise LifecycleFailure("DUPLICATE_SUPERVISOR_REGISTRATION")
        all_resources = (ready, result_channel) + children + startup_supervisors
        if len({id(resource) for resource in all_resources}) != len(all_resources):
            raise LifecycleFailure("RESOURCE_ROLE_COLLISION")

        self._ready = ready
        self._result_channel = result_channel
        self._children = children
        self._startup_supervisors = startup_supervisors
        self._child_state = {
            id(child): {"terminal": False, "arguments_released": False}
            for child in children
        }
        self._supervisor_state = {
            id(supervisor): {"quiescent": False}
            for supervisor in startup_supervisors
        }
        self._phase_index = 0
        self._released = False

    @property
    def phase(self):
        return REQUIRED_PHASES[self._phase_index]

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
    def released(self):
        return self._released

    def _require_active(self):
        if self._released:
            raise LifecycleFailure("LIFECYCLE_ALREADY_RELEASED")

    def _require_exact_child(self, child):
        self._require_active()
        if not any(child is registered for registered in self._children):
            raise LifecycleFailure("UNKNOWN_CHILD_REFERENCE")

    def _require_exact_supervisor(self, supervisor):
        self._require_active()
        if not any(
            supervisor is registered for registered in self._startup_supervisors
        ):
            raise LifecycleFailure("UNKNOWN_SUPERVISOR_REFERENCE")

    def transition_to(self, next_phase):
        self._require_active()
        next_index = self._phase_index + 1
        if next_index >= len(REQUIRED_PHASES):
            raise LifecycleFailure("NO_FURTHER_LIFECYCLE_TRANSITION")
        expected = REQUIRED_PHASES[next_index]
        if next_phase != expected:
            raise LifecycleFailure("INVALID_LIFECYCLE_TRANSITION")
        if next_phase == "RELEASED":
            raise LifecycleFailure("RELEASE_OPERATION_REQUIRED")
        self._phase_index = next_index

    def record_child_arguments_released(self, child):
        self._require_exact_child(child)
        state = self._child_state[id(child)]
        if state["arguments_released"]:
            raise LifecycleFailure("CHILD_ARGUMENT_RELEASE_ALREADY_RECORDED")
        state["arguments_released"] = True

    def mark_child_terminal(self, child):
        self._require_exact_child(child)
        state = self._child_state[id(child)]
        if state["terminal"]:
            raise LifecycleFailure("CHILD_ALREADY_TERMINAL")
        state["terminal"] = True

    def mark_supervisor_quiescent(self, supervisor):
        self._require_exact_supervisor(supervisor)
        state = self._supervisor_state[id(supervisor)]
        if state["quiescent"]:
            raise LifecycleFailure("SUPERVISOR_ALREADY_QUIESCENT")
        state["quiescent"] = True

    def child_arguments_released(self, child):
        self._require_exact_child(child)
        return self._child_state[id(child)]["arguments_released"]

    def child_terminal(self, child):
        self._require_exact_child(child)
        return self._child_state[id(child)]["terminal"]

    def supervisor_quiescent(self, supervisor):
        self._require_exact_supervisor(supervisor)
        return self._supervisor_state[id(supervisor)]["quiescent"]

    def release_resources(self):
        self._require_active()
        if self.phase != "CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL":
            raise LifecycleFailure("CLEANUP_PHASE_REQUIRED")
        if any(not state["terminal"] for state in self._child_state.values()):
            raise LifecycleFailure("NONTERMINAL_CHILD_PREVENTS_RELEASE")
        if any(
            not state["quiescent"] for state in self._supervisor_state.values()
        ):
            raise LifecycleFailure("ACTIVE_SUPERVISOR_PREVENTS_RELEASE")

        (
            self._ready,
            self._result_channel,
            self._children,
            self._startup_supervisors,
            self._child_state,
            self._supervisor_state,
            self._phase_index,
            self._released,
        ) = (None, None, (), (), {}, {}, len(REQUIRED_PHASES) - 1, True)
