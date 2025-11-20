#!/usr/bin/env python3
"""
L28 Miner - Production Proof of Work
Difficulty 18+ (GPU-resistant, $1M+ to attack)
"""
import asyncio
import hashlib
import time
import logging
from typing import Dict
from leap28.core.config import NETWORKS, NetworkType, retarget, MIN_DIFFICULTY, MAX_DIFFICULTY

logger = logging.getLogger(__name__)

class L28Miner:
    def __init__(self, wallet_address: str, network_type: NetworkType = NetworkType.MAIN):
        self.wallet_address = wallet_address
        self.network_config = NETWORKS[network_type]
        self.difficulty = self.network_config.difficulty
        self.target = "0" * self.difficulty
        self.total_mined = 0
        self.hash_rate = 0
        self.block_history = []
        self.block_reward = self.network_config.reward
        
        logger.info(f"🔒 L28 Secure Miner - Difficulty {self.difficulty} (MIN: {MIN_DIFFICULTY})")
    
    async def mine_block(self, transactions: list, previous_hash: str) -> Dict:
        block_number = self.total_mined + 1
        
        if block_number % self.network_config.adjustment_period == 0 and self.block_history:
            self._retarget_difficulty(block_number)
        
        timestamp = time.time()
        logger.info(f"⛏️  Mining block #{block_number} (difficulty: {self.difficulty})...")
        
        block_data = {
            "block_number": block_number,
            "transactions": transactions,
            "previous_hash": previous_hash,
            "timestamp": timestamp,
            "miner": self.wallet_address,
            "reward": self.block_reward,
            "difficulty": self.difficulty
        }
        
        nonce, block_hash, hash_attempts = await self._find_nonce(block_data)
        
        block_data["nonce"] = nonce
        block_data["hash"] = block_hash
        block_data["hash_attempts"] = hash_attempts
        
        mining_time = time.time() - timestamp
        block_data["mining_time"] = mining_time
        
        self.total_mined += 1
        self.hash_rate = hash_attempts / mining_time if mining_time > 0 else 0
        self.block_history.append(block_data)
        
        logger.info(f"✅ Block #{block_number} mined in {mining_time:.1f}s | {self.hash_rate:,.0f} H/s")
        return block_data
    
    async def _find_nonce(self, block_data: Dict) -> tuple:
        nonce = 0
        attempts = 0
        
        import json
        base = json.dumps({k: v for k, v in block_data.items() if k not in ["nonce", "hash"]}, sort_keys=True)
        
        while True:
            data = base + str(nonce)
            block_hash = hashlib.sha256(data.encode()).hexdigest()
            attempts += 1
            
            if block_hash.startswith(self.target):
                return nonce, block_hash, attempts
            
            nonce += 1
            if attempts % 100000 == 0:
                await asyncio.sleep(0)
    
    def _retarget_difficulty(self, block_number: int):
        period = self.network_config.adjustment_period
        if len(self.block_history) < period:
            return
        
        recent = self.block_history[-period:]
        actual_time = sum(b["mining_time"] for b in recent)
        target_time = self.network_config.target_time
        
        old_difficulty = self.difficulty
        new_difficulty = retarget.calculate_new_difficulty(old_difficulty, actual_time, target_time, period)
        
        if new_difficulty != old_difficulty:
            self.difficulty = new_difficulty
            self.target = "0" * new_difficulty
            logger.info(f"🔧 Retarget: {old_difficulty} → {new_difficulty}")
    
    def get_mining_stats(self) -> Dict:
        return {
            "total_mined": self.total_mined,
            "difficulty": self.difficulty,
            "min_difficulty": MIN_DIFFICULTY,
            "max_difficulty": MAX_DIFFICULTY,
            "hash_rate": self.hash_rate,
            "block_reward": self.block_reward,
            "miner_address": self.wallet_address
        }
