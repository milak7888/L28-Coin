"""
L28 COIN - Main Integration
Connects wallet, consensus, and ledger
"""
import logging
from typing import Optional, Dict

from ..wallet.l28_wallet import L28Wallet
from ..network.multi_network import MultiNetworkManager
from ..network.network_types import NetworkType
from ..ledger.transaction import Transaction
from ..ledger.event import Event

logger = logging.getLogger(__name__)


class L28Coin:
    """
    L28 COIN - Blockless Cryptocurrency
    Integrates wallet + consensus + ledger
    """

    def __init__(self, node_id: str, wallet_dir: str = "~/.l28/wallets"):
        self.node_id = node_id
        self.wallet = L28Wallet(wallet_dir)
        self.network_manager: Optional[MultiNetworkManager] = None
        self.is_running = False

    async def start(self, networks=None, bootstrap_configs=None):
        """
        Start L28 COIN node
        Initializes wallet, consensus, and network
        """
        logger.info("Starting L28 COIN node: %s", self.node_id)

        self.network_manager = MultiNetworkManager(self.node_id)

        # Default: MAIN only
        if networks is None:
            networks = [NetworkType.MAIN]

        await self.network_manager.start(networks, bootstrap_configs)
        self.is_running = True
        logger.info("L28 COIN node started with %d networks", len(networks))

    async def stop(self):
        """Shutdown L28 COIN node"""
        if self.network_manager:
            await self.network_manager.stop()
        self.is_running = False
        logger.info("L28 COIN node stopped")

    def create_wallet(self, name: str) -> Dict:
        """Create new L28 wallet"""
        return self.wallet.create_wallet(name)

    def load_wallet(self, name: str) -> Optional[Dict]:
        """Load existing wallet"""
        try:
            return self.wallet.load_wallet(name)
        except Exception:
            return None

    async def send_transaction(
        self,
        sender_wallet: str,
        receiver_address: str,
        amount: int,
        network: NetworkType = NetworkType.MAIN,
    ) -> bool:
        """
        Send L28 transaction through consensus

        Returns:
            True if transaction finalized, False otherwise
        """
        if not self.is_running:
            logger.error("L28 COIN node not running")
            return False

        if not self.network_manager:
            logger.error("Network manager not initialized")
            return False

        if amount <= 0:
            logger.error("Amount must be > 0")
            return False

        # Load sender wallet
        try:
            wallet_data = self.wallet.load_wallet(sender_wallet)
        except Exception as e:
            logger.error("Wallet %s not found (%s)", sender_wallet, e)
            return False

        import time

        # Create transaction (canonical tx.id derives from core fields)
        tx = Transaction(
            sender=wallet_data["address"],
            receiver=receiver_address,
            amount=int(amount),
            timestamp=int(time.time()),
        )

        # Sign transaction using wallet layer (signature over canonical core payload)
        tx_data = {
            "sender": tx.sender,
            "receiver": tx.receiver,
            "amount": int(tx.amount),
            "timestamp": int(tx.timestamp),
        }
        signature = self.wallet.sign_entry(sender_wallet, tx_data)
        tx.signature = signature

        # Canonical tx id (single source of truth)
        event_id = tx.compute_id()
        tx.id = event_id

        # Create event
        event = Event(
            event_id=event_id,
            transaction=tx,
            timestamp=tx.timestamp,
            shard_id=0,
        )

        # Mark network preference
        if network == NetworkType.SPEED:
            event.requires_speed = True
        elif network == NetworkType.PRIVACY:
            event.requires_privacy = True
        elif network == NetworkType.ENTERPRISE:
            event.is_enterprise = True

        logger.info(
            "Processing transaction: %s... → %s... (%s L28)",
            tx.sender[:8],
            tx.receiver[:8],
            amount,
        )

        result = await self.network_manager.process_event(event)

        if result:
            logger.info("✅ Transaction finalized on %s network", network.value)
        else:
            logger.warning("❌ Transaction rejected")

        return bool(result)
    def get_balance(self, address: str) -> int:
        """Get balance for address.

        Fail-closed: this method must NOT return mock balances.
        Use the ledger/network layer when wired.
        HARDENED: GET_BALANCE_FAIL_CLOSED_V1
        """
        raise NotImplementedError("Balance lookup not wired to ledger/network yet")

    def get_network_stats(self) -> Dict:
        """Get statistics for all running networks"""
        if not self.network_manager:
            return {}
        return self.network_manager.get_network_stats()

    def list_wallets(self):
        """List all wallets"""
        return self.wallet.list_wallets()
