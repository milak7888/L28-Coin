# L28 Coin - Blockless Architecture

## Current Supply Status

- **Entries Mined:** 100,874
- **L28 Mined:** 2,824,500 (10.09%)
- **L28 Available:** 25,175,500 (89.91%)
- **Max Supply:** 28,000,000 L28

All tokens mined via SHA-256 PoW at Difficulty: 18.

## Blockless Architecture Explained

### What "Blockless" Means

**Traditional Blockchain:**
- Blocks linked sequentially
- One block processed at a time
- Slow finality (wait for confirmations)

**L28 Blockless (DAG):**
- Entries processed in parallel
- No sequential chain
- Instant finality
- Shard-based storage

### The DAG Structure
```
Entry Flow (Parallel):

Entry 1 → Shard 0 ──┐
Entry 2 → Shard 1 ──┤
Entry 3 → Shard 2 ──┼→ DAG Ledger
Entry 4 → Shard 3 ──┤
Entry 5 → Shard 4 ──┘

(No blocks, no chain, instant processing)
```

## 5-Shard System

### Shard Distribution

Addresses are hashed to determine shard assignment:
```
Shard 0: Entries 0 - 24,999
Shard 1: Entries 25,000 - 49,999
Shard 2: Entries 50,000 - 74,999
Shard 3: Entries 75,000 - 99,999
Shard 4: Entries 100,000+
```

**Benefits:**
- Parallel processing
- No single point of congestion
- Scalable to millions of entries
- Independent shard operations

## Mining System (Without Blocks!)

### Entry Mining Process

1. **Gather Data:** Transactions + previous hash
2. **Add Nonce:** Random number to try
3. **Hash:** SHA-256(data + nonce)
4. **Check:** Does hash start with 12 zeros?
5. **If yes:** Valid entry! Get 28 L28
6. **If no:** Try next nonce (repeat ~281 trillion times)

### Difficulty: 18
```
Target: 000000000000xxxxxxxxxxxxxxxxxx...
        ^^^^^^^^^^^^
        12 zeros required

Probability: 1 / (16^12) = 1 / 281 trillion
```

### Auto-Adjustment

Maintains ~60 second entry time:
```
If entries < 48s: Difficulty increases (12 → 13)
If entries > 72s: Difficulty decreases (12 → 11)
Otherwise:        Difficulty stays at 12
```

## Ledger Structure

### Storage Format (JSONL)

Each entry is one line of JSON:
```json
{
  "entry_height": 100874,
  "current_supply": 2824500,
  "reward": 28.0,
  "hash": "000000000000a8f2...",
  "nonce": 441926,
  "prev": "2b65a3c2...",
  "timestamp": "2025-11-07T17:35:20"
}
```

### Sharding Strategy
```
Address → Hash → Shard ID (0-4)
Transaction → Shard → JSONL file
Balance → Tracked across all shards
```

## Multi-Network System

### Four Networks

1. **MAIN** - Standard transactions, full validation
2. **SPEED** - Optimized for high-speed processing
3. **PRIVACY** - Enhanced privacy features
4. **ENTERPRISE** - Business-grade reliability

All networks share the same L28 token but process differently.

## Performance Metrics

**Current:**
- Entries: 100,874
- Average entry time: ~60 seconds
- Finality: Instant (<1 second)
- TPS: 10,000+ potential

**Comparison to Bitcoin:**
- Bitcoin: 10 minute blocks
- L28: 60 second entries (10x faster)
- Bitcoin: Sequential
- L28: Parallel (even faster)

## Security

**Mining Security:**
- Difficulty: 18 = 281 trillion attempts
- SHA-256 cryptographic hashing
- Auto-adjusting difficulty

**Ledger Security:**
- Each entry references previous
- Cryptographic signatures required
- Distributed across 5 shards
- Open source & auditable

## Fair Distribution
```
Mined:      2,824,500 L28 (10.09%)
Available: 25,175,500 L28 (89.91%)

100% mined via PoW
0% pre-mine
0% founder allocation
```

## Technical Stack

- **Language:** Python 3.11+
- **Mining:** SHA-256 PoW
- **Signing:** ED25519
- **Storage:** JSONL (shard files)
- **Networks:** 4 parallel networks
- **Shards:** 5 independent ledgers

## Developer Resources

- **GitHub:** https://github.com/milak7888/Leap28
- **API:** https://leap28-production.up.railway.app
- **Docs:** Complete and open
- **License:** Apache 2.0

---

**Blockless. Parallel. Instant. Fair.** 🚀💎
