"""
Complete Blockless Ledger System
Sharded across 5 segments for manageability

Hardened for validator/reserve use:
- deterministic shard mapping (sha256) instead of Python hash()
- canonical transaction id (stable projection; id excluded from preimage)
- replay protection on the canonical id
- validation gate before state mutation
- fail-closed signature enforcement when signatures are required
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .tx_validation import (
    TxPolicy,
    compute_tx_id,
    is_coinbase_tx,
    resolve_tx_id,
    stable_address_shard,
    strict_protocol_int,
    validate_transaction,
)

logger = logging.getLogger(__name__)

# Explicit init kinds. Default (None) means issuance is not ready.
_ISSUANCE_INIT_DISPOSABLE_TEST = "disposable_test_only"


class BlocklessLedger:
    """
    Blockless Ledger with Sharding

    No blockchain - just events with:
    - shards for scalability
    - Balance tracking (account model)
    - Transaction history
    """

    def __init__(
        self,
        data_dir: str = "data/ledger",
        *,
        num_shards: int = 5,
        policy: Optional[TxPolicy] = None,
        verify_signature: Optional[Callable[[Dict[str, Any]], bool]] = None,
        require_signatures: Optional[bool] = True,
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.num_shards = int(num_shards)
        if self.num_shards <= 0:
            raise ValueError("num_shards must be positive")

        # Unify signature policy: ledger flag and TxPolicy must not silently disagree.
        base_policy = policy or TxPolicy()
        if require_signatures is not None:
            if policy is not None and bool(policy.require_signatures) != bool(require_signatures):
                raise ValueError(
                    "require_signatures disagrees with TxPolicy.require_signatures"
                )
            self.policy = replace(base_policy, require_signatures=bool(require_signatures))
        else:
            self.policy = base_policy

        self.require_signatures = bool(self.policy.require_signatures)
        # Do not install a presence-only default verifier. Missing verifier fails closed
        # inside validate_transaction when signatures are required.
        self.verify_signature = verify_signature

        # Shards: each shard is an append-only JSONL file plus in-memory list
        self.shards: List[List[Dict[str, Any]]] = [[] for _ in range(self.num_shards)]

        # Balance tracking
        self.balances: defaultdict[str, int] = defaultdict(int)

        # Transaction index / replay protection (keyed by canonical tx id)
        self.transactions: Dict[str, Dict[str, Any]] = {}
        self._seen_tx_ids: set[str] = set()

        # Stats
        self.total_transactions = 0
        self.total_volume = 0

        # Canonical mint height (coinbase emission height)
        # HARDENED: LEDGER_MINT_HEIGHT_V1
        self.mint_height: int = 0
        # Issued supply (coinbase/mint only)
        self.issued_supply: int = 0

        # Main-network coinbase MUST fail closed until canonical issuance state is
        # explicitly initialized. Empty directories / zero counters are NOT trusted genesis.
        self._canonical_issuance_ready: bool = False
        self._issuance_init_kind: Optional[str] = None

        # In-process concurrency guard
        self._lock = asyncio.Lock()

    def is_canonical_issuance_ready(self) -> bool:
        """True only after an explicit trusted issuance-state initialization."""
        return bool(self._canonical_issuance_ready)

    def initialize_disposable_test_issuance_state(
        self,
        *,
        mint_height: int,
        issued_supply: int,
        acknowledge_test_only: bool,
    ) -> None:
        """
        Explicit disposable TEST-ONLY issuance-state initialization.

        This is never the default. It does not load historical balances, does not
        create genesis_state.json, and does not mark empty directories as main-network
        genesis. Callers MUST pass acknowledge_test_only=True.

        Historical checkpoint values (2,824,584 mined / entry 100,877 / next height
        100,878) are NOT installed by this method.
        """
        if acknowledge_test_only is not True:
            raise ValueError(
                "initialize_disposable_test_issuance_state requires "
                "acknowledge_test_only=True (test-only opt-in)"
            )
        h, h_err = strict_protocol_int(mint_height, field="mint_height")
        s, s_err = strict_protocol_int(issued_supply, field="issued_supply")
        if h_err is not None or h is None:
            raise ValueError(f"invalid_mint_height:{h_err}")
        if s_err is not None or s is None:
            raise ValueError(f"invalid_issued_supply:{s_err}")
        if h < 0 or s < 0:
            raise ValueError("mint_height and issued_supply must be >= 0")

        self.mint_height = int(h)
        self.issued_supply = int(s)
        self._canonical_issuance_ready = True
        self._issuance_init_kind = _ISSUANCE_INIT_DISPOSABLE_TEST
        logger.info(
            "Disposable TEST-ONLY issuance state initialized "
            "(mint_height=%s issued_supply=%s); not main-network genesis",
            self.mint_height,
            self.issued_supply,
        )

    def get_shard_for_address(self, address: str) -> int:
        """Deterministic shard assignment (stable across runs / machines)."""
        return stable_address_shard(address, self.num_shards)

    def _seen_tx_lookup(self, tx_id: str) -> bool:
        return tx_id in self._seen_tx_ids

    def _current_balance_lookup(self, address: str, network: str = "MAIN") -> int:
        return int(self.balances.get(address, 0))

    def _normalize_tx(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize transaction identity idempotently.

        - Missing/empty id MAY be populated with the canonical computed id.
        - Non-empty mismatched id MUST fail closed (never silently replaced).
        - Repeated normalization MUST yield the same id.
        """
        if not isinstance(transaction, dict):
            raise TypeError("transaction must be a dict")
        tx = dict(transaction)

        # timestamp hard default only when absent or not an exact int
        if "timestamp" not in tx or type(tx.get("timestamp")) is not int or isinstance(tx.get("timestamp"), bool):
            tx["timestamp"] = int(time.time())

        tx_id, err = resolve_tx_id(tx)
        if err == "tx_id_mismatch":
            raise ValueError("tx_id_mismatch: provided id does not match canonical identity")
        if err is not None or not tx_id:
            raise ValueError(f"tx_id_unavailable: {err}")

        provided = tx.get("id")
        if provided is None or provided == "":
            tx["id"] = tx_id
        elif str(provided) != tx_id:
            raise ValueError("tx_id_mismatch: provided id does not match canonical identity")
        else:
            tx["id"] = tx_id

        # Idempotency check: recomputing must not change the id.
        again = compute_tx_id(tx)
        if again != tx["id"]:
            raise ValueError("tx_id_non_idempotent")
        return tx

    def _is_coinbase_tx(self, tx: Dict[str, Any]) -> bool:
        """
        HARDENED: DISABLE_DIRECT_MINT_V1

        Strict coinbase detector (single source of truth).
        Delegates to tx_validation.is_coinbase_tx (fail-closed, 3-signal identity).
        """
        try:
            return bool(is_coinbase_tx(tx))
        except Exception:
            return False

    async def add_transaction(self, transaction: Dict[str, Any]) -> bool:
        """
        Add transaction to ledger (validator safe)

        Enforces:
        - canonical tx id
        - replay protection
        - signature requirement (policy / ledger unified)
        - balance check (account model)
        """
        async with self._lock:
            try:
                tx = self._normalize_tx(transaction)

                # Coinbase issuance requires explicit canonical issuance readiness.
                # Empty dirs / zero counters / network labels alone are insufficient.
                if is_coinbase_tx(tx) and not self.is_canonical_issuance_ready():
                    logger.warning(
                        "❌ Reject coinbase: canonical_issuance_state_uninitialized"
                    )
                    return False

                # Validation gate.
                # Canonical emission height is provided via current_height_lookup only.
                # Do NOT rewrite tx["height"]: mutating height would change transaction
                # identity and break exact-replay protection.
                ok, tx_id, reason = validate_transaction(
                    tx,
                    policy=self.policy,
                    current_balance_lookup=self._current_balance_lookup,
                    seen_tx_lookup=self._seen_tx_lookup,
                    verify_signature=(self.verify_signature if self.require_signatures else None),
                    current_height_lookup=(lambda: int(getattr(self, "mint_height", 0))),
                    current_issued_lookup=(lambda: getattr(self, "issued_supply", None)),
                    now_ts=int(time.time()),
                )

                if not ok:
                    logger.warning("❌ Reject tx id=%s reason=%s", tx_id or tx.get("id", ""), reason)
                    return False

                # Stored id, replay-index key, and lookup key MUST match.
                if str(tx.get("id")) != str(tx_id):
                    logger.warning("❌ Reject tx: stored id diverges from validation id")
                    return False

                is_coinbase = bool(is_coinbase_tx(tx))
                sender = str(tx["sender"])
                receiver = str(tx["receiver"])
                amount = int(tx["amount"])
                shard_id = self.get_shard_for_address(receiver if is_coinbase else sender)

                # Persist the validated event before exposing its state transition.
                # A failed append must not leave trusted memory ahead of durable state.
                await self._save_transaction(tx, shard_id)

                if is_coinbase:
                    self.balances[receiver] += amount
                    self.mint_height += 1
                    self.issued_supply += int(amount)
                else:
                    self.balances[sender] -= amount
                    self.balances[receiver] += amount

                self.shards[shard_id].append(tx)

                self.transactions[tx_id] = tx
                self._seen_tx_ids.add(tx_id)

                self.total_transactions += 1
                self.total_volume += amount

                if is_coinbase:
                    logger.info(
                        "✅ Coinbase %s credited %s (+%s) shard=%s",
                        tx_id,
                        receiver,
                        amount,
                        shard_id,
                    )
                else:
                    logger.info("✅ Transaction %s added to shard %s", tx_id, shard_id)
                return True

            except ValueError as e:
                logger.warning("❌ Reject tx: %s", e)
                return False
            except Exception as e:
                logger.exception("add_transaction failed: %s", e)
                return False

    def get_balance(self, address: str) -> int:
        """Get current balance for address"""
        return int(self.balances.get(address, 0))

    def get_transaction(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction by ID"""
        return self.transactions.get(tx_id)

    def get_transaction_history(self, address: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get transaction history for address.

        NOTE: We shard by sender, so receiver-side lookups require scanning.
        With a small shard count this is cheap and correct.
        """
        addr = str(address)
        history: List[Dict[str, Any]] = []
        for shard in self.shards:
            for tx in shard:
                if tx.get("sender") == addr or tx.get("receiver") == addr:
                    history.append(tx)

        history.sort(key=lambda x: int(x.get("timestamp", 0)), reverse=True)
        return history[: int(limit)]

    async def _save_transaction(self, transaction: Dict[str, Any], shard_id: int) -> None:
        """Append one canonical JSON event and durably flush it before state mutation."""
        shard_file = self.data_dir / f"shard_{int(shard_id)}.jsonl"
        with open(shard_file, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    transaction,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                )
                + "\n"
            )
            f.flush()
            os.fsync(f.fileno())

    async def load_from_disk(
        self,
        *,
        validate_replay: bool = False,
        acknowledge_disposable_test_only: bool = False,
        expected_network: Optional[str] = None,
        validate_record: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> None:
        """
        Load ledger from disk on startup.

        Rebuilds:
        - shard lists
        - tx index
        - balances (account model replay)

        Legacy mismatched ids fail closed without rewriting persisted records.

        Default/legacy loading preserves the historical behavior: disk contents
        alone do NOT establish canonical issuance readiness.

        The opt-in disposable replay mode requires an explicit test-only
        acknowledgement and expected network. It re-runs the canonical validator,
        signature verifier, optional exact-schema callback, shard mapping, replay
        checks, and issuance rules for every persisted event before committing any
        in-memory state. Successful validated disposable replay restores only
        disposable issuance readiness; it never establishes main-network history.

        On any load failure, in-memory state is reset to empty and unready (no
        partial trusted state).
        """
        async with self._lock:
            logger.info("Loading ledger from disk...")

            if validate_replay:
                if acknowledge_disposable_test_only is not True:
                    raise ValueError("validated_replay_requires_test_only_acknowledgement")
                if not isinstance(expected_network, str) or not expected_network:
                    raise ValueError("validated_replay_requires_expected_network")
                if validate_record is not None and not callable(validate_record):
                    raise ValueError("validated_replay_record_validator_invalid")

            # Scratch buffers: commit only after full successful parse.
            shards: List[List[Dict[str, Any]]] = [[] for _ in range(self.num_shards)]
            balances: defaultdict[str, int] = defaultdict(int)
            transactions: Dict[str, Dict[str, Any]] = {}
            seen_tx_ids: set[str] = set()
            total_transactions = 0
            total_volume = 0
            issued_supply = 0
            mint_height = 0

            try:
                if validate_replay:
                    expected_shard_names = {
                        f"shard_{shard_id}.jsonl"
                        for shard_id in range(self.num_shards)
                    }
                    for candidate in self.data_dir.glob("shard_*.jsonl"):
                        if (
                            candidate.name not in expected_shard_names
                            or candidate.is_symlink()
                        ):
                            raise ValueError(
                                "validated_replay_unexpected_shard_file "
                                f"name={candidate.name}"
                            )
                for shard_id in range(self.num_shards):
                    shard_file = self.data_dir / f"shard_{shard_id}.jsonl"
                    if not shard_file.exists():
                        continue

                    with open(shard_file, "r", encoding="utf-8") as f:
                        for line_no, line in enumerate(f, start=1):
                            if not line.strip():
                                if validate_replay:
                                    raise ValueError(
                                        f"validated_replay_blank_record shard={shard_id} "
                                        f"line={line_no}"
                                    )
                                continue
                            if validate_replay and not line.endswith("\n"):
                                raise ValueError(
                                    f"validated_replay_truncated_record shard={shard_id} "
                                    f"line={line_no}"
                                )
                            tx = json.loads(line)
                            if not isinstance(tx, dict):
                                raise ValueError(
                                    f"legacy_ledger_invalid_record shard={shard_id} line={line_no}"
                                )

                            tx_id, err = resolve_tx_id(tx)
                            if err is not None or not tx_id:
                                raise ValueError(
                                    f"legacy_tx_id_mismatch_or_invalid shard={shard_id} "
                                    f"line={line_no} reason={err}"
                                )
                            if str(tx.get("id", "")) != str(tx_id):
                                raise ValueError(
                                    f"legacy_tx_id_mismatch shard={shard_id} line={line_no}"
                                )

                            if validate_replay:
                                canonical_line = json.dumps(
                                    tx,
                                    sort_keys=True,
                                    separators=(",", ":"),
                                    ensure_ascii=False,
                                    allow_nan=False,
                                )
                                if line[:-1] != canonical_line:
                                    raise ValueError(
                                        f"validated_replay_noncanonical_record shard={shard_id} "
                                        f"line={line_no}"
                                    )
                                if tx.get("network") != expected_network:
                                    raise ValueError(
                                        f"validated_replay_wrong_network shard={shard_id} "
                                        f"line={line_no}"
                                    )
                                if validate_record is not None:
                                    try:
                                        record_ok = validate_record(tx)
                                    except Exception as exc:
                                        raise ValueError(
                                            f"validated_replay_record_invalid shard={shard_id} "
                                            f"line={line_no}"
                                        ) from exc
                                    if record_ok is not True:
                                        raise ValueError(
                                            f"validated_replay_record_invalid shard={shard_id} "
                                            f"line={line_no}"
                                        )

                                sender = str(tx.get("sender", ""))
                                receiver = str(tx.get("receiver", ""))
                                coinbase = self._is_coinbase_tx(tx)
                                expected_shard = self.get_shard_for_address(
                                    receiver if coinbase else sender
                                )
                                if expected_shard != shard_id:
                                    raise ValueError(
                                        f"validated_replay_wrong_shard shard={shard_id} "
                                        f"line={line_no}"
                                    )

                                ok, validated_id, reason = validate_transaction(
                                    tx,
                                    policy=self.policy,
                                    current_balance_lookup=(
                                        lambda address, _network: int(
                                            balances.get(address, 0)
                                        )
                                    ),
                                    seen_tx_lookup=(lambda candidate: candidate in seen_tx_ids),
                                    verify_signature=(
                                        self.verify_signature
                                        if self.require_signatures
                                        else None
                                    ),
                                    current_height_lookup=(lambda: int(mint_height)),
                                    current_issued_lookup=(lambda: issued_supply),
                                    now_ts=int(time.time()),
                                    network=expected_network,
                                )
                                if not ok or validated_id != tx_id:
                                    raise ValueError(
                                        f"validated_replay_rejected shard={shard_id} "
                                        f"line={line_no} reason={reason}"
                                    )

                            if tx_id in seen_tx_ids:
                                if validate_replay:
                                    raise ValueError(
                                        f"validated_replay_duplicate shard={shard_id} "
                                        f"line={line_no}"
                                    )
                                continue

                            shards[shard_id].append(tx)
                            transactions[tx_id] = tx
                            seen_tx_ids.add(tx_id)

                            sender = str(tx.get("sender", ""))
                            receiver = str(tx.get("receiver", ""))
                            amount = int(tx.get("amount", 0) or 0)
                            is_coinbase = self._is_coinbase_tx(tx)

                            if is_coinbase:
                                mint_height += 1
                                issued_supply += int(amount)

                            if sender and (not is_coinbase):
                                balances[sender] -= amount
                            if receiver:
                                balances[receiver] += amount

                            total_transactions += 1
                            total_volume += amount

                # Commit scratch → live only after every record succeeds.
                self.shards = shards
                self.balances = balances
                self.transactions = transactions
                self._seen_tx_ids = seen_tx_ids
                self.total_transactions = total_transactions
                self.total_volume = total_volume
                self.issued_supply = issued_supply
                self.mint_height = mint_height
                self._canonical_issuance_ready = bool(validate_replay)
                self._issuance_init_kind = (
                    _ISSUANCE_INIT_DISPOSABLE_TEST if validate_replay else None
                )

                logger.info("✅ Loaded %s transactions from disk", self.total_transactions)
            except Exception:
                # Fail closed: no partial trusted in-memory state.
                self.shards = [[] for _ in range(self.num_shards)]
                self.balances = defaultdict(int)
                self.transactions = {}
                self._seen_tx_ids = set()
                self.total_transactions = 0
                self.total_volume = 0
                self.issued_supply = 0
                self.mint_height = 0
                self._canonical_issuance_ready = False
                self._issuance_init_kind = None
                raise

    def get_ledger_stats(self) -> Dict[str, Any]:
        """Get ledger statistics"""
        return {
            "total_transactions": int(self.total_transactions),
            "total_volume": int(self.total_volume),
            "unique_addresses": int(len(self.balances)),
            "shards": int(self.num_shards),
            "transactions_per_shard": [len(shard) for shard in self.shards],
        }

    async def mint(self, receiver: str, amount: int, timestamp: int, network: str) -> bool:
        """
        HARDENED: DISABLE_DIRECT_MINT_V1

        Direct minting is disabled.
        Reason: the old mint() path bypassed validate_transaction() and could be used to exceed invariants.

        Protocol rule:
        - All issuance MUST be expressed as a STRICT coinbase tx and must pass tx_validation + supply cap.
        - Route issuance through consensus/ledger add_transaction() using sender='COINBASE', type='coinbase', coinbase=True.
        """
        raise RuntimeError(
            "mint() disabled (hardening): use strict coinbase tx via consensus pipeline"
        )
