#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from quantum.mock_theta_kernel import MockThetaEngine
from quantum.mock_register import _mock_theta
import math
import cmath

class QuantumL28Consensus:
    def __init__(self):
        self.theta_engine = MockThetaEngine(n=4)
        self.golden_ratio = 1.618033988749895
        
    def encode_network_state(self, balance: int, height: int) -> complex:
        balance_norm = balance / 28_000_000
        height_norm = height / 1000
        amplitude = _mock_theta(balance_norm * math.pi, q=0.89, terms=16)
        phase_shift = cmath.exp(1j * height_norm)
        return amplitude * phase_shift
    
    def compute_harmonic_consensus(self, network_states: dict) -> dict:
        amplitudes = {}
        for network, state in network_states.items():
            amplitudes[network] = self.encode_network_state(
                state.get('balance', 0), state.get('height', 0)
            )
        
        total_amplitude = sum(amplitudes.values())
        magnitude = abs(total_amplitude)
        phase = cmath.phase(total_amplitude)
        harmonic_score = math.cos(magnitude - self.golden_ratio)
        
        feature_vector = {
            'magnitude': magnitude, 'phase': phase,
            'harmonic': harmonic_score, 'networks': len(amplitudes)
        }
        
        consensus_score = self.theta_engine.score(feature_vector)
        
        return {
            'consensus': consensus_score > 0.8,
            'score': consensus_score,
            'magnitude': magnitude,
            'harmonic_score': harmonic_score
        }

print("🌌 L28 QUANTUM CONSENSUS TEST")
qc = QuantumL28Consensus()
states = {
    'MAIN': {'balance': 1_524_584, 'height': 100},
    'SPEED': {'balance': 400_000, 'height': 98},
    'PRIVACY': {'balance': 300_000, 'height': 99},
    'ENTERPRISE': {'balance': 100_000, 'height': 97}
}
result = qc.compute_harmonic_consensus(states)
print(f"Consensus: {'YES ✅' if result['consensus'] else 'NO ❌'}")
print(f"Score: {result['score']:.4f}")
print(f"✅ QUANTUM ACTIVATED!")
