# SPDX-License-Identifier: Apache-2.0
"""Offline-only parent-ownership model for future spawn/bootstrap design."""


REQUIRED_PHASES = (
    "PROCESS_OBJECT_CONSTRUCTION",
    "PROCESS_START_SUPERVISION",
    "CHILD_BOOTSTRAP_WINDOW",
    "ACTIVE_EXECUTION",
    "CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL",
)

AUTHORIZATION_GRANTED = False
EXECUTION_CAPABILITY_ADDED = False


class LifetimeContractError(RuntimeError):
    """Raised when an offline lifecycle transition would fail open."""


class ChildLifecycle:
    """Non-runtime child lifecycle token with disposable argument references."""

    def __init__(self, identifier, argument_references):
        if not identifier or not argument_references:
            raise LifetimeContractError("child_lifecycle_invalid")
        self.identifier = identifier
        self._argument_references = list(argument_references)
        self._arguments_released = False
        self._terminal = False

    @property
    def terminal(self):
        return self._terminal

    @property
    def argument_reference_count(self):
        return len(self._argument_references)

    def drop_argument_references(self):
        if self._arguments_released:
            raise LifetimeContractError("child_arguments_already_released")
        self._argument_references.clear()
        self._arguments_released = True

    def mark_terminal(self):
        if self._terminal:
            raise LifetimeContractError("child_already_terminal")
        self._terminal = True


class StartupSupervisorLifecycle:
    """Non-runtime supervisor lifecycle token."""

    def __init__(self, identifier):
        if not identifier:
            raise LifetimeContractError("startup_supervisor_invalid")
        self.identifier = identifier
        self._active = True

    @property
    def active(self):
        return self._active

    def mark_quiescent(self):
        if not self._active:
            raise LifetimeContractError("startup_supervisor_already_quiescent")
        self._active = False


class ParentOwnedLifetimeBundle:
    """Strongly owns future child bootstrap resources until safe release."""

    def __init__(self, ready, result_channel, children, startup_supervisors):
        if ready is None:
            raise LifetimeContractError("ready_reference_required")
        if result_channel is None:
            raise LifetimeContractError("result_channel_reference_required")
        if not children:
            raise LifetimeContractError("child_lifecycle_references_required")
        if not startup_supervisors:
            raise LifetimeContractError("startup_supervisor_references_required")
        self._ready = ready
        self._result_channel = result_channel
        self._children = tuple(children)
        self._startup_supervisors = tuple(startup_supervisors)
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

    def transition_to(self, next_phase):
        if self._released:
            raise LifetimeContractError("bundle_already_released")
        next_index = self._phase_index + 1
        if next_index >= len(REQUIRED_PHASES):
            raise LifetimeContractError("lifecycle_already_at_cleanup")
        if next_phase != REQUIRED_PHASES[next_index]:
            raise LifetimeContractError("invalid_lifecycle_transition")
        self._phase_index = next_index

    def release_resources(self):
        if self._released:
            raise LifetimeContractError("bundle_already_released")
        if self.phase != "CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL":
            raise LifetimeContractError("cleanup_phase_required")
        if any(not child.terminal for child in self._children):
            raise LifetimeContractError("live_child_prevents_release")
        if any(supervisor.active for supervisor in self._startup_supervisors):
            raise LifetimeContractError("active_startup_supervisor_prevents_release")
        self._ready = None
        self._result_channel = None
        self._children = ()
        self._startup_supervisors = ()
        self._released = True
