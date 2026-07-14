import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from coin.historical_continuity_verifier import (
    MAX_MANIFEST_BYTES,
    PROFILE,
    STABLE_CODES,
    verify_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_MANIFEST = (
    ROOT / "docs" / "l28_historical_continuity_manifest_v0.1.json"
)


class HistoricalContinuityVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.temp_path = Path(self.temp.name)
        self.canonical_bytes = CANONICAL_MANIFEST.read_bytes()
        self.canonical = json.loads(self.canonical_bytes)

    def write_json(self, value, name="manifest.json"):
        path = self.temp_path / name
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    def set_path(self, value, dotted, replacement):
        result = copy.deepcopy(value)
        current = result
        components = dotted.split(".")
        for component in components[:-1]:
            current = current[component]
        current[components[-1]] = replacement
        return result

    def delete_path(self, value, dotted):
        result = copy.deepcopy(value)
        current = result
        components = dotted.split(".")
        for component in components[:-1]:
            current = current[component]
        del current[components[-1]]
        return result

    def test_canonical_manifest_is_valid(self):
        result = verify_manifest(CANONICAL_MANIFEST)

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "manifest_valid")
        self.assertEqual(result.manifest_version, PROFILE)
        self.assertEqual(
            result.manifest_sha256,
            hashlib.sha256(self.canonical_bytes).hexdigest(),
        )
        self.assertEqual(
            result.checks,
            (
                "identity",
                "snapshot",
                "raw_dag",
                "reconstruction",
                "parent_graph",
                "economics",
                "consolidation",
                "mining",
                "activation",
            ),
        )
        self.assertEqual(result.detail, "")

    def test_verification_does_not_modify_manifest(self):
        before_bytes = CANONICAL_MANIFEST.read_bytes()
        before_stat = CANONICAL_MANIFEST.stat()

        result = verify_manifest(CANONICAL_MANIFEST)

        after_bytes = CANONICAL_MANIFEST.read_bytes()
        after_stat = CANONICAL_MANIFEST.stat()

        self.assertTrue(result.ok)
        self.assertEqual(before_bytes, after_bytes)
        self.assertEqual(before_stat.st_size, after_stat.st_size)
        self.assertEqual(before_stat.st_mtime_ns, after_stat.st_mtime_ns)

    def test_stable_codes_are_explicit(self):
        self.assertEqual(
            STABLE_CODES,
            frozenset(
                {
                    "manifest_valid",
                    "invalid_manifest_path",
                    "manifest_not_found",
                    "manifest_symlink_rejected",
                    "manifest_not_regular_file",
                    "manifest_too_large",
                    "manifest_read_error",
                    "invalid_json",
                    "duplicate_json_key",
                    "manifest_not_object",
                    "unsupported_manifest_version",
                    "invalid_manifest_status",
                    "schema_error",
                    "invariant_violation",
                }
            ),
        )

    def test_invalid_and_missing_paths_fail_closed(self):
        cases = (
            (None, "invalid_manifest_path"),
            ("", "invalid_manifest_path"),
            (self.temp_path / "missing.json", "manifest_not_found"),
            (self.temp_path, "manifest_not_regular_file"),
        )

        for path, expected_code in cases:
            with self.subTest(path=path):
                result = verify_manifest(path)
                self.assertFalse(result.ok)
                self.assertEqual(result.code, expected_code)

    def test_symlink_is_rejected(self):
        link = self.temp_path / "manifest-link.json"
        try:
            os.symlink(CANONICAL_MANIFEST, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")

        result = verify_manifest(link)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "manifest_symlink_rejected")

    def test_oversized_manifest_is_rejected_before_parsing(self):
        path = self.temp_path / "oversized.json"
        path.write_bytes(b" " * (MAX_MANIFEST_BYTES + 1))

        result = verify_manifest(path)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "manifest_too_large")

    def test_invalid_encodings_and_json_are_rejected(self):
        cases = (
            (b"\xff\xfe", "invalid_json"),
            (b"{", "invalid_json"),
            (b"[]", "manifest_not_object"),
        )

        for index, (raw, expected_code) in enumerate(cases):
            path = self.temp_path / f"invalid-{index}.json"
            path.write_bytes(raw)

            result = verify_manifest(path)

            with self.subTest(index=index):
                self.assertFalse(result.ok)
                self.assertEqual(result.code, expected_code)

    def test_duplicate_keys_are_rejected_at_any_depth(self):
        raw = (
            b'{"manifest_version":"l28-historical-continuity/v0.1",'
            b'"status":"audit_evidence_only",'
            b'"identity":{"asset":"L28","asset":"OTHER"}}'
        )
        path = self.temp_path / "duplicate.json"
        path.write_bytes(raw)

        result = verify_manifest(path)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "duplicate_json_key")

    def test_version_and_status_are_fail_closed(self):
        cases = (
            (
                "manifest_version",
                "l28-historical-continuity/v9",
                "unsupported_manifest_version",
            ),
            ("status", "active", "invalid_manifest_status"),
        )

        for dotted, replacement, expected_code in cases:
            value = self.set_path(self.canonical, dotted, replacement)
            result = verify_manifest(
                self.write_json(value, f"{dotted}.json")
            )

            with self.subTest(field=dotted):
                self.assertFalse(result.ok)
                self.assertEqual(result.code, expected_code)

    def test_missing_and_wrongly_typed_fields_are_schema_errors(self):
        cases = (
            self.delete_path(
                self.canonical,
                "economics.historical_declared_supply",
            ),
            self.set_path(
                self.canonical,
                "economics.historical_declared_supply",
                True,
            ),
            self.set_path(
                self.canonical,
                "preserved_snapshot.sha256",
                "ABC",
            ),
            self.set_path(
                self.canonical,
                "activation.network_started",
                0,
            ),
        )

        for index, value in enumerate(cases):
            result = verify_manifest(
                self.write_json(value, f"schema-{index}.json")
            )

            with self.subTest(index=index):
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "schema_error")

    def test_arithmetic_and_partition_mutations_are_rejected(self):
        mutations = (
            ("preserved_snapshot.physical_records", 72_099),
            ("raw_dag.physical_records", 102_264),
            ("raw_dag.unique_represented_heights", 72_095),
            ("parent_graph.parent_only_in_raw_dag", 20_670),
            ("economics.physical_recorded_reward_total", 2_018_689),
            ("economics.missing_height_implied_amount", 805_897),
            ("economics.historical_declared_supply", 2_824_585),
            ("economics.derived_unlocked_amount", 2_324_585),
            ("consolidation.total_amount", 2_018_661),
            ("consolidation.unconsolidated_genesis_reward", 29),
        )

        for index, (dotted, replacement) in enumerate(mutations):
            value = self.set_path(self.canonical, dotted, replacement)
            result = verify_manifest(
                self.write_json(value, f"invariant-{index}.json")
            )

            with self.subTest(field=dotted):
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "invariant_violation")
                self.assertTrue(result.detail)

    def test_unsafe_activation_claims_are_rejected(self):
        fields = (
            "new_ledger_created",
            "historical_ledger_copied_to_public_repository",
            "canonical_continuation_proven",
            "canonical_issuance_initialized",
            "network_started",
            "wallet_spendability_proven",
        )

        for field in fields:
            value = self.set_path(
                self.canonical,
                f"activation.{field}",
                True,
            )
            result = verify_manifest(
                self.write_json(value, f"activation-{field}.json")
            )

            with self.subTest(field=field):
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "invariant_violation")

    def test_unsafe_mining_claims_are_rejected(self):
        mutations = (
            ("mining.active", True),
            ("mining.canonical_pow_formula_defined_in_v1", True),
            ("mining.difficulty_18_is_consensus", True),
            ("mining.automatic_creator_reward_routing", True),
            ("mining.winning_proof_binding_implemented", True),
            (
                "mining.accepted_coinbase_receiver_must_match_declared_miner",
                False,
            ),
        )

        for index, (dotted, replacement) in enumerate(mutations):
            value = self.set_path(self.canonical, dotted, replacement)
            result = verify_manifest(
                self.write_json(value, f"mining-{index}.json")
            )

            with self.subTest(field=dotted):
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "invariant_violation")

    def test_unsafe_economic_and_provenance_claims_are_rejected(self):
        mutations = (
            (
                "economics.derived_unlocked_is_live_spendable_proof",
                True,
            ),
            ("economics.treasury_economic_commitments_counted", 2),
            ("consolidation.creator_live_balance_proven", True),
            ("consolidation.writer_source_recovered", True),
            ("consolidation.writer_execution_provenance", True),
            ("consolidation.all_records_target_verified_creator", False),
        )

        for index, (dotted, replacement) in enumerate(mutations):
            value = self.set_path(self.canonical, dotted, replacement)
            result = verify_manifest(
                self.write_json(value, f"claim-{index}.json")
            )

            with self.subTest(field=dotted):
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "invariant_violation")


if __name__ == "__main__":
    unittest.main()
