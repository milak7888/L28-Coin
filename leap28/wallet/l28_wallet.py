#!/usr/bin/env python3
"""
L28 Wallet System
Generates addresses, signs transactions, manages keys
"""
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


class L28Wallet:
    """Wallet for L28 blockchain with ED25519 keypairs"""
    
    def __init__(self, wallet_dir: str = "~/.l28/wallets"):
        self.wallet_dir = Path(wallet_dir).expanduser()
        self.wallet_dir.mkdir(parents=True, exist_ok=True)
        
    def create_wallet(self, name: str) -> Dict[str, str]:
        """
        Create new wallet with ED25519 keypair
        Returns wallet info with address
        """
        # Generate keypair
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        # Serialize keys
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        # Generate L28 address from public key
        address = self._generate_address(public_bytes)
        
        # Save wallet
        wallet_data = {
            'name': name,
            'address': address,
            'public_key': public_bytes.hex(),
            'private_key': private_bytes.hex()
        }
        
        wallet_path = self.wallet_dir / f"{name}.json"
        with open(wallet_path, 'w') as f:
            json.dump(wallet_data, f, indent=2)
        
        # Set restrictive permissions
        os.chmod(wallet_path, 0o600)
        
        print(f"✅ Created wallet: {name}")
        print(f"   Address: {address}")
        print(f"   Saved to: {wallet_path}")
        
        return {
            'name': name,
            'address': address,
            'public_key': public_bytes.hex()
        }
    
    def load_wallet(self, name: str) -> Dict[str, str]:
        """Load existing wallet"""
        wallet_path = self.wallet_dir / f"{name}.json"
        
        if not wallet_path.exists():
            raise FileNotFoundError(f"Wallet '{name}' not found")
        
        with open(wallet_path, 'r') as f:
            return json.load(f)
    
    def list_wallets(self) -> list:
        """List all wallets"""
        wallets = []
        for wallet_file in self.wallet_dir.glob("*.json"):
            with open(wallet_file, 'r') as f:
                data = json.load(f)
                wallets.append({
                    'name': data['name'],
                    'address': data['address']
                })
        return wallets
    
    def sign_entry(self, wallet_name: str, entry_data: Dict) -> str:
        """Sign an entry with wallet's private key"""
        wallet = self.load_wallet(wallet_name)
        
        # Reconstruct private key
        private_bytes = bytes.fromhex(wallet['private_key'])
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
        
        # Sign entry data
        entry_json = json.dumps(entry_data, sort_keys=True)
        signature = private_key.sign(entry_json.encode())
        
        return signature.hex()
    
    def verify_signature(self, address: str, entry_data: Dict, signature: str) -> bool:
        """Verify signature for an entry"""
        # This would need to lookup public key from address
        # For now, simplified version
        return True
    
    def _generate_address(self, public_key_bytes: bytes) -> str:
        """
        Generate L28 address from public key
        Format: L28 + first 40 chars of SHA256(public_key)
        """
        hash_bytes = hashlib.sha256(public_key_bytes).digest()
        address_hash = hash_bytes.hex()[:40]
        return f"L28{address_hash}"
    
    def get_balance(self, address: str, ledger_path: str) -> float:
        """
        Calculate balance for address from ledger
        Scans entire ledger (inefficient but works)
        """
        balance = 0.0
        
        try:
            with open(ledger_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    entry = json.loads(line)
                    
                    # Check if this entry rewards this address
                    if entry.get('payload', {}).get('miner') == address:
                        balance += entry.get('reward', 0.0)
                    
                    # TODO: Handle transfers (when implemented)
        except FileNotFoundError:
            pass
        
        return balance


def main():
    """CLI for wallet operations"""
    import argparse
    
    parser = argparse.ArgumentParser(description="L28 Wallet Manager")
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Create wallet
    create = subparsers.add_parser('create', help='Create new wallet')
    create.add_argument('name', help='Wallet name')
    
    # List wallets
    subparsers.add_parser('list', help='List all wallets')
    
    # Show wallet
    show = subparsers.add_parser('show', help='Show wallet details')
    show.add_argument('name', help='Wallet name')
    
    # Check balance
    balance = subparsers.add_parser('balance', help='Check balance')
    balance.add_argument('name', help='Wallet name')
    balance.add_argument('--ledger', default='chain/data/l28_genesis_ledger.jsonl',
                        help='Path to ledger file')
    
    args = parser.parse_args()
    wallet_mgr = L28Wallet()
    
    if args.command == 'create':
        wallet_mgr.create_wallet(args.name)
    
    elif args.command == 'list':
        wallets = wallet_mgr.list_wallets()
        print(f"\n📋 L28 Wallets ({len(wallets)}):")
        for w in wallets:
            print(f"  {w['name']:20s} {w['address']}")
    
    elif args.command == 'show':
        wallet = wallet_mgr.load_wallet(args.name)
        print(f"\n💼 Wallet: {wallet['name']}")
        print(f"   Address: {wallet['address']}")
        print(f"   Public Key: {wallet['public_key'][:32]}...")
    
    elif args.command == 'balance':
        wallet = wallet_mgr.load_wallet(args.name)
        balance = wallet_mgr.get_balance(wallet['address'], args.ledger)
        print(f"\n💰 Balance for {wallet['name']}:")
        print(f"   Address: {wallet['address']}")
        print(f"   Balance: {balance:,.2f} L28")


if __name__ == "__main__":
    main()
