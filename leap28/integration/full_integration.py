#!/usr/bin/env python3
"""Full integration: Multi-network + Wallets + Bridges"""
import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from multinetwork.core.sync_coordinator import L28SyncCoordinator
from multinetwork.core.bridge_manager import L28BridgeManager
from multinetwork.integration.wallet_connector import MultiNetworkWallet

class L28FullSystem:
    def __init__(self, wallet_name: str):
        self.wallet = MultiNetworkWallet(wallet_name)
        self.coordinator = L28SyncCoordinator()
        self.bridge = L28BridgeManager(self.coordinator)
        
    async def start(self):
        print("=" * 60)
        print("    L28 FULL INTEGRATED SYSTEM")
        print("    Wallet + Multi-Network + Bridges")
        print("=" * 60)
        print(f"\n💼 Wallet: {self.wallet.address}")
        
        # Set actual balance from wallet
        self.wallet.balances["MAIN"] = 2324584
        self.coordinator.network_balances["MAIN"] = 2324584
        
        print(f"\n💰 Initial State:")
        print(f"   Your L28: {self.wallet.get_total_balance():,}")
        print(f"   All on MAIN network")
        
        # Start coordinator
        coordinator_task = asyncio.create_task(self.coordinator.start())
        
        # Demo: Bridge L28 between networks
        await asyncio.sleep(2)
        
        print(f"\n🌉 Bridging 500k L28: MAIN → SPEED")
        success = await self.bridge.bridge("MAIN", "SPEED", 500000, self.wallet.address)
        
        if success:
            self.wallet.balances["MAIN"] = self.coordinator.network_balances["MAIN"]
            self.wallet.balances["SPEED"] = self.coordinator.network_balances["SPEED"]
        
        await asyncio.sleep(2)
        
        print(f"\n🌉 Bridging 300k L28: MAIN → PRIVACY")
        success = await self.bridge.bridge("MAIN", "PRIVACY", 300000, self.wallet.address)
        
        if success:
            self.wallet.balances["MAIN"] = self.coordinator.network_balances["MAIN"]
            self.wallet.balances["PRIVACY"] = self.coordinator.network_balances["PRIVACY"]
        
        await asyncio.sleep(2)
        
        print(f"\n📊 Final Distribution:")
        for network, balance in self.wallet.balances.items():
            if balance > 0:
                print(f"   {network}: {balance:,} L28")
        print(f"\n   TOTAL: {self.wallet.get_total_balance():,} L28 ✅")
        print(f"\n✅ Your L28 now distributed across multiple networks!")

if __name__ == "__main__":
    try:
        system = L28FullSystem("test_wallet")
        asyncio.run(system.start())
    except KeyboardInterrupt:
        print("\n\n👋 System stopped")
