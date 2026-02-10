# SPDX-License-Identifier: Apache-2.0
"""
Transaction Builder
Helper for creating L28 transactions (dict-based, validator-compatible).
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

# Protocol-reserved pseudo-accounts (must NEVER be creatable via TransactionBuilder)
# HARDENED: TX_BUILDER_RESERVED_SENDER_GUARD_V1
RESERVED_SENDERS = {"COINBASE", "__MINT__"}


class TransactionBuilder:
    """Builder pattern for L28 transactions (returns a dict)."""

    def __init__(self) -> None:
        self.sender: Optional[str] = None
        self.receiver: Optional[str] = None
        self.amount: Optional[int] = None
        self.timestamp: Optional[int] = None
        self.metadata: Dict[str, Any] = {}

    def from_address(self, address: str) -> "TransactionBuilder":
        """Set sender address (reserved protocol senders are forbidden)."""
        addr = str(address)
        # HARDENED: TX_BUILDER_RESERVED_SENDER_GUARD_V1: block reserved protocol senders
        if addr in RESERVED_SENDERS:
            raise ValueError("Reserved sender address is not allowed")
        self.sender = addr
        return self

    def to_address(self, address: str) -> "TransactionBuilder":
        """Set receiver address."""
        self.receiver = str(address)
        return self

    def with_amount(self, amount: int) -> "TransactionBuilder":
        """Set amount."""
        try:
            amt = int(amount)
        except Exception as e:
            raise ValueError("Amount must be an integer") from e
        if amt <= 0:
            raise ValueError("Amount must be > 0")
        self.amount = amt
        return self

    def with_timestamp(self, timestamp: int) -> "TransactionBuilder":
        """Set explicit timestamp (unix seconds)."""
        try:
            ts = int(timestamp)
        except Exception as e:
            raise ValueError("Timestamp must be an integer") from e
        if ts <= 0:
            raise ValueError("Timestamp must be > 0")
        self.timestamp = ts
        return self

    def with_metadata(self, key: str, value: Any) -> "TransactionBuilder":
        """Add metadata."""
        self.metadata[str(key)] = value
        return self

    def build(self) -> Dict[str, Any]:
        """Build a validator-compatible transaction dict."""
        if not self.sender or not self.receiver or self.amount is None:
            raise ValueError("Sender, receiver, and amount required")

        # HARDENED: TX_BUILDER_RESERVED_SENDER_GUARD_V1: fail-closed validation
        if str(self.sender) in RESERVED_SENDERS:
            raise ValueError("Reserved sender address is not allowed")

        ts = int(self.timestamp) if self.timestamp is not None else int(time.time())

        tx: Dict[str, Any] = {
            "sender": str(self.sender),
            "receiver": str(self.receiver),
            "amount": int(self.amount),
            "timestamp": ts,
        }

        if self.metadata:
            tx["metadata"] = dict(self.metadata)

        return tx
