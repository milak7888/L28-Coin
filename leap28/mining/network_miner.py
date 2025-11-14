#!/usr/bin/env python3
import hashlib
import time
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from multinetwork.core.config import NETWORKS, NetworkType

class NetworkMiner:
    def __init__(self, network_type: NetworkType, worker_id: str):
        self.network_config = NETWORKS[network_type]
        self.worker_id = worker_id
        
    def mine_entry(self, prev_hash: str, height: int):
        difficulty = self.network_config.difficulty
        target = '0' * difficulty
        nonce = 0
        start_time = time.time()
        
        while True:
            entry = {
                'network': self.network_config.name,
                'height': height,
                'prev_hash': prev_hash,
                'timestamp': time.time(),
                'miner': self.worker_id,
                'nonce': nonce,
                'reward': 28
            }
            
            entry_str = json.dumps(entry, sort_keys=True)
            hash_result = hashlib.sha256(entry_str.encode()).hexdigest()
            
            if hash_result.startswith(target):
                elapsed = time.time() - start_time
                hashrate = nonce / elapsed if elapsed > 0 else 0
                entry['hash'] = hash_result
                entry['time'] = elapsed
                entry['hashrate'] = hashrate
                return entry
            
            nonce += 1
            if nonce % 1000000 == 0:
                elapsed = time.time() - start_time
                hr = nonce / elapsed if elapsed > 0 else 0
                print(f"⛏️  {nonce:,} hashes | {hr:,.0f} H/s", end='\r')

print(f"⛏️  Mining L28 on MAIN network (Difficulty 12)")
miner = NetworkMiner(NetworkType.MAIN, "test_miner")
height = 1
prev_hash = '0' * 64

while True:
    entry = miner.mine_entry(prev_hash, height)
    print(f"\n✅ Block {height} | {entry['time']:.1f}s | {entry['hashrate']:,.0f} H/s | 28 L28")
    prev_hash = entry['hash']
    height += 1
