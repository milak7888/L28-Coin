# SPDX-License-Identifier: Apache-2.0
"""
L28 PoW Difficulty Upgrade
Adds difficulty-based hash validation to existing blockless chain
Drop-in compatible with current ledger format
"""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass

@dataclass
class L28PoWConfig:
    """PoW configuration for L28 blockless chain"""
    GENESIS_LOCKED = 100_060  # Your current 100k entries
    TARGET_ENTRY_TIME = 0.89  # seconds per entry
    DIFFICULTY_WINDOW = 1440  # ~21 minutes of history
    MIN_DIFFICULTY = 12  # leading zeros (starts easy)
    MAX_DIFFICULTY = 16
    BASE_REWARD = 28.0  # L28 per entry

class L28PoW:
    """
    PoW difficulty manager for L28 blockless chain
    Works with your existing: nonce, hash, prev, payload structure
    """
    
    def __init__(self, ledger_path: str = "chain/data/l28_genesis_ledger.jsonl"):
        self.ledger_path = Path(ledger_path)
        self.config = L28PoWConfig()
        self.current_difficulty = self.config.MIN_DIFFICULTY
        self._difficulty_cache = {}
        
    def is_genesis_locked(self, entry_height: int) -> bool:
        """Protect genesis 100,061 entries"""
        return entry_height <= self.config.GENESIS_LOCKED
    
    def calculate_difficulty(self, entry_height: int) -> int:
        """
        Auto-adjust difficulty based on recent mining rate
        Maintains ~0.89s target per entry
        """
        # Cache check
        if entry_height in self._difficulty_cache:
            return self._difficulty_cache[entry_height]
        
        # Below window size, use minimum
        if entry_height < self.config.GENESIS_LOCKED + self.config.DIFFICULTY_WINDOW:
            return self.config.MIN_DIFFICULTY
        
        # Get recent entries
        recent = self._get_recent_entries(self.config.DIFFICULTY_WINDOW)
        if len(recent) < 100:  # Need sufficient data
            return self.current_difficulty
        
        # Calculate actual time taken
        time_span = recent[-1]['ts'] - recent[0]['ts']
        expected_time = self.config.TARGET_ENTRY_TIME * len(recent)
        ratio = time_span / expected_time
        
        # Adjust difficulty (gradual changes)
        if ratio < 0.7:  # Too fast - increase difficulty
            new_diff = min(self.current_difficulty + 1, self.config.MAX_DIFFICULTY)
        elif ratio > 1.5:  # Too slow - decrease difficulty
            new_diff = max(self.current_difficulty - 1, self.config.MIN_DIFFICULTY)
        else:
            new_diff = self.current_difficulty
        
        self.current_difficulty = new_diff
        self._difficulty_cache[entry_height] = new_diff
        return new_diff
    
    def compute_entry_hash(
        self, 
        entry_height: int,
        prev_hash: str,
        payload: Dict[str, Any],
        nonce: int
    ) -> str:
        """
        Compute hash for entry (matches your existing format)
        Hash input: height + prev + payload + nonce
        """
        # Serialize payload deterministically
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        
        # Build hash input string
        hash_input = f"{entry_height}{prev_hash}{payload_str}{nonce}"
        
        # Compute SHA-256
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    
    def validate_pow(self, entry: Dict[str, Any]) -> bool:
        """
        Validate that entry hash meets difficulty requirement
        Compatible with your existing entry structure
        """
        entry_height = entry['entry_height']
        
        # Get difficulty for this height
        if 'difficulty' in entry:
            difficulty = entry['difficulty']
        else:
            # For legacy entries, assume they pass
            if self.is_genesis_locked(entry_height):
                return True
            difficulty = self.calculate_difficulty(entry_height)
        
        # Check hash has required leading zeros
        return entry['hash'].startswith('0' * difficulty)
    
    def mine_entry_pow(
        self,
        entry_height: int,
        prev_hash: str,
        miner_id: str,
        current_supply: float,
        payload_extra: Optional[Dict] = None,
        max_attempts: int = 10_000_000
    ) -> Optional[Dict]:
        """
        Mine new entry with PoW difficulty
        Returns entry in your exact JSONL format
        """
        # Genesis protection
        if self.is_genesis_locked(entry_height):
            raise PermissionError(
                f"Entry {entry_height} is genesis-locked. "
                f"Cannot mine entries <= {self.config.GENESIS_LOCKED}"
            )
        
        # Get current difficulty
        difficulty = self.calculate_difficulty(entry_height)
        target = '0' * difficulty
        
        # Build base payload
        from datetime import datetime
        payload = {
            "type": "mining",
            "miner": miner_id,
            "timestamp": datetime.utcnow().isoformat(),
            "nonce": 0  # Will be set in loop
        }
        if payload_extra:
            payload.update(payload_extra)
        
        # Mining loop
        for nonce in range(max_attempts):
            payload['nonce'] = nonce
            
            # Compute hash
            entry_hash = self.compute_entry_hash(
                entry_height, prev_hash, payload, nonce
            )
            
            # Check if meets difficulty
            if entry_hash.startswith(target):
                # Build complete entry (your format)
                return {
                    "entry_height": entry_height,
                    "hash": entry_hash,
                    "prev": prev_hash,
                    "current_supply": current_supply + self.config.BASE_REWARD,
                    "reward": self.config.BASE_REWARD,
                    "difficulty": difficulty,  # NEW FIELD
                    "qubits": 50,
                    "poi_q": 1.0,
                    "poi_v": 100.0,
                    "validator_s": 100.0,
                    "ts": time.time(),
                    "payload": payload
                }
        
        # Failed to find valid nonce
        return None
    
    def verify_ledger_pow(self, start_height: int = 100_062) -> Dict[str, Any]:
        """
        Verify all entries after genesis have valid PoW
        Returns validation report
        """
        results = {
            "valid": True,
            "total_checked": 0,
            "invalid_entries": [],
            "difficulty_range": [999, 0]
        }
        
        for entry in self._iter_entries_from(start_height):
            results["total_checked"] += 1
            
            # Check PoW
            if not self.validate_pow(entry):
                results["valid"] = False
                results["invalid_entries"].append({
                    "height": entry['entry_height'],
                    "hash": entry['hash'],
                    "reason": "Insufficient PoW"
                })
            
            # Track difficulty range
            if 'difficulty' in entry:
                diff = entry['difficulty']
                results["difficulty_range"][0] = min(results["difficulty_range"][0], diff)
                results["difficulty_range"][1] = max(results["difficulty_range"][1], diff)
        
        return results
    
    def _get_recent_entries(self, count: int) -> list:
        """Read last N entries from ledger"""
        entries = []
        try:
            with open(self.ledger_path, 'r') as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
        except FileNotFoundError:
            return []
        
        return entries[-count:] if len(entries) > count else entries
    
    def _iter_entries_from(self, start_height: int):
        """Iterate entries starting from height"""
        try:
            with open(self.ledger_path, 'r') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        if entry['entry_height'] >= start_height:
                            yield entry
        except FileNotFoundError:
            return


# ============================================================================
# CLI TOOLS
# ============================================================================

def cmd_mine_next(ledger_path: str, miner_id: str = "WORKER_POW"):
    """Mine the next entry with PoW difficulty"""
    pow_engine = L28PoW(ledger_path)
    
    # Get last entry
    with open(ledger_path, 'r') as f:
        last_entry = None
        for line in f:
            if line.strip():
                last_entry = json.loads(line)
    
    if not last_entry:
        print("❌ No genesis entry found")
        return
    
    next_height = last_entry['entry_height'] + 1
    difficulty = pow_engine.calculate_difficulty(next_height)
    
    print(f"⛏️  Mining entry {next_height}")
    print(f"   Difficulty: {difficulty} leading zeros")
    print(f"   Target time: {L28PoWConfig.TARGET_ENTRY_TIME}s")
    
    start = time.time()
    entry = pow_engine.mine_entry_pow(
        entry_height=next_height,
        prev_hash=last_entry['hash'],
        miner_id=miner_id,
        current_supply=last_entry['current_supply']
    )
    elapsed = time.time() - start
    
    if entry:
        print(f"\n✅ Entry mined in {elapsed:.2f}s!")
        print(f"   Hash: {entry['hash']}")
        print(f"   Nonce: {entry['payload']['nonce']:,}")
        print(f"   Attempts: ~{entry['payload']['nonce']:,}")
        print(f"   Hashrate: {entry['payload']['nonce']/elapsed:.0f} H/s")
        
        # Append to ledger
        with open(ledger_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        print(f"\n💾 Appended to {ledger_path}")
    else:
        print(f"\n❌ Failed to mine entry (tried 10M nonces)")


def cmd_verify_pow(ledger_path: str):
    """Verify PoW for all post-genesis entries"""
    pow_engine = L28PoW(ledger_path)
    
    print(f"🔍 Verifying PoW for {ledger_path}")
    print(f"   Genesis locked: {L28PoWConfig.GENESIS_LOCKED} entries")
    
    results = pow_engine.verify_ledger_pow()
    
    print(f"\n📊 Results:")
    print(f"   Total checked: {results['total_checked']}")
    print(f"   Valid: {results['valid']}")
    print(f"   Difficulty range: {results['difficulty_range']}")
    
    if results['invalid_entries']:
        print(f"\n❌ Invalid entries: {len(results['invalid_entries'])}")
        for inv in results['invalid_entries'][:10]:
            print(f"   Height {inv['height']}: {inv['reason']}")


def cmd_difficulty_report(ledger_path: str):
    """Generate difficulty adjustment report"""
    pow_engine = L28PoW(ledger_path)
    
    entries = pow_engine._get_recent_entries(2000)
    if len(entries) < 100:
        print("❌ Insufficient entries for report")
        return
    
    print(f"📈 L28 Difficulty Report")
    print(f"   Total entries: {len(entries)}")
    print(f"   Height range: {entries[0]['entry_height']} - {entries[-1]['entry_height']}")
    
    # Calculate time metrics
    time_span = entries[-1]['ts'] - entries[0]['ts']
    avg_time = time_span / len(entries)
    target_time = L28PoWConfig.TARGET_ENTRY_TIME
    
    print(f"\n⏱️  Timing:")
    print(f"   Average: {avg_time:.3f}s per entry")
    print(f"   Target: {target_time:.3f}s per entry")
    print(f"   Ratio: {avg_time/target_time:.2f}x")
    
    # Calculate recommended difficulty
    current_height = entries[-1]['entry_height']
    recommended_diff = pow_engine.calculate_difficulty(current_height + 1)
    
    print(f"\n🎯 Difficulty:")
    print(f"   Current: {pow_engine.current_difficulty}")
    print(f"   Recommended: {recommended_diff}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python l28_pow_upgrade.py mine <ledger_path> [miner_id]")
        print("  python l28_pow_upgrade.py verify <ledger_path>")
        print("  python l28_pow_upgrade.py report <ledger_path>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    ledger = sys.argv[2] if len(sys.argv) > 2 else "chain/data/l28_genesis_ledger.jsonl"
    
    if cmd == "mine":
        miner_id = sys.argv[3] if len(sys.argv) > 3 else "WORKER_POW"
        cmd_mine_next(ledger, miner_id)
    elif cmd == "verify":
        cmd_verify_pow(ledger)
    elif cmd == "report":
        cmd_difficulty_report(ledger)
    else:
        print(f"❌ Unknown command: {cmd}")
