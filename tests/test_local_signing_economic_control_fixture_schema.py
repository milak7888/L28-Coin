# SPDX-License-Identifier: Apache-2.0
"""Foundation115 schema, inventory, and canonical-digest conformance tests."""

from __future__ import annotations

import copy
import json
import unittest
from collections import Counter

import local_signing_fixture_test_support as support


class TestLocalSigningEconomicControlFixtureSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = support.fixture_paths()
        cls.fixtures = support.load_fixtures()
        cls.by_case = support.by_case(cls.fixtures)

    def test_exactly_56_fixtures_and_12_families(self) -> None:
        self.assertTrue(support.FIXTURE_DIR.is_dir())
        self.assertEqual(len(self.paths), 56)
        self.assertEqual(len(self.fixtures), 56)
        self.assertEqual(
            {fixture["family"] for fixture in self.fixtures},
            {"iso", "aut", "val", "key", "lim", "apr", "rpl", "exp", "aud", "opr", "ext", "eco"},
        )

    def test_exact_section14_mapping_and_class_counts(self) -> None:
        self.assertEqual(len(support.PLANNED), 56)
        actual_cases = {fixture["case_id"] for fixture in self.fixtures}
        actual_fixture_ids = {fixture["fixture_id"] for fixture in self.fixtures}
        self.assertEqual(actual_cases, set(support.PLANNED_BY_CASE))
        self.assertEqual(actual_fixture_ids, set(support.PLANNED_BY_FIXTURE))
        counts: Counter[str] = Counter()
        for case_id, fixture_id, cls, code in support.PLANNED:
            fixture = self.by_case[case_id]
            self.assertEqual(fixture["fixture_id"], fixture_id)
            self.assertEqual(fixture["class"], support.CLASS_NAME[cls])
            self.assertEqual(fixture["expected"]["code"], code)
            self.assertEqual(fixture["expected"]["case_id"], case_id)
            self.assertEqual(fixture["expected"]["family"], fixture["family"])
            self.assertEqual(self.paths[[item["fixture_id"] for item in self.fixtures].index(fixture_id)].stem, fixture_id)
            counts[cls] += 1
        self.assertEqual(counts, support.EXPECTED_CLASS_COUNTS)

    def test_fixture_and_case_ids_are_unique_and_grammatical(self) -> None:
        fixture_ids = [fixture["fixture_id"] for fixture in self.fixtures]
        case_ids = [fixture["case_id"] for fixture in self.fixtures]
        self.assertEqual(len(set(fixture_ids)), 56)
        self.assertEqual(len(set(case_ids)), 56)
        for fixture in self.fixtures:
            case_match = support.CASE_ID_RE.fullmatch(fixture["case_id"])
            fixture_match = support.FIXTURE_ID_RE.fullmatch(fixture["fixture_id"])
            self.assertIsNotNone(case_match)
            self.assertIsNotNone(fixture_match)
            assert case_match is not None and fixture_match is not None
            self.assertEqual(case_match.group(1).lower(), fixture_match.group(1))
            self.assertEqual(case_match.group(2).lower(), fixture_match.group(2))

    def test_exact_top_level_and_nested_property_order(self) -> None:
        for fixture in self.fixtures:
            support.assert_exact_schema(fixture)

    def test_strict_loader_rejects_duplicate_properties(self) -> None:
        raw = '{"fixture_schema":"one","fixture_schema":"two"}'
        with self.assertRaises(support.DuplicateKeyError):
            support.strict_loads(raw)
        self.assertEqual(json.loads(raw)["fixture_schema"], "two")

    def test_schema_rejects_unknown_missing_and_reordered_properties(self) -> None:
        original = self.by_case["LSEC-CONF-v0.1-ISO-POS-001"]

        unknown = copy.deepcopy(original)
        unknown["unknown_property"] = "unsupported"
        self.assertEqual(support.structural_code(unknown), "schema_invalid")

        missing = copy.deepcopy(original)
        missing["input"]["policy"].pop("approval_threshold")
        self.assertEqual(support.structural_code(missing), "schema_invalid")

        reordered = copy.deepcopy(original)
        reordered["fixed_clock"] = {
            key: reordered["fixed_clock"][key]
            for key in reversed(support.ORDERS["fixed_clock"])
        }
        self.assertEqual(support.structural_code(reordered), "schema_invalid")
        self.assertEqual(original, self.by_case["LSEC-CONF-v0.1-ISO-POS-001"])

    def test_utf8_json_and_file_termination_are_deterministic(self) -> None:
        for path in self.paths:
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
            self.assertFalse(raw.endswith(b"\n\n"))
            text = raw.decode("utf-8")
            self.assertNotIn("\t", text)
            self.assertIsInstance(support.strict_loads(text), dict)

    def test_canonical_serializer_is_exact_and_order_sensitive(self) -> None:
        fixture = self.by_case["LSEC-CONF-v0.1-ISO-POS-001"]
        first = support.canonical_bytes(fixture["input"])
        second = support.canonical_bytes(copy.deepcopy(fixture["input"]))
        self.assertEqual(first, second)
        self.assertEqual(first.decode("utf-8").encode("utf-8"), first)
        self.assertNotIn(b"\n", first)
        self.assertNotIn(b'": ', first)
        self.assertNotIn(b'", ', first)
        sorted_bytes = json.dumps(
            fixture["input"],
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
        self.assertNotEqual(first, sorted_bytes)

    def test_all_three_digests_recompute_independently(self) -> None:
        for fixture in self.fixtures:
            input_digest, report_id, fixture_digest = support.recompute_digests(fixture)
            self.assertRegex(input_digest, support.HEX64)
            self.assertRegex(report_id, support.HEX64)
            self.assertRegex(fixture_digest, support.HEX64)
            self.assertEqual(fixture["canonical"]["input_sha256"], input_digest)
            self.assertEqual(fixture["expected"]["report_id"], report_id)
            self.assertEqual(fixture["canonical"]["expected_report_id"], report_id)
            self.assertEqual(fixture["canonical"]["fixture_sha256"], fixture_digest)
            self.assertEqual(fixture["canonical"]["algorithm"], "sha256-utf8-exact-order-json")
            self.assertIs(fixture["canonical"]["field_order_enforced"], True)

    def test_digest_mutation_fails_closed_without_repair(self) -> None:
        original = self.by_case["LSEC-CONF-v0.1-AUD-BND-001"]
        mutated = copy.deepcopy(original)
        mutated["input"]["intent"]["purpose"] = "changed fictional purpose"
        self.assertEqual(support.structural_code(mutated), "canonical_digest_mismatch")
        self.assertEqual(original, self.by_case["LSEC-CONF-v0.1-AUD-BND-001"])

    def test_protocol_transaction_input_digest_recomputes_when_available(self) -> None:
        for fixture in self.fixtures:
            validation = fixture["input"]["protocol_validation"]
            declared = validation["transaction_input_sha256"]
            if declared == "":
                self.assertIs(validation["available"], False)
                continue
            self.assertEqual(
                declared,
                support.sha256(fixture["input"]["intent"]["proposed_transaction"]),
            )

    def test_protected_economic_facts_are_exact(self) -> None:
        for fixture in self.fixtures:
            facts = fixture["authority_assertions"]["protected_economic_facts"]
            self.assertEqual(facts, support.PROTECTED_ECONOMICS)
            self.assertEqual(tuple(facts), support.ORDERS["protected_economic_facts"])

    def test_authority_assertions_and_override_flags_are_exact(self) -> None:
        for fixture in self.fixtures:
            authority = fixture["authority_assertions"]
            self.assertEqual(authority, support.AUTHORITY_ASSERTIONS)
            for flag in support.OVERRIDE_FLAGS:
                self.assertIs(authority[flag], False)
            self.assertIs(authority["authorization_equals_validation"], False)
            self.assertIs(authority["signer_may_override_protocol"], False)
            self.assertEqual(authority["blocked_security_decision_status"], support.BLOCKED)

    def test_authority_mutation_fails_closed(self) -> None:
        original = self.by_case["LSEC-CONF-v0.1-ECO-POS-001"]
        mutated = copy.deepcopy(original)
        mutated["authority_assertions"]["hard_cap_override_allowed"] = False
        self.assertEqual(support.structural_code(mutated), "schema_invalid")

        mutated = copy.deepcopy(original)
        mutated["authority_assertions"]["protected_economic_facts"]["hard_cap_l28"] = 28000001
        input_digest, report_id, _ = support.recompute_digests(mutated)
        mutated["canonical"]["input_sha256"] = input_digest
        mutated["canonical"]["expected_report_id"] = report_id
        mutated["expected"]["report_id"] = report_id
        fixture_copy = copy.deepcopy(mutated)
        fixture_copy["canonical"]["fixture_sha256"] = ""
        mutated["canonical"]["fixture_sha256"] = support.sha256(fixture_copy)
        self.assertEqual(support.structural_code(mutated), "authority_assertion_invalid")

    def test_all_expected_non_execution_flags_are_false(self) -> None:
        for fixture in self.fixtures:
            self.assertEqual(fixture["expected"]["non_execution"], support.NON_EXECUTION)
            self.assertTrue(
                all(value is False for value in fixture["expected"]["non_execution"].values())
            )

    def test_exact_safety_assertions_and_public_fixture_profile(self) -> None:
        for fixture in self.fixtures:
            self.assertEqual(fixture["safety_assertions"], support.SAFETY_ASSERTIONS)
            self.assertIs(fixture["safety_assertions"]["public_fictional_data_only"], True)

    def test_mandatory_validation_delegation_is_asserted_not_invoked_by_tests(self) -> None:
        for fixture in self.fixtures:
            validation = fixture["input"]["protocol_validation"]
            self.assertEqual(validation["delegate"], "coin.tx_validation.validate_transaction")
            self.assertIs(validation["invocation_required"], True)
            self.assertIs(validation["read_only"], True)
            if fixture["expected"]["outcome"] == "accept":
                self.assertIs(validation["invoked"], True)
                self.assertEqual(validation["status"], "accepted")
            if validation["status"] in {"rejected", "pending", "unavailable", "not_invoked"}:
                self.assertNotEqual(
                    fixture["expected"]["signer_edge_status"],
                    "eligible_public_projection",
                )

    def test_no_float_or_noncanonical_hash_values(self) -> None:
        for fixture in self.fixtures:
            for value in support.walk(fixture):
                self.assertNotIsInstance(value, float)
            for name in ("intent_id", "request_id"):
                self.assertRegex(fixture["input"]["intent"][name], support.HEX64)
            for name in ("input_sha256", "expected_report_id", "fixture_sha256"):
                self.assertRegex(fixture["canonical"][name], support.HEX64)


if __name__ == "__main__":
    unittest.main()
