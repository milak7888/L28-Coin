# SPDX-License-Identifier: Apache-2.0
"""Pure offline model for a proposed F165 authorization decision package."""


PROPOSED_EXPERIMENT_ID = "L28-F165-PROPOSED-BOUNDED-RUNTIME-001"

DEADLINE_COVERAGE = (
    "PROCESS_OBJECT_CONSTRUCTION",
    "PROCESS_START_SUPERVISION",
    "CHILD_BOOTSTRAP_WINDOW",
    "ACTIVE_EXECUTION",
    "CLEANUP_INITIATION",
)

TERMINAL_STATES = (
    "SUCCESS",
    "EXECUTION_ABORT",
    "CLEANUP_FAILURE",
    "TERMINALIZATION_FAILURE",
)

REQUIRED_SOURCE_BINDINGS = {
    "F160": "408fe4264253a2940b93a051cdace49fda325019c8178def003ff695632e23d5",
    "F161": "24e839fc0707c64ea4c0d957730368bb404e1f45b16d842cd383d1ba76de0e8c",
    "F162": "112008e5b4fc2d14b0b7239038f21006493f668ffff21f224e2633377bc8c8fc",
    "F163": "6322cbfca6260e36e445c8f110f420be2b161168e2e234ebcecbac50e56b4985",
    "F164": "a05dd02527b2cd20ca1636ec2a6b48c62719957a32140f55a83ceb3f6ab788e6",
}

EXPECTED_SCOPE = {
    "disposable": True,
    "isolated": True,
    "agent_count": 2,
    "child_process_count": 2,
    "network_family": "IPv4_LOOPBACK_ONLY",
    "external_network_allowed": False,
    "agent_a_listener": ("127.0.0.1", 28428),
    "agent_b_bind": ("127.0.0.1", 0),
    "fixed_client_source_port_28429_forbidden": True,
    "session_count": 2,
    "reconnect_count": 1,
    "maximum_duration_seconds": 60,
    "deadline_kind": "ONE_SINGLE_BOUNDED_DEADLINE",
    "deadline_coverage": DEADLINE_COVERAGE,
    "strong_parent_resource_ownership_required": True,
    "parent_ownership_contracts": ("F160", "F161"),
    "provenance_freeze_security_contracts": ("F162", "F163"),
    "f164_candidate_required": True,
    "f164_candidate_activating": False,
    "cleanup_requires_all_children_terminal": True,
    "cleanup_requires_all_supervisors_quiescent": True,
    "terminal_states": TERMINAL_STATES,
}


class AuthorizationPackageError(ValueError):
    """Raised when the proposed package would exceed or weaken its boundary."""


def proposed_scope():
    """Return a fresh exact-scope value suitable for offline review."""

    return dict(EXPECTED_SCOPE)


def required_source_bindings():
    """Return the exact F160-F164 decision-gate bindings."""

    return dict(REQUIRED_SOURCE_BINDINGS)


class RuntimeAuthorizationDecisionPackage:
    """Frozen proposed experiment data; deliberately has no grant operation."""

    def __init__(self):
        self._configured = False
        self._scope_items = ()
        self._binding_items = ()

    @property
    def configured(self):
        return self._configured

    def configure_proposal(self, experiment_id, scope, source_bindings):
        if self._configured:
            raise AuthorizationPackageError("PACKAGE_ALREADY_FROZEN")
        if experiment_id != PROPOSED_EXPERIMENT_ID:
            raise AuthorizationPackageError("PROPOSED_EXPERIMENT_ID_MISMATCH")
        if not isinstance(scope, dict) or scope != EXPECTED_SCOPE:
            raise AuthorizationPackageError("PROPOSED_SCOPE_NOT_EXACT")
        if (
            not isinstance(source_bindings, dict)
            or source_bindings != REQUIRED_SOURCE_BINDINGS
        ):
            raise AuthorizationPackageError("F160_F164_BINDINGS_NOT_EXACT")
        self._scope_items = tuple(scope.items())
        self._binding_items = tuple(source_bindings.items())
        self._configured = True
        return self.snapshot()

    def snapshot(self):
        scope = dict(self._scope_items)
        bindings = dict(self._binding_items)
        return {
            "proposed_experiment_id": PROPOSED_EXPERIMENT_ID,
            "package_configured": self._configured,
            "scope": scope,
            "source_bindings": bindings,
            "authorization_granted": False,
            "execution_authorized": False,
            "execution_invocation_present": False,
            "consumed": False,
            "reusable": False,
            "f159_authorization_reusable": False,
        }
