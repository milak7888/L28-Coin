#!/usr/bin/env python3
"""
L28 PoW Miner Worker
Drop-in replacement for existing mine_worker scripts
Adds difficulty-based PoW to your blockless chain
"""
import sys
import time
import json
from pathlib import Path

# Import your existing modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from l28_pow_upgrade import L28PoW, L28PoWConfig

class L28PoWWorker:
    """Mining worker with PoW difficulty"""
    
    def __init__(
        self, 
        worker_id: str,
        ledger_path: str = "chain/data/l28_genesis_ledger.jsonl",
        continuous: bool = True
    ):
        self.worker_id = worker_id
        self.ledger_path = Path(ledger_path)
        self.continuous = continuous
        self.pow = L28PoW(str(ledger_path))
        
        self.stats = {
            'mined': 0,
            'failed': 0,
            'total_time': 0,
            'total_hashes': 0
        }
    
    def get_last_entry(self) -> dict:
        """Read last entry from ledger"""
        last_entry = None
        try:
            with open(self.ledger_path, 'r') as f:
                for line in f:
                    if line.strip():
                        last_entry = json.loads(line)
        except FileNotFoundError:
            raise RuntimeError(f"Ledger not found: {self.ledger_path}")
        
        if not last_entry:
            raise RuntimeError("Empty ledger - need genesis entry")
        
        return last_entry
    
    def mine_single_entry(self) -> bool:
        """Mine one entry, return True if successful"""
        last_entry = self.get_last_entry()
        next_height = last_entry['entry_height'] + 1
        
        # Check genesis lock
        if self.pow.is_genesis_locked(next_height):
            print(f"⚠️  Entry {next_height} is genesis-locked")
            return False
        
        # Get difficulty
        difficulty = self.pow.calculate_difficulty(next_height)
        target_time = L28PoWConfig.TARGET_ENTRY_TIME
        
        print(f"\n⛏️  [{self.worker_id}] Mining entry {next_height}")
        print(f"   Difficulty: {difficulty} (target: {target_time:.2f}s)")
        
        # Mine
        start_time = time.time()
        entry = self.pow.mine_entry_pow(
            entry_height=next_height,
            prev_hash=last_entry['hash'],
            miner_id=self.worker_id,
            current_supply=last_entry['current_supply']
        )
        elapsed = time.time() - start_time
        
        if entry:
            # Success!
            nonce = entry['payload']['nonce']
            hashrate = nonce / elapsed if elapsed > 0 else 0
            
            self.stats['mined'] += 1
            self.stats['total_time'] += elapsed
            self.stats['total_hashes'] += nonce
            
            # Append to ledger
            with open(self.ledger_path, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            
            print(f"✅ Mined in {elapsed:.2f}s!")
            print(f"   Hash: {entry['hash']}")
            print(f"   Nonce: {nonce:,}")
            print(f"   Hashrate: {hashrate:,.0f} H/s")
            print(f"   Reward: +{entry['reward']} L28")
            print(f"   New supply: {entry['current_supply']:,.0f} L28")
            
            return True
        else:
            # Failed (shouldn't happen with 10M attempts)
            self.stats['failed'] += 1
            print(f"❌ Failed to mine (10M attempts)")
            return False
    
    def mine_continuous(self):
        """Continuous mining loop"""
        print(f"🪙 L28 PoW Worker Starting")
        print(f"   Worker ID: {self.worker_id}")
        print(f"   Ledger: {self.ledger_path}")
        print(f"   Genesis locked: {L28PoWConfig.GENESIS_LOCKED} entries")
        print("=" * 60)
        
        try:
            while True:
                success = self.mine_single_entry()
                
                if not success:
                    # Back off if failed or locked
                    time.sleep(5)
                
                # Brief pause between entries
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.print_stats()
            print("\n👋 Worker stopped")
    
    def print_stats(self):
        """Print worker statistics"""
        if self.stats['mined'] == 0:
            return
        
        avg_time = self.stats['total_time'] / self.stats['mined']
        avg_hashrate = self.stats['total_hashes'] / self.stats['total_time']
        
        print(f"\n📊 Worker Stats:")
        print(f"   Mined: {self.stats['mined']}")
        print(f"   Failed: {self.stats['failed']}")
        print(f"   Avg time: {avg_time:.2f}s per entry")
        print(f"   Avg hashrate: {avg_hashrate:,.0f} H/s")
        print(f"   Total L28 earned: {self.stats['mined'] * 28:.0f}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="L28 PoW Mining Worker")
    parser.add_argument(
        '--worker-id',
        required=True,
        help='Worker identifier (e.g., WORKER_1)'
    )
    parser.add_argument(
        '--ledger',
        default='chain/data/l28_genesis_ledger.jsonl',
        help='Path to ledger file'
    )
    parser.add_argument(
        '--single',
        action='store_true',
        help='Mine single entry and exit'
    )
    
    args = parser.parse_args()
    
    worker = L28PoWWorker(
        worker_id=args.worker_id,
        ledger_path=args.ledger,
        continuous=not args.single
    )
    
    if args.single:
        worker.mine_single_entry()
        worker.print_stats()
    else:
        worker.mine_continuous()


if __name__ == "__main__":
    main()
