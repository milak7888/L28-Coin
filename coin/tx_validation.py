# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

log = logging.getLogger("l28.tx_validation")

# --- protocol invariants
L28_MAX_SUPPLY: int = 28_000_000
L28_HALVING_INTERVAL: int = 100_000
L28_MAX_COINBASE_REWARD: int = 50

# Protocol-reserved pseudo-accounts (MUST NOT be usable for normal transfers)
RESERVED_SENDERS = {"COINBASE", "__MINT__"}


@dataclass(frozen=True)
class TxPolicy:
    """
    Keep this minimal + stable. Smoke/invariants build a policy dynamically.
    """
    require_signatures: bool = False
    max_tx_amount: int = 10_000_000_000
    min_tx_amount: int = 1


def _as_int(v: Any) -> Optional[int]:
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None


def compute_tx_id(tx: Dict[str, Any]) -> str:
    """
    Public API: deterministic tx id from canonical JSON encoding.
    """
    blob = json.dumps(tx, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


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
    Deterministic reward schedule.
    Observed behavior (your logs):
      Reward(0)=50
      Reward(99999)=50
      Reward(100000)=25
    => halving every 100,000 blocks.

    Floor at 1 to preserve mineability.
    """
    h = int(height)
    if h < 0:
        return 0
    halvings = h // int(L28_HALVING_INTERVAL)
    r = int(L28_MAX_COINBASE_REWARD) >> int(halvings)
    return max(1, int(r))


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

    tx_id = compute_tx_id(tx)

    # replay guard
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
            canonical_h = int(current_height_lookup())
        except Exception:
            return False, tx_id, "canonical_height_unavailable"

        issued = _as_int(current_issued_lookup())
        if issued is None:
            return False, tx_id, "issued_supply_unavailable"

        # strict required fields
        miner = tx.get("miner") or tx.get("miner_address") or tx.get("to") or receiver
        nonce = _as_int(tx.get("nonce"))
        height_field = _as_int(tx.get("height"))
        ts = _as_int(tx.get("timestamp"))

        if not isinstance(receiver, str) or not receiver:
            return False, tx_id, "coinbase_missing_receiver"
        if not isinstance(miner, str) or not miner:
            return False, tx_id, "coinbase_missing_miner"
        if receiver != miner:
            return False, tx_id, "coinbase_receiver_mismatch"
        if nonce is None:
            return False, tx_id, "coinbase_missing_nonce"
        if ts is None:
            return False, tx_id, "coinbase_missing_timestamp"
        if now_ts is not None and ts > int(now_ts) + 60:
            return False, tx_id, "coinbase_timestamp_in_future"
        if height_field is None:
            return False, tx_id, "coinbase_missing_height"

        # MUST match canonical consensus height (protocol invariant)
        if int(height_field) != int(canonical_h):
            return False, tx_id, "coinbase_height_mismatch"

        amount = _as_int(tx.get("amount"))
        if amount is None:
            return False, tx_id, "coinbase_amount_not_int"

        reward = int(l28_coinbase_reward(int(canonical_h)))

        # MUST equal deterministic Reward(canonical_h)
        if int(amount) != int(reward):
            return False, tx_id, "coinbase_bad_reward"

        # Supply cap invariant
        if int(issued) + int(reward) > int(L28_MAX_SUPPLY):
            return False, tx_id, "coinbase_supply_cap"

        return True, tx_id, "ok"

    # --- TRANSFER PATH (non-coinbase)
    if not isinstance(sender, str) or not sender:
        return False, tx_id, "missing_sender"
    if not isinstance(receiver, str) or not receiver:
        return False, tx_id, "missing_receiver"

    amount = _as_int(tx.get("amount"))
    if amount is None:
        return False, tx_id, "amount_not_int"
    if amount < int(pol.min_tx_amount):
        return False, tx_id, "amount_too_small"
    if amount > int(pol.max_tx_amount):
        return False, tx_id, "amount_too_large"

    ts = _as_int(tx.get("timestamp"))
    if ts is None:
        return False, tx_id, "missing_timestamp"
    if now_ts is not None and ts > int(now_ts) + 60:
        return False, tx_id, "timestamp_in_future"

    # optional signature verification
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
