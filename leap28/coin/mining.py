import hashlib
import time
from .tx_validation import compute_tx_id

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
    - Amount is deterministic by emission schedule at height.
    NOTE: ledger may overwrite height with canonical mint_height.
    """
    from .tx_validation import compute_tx_id, l28_coinbase_reward
    if timestamp is None:
        import time as _t
        timestamp = int(_t.time())
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
    tx["_builder"] = "HARDENED: COINBASE_BUILDER_REWRITE_V1"
    return tx

def build_mint_tx(
    to_address: str,
    amount: int,
    *,
    nonce: int,
    timestamp: int | None = None,
    memo: str = "mint",
) -> dict:
    """Alias of strict coinbase semantics (issuance path). HARDENED: COINBASE_REQUIRES_MINER_NONCE_V1"""
    return build_coinbase_tx(to_address, int(amount), nonce=int(nonce), timestamp=timestamp, tag=memo)
