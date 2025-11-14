"""
Complete Wallet Management System
"""
import hashlib
import secrets
from typing import Dict, List, Optional
import json
from pathlib import Path

class WalletManager:
    """Complete wallet management with balance tracking"""
    
    def __init__(self, data_dir: str = "data/wallets"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.wallets = {}
        self.balances = {}
    
    def create_wallet(self, name: str) -> Dict:
        """Create new L28 wallet"""
        # Generate private key
        private_key = secrets.token_hex(32)
        
        # Generate public key (simplified)
        public_key = hashlib.sha256(private_key.encode()).hexdigest()
        
        # Generate address
        address = "L28" + hashlib.sha256(public_key.encode()).hexdigest()[:40]
        
        wallet = {
            'name': name,
            'address': address,
            'public_key': public_key,
            'private_key': private_key,  # In production, encrypt this!
            'balance': 0
        }
        
        self.wallets[address] = wallet
        self.balances[address] = 0
        
        # Save wallet
        self._save_wallet(wallet)
        
        return wallet
    
    def get_balance(self, address: str) -> int:
        """Get wallet balance"""
        return self.balances.get(address, 0)
    
    def update_balance(self, address: str, amount: int):
        """Update wallet balance"""
        if address not in self.balances:
            self.balances[address] = 0
        self.balances[address] += amount
    
    def _save_wallet(self, wallet: Dict):
        """Save wallet to disk"""
        wallet_file = self.data_dir / f"{wallet['address']}.json"
        with open(wallet_file, 'w') as f:
            json.dump(wallet, f, indent=2)
    
    def list_wallets(self) -> List[Dict]:
        """List all wallets"""
        return list(self.wallets.values())
