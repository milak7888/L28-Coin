# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

log = logging.getLogger("l28.tx_validation")

# --- protocol invariants (canonical economic record)
L28_MAX_SUPPLY: int = 28_000_000
L28_EMISSION_CEILING: int = 11_130_000
L28_HALVING_INTERVAL: int = 210_000
L28_MAX_COINBASE_REWARD: int = 28
L28_REWARD_SCHEDULE: Tuple[int, ...] = (28, 14, 7, 3, 1)

# Historical allocation checkpoint (reference only; NOT auto-loaded into runtime state).
# Loading into balances/ledger requires a separately reviewed genesis/bootstrap milestone.
L28_HISTORICAL_MINED: int = 2_824_584
L28_HISTORICAL_LAST_ENTRY: int = 100_877
L28_NEXT_HEIGHT_AFTER_CHECKPOINT: int = 100_878

# Protocol-reserved pseudo-accounts (MUST NOT be usable for normal transfers)
RESERVED_SENDERS = {"COINBASE", "__MINT__"}

# Implementation-only fields excluded from the transaction-identity preimage.
# `id` must never hash itself. `_builder` is builder metadata, not protocol state.
_TX_ID_EXCLUDED_FIELDS = frozenset({"id", "_builder"})


@dataclass(frozen=True)
class TxPolicy:
    """
    Keep this minimal + stable. Smoke/invariants build a policy dynamically.
    """
    require_signatures: bool = False
    max_tx_amount: int = 10_000_000_000
    min_tx_amount: int = 1


def strict_protocol_int(value: Any, *, field: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Accept only exact built-in integers.
    Reject bool (subclass of int), float, numeric strings, null, and other types.
    """
    if value is None:
        return None, f"{field}_missing"
    if isinstance(value, bool):
        return None, f"{field}_not_int"
    if type(value) is not int:
        return None, f"{field}_not_int"
    return value, None


def transaction_identity_projection(tx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Canonical projection for transaction identity.
    Excludes only the derived id and explicit implementation-only builder metadata.
    All other fields present on the transaction, including signature, affect identity.
    """
    if not isinstance(tx, dict):
        raise TypeError("transaction must be a dict")
    return {k: v for k, v in tx.items() if k not in _TX_ID_EXCLUDED_FIELDS}


def compute_tx_id(tx: Dict[str, Any]) -> str:
    """
    Deterministic transaction id from the identity projection.

    Serialization practice (implementation behavior subordinate to PROTOCOL.md):
      UTF-8 JSON, recursively sorted keys, compact separators, ensure_ascii=False,
      allow_nan=False, SHA-256 lowercase hex digest.
    """
    projected = transaction_identity_projection(tx)
    blob = json.dumps(
        projected,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def resolve_tx_id(tx: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve canonical transaction id without mutating the transaction.

    Returns (tx_id, error_reason).
    - Missing/empty id: return computed id (caller MAY populate).
    - Non-empty mismatched id: fail closed.
    """
    if not isinstance(tx, dict):
        return None, "tx_not_dict"
    try:
        computed = compute_tx_id(tx)
    except (TypeError, ValueError, OverflowError) as e:
        return None, f"tx_id_compute_error:{type(e).__name__}"

    provided = tx.get("id")
    if provided is None or provided == "":
        return computed, None
    if str(provided) != computed:
        return None, "tx_id_mismatch"
    return computed, None


def stable_address_shard(address: str, shard_count: int = 28) -> int:
    """
    Public API: deterministic shard assignment for an address.
    This is NOT a consensus rule by itself; it's a stable mapping helper used by the ledger.

    shard_count default=28 to match L28 naming; callers may override.
    """
    sc = int(shard_count) if int(shard_count) > 0 else 1
    h = hashlib.sha256(str(address).encode("utf-8")).digest()
    n = int.from_bytes(h[:8], "big", signed=False)
    return int(n % sc)


def is_coinbase_tx(tx: Dict[str, Any]) -> bool:
    """
    Public API: strict coinbase identity.
    """
    try:
        return (
            str(tx.get("sender")) == "COINBASE"
            and str(tx.get("type")) == "coinbase"
            and bool(tx.get("coinbase")) is True
        )
    except Exception:
        return False


def l28_coinbase_reward(height: int) -> int:
    """
    Canonical reward schedule from the documented L28 economic record.

    Halving interval: 210,000
    Sequence: 28 → 14 → 7 → 3 → 1 → 0

    height 0 .. 209,999       -> 28
    height 210,000 .. 419,999 -> 14
    height 420,000 .. 629,999 -> 7
    height 630,000 .. 839,999 -> 3
    height 840,000 .. 1,049,999 -> 1
    height 1,050,000+         -> 0

    Complete scheduled emission:
      (28 + 14 + 7 + 3 + 1) * 210,000 = 11,130,000
    """
    if isinstance(height, bool) or type(height) is not int:
        return 0
    h = height
    if h < 0:
        return 0
    epoch = h // int(L28_HALVING_INTERVAL)
    if epoch >= len(L28_REWARD_SCHEDULE):
        return 0
    return int(L28_REWARD_SCHEDULE[epoch])


def validate_transaction(
    tx: Dict[str, Any],
    *,
    policy: Optional[TxPolicy],
    current_balance_lookup: Callable[[str, str], int],
    seen_tx_lookup: Callable[[str], bool],
    verify_signature: Optional[Callable[..., Any]] = None,
    now_ts: Optional[int] = None,
    current_issued_lookup: Optional[Callable[[], int]] = None,
    current_height_lookup: Optional[Callable[[], int]] = None,
    network: str = "MAIN",
) -> Tuple[bool, str, str]:
    """
    Returns: (ok, tx_id, reason)

    FAIL-CLOSED RULE:
      For coinbase validation, required consensus lookups MUST be present; otherwise reject.
    """
    if not isinstance(tx, dict):
        return False, "", "tx_not_dict"

    tx_id, id_err = resolve_tx_id(tx)
    if id_err is not None or not tx_id:
        return False, tx_id or "", id_err or "tx_id_unavailable"

    # replay guard (canonical id)
    try:
        if callable(seen_tx_lookup) and bool(seen_tx_lookup(tx_id)):
            return False, tx_id, "replay"
    except Exception:
        return False, tx_id, "replay_lookup_error"

    pol = policy or TxPolicy()

    sender = tx.get("sender")
    receiver = tx.get("receiver")

    # reserved sender misuse MUST reject unless strict coinbase
    if str(sender) in RESERVED_SENDERS and not is_coinbase_tx(tx):
        return False, tx_id, "reserved_sender_misuse"

    # --- COINBASE PATH (issuance)
    if is_coinbase_tx(tx):
        if current_height_lookup is None or current_issued_lookup is None:
            return False, tx_id, "missing_consensus_lookups"

        try:
            raw_h = current_height_lookup()
        except Exception:
            return False, tx_id, "canonical_height_unavailable"
        canonical_h, h_err = strict_protocol_int(raw_h, field="canonical_height")
        if h_err is not None or canonical_h is None:
            return False, tx_id, "canonical_height_unavailable"

        try:
            raw_issued = current_issued_lookup()
        except Exception:
            return False, tx_id, "issued_supply_unavailable"
        issued, issued_err = strict_protocol_int(raw_issued, field="issued_supply")
        if issued_err is not None or issued is None:
            return False, tx_id, "issued_supply_unavailable"

        miner = tx.get("miner") or tx.get("miner_address") or tx.get("to") or receiver
        nonce, nonce_err = strict_protocol_int(tx.get("nonce"), field="nonce")
        height_field, height_err = strict_protocol_int(tx.get("height"), field="height")
        ts, ts_err = strict_protocol_int(tx.get("timestamp"), field="timestamp")

        if not isinstance(receiver, str) or not receiver:
            return False, tx_id, "coinbase_missing_receiver"
        if not isinstance(miner, str) or not miner:
            return False, tx_id, "coinbase_missing_miner"
        if receiver != miner:
            return False, tx_id, "coinbase_receiver_mismatch"
        if nonce_err is not None or nonce is None:
            return False, tx_id, nonce_err or "coinbase_missing_nonce"
        if ts_err is not None or ts is None:
            return False, tx_id, ts_err or "coinbase_missing_timestamp"
        if now_ts is not None:
            now_i, now_err = strict_protocol_int(now_ts, field="now_ts")
            if now_err is None and now_i is not None and ts > int(now_i) + 60:
                return False, tx_id, "coinbase_timestamp_in_future"
        if height_err is not None or height_field is None:
            return False, tx_id, height_err or "coinbase_missing_height"

        # MUST match canonical consensus height (protocol invariant)
        if int(height_field) != int(canonical_h):
            return False, tx_id, "coinbase_height_mismatch"

        amount, amount_err = strict_protocol_int(tx.get("amount"), field="amount")
        if amount_err is not None or amount is None:
            return False, tx_id, amount_err or "coinbase_amount_not_int"

        reward = int(l28_coinbase_reward(int(canonical_h)))

        # No issuance when scheduled reward is zero
        if reward <= 0:
            return False, tx_id, "coinbase_reward_zero"

        if int(amount) != int(reward):
            return False, tx_id, "coinbase_bad_reward"

        if int(amount) > int(L28_MAX_COINBASE_REWARD):
            return False, tx_id, "coinbase_reward_exceeds_max"

        # Emission ceiling and hard cap
        if int(issued) + int(reward) > int(L28_EMISSION_CEILING):
            return False, tx_id, "coinbase_emission_ceiling"
        if int(issued) + int(reward) > int(L28_MAX_SUPPLY):
            return False, tx_id, "coinbase_supply_cap"

        return True, tx_id, "ok"

    # --- TRANSFER PATH (non-coinbase)
    if not isinstance(sender, str) or not sender:
        return False, tx_id, "missing_sender"
    if not isinstance(receiver, str) or not receiver:
        return False, tx_id, "missing_receiver"

    amount, amount_err = strict_protocol_int(tx.get("amount"), field="amount")
    if amount_err is not None or amount is None:
        return False, tx_id, amount_err or "amount_not_int"
    if amount < int(pol.min_tx_amount):
        return False, tx_id, "amount_too_small"
    if amount > int(pol.max_tx_amount):
        return False, tx_id, "amount_too_large"

    ts, ts_err = strict_protocol_int(tx.get("timestamp"), field="timestamp")
    if ts_err is not None or ts is None:
        return False, tx_id, ts_err or "missing_timestamp"
    if now_ts is not None:
        now_i, now_err = strict_protocol_int(now_ts, field="now_ts")
        if now_err is None and now_i is not None and ts > int(now_i) + 60:
            return False, tx_id, "timestamp_in_future"

    # Policy-controlled signatures for non-coinbase transfers.
    # Non-empty signature strings are NOT cryptographic proof.
    if bool(pol.require_signatures):
        if verify_signature is None:
            return False, tx_id, "signature_required_missing_verifier"
        try:
            ok = bool(verify_signature(tx))
        except Exception:
            return False, tx_id, "signature_verify_error"
        if not ok:
            return False, tx_id, "bad_signature"

    # balance check
    try:
        bal = int(current_balance_lookup(str(sender), network))
    except Exception:
        return False, tx_id, "balance_lookup_error"
    if bal < int(amount):
        return False, tx_id, "insufficient_balance"

    return True, tx_id, "ok"
