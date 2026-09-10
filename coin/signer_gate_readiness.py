# SPDX-License-Identifier: Apache-2.0
"""F177 custody-decision inventory and F171 composite reassessment.

Importing this module is inert. It never signs, loads keys, starts a runtime,
and never calls coin.tx_validation.validate_transaction. Unresolved CUS
decisions cannot become RESOLVED or PASS. Eligibility is not signer invocation.
Authorization is not Protocol validation.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

from coin.signer_custody_evidence import (
    BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS,
    EVIDENCE_COMPLETE,
    UNRESOLVED_DECISIONS,
)
from coin.signer_fault_recovery_evidence import (
    BLOCKED_BY_FAULT_RECOVERY_GAPS,
    FAULT_COMPLETE,
)
from coin.signer_runtime_hardening_evidence import (
    BLOCKED_BY_RUNTIME_HARDENING_GAPS,
    HARDENING_COMPLETE,
)


PROFILE = "l28-signer-gate-readiness/v0.1"
GATE_BLOCKED = "GATE_READINESS_BLOCKED"
GATE_INVALID = "GATE_READINESS_INVALID"

CLAIMED_RESOLVED = frozenset(
    {
        "RESOLVED",
        "APPROVED",
        "PASS",
        "COMPLETE",
        "ELIGIBLE",
        "ELIGIBLE_FOR_FUTURE_SIGNER_AUTHORIZATION_REVIEW",
        "CANDIDATE_APPROVED",
        "OPERATOR_APPROVED",
        EVIDENCE_COMPLETE,
        HARDENING_COMPLETE,
        FAULT_COMPLETE,
    }
)

RECORDED_POLICY = {
    "LSOD-CUS-002": "none",
    "KEY_GENERATION_PERMITTED": False,
    "KEY_IMPORT_PERMITTED": False,
    "LSOD-CUS-008": "backup prohibited",
    "BACKUP_PERMITTED": False,
    "LSOD-CUS-012": "A",
    "CUSTODY_EVIDENCE_SCOPE": "PUBLIC_NON_SECRET_ONLY",
}

# Classifications preserved from F126 / operator register. None are approvals.
CUS_DECISION_INVENTORY = {
    "LSOD-CUS-001": {
        "decision_id": "LSOD-CUS-001",
        "current_status": "UNRESOLVED",
        "decision_class": "SECURITY_EXPERT_DECISION_REQUIRED",
        "dependencies": ("LSOD-EVD-001", "LSOD-CUS-002", "LSOD-CUS-003"),
        "candidate_options": (
            "A_single_narrowly_versioned_signing_profile",
            "B_small_explicit_multi_profile_allowlist",
            "C_standards_compatible_profile_plus_migration_successor",
        ),
        "required_public_evidence": (
            "cryptographic_threat_model",
            "compatibility_vectors",
            "public_identifier_tests",
            "lifecycle_migration_review",
        ),
        "required_tests": (
            "public_identifier_binding_tests",
            "lifecycle_migration_review_tests",
        ),
        "known_gaps": (
            "no_algorithm_selected",
            "no_material_form_selected",
            "no_provider_selected",
        ),
        "activation_authority": False,
    },
    "LSOD-CUS-003": {
        "decision_id": "LSOD-CUS-003",
        "current_status": "UNRESOLVED",
        "decision_class": "SECURITY_EXPERT_DECISION_REQUIRED",
        "dependencies": ("LSOD-CUS-001", "LSOD-CUS-004", "LSOD-OPS-007"),
        "candidate_options": (
            "A_dedicated_isolated_software_process",
            "B_hardware_backed_isolated_boundary",
            "C_offline_ceremony_boundary",
        ),
        "required_public_evidence": (
            "attacker_model",
            "capability_map",
            "attestation_evidence",
            "export_bypass_tests",
            "fault_recovery_review",
        ),
        "required_tests": ("export_bypass_tests", "fault_recovery_review_tests"),
        "known_gaps": ("no_isolation_class_selected", "no_provider_selected"),
        "activation_authority": False,
    },
    "LSOD-CUS-004": {
        "decision_id": "LSOD-CUS-004",
        "current_status": "UNRESOLVED",
        "decision_class": "SECURITY_EXPERT_DECISION_REQUIRED",
        "dependencies": ("LSOD-EVD-003", "LSOD-EVD-007", "LSOD-CUS-003", "LSOD-CUS-005"),
        "candidate_options": (
            "A_fixed_separate_roles",
            "B_threshold_controlled_sensitive_ceremonies",
            "C_risk_tiered_role_threshold_profiles",
        ),
        "required_public_evidence": (
            "organizational_threat_model",
            "role_independence_evidence",
            "threshold_rationale",
            "collusion_availability_tests",
        ),
        "required_tests": ("collusion_availability_tests", "role_independence_tests"),
        "known_gaps": ("no_roles_selected", "no_thresholds_selected"),
        "activation_authority": False,
    },
    "LSOD-CUS-005": {
        "decision_id": "LSOD-CUS-005",
        "current_status": "UNRESOLVED",
        "decision_class": "SECURITY_EXPERT_DECISION_REQUIRED",
        "dependencies": ("LSOD-CUS-002", "LSOD-CUS-004", "LSOD-CUS-011", "LSOD-OPS-002"),
        "candidate_options": (
            "A_fixed_deterministic_checklist_with_witness",
            "B_threshold_workflow_with_ordered_approvals",
            "C_prepare_approve_execute_ceremony",
        ),
        "required_public_evidence": (
            "ceremony_threat_model",
            "exact_state_machine",
            "partial_abort_tests",
            "evidence_durability",
        ),
        "required_tests": ("partial_abort_tests", "evidence_durability_tests"),
        "known_gaps": ("no_ceremony_topology_selected",),
        "activation_authority": False,
    },
    "LSOD-CUS-006": {
        "decision_id": "LSOD-CUS-006",
        "current_status": "UNRESOLVED",
        "decision_class": "SECURITY_EXPERT_DECISION_REQUIRED",
        "dependencies": (
            "LSOD-CUS-001",
            "LSOD-CUS-005",
            "LSOD-CUS-007",
            "LSOD-OPS-001",
            "LSOD-STA-002",
        ),
        "candidate_options": (
            "A_hard_cutover_no_overlap",
            "B_bounded_overlap_tied_to_generation",
            "C_successor_prepublication_then_atomic_activation",
        ),
        "required_public_evidence": (
            "concurrency_model",
            "rotation_schedules",
            "boundary_tests",
            "rollback_recovery_review",
        ),
        "required_tests": ("boundary_tests", "rollback_recovery_review_tests"),
        "known_gaps": ("no_transition_design_selected", "numeric_durations_not_selected"),
        "activation_authority": False,
    },
    "LSOD-CUS-007": {
        "decision_id": "LSOD-CUS-007",
        "current_status": "UNRESOLVED",
        "decision_class": "SECURITY_EXPERT_DECISION_REQUIRED",
        "dependencies": (
            "LSOD-CUS-004",
            "LSOD-CUS-006",
            "LSOD-CUS-010",
            "LSOD-OPS-001",
            "LSOD-OPS-002",
        ),
        "candidate_options": (
            "A_dedicated_custody_revocation_authority",
            "B_threshold_emergency_revocation",
            "C_automated_quarantine_then_human_revocation",
        ),
        "required_public_evidence": (
            "incident_threat_model",
            "trigger_evidence",
            "freshness_latency_measurement",
            "concurrent_use_tests",
        ),
        "required_tests": ("concurrent_use_tests", "freshness_latency_tests"),
        "known_gaps": ("no_revocation_authority_selected", "no_trigger_design_selected"),
        "activation_authority": False,
    },
    "LSOD-CUS-009": {
        "decision_id": "LSOD-CUS-009",
        "current_status": "UNRESOLVED",
        "decision_class": "IMPLEMENTATION_EVIDENCE_REQUIRED_FIRST",
        "dependencies": ("LSOD-CUS-003", "LSOD-CUS-004", "LSOD-CUS-008", "LSOD-OPS-002"),
        "candidate_options": (
            "A_technology_native_verified_destruction",
            "B_cryptographic_erasure_plus_inventory",
            "C_physical_media_sanitization_plus_verification",
        ),
        "required_public_evidence": (
            "selected_technology_evidence",
            "copy_inventory",
            "destruction_assurance",
            "verification_method",
        ),
        "required_tests": ("failed_destruction_tests", "inventory_reconciliation_tests"),
        "known_gaps": (
            "custody_architecture_not_implemented",
            "copy_inventory_unavailable",
            "destruction_method_not_selectable_yet",
        ),
        "activation_authority": False,
    },
    "LSOD-CUS-010": {
        "decision_id": "LSOD-CUS-010",
        "current_status": "UNRESOLVED",
        "decision_class": "SECURITY_EXPERT_DECISION_REQUIRED",
        "dependencies": (
            "LSOD-CUS-004",
            "LSOD-CUS-006",
            "LSOD-CUS-007",
            "LSOD-CUS-011",
            "LSOD-OPS-006",
        ),
        "candidate_options": (
            "A_immediate_automatic_quarantine",
            "B_human_confirmed_quarantine",
            "C_tiered_suspected_confirmed_states",
        ),
        "required_public_evidence": (
            "incident_scenarios",
            "detection_evidence",
            "response_recovery_exercises",
            "privacy_legal_review",
        ),
        "required_tests": ("response_recovery_exercises", "non_invocable_quarantine_tests"),
        "known_gaps": ("no_compromise_response_policy_selected",),
        "activation_authority": False,
    },
    "LSOD-CUS-011": {
        "decision_id": "LSOD-CUS-011",
        "current_status": "UNRESOLVED",
        "decision_class": "SECURITY_EXPERT_DECISION_REQUIRED",
        "dependencies": (
            "LSOD-EVD-001",
            "LSOD-EVD-003",
            "LSOD-CUS-006",
            "LSOD-CUS-007",
            "LSOD-OPS-002",
        ),
        "candidate_options": (
            "A_signed_short_lived_public_custody_status",
            "B_public_digest_plus_protected_detail",
            "C_independently_attested_custody_status",
        ),
        "required_public_evidence": (
            "evidence_threat_model",
            "proof_design",
            "cadence_data",
            "privacy_review",
        ),
        "required_tests": ("stale_forged_revoked_tests", "freshness_tests"),
        "known_gaps": ("no_proof_cadence_design_selected",),
        "activation_authority": False,
    },
}

SECRET_KEYS = frozenset(
    {
        "private_key",
        "privkey",
        "seed",
        "seed_phrase",
        "mnemonic",
        "xprv",
        "secret",
        "password",
        "token",
        "wallet_credential",
        "rpc_user",
        "rpc_password",
        "rpc_cookie",
        "key_material",
        "key_bytes",
        "key_path",
        "keystore_path",
        "wallet_path",
        "hsm_slot",
        "kms_key",
        "pem",
        "der",
    }
)


class SignerGateReadinessError(ValueError):
    """Fail-closed signer-gate readiness error; does not repair input."""


def canonical_bytes(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def evidence_digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _contains_secret(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str) and key.lower() in SECRET_KEYS:
                return True
            if _contains_secret(value):
                return True
    elif isinstance(node, (list, tuple)):
        return any(_contains_secret(item) for item in node)
    elif isinstance(node, str) and node.lower() in SECRET_KEYS:
        return True
    return False


def _public_inventory():
    inventory = {}
    for decision_id in UNRESOLVED_DECISIONS:
        record = deepcopy(CUS_DECISION_INVENTORY[decision_id])
        record["dependencies"] = list(record["dependencies"])
        record["candidate_options"] = list(record["candidate_options"])
        record["required_public_evidence"] = list(record["required_public_evidence"])
        record["required_tests"] = list(record["required_tests"])
        record["known_gaps"] = list(record["known_gaps"])
        record["activation_authority"] = False
        inventory[decision_id] = record
    return inventory


def evaluate_cus_decision_readiness(evidence=None):
    """Return public CUS readiness inventory. Unresolved decisions stay unresolved."""

    snapshot = deepcopy(evidence) if evidence is not None else {}
    if evidence is not None and not isinstance(evidence, dict):
        return {
            "result": GATE_INVALID,
            "reason": "schema_invalid",
            "inventory": _public_inventory(),
            "CUSTODY_READINESS": "UNRESOLVED",
            "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
            "activation_authority": False,
            "NOT_INDEPENDENTLY_AUDITED": True,
        }
    if _contains_secret(snapshot):
        return {
            "result": GATE_INVALID,
            "reason": "secret_material_forbidden",
            "inventory": _public_inventory(),
            "CUSTODY_READINESS": "UNRESOLVED",
            "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
            "activation_authority": False,
            "NOT_INDEPENDENTLY_AUDITED": True,
        }

    claimed = snapshot.get("decision_overrides")
    if isinstance(claimed, dict):
        for decision_id in UNRESOLVED_DECISIONS:
            status = claimed.get(decision_id)
            if status in CLAIMED_RESOLVED:
                return {
                    "result": GATE_INVALID,
                    "reason": "unresolved_cus_decision_claimed_resolved",
                    "field": decision_id,
                    "inventory": _public_inventory(),
                    "CUSTODY_READINESS": "UNRESOLVED",
                    "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
                    "activation_authority": False,
                    "NOT_INDEPENDENTLY_AUDITED": True,
                }

    inventory = _public_inventory()
    for decision_id, record in inventory.items():
        if record["current_status"] in CLAIMED_RESOLVED:
            return {
                "result": GATE_INVALID,
                "reason": "unresolved_cus_decision_claimed_resolved",
                "field": decision_id,
                "inventory": _public_inventory(),
                "CUSTODY_READINESS": "UNRESOLVED",
                "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
                "activation_authority": False,
                "NOT_INDEPENDENTLY_AUDITED": True,
            }
        if record["activation_authority"] is True:
            return {
                "result": GATE_INVALID,
                "reason": "activation_authority_forbidden",
                "field": decision_id,
                "inventory": _public_inventory(),
                "CUSTODY_READINESS": "UNRESOLVED",
                "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
                "activation_authority": False,
                "NOT_INDEPENDENTLY_AUDITED": True,
            }

    return {
        "result": GATE_BLOCKED,
        "reason": "required_custody_decisions_unresolved",
        "inventory": inventory,
        "recorded_policy": dict(RECORDED_POLICY),
        "unresolved_decisions": list(UNRESOLVED_DECISIONS),
        "CUSTODY_READINESS": "UNRESOLVED",
        "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
        "activation_authority": False,
        "KEY_GENERATION_PERMITTED": False,
        "KEY_IMPORT_PERMITTED": False,
        "BACKUP_PERMITTED": False,
        "NOT_INDEPENDENTLY_AUDITED": True,
        "evidence_digest": evidence_digest(inventory),
    }


def committed_reassessment_inputs():
    return {
        "f172_production_audit_backend": "RESOLVED",
        "f173_production_time_backend": "RESOLVED",
        "f176_custody_evidence_result": BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS,
        "f177_runtime_hardening_result": BLOCKED_BY_RUNTIME_HARDENING_GAPS,
        "f177_fault_recovery_result": BLOCKED_BY_FAULT_RECOVERY_GAPS,
        "authorization_equals_validation": False,
        "eligibility_equals_invocation": False,
    }


def reassess_signer_gate(inputs=None):
    """Composite F171 reassessment. Never returns ELIGIBLE from schema validity."""

    if inputs is None:
        snapshot = committed_reassessment_inputs()
    elif not isinstance(inputs, dict):
        return {
            "result": GATE_INVALID,
            "reason": "schema_invalid",
            "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
            "CUSTODY_READINESS": "UNRESOLVED",
            "RUNTIME_HARDENING": "UNRESOLVED",
            "FAULT_RECOVERY": "UNRESOLVED",
            "authorization_equals_validation": False,
            "eligibility_equals_invocation": False,
            "NOT_INDEPENDENTLY_AUDITED": True,
        }
    else:
        snapshot = deepcopy(inputs)

    if _contains_secret(snapshot):
        return {
            "result": GATE_INVALID,
            "reason": "secret_material_forbidden",
            "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
            "CUSTODY_READINESS": "UNRESOLVED",
            "RUNTIME_HARDENING": "UNRESOLVED",
            "FAULT_RECOVERY": "UNRESOLVED",
            "authorization_equals_validation": False,
            "eligibility_equals_invocation": False,
            "NOT_INDEPENDENTLY_AUDITED": True,
        }

    if snapshot.get("authorization_equals_validation") is True:
        return {
            "result": GATE_INVALID,
            "reason": "authorization_equals_validation_forbidden",
            "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
            "CUSTODY_READINESS": "UNRESOLVED",
            "RUNTIME_HARDENING": "UNRESOLVED",
            "FAULT_RECOVERY": "UNRESOLVED",
            "authorization_equals_validation": False,
            "eligibility_equals_invocation": False,
            "NOT_INDEPENDENTLY_AUDITED": True,
        }
    if snapshot.get("eligibility_equals_invocation") is True:
        return {
            "result": GATE_INVALID,
            "reason": "eligibility_equals_invocation_forbidden",
            "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
            "CUSTODY_READINESS": "UNRESOLVED",
            "RUNTIME_HARDENING": "UNRESOLVED",
            "FAULT_RECOVERY": "UNRESOLVED",
            "authorization_equals_validation": False,
            "eligibility_equals_invocation": False,
            "NOT_INDEPENDENTLY_AUDITED": True,
        }

    cus = evaluate_cus_decision_readiness()
    unresolved = []
    if snapshot.get("f172_production_audit_backend") != "RESOLVED":
        unresolved.append("f172_production_audit_backend")
    if snapshot.get("f173_production_time_backend") != "RESOLVED":
        unresolved.append("f173_production_time_backend")
    custody_result = snapshot.get("f176_custody_evidence_result")
    if custody_result in CLAIMED_RESOLVED:
        return {
            "result": GATE_INVALID,
            "reason": "custody_readiness_overclaim",
            "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
            "CUSTODY_READINESS": "UNRESOLVED",
            "RUNTIME_HARDENING": "UNRESOLVED",
            "FAULT_RECOVERY": "UNRESOLVED",
            "authorization_equals_validation": False,
            "eligibility_equals_invocation": False,
            "NOT_INDEPENDENTLY_AUDITED": True,
        }
    if custody_result != BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS:
        unresolved.append("f176_custody_evidence_result")
    else:
        unresolved.append("CUSTODY_READINESS")
    if snapshot.get("f177_runtime_hardening_result") != BLOCKED_BY_RUNTIME_HARDENING_GAPS:
        if snapshot.get("f177_runtime_hardening_result") in CLAIMED_RESOLVED:
            return {
                "result": GATE_INVALID,
                "reason": "runtime_hardening_overclaim",
                "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
                "CUSTODY_READINESS": "UNRESOLVED",
                "RUNTIME_HARDENING": "UNRESOLVED",
                "FAULT_RECOVERY": "UNRESOLVED",
                "authorization_equals_validation": False,
                "eligibility_equals_invocation": False,
                "NOT_INDEPENDENTLY_AUDITED": True,
            }
        unresolved.append("f177_runtime_hardening_result")
    else:
        unresolved.append("RUNTIME_HARDENING")
    if snapshot.get("f177_fault_recovery_result") != BLOCKED_BY_FAULT_RECOVERY_GAPS:
        if snapshot.get("f177_fault_recovery_result") in CLAIMED_RESOLVED:
            return {
                "result": GATE_INVALID,
                "reason": "fault_recovery_overclaim",
                "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
                "CUSTODY_READINESS": "UNRESOLVED",
                "RUNTIME_HARDENING": "UNRESOLVED",
                "FAULT_RECOVERY": "UNRESOLVED",
                "authorization_equals_validation": False,
                "eligibility_equals_invocation": False,
                "NOT_INDEPENDENTLY_AUDITED": True,
            }
        unresolved.append("f177_fault_recovery_result")
    else:
        unresolved.append("FAULT_RECOVERY")
    unresolved.extend(cus["unresolved_decisions"])

    return {
        "result": GATE_BLOCKED,
        "reason": "required_dependencies_unresolved",
        "unresolved_dependencies": unresolved,
        "cus_inventory": cus["inventory"],
        "recorded_policy": dict(RECORDED_POLICY),
        "F172_PRODUCTION_AUDIT_BACKEND": snapshot.get("f172_production_audit_backend"),
        "F173_PRODUCTION_TIME_BACKEND": snapshot.get("f173_production_time_backend"),
        "F176_PUBLIC_CUSTODY_EVIDENCE_BOUNDARY": "IMPLEMENTED",
        "F176_CUSTODY_EVIDENCE_RESULT": custody_result,
        "F177_RUNTIME_HARDENING_EVIDENCE_BOUNDARY": "IMPLEMENTED",
        "F177_FAULT_RECOVERY_EVIDENCE_BOUNDARY": "IMPLEMENTED",
        "CUSTODY_READINESS": "UNRESOLVED",
        "RUNTIME_HARDENING": "UNRESOLVED",
        "FAULT_RECOVERY": "UNRESOLVED",
        "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
        "authorization_equals_validation": False,
        "eligibility_equals_invocation": False,
        "SIGNER_RUNTIME_ACTIVE": False,
        "SIGNING": False,
        "BROADCAST": False,
        "SETTLEMENT": False,
        "KEY_GENERATION_PERMITTED": False,
        "KEY_IMPORT_PERMITTED": False,
        "BACKUP_PERMITTED": False,
        "ASSURANCE_MODEL": "OPEN_SOURCE_PUBLIC_REVIEW",
        "NOT_INDEPENDENTLY_AUDITED": True,
        "evidence_digest": evidence_digest(
            {
                "inputs": snapshot,
                "unresolved": unresolved,
            }
        ),
    }
