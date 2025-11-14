#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from multinetwork.core.sync_coordinator import L28SyncCoordinator
from multinetwork.core.bridge_manager import L28BridgeManager

async def demo():
    print("L28 MULTI-NETWORK DEMO - 50k L28")
    coordinator = L28SyncCoordinator()
    bridge = L28BridgeManager(coordinator)
    coordinator.network_balances["MAIN"] = 50000
    coordinator.running = True
    asyncio.create_task(coordinator.start())
    await asyncio.sleep(2)
    
    await bridge.bridge("MAIN", "SPEED", 20000, "demo")
    await asyncio.sleep(2)
    await bridge.bridge("MAIN", "PRIVACY", 15000, "demo")
    await asyncio.sleep(2)
    
    print("\nFinal:")
    for net, bal in coordinator.network_balances.items():
        if bal > 0:
            print(f"  {net}: {bal:,} L28")

asyncio.run(demo())
