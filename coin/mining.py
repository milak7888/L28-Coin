# SPDX-License-Identifier: Apache-2.0
import hashlib
import time

from .tx_validation import compute_tx_id, l28_coinbase_reward


def mine_block(miner_address, difficulty=18, max_attempts=10000):
    target = "0" * difficulty
    for nonce in range(max_attempts):
        data = f"{miner_address}{time.time()}{nonce}"
        hash_result = hashlib.sha256(data.encode()).hexdigest()
        if hash_result.startswith(target):
            return {"nonce": nonce, "hash": hash_result}
    return None


def build_coinbase_tx(
    miner_address: str,
    *,
    nonce: int,
    height: int = 0,
    timestamp: int | None = None,
    network: str = "MAIN",
    tag: str | None = None,
) -> dict:
    """
    Build a STRICT coinbase tx that satisfies tx_validation invariants.
    - Includes miner + nonce + height.
    - Amount is deterministic by the canonical emission schedule at height.
    NOTE: callers must set height to the canonical consensus/mint height;
    the ledger does not rewrite height (identity stability / replay safety).
    Newly created transactions do not place implementation-only _builder metadata
    into the public transaction record.
    """
    if timestamp is None:
        timestamp = int(time.time())
    h = int(height)
    amt = int(l28_coinbase_reward(h))
    tx = {
        "sender": "COINBASE",
        "receiver": str(miner_address),
        "amount": int(amt),
        "timestamp": int(timestamp),
        "type": "coinbase",
        "coinbase": True,
        "signature": "COINBASE",
        "miner": str(miner_address),
        "nonce": int(nonce),
        "height": int(h),
        "network": str(network),
    }
    if tag is not None:
        tx["tag"] = str(tag)
    tx["id"] = compute_tx_id(tx)
    return tx


def build_mint_tx(
    to_address: str,
    amount: int,
    *,
    nonce: int,
    timestamp: int | None = None,
    memo: str = "mint",
) -> dict:
    """
    Direct/discretionary mint construction is disabled.

    Caller-selected issuance is forbidden. Use build_coinbase_tx with the
    canonical height-derived reward via the consensus/ledger pipeline.
    """
    raise RuntimeError(
        "build_mint_tx disabled: discretionary minting is forbidden; "
        "use strict canonical build_coinbase_tx via the consensus pipeline"
    )
