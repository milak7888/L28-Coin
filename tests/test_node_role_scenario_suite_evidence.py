from __future__ import annotations

import ast
import copy
import dataclasses
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

from coin import node_role_model as model
from coin import node_role_scenario as scenario
from coin import node_role_scenario_suite as suite
from coin import node_role_scenario_suite_cli as suite_cli
from coin import node_role_scenario_suite_evidence as evidence
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
        cases.append({
            "case_id": f"core-{index}",
            "scenario": _scenario(model.CORE_ROLE, states),
        })
    for index, states in enumerate(p2p_sequences):
        cases.append({
            "case_id": f"p2p-{index}",
            "scenario": _scenario(model.P2P_ROLE, states),
        })

    return {
        "suite_version": suite.SUITE_VERSION,
        "scenario_version": scenario.SCENARIO_VERSION,
        "model_version": model.MODEL_VERSION,
        "transcript_version": transcript.TRANSCRIPT_VERSION,
        "cases": cases,
    }


def _json(value: object, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _valid_evidence() -> tuple[dict[str, object], suite.NodeRoleScenarioSuiteResult]:
    suite_value = _canonical_suite()
    suite_result = suite.verify_scenario_suite_json(_json(suite_value))
    if not suite_result.ok:
        raise AssertionError(suite_result)
    report = suite_cli.build_report(suite_result)
    value: dict[str, object] = {
        "evidence_version": evidence.EVIDENCE_VERSION,
        "suite": suite_value,
        "report": report,
    }
    return value, suite_result


class NodeRoleScenarioSuiteEvidenceTests(unittest.TestCase):
    def test_canonical_evidence_is_valid_and_complete(self) -> None:
        value, suite_result = _valid_evidence()
        result = evidence.verify_scenario_suite_evidence_json(_json(value))

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "evidence_valid")
        self.assertEqual(result.case_count, 12)
        self.assertEqual(result.roles, tuple(suite_result.roles))
        self.assertEqual(result.core_transition_count, 11)
        self.assertEqual(result.p2p_transition_count, 8)
        self.assertEqual(result.core_reserved_rejection_count, 2)
        self.assertEqual(result.p2p_reserved_rejection_count, 1)
        self.assertEqual(result.suite_sha256, suite_result.suite_sha256)
        self.assertEqual(result.report_id, value["report"]["report_id"])
        self.assertEqual(result.checks, evidence.SUCCESS_CHECKS)
        self.assertEqual(result.detail, "")

    def test_evidence_sha256_matches_public_canonical_algorithm(self) -> None:
        value, _ = _valid_evidence()
        result = evidence.verify_scenario_suite_evidence_json(_json(value, pretty=True))
        self.assertTrue(result.ok)
        self.assertEqual(result.evidence_sha256, _canonical_sha256(value))

    def test_semantically_identical_formatting_is_deterministic(self) -> None:
        value, _ = _valid_evidence()
        compact = evidence.verify_scenario_suite_evidence_json(_json(value))
        pretty = evidence.verify_scenario_suite_evidence_json(_json(value, pretty=True))
        reordered = evidence.verify_scenario_suite_evidence_json(
            json.dumps(value, ensure_ascii=False, allow_nan=False)
        )
        self.assertEqual(compact, pretty)
        self.assertEqual(compact, reordered)

    def test_wrapper_matches_public_function(self) -> None:
        value, _ = _valid_evidence()
        payload = _json(value)
        self.assertEqual(
            evidence.NodeRoleScenarioSuiteEvidenceVerifier.verify_json(payload),
            evidence.verify_scenario_suite_evidence_json(payload),
        )

    def test_duplicate_keys_are_rejected_at_any_depth(self) -> None:
        value, _ = _valid_evidence()
        payload = _json(value)
        duplicate_top = payload[:-1] + ',"report":{}]'
        duplicate_top = duplicate_top[:-1] + "}"
        result = evidence.verify_scenario_suite_evidence_json(duplicate_top)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "duplicate_key")

        nested = payload.replace(
            '"evidence_version":',
            '"evidence_version":"duplicate","evidence_version":',
            1,
        )
        result = evidence.verify_scenario_suite_evidence_json(nested)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "duplicate_key")

    def test_invalid_json_encoding_nonfinite_and_input_types_are_rejected(self) -> None:
        cases = [
            (None, "input_type_invalid"),
            (bytearray(b"{}"), "input_type_invalid"),
            (b"\xff", "invalid_encoding"),
            ("{", "invalid_json"),
            ('{"value":NaN}', "invalid_json"),
            ('{"value":Infinity}', "invalid_json"),
            ("[]", "schema_error"),
        ]
        for payload, expected_code in cases:
            with self.subTest(payload=payload, expected_code=expected_code):
                result = evidence.verify_scenario_suite_evidence_json(payload)  # type: ignore[arg-type]
                self.assertFalse(result.ok)
                self.assertEqual(result.code, expected_code)

    def test_oversized_input_is_rejected_before_json_parsing(self) -> None:
        payload = b" " * (evidence.MAX_EVIDENCE_BYTES + 1)
        with mock.patch.object(evidence.json, "loads") as loads:
            result = evidence.verify_scenario_suite_evidence_json(payload)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "evidence_too_large")
        loads.assert_not_called()

    def test_top_level_schema_is_exact_and_fail_closed(self) -> None:
        valid, _ = _valid_evidence()
        mutations = []

        missing = copy.deepcopy(valid)
        missing.pop("report")
        mutations.append(missing)

        extra = copy.deepcopy(valid)
        extra["extra"] = False
        mutations.append(extra)

        wrong_suite = copy.deepcopy(valid)
        wrong_suite["suite"] = []
        mutations.append(wrong_suite)

        wrong_report = copy.deepcopy(valid)
        wrong_report["report"] = []
        mutations.append(wrong_report)

        for value in mutations:
            with self.subTest(value=value):
                result = evidence.verify_scenario_suite_evidence_json(_json(value))
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "schema_error")

    def test_evidence_version_type_and_value_fail_closed(self) -> None:
        valid, _ = _valid_evidence()
        for version, expected_code in (
            (1, "schema_error"),
            ("l28-node-role-scenario-suite-evidence/v9", "version_unsupported"),
        ):
            value = copy.deepcopy(valid)
            value["evidence_version"] = version
            result = evidence.verify_scenario_suite_evidence_json(_json(value))
            self.assertFalse(result.ok)
            self.assertEqual(result.code, expected_code)

    def test_invalid_or_incomplete_suite_is_rejected(self) -> None:
        value, _ = _valid_evidence()
        suite_value = value["suite"]
        assert isinstance(suite_value, dict)
        cases = suite_value["cases"]
        assert isinstance(cases, list)
        cases.pop()

        result = evidence.verify_scenario_suite_evidence_json(_json(value))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "suite_invalid")

    def test_valid_suite_semantic_change_breaks_report_binding(self) -> None:
        value, _ = _valid_evidence()
        suite_value = value["suite"]
        assert isinstance(suite_value, dict)
        cases = suite_value["cases"]
        assert isinstance(cases, list)
        first_case = cases[0]
        assert isinstance(first_case, dict)
        first_case["case_id"] = "core-renamed"

        result = evidence.verify_scenario_suite_evidence_json(_json(value))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "suite_report_mismatch")

    def test_report_missing_extra_and_wrongly_typed_fields_fail_schema(self) -> None:
        valid, _ = _valid_evidence()
        mutations = []

        missing = copy.deepcopy(valid)
        missing["report"].pop("checks")
        mutations.append(missing)

        extra = copy.deepcopy(valid)
        extra["report"]["extra"] = True
        mutations.append(extra)

        wrong_ok = copy.deepcopy(valid)
        wrong_ok["report"]["ok"] = 1
        mutations.append(wrong_ok)

        wrong_count = copy.deepcopy(valid)
        wrong_count["report"]["case_count"] = True
        mutations.append(wrong_count)

        wrong_roles = copy.deepcopy(valid)
        wrong_roles["report"]["roles"] = "CoreL28Node"
        mutations.append(wrong_roles)

        for value in mutations:
            with self.subTest(value=value):
                result = evidence.verify_scenario_suite_evidence_json(_json(value))
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "report_schema_invalid")

    def test_report_identifier_shape_and_commitment_are_enforced(self) -> None:
        valid, _ = _valid_evidence()

        malformed = copy.deepcopy(valid)
        malformed["report"]["report_id"] = "not-a-hash"
        result = evidence.verify_scenario_suite_evidence_json(_json(malformed))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "report_schema_invalid")

        tampered = copy.deepcopy(valid)
        original_id = tampered["report"]["report_id"]
        tampered["report"]["report_id"] = "0" * 64
        if original_id == "0" * 64:
            tampered["report"]["report_id"] = "1" * 64
        result = evidence.verify_scenario_suite_evidence_json(_json(tampered))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "report_id_invalid")

    def test_recomputed_false_report_claim_is_rejected(self) -> None:
        valid, _ = _valid_evidence()
        report = valid["report"]
        assert isinstance(report, dict)
        report["detail"] = "false-but-self-consistent-claim"
        report["report_id"] = suite_cli.compute_report_id(report)

        result = evidence.verify_scenario_suite_evidence_json(_json(valid))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "suite_report_mismatch")

    def test_recomputed_suite_hash_claim_is_rejected(self) -> None:
        valid, _ = _valid_evidence()
        report = valid["report"]
        assert isinstance(report, dict)
        report["suite_sha256"] = "0" * 64
        report["report_id"] = suite_cli.compute_report_id(report)

        result = evidence.verify_scenario_suite_evidence_json(_json(valid))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "suite_report_mismatch")

    def test_coverage_is_rechecked_after_suite_verification(self) -> None:
        valid, canonical = _valid_evidence()
        altered = dataclasses.replace(
            canonical,
            core_covered_transitions=canonical.core_covered_transitions[:-1],
            core_missing_transitions=("CREATED->EVIDENCE_ONLY",),
        )
        valid["report"] = suite_cli.build_report(altered)

        with mock.patch.object(
            evidence.suite_core,
            "verify_scenario_suite_json",
            return_value=altered,
        ):
            result = evidence.verify_scenario_suite_evidence_json(_json(valid))

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "coverage_invalid")
        self.assertEqual(result.detail, "transition_coverage_incomplete")

    def test_reserved_rejection_coverage_is_rechecked(self) -> None:
        valid, canonical = _valid_evidence()
        altered = dataclasses.replace(
            canonical,
            core_reserved_rejections=(),
            core_missing_reserved_rejections=("CANONICAL_READY_RESERVED",),
        )
        valid["report"] = suite_cli.build_report(altered)

        with mock.patch.object(
            evidence.suite_core,
            "verify_scenario_suite_json",
            return_value=altered,
        ):
            result = evidence.verify_scenario_suite_evidence_json(_json(valid))

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "coverage_invalid")
        self.assertEqual(result.detail, "reserved_coverage_incomplete")

    def test_terminal_case_evidence_is_rechecked(self) -> None:
        valid, canonical = _valid_evidence()
        first = dataclasses.replace(canonical.cases[0], final_state="PAUSED")
        altered = dataclasses.replace(
            canonical,
            cases=(first,) + canonical.cases[1:],
        )
        valid["report"] = suite_cli.build_report(altered)

        with mock.patch.object(
            evidence.suite_core,
            "verify_scenario_suite_json",
            return_value=altered,
        ):
            result = evidence.verify_scenario_suite_evidence_json(_json(valid))

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "terminal_evidence_invalid")
        self.assertEqual(result.detail, "case_not_terminal")

    def test_results_are_frozen_and_input_is_not_modified(self) -> None:
        value, _ = _valid_evidence()
        original = copy.deepcopy(value)
        result = evidence.verify_scenario_suite_evidence_json(_json(value))
        self.assertTrue(result.ok)
        self.assertEqual(value, original)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.code = "changed"  # type: ignore[misc]

    def test_internal_exception_is_sanitized(self) -> None:
        value, _ = _valid_evidence()
        with mock.patch.object(
            evidence.suite_core,
            "verify_scenario_suite_json",
            side_effect=RuntimeError("private-secret-path"),
        ):
            result = evidence.verify_scenario_suite_evidence_json(_json(value))

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "internal_error")
        self.assertEqual(result.detail, "internal_failure")
        self.assertNotIn("private-secret-path", repr(result))

    def test_stable_codes_and_success_checks_are_explicit(self) -> None:
        self.assertEqual(len(evidence.STABLE_CODES), len(set(evidence.STABLE_CODES)))
        self.assertEqual(
            evidence.STABLE_CODES,
            (
                "evidence_valid",
                "input_type_invalid",
                "evidence_too_large",
                "invalid_encoding",
                "invalid_json",
                "duplicate_key",
                "schema_error",
                "version_unsupported",
                "suite_invalid",
                "report_schema_invalid",
                "report_id_invalid",
                "suite_report_mismatch",
                "coverage_invalid",
                "terminal_evidence_invalid",
                "internal_error",
            ),
        )
        self.assertEqual(len(evidence.SUCCESS_CHECKS), len(set(evidence.SUCCESS_CHECKS)))

    def test_production_module_has_no_io_or_activation_imports(self) -> None:
        path = Path(evidence.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        forbidden = {
            "asyncio",
            "http",
            "os",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        }
        imported = {
            alias.name.split(".")[0]
            for node in tree.body
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertTrue(imported.isdisjoint(forbidden))

        forbidden_calls = {
            "open",
            "exec",
            "eval",
            "compile",
            "connect",
            "listen",
            "send",
            "recv",
        }
        called_names = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
        }
        self.assertTrue(called_names.isdisjoint(forbidden_calls))


if __name__ == "__main__":
    unittest.main()
