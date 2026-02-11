# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import time
from typing import Any, Dict

from .ledger import BlocklessLedger
from .mining import build_coinbase_tx
from .tx_validation import TxPolicy, validate_transaction, l28_coinbase_reward


def _default_policy() -> TxPolicy:
    try:
        return TxPolicy()  # type: ignore[call-arg]
    except Exception:
        return TxPolicy()  # type: ignore[call-arg]


def _make_lookups(ledger: BlocklessLedger):
    seen: set[str] = set()

    def current_balance_lookup(addr: str, network: str) -> int:
        # coin-local ledger: balance may be absent; default 0 (fail-closed happens elsewhere)
        for name in ("get_balance", "balance_of", "balance"):
            fn = getattr(ledger, name, None)
            if callable(fn):
                try:
                    return int(fn(addr, network=network) or 0)
                except Exception:
                    return 0
        return 0

    def seen_tx_lookup(tx_id: str) -> bool:
        return tx_id in seen

    def current_issued_lookup() -> int:
        return int(getattr(ledger, "issued_supply", 0) or 0)

    def current_height_lookup() -> int:
        # canonical height source (fail-closed if missing is enforced in validate_transaction)
        for name in ("mint_height", "height", "current_height"):
            v = getattr(ledger, name, None)
            if isinstance(v, int):
                return int(v)
        return 0

    def mark_seen(tx_id: str) -> None:
        seen.add(tx_id)

    return {
        "current_balance_lookup": current_balance_lookup,
        "seen_tx_lookup": seen_tx_lookup,
        "current_issued_lookup": current_issued_lookup,
        "current_height_lookup": current_height_lookup,
        "mark_seen": mark_seen,
    }


def _assert(ok: bool, msg: str) -> None:
    if not ok:
        raise AssertionError(msg)


def run_invariants() -> None:
    ledger = BlocklessLedger()
    policy = _default_policy()
    lookups = _make_lookups(ledger)

    miner = "L28_MINER_TEST_ADDR"
    ts = int(time.time())

    # 1) Reserved sender misuse must be rejected
    bad = {
        "sender": "COINBASE",
        "receiver": "X",
        "amount": 1,
        "timestamp": ts,
        "type": "transfer",
        "coinbase": False,
        "signature": "x",
    }
    ok, _, reason = validate_transaction(
        bad,
        policy=policy,
        current_balance_lookup=lookups["current_balance_lookup"],
        seen_tx_lookup=lookups["seen_tx_lookup"],
        verify_signature=None,
        now_ts=ts,
        current_issued_lookup=lookups["current_issued_lookup"],
        current_height_lookup=lookups["current_height_lookup"],
    )
    _assert((not ok) and ("reserved_sender" in reason or "coinbase" in reason), f"reserved sender misuse not rejected: {reason}")

    # 2) Height mismatch must be rejected (user-provided height != canonical)
    # canonical is 0 initially via current_height_lookup -> 0
    tx = build_coinbase_tx(miner, int(l28_coinbase_reward(0)), nonce=123, timestamp=ts, height=999, miner=miner)
    ok, _, reason = validate_transaction(
        tx,
        policy=policy,
        current_balance_lookup=lookups["current_balance_lookup"],
        seen_tx_lookup=lookups["seen_tx_lookup"],
        verify_signature=None,
        now_ts=ts,
        current_issued_lookup=lookups["current_issued_lookup"],
        current_height_lookup=lookups["current_height_lookup"],
    )
    _assert((not ok) and ("height_mismatch" in reason or "canonical" in reason), f"height mismatch not rejected: {reason}")

    # 3) Supply cap edge: if issued_supply already at max, coinbase must be rejected
    # We simulate by forcing ledger issued_supply and attempting a valid coinbase at canonical height 0.
    setattr(ledger, "issued_supply", 28_000_000)
    tx2 = build_coinbase_tx(miner, int(l28_coinbase_reward(0)), nonce=124, timestamp=ts + 1, height=0, miner=miner)
    ok, _, reason = validate_transaction(
        tx2,
        policy=policy,
        current_balance_lookup=lookups["current_balance_lookup"],
        seen_tx_lookup=lookups["seen_tx_lookup"],
        verify_signature=None,
        now_ts=ts + 1,
        current_issued_lookup=lookups["current_issued_lookup"],
        current_height_lookup=lookups["current_height_lookup"],
    )
    _assert((not ok) and ("supply" in reason or "max_supply" in reason), f"supply cap not enforced: {reason}")


def main() -> int:
    run_invariants()
    print("[l28] invariants OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
