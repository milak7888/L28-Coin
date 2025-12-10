# L28 Coin - Mining Guide

## Status: ✅ OPERATIONAL

Mining L28 entries (not blocks!) via SHA-256 PoW at Difficulty: 18.

## Current Opportunity

**Already Mined:** 2,018,688 L28 (7.21%)  
**Still Available:** 25,981,312 L28 (92.79%)  
**Your Opportunity:** Join early! 90% still available!

## Understanding L28 Mining

### Important: L28 is Blockless!

You're not mining "blocks" - you're mining "entries" in a DAG (Directed Acyclic Graph).

**Traditional Blockchain Mining:**
```
Mine Block 1 → Mine Block 2 → Mine Block 3
(Sequential, one at a time)
```

**L28 Blockless Mining:**
```
Mine Entry → Add to Shard → Parallel Processing
(No blocks, no sequential chain)
```

**But don't worry!** Mining works the same way:
- Solve SHA-256 puzzle ✅
- Get 28 L28 reward ✅
- Difficulty: 18 ✅

## Quick Start (5 Minutes)

### Prerequisites
- Python 3.11+
- 4GB RAM minimum
- Internet connection
- Any OS (macOS, Linux, Windows)

### Installation
```bash
# 1. Clone repository
git clone https://github.com/milak7888/Leap28.git
cd Leap28

# 2. Setup environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 5. Start mining entries!
python -c "
import asyncio
from leap28.mining import L28Miner

async def mine():
    miner = L28Miner('your_L28_address')
    print('⛏️  Mining L28 entry at Difficulty: 18...')
    entry = await miner.mine_block([], '0'*64)
    print(f'✅ Entry mined!')
    print(f'   Hash: {entry[\"hash\"]}')
    print(f'   Reward: 28 L28')

asyncio.run(mine())
"
```

## How Entry Mining Works

### The Process

**Step 1:** Take entry data
```
Data = {transactions, previous_hash, nonce}
```

**Step 2:** Hash with SHA-256
```
Hash = SHA256(Data)
```

**Step 3:** Check if hash has 12 leading zeros
```
Valid:   000000000000a8f2... ✅
Invalid: 0003f8a1e9b4c2d7... ❌
```

**Step 4:** If valid → Entry mined! If not → Try next nonce

**Step 5:** Repeat ~281 trillion times (average)

### Example Mining Attempts
```
Nonce 1:      Hash: 8f3a9b2c... ❌ (0 zeros)
Nonce 1000:   Hash: 0003f8a1... ❌ (3 zeros)
Nonce 10000:  Hash: 000000a8... ❌ (6 zeros)
...
Nonce 441926: Hash: 000000000000f2d8... ✅ (12 zeros!)

🎉 ENTRY MINED! Reward: 28 L28
```

## Mining Commands

### Basic Entry Mining
```bash
python << 'EOF'
import asyncio
from leap28.mining import L28Miner

async def simple_mine():
    miner = L28Miner(
        wallet_address="L28_your_wallet",
        difficulty = 18
    )
    
    entry = await miner.mine_block(
        transactions=[],
        previous_hash="0" * 64
    )
    
    print(f"✅ Entry mined!")
    print(f"   Hash: {entry['hash']}")
    print(f"   Nonce: {entry['nonce']}")
    print(f"   Reward: {miner.block_reward} L28")

asyncio.run(simple_mine())
EOF
```

### Create Wallet First
```bash
python << 'EOF'
from leap28.wallet.l28_wallet import L28Wallet

wallet = L28Wallet()
info = wallet.create_wallet("miner_wallet")

print(f"✅ Wallet created!")
print(f"   Address: {info['address']}")
print(f"   Save this for mining!")
EOF
```

## Hardware Requirements

### Minimum (CPU Mining)
- **CPU:** 2 cores
- **RAM:** 4GB
- **Storage:** 10GB
- **Hashrate:** ~10-100 H/s
- **Time per entry:** Variable (5-60 minutes)

### Recommended
- **CPU:** 4+ cores (like M3 Ultra)
- **RAM:** 8GB
- **Storage:** 50GB SSD
- **Hashrate:** ~1,000-10,000 H/s
- **Time per entry:** Faster (1-10 minutes)

### Professional
- **CPU:** 8+ cores (M3 Ultra, Threadripper)
- **RAM:** 16GB+
- **Storage:** 100GB+ NVMe
- **Hashrate:** ~100,000+ H/s
- **Time per entry:** Very fast (seconds to minutes)

## Difficulty System

### Current: Difficulty: 18
```
Difficulty: 18 = Hash starts with 000000000000
Probability = 1 / (16^12) = 1 / 281,474,976,710,656
```

### Auto-Adjustment

Maintains ~60 second entry time:
```
If entries < 48s: Difficulty increases (12 → 13)
If entries > 72s: Difficulty decreases (12 → 11)  
Otherwise:        Difficulty stays at 12
```

## Mining Rewards

### Current Reward: 28 L28 per Entry
```
Entry 1 - 72,097:    28 L28 each = 2,018,688 L28
Entry 100,875+:       28 L28 (until halving)
```

### Halving Schedule
- Periodic reward reduction (like Bitcoin)
- Keeps supply controlled
- Increases scarcity over time

## Why Mine Now?

✅ **Only 10% mined** - 90% opportunity  
✅ **Fair difficulty** - Same for everyone (18)  
✅ **No pre-mine** - Pure PoW distribution  
✅ **Early miner advantage** - Get in early  
✅ **Real rewards** - 28 L28 per entry  
✅ **Blockless = faster** - Instant finality  

## Mining Time Estimates

At Difficulty: 18:

| Your Hashrate | Time per Entry (avg) |
|--------------|---------------------|
| 1,000 H/s | ~8,900 years |
| 10,000 H/s | ~890 years |
| 100,000 H/s | ~89 years |
| 1,000,000 H/s | ~8.9 years |
| 10,000,000 H/s | ~323 days |
| 100,000,000 H/s | ~32 days |

**Note:** These are averages - you could mine in 1 second or never! That's the nature of PoW.

## Test Mining (Lower Difficulty)

For testing/development, use lower difficulty:
```python
# Difficulty: 18 (test) = ~65,000 attempts
test_miner = L28Miner("your_L28_address")

# Difficulty: 18 (moderate) = ~4 billion attempts  
moderate_miner = L28Miner("your_L28_address")

# Difficulty: 18 (production) = ~281 trillion attempts
prod_miner = L28Miner("your_L28_address")
```

## Security Best Practices

1. **Keep wallet keys secure**
2. **Use strong passwords**
3. **Backup wallet files**
4. **Monitor for anomalies**
5. **Update software regularly**

## Troubleshooting

### Mining is slow
**Normal!** Difficulty: 18 requires ~281 trillion attempts.
- Average time varies wildly (random)
- Could be 1 second or 1 hour
- Patience is key!

### Want to test faster?
Lower difficulty for testing:
```python
miner = L28Miner("your_L28_address")  # Much faster!
```

### Module not found
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

## FAQ

**Q: Why "entry" instead of "block"?**  
A: L28 is blockless! We mine entries in a DAG, not blocks in a chain.

**Q: Does mining work the same way?**  
A: Yes! Same SHA-256 PoW, same rewards, same difficulty.

**Q: Can I mine on my laptop?**  
A: Yes! Any CPU can mine. M3 Ultra works great.

**Q: How long to mine an entry?**  
A: Random! Could be seconds or hours at Difficulty: 18.

**Q: Is it profitable?**  
A: Early miners benefit most. Only 10% mined, 90% opportunity!

---

**Start mining entries today. 90% still available. 100% fair.** ⛏️💎

**2,018,688 entries mined. 900,000+ entries to go.** 🚀
