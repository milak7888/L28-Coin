import copy
import hashlib
import json
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from coin.historical_continuity_verifier import (
    MAX_MANIFEST_BYTES,
    PROFILE,
    STABLE_CODES,
    verify_manifest,
)
from coin import historical_continuity_verifier as hv


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_MANIFEST = (
    ROOT / "docs" / "l28_historical_continuity_manifest_v0.1.json"
)


class HistoricalPowTests(unittest.TestCase):
    def setUp(self):
        # One public preimage/hash regression vector, not a ledger dataset.
        # Outer numeric fields are synthetic; the historical PoW excludes them.
        self.record = {
            "entry_height": 100061,
            "prev": "0f0b31907458b903ecc534cf9db61afa5a21c9bbeee3a01c2315d5d73bfa7d2b",
            "hash": "00005d20db366636f8506c07b4fa49cef278085a75d9f4fc0d2e1ccaa66d7dd9",
            "difficulty": 4,
            "payload": {"type": "mining", "miner": "WORKER_POW_1",
                        "timestamp": "2025-11-08T12:50:14.080500", "nonce": 6624},
            "current_supply": 28.0, "reward": 28.0, "qubits": 50,
            "poi_q": 1.0, "poi_v": 100.0, "validator_s": 100.0, "ts": 1.0,
        }
        self.parent = {"entry_height": 100060, "hash": self.record["prev"],
                       "prev": "0" * 64}
        self.index = {self.parent["hash"]: self.parent,
                      self.record["hash"]: self.record}

    def test_pow_exact_preimage_and_stored_nonce_without_search(self):
        expected = (b'1000610f0b31907458b903ecc534cf9db61afa5a21c9bbeee3a01c2315d5d73bfa7d2b'
                    b'{"miner":"WORKER_POW_1","nonce":6624,"timestamp":'
                    b'"2025-11-08T12:50:14.080500","type":"mining"}6624')
        self.assertEqual(hv._pow_preimage(self.record), expected)
        self.assertEqual(hashlib.sha256(expected).hexdigest(), self.record["hash"])
        self.assertEqual(hv._verify_pow_record(self.record, self.index), self.record["hash"])
        self.assertIsNone(hv._verify_selected_pow(self.record, self.index))

    def test_pow_tamper_and_type_rejection_without_artifact_pins(self):
        cases = [
            ("hash", "f" * 64, "pow_hash_mismatch"),
            ("prev", "f" * 64, "pow_hash_mismatch"),
            ("entry_height", 100062, "pow_hash_mismatch"),
            ("entry_height", True, "record_schema_error"),
            ("difficulty", 0, "recorded_difficulty_invalid"),
            ("difficulty", 12, "recorded_difficulty_invalid"),
            ("difficulty", True, "recorded_difficulty_invalid"),
            ("difficulty", "4", "recorded_difficulty_invalid"),
            ("difficulty", 4.0, "recorded_difficulty_invalid"),
            ("hash", "A" * 64, "record_schema_error"),
            ("reward", True, "record_schema_error"),
        ]
        for key, value, code in cases:
            with self.subTest(key=key, value=value):
                record = copy.deepcopy(self.record)
                record[key] = value
                with self.assertRaisesRegex(hv._PowError, "^" + code + "$"):
                    hv._verify_pow_record(record, self.index)
        for value in [True, False, -1, 6624.0, "6624", None, 2**64]:
            with self.subTest(nonce=value):
                record = copy.deepcopy(self.record)
                record["payload"]["nonce"] = value
                with self.assertRaisesRegex(hv._PowError, "record_schema_error"):
                    hv._verify_pow_record(record, self.index)
        for key, value in [("miner", "altered"), ("nonce", 6625),
                           ("timestamp", "altered")]:
            record = copy.deepcopy(self.record)
            record["payload"][key] = value
            with self.assertRaisesRegex(hv._PowError, "pow_hash_mismatch"):
                hv._verify_pow_record(record, self.index)
        for key in self.record:
            record = copy.deepcopy(self.record)
            del record[key]
            with self.assertRaises(hv._PowError):
                hv._verify_pow_record(record, self.index)

    def test_pow_declared_work_independently_checked(self):
        record = copy.deepcopy(self.record)
        record["payload"]["nonce"] = 0
        record["hash"] = hashlib.sha256(hv._pow_preimage(record)).hexdigest()
        self.assertFalse(record["hash"].startswith("0000"))
        with self.assertRaisesRegex(hv._PowError, "recorded_difficulty_invalid"):
            hv._verify_pow_record(record, self.index)

    def test_pow_parent_and_selected_binding(self):
        with self.assertRaisesRegex(hv._PowError, "parent_missing"):
            hv._verify_pow_record(self.record, {})
        self.parent["entry_height"] = 100059
        with self.assertRaisesRegex(hv._PowError, "parent_height_mismatch"):
            hv._verify_pow_record(self.record, self.index)
        for value in [29.0, 28]:
            record = copy.deepcopy(self.record)
            record["reward"] = value
            with self.assertRaisesRegex(hv._PowError, "selected_record_mismatch"):
                hv._verify_selected_pow(record, self.index)
        with self.assertRaisesRegex(hv._PowError, "selected_record_mismatch"):
            hv._verify_selected_pow(self.record, {})

    def test_pow_json_failures_and_bounds(self):
        for data, code in [
            (b'\xff', "invalid_record_json"), (b'{', "invalid_record_json"),
            (b'{}\n\n', "record_schema_error"),
            (b'{"a":1,"a":2}', "duplicate_record_key"),
            (b'[]', "record_schema_error"),
            (b' ' * (hv.MAX_RECORD_BYTES + 1), "record_too_large"),
            (b'\n' * (hv.MAX_RECORDS + 2), "record_limit"),
            (b'[' * 1100, "invalid_record_json"),
        ]:
            with self.subTest(code=code):
                with self.assertRaisesRegex(hv._PowError, code):
                    hv._parse_pow_records(data)
        for value in [float('nan'), float('inf'), -float('inf'), '\ud800']:
            record = copy.deepcopy(self.record)
            record["payload"]["miner"] = value
            with self.assertRaisesRegex(hv._PowError, "record_schema_error"):
                hv._parse_pow_records(json.dumps(record).encode())
        encoded = json.dumps(self.record).encode()
        with self.assertRaisesRegex(hv._PowError, "duplicate_record"):
            hv._parse_pow_records(encoded + b'\n' + encoded)
        record = copy.deepcopy(self.record)
        record["payload"]["miner"] = "é"
        self.assertIn(b'\\u00e9', hv._pow_preimage(record))

    def test_pow_empty_and_count_mismatches(self):
        for raw, snapshot in [({}, {}), (self.index, {}), (self.index, self.index)]:
            with self.assertRaisesRegex(hv._PowError, "record_count_mismatch"):
                hv._verify_pow_indexes(raw, snapshot)

    def test_pow_artifact_boundary_and_no_policy_promotion(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "public.jsonl"
            path.write_bytes(b'{}\n')
            with mock.patch.object(hv, "_parse_pow_records") as parser:
                report = hv.verify_pow_artifacts(path, path)
                parser.assert_not_called()
            self.assertEqual(report["code"], "artifact_hash_mismatch")
            for flag in ["HASH_VALID", "RECORDED_DIFFICULTY_VALID",
                         "HISTORICAL_POLICY_AUTHENTICATED", "CANONICAL_ACCEPTANCE"]:
                self.assertIs(report[flag], False)
            self.assertEqual(report["source_policy_status"], "MISMATCH_NOT_CONSENSUS_AUTHORITY")
            for invalid in [None, "", Path(directory), path.with_name("missing")]:
                self.assertFalse(hv.verify_pow_artifacts(invalid, path)["ok"])
            link = path.with_name("link")
            link.symlink_to(path)
            self.assertFalse(hv.verify_pow_artifacts(link, path)["ok"])
            with path.open("wb") as stream:
                stream.truncate(hv.MAX_ARTIFACT_BYTES + 1)
            self.assertEqual(hv.verify_pow_artifacts(path, path)["code"], "artifact_too_large")


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
