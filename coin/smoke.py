# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import asyncio
import inspect
import logging
import time
from dataclasses import fields, is_dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from .ledger import BlocklessLedger
from .tx_validation import TxPolicy, validate_transaction

log = logging.getLogger("l28.smoke")


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
            # conservative defaults; coinbase reward is enforced separately anyway
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
    supported = {}
    for k, v in kwargs.items():
        if k in sig.parameters:
            supported[k] = v
    return fn(*args, **supported)


def make_default_lookups(ledger: BlocklessLedger) -> Dict[str, Any]:
    """
    Provide the dependency-injected lookups required by validate_transaction().
    This is strict wiring for local smoke tests.
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
        return int(getattr(ledger, "issued_supply", 0) or 0)

    def current_height_lookup() -> int:
        # ledger may track a canonical mint height; fall back to 0.
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
        "_mark_seen": mark_seen,
    }


def validate_tx_default(
    tx: dict,
    *,
    ledger: BlocklessLedger,
    policy: Optional[TxPolicy] = None,
    verify_signature: Optional[Callable[..., Any]] = None,
    now_ts: Optional[int] = None,
) -> Tuple[bool, str, str]:
    lookups = make_default_lookups(ledger)
    pol = policy or _default_policy()
    ok, tx_id, reason = validate_transaction(
        tx,
        policy=pol,
        current_balance_lookup=lookups["current_balance_lookup"],
        seen_tx_lookup=lookups["seen_tx_lookup"],
        verify_signature=verify_signature,
        now_ts=now_ts,
        current_issued_lookup=lookups["current_issued_lookup"],
        current_height_lookup=lookups["current_height_lookup"],
    )
    if ok:
        lookups["_mark_seen"](tx_id)
    return ok, tx_id, reason


async def add_tx_to_ledger_async(ledger: BlocklessLedger, tx: dict, policy: Optional[TxPolicy] = None) -> Any:
    """
    Call the ledger ingestion method in a signature-safe way.
    Handles sync or async ledger ingestion.
    """
    pol = policy or _default_policy()
    for name in ("add_transaction", "apply_transaction", "append_transaction"):
        fn = getattr(ledger, name, None)
        if callable(fn):
            res = _call_with_supported_kwargs(fn, tx, policy=pol)
            if inspect.isawaitable(res):
                return await res
            return res
    raise RuntimeError("No ledger ingestion method found (expected add_transaction/apply_transaction/append_transaction)")


def _build_coinbase_safely(miner: str, *, height: int, nonce: int, ts: int) -> dict:
    """
    Adapter layer: tolerate refactors of mining.build_coinbase_tx signature.
    Goal: always build a STRICT coinbase tx that passes tx_validation invariants.
    """
    from . import mining
    from .tx_validation import l28_coinbase_reward

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
            return "smoke"
        if n in ("amount", "reward", "subsidy"):
            return int(l28_coinbase_reward(int(height)))
        return None

    args = []
    kwargs = {}

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


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[l28] %(message)s")

    ledger = BlocklessLedger()
    policy = _default_policy()

    miner = "L28_MINER_TEST_ADDR"
    base_ts = int(time.time())
    blocks = 3

    async def _run() -> None:
        for h in range(blocks):
            ts = base_ts + h

            tx = _build_coinbase_safely(miner, height=h, nonce=1000 + h, ts=ts)
            ok, tx_id, reason = validate_tx_default(tx, ledger=ledger, policy=policy, now_ts=ts)
            if not ok:
                raise SystemExit(f"coinbase validate failed: h={h} tx_id={tx_id} reason={reason}")

            await add_tx_to_ledger_async(ledger, tx, policy=policy)

            issued = int(getattr(ledger, "issued_supply", -1))
            log.info("OK block=%s coinbase_tx=%s issued_supply=%s", h, tx_id, issued)

            # If ledger tracks mint height, update it deterministically for next reward calc.
            if hasattr(ledger, "mint_height") and isinstance(getattr(ledger, "mint_height"), int):
                setattr(ledger, "mint_height", int(h) + 1)

        log.info("SMOKE OK: blocks=%s issued_supply=%s", blocks, int(getattr(ledger, "issued_supply", 0)))

    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
