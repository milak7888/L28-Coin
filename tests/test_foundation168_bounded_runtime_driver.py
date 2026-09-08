# SPDX-License-Identifier: Apache-2.0
import pytest

from coin.foundation168_bounded_runtime_driver import (
    BoundedRuntimeDriver,
    EXPECTED_ARTIFACT_HASHES,
    RuntimeDriverFailure,
    exact_scope,
)
from coin.foundation168_execution_authorization import (
    BASE_COMMIT,
    EXPERIMENT_ID,
    F164_CANDIDATE_SHA256,
    F166_DECISION,
    F166_GATE_SHA256,
    F167_GATE_SHA256,
    F168_INVOCATION,
    OneShotExecutionAuthorization,
    initial_state,
)
from coin.foundation168_post_run_review import ABORT_ACCEPTED, PASS, evaluate_post_run


def decision_evidence():
    return {
        "experiment_id": EXPERIMENT_ID,
        "decision": F166_DECISION,
        "authorization_id": "L28-F168-FUTURE-ONE-SHOT-TEST",
        "base_commit": BASE_COMMIT,
        "f164_candidate_sha256": F164_CANDIDATE_SHA256,
        "f166_gate_sha256": F166_GATE_SHA256,
        "f167_gate_sha256": F167_GATE_SHA256,
        "one_shot": True,
        "f159_retry_forbidden": True,
        "old_authorization_reusable": False,
    }


def invocation_evidence():
    return {
        "experiment_id": EXPERIMENT_ID,
        "invocation": F168_INVOCATION,
        "authorization_id": "L28-F168-FUTURE-ONE-SHOT-TEST",
        "separate_explicit_invocation": True,
    }


class FakeClock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value


class FakeBackend:
    def __init__(self, authorization, clock, failure=None, cleanup_complete=True):
        assert authorization.state["F168_AUTHORIZATION_CONSUMED"] is True
        self.clock = clock
        self.failure = failure
        self.cleanup_complete = cleanup_complete
        self.calls = []

    def _step(self, name):
        self.calls.append(name)
        if self.failure == name:
            raise RuntimeError(name + " failed")

    def construct_resources(self, deadline):
        self._step("construction")
        return {"fake": True}

    def start_supervision(self, resources, deadline):
        self._step("startup")

    def bootstrap(self, resources, deadline):
        self._step("bootstrap")

    def active_work(self, resources, deadline):
        self._step("active")
        if self.failure == "deadline":
            self.clock.value = deadline + 1
        if self.failure == "reconnect":
            raise RuntimeError("reconnect failed")
        if self.failure == "child":
            raise RuntimeError("child failed")
        return {
            "agent_a_effective_listener": ["127.0.0.1", 28428],
            "agent_b_effective_source_ports": [31001, 31002],
            "session_count": 2,
            "reconnect_count": 1,
        }

    def cleanup(self, resources, deadline):
        self.calls.append("cleanup")
        if self.failure == "cleanup_exception":
            raise RuntimeError("cleanup failed")
        return {
            "all_children_terminal": self.cleanup_complete,
            "supervisors_quiescent": self.cleanup_complete,
            "cleanup_complete": self.cleanup_complete,
            "child_lifecycle_states": [
                {"name": "agent-a", "terminal": self.cleanup_complete},
                {"name": "agent-b", "terminal": self.cleanup_complete},
            ],
        }


def run_fake(failure=None, cleanup_complete=True):
    authorization = OneShotExecutionAuthorization(initial_state())
    clock = FakeClock()
    holder = {}

    def factory():
        backend = FakeBackend(authorization, clock, failure, cleanup_complete)
        holder["backend"] = backend
        return backend

    driver = BoundedRuntimeDriver(authorization, factory, monotonic=clock)
    evidence = driver._run_claimed_once(
        exact_scope(),
        dict(EXPECTED_ARTIFACT_HASHES),
        decision_evidence(),
        invocation_evidence(),
    )
    return evidence, authorization, holder.get("backend")


def test_valid_dual_evidence_reaches_one_shot_success_with_cleanup():
    evidence, authorization, backend = run_fake()
    assert evaluate_post_run(evidence) == PASS
    assert backend.calls == ["construction", "startup", "bootstrap", "active", "cleanup"]
    assert authorization.state["claim_count"] == 1
    assert evidence["authorization_consumed"] is True
    assert evidence["lifecycle_phases"][-2:] == ["RECONNECT", "CLEANUP_INITIATION"]


@pytest.mark.parametrize(
    ("key", "expanded"),
    [
        ("agent_count", 3),
        ("child_process_count", 3),
        ("network_family", "IPv4_ANY"),
        ("external_network", True),
        ("agent_a_listener", ("0.0.0.0", 28428)),
        ("agent_b_source_bind", ("127.0.0.1", 28429)),
        ("fixed_client_source_port_28429_forbidden", False),
        ("session_count", 3),
        ("reconnect_count", 2),
        ("maximum_duration_seconds", 61),
        ("deadline_coverage", ("ACTIVE_EXECUTION",)),
        ("cleanup_requires_all_children_terminal", False),
        ("cleanup_requires_supervisors_quiescent", False),
        ("terminal_states", ("SUCCESS",)),
    ],
)
def test_scope_expansion_is_rejected_before_backend_construction(key, expanded):
    authorization = OneShotExecutionAuthorization(initial_state())
    constructed = []
    scope = exact_scope()
    scope[key] = expanded
    driver = BoundedRuntimeDriver(authorization, lambda: constructed.append(True))
    with pytest.raises(RuntimeDriverFailure, match="SCOPE_INVALID"):
        driver._run_claimed_once(
            scope, dict(EXPECTED_ARTIFACT_HASHES), decision_evidence(), invocation_evidence()
        )
    assert constructed == []
    assert authorization.state == initial_state()


def test_stale_hash_is_rejected_before_claim_or_construction():
    authorization = OneShotExecutionAuthorization(initial_state())
    hashes = dict(EXPECTED_ARTIFACT_HASHES)
    hashes["f167_gate"] = "0" * 64
    driver = BoundedRuntimeDriver(authorization, lambda: pytest.fail("constructed"))
    with pytest.raises(RuntimeDriverFailure, match="ARTIFACT_BINDING_INVALID"):
        driver._run_claimed_once(exact_scope(), hashes, decision_evidence(), invocation_evidence())
    assert authorization.state == initial_state()


@pytest.mark.parametrize("failure", ("construction", "startup", "bootstrap", "active", "child", "reconnect"))
def test_runtime_failure_is_bounded_consumed_and_always_cleans_up(failure):
    evidence, authorization, backend = run_fake(failure=failure)
    assert evidence["terminal_state"] == "EXECUTION_ABORT"
    assert evidence["authorization_consumed"] is True
    assert authorization.state["F168_RETRY_ALLOWED"] is False
    assert backend.calls[-1] == "cleanup"
    assert evaluate_post_run(evidence) == ABORT_ACCEPTED


def test_deadline_overrun_fails_closed_and_cannot_be_accepted_as_bounded():
    evidence, authorization, backend = run_fake(failure="deadline")
    assert evidence["terminal_state"] == "EXECUTION_ABORT"
    assert authorization.state["F168_RETRY_ALLOWED"] is False
    assert backend.calls[-1] == "cleanup"
    assert evaluate_post_run(evidence) != PASS
    assert evaluate_post_run(evidence) != ABORT_ACCEPTED


def test_cleanup_incomplete_or_exception_cannot_pass():
    incomplete, _, _ = run_fake(cleanup_complete=False)
    assert incomplete["terminal_state"] == "CLEANUP_FAILURE"
    assert evaluate_post_run(incomplete) != PASS
    failed, _, backend = run_fake(failure="cleanup_exception")
    assert backend.calls[-1] == "cleanup"
    assert failed["terminal_state"] == "CLEANUP_FAILURE"
    assert evaluate_post_run(failed) != PASS


def test_no_automatic_retry_after_success_or_abort():
    evidence, authorization, backend = run_fake(failure="bootstrap")
    assert evidence["terminal_state"] == "EXECUTION_ABORT"
    driver = BoundedRuntimeDriver(authorization, lambda: backend)
    with pytest.raises(Exception, match="ALREADY_CONSUMED"):
        driver._run_claimed_once(
            exact_scope(), dict(EXPECTED_ARTIFACT_HASHES), decision_evidence(), invocation_evidence()
        )
    assert backend.calls.count("construction") == 1


def test_backend_factory_failure_is_persistable_abort_after_claim():
    authorization = OneShotExecutionAuthorization(initial_state())
    driver = BoundedRuntimeDriver(
        authorization, lambda: (_ for _ in ()).throw(RuntimeError("factory failed"))
    )
    evidence = driver._run_claimed_once(
        exact_scope(), dict(EXPECTED_ARTIFACT_HASHES), decision_evidence(), invocation_evidence()
    )
    assert evidence["terminal_state"] == "EXECUTION_ABORT"
    assert evidence["exception_type"] == "RuntimeError"
    assert authorization.state["F168_AUTHORIZATION_CONSUMED"] is True
