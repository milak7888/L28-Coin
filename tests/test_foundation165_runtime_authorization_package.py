# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "tests/foundation165_runtime_authorization_package.py"


def load_model():
    spec = importlib.util.spec_from_file_location("f165_package", MODEL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


model = load_model()


def configured_package(scope=None, bindings=None):
    package = model.RuntimeAuthorizationDecisionPackage()
    package.configure_proposal(
        model.PROPOSED_EXPERIMENT_ID,
        model.proposed_scope() if scope is None else scope,
        model.required_source_bindings() if bindings is None else bindings,
    )
    return package


def test_exact_proposed_scope_is_accepted_and_frozen_without_authority():
    package = configured_package()
    snapshot = package.snapshot()
    assert snapshot["proposed_experiment_id"] == (
        "L28-F165-PROPOSED-BOUNDED-RUNTIME-001"
    )
    assert snapshot["scope"] == model.EXPECTED_SCOPE
    for key in (
        "authorization_granted",
        "execution_authorized",
        "execution_invocation_present",
        "consumed",
        "reusable",
        "f159_authorization_reusable",
    ):
        assert snapshot[key] is False
    with pytest.raises(model.AuthorizationPackageError, match="ALREADY_FROZEN"):
        package.configure_proposal(
            model.PROPOSED_EXPERIMENT_ID,
            model.proposed_scope(),
            model.required_source_bindings(),
        )


@pytest.mark.parametrize(
    ("key", "expanded"),
    [
        ("disposable", False),
        ("isolated", False),
        ("agent_count", 3),
        ("child_process_count", 3),
        ("network_family", "IPv4_ANY"),
        ("external_network_allowed", True),
        ("agent_a_listener", ("0.0.0.0", 28428)),
        ("agent_b_bind", ("127.0.0.1", 28429)),
        ("fixed_client_source_port_28429_forbidden", False),
        ("session_count", 3),
        ("reconnect_count", 0),
        ("reconnect_count", 2),
        ("maximum_duration_seconds", 61),
        ("deadline_kind", "PER_PHASE_DEADLINES"),
        ("deadline_coverage", model.DEADLINE_COVERAGE[:-1]),
        ("strong_parent_resource_ownership_required", False),
        ("parent_ownership_contracts", ("F161",)),
        ("provenance_freeze_security_contracts", ("F162",)),
        ("f164_candidate_required", False),
        ("f164_candidate_activating", True),
        ("cleanup_requires_all_children_terminal", False),
        ("cleanup_requires_all_supervisors_quiescent", False),
        ("terminal_states", model.TERMINAL_STATES[:-1]),
    ],
)
def test_every_scope_expansion_or_weakening_is_rejected(key, expanded):
    scope = model.proposed_scope()
    scope[key] = expanded
    with pytest.raises(model.AuthorizationPackageError, match="SCOPE_NOT_EXACT"):
        configured_package(scope=scope)


@pytest.mark.parametrize("foundation", ("F160", "F161", "F162", "F163", "F164"))
def test_missing_or_tampered_required_binding_is_rejected(foundation):
    bindings = model.required_source_bindings()
    bindings.pop(foundation)
    with pytest.raises(model.AuthorizationPackageError, match="BINDINGS_NOT_EXACT"):
        configured_package(bindings=bindings)
    bindings = model.required_source_bindings()
    bindings[foundation] = "0" * 64
    with pytest.raises(model.AuthorizationPackageError, match="BINDINGS_NOT_EXACT"):
        configured_package(bindings=bindings)


def test_wrong_or_old_experiment_identity_is_rejected():
    package = model.RuntimeAuthorizationDecisionPackage()
    with pytest.raises(model.AuthorizationPackageError, match="ID_MISMATCH"):
        package.configure_proposal(
            "L28-F157-CORRECTED-RECONNECT-ONE-SHOT-001",
            model.proposed_scope(),
            model.required_source_bindings(),
        )
