"""
Complete Blockless Ledger System
Sharded across 5 segments for manageability
"""
import asyncio
import logging
from typing import Dict, List, Optional
from collections import defaultdict
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class BlocklessLedger:
    """
    Blockless Ledger with Sharding
    
    No blockchain - just events with:
    - 5 shards for scalability
    - Event ordering by timestamp
    - Balance tracking
    - Transaction history
    """
    
    def __init__(self, data_dir: str = "data/ledger"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 5 shards (based on address hash)
        self.num_shards = 5
        self.shards = [[] for _ in range(self.num_shards)]
        
        # Balance tracking
        self.balances = defaultdict(int)
        
        # Transaction index
        self.transactions = {}
        
        # Stats
        self.total_transactions = 0
        self.total_volume = 0
    
    def get_shard_for_address(self, address: str) -> int:
        """Determine which shard an address belongs to"""
        return hash(address) % self.num_shards
    
    async def add_transaction(self, transaction: Dict) -> bool:
        """
        Add transaction to ledger
        
        Updates:
        - Sender balance (decrease)
        - Receiver balance (increase)
        - Shard data
        - Transaction index
        """
        tx_id = transaction['id']
        sender = transaction['sender']
        receiver = transaction['receiver']
        amount = transaction['amount']
        
        # Check sender balance
        if self.balances[sender] < amount:
            logger.warning(f"Insufficient balance for {sender}")
            return False
        
        # Update balances
        self.balances[sender] -= amount
        self.balances[receiver] += amount
        
        # Add to appropriate shard
        shard_id = self.get_shard_for_address(sender)
        self.shards[shard_id].append(transaction)
        
        # Index transaction
        self.transactions[tx_id] = transaction
        
        # Update stats
        self.total_transactions += 1
        self.total_volume += amount
        
        logger.info(f"✅ Transaction {tx_id} added to shard {shard_id}")
        
        # Persist to disk
        await self._save_transaction(transaction, shard_id)
        
        return True
    
    def get_balance(self, address: str) -> int:
        """Get current balance for address"""
        return self.balances.get(address, 0)
    
    def get_transaction(self, tx_id: str) -> Optional[Dict]:
        """Get transaction by ID"""
        return self.transactions.get(tx_id)
    
    def get_transaction_history(self, address: str, limit: int = 100) -> List[Dict]:
        """Get transaction history for address"""
        # Get shard for address
        shard_id = self.get_shard_for_address(address)
        
        # Filter transactions involving this address
        history = []
        for tx in self.shards[shard_id]:
            if tx['sender'] == address or tx['receiver'] == address:
                history.append(tx)
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return history[:limit]
    
    async def _save_transaction(self, transaction: Dict, shard_id: int):
        """Persist transaction to disk"""
        shard_file = self.data_dir / f"shard_{shard_id}.jsonl"
        
        # Append to shard file (JSONL format)
        with open(shard_file, 'a') as f:
            f.write(json.dumps(transaction) + '\n')
    
    async def load_from_disk(self):
        """Load ledger from disk on startup"""
        logger.info("Loading ledger from disk...")
        
        for shard_id in range(self.num_shards):
            shard_file = self.data_dir / f"shard_{shard_id}.jsonl"
            
            if not shard_file.exists():
                continue
            
            with open(shard_file, 'r') as f:
                for line in f:
                    if line.strip():
                        tx = json.loads(line)
                        
                        # Rebuild state
                        self.shards[shard_id].append(tx)
                        self.transactions[tx['id']] = tx
                        
                        # Update balances
                        self.balances[tx['sender']] -= tx['amount']
                        self.balances[tx['receiver']] += tx['amount']
                        
                        self.total_transactions += 1
                        self.total_volume += tx['amount']
        
        logger.info(f"✅ Loaded {self.total_transactions} transactions from disk")
    
    def get_ledger_stats(self) -> Dict:
        """Get ledger statistics"""
        return {
            'total_transactions': self.total_transactions,
            'total_volume': self.total_volume,
            'unique_addresses': len(self.balances),
            'shards': self.num_shards,
            'transactions_per_shard': [len(shard) for shard in self.shards]
        }
