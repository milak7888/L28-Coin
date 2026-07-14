"""Adversarial tests for the offline inert node-role scenario runner."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

from coin import node_role_scenario as scenario
from coin import node_role_transcript as transcript


def _document(
    role: str,
    requested_states: list[object],
) -> dict[str, object]:
    return {
        "scenario_version": scenario.SCENARIO_VERSION,
        "model_version": scenario.MODEL_VERSION,
        "transcript_version": scenario.TRANSCRIPT_VERSION,
        "role": role,
        "requested_states": requested_states,
    }


def _core_document() -> dict[str, object]:
    return _document(
        scenario.CORE_ROLE,
        ["EVIDENCE_ONLY", "PAUSED", "STOPPED"],
    )


def _p2p_document() -> dict[str, object]:
    return _document(
        scenario.P2P_ROLE,
        ["CONFIGURED", "PAUSED", "STOPPED"],
    )


def _run(document: object) -> scenario.NodeRoleScenarioResult:
    return scenario.run_scenario_json(
        json.dumps(document, separators=(",", ":"), sort_keys=True)
    )


class NodeRoleScenarioTests(unittest.TestCase):
    def test_valid_core_and_p2p_scenarios(self) -> None:
        for document, role in (
            (_core_document(), scenario.CORE_ROLE),
            (_p2p_document(), scenario.P2P_ROLE),
        ):
            with self.subTest(role=role):
                result = _run(document)
                self.assertTrue(result.ok)
                self.assertEqual(result.code, "scenario_valid")
                self.assertEqual(result.role, role)
                self.assertEqual(result.final_state, "STOPPED")
                self.assertEqual(result.request_count, 3)
                self.assertEqual(result.transcript_verification_code, "transcript_valid")
                self.assertEqual(result.checks, scenario.SUCCESS_CHECKS)
                self.assertEqual(len(result.scenario_sha256), 64)
                self.assertEqual(len(result.transcript_sha256), 64)

                replay = transcript.verify_transcript_json(result.transcript_json)
                self.assertTrue(replay.ok)
                self.assertEqual(replay.transcript_sha256, result.transcript_sha256)

    def test_generated_transcript_fields_are_derived_exactly(self) -> None:
        result = _run(_core_document())
        generated = json.loads(result.transcript_json)

        self.assertEqual(
            frozenset(generated),
            transcript.TOP_LEVEL_FIELDS,
        )
        self.assertEqual(generated["role"], scenario.CORE_ROLE)
        self.assertEqual(generated["initial_state"], "CREATED")
        self.assertEqual(generated["final_state"], "STOPPED")
        self.assertEqual(len(generated["transitions"]), 3)

        for index, entry in enumerate(generated["transitions"]):
            self.assertEqual(frozenset(entry), transcript.ENTRY_FIELDS)
            self.assertEqual(entry["sequence"], index)

    def test_reserved_requests_are_recorded_as_rejected_without_entry(self) -> None:
        documents = (
            _document(
                scenario.CORE_ROLE,
                ["RUNNING_RESERVED", "PAUSED", "STOPPED"],
            ),
            _document(
                scenario.P2P_ROLE,
                ["LISTENING_RESERVED", "PAUSED", "STOPPED"],
            ),
        )

        for document in documents:
            with self.subTest(role=document["role"]):
                result = _run(document)
                self.assertTrue(result.ok)
                first = result.steps[0]
                self.assertFalse(first.ok)
                self.assertEqual(first.code, "reserved_state_unreachable")
                self.assertEqual(first.previous_state, "CREATED")
                self.assertEqual(first.resulting_state, "CREATED")
                self.assertNotEqual(first.resulting_state, first.requested_state)

    def test_unknown_and_disallowed_requests_are_derived_as_rejections(self) -> None:
        for requested, expected_code in (
            ("UNKNOWN_STATE", "state_invalid"),
            ("STOPPED", "transition_not_allowed"),
        ):
            with self.subTest(requested=requested):
                result = _run(
                    _document(
                        scenario.CORE_ROLE,
                        [requested, "PAUSED", "STOPPED"],
                    )
                )
                self.assertTrue(result.ok)
                self.assertFalse(result.steps[0].ok)
                self.assertEqual(result.steps[0].code, expected_code)
                self.assertEqual(result.steps[0].resulting_state, "CREATED")

    def test_incomplete_scenario_fails_terminal_requirement(self) -> None:
        result = _run(
            _document(scenario.CORE_ROLE, ["PAUSED"])
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "terminal_state_required")
        self.assertEqual(result.final_state, "PAUSED")
        self.assertEqual(result.transcript_verification_code, "terminal_state_required")
        self.assertTrue(result.transcript_json)
        self.assertEqual(len(result.transcript_sha256), 64)

    def test_transcript_self_verification_failure_fails_closed(self) -> None:
        failed_verification = SimpleNamespace(
            ok=False,
            code="schema_error",
            transcript_sha256="a" * 64,
        )

        with mock.patch.object(
            scenario,
            "verify_transcript_json",
            return_value=failed_verification,
        ):
            result = _run(_core_document())

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "transcript_verification_failed")
        self.assertEqual(result.transcript_verification_code, "schema_error")

    def test_versions_and_role_fail_closed(self) -> None:
        cases = (
            ("scenario_version", "l28-node-role-scenario/v9", "version_unsupported"),
            ("model_version", "l28-node-role-model/v9", "version_unsupported"),
            ("transcript_version", "l28-node-role-transcript/v9", "version_unsupported"),
            ("role", "UnknownNode", "role_invalid"),
        )

        for field, value, expected_code in cases:
            with self.subTest(field=field):
                document = _core_document()
                document[field] = value
                result = _run(document)
                self.assertFalse(result.ok)
                self.assertEqual(result.code, expected_code)

    def test_missing_extra_and_wrongly_typed_fields_fail_schema(self) -> None:
        documents = []

        missing = _core_document()
        del missing["role"]
        documents.append(missing)

        extra = _core_document()
        extra["unexpected"] = False
        documents.append(extra)

        wrong_requests = _core_document()
        wrong_requests["requested_states"] = {}
        documents.append(wrong_requests)

        wrong_role = _core_document()
        wrong_role["role"] = 28
        documents.append(wrong_role)

        for index, document in enumerate(documents):
            with self.subTest(index=index):
                result = _run(document)
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "schema_error")

    def test_requested_states_must_be_nonempty_bounded_strings(self) -> None:
        values = (
            [""],
            [28],
            [True],
            ["X" * (scenario.MAX_STATE_TEXT_LENGTH + 1)],
        )

        for requested_states in values:
            with self.subTest(requested_states=requested_states):
                result = _run(
                    _document(scenario.CORE_ROLE, requested_states)
                )
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "schema_error")

    def test_empty_excessive_and_maximum_request_counts(self) -> None:
        empty = _run(_document(scenario.CORE_ROLE, []))
        self.assertFalse(empty.ok)
        self.assertEqual(empty.code, "request_count_invalid")

        excessive = _run(
            _document(
                scenario.CORE_ROLE,
                ["UNKNOWN_STATE"] * (scenario.MAX_REQUESTS + 1),
            )
        )
        self.assertFalse(excessive.ok)
        self.assertEqual(excessive.code, "request_count_invalid")

        maximum = _run(
            _document(
                scenario.CORE_ROLE,
                (["UNKNOWN_STATE"] * (scenario.MAX_REQUESTS - 2))
                + ["PAUSED", "STOPPED"],
            )
        )
        self.assertTrue(maximum.ok)
        self.assertEqual(maximum.request_count, scenario.MAX_REQUESTS)
        self.assertEqual(len(maximum.steps), scenario.MAX_REQUESTS)

    def test_duplicate_keys_are_rejected(self) -> None:
        payload = (
            '{"scenario_version":"l28-node-role-scenario/v0.1",'
            '"scenario_version":"l28-node-role-scenario/v0.1"}'
        )
        result = scenario.run_scenario_json(payload)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "duplicate_key")

    def test_invalid_json_encoding_nonfinite_and_input_type_are_rejected(self) -> None:
        cases = (
            ("{", "invalid_json"),
            ('{"value":NaN}', "invalid_json"),
            (b"\xff", "invalid_encoding"),
            (object(), "input_type_invalid"),
        )

        for payload, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                result = scenario.run_scenario_json(payload)
                self.assertFalse(result.ok)
                self.assertEqual(result.code, expected_code)

    def test_oversized_input_is_rejected_before_parsing(self) -> None:
        payload = "{" + (" " * scenario.MAX_SCENARIO_BYTES)
        result = scenario.run_scenario_json(payload)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "scenario_too_large")
        self.assertEqual(result.scenario_sha256, "")

    def test_semantically_identical_reformatting_is_deterministic(self) -> None:
        document = _core_document()
        compact = json.dumps(document, separators=(",", ":"), sort_keys=True)
        pretty = json.dumps(document, indent=4, sort_keys=False)

        compact_result = scenario.run_scenario_json(compact)
        pretty_result = scenario.run_scenario_json(pretty)

        self.assertEqual(compact_result, pretty_result)
        self.assertTrue(compact_result.ok)

    def test_scenario_commitment_is_body_bound(self) -> None:
        first = _run(_core_document())
        second = _run(
            _document(
                scenario.CORE_ROLE,
                ["PAUSED", "STOPPED"],
            )
        )

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertNotEqual(first.scenario_sha256, second.scenario_sha256)
        self.assertNotEqual(first.transcript_sha256, second.transcript_sha256)

    def test_scenario_sha256_matches_public_algorithm(self) -> None:
        document = _core_document()
        canonical = json.dumps(
            document,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

        result = _run(document)

        self.assertTrue(result.ok)
        self.assertEqual(
            result.scenario_sha256,
            hashlib.sha256(canonical).hexdigest(),
        )

    def test_models_results_and_steps_are_immutable(self) -> None:
        result = _run(_core_document())
        self.assertTrue(result.ok)
        self.assertIsInstance(result.steps, tuple)

        with self.assertRaises(FrozenInstanceError):
            result.final_state = "FAILED"

        with self.assertRaises(FrozenInstanceError):
            result.steps[0].resulting_state = "FAILED"

        model = scenario.CoreNodeRoleModel()
        scenario.run_scenario_json(json.dumps(_core_document()))
        self.assertEqual(model.state, "CREATED")

    def test_internal_exception_is_sanitized(self) -> None:
        with mock.patch.object(
            scenario,
            "_parse_json",
            side_effect=RuntimeError("sensitive internal information"),
        ):
            result = scenario.run_scenario_json("{}")

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "internal_error")
        self.assertEqual(result.detail, "")
        self.assertNotIn("sensitive", repr(result))

    def test_result_fields_and_stable_codes_are_explicit(self) -> None:
        self.assertEqual(
            tuple(field.name for field in fields(scenario.NodeRoleScenarioResult)),
            (
                "ok",
                "code",
                "role",
                "final_state",
                "request_count",
                "scenario_sha256",
                "transcript_sha256",
                "transcript_verification_code",
                "transcript_json",
                "steps",
                "checks",
                "detail",
                "scenario_version",
                "model_version",
                "transcript_version",
                "runner_version",
            ),
        )
        self.assertEqual(len(scenario.STABLE_CODES), len(set(scenario.STABLE_CODES)))
        self.assertEqual(
            scenario.STABLE_CODES,
            (
                "scenario_valid",
                "input_type_invalid",
                "scenario_too_large",
                "invalid_encoding",
                "invalid_json",
                "duplicate_key",
                "schema_error",
                "version_unsupported",
                "role_invalid",
                "request_count_invalid",
                "terminal_state_required",
                "transcript_verification_failed",
                "internal_error",
            ),
        )

    def test_production_module_has_no_io_or_activation_imports(self) -> None:
        path = Path(scenario.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        forbidden = {
            "asyncio",
            "multiprocessing",
            "os",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "threading",
            "urllib",
        }
        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.lstrip(".").split(".", 1)[0])
            elif isinstance(node, ast.Call):
                self.assertNotIn(
                    ast.unparse(node.func),
                    {"open", "exec", "eval", "compile", "__import__"},
                )

        self.assertFalse(imports & forbidden)


if __name__ == "__main__":
    unittest.main()
