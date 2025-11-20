#!/usr/bin/env python3
from enum import Enum
from dataclasses import dataclass

class NetworkType(Enum):
    MAIN = "MAIN"
    SPEED = "SPEED"
    PRIVACY = "PRIVACY"
    ENTERPRISE = "ENTERPRISE"

@dataclass
class NetworkConfig:
    name: str
    difficulty: int
    target_time: float
    reward: int
    halving_interval: int
    adjustment_period: int

NETWORKS = {
    NetworkType.MAIN: NetworkConfig(
        name="MAIN", difficulty=18, target_time=30.0, reward=28,
        halving_interval=210000, adjustment_period=100
    ),
    NetworkType.SPEED: NetworkConfig(
        name="SPEED", difficulty=18, target_time=10.0, reward=14,
        halving_interval=420000, adjustment_period=50
    ),
    NetworkType.PRIVACY: NetworkConfig(
        name="PRIVACY", difficulty=20, target_time=60.0, reward=42,
        halving_interval=105000, adjustment_period=100
    ),
    NetworkType.ENTERPRISE: NetworkConfig(
        name="ENTERPRISE", difficulty=18, target_time=30.0, reward=21,
        halving_interval=210000, adjustment_period=100
    )
}

MIN_DIFFICULTY = 18
MAX_DIFFICULTY = 24

class DifficultyRetarget:
    @staticmethod
    def calculate_new_difficulty(current_difficulty, actual_time, target_time, entries_count):
        expected_total = target_time * entries_count
        ratio = actual_time / expected_total
        ratio = max(0.25, min(4.0, ratio))
        if ratio < 0.5: new_difficulty = current_difficulty + 2
        elif ratio < 0.75: new_difficulty = current_difficulty + 1
        elif ratio > 2.0: new_difficulty = current_difficulty - 2
        elif ratio > 1.5: new_difficulty = current_difficulty - 1
        else: new_difficulty = current_difficulty
        return max(MIN_DIFFICULTY, min(MAX_DIFFICULTY, new_difficulty))

retarget = DifficultyRetarget()
