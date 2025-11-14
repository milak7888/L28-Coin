"""
L28 COIN - Main Integration
Connects wallet, consensus, and ledger
"""
import asyncio
import logging
import hashlib
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
        logger.info(f"Starting L28 COIN node: {self.node_id}")
        
        # Initialize multi-network manager
        self.network_manager = MultiNetworkManager(self.node_id)
        
        # Start networks (default: MAIN only for now)
        if networks is None:
            networks = [NetworkType.MAIN]
        
        await self.network_manager.start(networks, bootstrap_configs)
        
        self.is_running = True
        logger.info(f"L28 COIN node started with {len(networks)} networks")
        
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
        return self.wallet.load_wallet(name)
    
    async def send_transaction(
        self,
        sender_wallet: str,
        receiver_address: str,
        amount: int,
        network: NetworkType = NetworkType.MAIN
    ) -> bool:
        """
        Send L28 transaction through consensus
        
        Args:
            sender_wallet: Name of sender's wallet
            receiver_address: Receiver's L28 address
            amount: Amount of L28 to send
            network: Which network to use (MAIN/SPEED/PRIVACY/ENTERPRISE)
        
        Returns:
            True if transaction finalized, False otherwise
        """
        if not self.is_running:
            logger.error("L28 COIN node not running")
            return False
        
        # Load sender wallet
        wallet_data = self.wallet.load_wallet(sender_wallet)
        if not wallet_data:
            logger.error(f"Wallet {sender_wallet} not found")
            return False
        
        # Create transaction
        import time
        tx = Transaction(
            sender=wallet_data['address'],
            receiver=receiver_address,
            amount=amount,
            timestamp=int(time.time())
        )
        
        # Sign transaction using existing sign_entry method
        tx_data = {
            'sender': tx.sender,
            'receiver': tx.receiver,
            'amount': tx.amount,
            'timestamp': tx.timestamp
        }
        signature = self.wallet.sign_entry(sender_wallet, tx_data)
        tx.signature = signature
        
        # FIXED: Create proper event_id as hash
        tx_bytes = f"{tx.sender}{tx.receiver}{tx.amount}{tx.timestamp}".encode()
        event_id = hashlib.sha256(tx_bytes).hexdigest()
        
        # Create event
        event = Event(
            event_id=event_id,
            transaction=tx,
            timestamp=tx.timestamp,
            shard_id=0
        )
        
        # Mark network preference
        if network == NetworkType.SPEED:
            event.requires_speed = True
        elif network == NetworkType.PRIVACY:
            event.requires_privacy = True
        elif network == NetworkType.ENTERPRISE:
            event.is_enterprise = True
        
        # Process through consensus
        logger.info(f"Processing transaction: {tx.sender[:8]}... → {tx.receiver[:8]}... ({amount} L28)")
        result = await self.network_manager.process_event(event)
        
        if result:
            logger.info(f"✅ Transaction finalized on {network.value} network")
        else:
            logger.warning(f"❌ Transaction rejected")
        
        return result
    
    def get_balance(self, address: str) -> int:
        """Get balance for address"""
        logger.warning("Balance checking not yet implemented - using mock")
        return 1000
    
    def get_network_stats(self) -> Dict:
        """Get statistics for all running networks"""
        if not self.network_manager:
            return {}
        return self.network_manager.get_network_stats()
    
    def list_wallets(self):
        """List all wallets"""
        return self.wallet.list_wallets()
