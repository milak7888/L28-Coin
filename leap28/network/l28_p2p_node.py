#!/usr/bin/env python3
"""
L28 P2P Networking
Node discovery, chain sync, peer communication
"""
import asyncio
import json
import socket
import time
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, asdict


@dataclass
class Peer:
    """Represents a peer node"""
    host: str
    port: int
    last_seen: float
    height: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)


class L28Node:
    """P2P node for L28 network"""
    
    def __init__(
        self, 
        host: str = '0.0.0.0',
        port: int = 28280,
        ledger_path: str = 'chain/data/l28_genesis_ledger.jsonl'
    ):
        self.host = host
        self.port = port
        self.ledger_path = ledger_path
        self.peers: Dict[str, Peer] = {}
        self.running = False
        
    async def start(self):
        """Start the P2P node"""
        self.running = True
        print(f"🌐 Starting L28 node on {self.host}:{self.port}")
        
        server = await asyncio.start_server(
            self.handle_connection,
            self.host,
            self.port
        )
        
        # Start background tasks
        asyncio.create_task(self.peer_discovery())
        asyncio.create_task(self.sync_chain())
        
        async with server:
            await server.serve_forever()
    
    async def handle_connection(self, reader, writer):
        """Handle incoming peer connection"""
        addr = writer.get_extra_info('peername')
        print(f"📥 Connection from {addr}")
        
        try:
            data = await reader.read(8192)
            message = json.loads(data.decode())
            
            response = await self.process_message(message)
            
            writer.write(json.dumps(response).encode())
            await writer.drain()
            
        except Exception as e:
            print(f"❌ Error handling connection: {e}")
        
        finally:
            writer.close()
            await writer.wait_closed()
    
    async def process_message(self, message: Dict) -> Dict:
        """Process incoming message from peer"""
        msg_type = message.get('type')
        
        if msg_type == 'ping':
            return {'type': 'pong', 'height': self.get_height()}
        
        elif msg_type == 'get_peers':
            return {
                'type': 'peers',
                'peers': [p.to_dict() for p in self.peers.values()]
            }
        
        elif msg_type == 'get_block':
            height = message.get('height')
            entry = self.get_entry(height)
            return {'type': 'block', 'entry': entry}
        
        elif msg_type == 'get_height':
            return {'type': 'height', 'height': self.get_height()}
        
        elif msg_type == 'new_entry':
            # Received new mined entry from peer
            entry = message.get('entry')
            valid = self.validate_and_add_entry(entry)
            return {'type': 'ack', 'valid': valid}
        
        else:
            return {'type': 'error', 'message': 'Unknown message type'}
    
    async def connect_to_peer(self, host: str, port: int) -> Optional[Dict]:
        """Connect to a peer and send message"""
        try:
            reader, writer = await asyncio.open_connection(host, port)
            
            # Send ping
            message = {'type': 'ping'}
            writer.write(json.dumps(message).encode())
            await writer.drain()
            
            # Get response
            data = await reader.read(8192)
            response = json.loads(data.decode())
            
            writer.close()
            await writer.wait_closed()
            
            # Add to peers
            peer_id = f"{host}:{port}"
            self.peers[peer_id] = Peer(
                host=host,
                port=port,
                last_seen=time.time(),
                height=response.get('height', 0)
            )
            
            print(f"✅ Connected to peer {peer_id}")
            return response
            
        except Exception as e:
            print(f"❌ Failed to connect to {host}:{port}: {e}")
            return None
    
    async def peer_discovery(self):
        """Discover and maintain peer connections"""
        # Bootstrap peers (would be configured)
        bootstrap_peers = [
            # ('127.0.0.1', 28281),
            # ('127.0.0.1', 28282),
        ]
        
        while self.running:
            # Connect to bootstrap peers
            for host, port in bootstrap_peers:
                await self.connect_to_peer(host, port)
            
            # Ask peers for more peers
            for peer_id, peer in list(self.peers.items()):
                try:
                    reader, writer = await asyncio.open_connection(
                        peer.host, peer.port
                    )
                    
                    message = {'type': 'get_peers'}
                    writer.write(json.dumps(message).encode())
                    await writer.drain()
                    
                    data = await reader.read(8192)
                    response = json.loads(data.decode())
                    
                    if response.get('type') == 'peers':
                        for peer_info in response.get('peers', []):
                            new_peer_id = f"{peer_info['host']}:{peer_info['port']}"
                            if new_peer_id not in self.peers:
                                await self.connect_to_peer(
                                    peer_info['host'],
                                    peer_info['port']
                                )
                    
                    writer.close()
                    await writer.wait_closed()
                    
                except:
                    pass
            
            # Wait before next discovery round
            await asyncio.sleep(60)
    
    async def sync_chain(self):
        """Sync blockchain with peers"""
        while self.running:
            my_height = self.get_height()
            
            # Find peer with highest height
            best_peer = None
            max_height = my_height
            
            for peer in self.peers.values():
                if peer.height > max_height:
                    max_height = peer.height
                    best_peer = peer
            
            # Sync if behind
            if best_peer and max_height > my_height:
                print(f"⬇️  Syncing from {best_peer.host}:{best_peer.port}")
                print(f"   Local: {my_height}, Remote: {max_height}")
                
                # Fetch missing entries
                for height in range(my_height + 1, max_height + 1):
                    try:
                        reader, writer = await asyncio.open_connection(
                            best_peer.host, best_peer.port
                        )
                        
                        message = {'type': 'get_block', 'height': height}
                        writer.write(json.dumps(message).encode())
                        await writer.drain()
                        
                        data = await reader.read(8192)
                        response = json.loads(data.decode())
                        
                        if response.get('type') == 'block':
                            entry = response.get('entry')
                            if entry:
                                self.validate_and_add_entry(entry)
                        
                        writer.close()
                        await writer.wait_closed()
                        
                    except Exception as e:
                        print(f"❌ Sync error at height {height}: {e}")
                        break
            
            await asyncio.sleep(30)
    
    async def broadcast_entry(self, entry: Dict):
        """Broadcast newly mined entry to all peers"""
        message = {'type': 'new_entry', 'entry': entry}
        
        for peer in self.peers.values():
            try:
                reader, writer = await asyncio.open_connection(
                    peer.host, peer.port
                )
                
                writer.write(json.dumps(message).encode())
                await writer.drain()
                
                writer.close()
                await writer.wait_closed()
                
            except:
                pass
    
    def get_height(self) -> int:
        """Get current blockchain height"""
        try:
            with open(self.ledger_path, 'r') as f:
                last_line = None
                for line in f:
                    if line.strip():
                        last_line = line
                
                if last_line:
                    entry = json.loads(last_line)
                    return entry.get('entry_height', 0)
        except:
            pass
        
        return 0
    
    def get_entry(self, height: int) -> Optional[Dict]:
        """Get entry at specific height"""
        try:
            with open(self.ledger_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    entry = json.loads(line)
                    if entry.get('entry_height') == height:
                        return entry
        except:
            pass
        
        return None
    
    def validate_and_add_entry(self, entry: Dict) -> bool:
        """
        Validate entry and add to ledger if valid
        TODO: Add full PoW validation
        """
        # Basic validation
        required_fields = ['entry_height', 'hash', 'prev', 'difficulty']
        if not all(f in entry for f in required_fields):
            return False
        
        # Check difficulty
        if not entry['hash'].startswith('0' * entry['difficulty']):
            return False
        
        # TODO: Add to ledger with SafeLedger
        return True


def main():
    """Run L28 P2P node"""
    import argparse
    
    parser = argparse.ArgumentParser(description="L28 P2P Node")
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind')
    parser.add_argument('--port', type=int, default=28280, help='Port to bind')
    parser.add_argument('--ledger', default='chain/data/l28_genesis_ledger.jsonl',
                       help='Path to ledger')
    
    args = parser.parse_args()
    
    node = L28Node(args.host, args.port, args.ledger)
    
    try:
        asyncio.run(node.start())
    except KeyboardInterrupt:
        print("\n👋 Node stopped")


if __name__ == "__main__":
    main()
