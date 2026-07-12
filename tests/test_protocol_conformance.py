# SPDX-License-Identifier: Apache-2.0
"""Offline Foundation 3 protocol conformance tests. Uses temporary ledgers only."""
from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from coin.ledger import BlocklessLedger
from coin.mining import build_coinbase_tx, build_mint_tx
from coin.tx_validation import (
    L28_EMISSION_CEILING,
    L28_HALVING_INTERVAL,
    L28_HISTORICAL_LAST_ENTRY,
    L28_HISTORICAL_MINED,
    L28_MAX_SUPPLY,
    L28_NEXT_HEIGHT_AFTER_CHECKPOINT,
    L28_REWARD_SCHEDULE,
    TxPolicy,
    compute_tx_id,
    l28_coinbase_reward,
    resolve_tx_id,
    strict_protocol_int,
    validate_transaction,
)


def _run(coro):
    return asyncio.run(coro)


def _temp_ledger(td: str, **kwargs) -> BlocklessLedger:
    req = kwargs.pop("require_signatures", False)
    pol = kwargs.pop("policy", None)
    if pol is None:
        pol = TxPolicy(require_signatures=bool(req))
    return BlocklessLedger(data_dir=td, require_signatures=req, policy=pol, **kwargs)


def _enable_disposable_test_issuance(ledger: BlocklessLedger, *, mint_height: int = 0, issued_supply: int = 0) -> None:
    """Unmistakable test-only opt-in. Never used as a production default."""
    ledger.initialize_disposable_test_issuance_state(
        mint_height=mint_height,
        issued_supply=issued_supply,
        acknowledge_test_only=True,
    )


class TestStrictIntegers(unittest.TestCase):
    def test_reject_bool_true_false(self):
        for v in (True, False):
            got, err = strict_protocol_int(v, field="amount")
            self.assertIsNone(got)
            self.assertEqual(err, "amount_not_int")

    def test_reject_floats(self):
        for v in (1.0, 1.5, -2.2):
            got, err = strict_protocol_int(v, field="amount")
            self.assertIsNone(got)
            self.assertEqual(err, "amount_not_int")

    def test_reject_numeric_strings(self):
        for v in ("1", "0", "-3", "28"):
            got, err = strict_protocol_int(v, field="timestamp")
            self.assertIsNone(got)
            self.assertEqual(err, "timestamp_not_int")

    def test_reject_missing_null(self):
        got, err = strict_protocol_int(None, field="nonce")
        self.assertIsNone(got)
        self.assertEqual(err, "nonce_missing")

    def test_accept_exact_integers(self):
        for v in (0, 1, 28, 210_000, -1, 10**18):
            got, err = strict_protocol_int(v, field="height")
            self.assertEqual(got, v)
            self.assertIsNone(err)

    def test_validate_rejects_bool_amount_transfer(self):
        tx = {
            "sender": "A",
            "receiver": "B",
            "amount": True,
            "timestamp": 1_700_000_000,
        }
        ok, _, reason = validate_transaction(
            tx,
            policy=TxPolicy(require_signatures=False),
            current_balance_lookup=lambda a, n: 100,
            seen_tx_lookup=lambda i: False,
        )
        self.assertFalse(ok)
        self.assertIn("not_int", reason)


class TestEmissionSchedule(unittest.TestCase):
    def test_halving_boundaries(self):
        cases = [
            (0, 28),
            (209_999, 28),
            (210_000, 14),
            (419_999, 14),
            (420_000, 7),
            (629_999, 7),
            (630_000, 3),
            (839_999, 3),
            (840_000, 1),
            (1_049_999, 1),
            (1_050_000, 0),
            (2_000_000, 0),
        ]
        for height, expected in cases:
            self.assertEqual(
                l28_coinbase_reward(height),
                expected,
                msg=f"height={height}",
            )

    def test_total_scheduled_emission(self):
        total = sum(L28_REWARD_SCHEDULE) * L28_HALVING_INTERVAL
        self.assertEqual(total, 11_130_000)
        self.assertEqual(total, L28_EMISSION_CEILING)

    def test_hard_cap_constant(self):
        self.assertEqual(L28_MAX_SUPPLY, 28_000_000)

    def test_reward_zero_coinbase_rejected(self):
        h = 1_050_000
        tx = build_coinbase_tx("miner1", nonce=1, height=h, timestamp=1_700_000_000)
        self.assertEqual(tx["amount"], 0)
        ok, _, reason = validate_transaction(
            tx,
            policy=TxPolicy(require_signatures=False),
            current_balance_lookup=lambda a, n: 0,
            seen_tx_lookup=lambda i: False,
            current_height_lookup=lambda: h,
            current_issued_lookup=lambda: 0,
            now_ts=1_700_000_000,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "coinbase_reward_zero")

    def test_emission_ceiling_rejected(self):
        tx = build_coinbase_tx("miner1", nonce=2, height=0, timestamp=1_700_000_000)
        ok, _, reason = validate_transaction(
            tx,
            policy=TxPolicy(require_signatures=False),
            current_balance_lookup=lambda a, n: 0,
            seen_tx_lookup=lambda i: False,
            current_height_lookup=lambda: 0,
            current_issued_lookup=lambda: L28_EMISSION_CEILING,
            now_ts=1_700_000_000,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "coinbase_emission_ceiling")

    def test_hard_cap_rejected(self):
        # Even if emission ceiling were somehow bypassed, hard cap still applies.
        # Use issued just below hard cap but reward would exceed it.
        tx = build_coinbase_tx("miner1", nonce=3, height=0, timestamp=1_700_000_000)
        ok, _, reason = validate_transaction(
            tx,
            policy=TxPolicy(require_signatures=False),
            current_balance_lookup=lambda a, n: 0,
            seen_tx_lookup=lambda i: False,
            current_height_lookup=lambda: 0,
            current_issued_lookup=lambda: L28_MAX_SUPPLY,
            now_ts=1_700_000_000,
        )
        self.assertFalse(ok)
        self.assertIn(reason, {"coinbase_emission_ceiling", "coinbase_supply_cap"})

    def test_canonical_height_mismatch_rejected(self):
        tx = build_coinbase_tx("miner1", nonce=4, height=210_000, timestamp=1_700_000_000)
        ok, _, reason = validate_transaction(
            tx,
            policy=TxPolicy(require_signatures=False),
            current_balance_lookup=lambda a, n: 0,
            seen_tx_lookup=lambda i: False,
            current_height_lookup=lambda: 0,
            current_issued_lookup=lambda: 0,
            now_ts=1_700_000_000,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "coinbase_height_mismatch")

    def test_no_permanent_minimum_reward(self):
        self.assertEqual(l28_coinbase_reward(1_050_000), 0)
        self.assertEqual(l28_coinbase_reward(10_000_000), 0)


class TestTransactionIdentity(unittest.TestCase):
    def _core_tx(self, **extra):
        tx = {
            "sender": "alice",
            "receiver": "bob",
            "amount": 7,
            "timestamp": 1_700_000_000,
        }
        tx.update(extra)
        return tx

    def test_key_order_independence(self):
        a = {"sender": "a", "receiver": "b", "amount": 1, "timestamp": 10}
        b = {"timestamp": 10, "amount": 1, "receiver": "b", "sender": "a"}
        self.assertEqual(compute_tx_id(a), compute_tx_id(b))

    def test_id_excluded_from_preimage(self):
        tx = self._core_tx()
        id1 = compute_tx_id(tx)
        tx_with_id = dict(tx)
        tx_with_id["id"] = id1
        self.assertEqual(compute_tx_id(tx_with_id), id1)

    def test_builder_excluded_from_identity(self):
        tx = self._core_tx()
        base = compute_tx_id(tx)
        with_builder = dict(tx)
        with_builder["_builder"] = "SHOULD_NOT_AFFECT"
        self.assertEqual(compute_tx_id(with_builder), base)

    def test_signature_affects_identity(self):
        tx = self._core_tx()
        a = compute_tx_id(tx)
        b = compute_tx_id({**tx, "signature": "sig-a"})
        c = compute_tx_id({**tx, "signature": "sig-b"})
        self.assertNotEqual(a, b)
        self.assertNotEqual(b, c)

    def test_mismatched_provided_id_fails_closed(self):
        tx = self._core_tx(id="deadbeef" * 8)
        tx_id, err = resolve_tx_id(tx)
        self.assertIsNone(tx_id)
        self.assertEqual(err, "tx_id_mismatch")
        ok, _, reason = validate_transaction(
            tx,
            policy=TxPolicy(require_signatures=False),
            current_balance_lookup=lambda a, n: 100,
            seen_tx_lookup=lambda i: False,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "tx_id_mismatch")

    def test_protocol_field_mutation_changes_id(self):
        tx = self._core_tx()
        base = compute_tx_id(tx)
        mutated = dict(tx)
        mutated["amount"] = 8
        self.assertNotEqual(compute_tx_id(mutated), base)

    def test_repeated_normalization_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = BlocklessLedger(
                data_dir=td,
                require_signatures=False,
                policy=TxPolicy(require_signatures=False),
            )
            tx = self._core_tx()
            n1 = ledger._normalize_tx(tx)
            n2 = ledger._normalize_tx(n1)
            n3 = ledger._normalize_tx(dict(n2))
            self.assertEqual(n1["id"], n2["id"])
            self.assertEqual(n2["id"], n3["id"])
            self.assertEqual(n1["id"], compute_tx_id(n1))


class TestLedgerIdentityAndReplay(unittest.TestCase):
    def test_stored_id_equals_replay_index_and_replay_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = _temp_ledger(td)
            _enable_disposable_test_issuance(ledger)
            # Fund alice via coinbase
            cb = build_coinbase_tx("alice", nonce=1, height=0, timestamp=1_700_000_000)
            self.assertTrue(_run(ledger.add_transaction(cb)))
            stored_cb = ledger.get_transaction(cb["id"])
            self.assertIsNotNone(stored_cb)
            self.assertEqual(stored_cb["id"], cb["id"])
            self.assertIn(cb["id"], ledger._seen_tx_ids)

            # Exact replay rejected
            self.assertFalse(_run(ledger.add_transaction(dict(cb))))

            transfer = {
                "sender": "alice",
                "receiver": "bob",
                "amount": 1,
                "timestamp": 1_700_000_001,
            }
            transfer["id"] = compute_tx_id(transfer)
            self.assertTrue(_run(ledger.add_transaction(transfer)))
            self.assertEqual(ledger.transactions[transfer["id"]]["id"], transfer["id"])
            self.assertFalse(_run(ledger.add_transaction(dict(transfer))))

    def test_save_reload_preserves_id(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertFalse(str(td).endswith("/data") or "/data/" in str(Path(td)))
            ledger = _temp_ledger(td)
            _enable_disposable_test_issuance(ledger)
            cb = build_coinbase_tx("alice", nonce=9, height=0, timestamp=1_700_000_000)
            self.assertTrue(_run(ledger.add_transaction(cb)))
            tx_id = cb["id"]

            ledger2 = _temp_ledger(td)
            _run(ledger2.load_from_disk())
            loaded = ledger2.get_transaction(tx_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["id"], tx_id)
            self.assertEqual(compute_tx_id(loaded), tx_id)
            # Reload does not grant issuance readiness by itself.
            self.assertFalse(ledger2.is_canonical_issuance_ready())

    def test_legacy_mismatched_record_fails_closed_without_rewrite(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            shard = path / "shard_0.jsonl"
            # Craft a legacy-like record whose stored id does not match canonical projection.
            body = {
                "sender": "alice",
                "receiver": "bob",
                "amount": 1,
                "timestamp": 1_700_000_000,
                "id": "0" * 64,
            }
            shard.write_text(json.dumps(body) + "\n", encoding="utf-8")
            original = shard.read_text(encoding="utf-8")

            ledger = _temp_ledger(td)
            with self.assertRaises(ValueError):
                _run(ledger.load_from_disk())
            # Persisted bytes must be unchanged (no silent migration).
            self.assertEqual(shard.read_text(encoding="utf-8"), original)
            self.assertFalse(ledger.is_canonical_issuance_ready())
            self.assertEqual(ledger.issued_supply, 0)
            self.assertEqual(ledger.total_transactions, 0)

    def test_mismatched_id_rejected_on_add(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = _temp_ledger(td)
            tx = {
                "sender": "alice",
                "receiver": "bob",
                "amount": 1,
                "timestamp": 1_700_000_000,
                "id": "f" * 64,
            }
            self.assertFalse(_run(ledger.add_transaction(tx)))


class TestCanonicalIssuanceGate(unittest.TestCase):
    def test_fresh_default_ledger_rejects_coinbase(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = BlocklessLedger(
                data_dir=td,
                require_signatures=False,
                policy=TxPolicy(require_signatures=False),
            )
            self.assertFalse(ledger.is_canonical_issuance_ready())
            self.assertEqual(ledger.issued_supply, 0)
            self.assertEqual(ledger.mint_height, 0)
            cb = build_coinbase_tx("miner", nonce=1, height=0, timestamp=1_700_000_000)
            self.assertFalse(_run(ledger.add_transaction(cb)))
            self.assertEqual(ledger.issued_supply, 0)
            self.assertEqual(ledger.get_balance("miner"), 0)

    def test_empty_directory_is_not_canonical_genesis(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = _temp_ledger(td)
            _run(ledger.load_from_disk())
            self.assertFalse(ledger.is_canonical_issuance_ready())
            cb = build_coinbase_tx("miner", nonce=2, height=0, timestamp=1_700_000_000)
            self.assertFalse(_run(ledger.add_transaction(cb)))

    def test_missing_canonical_initialization_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = _temp_ledger(td)
            # Manual zero counters without explicit init remain untrusted.
            ledger.mint_height = 0
            ledger.issued_supply = 0
            self.assertFalse(ledger.is_canonical_issuance_ready())
            cb = build_coinbase_tx("miner", nonce=3, height=0, timestamp=1_700_000_000)
            self.assertFalse(_run(ledger.add_transaction(cb)))

    def test_partial_initialization_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = _temp_ledger(td)
            with self.assertRaises(ValueError):
                ledger.initialize_disposable_test_issuance_state(
                    mint_height=0,
                    issued_supply=0,
                    acknowledge_test_only=False,
                )
            with self.assertRaises(TypeError):
                # Missing required acknowledge_test_only
                ledger.initialize_disposable_test_issuance_state(  # type: ignore[call-arg]
                    mint_height=0,
                    issued_supply=0,
                )
            with self.assertRaises(ValueError):
                ledger.initialize_disposable_test_issuance_state(
                    mint_height=True,  # type: ignore[arg-type]
                    issued_supply=0,
                    acknowledge_test_only=True,
                )
            self.assertFalse(ledger.is_canonical_issuance_ready())
            cb = build_coinbase_tx("miner", nonce=4, height=0, timestamp=1_700_000_000)
            self.assertFalse(_run(ledger.add_transaction(cb)))

    def test_explicit_disposable_test_init_allows_height0_schedule(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = _temp_ledger(td)
            _enable_disposable_test_issuance(ledger, mint_height=0, issued_supply=0)
            self.assertTrue(ledger.is_canonical_issuance_ready())
            cb = build_coinbase_tx("miner", nonce=5, height=0, timestamp=1_700_000_000)
            self.assertEqual(cb["amount"], 28)
            self.assertTrue(_run(ledger.add_transaction(cb)))
            self.assertEqual(ledger.get_balance("miner"), 28)
            self.assertEqual(ledger.issued_supply, 28)
            # Default construction elsewhere remains unready.
            other = _temp_ledger(td + "-other")
            self.assertFalse(other.is_canonical_issuance_ready())

    def test_historical_checkpoint_not_auto_minted(self):
        self.assertEqual(L28_HISTORICAL_MINED, 2_824_584)
        self.assertEqual(L28_HISTORICAL_LAST_ENTRY, 100_877)
        self.assertEqual(L28_NEXT_HEIGHT_AFTER_CHECKPOINT, 100_878)
        with tempfile.TemporaryDirectory() as td:
            ledger = _temp_ledger(td)
            self.assertNotEqual(ledger.issued_supply, L28_HISTORICAL_MINED)
            self.assertEqual(ledger.get_balance("anyone"), 0)
            _enable_disposable_test_issuance(ledger)
            cb = build_coinbase_tx("miner", nonce=6, height=0, timestamp=1_700_000_000)
            self.assertTrue(_run(ledger.add_transaction(cb)))
            self.assertEqual(ledger.issued_supply, 28)
            self.assertNotEqual(ledger.issued_supply, L28_HISTORICAL_MINED)
            self.assertEqual(ledger.mint_height, 1)
            self.assertNotEqual(ledger.mint_height, L28_NEXT_HEIGHT_AFTER_CHECKPOINT)

    def test_transfers_still_enforce_balance_and_signatures(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = _temp_ledger(td, require_signatures=True, verify_signature=lambda t: True)
            # Without funding, transfer fails balance even if signatures would pass.
            tx = {
                "sender": "alice",
                "receiver": "bob",
                "amount": 1,
                "timestamp": 1_700_000_000,
                "signature": "sig",
            }
            tx["id"] = compute_tx_id(tx)
            self.assertFalse(_run(ledger.add_transaction(tx)))

            _enable_disposable_test_issuance(ledger)
            cb = build_coinbase_tx("alice", nonce=7, height=0, timestamp=1_700_000_000)
            self.assertTrue(_run(ledger.add_transaction(cb)))

            # Signature required: missing verifier path covered elsewhere; here false verifier.
            ledger2 = _temp_ledger(td + "-sig", require_signatures=True, verify_signature=lambda t: False)
            _enable_disposable_test_issuance(ledger2)
            cb2 = build_coinbase_tx("alice", nonce=8, height=0, timestamp=1_700_000_000)
            self.assertTrue(_run(ledger2.add_transaction(cb2)))
            bad = {
                "sender": "alice",
                "receiver": "bob",
                "amount": 1,
                "timestamp": 1_700_000_001,
                "signature": "sig",
            }
            bad["id"] = compute_tx_id(bad)
            self.assertFalse(_run(ledger2.add_transaction(bad)))

    def test_no_repository_data_dir_usage(self):
        repo_root = Path(__file__).resolve().parents[1]
        repo_data = repo_root / "data"
        with tempfile.TemporaryDirectory(dir=None) as td:
            ledger = _temp_ledger(td)
            self.assertTrue(str(ledger.data_dir.resolve()).startswith(str(Path(td).resolve())))
            self.assertNotEqual(ledger.data_dir.resolve(), repo_data.resolve())
            _enable_disposable_test_issuance(ledger)
            cb = build_coinbase_tx("miner", nonce=9, height=0, timestamp=1_700_000_000)
            self.assertTrue(_run(ledger.add_transaction(cb)))
            for p in Path(td).rglob("*"):
                self.assertTrue(str(p.resolve()).startswith(str(Path(td).resolve())))


class TestSignatures(unittest.TestCase):
    def _funded_ledger(self, td: str, verify_signature=None, require_signatures=True):
        ledger = BlocklessLedger(
            data_dir=td,
            require_signatures=require_signatures,
            policy=TxPolicy(require_signatures=require_signatures),
            verify_signature=verify_signature,
        )
        _enable_disposable_test_issuance(ledger)
        cb = build_coinbase_tx("alice", nonce=11, height=0, timestamp=1_700_000_000)
        self.assertTrue(_run(ledger.add_transaction(cb)))
        return ledger

    def test_nonempty_string_alone_not_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            # require signatures, no verifier injected
            ledger = self._funded_ledger(td, verify_signature=None, require_signatures=True)
            tx = {
                "sender": "alice",
                "receiver": "bob",
                "amount": 1,
                "timestamp": 1_700_000_010,
                "signature": "not-cryptographic",
            }
            tx["id"] = compute_tx_id(tx)
            self.assertFalse(_run(ledger.add_transaction(tx)))

    def test_missing_verifier_fails_closed(self):
        tx = {
            "sender": "alice",
            "receiver": "bob",
            "amount": 1,
            "timestamp": 1_700_000_010,
            "signature": "anything",
        }
        ok, _, reason = validate_transaction(
            tx,
            policy=TxPolicy(require_signatures=True),
            current_balance_lookup=lambda a, n: 100,
            seen_tx_lookup=lambda i: False,
            verify_signature=None,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "signature_required_missing_verifier")

    def test_verifier_exception_fails_closed(self):
        def boom(_tx):
            raise RuntimeError("boom")

        tx = {
            "sender": "alice",
            "receiver": "bob",
            "amount": 1,
            "timestamp": 1_700_000_010,
            "signature": "x",
        }
        ok, _, reason = validate_transaction(
            tx,
            policy=TxPolicy(require_signatures=True),
            current_balance_lookup=lambda a, n: 100,
            seen_tx_lookup=lambda i: False,
            verify_signature=boom,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "signature_verify_error")

    def test_false_verifier_rejects(self):
        tx = {
            "sender": "alice",
            "receiver": "bob",
            "amount": 1,
            "timestamp": 1_700_000_010,
            "signature": "x",
        }
        ok, _, reason = validate_transaction(
            tx,
            policy=TxPolicy(require_signatures=True),
            current_balance_lookup=lambda a, n: 100,
            seen_tx_lookup=lambda i: False,
            verify_signature=lambda t: False,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "bad_signature")

    def test_true_verifier_accepts_funded_transfer(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = self._funded_ledger(
                td,
                verify_signature=lambda t: True,
                require_signatures=True,
            )
            tx = {
                "sender": "alice",
                "receiver": "bob",
                "amount": 1,
                "timestamp": 1_700_000_010,
                "signature": "offline-test-sig",
            }
            tx["id"] = compute_tx_id(tx)
            self.assertTrue(_run(ledger.add_transaction(tx)))
            self.assertEqual(ledger.get_balance("bob"), 1)

    def test_policy_ledger_signature_disagreement_fails(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                BlocklessLedger(
                    data_dir=td,
                    policy=TxPolicy(require_signatures=False),
                    require_signatures=True,
                )


class TestMintBoundary(unittest.TestCase):
    def test_ledger_mint_disabled(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = BlocklessLedger(
                data_dir=td,
                require_signatures=False,
                policy=TxPolicy(require_signatures=False),
            )
            with self.assertRaises(RuntimeError):
                _run(ledger.mint("x", 1, 1_700_000_000, "MAIN"))

    def test_build_mint_tx_disabled(self):
        with self.assertRaises(RuntimeError):
            build_mint_tx("x", 100, nonce=1, timestamp=1_700_000_000)

    def test_build_coinbase_has_no_builder_metadata(self):
        tx = build_coinbase_tx("miner", nonce=1, height=0, timestamp=1_700_000_000)
        self.assertNotIn("_builder", tx)
        self.assertEqual(tx["id"], compute_tx_id(tx))
        self.assertEqual(tx["amount"], 28)


if __name__ == "__main__":
    unittest.main()
