"""
Transaction Builder
Helper for creating L28 transactions
"""
import time
# Protocol-reserved pseudo-accounts (must NEVER be creatable via TransactionBuilder)
# HARDENED: TX_BUILDER_RESERVED_SENDER_GUARD_V1
RESERVED_SENDERS = {"COINBASE", "__MINT__"}

from typing import Dict
from ..ledger.transaction import Transaction


class TransactionBuilder:
    """Builder pattern for L28 transactions"""
    
    def __init__(self):
        self.sender = None
        self.receiver = None
        self.amount = None
        self.timestamp = None
        self.metadata = {}
    
    def from_address(self, address: str):
        """Set sender address"""
        self.sender = address
        # HARDENED: TX_BUILDER_RESERVED_SENDER_GUARD_V1: block reserved protocol senders
        if str(address) in RESERVED_SENDERS:
            raise ValueError("Reserved sender address is not allowed")

        return self
    
    def to_address(self, address: str):
        """Set receiver address"""
        self.receiver = address
        return self
    
    def with_amount(self, amount: int):
        """Set amount"""
        self.amount = amount
        return self
    
    def with_metadata(self, key: str, value):
        """Add metadata"""
        self.metadata[key] = value
        return self
    
    def build(self) -> Transaction:
        """Build transaction"""
        if not all([self.sender, self.receiver, self.amount]):
            raise ValueError("Sender, receiver, and amount required")
        
        if self.timestamp is None:
            self.timestamp = int(time.time())
        
        # HARDENED: TX_BUILDER_RESERVED_SENDER_GUARD_V1: fail-closed validation
        
        if str(self.sender) in RESERVED_SENDERS:
        
            raise ValueError("Reserved sender address is not allowed")
        
        try:
        
            amt = int(self.amount)
        
        except Exception:
        
            raise ValueError("Amount must be an integer")
        
        if amt <= 0:
        
            raise ValueError("Amount must be > 0")
        
        self.amount = amt

        
        return Transaction(
            sender=self.sender,
            receiver=self.receiver,
            amount=self.amount,
            timestamp=self.timestamp
        )
