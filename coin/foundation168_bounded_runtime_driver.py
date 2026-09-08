# SPDX-License-Identifier: Apache-2.0
"""Dormant, explicitly invoked bounded F168 loopback runtime driver."""

import importlib
import json
import multiprocessing
import queue
import socket
import threading
import time
from pathlib import Path

from coin.foundation168_execution_authorization import (
    BASE_COMMIT,
    EXPERIMENT_ID,
    OneShotExecutionAuthorization,
)
from coin.foundation168_execution_evidence import finalize_evidence, sanitized_exception
MAX_DURATION_SECONDS = 60
EXPECTED_ARTIFACT_HASHES = {
    "f164_candidate": "1921fb28103e0240c9fac6f0e1c3e17f6c0a2b5824a1609ed3cbdf91f1e4d2db",
    "f166_gate": "f5433efd24f051b188d6e937f0debf651ddf61543089c10a8443745bb1c1b526",
    "f167_gate": "e569f395327db19deff63cc8228339e48f50ea2ece447cadbc35eba5daa82ca0",
    "protocol": "eabd5f2a11916781e6a047e5b2c2188fe4e0f1eae2fdcdc2f68e4c19193c397d",
    "validator": "ac36bd95c932733a60ffc3acbb10b8a9f57e09c9533d0b64ff83affa876f3004",
}
DEADLINE_COVERAGE = (
    "PROCESS_OBJECT_CONSTRUCTION",
    "PROCESS_START_SUPERVISION",
    "CHILD_BOOTSTRAP_WINDOW",
    "ACTIVE_EXECUTION",
    "RECONNECT",
    "CLEANUP_INITIATION",
)
TERMINAL_STATES = (
    "SUCCESS",
    "EXECUTION_ABORT",
    "CLEANUP_FAILURE",
    "TERMINALIZATION_FAILURE",
)
EXPECTED_SCOPE = {
    "disposable": True,
    "isolated": True,
    "agent_count": 2,
    "child_process_count": 2,
    "network_family": "IPv4_LOOPBACK_ONLY",
    "external_network": False,
    "agent_a_listener": ("127.0.0.1", 28428),
    "agent_b_source_bind": ("127.0.0.1", 0),
    "fixed_client_source_port_28429_forbidden": True,
    "session_count": 2,
    "reconnect_count": 1,
    "maximum_duration_seconds": 60,
    "deadline_kind": "ONE_ABSOLUTE_MONOTONIC_DEADLINE",
    "deadline_coverage": DEADLINE_COVERAGE,
    "strong_parent_resource_retention": True,
    "f160_f161_lifecycle_required": True,
    "f162_f163_provenance_freeze_required": True,
    "f164_candidate_required": True,
    "cleanup_requires_all_children_terminal": True,
    "cleanup_requires_supervisors_quiescent": True,
    "terminal_states": TERMINAL_STATES,
}


class RuntimeDriverFailure(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def exact_scope():
    return dict(EXPECTED_SCOPE)


class _SupervisorMarker:
    def __init__(self):
        self.quiescent = False


class _RuntimeLifecycleOwner:
    PHASES = (
        "PROCESS_OBJECT_CONSTRUCTION",
        "PROCESS_START_SUPERVISION",
        "CHILD_BOOTSTRAP_WINDOW",
        "ACTIVE_EXECUTION",
        "CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL",
        "RELEASED",
    )

    def __init__(self, ready, result_channel, children, supervisors):
        self.ready = ready
        self.result_channel = result_channel
        self.children = children
        self.startup_supervisors = supervisors
        self._phase_index = 0
        self.released = False

    @property
    def phase(self):
        return self.PHASES[self._phase_index]

    def advance(self, phase):
        expected = self.PHASES[self._phase_index + 1]
        if phase != expected or phase == "RELEASED":
            raise RuntimeDriverFailure("INVALID_RUNTIME_LIFECYCLE_TRANSITION")
        self._phase_index += 1

    def release(self):
        if self.phase != "CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL":
            raise RuntimeDriverFailure("PREMATURE_RUNTIME_RESOURCE_RELEASE")
        self._phase_index += 1
        self.released = True


class _RuntimeSecurityBoundary:
    def __init__(self, owner):
        self.registered = True
        self.resource_set_frozen = True
        self.provenance_verified = True
        self.execution_authorized = False
        self.lifecycle_helper = owner
        self.ready = owner.ready
        self.result_channel = owner.result_channel
        self.children = owner.children
        self.startup_supervisors = owner.startup_supervisors


def _agent_a_child(ready, result_channel, deadline):
    listener = None
    try:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.settimeout(max(0.1, deadline - time.monotonic()))
        listener.bind(("127.0.0.1", 28428))
        listener.listen(1)
        result_channel.put({"kind": "listener", "address": ["127.0.0.1", 28428]})
        ready.set()
        received = 0
        for _ in range(2):
            connection, address = listener.accept()
            try:
                if address[0] != "127.0.0.1":
                    raise RuntimeDriverFailure("EXTERNAL_PEER_FORBIDDEN")
                connection.settimeout(max(0.1, deadline - time.monotonic()))
                if connection.recv(64) != b"F168-BOUNDED-SESSION":
                    raise RuntimeDriverFailure("SESSION_PAYLOAD_INVALID")
                received += 1
            finally:
                connection.close()
        result_channel.put({"kind": "agent_a_complete", "sessions": received})
    except BaseException as error:
        result_channel.put(
            {"kind": "child_error", "child": "agent_a", "error": repr(error)}
        )
        raise
    finally:
        if listener is not None:
            listener.close()


def _agent_b_child(ready, result_channel, deadline):
    ports = []
    try:
        if not ready.wait(max(0.0, deadline - time.monotonic())):
            raise RuntimeDriverFailure("AGENT_A_BOOTSTRAP_TIMEOUT")
        for _ in range(2):
            connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                connection.settimeout(max(0.1, deadline - time.monotonic()))
                connection.bind(("127.0.0.1", 0))
                port = connection.getsockname()[1]
                if port in (0, 28429) or port in ports:
                    raise RuntimeDriverFailure("EPHEMERAL_SOURCE_PORT_INVALID")
                ports.append(port)
                connection.connect(("127.0.0.1", 28428))
                connection.sendall(b"F168-BOUNDED-SESSION")
            finally:
                connection.close()
        result_channel.put({"kind": "agent_b_complete", "source_ports": ports})
    except BaseException as error:
        result_channel.put(
            {"kind": "child_error", "child": "agent_b", "error": repr(error)}
        )
        raise


class _LoopbackRuntimeBackend:
    """Concrete future backend. Construction is deferred until after claim."""

    def __init__(self, f163_gate_path):
        self._f163_gate_path = Path(f163_gate_path)
        self._resources = {
            "ready": None,
            "result_channel": None,
            "children": (),
            "supervisors": (),
            "owner": None,
            "candidate": None,
        }

    def construct_resources(self, deadline):
        candidate_module = importlib.import_module(
            "coin.future_live_adapter_candidate"
        )
        context = multiprocessing.get_context("spawn")
        ready = context.Event()
        self._resources["ready"] = ready
        result_channel = context.Queue()
        self._resources["result_channel"] = result_channel
        children = (
            context.Process(target=_agent_a_child, args=(ready, result_channel, deadline)),
            context.Process(target=_agent_b_child, args=(ready, result_channel, deadline)),
        )
        self._resources["children"] = children
        supervisors = (_SupervisorMarker(), _SupervisorMarker())
        self._resources["supervisors"] = supervisors
        owner = _RuntimeLifecycleOwner(ready, result_channel, children, supervisors)
        self._resources["owner"] = owner
        boundary = _RuntimeSecurityBoundary(owner)
        gate = json.loads(self._f163_gate_path.read_text(encoding="utf-8"))
        candidate = candidate_module.FutureLiveAdapterCandidate()
        candidate.register_and_freeze(
            owner, boundary, gate, ready, result_channel, children, supervisors,
            candidate_module.DEADLINE_DESCRIPTOR,
        )
        self._resources["candidate"] = candidate
        return self._resources

    @staticmethod
    def _advance(resources, phase):
        resources["owner"].advance(phase)
        resources["candidate"].plan_lifecycle_transition(phase)

    def start_supervision(self, resources, deadline):
        self._advance(resources, "PROCESS_START_SUPERVISION")
        for child in resources["children"]:
            if time.monotonic() >= deadline:
                raise RuntimeDriverFailure("DEADLINE_EXCEEDED_BEFORE_PROCESS_START")
            child.start()
        for supervisor in resources["supervisors"]:
            supervisor.quiescent = True

    def bootstrap(self, resources, deadline):
        self._advance(resources, "CHILD_BOOTSTRAP_WINDOW")
        if not resources["ready"].wait(max(0.0, deadline - time.monotonic())):
            raise RuntimeDriverFailure("CHILD_BOOTSTRAP_TIMEOUT")

    def active_work(self, resources, deadline):
        self._advance(resources, "ACTIVE_EXECUTION")
        messages = []
        while len(messages) < 3:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeDriverFailure("ACTIVE_DEADLINE_EXCEEDED")
            try:
                message = resources["result_channel"].get(timeout=remaining)
            except queue.Empty as error:
                raise RuntimeDriverFailure("ACTIVE_RESULT_TIMEOUT") from error
            if message.get("kind") == "child_error":
                raise RuntimeDriverFailure("CHILD_RUNTIME_FAILURE:" + message["child"])
            messages.append(message)
        by_kind = {message["kind"]: message for message in messages}
        return {
            "agent_a_effective_listener": by_kind["listener"]["address"],
            "agent_b_effective_source_ports": by_kind["agent_b_complete"]["source_ports"],
            "session_count": by_kind["agent_a_complete"]["sessions"],
            "reconnect_count": 1,
        }

    def cleanup(self, resources, deadline):
        resources = resources or self._resources
        if resources is None:
            resources = self._resources
        owner = resources["owner"]
        candidate = resources["candidate"]
        if owner is not None and candidate is not None and owner.phase != "CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL":
            while owner.phase != "CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL":
                next_phase = owner.PHASES[owner._phase_index + 1]
                owner.advance(next_phase)
                candidate.plan_lifecycle_transition(next_phase)
        states = []
        for child in resources["children"]:
            started = child.pid is not None
            if started:
                remaining = max(0.0, deadline - time.monotonic())
                child.join(remaining)
                if child.is_alive():
                    child.terminate()
                    child.join(max(0.0, deadline - time.monotonic()))
                terminal = not child.is_alive()
            else:
                terminal = True
            states.append({"name": child.name, "terminal": terminal})
            if terminal and candidate is not None:
                candidate.record_child_terminal_state(child)
        for supervisor in resources["supervisors"]:
            supervisor.quiescent = True
            if candidate is not None:
                candidate.record_supervisor_quiescent_state(supervisor)
        all_terminal = all(state["terminal"] for state in states)
        supervisors_quiescent = all(item.quiescent for item in resources["supervisors"])
        cleanup_complete = all_terminal and supervisors_quiescent
        if cleanup_complete and candidate is not None and owner is not None:
            candidate.plan_release_after_cleanup()
            owner.release()
        channel = resources.get("result_channel")
        if channel is not None:
            channel.close()
            channel.join_thread()
        return {
            "all_children_terminal": all_terminal,
            "supervisors_quiescent": supervisors_quiescent,
            "cleanup_complete": cleanup_complete,
            "child_lifecycle_states": states,
        }


class BoundedRuntimeDriver:
    """One-shot supervisor. Tests inject a fake backend and fake clock."""

    def __init__(self, authorization, backend_factory, monotonic=time.monotonic):
        if not isinstance(authorization, OneShotExecutionAuthorization):
            raise RuntimeDriverFailure("F168_AUTHORIZATION_OBJECT_REQUIRED")
        self._authorization = authorization
        self._backend_factory = backend_factory
        self._monotonic = monotonic
        self._claim_lock = threading.Lock()

    @staticmethod
    def validate_package(scope, artifact_hashes):
        if scope != EXPECTED_SCOPE:
            raise RuntimeDriverFailure("F168_SCOPE_INVALID")
        if artifact_hashes != EXPECTED_ARTIFACT_HASHES:
            raise RuntimeDriverFailure("F168_ARTIFACT_BINDING_INVALID")

    def _run_claimed_once(
        self, scope, artifact_hashes, decision_evidence, invocation_evidence
    ):
        self.validate_package(scope, artifact_hashes)
        with self._claim_lock:
            fingerprint = self._authorization.claim_once(
                decision_evidence, invocation_evidence
            )
        start = self._monotonic()
        deadline = start + scope["maximum_duration_seconds"]
        backend = None
        resources = None
        runtime = {
            "agent_a_effective_listener": ["127.0.0.1", 28428],
            "agent_b_effective_source_ports": [],
            "session_count": 0,
            "reconnect_count": 0,
        }
        phase = "AUTHORIZATION_CONSUMED"
        lifecycle_phases = [phase]
        error = None
        cleanup = {
            "all_children_terminal": False,
            "supervisors_quiescent": False,
            "cleanup_complete": False,
            "child_lifecycle_states": [],
        }
        terminal = "EXECUTION_ABORT"
        try:
            backend = self._backend_factory()
            resources = backend.construct_resources(deadline)
            phase = "PROCESS_OBJECT_CONSTRUCTION"
            lifecycle_phases.append(phase)
            backend.start_supervision(resources, deadline)
            phase = "PROCESS_START_SUPERVISION"
            lifecycle_phases.append(phase)
            backend.bootstrap(resources, deadline)
            phase = "CHILD_BOOTSTRAP_WINDOW"
            lifecycle_phases.append(phase)
            runtime = backend.active_work(resources, deadline)
            phase = "ACTIVE_EXECUTION"
            lifecycle_phases.extend((phase, "RECONNECT"))
            if self._monotonic() > deadline:
                raise RuntimeDriverFailure("ABSOLUTE_DEADLINE_EXCEEDED")
            terminal = "SUCCESS"
        except BaseException as caught:
            error = caught
            terminal = "EXECUTION_ABORT"
        finally:
            phase = "CLEANUP_INITIATION"
            lifecycle_phases.append(phase)
            try:
                if backend is None:
                    cleanup = {
                        "all_children_terminal": True,
                        "supervisors_quiescent": True,
                        "cleanup_complete": True,
                        "child_lifecycle_states": [],
                    }
                else:
                    cleanup = backend.cleanup(resources, deadline)
            except BaseException as cleanup_error:
                if error is None:
                    error = cleanup_error
                terminal = "CLEANUP_FAILURE"
            if not cleanup.get("cleanup_complete", False):
                terminal = "CLEANUP_FAILURE"
            if terminal == "SUCCESS" and (
                not cleanup.get("all_children_terminal", False)
                or not cleanup.get("supervisors_quiescent", False)
            ):
                terminal = "TERMINALIZATION_FAILURE"
        end = self._monotonic()
        if end > deadline and terminal == "SUCCESS":
            terminal = "EXECUTION_ABORT"
            error = RuntimeDriverFailure("ABSOLUTE_DEADLINE_EXCEEDED")
        exception_type, exception_repr = sanitized_exception(error)
        evidence = {
            "experiment_id": EXPERIMENT_ID,
            "authorization_fingerprint": fingerprint,
            "protected_hashes": {
                "base_commit": BASE_COMMIT,
                "f164_candidate_sha256": artifact_hashes["f164_candidate"],
                "f166_gate_sha256": artifact_hashes["f166_gate"],
                "f167_gate_sha256": artifact_hashes["f167_gate"],
                "protocol_sha256": artifact_hashes["protocol"],
                "tx_validation_sha256": artifact_hashes["validator"],
            },
            "start_monotonic": start,
            "end_monotonic": end,
            "deadline_monotonic": deadline,
            "maximum_duration_seconds": scope["maximum_duration_seconds"],
            **runtime,
            **cleanup,
            "cleanup_result": (
                "PASS" if cleanup.get("cleanup_complete", False) else "FAIL"
            ),
            "terminalization_complete": (
                cleanup.get("all_children_terminal", False)
                and cleanup.get("supervisors_quiescent", False)
            ),
            "terminalization_result": (
                "COMPLETE"
                if cleanup.get("all_children_terminal", False)
                and cleanup.get("supervisors_quiescent", False)
                else "INCOMPLETE"
            ),
            "terminal_state": terminal,
            "exception_type": exception_type,
            "exception_repr": exception_repr,
            "phase_reached": phase,
            "lifecycle_phases": lifecycle_phases,
            "authorization_consumed": True,
            "authorization_claim_count": 1,
            "retry_occurred": False,
            "external_network": False,
            "protocol_authority": False,
            "economic_authority": False,
            "signing": False,
        }
        return finalize_evidence(evidence)


def default_backend_factory(root):
    root_path = Path(root)
    return lambda: _LoopbackRuntimeBackend(
        root_path / "docs/l28_foundation163_live_adapter_implementation_readiness_gate_v0.1.json"
    )
