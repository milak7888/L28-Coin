# SPDX-License-Identifier: Apache-2.0
"""Data-only terminalization states for the non-activating F164 candidate."""


OPEN = "OPEN"
SUCCESS = "SUCCESS"
EXECUTION_ABORT = "EXECUTION_ABORT"
CLEANUP_FAILURE = "CLEANUP_FAILURE"
TERMINALIZATION_FAILURE = "TERMINALIZATION_FAILURE"
TERMINAL_STATES = (
    SUCCESS,
    EXECUTION_ABORT,
    CLEANUP_FAILURE,
    TERMINALIZATION_FAILURE,
)
F164_EXECUTION_AUTHORIZED = False


class TerminalizationFailure(RuntimeError):
    """Deterministic data-state transition error."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


class TerminalizationRecord:
    """Records exactly one terminal outcome without performing any action."""

    def __init__(self):
        self._state = OPEN

    @property
    def state(self):
        return self._state

    @property
    def terminal(self):
        return self._state in TERMINAL_STATES

    @property
    def execution_authorized(self):
        return False

    def record(self, terminal_state):
        if self._state != OPEN:
            raise TerminalizationFailure("TERMINAL_STATE_ALREADY_RECORDED")
        if terminal_state not in TERMINAL_STATES:
            raise TerminalizationFailure("ILLEGAL_TERMINAL_STATE")
        self._state = terminal_state
        return {
            "state": terminal_state,
            "data_only": True,
            "execution_performed": False,
            "cleanup_performed": False,
            "execution_authorized": False,
        }
