import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from coin import node_role_conformance as conformance


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PROFILE = ROOT / "docs" / "l28_core_p2p_security_profile_v0.1.json"


class NodeRoleConformanceTests(unittest.TestCase):
    def setUp(self):
        self.profile_bytes = CANONICAL_PROFILE.read_bytes()
        self.profile = json.loads(self.profile_bytes.decode("utf-8"))
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)

    def write_json(self, value, name="profile.json"):
        target = self.root / name
        target.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return target

    def write_bytes(self, value, name="profile.json"):
        target = self.root / name
        target.write_bytes(value)
        return target

    def verify_mutation(self, mutate):
        value = copy.deepcopy(self.profile)
        mutate(value)
        return conformance.verify_node_role_profile(self.write_json(value))

    def test_canonical_profile_is_conformant(self):
        result = conformance.verify_node_role_profile(CANONICAL_PROFILE)
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "conformant")
        self.assertEqual(result.detail, "")
        self.assertEqual(result.profile_version, conformance.PROFILE)
        self.assertEqual(
            result.profile_sha256,
            "61e787f9f665d76a704d5e6dca8bccc6a80bb3ed231ac741fb5b7497383b04f6",
        )
        self.assertEqual(result.checks, conformance.CHECKS)

    def test_semantically_identical_reformatting_is_accepted(self):
        target = self.write_bytes(
            json.dumps(
                self.profile,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        result = conformance.verify_node_role_profile(target)
        self.assertTrue(result.ok)
        self.assertNotEqual(result.profile_sha256, hashlib.sha256(self.profile_bytes).hexdigest())

    def test_missing_extra_and_wrongly_typed_fields_fail_closed(self):
        missing = self.verify_mutation(lambda value: value.pop("roles"))
        self.assertEqual(missing.code, "profile_schema_invalid")

        extra = self.verify_mutation(lambda value: value.__setitem__("extra", False))
        self.assertEqual(extra.code, "profile_schema_invalid")

        wrong_type = self.verify_mutation(
            lambda value: value.__setitem__("foundation19_prohibitions", [])
        )
        self.assertEqual(wrong_type.code, "profile_schema_invalid")

    def test_version_status_and_architecture_fail_closed(self):
        version = self.verify_mutation(
            lambda value: value.__setitem__("profile_version", "v-next")
        )
        self.assertEqual(version.code, "profile_version_unsupported")

        status = self.verify_mutation(
            lambda value: value.__setitem__("status", "active")
        )
        self.assertEqual(status.code, "profile_status_invalid")

        architecture = self.verify_mutation(
            lambda value: value.__setitem__("architecture", "other")
        )
        self.assertEqual(architecture.code, "profile_invariant_failed")

    def test_role_and_capability_mutations_are_rejected(self):
        missing_role = self.verify_mutation(
            lambda value: value["roles"].pop("L28P2PNode")
        )
        self.assertEqual(missing_role.code, "profile_schema_invalid")

        def overlap(value):
            value["roles"]["L28P2PNode"]["prohibited"].append(
                value["roles"]["L28P2PNode"]["owns"][0]
            )

        overlapping = self.verify_mutation(overlap)
        self.assertEqual(overlapping.code, "profile_invariant_failed")

        changed_trust = self.verify_mutation(
            lambda value: value["roles"]["CoreL28Node"].__setitem__(
                "trust", "changed"
            )
        )
        self.assertEqual(changed_trust.code, "profile_semantic_mismatch")

    def test_reserved_states_and_activation_are_rejected(self):
        def reachable_reserved(value):
            value["core_lifecycle"]["allowed_transitions"].append(
                ["PAUSED", "RUNNING_RESERVED"]
            )

        reachable = self.verify_mutation(reachable_reserved)
        self.assertEqual(reachable.code, "profile_invariant_failed")

        core_active = self.verify_mutation(
            lambda value: value["core_lifecycle"].__setitem__(
                "canonical_activation_transition_present", True
            )
        )
        self.assertEqual(core_active.code, "profile_invariant_failed")

        p2p_active = self.verify_mutation(
            lambda value: value["p2p_lifecycle"].__setitem__(
                "network_activation_transition_present", True
            )
        )
        self.assertEqual(p2p_active.code, "profile_invariant_failed")

    def test_lifecycle_transition_shape_and_uniqueness_are_enforced(self):
        malformed = self.verify_mutation(
            lambda value: value["p2p_lifecycle"]["allowed_transitions"].append(
                ["PAUSED"]
            )
        )
        self.assertEqual(malformed.code, "profile_schema_invalid")

        def duplicate(value):
            value["p2p_lifecycle"]["allowed_transitions"].append(
                copy.deepcopy(value["p2p_lifecycle"]["allowed_transitions"][0])
            )

        duplicated = self.verify_mutation(duplicate)
        self.assertEqual(duplicated.code, "profile_invariant_failed")

    def test_trust_boundary_and_frame_mutations_are_rejected(self):
        def duplicate_boundary(value):
            value["trust_boundaries"][1]["id"] = value["trust_boundaries"][0]["id"]

        duplicate = self.verify_mutation(duplicate_boundary)
        self.assertEqual(duplicate.code, "profile_invariant_failed")

        def missing_frame_field(value):
            value["future_frame_requirements"]["required_fields"].remove("network_id")

        missing = self.verify_mutation(missing_frame_field)
        self.assertEqual(missing.code, "profile_invariant_failed")

        changed_control = self.verify_mutation(
            lambda value: value["trust_boundaries"][0]["required_controls"].append(
                "unexpected_control"
            )
        )
        self.assertEqual(changed_control.code, "profile_semantic_mismatch")

    def test_non_activation_claims_must_remain_false(self):
        for key in sorted(self.profile["foundation19_prohibitions"]):
            with self.subTest(key=key):
                result = self.verify_mutation(
                    lambda value, selected=key: value[
                        "foundation19_prohibitions"
                    ].__setitem__(selected, True)
                )
                self.assertEqual(result.code, "profile_invariant_failed")

    def test_unvalidated_semantic_mutation_is_rejected_by_commitment(self):
        result = self.verify_mutation(
            lambda value: value["future_frame_requirements"].__setitem__(
                "reason_runtime_limits_undefined", "changed"
            )
        )
        self.assertEqual(result.code, "profile_semantic_mismatch")

    def test_duplicate_keys_invalid_json_nonfinite_and_encoding_are_rejected(self):
        duplicate = self.write_bytes(
            b'{"profile_version":"one","profile_version":"two"}'
        )
        self.assertEqual(
            conformance.verify_node_role_profile(duplicate).code,
            "profile_duplicate_key",
        )

        invalid = self.write_bytes(b"{", "invalid.json")
        self.assertEqual(
            conformance.verify_node_role_profile(invalid).code,
            "profile_json_invalid",
        )

        nonfinite = self.write_bytes(b'{"value":NaN}', "nonfinite.json")
        self.assertEqual(
            conformance.verify_node_role_profile(nonfinite).code,
            "profile_json_invalid",
        )

        invalid_utf8 = self.write_bytes(b"\xff", "invalid-utf8.json")
        self.assertEqual(
            conformance.verify_node_role_profile(invalid_utf8).code,
            "profile_encoding_invalid",
        )

    def test_path_boundaries_are_fail_closed(self):
        self.assertEqual(
            conformance.verify_node_role_profile(None).code,
            "path_required",
        )
        self.assertEqual(
            conformance.verify_node_role_profile(123).code,
            "path_invalid",
        )
        self.assertEqual(
            conformance.verify_node_role_profile(self.root / "missing.json").code,
            "profile_read_failed",
        )
        self.assertEqual(
            conformance.verify_node_role_profile(self.root).code,
            "path_not_file",
        )

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support required")
    def test_symlink_is_rejected(self):
        source = self.write_bytes(self.profile_bytes, "source.json")
        link = self.root / "link.json"
        link.symlink_to(source)
        self.assertEqual(
            conformance.verify_node_role_profile(link).code,
            "path_symlink",
        )

    def test_oversized_profile_is_rejected_before_json_parsing(self):
        target = self.write_bytes(
            b"{" + b" " * conformance.MAX_PROFILE_BYTES + b"}",
            "oversized.json",
        )
        self.assertEqual(
            conformance.verify_node_role_profile(target).code,
            "profile_too_large",
        )

    def test_verification_is_deterministic_and_does_not_modify_profile(self):
        before = CANONICAL_PROFILE.read_bytes()
        first = conformance.verify_node_role_profile(CANONICAL_PROFILE)
        second = conformance.verify_node_role_profile(CANONICAL_PROFILE)
        after = CANONICAL_PROFILE.read_bytes()
        self.assertEqual(first, second)
        self.assertEqual(before, after)

    def test_internal_exception_is_sanitized(self):
        with mock.patch.object(
            conformance,
            "_read_profile",
            side_effect=RuntimeError("sensitive internal detail"),
        ):
            result = conformance.verify_node_role_profile(CANONICAL_PROFILE)
        self.assertEqual(result.code, "internal_error")
        self.assertEqual(result.detail, "verification:internal_error")
        self.assertNotIn("sensitive", result.detail)

    def test_stable_codes_are_unique_and_complete(self):
        self.assertEqual(len(conformance.STABLE_CODES), len(set(conformance.STABLE_CODES)))
        self.assertEqual(
            set(conformance.STABLE_CODES),
            {
                "conformant",
                "path_required",
                "path_invalid",
                "path_symlink",
                "path_not_file",
                "profile_too_large",
                "profile_read_failed",
                "profile_encoding_invalid",
                "profile_json_invalid",
                "profile_duplicate_key",
                "profile_schema_invalid",
                "profile_version_unsupported",
                "profile_status_invalid",
                "profile_invariant_failed",
                "profile_semantic_mismatch",
                "internal_error",
            },
        )


if __name__ == "__main__":
    unittest.main()
