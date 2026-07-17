from __future__ import annotations

import ast
import copy
import dataclasses
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

from coin import node_role_composition_manifest as composition
from coin import node_role_composition_manifest_cli as composition_cli
from coin import node_role_composition_manifest_evidence as evidence
from test_node_role_composition_manifest import _json, _valid_manifest


def _valid_evidence() -> dict[str, object]:
    manifest = _valid_manifest()
    result = composition.verify_node_role_composition_manifest_json(_json(manifest))
    if not result.ok:
        raise AssertionError(result.code)
    return {
        "evidence_version": evidence.EVIDENCE_VERSION,
        "manifest": manifest,
        "report": composition_cli.build_report(result),
    }


class NodeRoleCompositionManifestEvidenceTests(unittest.TestCase):
    def test_canonical_evidence_is_valid_and_bound(self) -> None:
        value = _valid_evidence()
        result = evidence.verify_node_role_composition_manifest_evidence_json(
            _json(value)
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "evidence_valid")
        self.assertEqual(
            result.evidence_sha256,
            evidence.compute_composition_manifest_evidence_sha256(value),
        )
        self.assertEqual(
            result.manifest_sha256,
            composition.compute_composition_manifest_sha256(value["manifest"]),
        )
        self.assertEqual(result.component_ids, ("core-primary", "p2p-boundary"))
        self.assertEqual(result.roles, ("CoreL28Node", "L28P2PNode"))
        self.assertEqual(
            result.trust_boundary_ids,
            (
                "peer_to_p2p",
                "p2p_to_core",
                "core_to_persistence",
                "checkpoint_to_core",
            ),
        )
        self.assertEqual(result.checks, evidence.SUCCESS_CHECKS)

    def test_evidence_sha256_matches_public_canonical_algorithm(self) -> None:
        value = _valid_evidence()
        expected = hashlib.sha256(
            json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        self.assertEqual(
            evidence.compute_composition_manifest_evidence_sha256(value), expected
        )

    def test_semantically_identical_formatting_is_deterministic(self) -> None:
        value = _valid_evidence()
        compact = _json(value)
        pretty = _json(value, pretty=True)

        compact_result = evidence.verify_node_role_composition_manifest_evidence_json(
            compact
        )
        pretty_result = evidence.verify_node_role_composition_manifest_evidence_json(
            pretty
        )

        self.assertTrue(compact_result.ok)
        self.assertEqual(compact_result, pretty_result)

    def test_semantic_manifest_mutation_breaks_report_binding(self) -> None:
        value = _valid_evidence()
        value["manifest"]["components"][0]["component_id"] = "core-secondary"

        result = evidence.verify_node_role_composition_manifest_evidence_json(
            _json(value)
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "manifest_report_mismatch")

    def test_duplicate_keys_are_rejected_at_any_depth(self) -> None:
        raw = (
            '{"evidence_version":"'
            + evidence.EVIDENCE_VERSION
            + '","manifest":{"a":1,"a":2},"report":{}}'
        )

        result = evidence.verify_node_role_composition_manifest_evidence_json(raw)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "duplicate_key")

    def test_invalid_json_encoding_nonfinite_and_input_type_fail_closed(self) -> None:
        cases: list[object] = [
            b"\xff",
            '{"evidence_version":NaN}',
            7,
            None,
        ]

        for payload in cases:
            with self.subTest(payload_type=type(payload).__name__):
                result = evidence.verify_node_role_composition_manifest_evidence_json(
                    payload  # type: ignore[arg-type]
                )
                self.assertFalse(result.ok)
                self.assertIn(
                    result.code,
                    {
                        "invalid_encoding",
                        "invalid_json",
                        "input_type_invalid",
                    },
                )

    def test_oversized_input_is_rejected_before_json_parsing(self) -> None:
        payload = b"x" * (evidence.MAX_EVIDENCE_BYTES + 1)

        result = evidence.verify_node_role_composition_manifest_evidence_json(payload)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "evidence_too_large")

    def test_top_level_schema_is_exact_and_fail_closed(self) -> None:
        value = _valid_evidence()

        missing = copy.deepcopy(value)
        del missing["report"]
        extra = copy.deepcopy(value)
        extra["unexpected"] = True

        for candidate in (missing, extra):
            result = evidence.verify_node_role_composition_manifest_evidence_json(
                _json(candidate)
            )
            self.assertFalse(result.ok)
            self.assertEqual(result.code, "schema_error")

    def test_evidence_version_type_and_value_fail_closed(self) -> None:
        for version in (1, "unsupported/v0.1"):
            value = _valid_evidence()
            value["evidence_version"] = version

            result = evidence.verify_node_role_composition_manifest_evidence_json(
                _json(value)
            )

            self.assertFalse(result.ok)
            self.assertIn(result.code, {"schema_error", "version_unsupported"})

    def test_invalid_or_incomplete_manifest_is_rejected(self) -> None:
        value = _valid_evidence()
        value["manifest"]["runtime_configuration"]["listeners"] = ["127.0.0.1:1"]

        result = evidence.verify_node_role_composition_manifest_evidence_json(
            _json(value)
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "manifest_invalid")

    def test_report_schema_is_exact_and_fail_closed(self) -> None:
        missing = _valid_evidence()
        del missing["report"]["checks"]

        extra = _valid_evidence()
        extra["report"]["unexpected"] = True

        for value in (missing, extra):
            result = evidence.verify_node_role_composition_manifest_evidence_json(
                _json(value)
            )
            self.assertFalse(result.ok)
            self.assertEqual(result.code, "report_schema_invalid")

    def test_report_identifier_shape_and_commitment_are_enforced(self) -> None:
        bad_shape = _valid_evidence()
        bad_shape["report"]["report_id"] = "not-a-sha256"

        bad_commitment = _valid_evidence()
        bad_commitment["report"]["report_id"] = "0" * 64

        for value, expected in (
            (bad_shape, "report_schema_invalid"),
            (bad_commitment, "report_id_invalid"),
        ):
            result = evidence.verify_node_role_composition_manifest_evidence_json(
                _json(value)
            )
            self.assertFalse(result.ok)
            self.assertEqual(result.code, expected)

    def test_recomputed_false_report_claim_is_rejected(self) -> None:
        value = _valid_evidence()
        value["report"]["ok"] = False
        value["report"]["report_id"] = composition_cli.compute_report_id(value["report"])

        result = evidence.verify_node_role_composition_manifest_evidence_json(
            _json(value)
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "manifest_report_mismatch")

    def test_recomputed_manifest_hash_claim_is_rejected(self) -> None:
        value = _valid_evidence()
        value["report"]["manifest_sha256"] = "0" * 64
        value["report"]["report_id"] = composition_cli.compute_report_id(value["report"])

        result = evidence.verify_node_role_composition_manifest_evidence_json(
            _json(value)
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "manifest_report_mismatch")

    def test_result_is_frozen_and_input_is_not_modified(self) -> None:
        value = _valid_evidence()
        original = copy.deepcopy(value)

        result = evidence.verify_node_role_composition_manifest_evidence_json(
            _json(value)
        )

        self.assertTrue(result.ok)
        self.assertEqual(value, original)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.code = "changed"  # type: ignore[misc]

    def test_wrapper_matches_public_function(self) -> None:
        payload = _json(_valid_evidence())

        direct = evidence.verify_node_role_composition_manifest_evidence_json(payload)
        wrapped = evidence.NodeRoleCompositionManifestEvidenceVerifier.verify_json(
            payload
        )

        self.assertEqual(wrapped, direct)

    def test_stable_codes_and_success_checks_are_explicit(self) -> None:
        self.assertEqual(evidence.STABLE_CODES[0], "evidence_valid")
        self.assertIn("manifest_invalid", evidence.STABLE_CODES)
        self.assertIn("report_id_invalid", evidence.STABLE_CODES)
        self.assertIn("manifest_report_mismatch", evidence.STABLE_CODES)
        self.assertEqual(
            evidence.SUCCESS_CHECKS,
            (
                "identity",
                "schema",
                "manifest_verification",
                "report_schema",
                "report_identifier",
                "manifest_report_binding",
                "semantic_commitment",
            ),
        )

    def test_internal_exception_is_sanitized(self) -> None:
        payload = _json(_valid_evidence())
        with mock.patch.object(
            evidence.manifest_core,
            "verify_node_role_composition_manifest_json",
            side_effect=RuntimeError("private detail"),
        ):
            result = evidence.verify_node_role_composition_manifest_evidence_json(
                payload
            )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "internal_error")
        self.assertEqual(result.detail, "internal_failure")

    def test_production_module_has_no_io_or_activation_imports(self) -> None:
        path = Path("coin/node_role_composition_manifest_evidence.py")
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )

        forbidden = {
            "os",
            "pathlib",
            "socket",
            "subprocess",
            "threading",
            "multiprocessing",
            "requests",
            "urllib",
            "http",
            "ssl",
            "asyncio",
        }
        self.assertFalse(imports.intersection(forbidden))


if __name__ == "__main__":
    unittest.main()
