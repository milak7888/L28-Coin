# SPDX-License-Identifier: Apache-2.0
"""
L28 BLOCKLESS LEDGER - IMMUTABLE TOKENOMICS
============================================
Total Supply: 28,000,000 L28 (HARD CAP)
Initial Reward: 28 L28 per entry
Halving: Every 210,000 entries
Architecture: Blockless (individual chained entries)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Any
import json, time, hashlib, os

# IMMUTABLE L28 TOKENOMICS
MAX_SUPPLY = 28_000_000
INITIAL_REWARD = 28.0
HALVING_INTERVAL = 210_000
ENTRY_TIME = 89

@dataclass
class LedgerEntry:
    ts: float
    payload: Mapping[str, Any]
    qubits: int
    validator_s: float
    poi_q: float
    poi_v: float
    reward: float
    prev: str
    hash: str
    entry_height: int
    current_supply: float

def calculate_entry_reward(entry_height: int, current_supply: float) -> float:
    if current_supply >= MAX_SUPPLY:
        return 0.0
    halvings = entry_height // HALVING_INTERVAL
    reward = INITIAL_REWARD / (2 ** halvings)
    if current_supply + reward > MAX_SUPPLY:
        return MAX_SUPPLY - current_supply
    return reward

def get_current_supply(path: str) -> tuple[float, int]:
    if not os.path.exists(path):
        return 0.0, 0
    total = 0.0
    entries = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                total += entry.get("reward", 0)
                entries += 1
    return total, entries

def _json_dumps_sorted(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def head_hash(path: str) -> str:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return "0" * 64
    last = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last = line
    if not last:
        return "0" * 64
    try:
        return json.loads(last).get("hash", "0" * 64)
    except:
        return "0" * 64

def append_entry(path: str, payload: Mapping[str, Any], *, qubits: int, S: float = 100.0, K: float = 100.0, poi_q: float = 0.5) -> LedgerEntry:
    current_supply, entry_height = get_current_supply(path)
    reward = calculate_entry_reward(entry_height, current_supply)
    ts = time.time()
    prev = head_hash(path)
    validator_s = S * (1 + 0.1 * (qubits - 50) / 50)
    poi_v = validator_s * poi_q
    entry_data = {
        "ts": ts,
        "payload": payload,
        "qubits": qubits,
        "validator_s": validator_s,
        "poi_q": poi_q,
        "poi_v": poi_v,
        "reward": reward,
        "prev": prev,
        "entry_height": entry_height,
        "current_supply": current_supply + reward,
    }
    entry_str = _json_dumps_sorted(entry_data)
    entry_hash = _sha256_str(entry_str)
    entry_data["hash"] = entry_hash
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(_json_dumps_sorted(entry_data) + "\n")
    return LedgerEntry(ts=ts, payload=payload, qubits=qubits, validator_s=validator_s, poi_q=poi_q, poi_v=poi_v, reward=reward, prev=prev, hash=entry_hash, entry_height=entry_height, current_supply=current_supply + reward)

def get_ledger_stats(path: str) -> dict:
    if not os.path.exists(path):
        return {"total_supply": 0.0, "total_entries": 0, "remaining_supply": MAX_SUPPLY, "current_era": 0, "current_reward": INITIAL_REWARD, "next_halving_at": HALVING_INTERVAL, "max_supply": MAX_SUPPLY}
    total_supply, entry_count = get_current_supply(path)
    current_era = entry_count // HALVING_INTERVAL
    current_reward = calculate_entry_reward(entry_count, total_supply)
    next_halving = ((current_era + 1) * HALVING_INTERVAL) - entry_count
    return {"total_supply": total_supply, "total_entries": entry_count, "remaining_supply": MAX_SUPPLY - total_supply, "percent_mined": (total_supply / MAX_SUPPLY) * 100, "current_era": current_era, "current_reward": current_reward, "next_halving_at": next_halving, "max_supply": MAX_SUPPLY}
