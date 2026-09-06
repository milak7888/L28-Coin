# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative_path):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


resource_model = load_module(
    "foundation163_resource_contract",
    "tests/foundation163_live_adapter_resource_contract.py",
)
boundary_model = load_module(
    "foundation162_boundary",
    "tests/foundation162_future_live_adapter_boundary.py",
)
f161_model = load_module(
    "foundation161_lifecycle",
    "tests/foundation161_future_runtime_lifecycle_helper.py",
)


class Token:
    pass


class LookalikeToken:
    def __eq__(self, _other):
        return True


def make_registered_inputs(child_count=2, supervisor_count=2):
    ready = Token()
    result_channel = Token()
    children = tuple(Token() for _ in range(child_count))
    supervisors = tuple(Token() for _ in range(supervisor_count))
    owner = f161_model.FutureRuntimeLifecycleHelper(
        ready,
        result_channel,
        children,
        supervisors,
    )
    boundary = boundary_model.FutureLiveAdapterBoundary()
    boundary.register_parent_owned_resources(
        owner,
        ready,
        result_channel,
        children,
        supervisors,
    )
    return (
        boundary,
        owner,
        ready,
        result_channel,
        children,
        supervisors,
        resource_model.bounded_deadline_descriptor(),
    )


def make_contract():
    contract = resource_model.LiveAdapterResourceContract()
    inputs = make_registered_inputs()
    contract.register_and_freeze(*inputs)
    return contract, inputs


def test_complete_exact_resource_contract_is_accepted_and_frozen():
    contract, inputs = make_contract()
    assert contract.boundary is inputs[0]
    assert contract.lifecycle_owner is inputs[1]
    assert contract.ready is inputs[2]
    assert contract.result_channel is inputs[3]
    assert contract.children == inputs[4]
    assert contract.startup_supervisors == inputs[5]
    assert contract.deadline_descriptor == inputs[6]
    assert contract.frozen is True
    assert contract.provenance_verified is True
    assert contract.readiness_code == resource_model.RESOURCE_CONTRACT_READY
    assert contract.execution_authorized is False


@pytest.mark.parametrize(
    ("index", "replacement", "code"),
    [
        (0, None, "F162_BOUNDARY_REQUIRED"),
        (1, None, "F161_LIFECYCLE_OWNER_REQUIRED"),
        (2, None, "READY_REFERENCE_REQUIRED"),
        (3, None, "RESULT_CHANNEL_REFERENCE_REQUIRED"),
        (4, (), "EXACT_CHILD_COLLECTION_REQUIRED"),
        (5, (), "EXACT_SUPERVISOR_COLLECTION_REQUIRED"),
        (6, None, "BOUNDED_DEADLINE_DESCRIPTOR_REQUIRED"),
    ],
)
def test_missing_resources_fail_closed(index, replacement, code):
    inputs = list(make_registered_inputs())
    inputs[index] = replacement
    contract = resource_model.LiveAdapterResourceContract()
    with pytest.raises(resource_model.ResourceContractFailure) as captured:
        contract.register_and_freeze(*inputs)
    assert captured.value.code == code
    assert contract.frozen is False


@pytest.mark.parametrize("resource_index", [4, 5])
def test_duplicate_child_or_supervisor_is_rejected(resource_index):
    inputs = list(make_registered_inputs())
    duplicate = inputs[resource_index][0]
    inputs[resource_index] = (duplicate, duplicate)
    contract = resource_model.LiveAdapterResourceContract()
    with pytest.raises(resource_model.ResourceContractFailure) as captured:
        contract.register_and_freeze(*inputs)
    assert captured.value.code == "DUPLICATE_RESOURCE_IDENTITY"


@pytest.mark.parametrize(
    ("resource_index", "code"),
    [
        (2, "READY_PROVENANCE_MISMATCH"),
        (3, "RESULT_CHANNEL_PROVENANCE_MISMATCH"),
        (4, "CHILD_PROVENANCE_MISMATCH"),
        (5, "SUPERVISOR_PROVENANCE_MISMATCH"),
    ],
)
def test_resource_substitution_and_lookalikes_are_rejected(resource_index, code):
    inputs = list(make_registered_inputs())
    if resource_index in (2, 3):
        inputs[resource_index] = LookalikeToken()
    else:
        resources = list(inputs[resource_index])
        resources[0] = LookalikeToken()
        inputs[resource_index] = tuple(resources)
    contract = resource_model.LiveAdapterResourceContract()
    with pytest.raises(resource_model.ResourceContractFailure) as captured:
        contract.register_and_freeze(*inputs)
    assert captured.value.code == code


def test_exact_lifecycle_owner_identity_is_required():
    inputs = list(make_registered_inputs())
    inputs[1] = LookalikeToken()
    contract = resource_model.LiveAdapterResourceContract()
    with pytest.raises(resource_model.ResourceContractFailure) as captured:
        contract.register_and_freeze(*inputs)
    assert captured.value.code == "LIFECYCLE_OWNER_IDENTITY_MISMATCH"


@pytest.mark.parametrize(
    ("target_index", "attribute", "code"),
    [
        (0, "_children", "F162_BOUNDARY_RESOURCE_SET_INVALID"),
        (1, "_children", "F161_OWNER_RESOURCE_SET_INVALID"),
    ],
)
def test_malformed_owned_collection_fails_with_deterministic_code(
    target_index, attribute, code
):
    inputs = list(make_registered_inputs())
    setattr(inputs[target_index], attribute, None)
    contract = resource_model.LiveAdapterResourceContract()
    with pytest.raises(resource_model.ResourceContractFailure) as captured:
        contract.register_and_freeze(*inputs)
    assert captured.value.code == code
    assert contract.frozen is False


@pytest.mark.parametrize(
    "role",
    [
        "boundary",
        "lifecycle_owner",
        "ready",
        "result_channel",
        "child",
        "startup_supervisor",
        "deadline_descriptor",
    ],
)
def test_post_freeze_mutation_is_rejected(role):
    contract, inputs = make_contract()
    with pytest.raises(resource_model.ResourceContractFailure) as captured:
        contract.attempt_replacement(role, LookalikeToken())
    assert captured.value.code == "FROZEN_RESOURCE_CONTRACT_IMMUTABLE"
    assert contract.ready is inputs[2]
    assert contract.result_channel is inputs[3]


def test_repeated_freeze_is_rejected():
    contract, inputs = make_contract()
    with pytest.raises(resource_model.ResourceContractFailure) as captured:
        contract.register_and_freeze(*inputs)
    assert captured.value.code == "RESOURCE_CONTRACT_ALREADY_FROZEN"


@pytest.mark.parametrize(
    ("resource_index", "replacement", "code"),
    [
        (4, [Token()], "EXACT_CHILD_COLLECTION_REQUIRED"),
        (5, [Token()], "EXACT_SUPERVISOR_COLLECTION_REQUIRED"),
        (4, (None,), "INVALID_CHILD_REFERENCE"),
        (5, (None,), "INVALID_SUPERVISOR_REFERENCE"),
    ],
)
def test_invalid_resource_collections_fail_closed(resource_index, replacement, code):
    inputs = list(make_registered_inputs())
    inputs[resource_index] = replacement
    contract = resource_model.LiveAdapterResourceContract()
    with pytest.raises(resource_model.ResourceContractFailure) as captured:
        contract.register_and_freeze(*inputs)
    assert captured.value.code == code


def test_deadline_descriptor_is_immutable_data_only():
    descriptor = resource_model.bounded_deadline_descriptor()
    assert isinstance(descriptor, tuple)
    assert descriptor == (
        "SINGLE_BOUNDED_DEADLINE_DATA_ONLY",
        (
            "RESOURCE_CONSTRUCTION",
            "STARTUP_SUPERVISION",
            "CHILD_BOOTSTRAP",
            "ACTIVE_WORK",
            "CLEANUP_INITIATION",
        ),
        ("bounded", True),
        ("timer_implemented", False),
    )


def test_invalid_deadline_descriptor_is_rejected():
    inputs = list(make_registered_inputs())
    inputs[6] = ("UNBOUNDED",)
    contract = resource_model.LiveAdapterResourceContract()
    with pytest.raises(resource_model.ResourceContractFailure) as captured:
        contract.register_and_freeze(*inputs)
    assert captured.value.code == "INVALID_DEADLINE_DESCRIPTOR"


def test_resource_contract_never_produces_execution_authority():
    contract, _inputs = make_contract()
    assert resource_model.F163_EXECUTION_AUTHORIZED is False
    assert contract.execution_authorized is False
