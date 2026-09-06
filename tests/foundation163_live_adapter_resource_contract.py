# SPDX-License-Identifier: Apache-2.0
"""Offline resource contract for future live-adapter implementation review."""


DEADLINE_COVERAGE = (
    "RESOURCE_CONSTRUCTION",
    "STARTUP_SUPERVISION",
    "CHILD_BOOTSTRAP",
    "ACTIVE_WORK",
    "CLEANUP_INITIATION",
)
DEADLINE_DESCRIPTOR_KIND = "SINGLE_BOUNDED_DEADLINE_DATA_ONLY"
RESOURCE_CONTRACT_READY = "RESOURCE_CONTRACT_READY_FOR_IMPLEMENTATION_REVIEW"
RESOURCE_CONTRACT_NOT_READY = "RESOURCE_CONTRACT_NOT_READY"

F163_EXECUTION_AUTHORIZED = False


class ResourceContractFailure(RuntimeError):
    """Deterministic fail-closed registration error."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def bounded_deadline_descriptor():
    """Return an immutable, capability-free deadline requirement descriptor."""

    return (
        DEADLINE_DESCRIPTOR_KIND,
        DEADLINE_COVERAGE,
        ("bounded", True),
        ("timer_implemented", False),
    )


class LiveAdapterResourceContract:
    """Freezes exact opaque resources already governed by F161 and F162."""

    def __init__(self):
        self._boundary = None
        self._lifecycle_owner = None
        self._ready = None
        self._result_channel = None
        self._children = ()
        self._startup_supervisors = ()
        self._deadline_descriptor = None
        self._frozen = False
        self._provenance_verified = False

    @property
    def boundary(self):
        return self._boundary

    @property
    def lifecycle_owner(self):
        return self._lifecycle_owner

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
    def readiness_code(self):
        if self._frozen and self._provenance_verified:
            return RESOURCE_CONTRACT_READY
        return RESOURCE_CONTRACT_NOT_READY

    @property
    def execution_authorized(self):
        return False

    def register_and_freeze(
        self,
        boundary,
        lifecycle_owner,
        ready,
        result_channel,
        children,
        startup_supervisors,
        deadline_descriptor,
    ):
        if self._frozen:
            raise ResourceContractFailure("RESOURCE_CONTRACT_ALREADY_FROZEN")
        if boundary is None:
            raise ResourceContractFailure("F162_BOUNDARY_REQUIRED")
        if lifecycle_owner is None:
            raise ResourceContractFailure("F161_LIFECYCLE_OWNER_REQUIRED")
        if ready is None:
            raise ResourceContractFailure("READY_REFERENCE_REQUIRED")
        if result_channel is None:
            raise ResourceContractFailure("RESULT_CHANNEL_REFERENCE_REQUIRED")
        if not isinstance(children, tuple) or not children:
            raise ResourceContractFailure("EXACT_CHILD_COLLECTION_REQUIRED")
        if not isinstance(startup_supervisors, tuple) or not startup_supervisors:
            raise ResourceContractFailure("EXACT_SUPERVISOR_COLLECTION_REQUIRED")
        if any(resource is None for resource in children):
            raise ResourceContractFailure("INVALID_CHILD_REFERENCE")
        if any(resource is None for resource in startup_supervisors):
            raise ResourceContractFailure("INVALID_SUPERVISOR_REFERENCE")
        if deadline_descriptor is None:
            raise ResourceContractFailure("BOUNDED_DEADLINE_DESCRIPTOR_REQUIRED")
        if deadline_descriptor != bounded_deadline_descriptor():
            raise ResourceContractFailure("INVALID_DEADLINE_DESCRIPTOR")

        exact_resources = (
            lifecycle_owner,
            ready,
            result_channel,
        ) + children + startup_supervisors
        if len({id(resource) for resource in exact_resources}) != len(
            exact_resources
        ):
            raise ResourceContractFailure("DUPLICATE_RESOURCE_IDENTITY")

        if getattr(boundary, "registered", False) is not True:
            raise ResourceContractFailure("F162_REGISTERED_BOUNDARY_REQUIRED")
        if getattr(boundary, "resource_set_frozen", False) is not True:
            raise ResourceContractFailure("F162_FROZEN_BOUNDARY_REQUIRED")
        if getattr(boundary, "provenance_verified", False) is not True:
            raise ResourceContractFailure("F162_PROVENANCE_REQUIRED")
        if getattr(boundary, "execution_authorized", True) is not False:
            raise ResourceContractFailure("F162_EXECUTION_AUTHORITY_FORBIDDEN")
        if getattr(boundary, "hypothetical_start_eligible", False) is not True:
            raise ResourceContractFailure("F162_HYPOTHETICAL_ELIGIBILITY_REQUIRED")
        if getattr(boundary, "lifecycle_helper", None) is not lifecycle_owner:
            raise ResourceContractFailure("LIFECYCLE_OWNER_IDENTITY_MISMATCH")
        if getattr(boundary, "ready", None) is not ready:
            raise ResourceContractFailure("READY_PROVENANCE_MISMATCH")
        if getattr(boundary, "result_channel", None) is not result_channel:
            raise ResourceContractFailure("RESULT_CHANNEL_PROVENANCE_MISMATCH")
        boundary_children = getattr(boundary, "children", None)
        boundary_supervisors = getattr(boundary, "startup_supervisors", None)
        if not isinstance(boundary_children, tuple) or not isinstance(
            boundary_supervisors, tuple
        ):
            raise ResourceContractFailure("F162_BOUNDARY_RESOURCE_SET_INVALID")
        if not self._same_identity_sequence(boundary_children, children):
            raise ResourceContractFailure("CHILD_PROVENANCE_MISMATCH")
        if not self._same_identity_sequence(
            boundary_supervisors,
            startup_supervisors,
        ):
            raise ResourceContractFailure("SUPERVISOR_PROVENANCE_MISMATCH")

        if getattr(lifecycle_owner, "released", True):
            raise ResourceContractFailure("ACTIVE_F161_OWNERSHIP_REQUIRED")
        if getattr(lifecycle_owner, "ready", None) is not ready:
            raise ResourceContractFailure("F161_READY_OWNERSHIP_MISMATCH")
        if getattr(lifecycle_owner, "result_channel", None) is not result_channel:
            raise ResourceContractFailure("F161_RESULT_OWNERSHIP_MISMATCH")
        owner_children = getattr(lifecycle_owner, "children", None)
        owner_supervisors = getattr(lifecycle_owner, "startup_supervisors", None)
        if not isinstance(owner_children, tuple) or not isinstance(
            owner_supervisors, tuple
        ):
            raise ResourceContractFailure("F161_OWNER_RESOURCE_SET_INVALID")
        if not self._same_identity_sequence(owner_children, children):
            raise ResourceContractFailure("F161_CHILD_OWNERSHIP_MISMATCH")
        if not self._same_identity_sequence(
            owner_supervisors,
            startup_supervisors,
        ):
            raise ResourceContractFailure("F161_SUPERVISOR_OWNERSHIP_MISMATCH")

        (
            self._boundary,
            self._lifecycle_owner,
            self._ready,
            self._result_channel,
            self._children,
            self._startup_supervisors,
            self._deadline_descriptor,
            self._frozen,
            self._provenance_verified,
        ) = (
            boundary,
            lifecycle_owner,
            ready,
            result_channel,
            children,
            startup_supervisors,
            deadline_descriptor,
            True,
            True,
        )

    @staticmethod
    def _same_identity_sequence(registered, supplied):
        return len(registered) == len(supplied) and all(
            owned is candidate
            for owned, candidate in zip(registered, supplied, strict=True)
        )

    def attempt_replacement(self, resource_role, replacement):
        if not self._frozen:
            raise ResourceContractFailure("FROZEN_RESOURCE_CONTRACT_REQUIRED")
        if resource_role not in {
            "boundary",
            "lifecycle_owner",
            "ready",
            "result_channel",
            "child",
            "startup_supervisor",
            "deadline_descriptor",
        }:
            raise ResourceContractFailure("UNKNOWN_RESOURCE_ROLE")
        if replacement is None:
            raise ResourceContractFailure("INVALID_REPLACEMENT_REFERENCE")
        raise ResourceContractFailure("FROZEN_RESOURCE_CONTRACT_IMMUTABLE")
