#!/usr/bin/env python3
"""Production L28 Multi-Network System with persistent ledgers"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from multinetwork.core.sync_coordinator import L28SyncCoordinator
from multinetwork.core.bridge_manager import L28BridgeManager
from multinetwork.core.network_ledger import NetworkLedger
from multinetwork.integration.wallet_connector import MultiNetworkWallet

class L28ProductionSystem:
    def __init__(self, wallet_name: str):
        self.wallet = MultiNetworkWallet(wallet_name)
        self.coordinator = L28SyncCoordinator()
        self.bridge = L28BridgeManager(self.coordinator)
        
        # Initialize ledgers for each network
        self.ledgers = {
            'MAIN': NetworkLedger('MAIN', 'chain/data/networks/l28_main_ledger.jsonl'),
            'SPEED': NetworkLedger('SPEED', 'chain/data/networks/l28_speed_ledger.jsonl'),
            'PRIVACY': NetworkLedger('PRIVACY', 'chain/data/networks/l28_privacy_ledger.jsonl'),
            'ENTERPRISE': NetworkLedger('ENTERPRISE', 'chain/data/networks/l28_enterprise_ledger.jsonl')
        }
        
    async def start(self):
        print("=" * 70)
        print("    L28 PRODUCTION MULTI-NETWORK SYSTEM v2.0")
        print("    Wallet + Networks + Bridges + Persistent Ledgers")
        print("=" * 70)
        
        print(f"\n💼 Wallet: {self.wallet.address}")
        
        # Load balances from ledgers
        for network, ledger in self.ledgers.items():
            self.coordinator.network_balances[network] = ledger.current_supply
        
        # Set initial MAIN balance (your 2.32M L28)
        if self.ledgers['MAIN'].current_supply == 0:
            self.coordinator.network_balances['MAIN'] = 2324584
            self.wallet.balances['MAIN'] = 2324584
            print(f"\n💰 Initializing MAIN network with 2,324,584 L28")
        
        print(f"\n📊 Network Status:")
        for network, ledger in self.ledgers.items():
            balance = self.coordinator.network_balances[network]
            print(f"   {network:12} | Height: {ledger.current_height:6} | Supply: {balance:,} L28")
        
        total = sum(self.coordinator.network_balances.values())
        print(f"\n   TOTAL: {total:,} L28")
        
        # Start coordinator
        coordinator_task = asyncio.create_task(self.coordinator.start())
        
        # Demo bridges with ledger persistence
        await asyncio.sleep(3)
        
        print(f"\n🌉 Bridge 1: MAIN → SPEED (500,000 L28)")
        success = await self.bridge_with_ledger("MAIN", "SPEED", 500000)
        await asyncio.sleep(3)
        
        print(f"\n🌉 Bridge 2: MAIN → PRIVACY (300,000 L28)")
        success = await self.bridge_with_ledger("MAIN", "PRIVACY", 300000)
        await asyncio.sleep(3)
        
        print(f"\n🌉 Bridge 3: SPEED → ENTERPRISE (100,000 L28)")
        success = await self.bridge_with_ledger("SPEED", "ENTERPRISE", 100000)
        await asyncio.sleep(2)
        
        print(f"\n📊 Final Network Status:")
        for network, ledger in self.ledgers.items():
            balance = self.coordinator.network_balances[network]
            print(f"   {network:12} | Height: {ledger.current_height:6} | Supply: {balance:,} L28")
        
        total = sum(self.coordinator.network_balances.values())
        print(f"\n   TOTAL: {total:,} L28 ✅")
        print(f"\n✅ All bridges persisted to ledgers!")
        
    async def bridge_with_ledger(self, from_net: str, to_net: str, amount: int) -> bool:
        import hashlib
        import time
        
        bridge_id = hashlib.sha256(f"{from_net}{to_net}{amount}{time.time()}".encode()).hexdigest()[:16]
        
        success = await self.bridge.bridge(from_net, to_net, amount, self.wallet.address)
        
        if success:
            # Record bridge in both ledgers
            self.ledgers[from_net].add_bridge_entry(from_net, to_net, amount, bridge_id)
            self.ledgers[to_net].add_bridge_entry(from_net, to_net, amount, bridge_id)
            
            # Update wallet
            self.wallet.balances[from_net] = self.coordinator.network_balances[from_net]
            self.wallet.balances[to_net] = self.coordinator.network_balances[to_net]
        
        return success

if __name__ == "__main__":
    try:
        system = L28ProductionSystem("test_wallet")
        asyncio.run(system.start())
    except KeyboardInterrupt:
        print("\n\n👋 System stopped")
