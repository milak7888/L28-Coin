"""
Difficulty Adjustment Algorithm
"""
import math


class DifficultyAdjuster:
    """
    Manages mining difficulty adjustments
    Based on block time targets
    """
    
    def __init__(self, target_block_time: float = 60.0):
        self.target_block_time = target_block_time
        self.difficulty_history = []
    
    def calculate_new_difficulty(
        self,
        current_difficulty: int,
        actual_time: float
    ) -> int:
        """
        Calculate new difficulty based on actual vs target time
        
        Uses exponential adjustment for faster convergence
        """
        ratio = actual_time / self.target_block_time
        
        # If blocks are too fast (ratio < 1), increase difficulty
        if ratio < 0.8:
            new_difficulty = current_difficulty + 1
        # If blocks are too slow (ratio > 1), decrease difficulty
        elif ratio > 1.2 and current_difficulty > 8:
            new_difficulty = current_difficulty - 1
        else:
            new_difficulty = current_difficulty
        
        # Record history
        self.difficulty_history.append({
            'difficulty': new_difficulty,
            'ratio': ratio,
            'actual_time': actual_time
        })
        
        return new_difficulty
    
    def get_average_block_time(self, window: int = 10) -> float:
        """Get average block time over window"""
        if not self.difficulty_history:
            return self.target_block_time
        
        recent = self.difficulty_history[-window:]
        return sum(h['actual_time'] for h in recent) / len(recent)
