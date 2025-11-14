#!/usr/bin/env python3
"""
Test L28 Quantum Consensus with Real Bridge Operations
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from multinetwork.core.sync_coordinator import L28SyncCoordinator
from multinetwork.core.bridge_manager import L28BridgeManager
from multinetwork.quantum.quantum_consensus import QuantumL28Consensus

class QuantumBridgeTester:
    def __init__(self):
        self.coordinator = L28SyncCoordinator()
        self.bridge = L28BridgeManager(self.coordinator)
        self.quantum = QuantumL28Consensus()
        
    def get_network_states(self):
        """Get current network states for quantum analysis"""
        return {
            'MAIN': {
                'balance': self.coordinator.network_balances['MAIN'],
                'height': 100  # Mock height for now
            },
            'SPEED': {
                'balance': self.coordinator.network_balances['SPEED'],
                'height': 98
            },
            'PRIVACY': {
                'balance': self.coordinator.network_balances['PRIVACY'],
                'height': 99
            },
            'ENTERPRISE': {
                'balance': self.coordinator.network_balances['ENTERPRISE'],
                'height': 97
            }
        }
    
    async def test_quantum_bridges(self):
        print("=" * 70)
        print("    L28 QUANTUM BRIDGE TEST")
        print("    Real bridges + Quantum consensus validation")
        print("=" * 70)
        print()
        
        # Initialize with 1M L28 on MAIN
        self.coordinator.network_balances["MAIN"] = 1_000_000
        self.coordinator.running = True
        
        # Start coordinator
        asyncio.create_task(self.coordinator.start())
        await asyncio.sleep(1)
        
        print("💰 Initial State:")
        print(f"   MAIN: {self.coordinator.network_balances['MAIN']:,} L28")
        print()
        
        # Test 1: Bridge with quantum validation
        print("🧪 TEST 1: Bridge + Quantum Consensus")
        print("-" * 70)
        
        # Get quantum consensus BEFORE bridge
        states_before = self.get_network_states()
        quantum_before = self.quantum.compute_harmonic_consensus(states_before)
        
        print(f"⚛️  Quantum State BEFORE:")
        print(f"   Consensus Score: {quantum_before['score']:.4f}")
        print(f"   Harmonic: {quantum_before['harmonic_score']:.4f}")
        print(f"   Magnitude: {quantum_before['magnitude']:.4f}")
        print()
        
        # Execute bridge
        print("🌉 Executing: MAIN → SPEED (200,000 L28)")
        success = await self.bridge.bridge("MAIN", "SPEED", 200_000, "quantum_test")
        
        if success:
            await asyncio.sleep(1)
            
            # Get quantum consensus AFTER bridge
            states_after = self.get_network_states()
            quantum_after = self.quantum.compute_harmonic_consensus(states_after)
            
            print(f"\n⚛️  Quantum State AFTER:")
            print(f"   Consensus Score: {quantum_after['score']:.4f}")
            print(f"   Harmonic: {quantum_after['harmonic_score']:.4f}")
            print(f"   Magnitude: {quantum_after['magnitude']:.4f}")
            print()
            
            # Compare quantum states
            score_change = quantum_after['score'] - quantum_before['score']
            harmonic_change = quantum_after['harmonic_score'] - quantum_before['harmonic_score']
            
            print(f"📊 Quantum Analysis:")
            print(f"   Score Change: {score_change:+.4f}")
            print(f"   Harmonic Change: {harmonic_change:+.4f}")
            
            if quantum_after['consensus']:
                print(f"   ✅ Networks still in quantum harmony!")
            else:
                print(f"   ⚠️  Quantum harmony disrupted")
        
        print()
        print("-" * 70)
        
        # Test 2: Multiple rapid bridges with quantum tracking
        print("\n🧪 TEST 2: Rapid Bridges + Quantum Tracking")
        print("-" * 70)
        
        quantum_scores = []
        
        for i in range(5):
            amount = 50_000
            from_net = "MAIN" if i % 2 == 0 else "SPEED"
            to_net = "SPEED" if i % 2 == 0 else "PRIVACY"
            
            print(f"\n🌉 Bridge {i+1}: {from_net} → {to_net} ({amount:,} L28)")
            
            await self.bridge.bridge(from_net, to_net, amount, f"rapid_test_{i}")
            await asyncio.sleep(0.5)
            
            # Check quantum state after each bridge
            states = self.get_network_states()
            quantum = self.quantum.compute_harmonic_consensus(states)
            quantum_scores.append(quantum['score'])
            
            print(f"   ⚛️  Quantum Score: {quantum['score']:.4f} {'✅' if quantum['consensus'] else '⚠️'}")
        
        print()
        print("📈 Quantum Score Evolution:")
        for i, score in enumerate(quantum_scores):
            bar = "█" * int(score * 50)
            print(f"   Bridge {i+1}: {bar} {score:.4f}")
        
        # Final state
        print()
        print("=" * 70)
        print("    FINAL QUANTUM STATE")
        print("=" * 70)
        
        final_states = self.get_network_states()
        final_quantum = self.quantum.compute_harmonic_consensus(final_states)
        
        print(f"\n⚛️  Final Quantum Consensus:")
        print(f"   Score: {final_quantum['score']:.4f}")
        print(f"   Harmonic: {final_quantum['harmonic_score']:.4f}")
        print(f"   Consensus: {'YES ✅' if final_quantum['consensus'] else 'NO ❌'}")
        print()
        
        print("💰 Final Distribution:")
        for network, balance in self.coordinator.network_balances.items():
            if balance > 0:
                print(f"   {network}: {balance:,} L28")
        
        total = sum(self.coordinator.network_balances.values())
        print(f"\n   TOTAL: {total:,} L28")
        
        if total == 1_000_000:
            print("   ✅ Supply preserved!")
        
        print()
        print("🎉 QUANTUM BRIDGE TEST COMPLETE!")

if __name__ == "__main__":
    try:
        tester = QuantumBridgeTester()
        asyncio.run(tester.test_quantum_bridges())
    except KeyboardInterrupt:
        print("\n\n👋 Test stopped")
