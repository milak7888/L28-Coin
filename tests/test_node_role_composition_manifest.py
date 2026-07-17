from __future__ import annotations

import ast
import copy
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

from coin import node_role_composition_manifest as composition
from coin import node_role_model as model
from coin import node_role_scenario as scenario
from coin import node_role_scenario_suite as suite
from coin import node_role_scenario_suite_cli as suite_cli
from coin import node_role_scenario_suite_evidence as evidence
from coin import node_role_scenario_suite_evidence_cli as evidence_cli
from coin import node_role_transcript as transcript


def _json(value: object, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _scenario(role: str, requested_states: list[str]) -> dict[str, object]:
    return {
        "scenario_version": scenario.SCENARIO_VERSION,
        "model_version": model.MODEL_VERSION,
        "transcript_version": transcript.TRANSCRIPT_VERSION,
        "role": role,
        "requested_states": requested_states,
    }


def _canonical_suite() -> dict[str, object]:
    core_sequences = [
        [
            "CANONICAL_READY_RESERVED",
            "RUNNING_RESERVED",
            "EVIDENCE_ONLY",
            "PAUSED",
            "STOPPED",
        ],
        ["DISPOSABLE_TEST_READY", "PAUSED", "STOPPED"],
        ["PAUSED", "STOPPED"],
        ["FAILED", "STOPPED"],
        ["EVIDENCE_ONLY", "FAILED", "STOPPED"],
        ["DISPOSABLE_TEST_READY", "FAILED", "STOPPED"],
        ["PAUSED", "FAILED", "STOPPED"],
    ]
    p2p_sequences = [
        ["LISTENING_RESERVED", "CONFIGURED", "PAUSED", "STOPPED"],
        ["PAUSED", "STOPPED"],
        ["FAILED", "STOPPED"],
        ["CONFIGURED", "FAILED", "STOPPED"],
        ["PAUSED", "FAILED", "STOPPED"],
    ]
    cases: list[dict[str, object]] = []
    for index, states in enumerate(core_sequences):
        cases.append(
            {"case_id": f"core-{index}", "scenario": _scenario(model.CORE_ROLE, states)}
        )
    for index, states in enumerate(p2p_sequences):
        cases.append(
            {"case_id": f"p2p-{index}", "scenario": _scenario(model.P2P_ROLE, states)}
        )
    return {
        "suite_version": suite.SUITE_VERSION,
        "scenario_version": scenario.SCENARIO_VERSION,
        "model_version": model.MODEL_VERSION,
        "transcript_version": transcript.TRANSCRIPT_VERSION,
        "cases": cases,
    }


def _valid_evidence() -> dict[str, object]:
    suite_value = _canonical_suite()
    suite_result = suite.verify_scenario_suite_json(_json(suite_value))
    if not suite_result.ok:
        raise AssertionError(suite_result.code)
    return {
        "evidence_version": evidence.EVIDENCE_VERSION,
        "suite": suite_value,
        "report": suite_cli.build_report(suite_result),
    }


def _components() -> list[dict[str, object]]:
    return [
        {
            "component_id": "core-primary",
            "role": model.CORE_ROLE,
            "initial_state": "CREATED",
            "trust": "native_policy_coordinator",
            "owns": [
                "lifecycle_policy",
                "native_validation_coordination",
                "issuance_readiness_policy",
                "persistence_authorization",
                "checkpoint_admission_policy",
            ],
            "prohibited": [
                "network_listen",
                "network_connect",
                "peer_discovery",
                "participant_signing",
                "wallet_custody",
                "automatic_historical_state_discovery",
                "automatic_canonical_designation",
                "automatic_creator_reward_routing",
            ],
        },
        {
            "component_id": "p2p-boundary",
            "role": model.P2P_ROLE,
            "initial_state": "CREATED",
            "trust": "untrusted_transport_boundary",
            "owns": [
                "bounded_frame_decoding",
                "peer_session_policy",
                "peer_replay_policy",
                "candidate_forwarding",
                "transport_pause_and_shutdown",
            ],
            "prohibited": [
                "native_ledger_mutation",
                "mint_authorization",
                "issued_supply_change",
                "checkpoint_canonicalization",
                "core_decision_override",
                "participant_signing",
                "wallet_custody",
                "private_historical_state_loading",
                "wrapped_asset_identity_substitution",
            ],
        },
    ]


def _trust_boundaries() -> list[dict[str, object]]:
    return [
        {
            "id": "peer_to_p2p",
            "input_trust": "untrusted",
            "required_controls": [
                "predecode_size_limit",
                "deterministic_decode",
                "network_and_protocol_binding",
                "peer_identity_evidence",
                "nonce_and_replay_validation",
                "timestamp_and_expiry_validation",
            ],
        },
        {
            "id": "p2p_to_core",
            "input_trust": "normalized_but_untrusted",
            "required_controls": [
                "immutable_candidate_projection",
                "native_transaction_validation",
                "signature_verification",
                "issuance_and_supply_invariants",
                "checkpoint_policy_when_applicable",
                "no_transport_decision_override",
            ],
        },
        {
            "id": "core_to_persistence",
            "input_trust": "validated_candidate_only",
            "required_controls": [
                "atomic_commit_boundary",
                "deterministic_identity",
                "replay_state_consistency",
                "failure_before_partial_mutation",
                "auditable_result",
            ],
        },
        {
            "id": "checkpoint_to_core",
            "input_trust": "untrusted_evidence",
            "required_controls": [
                "explicit_caller_supplied_input",
                "duplicate_key_rejection",
                "schema_and_version_validation",
                "hash_size_and_count_commitments",
                "parent_graph_and_supply_checks",
                "enforced_provenance",
                "separate_canonical_authorization",
            ],
        },
    ]


def _valid_manifest() -> dict[str, object]:
    evidence_value = _valid_evidence()
    evidence_result = evidence.verify_scenario_suite_evidence_json(
        _json(evidence_value)
    )
    if not evidence_result.ok:
        raise AssertionError(evidence_result.code)
    return {
        "manifest_version": composition.MANIFEST_VERSION,
        "security_profile": {
            "profile_version": composition.SECURITY_PROFILE_VERSION,
            "sha256": composition.SECURITY_PROFILE_SHA256,
        },
        "components": _components(),
        "trust_boundaries": _trust_boundaries(),
        "runtime_configuration": {
            "endpoints": [],
            "listeners": [],
            "peers": [],
            "credentials": [],
            "automatic_discovery": False,
            "activation_authorized": False,
        },
        "evidence": evidence_value,
        "evidence_report": evidence_cli.build_report(evidence_result),
    }


class NodeRoleCompositionManifestTests(unittest.TestCase):
    def test_canonical_manifest_is_valid_and_bound(self) -> None:
        manifest = _valid_manifest()
        result = composition.verify_node_role_composition_manifest_json(
            _json(manifest)
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "manifest_valid")
        self.assertEqual(result.manifest_sha256, composition.compute_composition_manifest_sha256(manifest))
        self.assertEqual(result.security_profile_sha256, composition.SECURITY_PROFILE_SHA256)
        self.assertEqual(result.evidence_report_id, manifest["evidence_report"]["report_id"])
        self.assertEqual(result.component_ids, ("core-primary", "p2p-boundary"))
        self.assertEqual(result.roles, (model.CORE_ROLE, model.P2P_ROLE))
        self.assertEqual(result.trust_boundary_ids, tuple(item["id"] for item in _trust_boundaries()))

    def test_profile_declarations_are_exact(self) -> None:
        self.assertEqual(composition.SECURITY_PROFILE_VERSION, "l28-core-p2p-security/v0.1")
        self.assertEqual(
            composition.SECURITY_PROFILE_SHA256,
            "61e787f9f665d76a704d5e6dca8bccc6a80bb3ed231ac741fb5b7497383b04f6",
        )
        self.assertEqual(set(composition.ROLE_DECLARATIONS), {model.CORE_ROLE, model.P2P_ROLE})
        self.assertEqual(set(composition.TRUST_BOUNDARY_DECLARATIONS), {
            "peer_to_p2p", "p2p_to_core", "core_to_persistence", "checkpoint_to_core"
        })

    def test_canonical_sha256_matches_public_algorithm(self) -> None:
        manifest = _valid_manifest()
        canonical = json.dumps(
            manifest,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(
            composition.compute_composition_manifest_sha256(manifest),
            hashlib.sha256(canonical).hexdigest(),
        )

    def test_semantically_identical_formatting_is_deterministic(self) -> None:
        manifest = _valid_manifest()
        compact = composition.verify_node_role_composition_manifest_json(_json(manifest))
        pretty = composition.verify_node_role_composition_manifest_json(_json(manifest, pretty=True))
        self.assertTrue(compact.ok)
        self.assertEqual(compact, pretty)

    def test_semantic_mutation_changes_manifest_commitment(self) -> None:
        first = _valid_manifest()
        second = copy.deepcopy(first)
        second["components"][0]["component_id"] = "core-secondary"
        first_result = composition.verify_node_role_composition_manifest_json(_json(first))
        second_result = composition.verify_node_role_composition_manifest_json(_json(second))
        self.assertTrue(first_result.ok and second_result.ok)
        self.assertNotEqual(first_result.manifest_sha256, second_result.manifest_sha256)

    def test_duplicate_keys_are_rejected_at_any_depth(self) -> None:
        result = composition.verify_node_role_composition_manifest_json(
            '{"manifest_version":"x","manifest_version":"y"}'
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "duplicate_key")
        nested = _json(_valid_manifest()).replace(
            '"profile_version":"l28-core-p2p-security/v0.1"',
            '"profile_version":"l28-core-p2p-security/v0.1","profile_version":"x"',
            1,
        )
        self.assertEqual(
            composition.verify_node_role_composition_manifest_json(nested).code,
            "duplicate_key",
        )

    def test_invalid_input_encoding_json_and_nonfinite_fail_closed(self) -> None:
        self.assertEqual(composition.verify_node_role_composition_manifest_json(None).code, "input_type_invalid")
        self.assertEqual(composition.verify_node_role_composition_manifest_json(b"\xff").code, "invalid_encoding")
        self.assertEqual(composition.verify_node_role_composition_manifest_json("{").code, "invalid_json")
        self.assertEqual(composition.verify_node_role_composition_manifest_json('{"x":NaN}').code, "invalid_json")
        self.assertEqual(composition.verify_node_role_composition_manifest_json("[]").code, "schema_error")

    def test_oversized_input_is_rejected_before_json_parsing(self) -> None:
        payload = b"{" + b" " * composition.MAX_MANIFEST_BYTES
        result = composition.verify_node_role_composition_manifest_json(payload)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "manifest_too_large")

    def test_top_level_schema_is_exact(self) -> None:
        for mutation in ("missing", "extra"):
            manifest = _valid_manifest()
            if mutation == "missing":
                del manifest["components"]
            else:
                manifest["unexpected"] = False
            result = composition.verify_node_role_composition_manifest_json(_json(manifest))
            self.assertFalse(result.ok)
            self.assertEqual(result.code, "schema_error")

    def test_versions_fail_closed(self) -> None:
        for value in ("wrong", 1, None):
            manifest = _valid_manifest()
            manifest["manifest_version"] = value
            result = composition.verify_node_role_composition_manifest_json(_json(manifest))
            self.assertFalse(result.ok)
            self.assertEqual(result.code, "version_unsupported")

    def test_security_profile_binding_is_exact(self) -> None:
        mutations = [
            {"profile_version": "wrong", "sha256": composition.SECURITY_PROFILE_SHA256},
            {"profile_version": composition.SECURITY_PROFILE_VERSION, "sha256": "0" * 64},
            {"profile_version": composition.SECURITY_PROFILE_VERSION},
            {"profile_version": composition.SECURITY_PROFILE_VERSION, "sha256": composition.SECURITY_PROFILE_SHA256, "extra": 1},
        ]
        for binding in mutations:
            manifest = _valid_manifest()
            manifest["security_profile"] = binding
            result = composition.verify_node_role_composition_manifest_json(_json(manifest))
            self.assertFalse(result.ok)
            self.assertEqual(result.code, "security_profile_mismatch")

    def test_exactly_one_component_per_role_is_required(self) -> None:
        manifest = _valid_manifest()
        manifest["components"] = manifest["components"][:1]
        self.assertEqual(composition.verify_node_role_composition_manifest_json(_json(manifest)).code, "component_invalid")
        manifest = _valid_manifest()
        manifest["components"][1]["role"] = model.CORE_ROLE
        self.assertEqual(composition.verify_node_role_composition_manifest_json(_json(manifest)).code, "component_invalid")

    def test_component_identifiers_are_bounded_unique_and_canonical(self) -> None:
        for value in ("", "Upper", "1core", "core space", "a" * 65):
            manifest = _valid_manifest()
            manifest["components"][0]["component_id"] = value
            self.assertEqual(composition.verify_node_role_composition_manifest_json(_json(manifest)).code, "component_invalid")
        manifest = _valid_manifest()
        manifest["components"][1]["component_id"] = manifest["components"][0]["component_id"]
        self.assertEqual(composition.verify_node_role_composition_manifest_json(_json(manifest)).code, "component_invalid")

    def test_components_must_start_created(self) -> None:
        manifest = _valid_manifest()
        manifest["components"][0]["initial_state"] = "EVIDENCE_ONLY"
        result = composition.verify_node_role_composition_manifest_json(_json(manifest))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "component_invalid")

    def test_role_trust_and_capabilities_must_match_exactly(self) -> None:
        mutations = (
            ("trust", "untrusted"),
            ("owns", ["lifecycle_policy"]),
            ("prohibited", ["network_listen"]),
        )
        for field, value in mutations:
            manifest = _valid_manifest()
            manifest["components"][0][field] = value
            result = composition.verify_node_role_composition_manifest_json(_json(manifest))
            self.assertFalse(result.ok)
            self.assertEqual(result.code, "capability_invalid")

    def test_component_schema_and_capability_duplicates_fail_closed(self) -> None:
        manifest = _valid_manifest()
        manifest["components"][0]["extra"] = False
        self.assertEqual(composition.verify_node_role_composition_manifest_json(_json(manifest)).code, "component_invalid")
        manifest = _valid_manifest()
        manifest["components"][0]["owns"].append(manifest["components"][0]["owns"][0])
        self.assertEqual(composition.verify_node_role_composition_manifest_json(_json(manifest)).code, "capability_invalid")

    def test_all_public_trust_boundaries_are_required(self) -> None:
        manifest = _valid_manifest()
        manifest["trust_boundaries"] = manifest["trust_boundaries"][:-1]
        self.assertEqual(composition.verify_node_role_composition_manifest_json(_json(manifest)).code, "trust_boundary_invalid")
        manifest = _valid_manifest()
        manifest["trust_boundaries"][3]["id"] = "peer_to_p2p"
        self.assertEqual(composition.verify_node_role_composition_manifest_json(_json(manifest)).code, "trust_boundary_invalid")

    def test_trust_boundary_values_and_controls_are_exact(self) -> None:
        manifest = _valid_manifest()
        manifest["trust_boundaries"][0]["input_trust"] = "trusted"
        self.assertEqual(composition.verify_node_role_composition_manifest_json(_json(manifest)).code, "trust_boundary_invalid")
        manifest = _valid_manifest()
        manifest["trust_boundaries"][0]["required_controls"] = ["deterministic_decode"]
        self.assertEqual(composition.verify_node_role_composition_manifest_json(_json(manifest)).code, "trust_boundary_invalid")
        manifest = _valid_manifest()
        manifest["trust_boundaries"][0]["extra"] = True
        self.assertEqual(composition.verify_node_role_composition_manifest_json(_json(manifest)).code, "trust_boundary_invalid")

    def test_runtime_configuration_must_be_exactly_inert(self) -> None:
        for field, value in (
            ("endpoints", ["127.0.0.1"]),
            ("listeners", ["tcp"]),
            ("peers", ["peer"]),
            ("credentials", ["secret"]),
            ("automatic_discovery", True),
            ("activation_authorized", True),
        ):
            manifest = _valid_manifest()
            manifest["runtime_configuration"][field] = value
            result = composition.verify_node_role_composition_manifest_json(_json(manifest))
            self.assertFalse(result.ok)
            self.assertEqual(result.code, "runtime_configuration_present")

    def test_runtime_configuration_schema_and_types_fail_closed(self) -> None:
        manifest = _valid_manifest()
        del manifest["runtime_configuration"]["peers"]
        self.assertEqual(composition.verify_node_role_composition_manifest_json(_json(manifest)).code, "runtime_configuration_present")
        manifest = _valid_manifest()
        manifest["runtime_configuration"]["automatic_discovery"] = 0
        self.assertEqual(composition.verify_node_role_composition_manifest_json(_json(manifest)).code, "runtime_configuration_present")

    def test_invalid_foundation25_evidence_is_rejected(self) -> None:
        manifest = _valid_manifest()
        manifest["evidence"]["evidence_version"] = "wrong"
        result = composition.verify_node_role_composition_manifest_json(_json(manifest))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "evidence_invalid")

    def test_foundation25_evidence_report_is_recomputed_and_bound(self) -> None:
        manifest = _valid_manifest()
        manifest["evidence_report"]["case_count"] += 1
        result = composition.verify_node_role_composition_manifest_json(_json(manifest))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "evidence_binding_invalid")
        manifest = _valid_manifest()
        manifest["evidence_report"]["report_id"] = "0" * 64
        self.assertEqual(composition.verify_node_role_composition_manifest_json(_json(manifest)).code, "evidence_binding_invalid")

    def test_evidence_and_report_must_be_objects(self) -> None:
        manifest = _valid_manifest()
        manifest["evidence"] = []
        self.assertEqual(composition.verify_node_role_composition_manifest_json(_json(manifest)).code, "evidence_invalid")
        manifest = _valid_manifest()
        manifest["evidence_report"] = []
        self.assertEqual(composition.verify_node_role_composition_manifest_json(_json(manifest)).code, "evidence_report_invalid")

    def test_result_fields_stable_codes_and_success_checks_are_explicit(self) -> None:
        result = composition.verify_node_role_composition_manifest_json(_json(_valid_manifest()))
        self.assertEqual(composition.STABLE_CODES, (
            "manifest_valid", "input_type_invalid", "manifest_too_large", "invalid_encoding",
            "invalid_json", "duplicate_key", "schema_error", "version_unsupported",
            "security_profile_mismatch", "component_invalid", "capability_invalid",
            "trust_boundary_invalid", "runtime_configuration_present", "evidence_invalid",
            "evidence_report_invalid", "evidence_binding_invalid", "internal_error",
        ))
        self.assertEqual(result.checks, composition.SUCCESS_CHECKS)
        self.assertEqual(result.manifest_version, composition.MANIFEST_VERSION)
        self.assertEqual(result.evidence_version, evidence.EVIDENCE_VERSION)
        self.assertEqual(result.evidence_report_version, evidence_cli.REPORT_VERSION)

    def test_results_are_frozen_and_input_is_not_modified(self) -> None:
        manifest = _valid_manifest()
        original = copy.deepcopy(manifest)
        result = composition.verify_node_role_composition_manifest_json(_json(manifest))
        self.assertTrue(result.ok)
        self.assertEqual(manifest, original)
        with self.assertRaises(FrozenInstanceError):
            result.code = "changed"

    def test_wrapper_matches_verifier_class(self) -> None:
        payload = _json(_valid_manifest())
        self.assertEqual(
            composition.verify_node_role_composition_manifest_json(payload),
            composition.NodeRoleCompositionManifestVerifier.verify_json(payload),
        )

    def test_internal_exception_is_sanitized(self) -> None:
        with mock.patch.object(
            composition, "_validate_evidence", side_effect=RuntimeError("private detail")
        ):
            result = composition.verify_node_role_composition_manifest_json(_json(_valid_manifest()))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "internal_error")
        self.assertEqual(result.detail, "internal verification failure")
        self.assertNotIn("private detail", result.detail)

    def test_production_module_has_no_io_or_activation_imports(self) -> None:
        path = Path(composition.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        forbidden = {
            "os", "pathlib", "socket", "subprocess", "threading", "multiprocessing",
            "sqlite3", "urllib", "http", "wallet", "ledger", "mining",
        }
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add((node.module or "").split(".")[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, {"open", "exec", "eval", "compile", "__import__"})
        self.assertTrue(imports.isdisjoint(forbidden))


if __name__ == "__main__":
    unittest.main()
