#!/usr/bin/env python3
"""Network-specific ledger management"""
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

class NetworkLedger:
    def __init__(self, network_name: str, ledger_path: str):
        self.network_name = network_name
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.ledger_path.exists():
            self.ledger_path.touch()
        
        self.current_height = self._get_last_height()
        self.current_supply = self._get_current_supply()
    
    def _get_last_height(self) -> int:
        if not self.ledger_path.exists() or self.ledger_path.stat().st_size == 0:
            return 0
        
        with open(self.ledger_path, 'r') as f:
            for line in f:
                pass
            if line.strip():
                entry = json.loads(line)
                return entry.get('entry_height', 0)
        return 0
    
    def _get_current_supply(self) -> int:
        if not self.ledger_path.exists() or self.ledger_path.stat().st_size == 0:
            return 0
        
        with open(self.ledger_path, 'r') as f:
            for line in f:
                pass
            if line.strip():
                entry = json.loads(line)
                return entry.get('network_supply', 0)
        return 0
    
    def add_entry(self, entry_type: str, payload: Dict) -> Dict:
        entry = {
            'entry_height': self.current_height + 1,
            'timestamp': time.time(),
            'network': self.network_name,
            'type': entry_type,
            'payload': payload,
            'network_supply': self.current_supply
        }
        
        with open(self.ledger_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        self.current_height += 1
        
        return entry
    
    def add_bridge_entry(self, from_network: str, to_network: str, amount: int, bridge_id: str):
        if from_network == self.network_name:
            # Outgoing bridge
            entry = self.add_entry('BRIDGE_OUT', {
                'from': from_network,
                'to': to_network,
                'amount': amount,
                'bridge_id': bridge_id
            })
            self.current_supply -= amount
        elif to_network == self.network_name:
            # Incoming bridge
            entry = self.add_entry('BRIDGE_IN', {
                'from': from_network,
                'to': to_network,
                'amount': amount,
                'bridge_id': bridge_id
            })
            self.current_supply += amount
        
        return entry
    
    def get_entries(self, start: int = 0, count: int = 100) -> List[Dict]:
        entries = []
        with open(self.ledger_path, 'r') as f:
            for i, line in enumerate(f):
                if i < start:
                    continue
                if len(entries) >= count:
                    break
                if line.strip():
                    entries.append(json.loads(line))
        return entries

if __name__ == "__main__":
    # Test ledgers for each network
    networks = ['MAIN', 'SPEED', 'PRIVACY', 'ENTERPRISE']
    
    print("🧪 Testing network ledgers...")
    
    for network in networks:
        ledger = NetworkLedger(network, f"chain/data/networks/l28_{network.lower()}_ledger.jsonl")
        print(f"\n{network} Network:")
        print(f"  Height: {ledger.current_height}")
        print(f"  Supply: {ledger.current_supply:,} L28")
        
        if ledger.current_height == 0:
            # Initialize with genesis
            ledger.add_entry('GENESIS', {'initial_supply': 0})
            print(f"  ✅ Genesis created")
    
    print("\n✅ All network ledgers ready!")
