# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/foundation159_corrected_one_shot_loopback_experiment_evidence_v1.0.json"
STATE = ROOT / "docs/l28_foundation159_corrected_one_shot_execution_state_v1.0.json"
CONSUMPTION_MARKER = ROOT / "docs/l28_foundation158_corrected_one_shot_execution_state_v1.0.json"
PROTOCOL = ROOT / "PROTOCOL.md"
VALIDATOR = ROOT / "coin/tx_validation.py"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_result_is_abort_and_binding_is_exact():
    evidence = load(EVIDENCE)
    assert evidence["result"] == "ABORT"
    assert evidence["authorization_id"] == "L28-F157-CORRECTED-RECONNECT-ONE-SHOT-001"
    assert evidence["repository_execution_baseline"] == "ea209aab0717283cbed43493366fff81f02bb52f"
    assert evidence["f158_execution_binding"] == {
        "baseline_commit": "25d3bdc8ec77b96c0af717b1864650388559da5e",
        "preflight_gate_sha256": "1a7f21c69f4169d4714df1c18d082e0cc52647aafb945d7636e7381050a4b62f",
        "helper_sha256": "56d3a8b796ff245cf29124886c0da64b3ab605a640fc45d14a0a26e20ea8e9b6",
        "focused_pre_start_tests_passed": 35,
    }


def test_authorization_is_consumed_terminal_and_never_restartable():
    evidence = load(EVIDENCE)
    state = load(STATE)
    expected = {
        "AUTHORIZATION_GRANTED": True,
        "AUTHORIZATION_CONSUMED": True,
        "CONSUMED_FOR_REUSE": True,
        "VALID_FOR_ACTIVE_EXECUTION": False,
        "EXECUTION_GATE_OPEN": False,
        "EXPERIMENT_EXECUTED": True,
        "RESTART_ALLOWED": False,
    }
    assert evidence["terminal_authorization_state"] == expected
    assert state["final_state"] == expected
    assert state["termination"]["retry_permitted"] is False
    assert state["termination"]["authorization_reusable"] is False


def test_authoritative_consumption_marker_is_retained_and_bound():
    state = load(STATE)
    marker = load(CONSUMPTION_MARKER)
    binding = state["authoritative_consumption_marker"]
    assert binding["retained_required"] is True
    assert binding["sha256"] == sha256(CONSUMPTION_MARKER)
    assert marker["result"] == "ABORT"
    assert marker["state"] == state["final_state"]


def test_spawn_failure_is_precise_and_no_runtime_success_is_invented():
    evidence = load(EVIDENCE)
    failure = evidence["failure"]
    observed = evidence["topology_and_runtime_observations"]
    scenario = evidence["required_scenario_observations"]
    assert failure["reason_code"] == "CHILD_SPAWN_SEMLOCK_REBUILD_FAILED"
    assert failure["reason_code_provenance"] == "OPERATOR_OBSERVED_EXECUTION_OUTPUT"
    assert failure["child_error_type"] == "FileNotFoundError"
    assert failure["child_errno"] == 2
    assert failure["child_failure_count"] == 2
    assert failure["operator_session_retry_observed"] is False
    assert failure["machine_proves_no_retry_attempted"] is False
    assert failure["machine_proves_second_execution_can_run"] is False
    assert failure["retry_permitted"] is False
    assert observed["child_processes_spawn_attempted"] == 2
    assert observed["agent_targets_initialized"] == 0
    assert observed["session_count_completed"] == 0
    assert observed["reconnect_count_completed"] == 0
    assert observed["session_1_agent_b_source_port"] is None
    assert observed["session_2_agent_b_source_port"] is None
    assert set(scenario.values()) == {False}


def test_provenance_classes_machine_operator_and_hypothesis_separately():
    evidence = load(EVIDENCE)
    provenance = evidence["provenance_classification"]
    marker = load(CONSUMPTION_MARKER)
    machine = provenance["persisted_machine_evidence"]
    observed = provenance["operator_observed_execution_output"]
    hypothesis = provenance["inferred_or_hypothesized_cause"]
    assert machine["result"] == marker["result"] == "ABORT"
    assert machine["controller_execution_error"] == marker["execution_error"] == "Empty:"
    assert observed["classification"] == "OPERATOR_OBSERVED_NOT_MACHINE_PERSISTED"
    assert observed["reason_code"] == "CHILD_SPAWN_SEMLOCK_REBUILD_FAILED"
    assert observed["retry_observed_in_operator_session"] is False
    assert hypothesis["status"] == "NOT_PROVEN"
    assert hypothesis["deeper_os_or_multiprocessing_root_cause_claimed"] is False
    assert provenance["raw_stderr_retained_or_hash_bound"] is False


def test_missing_timing_and_port_evidence_is_explicit():
    evidence = load(EVIDENCE)
    timing = evidence["timing"]
    limits = evidence["evidence_limitations"]
    assert timing["start_time_utc"] is None
    assert timing["active_duration_seconds"] is None
    assert timing["exact_start_and_duration_persisted_by_runner"] is False
    assert timing["maximum_active_duration_seconds"] == 60
    assert limits["exact_start_time_unavailable"] is True
    assert limits["exact_duration_unavailable"] is True
    assert limits["ephemeral_ports_unavailable_because_no_session_established"] is True
    assert limits["runtime_replay_or_option_a_success_must_not_be_claimed"] is True
    assert limits["semlock_traceback_is_machine_persisted"] is False
    assert limits["no_retry_attempt_is_machine_proven"] is False


def test_cleanup_is_complete_and_persistent_runtime_is_absent():
    cleanup = load(EVIDENCE)["cleanup"]
    assert cleanup == {
        "cleanup_success": True,
        "sockets_closed": True,
        "processes_terminated": True,
        "child_processes_remaining": 0,
        "startup_supervisors_remaining": 0,
        "port_28428_free": True,
        "temporary_state_removed": True,
        "persistent_runtime_created": False,
        "errors": [],
    }


def test_no_unauthorized_state_or_authority_is_claimed():
    evidence = load(EVIDENCE)
    state_invariants = evidence["state_invariants"]
    authority = evidence["authority_invariants"]
    assert set(state_invariants.values()) == {False}
    assert set(authority.values()) == {False}
    assert evidence["topology_and_runtime_observations"]["external_network_used"] is False
    assert evidence["evidence_limitations"]["public_testnet_or_production_readiness_claimed"] is False


def test_protocol_validator_and_protected_facts_are_unchanged():
    protected = load(EVIDENCE)["protected_invariants"]
    assert protected["protocol_version"] == "1.0.0"
    assert protected["protocol_sha256"] == sha256(PROTOCOL)
    assert protected["canonical_validator"] == "coin.tx_validation.validate_transaction"
    assert protected["tx_validation_sha256"] == sha256(VALIDATOR)
    assert protected["hard_cap"] == 28000000
    assert protected["emission_ceiling"] == 11130000
    assert protected["historically_mined"] == 2824584
    assert protected["treasury_locked"] == 500000
    assert protected["circulating_snapshot"] == 2324584
    assert protected["halving_interval"] == 210000
    assert protected["reward_schedule"] == [28, 14, 7, 3, 1, 0]
    assert protected["historical_mined_through_entry"] == 100877
    assert protected["next_canonical_height"] == 100878


def test_f37_statuses_do_not_advance():
    reassessment = load(EVIDENCE)["f37_reassessment"]
    assert reassessment == {
        "foundation159_advancement": False,
        "F37-07": "PARTIAL_ISOLATED_LOOPBACK_TRANSPORT_EVIDENCE",
        "F37-10": "PARTIAL_ISOLATED_LOOPBACK_PROPAGATION_EVIDENCE",
        "F37-11": "OFFLINE_OPTION_A_REVIEWED_NON_NORMATIVE",
        "runtime_network_testnet_or_production_authority_granted": False,
    }


def test_future_execution_requires_entirely_new_authority_chain():
    requirements = load(EVIDENCE)["future_authority_requirements"]
    assert requirements == {
        "NEW_AUTHORIZATION_REQUIRED": True,
        "SEPARATE_SECURITY_REVIEW_REQUIRED": True,
        "SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED": True,
        "F159_RETRY_FORBIDDEN": True,
        "F157_F158_F159_CONSUMPTION_STATE_REUSABLE": False,
    }
    assert load(STATE)["future_authority_requirements"] == requirements


def test_json_artifacts_have_no_duplicate_keys():
    def reject(pairs):
        result = {}
        for key, value in pairs:
            assert key not in result, f"duplicate key: {key}"
            result[key] = value
        return result

    for path in (EVIDENCE, STATE, CONSUMPTION_MARKER):
        json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject)
