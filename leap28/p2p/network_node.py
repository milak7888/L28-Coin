#!/usr/bin/env python3
import asyncio
import json
from typing import Dict, List, Set

class L28NetworkNode:
    def __init__(self, network_name: str, port: int):
        self.network_name = network_name
        self.port = port
        self.peers: Set[str] = set()
        self.server = None
        self.running = False
        
    async def start(self):
        print(f"🌐 Starting {self.network_name} P2P node on port {self.port}")
        self.running = True
        
        self.server = await asyncio.start_server(
            self.handle_peer, '0.0.0.0', self.port
        )
        
        print(f"   ✅ {self.network_name} listening on {self.port}")
        print(f"   Peers: {len(self.peers)}")
        
        async with self.server:
            await self.server.serve_forever()
    
    async def handle_peer(self, reader, writer):
        addr = writer.get_extra_info('peername')
        peer_id = f"{addr[0]}:{addr[1]}"
        self.peers.add(peer_id)
        print(f"   🔗 New peer: {peer_id}")
        
        try:
            while self.running:
                data = await reader.read(4096)
                if not data:
                    break
        finally:
            self.peers.discard(peer_id)
            writer.close()

if __name__ == "__main__":
    node = L28NetworkNode("MAIN", 28280)
    asyncio.run(node.start())
