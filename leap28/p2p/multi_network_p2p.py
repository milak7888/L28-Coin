#!/usr/bin/env python3
"""Run P2P nodes for all L28 networks simultaneously"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from multinetwork.p2p.network_node import L28NetworkNode

class MultiNetworkP2P:
    def __init__(self):
        self.nodes = {
            'MAIN': L28NetworkNode('MAIN', 28280),
            'SPEED': L28NetworkNode('SPEED', 28281),
            'PRIVACY': L28NetworkNode('PRIVACY', 28282),
            'ENTERPRISE': L28NetworkNode('ENTERPRISE', 28283)
        }
    
    async def start_all(self):
        print("=" * 60)
        print("    L28 MULTI-NETWORK P2P SYSTEM")
        print("    Starting all 4 networks")
        print("=" * 60)
        print()
        
        tasks = []
        for network_name, node in self.nodes.items():
            task = asyncio.create_task(node.start())
            tasks.append(task)
        
        await asyncio.gather(*tasks)
    
    def get_stats(self):
        stats = {}
        for name, node in self.nodes.items():
            stats[name] = {
                'port': node.port,
                'peers': len(node.peers),
                'running': node.running
            }
        return stats

if __name__ == "__main__":
    try:
        p2p = MultiNetworkP2P()
        asyncio.run(p2p.start_all())
    except KeyboardInterrupt:
        print("\n\n👋 All P2P nodes stopped")
