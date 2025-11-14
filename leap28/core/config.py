#!/usr/bin/env python3
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict

class NetworkType(Enum):
    MAIN = "MAIN"
    SPEED = "SPEED"
    PRIVACY = "PRIVACY"
    ENTERPRISE = "ENTERPRISE"

@dataclass
class NetworkConfig:
    name: str
    network_type: NetworkType
    port: int
    ledger_path: str
    difficulty: int
    target_time: float
    purpose: str
    features: List[str]
    min_confirmations: int
    max_block_size: int
    fee_structure: Dict[str, float]

# ALL NETWORKS: SAME DIFFICULTY (12) - SAME L28 COIN!
MAIN_CONFIG = NetworkConfig(
    name="L28-MAIN", network_type=NetworkType.MAIN, port=28280,
    ledger_path="chain/data/networks/l28_main_ledger.jsonl",
    difficulty=12, target_time=0.89,
    purpose="Universal bridge", features=["bridge", "pow"],
    min_confirmations=6, max_block_size=1000,
    fee_structure={"base": 0.1, "per_kb": 0.01, "bridge": 0.1}
)

SPEED_CONFIG = NetworkConfig(
    name="L28-SPEED", network_type=NetworkType.SPEED, port=28281,
    ledger_path="chain/data/networks/l28_speed_ledger.jsonl",
    difficulty=12, target_time=0.89,  # SAME!
    purpose="Fast payments", features=["fast", "instant"],
    min_confirmations=2, max_block_size=5000,
    fee_structure={"base": 0.01, "per_kb": 0.001, "bridge": 0.05}
)

PRIVACY_CONFIG = NetworkConfig(
    name="L28-PRIVACY", network_type=NetworkType.PRIVACY, port=28282,
    ledger_path="chain/data/networks/l28_privacy_ledger.jsonl",
    difficulty=12, target_time=0.89,  # SAME!
    purpose="Anonymous transactions", features=["private", "zk-proofs"],
    min_confirmations=10, max_block_size=500,
    fee_structure={"base": 0.2, "per_kb": 0.02, "bridge": 0.15}
)

ENTERPRISE_CONFIG = NetworkConfig(
    name="L28-ENTERPRISE", network_type=NetworkType.ENTERPRISE, port=28283,
    ledger_path="chain/data/networks/l28_enterprise_ledger.jsonl",
    difficulty=12, target_time=0.89,  # SAME!
    purpose="Corporate compliance", features=["kyc", "audit"],
    min_confirmations=6, max_block_size=2000,
    fee_structure={"base": 0.15, "per_kb": 0.015, "bridge": 0.1}
)

NETWORKS = {
    NetworkType.MAIN: MAIN_CONFIG,
    NetworkType.SPEED: SPEED_CONFIG,
    NetworkType.PRIVACY: PRIVACY_CONFIG,
    NetworkType.ENTERPRISE: ENTERPRISE_CONFIG
}

TOTAL_SUPPLY = 28_000_000
SYNC_INTERVAL = 0.89

if __name__ == "__main__":
    print("L28 Multi-Network Configuration")
    print("=" * 50)
    for net_type, config in NETWORKS.items():
        print(f"\n{config.name}:")
        print(f"  Port: {config.port}")
        print(f"  Difficulty: {config.difficulty} (SAME FOR ALL!)")
        print(f"  Purpose: {config.purpose}")
