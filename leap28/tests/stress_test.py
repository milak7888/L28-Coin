#!/usr/bin/env python3
import asyncio
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from multinetwork.core.sync_coordinator import L28SyncCoordinator
from multinetwork.core.bridge_manager import L28BridgeManager

class StressTest:
    def __init__(self):
        self.coordinator = L28SyncCoordinator()
        self.bridge = L28BridgeManager(self.coordinator)
        self.errors = []
        
    async def test_rapid_bridges(self):
        print("\n🧪 TEST 1: Rapid Bridges (100 ops)")
        self.coordinator.network_balances["MAIN"] = 1_000_000
        self.coordinator.running = True
        start = time.time()
        for i in range(100):
            if i % 4 == 0:
                await self.bridge.bridge("MAIN", "SPEED", 1000, f"t{i}")
            elif i % 4 == 1:
                await self.bridge.bridge("SPEED", "PRIVACY", 500, f"t{i}")
            elif i % 4 == 2:
                await self.bridge.bridge("PRIVACY", "ENTERPRISE", 250, f"t{i}")
            else:
                await self.bridge.bridge("ENTERPRISE", "MAIN", 100, f"t{i}")
        elapsed = time.time() - start
        total = sum(self.coordinator.network_balances.values())
        print(f"   ✅ 100 bridges in {elapsed:.2f}s ({100/elapsed:.1f}/sec)")
        if total == 1_000_000:
            print(f"   ✅ Supply preserved: {total:,} L28")
        else:
            self.errors.append(f"Supply error: {total:,}")
    
    async def run_all_tests(self):
        print("L28 STRESS TEST")
        asyncio.create_task(self.coordinator.start())
        await asyncio.sleep(1)
        await self.test_rapid_bridges()
        await asyncio.sleep(1)
        if not self.errors:
            print("\n✅ ALL TESTS PASSED!")
        else:
            print(f"\n❌ {len(self.errors)} errors")

asyncio.run(StressTest().run_all_tests())
