# SPDX-License-Identifier: Apache-2.0
"""Foundation 39 disposable network identity / genesis-binding tests (M1 only)."""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from coin import disposable_network_identity_genesis_binding as binding
from coin.tx_validation import (
    L28_EMISSION_CEILING,
    L28_HALVING_INTERVAL,
    L28_MAX_COINBASE_REWARD,
    L28_MAX_SUPPLY,
    L28_REWARD_SCHEDULE,
)


def _wire(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")


class DeterministicIdentityTests(unittest.TestCase):
    def test_network_id_and_chain_id_are_stable(self) -> None:
        first = binding.compute_disposable_chain_id(
            network_id=binding.NETWORK_ID,
            protocol_version=binding.PROTOCOL_VERSION,
        )
        second = binding.compute_disposable_chain_id(
            network_id=binding.NETWORK_ID,
            protocol_version=binding.PROTOCOL_VERSION,
        )
        self.assertEqual(first, second)
        self.assertRegex(first, r"^[0-9a-f]{64}$")
        self.assertEqual(binding.NETWORK_ID, "l28-disposable-test/v0.1")
        self.assertEqual(binding.PROTOCOL_VERSION, "l28-protocol/1.0.0")

    def test_genesis_digest_stable_across_repeated_runs(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        digests = [binding.compute_disposable_genesis_digest(genesis) for _ in range(3)]
        self.assertEqual(len(set(digests)), 1)
        results = [
            binding.verify_disposable_network_genesis_json(_wire(genesis))
            for _ in range(3)
        ]
        self.assertTrue(all(item.ok for item in results))
        self.assertEqual({item.genesis_digest for item in results}, {digests[0]})
        self.assertEqual({item.report_id for item in results}, {results[0].report_id})
        self.assertEqual(results[0].checks, binding.SUCCESS_CHECKS)


class ExactSchemaAcceptanceTests(unittest.TestCase):
    def test_valid_genesis_and_binding_config_pass(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        genesis_result = binding.verify_disposable_network_genesis_json(_wire(genesis))
        self.assertTrue(genesis_result.ok, genesis_result.code)
        self.assertIs(genesis_result.execution_authorized, False)

        config = binding.build_disposable_binding_config(genesis_result.genesis_digest)
        binding_result = binding.verify_disposable_network_binding_config_json(
            _wire(config),
            expected_genesis_digest=genesis_result.genesis_digest,
        )
        self.assertTrue(binding_result.ok, binding_result.code)
        self.assertEqual(binding_result.genesis_digest, genesis_result.genesis_digest)
        self.assertIs(binding_result.execution_authorized, False)

    def test_compact_and_pretty_json_are_logically_equal(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        compact = json.dumps(genesis, separators=(",", ":"))
        pretty = json.dumps(genesis, indent=2)
        first = binding.verify_disposable_network_genesis_json(compact)
        second = binding.verify_disposable_network_genesis_json(pretty)
        self.assertEqual(first, second)


class EconomicsImmutabilityTests(unittest.TestCase):
    def test_mutated_hard_cap_fails(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        genesis["economics"]["hard_cap"] = L28_MAX_SUPPLY + 1
        result = binding.verify_disposable_network_genesis_json(_wire(genesis))
        self.assertEqual(result.code, "economics_invalid")
        self.assertIs(result.execution_authorized, False)

    def test_mutated_schedule_fails(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        genesis["economics"]["reward_schedule"] = [28, 14, 7, 3, 2]
        result = binding.verify_disposable_network_genesis_json(_wire(genesis))
        self.assertEqual(result.code, "economics_invalid")

    def test_economics_match_protocol_constants(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        economics = genesis["economics"]
        self.assertEqual(economics["hard_cap"], L28_MAX_SUPPLY)
        self.assertEqual(economics["emission_ceiling"], L28_EMISSION_CEILING)
        self.assertEqual(economics["halving_interval"], L28_HALVING_INTERVAL)
        self.assertEqual(economics["max_coinbase_reward"], L28_MAX_COINBASE_REWARD)
        self.assertEqual(tuple(economics["reward_schedule"]), L28_REWARD_SCHEDULE)


class HistoricalCanonicalSeparationTests(unittest.TestCase):
    def test_main_network_id_rejected(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        genesis["network_id"] = "MAIN"
        result = binding.verify_disposable_network_genesis_json(_wire(genesis))
        self.assertEqual(result.code, "network_id_invalid")

    def test_historical_import_flag_rejected(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        genesis["historical_state_imported"] = True
        result = binding.verify_disposable_network_genesis_json(_wire(genesis))
        self.assertEqual(result.code, "historical_import_forbidden")

    def test_canonical_continuation_rejected(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        genesis["canonical_continuation"] = True
        result = binding.verify_disposable_network_genesis_json(_wire(genesis))
        self.assertEqual(result.code, "historical_import_forbidden")

    def test_nonzero_initial_supply_rejected(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        genesis["initial_issued_supply"] = 28
        result = binding.verify_disposable_network_genesis_json(_wire(genesis))
        self.assertEqual(result.code, "historical_import_forbidden")

    def test_continuity_manifest_digest_as_state_rejected(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        # inject forbidden extra historical state claim
        mutated = dict(genesis)
        mutated["historical_continuity_manifest_sha256"] = "a" * 64
        result = binding.verify_disposable_network_genesis_json(_wire(mutated))
        self.assertEqual(result.code, "schema_invalid")


class MismatchMatrixTests(unittest.TestCase):
    def test_wrong_chain_id_fails(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        genesis["chain_id"] = "0" * 64
        result = binding.verify_disposable_network_genesis_json(_wire(genesis))
        self.assertEqual(result.code, "chain_id_invalid")

    def test_wrong_protocol_version_fails(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        genesis["protocol_version"] = "l28-protocol/0.0.0"
        result = binding.verify_disposable_network_genesis_json(_wire(genesis))
        self.assertEqual(result.code, "protocol_version_invalid")

    def test_wrong_environment_fails(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        genesis["environment"] = "PRODUCTION"
        result = binding.verify_disposable_network_genesis_json(_wire(genesis))
        self.assertEqual(result.code, "environment_invalid")

    def test_wrong_acknowledgement_fails(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        genesis["acknowledgement"] = "please"
        result = binding.verify_disposable_network_genesis_json(_wire(genesis))
        self.assertEqual(result.code, "acknowledgement_invalid")

    def test_binding_digest_mismatch_fails(self) -> None:
        genesis_result = binding.verify_disposable_network_genesis_json(
            binding.genesis_json_bytes()
        )
        self.assertTrue(genesis_result.ok)
        config = binding.build_disposable_binding_config(genesis_result.genesis_digest)
        result = binding.verify_disposable_network_binding_config_json(
            _wire(config),
            expected_genesis_digest="b" * 64,
        )
        self.assertEqual(result.code, "genesis_digest_invalid")

    def test_handshake_and_ledger_surfaces_reject_main(self) -> None:
        genesis_result = binding.verify_disposable_network_genesis_json(
            binding.genesis_json_bytes()
        )
        handshake = binding.validate_disposable_handshake_identity_binding(
            network_id="MAIN",
            chain_id=genesis_result.chain_id,
            protocol_version=binding.PROTOCOL_VERSION,
            genesis_digest=genesis_result.genesis_digest,
        )
        ledger = binding.validate_disposable_ledger_replay_identity_binding(
            network_id="MAIN",
            chain_id=genesis_result.chain_id,
            protocol_version=binding.PROTOCOL_VERSION,
            genesis_digest=genesis_result.genesis_digest,
        )
        self.assertEqual(handshake.code, "network_id_invalid")
        self.assertEqual(ledger.code, "network_id_invalid")
        self.assertIs(handshake.execution_authorized, False)
        self.assertIs(ledger.execution_authorized, False)

    def test_handshake_surface_accepts_bound_tuple(self) -> None:
        genesis_result = binding.verify_disposable_network_genesis_json(
            binding.genesis_json_bytes()
        )
        result = binding.validate_disposable_handshake_identity_binding(
            network_id=genesis_result.network_id,
            chain_id=genesis_result.chain_id,
            protocol_version=genesis_result.protocol_version,
            genesis_digest=genesis_result.genesis_digest,
        )
        self.assertTrue(result.ok, result.code)


class MalformedAndSizeLimitTests(unittest.TestCase):
    def test_malformed_matrix(self) -> None:
        cases = (
            (object(), "input_type_invalid"),
            (b"x" * (binding.MAX_GENESIS_BYTES + 1), "input_too_large"),
            (bytes([255]), "encoding_invalid"),
            ("{", "json_invalid"),
            ("[]", "invalid_top_level"),
            ('{"x":NaN}', "json_invalid"),
            ('{"a":1,"a":2}', "duplicate_key"),
        )
        for payload, code in cases:
            with self.subTest(code=code):
                result = binding.verify_disposable_network_genesis_json(payload)  # type: ignore[arg-type]
                self.assertEqual(result.code, code)
                self.assertIs(result.execution_authorized, False)
                self.assertNotIn("Traceback", result.code)

    def test_reordered_fields_fail(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        reordered = {name: genesis[name] for name in reversed(list(genesis.keys()))}
        result = binding.verify_disposable_network_genesis_json(_wire(reordered))
        self.assertEqual(result.code, "schema_invalid")

    def test_nested_duplicate_key_fails(self) -> None:
        raw = binding.genesis_json_bytes().decode("utf-8").replace(
            '"hard_cap":28000000',
            '"hard_cap":28000000,"hard_cap":28000000',
            1,
        )
        result = binding.verify_disposable_network_genesis_json(raw)
        self.assertEqual(result.code, "duplicate_key")


class NonActivationAndCleanupTests(unittest.TestCase):
    def test_execution_authorized_true_fails(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        genesis["execution_authorized"] = True
        result = binding.verify_disposable_network_genesis_json(_wire(genesis))
        self.assertEqual(result.code, "execution_authorized_invalid")
        self.assertIs(result.execution_authorized, False)

    def test_temp_dir_artifacts_are_cleaned_up(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        genesis_result = binding.verify_disposable_network_genesis_json(_wire(genesis))
        self.assertTrue(genesis_result.ok)
        root = Path(
            tempfile.mkdtemp(prefix=f"{binding.DATA_DIR_TAG}-")
        )
        try:
            self.assertIn(binding.DATA_DIR_TAG, root.name)
            genesis_path = root / "genesis.json"
            binding_path = root / "binding.json"
            genesis_path.write_bytes(_wire(genesis))
            config = binding.build_disposable_binding_config(genesis_result.genesis_digest)
            binding_path.write_bytes(_wire(config))
            # Core APIs remain bytes-only; tests only use isolated temp files.
            loaded = binding.verify_disposable_network_genesis_json(
                genesis_path.read_bytes()
            )
            self.assertTrue(loaded.ok)
            self.assertEqual(loaded.genesis_digest, genesis_result.genesis_digest)
        finally:
            shutil.rmtree(root)
        self.assertFalse(root.exists())

    def test_module_has_no_network_or_leap28_imports(self) -> None:
        path = Path(binding.__file__)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        modules = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        modules |= {
            (node.module or "").split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        self.assertFalse(
            modules
            & {
                "socket",
                "subprocess",
                "requests",
                "urllib",
                "http",
                "asyncio",
                "wallet",
                "ledger",
                "mining",
            }
        )
        self.assertNotIn("Leap28", source)
        self.assertNotIn("Nova", source)
        self.assertNotIn("load_wallet", source)


class FixtureDigestReportTests(unittest.TestCase):
    def test_report_known_fixture_digests(self) -> None:
        genesis = binding.build_disposable_genesis_document()
        chain_id = binding.compute_disposable_chain_id(
            network_id=binding.NETWORK_ID,
            protocol_version=binding.PROTOCOL_VERSION,
        )
        genesis_digest = binding.compute_disposable_genesis_digest(genesis)
        # Stable fixtures for review reporting / cross-run comparison.
        self.assertEqual(
            chain_id,
            hashlib.sha256(
                binding.PROFILE_DOMAIN
                + binding.NETWORK_ID.encode("utf-8")
                + b"\x00"
                + binding.PROTOCOL_VERSION.encode("utf-8")
            ).hexdigest(),
        )
        result = binding.verify_disposable_network_genesis_json(_wire(genesis))
        self.assertEqual(result.chain_id, chain_id)
        self.assertEqual(result.genesis_digest, genesis_digest)
        # Expose values for the Foundation 39 review summary.
        self._chain_id = chain_id
        self._genesis_digest = genesis_digest


if __name__ == "__main__":
    unittest.main()
