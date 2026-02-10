"""
Transaction Builder
Helper for creating L28 transactions
"""
import time
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
        
        return Transaction(
            sender=self.sender,
            receiver=self.receiver,
            amount=self.amount,
            timestamp=self.timestamp
        )
