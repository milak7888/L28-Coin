# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import inspect
import logging
import time
from dataclasses import fields, is_dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from .ledger import BlocklessLedger
from .tx_validation import TxPolicy, l28_coinbase_reward, validate_transaction

log = logging.getLogger("l28.invariants")


def _default_policy() -> TxPolicy:
    """
    Build a TxPolicy without hard-coding its schema.
    Works even if TxPolicy fields change.
    """
    try:
        if not is_dataclass(TxPolicy):
            return TxPolicy()  # type: ignore[call-arg]

        kwargs: Dict[str, Any] = {}
        for f in fields(TxPolicy):
            name = str(f.name)

            # Conservative limits for invariants tests
            if name in ("max_amount", "max_tx_amount", "max_transfer_amount"):
                kwargs[name] = 10_000_000_000
            if name in ("min_amount", "min_tx_amount"):
                kwargs[name] = 1

        try:
            return TxPolicy(**kwargs)  # type: ignore[arg-type]
        except TypeError:
            return TxPolicy()  # type: ignore[call-arg]
    except Exception:
        return TxPolicy()  # type: ignore[call-arg]


def _call_with_supported_kwargs(fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
    sig = inspect.signature(fn)
    supported: Dict[str, Any] = {}
    for k, v in kwargs.items():
        if k in sig.parameters:
            supported[k] = v
    return fn(*args, **supported)


def _build_coinbase_safely(miner: str, *, height: int, nonce: int, ts: int, amount: int) -> dict:
    """
    Adapter layer: tolerate refactors of mining.build_coinbase_tx signature.
    Goal: always build a STRICT coinbase tx compatible with tx_validation invariants.
    """
    from . import mining

    sig = inspect.signature(mining.build_coinbase_tx)

    def _value_for(param_name: str):
        n = str(param_name)
        if n in ("miner_address", "miner", "to_address", "receiver", "receiver_address", "address", "to"):
            return str(miner)
        if n in ("height", "h", "block_height", "canonical_height"):
            return int(height)
        if n in ("nonce", "miner_nonce"):
            return int(nonce)
        if n in ("timestamp", "ts", "now_ts", "time"):
            return int(ts)
        if n in ("tag", "memo", "note"):
            return "invariants"
        if n in ("amount", "reward", "subsidy"):
            return int(amount)
        return None

    args = []
    kwargs: Dict[str, Any] = {}

    for name, param in sig.parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue

        v = _value_for(name)
        if v is None:
            if param.default is not inspect._empty:
                continue
            raise RuntimeError(f"build_coinbase_tx has required param '{name}' I don't know how to fill")

        if param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD):
            args.append(v)
        elif param.kind == param.KEYWORD_ONLY:
            kwargs[name] = v
        else:
            raise RuntimeError(f"Unhandled param kind for {name}: {param.kind}")

    tx = mining.build_coinbase_tx(*args, **kwargs)
    if not isinstance(tx, dict):
        raise RuntimeError(f"build_coinbase_tx returned non-dict: {type(tx)}")
    return tx


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _make_lookups(
    ledger: BlocklessLedger,
    *,
    canonical_height: int,
    issued_supply: int,
) -> Dict[str, Any]:
    """
    Dependency-injected lookups required by validate_transaction().
    """
    seen: set[str] = set()

    def current_balance_lookup(addr: str, network: str) -> int:
        # Try common ledger APIs; fail closed to 0 if unknown.
        for name in ("get_balance", "balance_of", "balance"):
            fn = getattr(ledger, name, None)
            if callable(fn):
                try:
                    return int(_call_with_supported_kwargs(fn, addr, network=network) or 0)
                except Exception:
                    return 0
        return 0

    def seen_tx_lookup(tx_id: str) -> bool:
        return tx_id in seen

    def current_issued_lookup() -> int:
        return int(issued_supply)

    def current_height_lookup() -> int:
        return int(canonical_height)

    def mark_seen(tx_id: str) -> None:
        seen.add(tx_id)

    return {
        "current_balance_lookup": current_balance_lookup,
        "seen_tx_lookup": seen_tx_lookup,
        "current_issued_lookup": current_issued_lookup,
        "current_height_lookup": current_height_lookup,
        "_mark_seen": mark_seen,
    }


def _validate(
    tx: dict,
    *,
    ledger: BlocklessLedger,
    policy: TxPolicy,
    now_ts: int,
    canonical_height: int,
    issued_supply: int,
) -> Tuple[bool, str, str]:
    lookups = _make_lookups(ledger, canonical_height=canonical_height, issued_supply=issued_supply)
    ok, tx_id, reason = validate_transaction(
        tx,
        policy=policy,
        current_balance_lookup=lookups["current_balance_lookup"],
        seen_tx_lookup=lookups["seen_tx_lookup"],
        verify_signature=None,
        now_ts=now_ts,
        current_issued_lookup=lookups["current_issued_lookup"],
        current_height_lookup=lookups["current_height_lookup"],
    )
    if ok:
        lookups["_mark_seen"](tx_id)
    return ok, tx_id, reason


def run_invariants() -> None:
    policy = _default_policy()
    ledger = BlocklessLedger()
    miner = "L28_MINER_TEST_ADDR"
    ts = int(time.time())

    # 1) Canonical height reward enforcement:
    # canonical H=0 => Reward=50 (per your current schedule demo)
    # tx lies: height=100000 => Reward(tx_height)=25, should be rejected because canonical wins.
    canonical_h = 0
    tx_height = 100000
    tx_amount = int(l28_coinbase_reward(tx_height))
    canonical_amount = int(l28_coinbase_reward(canonical_h))

    tx = _build_coinbase_safely(miner, height=tx_height, nonce=123, ts=ts, amount=tx_amount)
    ok, tx_id, reason = _validate(
        tx,
        ledger=ledger,
        policy=policy,
        now_ts=ts,
        canonical_height=canonical_h,
        issued_supply=0,
    )
    _assert(
        not ok,
        (
            "expected canonical reward enforcement to reject mismatch height: "
            f"canonical_h={canonical_h} tx_height={tx_height} "
            f"Reward(canonical)={canonical_amount} Reward(tx_height)={tx_amount} "
            f"got ok tx={tx_id} reason={reason}"
        ),
    )

    # 2) Reserved sender misuse must be rejected for non-coinbase.
    # tx_validation must reject any non-coinbase that uses COINBASE/__MINT__ as sender.
    bad_tx = {
        "sender": "COINBASE",
        "receiver": "X",
        "amount": 1,
        "timestamp": ts,
        "type": "transfer",
    }
    ok2, tx_id2, reason2 = _validate(
        bad_tx,
        ledger=ledger,
        policy=policy,
        now_ts=ts,
        canonical_height=0,
        issued_supply=0,
    )
    _assert(
        not ok2,
        f"expected reserved sender misuse to reject; got ok tx={tx_id2} reason={reason2}",
    )

    # 3) Supply cap edge must reject coinbase that would exceed cap.
    # We don't need the literal cap constant here; validate_transaction should fail-closed
    # when the lookup indicates no remaining issuance budget.
    # Set issued_supply artificially high; coinbase must reject.
    huge_supply = 10**18
    tx3 = _build_coinbase_safely(miner, height=0, nonce=999, ts=ts, amount=int(l28_coinbase_reward(0)))
    ok3, tx_id3, reason3 = _validate(
        tx3,
        ledger=ledger,
        policy=policy,
        now_ts=ts,
        canonical_height=0,
        issued_supply=huge_supply,
    )
    _assert(
        not ok3,
        f"expected supply cap edge to reject; got ok tx={tx_id3} reason={reason3}",
    )

    log.info("INVARIANTS OK: canonical_reward_enforced, reserved_sender_misuse, supply_cap_edge")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[l28] %(message)s")
    run_invariants()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
