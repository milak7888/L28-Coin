"""
L28 Miner - Proof of Work Implementation
Difficulty 12 (leading zeros in hash)
"""
import asyncio
import hashlib
import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class L28Miner:
    """
    L28 Mining System
    
    Uses SHA-256 PoW with difficulty 12
    (hash must start with 12 zeros = 000000000000...)
    """
    
    def __init__(self, wallet_address: str, difficulty: int = 12):
        self.wallet_address = wallet_address
        self.difficulty = difficulty
        self.target = "0" * difficulty
        
        # Mining stats
        self.total_mined = 0
        self.hash_rate = 0
        self.last_block_time = time.time()
        
        # Mining reward (starts at 50 L28, halves periodically)
        self.block_reward = 50
    
    async def mine_block(self, transactions: list, previous_hash: str) -> Dict:
        """
        Mine a new block
        
        Returns:
        {
            'block_number': int,
            'transactions': list,
            'previous_hash': str,
            'nonce': int,
            'hash': str,
            'timestamp': float,
            'miner': str,
            'reward': int
        }
        """
        block_number = self.total_mined + 1
        timestamp = time.time()
        
        logger.info(f"⛏️  Mining block #{block_number} (difficulty: {self.difficulty})...")
        
        # Create block data
        block_data = {
            'block_number': block_number,
            'transactions': transactions,
            'previous_hash': previous_hash,
            'timestamp': timestamp,
            'miner': self.wallet_address,
            'reward': self.block_reward
        }
        
        # Find nonce that satisfies difficulty
        nonce, block_hash, hash_attempts = await self._find_nonce(block_data)
        
        # Add nonce and hash to block
        block_data['nonce'] = nonce
        block_data['hash'] = block_hash
        block_data['hash_attempts'] = hash_attempts
        
        # Update stats
        self.total_mined += 1
        mining_time = time.time() - timestamp
        self.hash_rate = hash_attempts / mining_time if mining_time > 0 else 0
        
        logger.info(f"✅ Block #{block_number} mined!")
        logger.info(f"   Hash: {block_hash}")
        logger.info(f"   Nonce: {nonce:,}")
        logger.info(f"   Attempts: {hash_attempts:,}")
        logger.info(f"   Time: {mining_time:.2f}s")
        logger.info(f"   Hash rate: {self.hash_rate:,.0f} H/s")
        
        return block_data
    
    async def _find_nonce(self, block_data: Dict) -> tuple:
        """
        Find nonce that produces hash with required difficulty
        
        Returns: (nonce, hash, attempts)
        """
        nonce = 0
        attempts = 0
        start_time = time.time()
        
        # Create base string without nonce
        base = f"{block_data['block_number']}{block_data['transactions']}{block_data['previous_hash']}{block_data['timestamp']}{block_data['miner']}"
        
        while True:
            # Try nonce
            data = base + str(nonce)
            block_hash = hashlib.sha256(data.encode()).hexdigest()
            attempts += 1
            
            # Check if hash meets difficulty
            if block_hash.startswith(self.target):
                return nonce, block_hash, attempts
            
            nonce += 1
            
            # Yield control periodically to not block event loop
            if attempts % 10000 == 0:
                await asyncio.sleep(0)
                
                # Log progress
                if attempts % 100000 == 0:
                    elapsed = time.time() - start_time
                    current_rate = attempts / elapsed if elapsed > 0 else 0
                    logger.debug(f"Mining... {attempts:,} attempts, {current_rate:,.0f} H/s")
    
    def adjust_difficulty(self, target_time: float = 60.0, actual_time: float = None):
        """
        Adjust mining difficulty based on block time
        
        Target: 60 seconds per block
        """
        if actual_time is None:
            actual_time = time.time() - self.last_block_time
        
        # If blocks are too fast, increase difficulty
        if actual_time < target_time * 0.8:
            self.difficulty += 1
            self.target = "0" * self.difficulty
            logger.info(f"⬆️  Difficulty increased to {self.difficulty}")
        
        # If blocks are too slow, decrease difficulty
        elif actual_time > target_time * 1.2 and self.difficulty > 8:
            self.difficulty -= 1
            self.target = "0" * self.difficulty
            logger.info(f"⬇️  Difficulty decreased to {self.difficulty}")
        
        self.last_block_time = time.time()
    
    def get_mining_stats(self) -> Dict:
        """Get mining statistics"""
        return {
            'total_mined': self.total_mined,
            'difficulty': self.difficulty,
            'hash_rate': self.hash_rate,
            'block_reward': self.block_reward,
            'miner_address': self.wallet_address
        }
