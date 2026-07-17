from __future__ import annotations

import ast
import copy
from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

from coin import node_role_model as model
from coin import node_role_scenario as scenario
from coin import node_role_scenario_suite as suite
from coin import node_role_transcript as transcript


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
            {
                "case_id": f"core-{index}",
                "scenario": _scenario(model.CORE_ROLE, states),
            }
        )
    for index, states in enumerate(p2p_sequences):
        cases.append(
            {
                "case_id": f"p2p-{index}",
                "scenario": _scenario(model.P2P_ROLE, states),
            }
        )

    return {
        "suite_version": suite.SUITE_VERSION,
        "scenario_version": scenario.SCENARIO_VERSION,
        "model_version": model.MODEL_VERSION,
        "transcript_version": transcript.TRANSCRIPT_VERSION,
        "cases": cases,
    }


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


class NodeRoleScenarioSuiteTests(unittest.TestCase):
    def test_canonical_suite_is_valid_and_complete(self) -> None:
        result = suite.verify_scenario_suite_json(_json(_canonical_suite()))

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "suite_valid")
        self.assertEqual(result.case_count, 12)
        self.assertEqual(result.roles, (model.CORE_ROLE, model.P2P_ROLE))
        self.assertEqual(len(result.core_covered_transitions), 11)
        self.assertEqual(len(result.p2p_covered_transitions), 8)
        self.assertEqual(result.core_missing_transitions, ())
        self.assertEqual(result.p2p_missing_transitions, ())
        self.assertEqual(result.core_missing_reserved_rejections, ())
        self.assertEqual(result.p2p_missing_reserved_rejections, ())
        self.assertEqual(result.checks, suite.SUCCESS_CHECKS)

    def test_suite_sha256_matches_public_canonical_algorithm(self) -> None:
        value = _canonical_suite()
        expected = hashlib.sha256(_json(value).encode("utf-8")).hexdigest()

        result = suite.verify_scenario_suite_json(_json(value, pretty=True))

        self.assertTrue(result.ok)
        self.assertEqual(result.suite_sha256, expected)

    def test_semantically_identical_formatting_is_deterministic(self) -> None:
        value = _canonical_suite()
        compact = suite.verify_scenario_suite_json(_json(value))
        pretty = suite.verify_scenario_suite_json(_json(value, pretty=True))

        self.assertEqual(compact, pretty)

    def test_semantic_mutation_changes_suite_commitment(self) -> None:
        original = _canonical_suite()
        mutated = copy.deepcopy(original)
        mutated["cases"][0]["scenario"]["requested_states"].insert(0, "UNKNOWN")

        original_result = suite.verify_scenario_suite_json(_json(original))
        mutated_result = suite.verify_scenario_suite_json(_json(mutated))

        self.assertTrue(original_result.ok)
        self.assertTrue(mutated_result.ok)
        self.assertNotEqual(original_result.suite_sha256, mutated_result.suite_sha256)

    def test_duplicate_keys_are_rejected_at_any_depth(self) -> None:
        compact = _json(_canonical_suite())
        top_level = compact.replace(
            '"suite_version":"l28-node-role-scenario-suite/v0.1"',
            '"suite_version":"l28-node-role-scenario-suite/v0.1",'
            '"suite_version":"l28-node-role-scenario-suite/v0.1"',
            1,
        )
        nested = compact.replace(
            '"role":"CoreL28Node"',
            '"role":"CoreL28Node","role":"CoreL28Node"',
            1,
        )

        for payload in (top_level, nested):
            with self.subTest(payload=payload[:80]):
                result = suite.verify_scenario_suite_json(payload)
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "duplicate_key")

    def test_invalid_json_encoding_nonfinite_and_input_type_are_rejected(self) -> None:
        cases = (
            ("{", "invalid_json"),
            ('{"value":NaN}', "invalid_json"),
            (b"\xff", "invalid_encoding"),
            (123, "input_type_invalid"),
        )

        for payload, code in cases:
            with self.subTest(code=code):
                result = suite.verify_scenario_suite_json(payload)
                self.assertFalse(result.ok)
                self.assertEqual(result.code, code)

    def test_oversized_input_is_rejected_before_parsing(self) -> None:
        payload = b" " * (suite.MAX_SUITE_BYTES + 1)
        result = suite.verify_scenario_suite_json(payload)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "suite_too_large")

    def test_missing_extra_and_wrongly_typed_fields_fail_schema(self) -> None:
        missing = _canonical_suite()
        del missing["cases"]
        extra = _canonical_suite()
        extra["extra"] = False
        wrong_top = []
        wrong_cases = _canonical_suite()
        wrong_cases["cases"] = "not-an-array"

        for value in (missing, extra, wrong_top, wrong_cases):
            with self.subTest(value_type=type(value).__name__):
                result = suite.verify_scenario_suite_json(_json(value))
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "schema_error")

    def test_versions_fail_closed(self) -> None:
        fields_and_values = (
            ("suite_version", "l28-node-role-scenario-suite/v9"),
            ("scenario_version", "l28-node-role-scenario/v9"),
            ("model_version", "l28-node-role-model/v9"),
            ("transcript_version", "l28-node-role-transcript/v9"),
        )

        for field_name, value in fields_and_values:
            mutated = _canonical_suite()
            mutated[field_name] = value
            with self.subTest(field=field_name):
                result = suite.verify_scenario_suite_json(_json(mutated))
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "version_unsupported")

        wrong_type = _canonical_suite()
        wrong_type["suite_version"] = 1
        result = suite.verify_scenario_suite_json(_json(wrong_type))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "schema_error")

    def test_empty_excessive_and_maximum_case_counts(self) -> None:
        empty = _canonical_suite()
        empty["cases"] = []
        excessive = _canonical_suite()
        excessive["cases"] = [
            {
                "case_id": f"case-{index}",
                "scenario": _scenario(model.CORE_ROLE, ["PAUSED", "STOPPED"]),
            }
            for index in range(suite.MAX_CASES + 1)
        ]

        for value in (empty, excessive):
            result = suite.verify_scenario_suite_json(_json(value))
            self.assertFalse(result.ok)
            self.assertEqual(result.code, "case_count_invalid")

        maximum = _canonical_suite()
        originals = copy.deepcopy(maximum["cases"])
        maximum["cases"] = []
        for index in range(suite.MAX_CASES):
            item = copy.deepcopy(originals[index % len(originals)])
            item["case_id"] = f"case-{index}"
            maximum["cases"].append(item)

        result = suite.verify_scenario_suite_json(_json(maximum))
        self.assertTrue(result.ok)
        self.assertEqual(result.case_count, suite.MAX_CASES)

    def test_case_identifiers_are_bounded_unique_and_explicit(self) -> None:
        invalid_values = ("", "contains space", "x" * 65, True, 7)

        for invalid in invalid_values:
            mutated = _canonical_suite()
            mutated["cases"][0]["case_id"] = invalid
            with self.subTest(case_id=invalid):
                result = suite.verify_scenario_suite_json(_json(mutated))
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "case_id_invalid")

        duplicate = _canonical_suite()
        duplicate["cases"][1]["case_id"] = duplicate["cases"][0]["case_id"]
        result = suite.verify_scenario_suite_json(_json(duplicate))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "duplicate_case_id")

        invalid_fields = _canonical_suite()
        invalid_fields["cases"][0]["extra"] = None
        result = suite.verify_scenario_suite_json(_json(invalid_fields))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "schema_error")

    def test_both_roles_are_required(self) -> None:
        value = _canonical_suite()
        value["cases"] = [
            item for item in value["cases"]
            if item["scenario"]["role"] == model.CORE_ROLE
        ]

        result = suite.verify_scenario_suite_json(_json(value))

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "role_coverage_incomplete")

    def test_every_allowed_transition_is_required(self) -> None:
        mutations = (
            ("core-5", "DISPOSABLE_TEST_READY->FAILED"),
            ("p2p-3", "CONFIGURED->FAILED"),
        )

        for removed_case, missing_transition in mutations:
            value = _canonical_suite()
            value["cases"] = [
                item for item in value["cases"]
                if item["case_id"] != removed_case
            ]
            with self.subTest(case=removed_case):
                result = suite.verify_scenario_suite_json(_json(value))
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "transition_coverage_incomplete")
                missing = (
                    result.core_missing_transitions
                    if removed_case.startswith("core")
                    else result.p2p_missing_transitions
                )
                self.assertIn(missing_transition, missing)

    def test_every_reserved_state_rejection_is_required(self) -> None:
        core_missing = _canonical_suite()
        core_missing["cases"][0]["scenario"]["requested_states"] = [
            "EVIDENCE_ONLY",
            "PAUSED",
            "STOPPED",
        ]
        p2p_missing = _canonical_suite()
        p2p_missing["cases"][7]["scenario"]["requested_states"] = [
            "CONFIGURED",
            "PAUSED",
            "STOPPED",
        ]

        for value in (core_missing, p2p_missing):
            result = suite.verify_scenario_suite_json(_json(value))
            self.assertFalse(result.ok)
            self.assertEqual(result.code, "reserved_coverage_incomplete")

    def test_invalid_or_incomplete_scenario_fails_closed(self) -> None:
        value = _canonical_suite()
        value["cases"][0]["scenario"]["requested_states"] = ["PAUSED"]

        result = suite.verify_scenario_suite_json(_json(value))

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "scenario_failed")
        self.assertEqual(result.detail, "scenario_case_failed")

    def test_scenario_result_commitments_are_rechecked(self) -> None:
        value = _canonical_suite()
        scenario_bytes = _json(value["cases"][0]["scenario"]).encode("utf-8")
        original = scenario.NodeRoleScenarioRunner.run_json(scenario_bytes)
        mutations = (
            replace(original, scenario_sha256="0" * 64),
            replace(original, transcript_verification_code="internal_error"),
            replace(original, final_state="PAUSED"),
        )

        for mutated_result in mutations:
            with self.subTest(mutation=mutated_result):
                with mock.patch.object(
                    suite.NodeRoleScenarioRunner,
                    "run_json",
                    return_value=mutated_result,
                ):
                    result = suite.verify_scenario_suite_json(_json(value))
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "scenario_failed")

    def test_internal_exception_is_sanitized(self) -> None:
        with mock.patch.object(suite, "_parse", side_effect=RuntimeError("secret")):
            result = suite.verify_scenario_suite_json(_json(_canonical_suite()))

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "internal_error")
        self.assertEqual(result.detail, "internal_failure")
        self.assertNotIn("secret", result.detail)

    def test_results_are_frozen_and_input_is_not_modified(self) -> None:
        value = _canonical_suite()
        original = copy.deepcopy(value)
        result = suite.verify_scenario_suite_json(_json(value))

        self.assertEqual(value, original)
        self.assertTrue(result.ok)
        with self.assertRaises(FrozenInstanceError):
            result.code = "changed"
        with self.assertRaises(FrozenInstanceError):
            result.cases[0].case_id = "changed"

    def test_result_fields_and_stable_codes_are_explicit(self) -> None:
        self.assertEqual(len(suite.STABLE_CODES), len(set(suite.STABLE_CODES)))
        self.assertEqual(
            suite.STABLE_CODES,
            (
                "suite_valid",
                "input_type_invalid",
                "suite_too_large",
                "invalid_encoding",
                "invalid_json",
                "duplicate_key",
                "schema_error",
                "version_unsupported",
                "case_count_invalid",
                "case_id_invalid",
                "duplicate_case_id",
                "scenario_failed",
                "role_coverage_incomplete",
                "transition_coverage_incomplete",
                "reserved_coverage_incomplete",
                "internal_error",
            ),
        )
        self.assertEqual(
            [field.name for field in fields(suite.NodeRoleScenarioCaseResult)],
            [
                "case_id",
                "ok",
                "code",
                "role",
                "final_state",
                "request_count",
                "scenario_sha256",
                "transcript_sha256",
                "covered_transitions",
                "reserved_rejections",
            ],
        )
        self.assertEqual(
            [field.name for field in fields(suite.NodeRoleScenarioSuiteResult)],
            [
                "ok",
                "code",
                "case_count",
                "roles",
                "suite_sha256",
                "core_covered_transitions",
                "core_missing_transitions",
                "p2p_covered_transitions",
                "p2p_missing_transitions",
                "core_reserved_rejections",
                "core_missing_reserved_rejections",
                "p2p_reserved_rejections",
                "p2p_missing_reserved_rejections",
                "cases",
                "checks",
                "detail",
                "suite_version",
                "scenario_version",
                "model_version",
                "transcript_version",
                "verifier_version",
            ],
        )

    def test_production_module_has_no_io_or_activation_imports(self) -> None:
        path = Path(suite.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        banned_imports = {
            "asyncio",
            "http",
            "multiprocessing",
            "os",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "threading",
            "urllib",
        }
        imports: set[str] = set()
        banned_calls = {
            "connect",
            "listen",
            "mkdir",
            "open",
            "read_bytes",
            "read_text",
            "unlink",
            "write_bytes",
            "write_text",
        }
        calls: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)

        self.assertFalse(imports & banned_imports)
        self.assertFalse(calls & banned_calls)


if __name__ == "__main__":
    unittest.main()
