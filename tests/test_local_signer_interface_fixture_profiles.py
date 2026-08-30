# SPDX-License-Identifier: Apache-2.0
"""Foundation121 deterministic family and case-profile tests."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from collections import Counter

import local_signer_interface_fixture_test_support as support


class TestLocalSignerInterfaceFixtureProfiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = support.load_fixtures()
        cls.fx = support.by_case(cls.fixtures)

    def test_all_18_families_and_exact_class_counts(self) -> None:
        self.assertEqual({fixture["family"].upper() for fixture in self.fixtures}, set(support.FAMILIES))
        counts = Counter(fixture["case_id"].split("-")[-2] for fixture in self.fixtures)
        self.assertEqual(counts, support.EXPECTED_CLASS_COUNTS)

    def test_case_family_and_class_fields_bind_to_ids(self) -> None:
        for fixture in self.fixtures:
            match = support.CASE_ID_RE.fullmatch(fixture["case_id"])
            assert match is not None
            self.assertEqual(fixture["family"], match.group(1).lower())
            self.assertEqual(fixture["class"], support.CLASS_NAME[match.group(2)])

    def test_public_identifiers_derive_from_fixture_id_and_exact_roles(self) -> None:
        scalar_roles = {
            "request_id": "input.request.request_id",
            "idempotency_key": "input.request.idempotency_key",
        }
        nested_roles = (
            ("authorization_evidence", "intent_id", "input.request.authorization_evidence.intent_id"),
            ("economic_policy", "policy_id", "input.request.economic_policy.policy_id"),
            ("caller_identity_evidence", "evidence_id", "input.request.caller_identity_evidence.evidence_id"),
            ("operator_authorization_evidence", "evidence_id", "input.request.operator_authorization_evidence.evidence_id"),
            ("operator_authorization_evidence", "independent_security_review_id", "input.request.operator_authorization_evidence.independent_security_review_id"),
            ("authorization_evidence", "authorization_id", "input.request.authorization_evidence.authorization_id"),
            ("replay_evidence", "evidence_id", "input.request.replay_evidence.evidence_id"),
            ("time_evidence", "evidence_id", "input.request.time_evidence.evidence_id"),
            ("protocol_validation_binding", "validation_report_id", "input.request.protocol_validation_binding.validation_report_id"),
            ("protocol_validation_binding", "ledger_context_id", "input.request.protocol_validation_binding.ledger_context_id"),
            ("protocol_validation_binding", "consensus_context_id", "input.request.protocol_validation_binding.consensus_context_id"),
            ("protocol_validation_binding", "issued_supply_context_id", "input.request.protocol_validation_binding.issued_supply_context_id"),
        )
        for fixture in self.fixtures:
            request = fixture["input"]["request"]
            for field, role in scalar_roles.items():
                self.assertEqual(request[field], support.public_id(fixture["fixture_id"], role))
            for section, field, role in nested_roles:
                self.assertEqual(request[section][field], support.public_id(fixture["fixture_id"], role))
            for index, approval in enumerate(request["approvals"]):
                role = f"input.request.approvals[{index}].approval_id"
                self.assertEqual(approval["approval_id"], support.public_id(fixture["fixture_id"], role))

    def test_fixed_fictional_identities_and_nonces_are_exact(self) -> None:
        for fixture in self.fixtures:
            self.assertEqual(fixture["public_identities"], support.PUBLIC_IDENTITIES)
            request = fixture["input"]["request"]
            self.assertEqual(request["nonce"], "lsi-fixture-envelope-nonce-001")
            self.assertEqual(request["proposed_transaction"]["nonce"], "lsi-fixture-transaction-nonce-001")
            self.assertEqual(request["proposed_transaction"]["sender"], support.PUBLIC_IDENTITIES["payer_id"])
            self.assertEqual(request["proposed_transaction"]["receiver"], support.PUBLIC_IDENTITIES["payee_id"])

    def test_baseline_fixed_clock_is_exact_and_no_clock_is_read(self) -> None:
        baseline = self.fx["LSI-CONF-v0.1-CMP-POS-001"]
        self.assertEqual(baseline["fixed_clock"], support.FIXED_CLOCK)
        for fixture in self.fixtures:
            self.assertEqual(fixture["fixed_clock"], support.FIXED_CLOCK)
            time_evidence = fixture["input"]["request"]["time_evidence"]
            self.assertIs(time_evidence["system_clock_read"], False)
            self.assertIs(time_evidence["network_clock_read"], False)

    def test_mandatory_protocol_validation_binding_is_evidence_only(self) -> None:
        for fixture in self.fixtures:
            binding = fixture["input"]["request"]["protocol_validation_binding"]
            response_binding = fixture["expected"]["response"]["validation_binding"]
            self.assertEqual(binding["delegate"], "coin.tx_validation.validate_transaction")
            self.assertEqual(response_binding["delegate"], binding["delegate"])
            self.assertIs(binding["invocation_required"], True)
            self.assertIs(binding["alternate_validator_supplied"], False)
            self.assertIs(binding["override_requested"], False)
            self.assertIs(binding["read_only"], True)
            self.assertIs(fixture["safety_assertions"]["invokes_validate_transaction"], False)

    def test_authorization_remains_distinct_from_validation(self) -> None:
        pos = self.fx["LSI-CONF-v0.1-AUT-POS-001"]["expected"]["response"]["eligibility"]
        denied = self.fx["LSI-CONF-v0.1-AUT-NEG-001"]["expected"]["response"]["eligibility"]
        pending = self.fx["LSI-CONF-v0.1-AUT-BND-001"]["expected"]["response"]["eligibility"]
        self.assertEqual((pos["authorization_status"], pos["validation_status"]), ("allowed", "accepted"))
        self.assertEqual((denied["authorization_status"], denied["validation_status"]), ("denied", "not_invoked"))
        self.assertEqual(
            self.fx["LSI-CONF-v0.1-AUT-NEG-001"]["input"]["request"]["protocol_validation_binding"]["status"],
            "accepted",
        )
        self.assertEqual((pending["authorization_status"], pending["validation_status"]), ("pending", "pending"))
        self.assertEqual(
            self.fx["LSI-CONF-v0.1-AUT-BND-001"]["input"]["request"]["authorization_evidence"]["authorization_status"],
            "allowed",
        )
        self.assertIs(self.fx["LSI-CONF-v0.1-AUT-FCL-001"]["authority_assertions"]["authorization_equals_validation"], False)

    def test_eligibility_remains_distinct_from_signer_invocation(self) -> None:
        for fixture in self.fixtures:
            eligibility = fixture["expected"]["response"]["eligibility"]
            self.assertEqual(eligibility["signer_invocation_status"], "not_invoked")
            self.assertIs(eligibility["signing_authorized"], False)
            self.assertIs(eligibility["spend_authorized"], False)
            self.assertIs(eligibility["settlement_authorized"], False)
            self.assertIs(eligibility["execution_authorized"], False)
            self.assertIs(fixture["authority_assertions"]["eligibility_equals_invocation"], False)

    def test_spending_limit_profiles_preserve_exact_integer_boundaries(self) -> None:
        per_tx = self.fx["LSI-CONF-v0.1-LIM-NEG-001"]
        cumulative = self.fx["LSI-CONF-v0.1-LIM-NEG-002"]
        boundary = self.fx["LSI-CONF-v0.1-LIM-BND-001"]
        self.assertEqual(per_tx["expected"]["code"], "per_transaction_limit_exceeded")
        self.assertEqual(cumulative["expected"]["code"], "cumulative_limit_exceeded")
        self.assertEqual(boundary["input"]["case_probe"]["probe_kind"], "limits_equal")
        for fixture in self.fixtures:
            policy = fixture["input"]["request"]["economic_policy"]
            self.assertIs(policy["unlimited_spend_allowed"], False)
            self.assertIs(policy["protocol_override_allowed"], False)
            self.assertIs(policy["runtime_authorized"], False)

    def test_approval_threshold_and_duplicate_profiles_fail_closed(self) -> None:
        below = self.fx["LSI-CONF-v0.1-APR-NEG-001"]
        duplicate = self.fx["LSI-CONF-v0.1-APR-NEG-002"]
        exact = self.fx["LSI-CONF-v0.1-APR-BND-001"]
        self.assertEqual(below["expected"]["code"], "approval_threshold_not_met")
        self.assertEqual(duplicate["expected"]["code"], "duplicate_approval")
        self.assertEqual(exact["input"]["case_probe"]["public_value"], 2)
        for fixture in self.fixtures:
            self.assertEqual(fixture["input"]["request"]["approvals"][0]["public_evidence_only"], True)

    def test_replay_evidence_is_read_only_and_unavailable_never_fresh(self) -> None:
        for fixture in self.fixtures:
            replay = fixture["input"]["request"]["replay_evidence"]
            self.assertIs(replay["read_only"], True)
            self.assertEqual(replay["atomic_transition_status"], "not_implemented")
            self.assertEqual(replay["atomicity_evidence_id"], "")
        self.assertEqual(self.fx["LSI-CONF-v0.1-RPL-NEG-001"]["expected"]["code"], "replay_detected")
        self.assertEqual(self.fx["LSI-CONF-v0.1-RPL-FCL-001"]["expected"]["code"], "replay_state_unavailable")

    def test_expiration_boundaries_and_unavailable_time_are_explicit(self) -> None:
        self.assertEqual(self.fx["LSI-CONF-v0.1-EXP-BND-001"]["expected"]["code"], "artifact_expired")
        self.assertEqual(self.fx["LSI-CONF-v0.1-EXP-BND-002"]["expected"]["status"], "eligible_public_projection")
        unavailable = self.fx["LSI-CONF-v0.1-EXP-FCL-001"]
        self.assertEqual(unavailable["expected"]["code"], "evaluation_time_unavailable")
        self.assertEqual(unavailable["input"]["case_probe"]["public_value"], "unavailable")

    def test_operator_and_authenticated_evidence_profiles_are_public_only(self) -> None:
        for fixture in self.fixtures:
            request = fixture["input"]["request"]
            for name in ("caller_identity_evidence", "operator_authorization_evidence", "authorization_evidence"):
                self.assertIs(request[name]["public_evidence_only"], True)
            for approval in request["approvals"]:
                self.assertIs(approval["public_evidence_only"], True)
        self.assertEqual(self.fx["LSI-CONF-v0.1-OPR-NEG-001"]["expected"]["code"], "operator_authorization_denied")
        self.assertEqual(self.fx["LSI-CONF-v0.1-ATH-FCL-001"]["expected"]["code"], "future_security_decision_required")

    def test_public_audit_evidence_has_no_signature_or_settlement_authority(self) -> None:
        for fixture in self.fixtures:
            audit = fixture["expected"]["response"]["public_audit_evidence"]
            self.assertIs(audit["public_evidence_only"], True)
            self.assertEqual(audit["settlement_evidence_status"], "not_supplied")
            self.assertEqual(audit["signature_evidence_status"], "not_created")
            self.assertEqual(audit["decision_code"], fixture["expected"]["code"])

    def test_case_probe_vocabulary_and_precedence_are_exact(self) -> None:
        allowed = {"none", "replace", "omit", "insert_unknown", "duplicate", "reorder", "truncate", "encode_invalid", "claim"}
        for fixture in self.fixtures:
            probe = fixture["input"]["case_probe"]
            self.assertIn(probe["operation"], allowed)
            self.assertIn(probe["expected_precedence_rank"], range(1, 18))
            if probe["operation"] == "none":
                self.assertEqual(probe["target_path"], "")
            else:
                self.assertNotEqual(probe["target_path"], "")
            self.assertIn(probe["public_marker"], {"", support.DISPOSABLE_MARKER})

    def test_fail_closed_malformed_probes_use_disposable_copies_only(self) -> None:
        original = self.fx["LSI-CONF-v0.1-SCH-POS-001"]
        before = hashlib.sha256(support.canonical_bytes(original)).hexdigest()
        missing = copy.deepcopy(original)
        missing["input"]["request"].pop("interface_profile")
        self.assertEqual(support.structural_code(missing), "schema_invalid")
        unknown = copy.deepcopy(original)
        unknown["input"]["request"]["caller_identity_evidence"]["public_unknown"] = "DISPOSABLE"
        self.assertEqual(support.structural_code(unknown), "schema_invalid")
        duplicate_raw = '{"request_id":"one","request_id":"two"}'
        with self.assertRaises(support.DuplicateKeyError):
            support.strict_loads(duplicate_raw)
        with self.assertRaises((json.JSONDecodeError, ValueError)):
            support.strict_loads('{"request_id":')
        after = hashlib.sha256(support.canonical_bytes(self.fx["LSI-CONF-v0.1-SCH-POS-001"])).hexdigest()
        self.assertEqual(before, after)

    def test_precedence_cases_keep_the_first_declared_failure(self) -> None:
        expected = {
            "LSI-CONF-v0.1-PRE-NEG-001": (9, "replay_detected"),
            "LSI-CONF-v0.1-PRE-BND-001": (1, "schema_invalid"),
            "LSI-CONF-v0.1-PRE-FCL-001": (17, "internal_failure"),
        }
        for case_id, (rank, code) in expected.items():
            fixture = self.fx[case_id]
            self.assertEqual(fixture["input"]["case_probe"]["expected_precedence_rank"], rank)
            self.assertEqual(fixture["expected"]["code"], code)


if __name__ == "__main__":
    unittest.main()
