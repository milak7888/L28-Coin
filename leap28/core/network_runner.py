#!/usr/bin/env python3
import asyncio
from sync_coordinator import L28SyncCoordinator
from bridge_manager import L28BridgeManager

class L28NetworkRunner:
    def __init__(self):
        self.coordinator = L28SyncCoordinator()
        self.bridge = L28BridgeManager(self.coordinator)
        
    async def start(self):
        print("=" * 60)
        print("    L28 MULTI-NETWORK SYSTEM v2.0")
        print("    One Coin. Four Networks. Perfect Sync.")
        print("=" * 60)
        print()
        
        self.coordinator.network_balances["MAIN"] = 2_324_584
        self.coordinator.network_balances["SPEED"] = 0
        self.coordinator.network_balances["PRIVACY"] = 0
        self.coordinator.network_balances["ENTERPRISE"] = 0
        
        print("💰 Initial Distribution:")
        for net, balance in self.coordinator.network_balances.items():
            print(f"   {net}: {balance:,} L28")
        print()
        
        tasks = [
            asyncio.create_task(self.coordinator.start()),
            asyncio.create_task(self.demo_bridges())
        ]
        
        await asyncio.gather(*tasks)
    
    async def demo_bridges(self):
        await asyncio.sleep(3)
        
        print("\n🧪 Testing atomic bridges...")
        
        await self.bridge.bridge("MAIN", "SPEED", 500_000, "speed_user")
        await asyncio.sleep(2)
        
        await self.bridge.bridge("MAIN", "PRIVACY", 300_000, "privacy_user")
        await asyncio.sleep(2)
        
        await self.bridge.bridge("SPEED", "ENTERPRISE", 100_000, "corp_user")
        await asyncio.sleep(2)
        
        total = sum(self.coordinator.network_balances.values())
        print(f"\n📊 Final State:")
        for net, balance in self.coordinator.network_balances.items():
            print(f"   {net}: {balance:,} L28")
        print(f"   TOTAL: {total:,} L28 ✅")

if __name__ == "__main__":
    try:
        runner = L28NetworkRunner()
        asyncio.run(runner.start())
    except KeyboardInterrupt:
        print("\n\n👋 L28 networks stopped")
