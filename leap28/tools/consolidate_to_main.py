#!/usr/bin/env python3
"""Consolidate all L28 back to MAIN network"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from multinetwork.core.sync_coordinator import L28SyncCoordinator
from multinetwork.core.bridge_manager import L28BridgeManager
from multinetwork.core.network_ledger import NetworkLedger
from multinetwork.integration.wallet_connector import MultiNetworkWallet

async def consolidate():
    print("🔄 Consolidating all L28 back to MAIN network...")
    
    wallet = MultiNetworkWallet("test_wallet")
    coordinator = L28SyncCoordinator()
    bridge = L28BridgeManager(coordinator)
    
    # Load current state from ledgers
    ledgers = {
        'MAIN': NetworkLedger('MAIN', 'chain/data/networks/l28_main_ledger.jsonl'),
        'SPEED': NetworkLedger('SPEED', 'chain/data/networks/l28_speed_ledger.jsonl'),
        'PRIVACY': NetworkLedger('PRIVACY', 'chain/data/networks/l28_privacy_ledger.jsonl'),
        'ENTERPRISE': NetworkLedger('ENTERPRISE', 'chain/data/networks/l28_enterprise_ledger.jsonl')
    }
    
    for network, ledger in ledgers.items():
        coordinator.network_balances[network] = ledger.current_supply
    
    print("\n📊 Current Distribution:")
    for network, balance in coordinator.network_balances.items():
        if balance > 0:
            print(f"   {network}: {balance:,} L28")
    
    # Start coordinator
    coordinator.running = True
    
    # Bridge everything back to MAIN
    for network in ['ENTERPRISE', 'PRIVACY', 'SPEED']:
        amount = coordinator.network_balances[network]
        if amount > 0:
            print(f"\n🌉 Bridging {amount:,} L28: {network} → MAIN")
            await bridge.bridge(network, "MAIN", amount, wallet.address)
            
            # Record in ledgers
            import hashlib, time
            bridge_id = hashlib.sha256(f"{network}MAIN{amount}{time.time()}".encode()).hexdigest()[:16]
            ledgers[network].add_bridge_entry(network, "MAIN", amount, bridge_id)
            ledgers["MAIN"].add_bridge_entry(network, "MAIN", amount, bridge_id)
            
            await asyncio.sleep(1)
    
    print("\n📊 Final Distribution:")
    for network, ledger in ledgers.items():
        balance = coordinator.network_balances[network]
        print(f"   {network}: {balance:,} L28")
    
    total = sum(coordinator.network_balances.values())
    print(f"\n   TOTAL: {total:,} L28")
    print(f"\n✅ All L28 consolidated back to MAIN network!")

if __name__ == "__main__":
    asyncio.run(consolidate())
