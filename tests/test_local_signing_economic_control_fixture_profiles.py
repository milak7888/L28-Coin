# SPDX-License-Identifier: Apache-2.0
"""Foundation115 deterministic family and fail-closed profile tests."""

from __future__ import annotations

import copy
import unittest

import local_signing_fixture_test_support as support


class TestLocalSigningEconomicControlFixtureProfiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = support.load_fixtures()
        cls.fx = support.by_case(cls.fixtures)

    def test_iso_future_signer_boundary_remains_inactive(self) -> None:
        pos = self.fx["LSEC-CONF-v0.1-ISO-POS-001"]
        neg = self.fx["LSEC-CONF-v0.1-ISO-NEG-001"]
        bnd = self.fx["LSEC-CONF-v0.1-ISO-BND-001"]
        fcl = self.fx["LSEC-CONF-v0.1-ISO-FCL-001"]
        self.assertEqual(pos["expected"]["signer_edge_status"], "eligible_public_projection")
        self.assertEqual(neg["input"]["case_probe"]["probe_kind"], "signer_authority_claim")
        self.assertEqual(bnd["input"]["case_probe"]["probe_kind"], "public_metadata_boundary")
        self.assertIs(fcl["input"]["policy"]["signer_boundary_authorized"], False)
        for fixture in (pos, neg, bnd, fcl):
            self.assertIs(fixture["expected"]["non_execution"]["signing_attempted"], False)
            self.assertIs(fixture["expected"]["non_execution"]["signature_created"], False)

    def test_aut_authorization_never_equals_validation(self) -> None:
        pos = self.fx["LSEC-CONF-v0.1-AUT-POS-001"]["expected"]
        neg = self.fx["LSEC-CONF-v0.1-AUT-NEG-001"]["expected"]
        bnd = self.fx["LSEC-CONF-v0.1-AUT-BND-001"]["expected"]
        fcl = self.fx["LSEC-CONF-v0.1-AUT-FCL-001"]
        self.assertEqual((pos["authorization_status"], pos["validation_status"]), ("allowed", "accepted"))
        self.assertEqual((neg["authorization_status"], neg["validation_status"]), ("allowed", "rejected"))
        self.assertEqual(neg["protocol_reason"], "insufficient_balance")
        self.assertEqual((bnd["authorization_status"], bnd["validation_status"], bnd["outcome"]), ("allowed", "pending", "blocked"))
        self.assertEqual(fcl["input"]["case_probe"]["probe_kind"], "contradictory_authority_binding")
        self.assertIs(fcl["authority_assertions"]["authorization_equals_validation"], False)

    def test_val_mandatory_delegate_and_context_boundaries(self) -> None:
        pos = self.fx["LSEC-CONF-v0.1-VAL-POS-001"]
        neg = self.fx["LSEC-CONF-v0.1-VAL-NEG-001"]
        bnd = self.fx["LSEC-CONF-v0.1-VAL-BND-001"]
        fcl = self.fx["LSEC-CONF-v0.1-VAL-FCL-001"]
        self.assertEqual(pos["input"]["protocol_validation"]["status"], "accepted")
        self.assertEqual(neg["input"]["case_probe"]["probe_kind"], "alternate_validator_override")
        self.assertEqual(bnd["input"]["intent"]["amount"], bnd["input"]["policy"]["per_transaction_limit"])
        self.assertEqual(bnd["expected"]["validation_status"], "accepted")
        validation = fcl["input"]["protocol_validation"]
        self.assertIs(validation["available"], False)
        self.assertIs(validation["invoked"], False)
        self.assertTrue(all(validation[name] is False for name in ("ledger_context_available", "consensus_context_available", "issued_supply_context_available")))
        self.assertEqual(fcl["expected"]["code"], "protocol_validation_unavailable")

    def test_key_custody_uses_disposable_public_probe_only(self) -> None:
        neg = self.fx["LSEC-CONF-v0.1-KEY-NEG-001"]
        bnd = self.fx["LSEC-CONF-v0.1-KEY-BND-001"]
        fcl = self.fx["LSEC-CONF-v0.1-KEY-FCL-001"]
        probe = neg["input"]["case_probe"]
        self.assertEqual(probe["public_marker"], support.DISPOSABLE_MARKER)
        self.assertEqual(probe["public_value"], support.DISPOSABLE_MARKER)
        self.assertNotIn(support.DISPOSABLE_MARKER, support.canonical_bytes(neg["expected"]).decode("utf-8"))
        self.assertEqual(bnd["public_identities"]["signer_public_key_id"], "fictional-public-key-id-lsec-v01")
        self.assertEqual(fcl["input"]["case_probe"]["probe_kind"], "external_custodian_assignment")
        for fixture in (neg, bnd, fcl):
            self.assertIs(fixture["expected"]["non_execution"]["wallet_accessed"], False)

    def test_lim_exact_integer_comparisons_and_unavailable_policy(self) -> None:
        pos = self.fx["LSEC-CONF-v0.1-LIM-POS-001"]["input"]
        neg1 = self.fx["LSEC-CONF-v0.1-LIM-NEG-001"]
        neg2 = self.fx["LSEC-CONF-v0.1-LIM-NEG-002"]
        bnd1 = self.fx["LSEC-CONF-v0.1-LIM-BND-001"]["input"]
        bnd2 = self.fx["LSEC-CONF-v0.1-LIM-BND-002"]["input"]
        fcl = self.fx["LSEC-CONF-v0.1-LIM-FCL-001"]
        self.assertLess(pos["intent"]["amount"], pos["policy"]["per_transaction_limit"])
        self.assertLess(pos["policy"]["prior_authorized_total"] + pos["intent"]["amount"], pos["policy"]["cumulative_limit"])
        self.assertGreater(neg1["input"]["intent"]["amount"], neg1["input"]["policy"]["per_transaction_limit"])
        self.assertEqual(neg1["expected"]["limit_status"], "exceeded")
        self.assertGreater(neg2["input"]["policy"]["prior_authorized_total"] + neg2["input"]["intent"]["amount"], neg2["input"]["policy"]["cumulative_limit"])
        self.assertEqual(bnd1["intent"]["amount"], bnd1["policy"]["per_transaction_limit"])
        self.assertEqual(bnd2["policy"]["prior_authorized_total"] + bnd2["intent"]["amount"], bnd2["policy"]["cumulative_limit"])
        self.assertIs(fcl["input"]["policy"]["available"], False)
        self.assertEqual(fcl["expected"]["limit_status"], "unavailable")
        self.assertIs(fcl["input"]["policy"]["unlimited_spend_allowed"], False)

    def test_apr_distinct_threshold_duplicate_and_unavailable_profiles(self) -> None:
        pos = self.fx["LSEC-CONF-v0.1-APR-POS-001"]
        neg1 = self.fx["LSEC-CONF-v0.1-APR-NEG-001"]
        neg2 = self.fx["LSEC-CONF-v0.1-APR-NEG-002"]
        bnd = self.fx["LSEC-CONF-v0.1-APR-BND-001"]
        fcl = self.fx["LSEC-CONF-v0.1-APR-FCL-001"]

        def distinct_count(fixture):
            return len({item["approver_id"] for item in fixture["input"]["approvals"]})

        self.assertGreater(distinct_count(pos), pos["input"]["policy"]["approval_threshold"])
        self.assertLess(distinct_count(neg1), neg1["input"]["policy"]["approval_threshold"])
        self.assertLess(distinct_count(neg2), len(neg2["input"]["approvals"]))
        self.assertEqual(neg2["input"]["case_probe"]["operation"], "duplicate")
        self.assertEqual(distinct_count(bnd), bnd["input"]["policy"]["approval_threshold"])
        self.assertIs(fcl["input"]["policy"]["available"], False)
        self.assertEqual(fcl["expected"]["approval_status"], "unavailable")

    def test_rpl_present_boundary_is_inclusive_and_read_only(self) -> None:
        pos = self.fx["LSEC-CONF-v0.1-RPL-POS-001"]
        neg = self.fx["LSEC-CONF-v0.1-RPL-NEG-001"]
        bnd = self.fx["LSEC-CONF-v0.1-RPL-BND-001"]
        fcl = self.fx["LSEC-CONF-v0.1-RPL-FCL-001"]
        self.assertEqual(pos["input"]["replay_view"]["status"], "absent")
        self.assertEqual(pos["expected"]["replay_status"], "fresh")
        self.assertEqual(neg["input"]["replay_view"]["status"], "present")
        self.assertLess(neg["fixed_clock"]["evaluation_time"], neg["input"]["replay_view"]["retention_until"])
        self.assertEqual(bnd["fixed_clock"]["evaluation_time"], bnd["input"]["replay_view"]["retention_until"])
        self.assertEqual(bnd["expected"]["code"], "replay_detected")
        self.assertIs(fcl["input"]["replay_view"]["available"], False)
        for fixture in (pos, neg, bnd, fcl):
            self.assertIs(fixture["input"]["replay_view"]["read_only"], True)
            self.assertIs(fixture["expected"]["non_execution"]["replay_state_mutated"], False)

    def test_exp_uses_fixture_time_and_exact_expiry_boundary(self) -> None:
        pos = self.fx["LSEC-CONF-v0.1-EXP-POS-001"]
        neg1 = self.fx["LSEC-CONF-v0.1-EXP-NEG-001"]
        neg2 = self.fx["LSEC-CONF-v0.1-EXP-NEG-002"]
        bnd = self.fx["LSEC-CONF-v0.1-EXP-BND-001"]
        fcl = self.fx["LSEC-CONF-v0.1-EXP-FCL-001"]
        view = pos["input"]["expiration_view"]
        now = view["evaluation_time"]
        self.assertLessEqual(view["intent_not_before"], now)
        self.assertLess(now, min(view[name] for name in ("intent_expires_at", "quote_expires_at", "payment_expires_at", "approvals_expire_at", "operator_evidence_expires_at")))
        self.assertLess(neg1["input"]["expiration_view"]["approvals_expire_at"], neg1["fixed_clock"]["evaluation_time"])
        self.assertGreater(neg2["input"]["expiration_view"]["intent_not_before"], neg2["fixed_clock"]["evaluation_time"])
        self.assertEqual(bnd["input"]["expiration_view"]["quote_expires_at"], bnd["fixed_clock"]["evaluation_time"])
        self.assertEqual(bnd["expected"]["code"], "artifact_expired")
        self.assertEqual(fcl["input"]["case_probe"]["operation"], "omit")
        for fixture in (pos, neg1, neg2, bnd, fcl):
            expiration = fixture["input"]["expiration_view"]
            self.assertEqual(expiration["clock_source"], "fixture_supplied")
            self.assertIs(expiration["system_clock_read"], False)
            self.assertIs(expiration["network_clock_read"], False)

    def test_aud_evidence_is_public_deterministic_and_non_authoritative(self) -> None:
        pos = self.fx["LSEC-CONF-v0.1-AUD-POS-001"]
        neg1 = self.fx["LSEC-CONF-v0.1-AUD-NEG-001"]
        neg2 = self.fx["LSEC-CONF-v0.1-AUD-NEG-002"]
        bnd = self.fx["LSEC-CONF-v0.1-AUD-BND-001"]
        fcl = self.fx["LSEC-CONF-v0.1-AUD-FCL-001"]
        self.assertEqual(pos["expected"]["audit_status"], "public_evidence_valid")
        self.assertEqual(neg1["input"]["receipt_audit_evidence"]["settlement_evidence_status"], "unverified_claim")
        self.assertEqual(neg2["input"]["case_probe"]["probe_kind"], "audit_execution_authority_claim")
        self.assertEqual(support.canonical_bytes(bnd["input"]), support.canonical_bytes(copy.deepcopy(bnd["input"])))
        self.assertEqual(bnd["expected"]["report_id"], support.recompute_digests(bnd)[1])
        self.assertEqual(fcl["input"]["receipt_audit_evidence"]["lineage_id"], "")
        for fixture in (pos, neg1, neg2, bnd, fcl):
            audit = fixture["input"]["receipt_audit_evidence"]
            self.assertTrue(all(audit[name] is False for name in ("claims_signature_created", "claims_broadcast", "claims_ledger_mutation", "claims_consensus_change")))

    def test_opr_exact_scope_denial_mismatch_and_unavailable_gate(self) -> None:
        pos = self.fx["LSEC-CONF-v0.1-OPR-POS-001"]
        neg1 = self.fx["LSEC-CONF-v0.1-OPR-NEG-001"]
        neg2 = self.fx["LSEC-CONF-v0.1-OPR-NEG-002"]
        bnd = self.fx["LSEC-CONF-v0.1-OPR-BND-001"]
        fcl = self.fx["LSEC-CONF-v0.1-OPR-FCL-001"]
        self.assertEqual(pos["input"]["operator_authorization"]["decision"], "approved")
        self.assertIs(pos["input"]["operator_authorization"]["scope_matches"], True)
        self.assertEqual(neg1["input"]["operator_authorization"]["decision"], "denied")
        self.assertIs(neg2["input"]["operator_authorization"]["scope_matches"], False)
        self.assertEqual(bnd["input"]["intent"]["amount"], bnd["input"]["operator_authorization"]["maximum_amount"])
        self.assertLess(bnd["fixed_clock"]["evaluation_time"], bnd["input"]["operator_authorization"]["expires_at"])
        self.assertIs(fcl["input"]["operator_authorization"]["available"], False)
        self.assertEqual(fcl["input"]["operator_authorization"]["independent_security_review_id"], "")

    def test_ext_advisory_and_bitcoin_evidence_never_gain_authority(self) -> None:
        pos = self.fx["LSEC-CONF-v0.1-EXT-POS-001"]
        neg1 = self.fx["LSEC-CONF-v0.1-EXT-NEG-001"]
        neg2 = self.fx["LSEC-CONF-v0.1-EXT-NEG-002"]
        bnd = self.fx["LSEC-CONF-v0.1-EXT-BND-001"]
        fcl = self.fx["LSEC-CONF-v0.1-EXT-FCL-001"]
        self.assertIs(pos["input"]["advisory_evidence"]["harness_evals_present"], True)
        self.assertEqual(neg1["input"]["case_probe"]["probe_kind"], "advisory_authority_claim")
        self.assertEqual(neg2["input"]["case_probe"]["probe_kind"], "bitcoin_l28_authority_claim")
        self.assertIs(bnd["input"]["advisory_evidence"]["harness_evals_present"], False)
        self.assertIs(bnd["input"]["advisory_evidence"]["bitcoin_evidence_present"], False)
        self.assertEqual(fcl["expected"]["code"], "future_security_decision_required")
        self.assertEqual(fcl["authority_assertions"]["blocked_security_decision_status"], support.BLOCKED)
        for fixture in (pos, neg1, neg2, bnd, fcl):
            evidence = fixture["input"]["advisory_evidence"]
            self.assertEqual(evidence["harness_evals_effect"], "advisory_only")
            self.assertEqual(evidence["bitcoin_effect"], "external_evidence_only")
            self.assertIs(evidence["authority_claimed"], False)
            self.assertIs(evidence["removal_changes_core_result"], False)

    def test_eco_preserves_protocol_economics_and_fails_closed(self) -> None:
        pos = self.fx["LSEC-CONF-v0.1-ECO-POS-001"]
        neg1 = self.fx["LSEC-CONF-v0.1-ECO-NEG-001"]
        neg2 = self.fx["LSEC-CONF-v0.1-ECO-NEG-002"]
        bnd = self.fx["LSEC-CONF-v0.1-ECO-BND-001"]
        fcl = self.fx["LSEC-CONF-v0.1-ECO-FCL-001"]
        self.assertEqual(pos["authority_assertions"]["protected_economic_facts"], support.PROTECTED_ECONOMICS)
        self.assertEqual(neg1["input"]["case_probe"]["probe_kind"], "protected_economic_override")
        self.assertEqual(neg2["expected"]["protocol_reason"], "reserved_sender_misuse")
        self.assertEqual(neg2["input"]["protocol_validation"]["reason"], "reserved_sender_misuse")
        self.assertEqual(bnd["input"]["policy"]["per_transaction_limit"], support.PROTECTED_ECONOMICS["hard_cap_l28"])
        validation = fcl["input"]["protocol_validation"]
        self.assertTrue(all(validation[name] is False for name in ("ledger_context_available", "consensus_context_available", "issued_supply_context_available")))
        for fixture in (pos, neg1, neg2, bnd, fcl):
            self.assertEqual(fixture["authority_assertions"]["protected_economic_facts"], support.PROTECTED_ECONOMICS)
            self.assertIs(fixture["authority_assertions"]["historical_evidence_mutable"], False)
            self.assertIs(fixture["expected"]["non_execution"]["ledger_mutated"], False)
            self.assertIs(fixture["expected"]["non_execution"]["consensus_modified"], False)

    def test_all_fail_closed_profiles_block_without_execution(self) -> None:
        fail_closed = [fixture for fixture in self.fixtures if fixture["class"] == "fail_closed"]
        self.assertEqual(len(fail_closed), 12)
        for fixture in fail_closed:
            self.assertEqual(fixture["expected"]["outcome"], "blocked")
            self.assertIs(fixture["expected"]["ok"], False)
            self.assertNotEqual(fixture["expected"]["signer_edge_status"], "eligible_public_projection")
            self.assertEqual(fixture["expected"]["non_execution"], support.NON_EXECUTION)

    def test_test_local_malformed_probes_are_deterministic_and_non_mutating(self) -> None:
        original = self.fx["LSEC-CONF-v0.1-ISO-POS-001"]
        snapshot = copy.deepcopy(original)
        results = []
        for _ in range(2):
            missing = copy.deepcopy(original)
            missing["input"].pop("replay_view")
            results.append(support.structural_code(missing))
            unknown = copy.deepcopy(original)
            unknown["input"]["case_probe"]["unexpected"] = False
            results.append(support.structural_code(unknown))
        self.assertEqual(results, ["schema_invalid"] * 4)
        self.assertEqual(original, snapshot)


if __name__ == "__main__":
    unittest.main()
