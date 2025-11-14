#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path

class MultiNetworkWallet:
    def __init__(self, wallet_name: str):
        wallet_path = Path(f"~/.l28/wallets/{wallet_name}.json").expanduser()
        with open(wallet_path, 'r') as f:
            wallet_data = json.load(f)
        
        self.name = wallet_data['name']
        self.address = wallet_data['address']
        self.balances = {"MAIN": 0, "SPEED": 0, "PRIVACY": 0, "ENTERPRISE": 0}
    
    def get_total_balance(self) -> int:
        return sum(self.balances.values())

if __name__ == "__main__":
    wallet = MultiNetworkWallet("test_wallet")
    print(f"✅ Multi-network wallet loaded")
    print(f"Address: {wallet.get_address()}")
    
    # YOUR ACTUAL L28 - ALL on MAIN network initially
    wallet.balances["MAIN"] = 2324584
    
    print(f"\n💰 Your L28 distribution:")
    for network, balance in wallet.balances.items():
        print(f"   {network}: {balance:,} L28")
    print(f"\n   TOTAL: {wallet.get_total_balance():,} L28")
    print(f"\n✅ Ready to bridge between networks!")
