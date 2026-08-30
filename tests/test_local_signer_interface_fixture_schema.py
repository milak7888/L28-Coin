# SPDX-License-Identifier: Apache-2.0
"""Foundation121 exact schema, inventory, and digest conformance tests."""

from __future__ import annotations

import copy
import json
import unittest
from collections import Counter

import local_signer_interface_fixture_test_support as support


class TestLocalSignerInterfaceFixtureSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = support.fixture_paths()
        cls.fixtures = support.load_fixtures()
        cls.by_case = support.by_case(cls.fixtures)
        cls.inventory = support.inventory()

    def test_exactly_100_fixture_files_and_inventory_rows(self) -> None:
        self.assertEqual(len(self.paths), 100)
        self.assertEqual(len(self.fixtures), 100)
        self.assertEqual(len(self.inventory), 100)

    def test_inventory_case_fixture_class_status_and_code_mapping(self) -> None:
        counts: Counter[str] = Counter()
        for case_id, fixture_id, case_class, status, code in self.inventory:
            fixture = self.by_case[case_id]
            self.assertEqual(fixture["fixture_id"], fixture_id)
            self.assertEqual(fixture["class"], support.CLASS_NAME[case_class])
            self.assertEqual(fixture["expected"]["status"], status)
            self.assertEqual(fixture["expected"]["code"], code)
            self.assertEqual((support.FIXTURE_DIR / f"{fixture_id}.json").stem, fixture_id)
            counts[case_class] += 1
        self.assertEqual(counts, support.EXPECTED_CLASS_COUNTS)

    def test_case_and_fixture_ids_are_unique_immutable_and_grammatical(self) -> None:
        case_ids = [fixture["case_id"] for fixture in self.fixtures]
        fixture_ids = [fixture["fixture_id"] for fixture in self.fixtures]
        self.assertEqual(len(set(case_ids)), 100)
        self.assertEqual(len(set(fixture_ids)), 100)
        for fixture in self.fixtures:
            case_match = support.CASE_ID_RE.fullmatch(fixture["case_id"])
            fixture_match = support.FIXTURE_ID_RE.fullmatch(fixture["fixture_id"])
            self.assertIsNotNone(case_match)
            self.assertIsNotNone(fixture_match)
            assert case_match is not None and fixture_match is not None
            self.assertEqual(case_match.group(1).lower(), fixture_match.group(1))
            self.assertEqual(case_match.group(2).lower(), fixture_match.group(2))
            self.assertEqual(case_match.group(3), fixture_match.group(3))

    def test_exact_top_level_and_all_nested_property_order(self) -> None:
        for fixture in self.fixtures:
            support.assert_exact_schema(fixture)

    def test_strict_loader_rejects_duplicate_properties(self) -> None:
        raw = '{"fixture_schema":"one","fixture_schema":"two"}'
        with self.assertRaises(support.DuplicateKeyError):
            support.strict_loads(raw)
        self.assertEqual(json.loads(raw)["fixture_schema"], "two")

    def test_strict_loader_rejects_floats_and_nonfinite_constants(self) -> None:
        for raw in ('{"amount":1.0}', '{"amount":NaN}', '{"amount":Infinity}'):
            with self.assertRaises(ValueError):
                support.strict_loads(raw)

    def test_schema_rejects_unknown_missing_and_reordered_fields(self) -> None:
        original = self.by_case["LSI-CONF-v0.1-SCH-POS-001"]
        unknown = copy.deepcopy(original)
        unknown["unknown_property"] = "public-disposable"
        self.assertEqual(support.structural_code(unknown), "schema_invalid")

        missing = copy.deepcopy(original)
        missing["input"]["request"]["economic_policy"].pop("approval_threshold")
        self.assertEqual(support.structural_code(missing), "schema_invalid")

        reordered = copy.deepcopy(original)
        reordered["expected"]["response"]["error"] = {
            key: reordered["expected"]["response"]["error"][key]
            for key in reversed(support.ORDERS["error"])
        }
        self.assertEqual(support.structural_code(reordered), "schema_invalid")
        self.assertEqual(original, self.by_case["LSI-CONF-v0.1-SCH-POS-001"])

    def test_utf8_json_and_file_framing_are_deterministic(self) -> None:
        for path in self.paths:
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
            self.assertFalse(raw.endswith(b"\n\n"))
            self.assertNotIn(b"\t", raw)
            self.assertIsInstance(support.strict_loads(raw.decode("utf-8")), dict)

    def test_canonical_serializer_is_compact_utf8_and_order_sensitive(self) -> None:
        request = self.by_case["LSI-CONF-v0.1-CAN-POS-001"]["input"]["request"]
        first = support.canonical_bytes(request)
        second = support.canonical_bytes(copy.deepcopy(request))
        self.assertEqual(first, second)
        self.assertEqual(first.decode("utf-8").encode("utf-8"), first)
        self.assertNotIn(b"\n", first)
        self.assertNotIn(b'": ', first)
        sorted_bytes = json.dumps(request, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False).encode()
        self.assertNotEqual(first, sorted_bytes)

    def test_all_nine_declared_digests_recompute_independently(self) -> None:
        for fixture in self.fixtures:
            recomputed = support.recompute_digests(fixture)
            for name, value in recomputed.items():
                self.assertRegex(value, support.HEX64, (fixture["fixture_id"], name))
                self.assertEqual(fixture["canonical"][name], value)
            self.assertEqual(fixture["input"]["request"]["request_digest"], recomputed["request_digest"])
            self.assertEqual(fixture["input"]["request"]["protocol_validation_binding"]["transaction_input_sha256"], recomputed["transaction_input_sha256"])
            self.assertEqual(fixture["input"]["request"]["protocol_validation_binding"]["binding_digest"], recomputed["validation_binding_digest"])
            response = fixture["expected"]["response"]
            self.assertEqual(response["public_audit_evidence"]["audit_id"], recomputed["expected_audit_id"])
            self.assertEqual(response["public_audit_evidence"]["eligibility_receipt_id"], recomputed["expected_eligibility_receipt_id"])
            self.assertEqual(response["report_id"], recomputed["expected_report_id"])

    def test_digest_mutations_fail_closed_without_repair(self) -> None:
        original = self.by_case["LSI-CONF-v0.1-CAN-POS-001"]
        mutated = copy.deepcopy(original)
        mutated["input"]["request"]["nonce"] = "changed-public-nonce"
        self.assertEqual(support.structural_code(mutated), "canonical_digest_mismatch")
        self.assertEqual(original, self.by_case["LSI-CONF-v0.1-CAN-POS-001"])

    def test_schema_and_interface_constants_are_exact(self) -> None:
        for fixture in self.fixtures:
            self.assertEqual(fixture["fixture_schema"], "l28-local-signer-interface-fixture/v0.1")
            self.assertEqual(fixture["fixture_spec_version"], "local-signer-interface-fixture-spec/v0.1")
            self.assertEqual(fixture["plan_version"], "local-signer-interface-conformance-plan/v0.1")
            self.assertEqual(fixture["interface_profile"], "l28-local-signer-interface/v0.1")
            request = fixture["input"]["request"]
            self.assertEqual((request["interface_profile"], request["interface_version"], request["operation"]), ("l28-local-signer-interface/v0.1", "0.1", "evaluate_signer_eligibility"))
            self.assertEqual(fixture["canonical"]["algorithm"], "sha256-utf8-exact-order-json")
            self.assertIs(fixture["canonical"]["field_order_enforced"], True)

    def test_response_status_code_and_error_binding_is_exact(self) -> None:
        for fixture in self.fixtures:
            expected = fixture["expected"]
            response = expected["response"]
            self.assertEqual(response["code"], expected["code"])
            self.assertEqual(response["design_status"], "DEFINED_DESIGN_ONLY")
            if expected["status"] == "eligible_public_projection":
                self.assertIs(response["ok"], True)
                self.assertEqual(response["eligibility"]["eligibility_status"], "eligible_public_projection")
                self.assertTrue(all(value == "" for value in response["error"].values()))
            else:
                self.assertIs(response["ok"], False)
                self.assertEqual(response["error"]["code"], expected["code"])
                wanted = "blocked" if expected["status"] == "blocked" else "not_evaluated"
                self.assertEqual(response["eligibility"]["eligibility_status"], wanted)


if __name__ == "__main__":
    unittest.main()
