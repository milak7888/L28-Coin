# L28 COIN - Blockless Proof-of-Work Cryptocurrency

**Open Source | Quantum-Enhanced | High-Difficulty Mining**

---

## ⚠️ SECURITY DISCLAIMER

**READ THIS BEFORE USING L28**

### Alpha Software Warning
L28 is experimental blockchain software currently in **ALPHA** stage. Use at your own risk.

### Known Limitations
- ❌ **Not Audited**: No security audit has been performed
- ❌ **Experimental**: Core features still in development
- ❌ **No Warranty**: Provided AS-IS with no guarantees
- ❌ **Data Loss Risk**: Backup your wallets and ledger regularly
- ❌ **Network Instability**: P2P sync may fail or fork
- ❌ **Key Management**: You are responsible for securing private keys

### Critical Security Practices

#### 1. **Private Key Security**
```bash
# Your private keys are stored in:
~/.l28/wallets/*.json

# IMMEDIATELY backup this directory:
tar -czf l28_wallets_backup.tar.gz ~/.l28/wallets/
# Store backup on encrypted USB drive or offline storage

# Set restrictive permissions:
chmod 600 ~/.l28/wallets/*.json
chmod 700 ~/.l28/wallets/
```

**⚠️ IF YOU LOSE YOUR PRIVATE KEYS, YOUR L28 IS GONE FOREVER**

#### 2. **Ledger Backup**
```bash
# Backup ledger before ANY operation:
python3 leap28/ledger/l28_safe_ledger.py \
  --ledger chain/data/l28_genesis_ledger.jsonl \
  backup

# Store backups in multiple locations
# Verify backups regularly
```

#### 3. **Network Security**
```bash
# If running P2P node, use firewall:
ufw allow 28280/tcp  # Only if you want public node
ufw enable

# For private mining, DON'T open port 28280
```

#### 4. **Verification**
```bash
# Verify ledger integrity BEFORE mining:
python3 leap28/ledger/l28_safe_ledger.py \
  --ledger chain/data/l28_genesis_ledger.jsonl \
  verify

# Run verification weekly
```

### Legal Disclaimer

**NO FINANCIAL ADVICE**: L28 has no monetary value. Do not treat it as an investment.

**NO LIABILITY**: Developers are not liable for:
- Lost funds or data
- Mining hardware damage
- Network forks or chain splits
- Security breaches
- Any damages whatsoever

**REGULATORY COMPLIANCE**: You are responsible for compliance with local laws regarding cryptocurrency mining and trading.

**OPEN SOURCE LICENSE**: See LICENSE file for terms.

### What Could Go Wrong

**File Corruption:**
- Multiple miners without file locking → corrupted ledger
- Solution: Use `SafeLedger` with locking

**Chain Forks:**
- Network splits → competing chains
- Solution: Longest valid chain wins (implement fork resolution)

**51% Attacks:**
- Entity with >50% hashpower can reorg chain
- Mitigation: High difficulty + distributed miners

**Lost Wallets:**
- Lose private key → lose L28 forever
- Solution: Multiple encrypted backups

**Software Bugs:**
- Alpha code may have critical bugs
- Solution: Test on testnet first, report issues

### Best Practices

1. **Test First**: Run on separate test ledger before production
2. **Small Amounts**: Don't mine large amounts until stable
3. **Regular Backups**: Daily backups of wallets and ledger
4. **Verify Often**: Check ledger integrity regularly
5. **Update Carefully**: Review changes before updating
6. **Report Issues**: File bugs on GitHub
7. **Secure Environment**: Mine on dedicated machine
8. **Monitor Logs**: Watch for errors and warnings

### Emergency Procedures

**If Ledger Corrupted:**
```bash
# Stop all miners immediately
pkill -f l28_pow_worker

# Restore from backup
cp chain/data/backups/l28_ledger_YYYYMMDD_HHMMSS.jsonl \
   chain/data/l28_genesis_ledger.jsonl

# Verify restoration
python3 leap28/ledger/l28_safe_ledger.py \
  --ledger chain/data/l28_genesis_ledger.jsonl \
  verify
```

**If Wallet Compromised:**
```bash
# Create new wallet immediately
python3 leap28/wallet/l28_wallet.py create new_wallet_emergency

# Stop using compromised wallet
# Note: No transaction support yet, so can't transfer funds
```

**If Chain Forks:**
```bash
# Determine longest valid chain
# Rollback to common ancestor
python3 leap28/ledger/l28_safe_ledger.py \
  --ledger chain/data/l28_genesis_ledger.jsonl \
  rollback <HEIGHT>

# Sync from trusted peer
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- 8GB+ RAM
- SSD recommended (for I/O)
- GPU optional (but highly recommended for difficulty 12)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/l28-coin.git
cd l28-coin

# Install dependencies
pip install cryptography --break-system-packages

# Verify installation
python3 tests/test_l28_pow.py
```

### Create Wallet

```bash
# Create your first wallet
python3 leap28/wallet/l28_wallet.py create my_miner

# Backup immediately
tar -czf l28_wallet_backup.tar.gz ~/.l28/wallets/
```

### Start Mining

```bash
# IMPORTANT: Backup ledger first
python3 leap28/ledger/l28_safe_ledger.py \
  --ledger chain/data/l28_genesis_ledger.jsonl \
  backup

# Mine with your wallet (difficulty 12 - GPU recommended)
PYTHONPATH=leap28/consensus/pow:$PYTHONPATH \
python3 chain/l28_pow_worker.py \
  --worker-id my_miner \
  --ledger chain/data/l28_genesis_ledger.jsonl
```

---

## 📊 L28 Specifications

| Property | Value |
|----------|-------|
| **Algorithm** | SHA-256 PoW |
| **Difficulty** | 12 (000000000000...) |
| **Block Time** | 0.89 seconds (target) |
| **Reward** | 28 L28 per entry |
| **Max Supply** | 28,000,000 L28 |
| **Genesis** | 100,061 entries (locked) |
| **Pre-mine** | ~2.82M L28 (10%) |
| **Public Supply** | ~25.18M L28 (90%) |
| **Quantum Enhanced** | Mock Theta scoring |
| **Economic Model** | Black-Scholes reward curve |

### Mining Requirements

**Difficulty 12 Mining:**
- CPU: ~6-10 days per entry (not viable)
- GPU (RTX 3080): ~1-2 hours per entry
- GPU (RTX 4090): ~30-60 minutes per entry
- Network hashrate: ~315 GH/s for target time

---

## 🔒 Security Features

### 1. Genesis Protection
```python
# First 100,061 entries are immutable
GENESIS_LOCKED = 100_060

# Attempting to mine genesis entries raises:
# PermissionError: "Entry X is genesis-locked"
```

### 2. File Locking
```python
# Prevents race conditions and corruption
from leap28.ledger.l28_safe_ledger import SafeLedger

ledger = SafeLedger("chain/data/l28_genesis_ledger.jsonl")

# Atomic append with exclusive lock
ledger.append_entry_safe(entry)
```

### 3. Proof-of-Work Validation
```python
# All entries must meet difficulty requirement
assert entry['hash'].startswith('0' * entry['difficulty'])

# Difficulty 12 = 281 trillion attempts average
```

### 4. Hash Chain Integrity
```python
# Each entry links to previous
entry['prev'] == previous_entry['hash']

# Tampering breaks entire chain
```

---

## 🛠️ Safety Tools

### Verify Ledger Integrity

```bash
python3 leap28/ledger/l28_safe_ledger.py \
  --ledger chain/data/l28_genesis_ledger.jsonl \
  verify

# Checks:
# - Hash chain continuity
# - Duplicate heights
# - JSON validity
# - PoW difficulty
```

### Create Backup

```bash
python3 leap28/ledger/l28_safe_ledger.py \
  --ledger chain/data/l28_genesis_ledger.jsonl \
  backup --dir /path/to/backups

# Creates timestamped backup:
# l28_ledger_20251108_134500.jsonl
```

### Recover from Backup

```bash
# List backups
ls -lh chain/data/backups/

# Restore specific backup
cp chain/data/backups/l28_ledger_20251108_134500.jsonl \
   chain/data/l28_genesis_ledger.jsonl

# Verify restoration
python3 leap28/ledger/l28_safe_ledger.py \
  --ledger chain/data/l28_genesis_ledger.jsonl \
  verify
```

### Rollback Chain

```bash
# Rollback to specific height (creates backup first)
python3 leap28/ledger/l28_safe_ledger.py \
  --ledger chain/data/l28_genesis_ledger.jsonl \
  rollback 100500

# Output:
# 📦 Backup created: chain/data/backups/l28_ledger_20251108_134501.jsonl
# ✅ Rolled back to height 100500
```

### Check Wallet Balance

```bash
python3 leap28/wallet/l28_wallet.py balance my_miner \
  --ledger chain/data/l28_genesis_ledger.jsonl

# Shows:
# - Wallet address
# - Total L28 balance
# - Entries mined
```

---

## 🌐 Network (Alpha)

### Start P2P Node

```bash
python3 leap28/network/l28_p2p_node.py \
  --host 0.0.0.0 \
  --port 28280 \
  --ledger chain/data/l28_genesis_ledger.jsonl

# Features:
# - Peer discovery
# - Chain synchronization
# - Entry broadcasting
# - Fork detection (basic)
```

**⚠️ P2P is experimental - test locally first**

---

## 📁 Project Structure

```
L28/
├── chain/
│   ├── l28_pow_worker.py        # Mining worker
│   └── data/
│       ├── l28_genesis_ledger.jsonl  # Main ledger
│       └── backups/                  # Automatic backups
├── leap28/
│   ├── consensus/
│   │   └── pow/
│   │       └── l28_pow_upgrade.py   # PoW engine
│   ├── wallet/
│   │   └── l28_wallet.py            # Wallet system
│   ├── ledger/
│   │   └── l28_safe_ledger.py       # Safe operations
│   └── network/
│       └── l28_p2p_node.py          # P2P networking
├── tests/
│   └── test_l28_pow.py              # Test suite
├── logs/
│   └── miners/                      # Mining logs
└── ~/.l28/
    └── wallets/                     # Private keys (BACKUP!)
```

---

## 🤝 Contributing

L28 is open source. Contributions welcome:

1. Fork repository
2. Create feature branch
3. Add tests
4. Submit pull request

### Development Priorities
- [ ] Transaction support (send L28 between wallets)
- [ ] Mempool implementation
- [ ] Robust fork resolution
- [ ] API endpoints (REST/GraphQL)
- [ ] Block explorer
- [ ] Mining pool software
- [ ] GPU miner optimization
- [ ] Security audit

---

## 📜 License

MIT License - See LICENSE file

---

## 💬 Community

- GitHub Issues: Bug reports and features
- Discussions: Technical questions
- Wiki: Documentation and guides

---

## ⚡ Performance Tips

### CPU Mining (Not Recommended)
- Use all cores: Start multiple workers
- Expect 6-10 days per entry at difficulty 12
- Better for testnet only

### GPU Mining (Recommended)
- Use CUDA-enabled GPU
- RTX 3080+ recommended
- Consider mining pools when available

### Network Performance
- SSD for ledger I/O
- Fast internet for P2P sync
- Open port 28280 for full node

---

## 🔮 Roadmap

**Phase 1 (Current): Core PoW** ✅
- Genesis protection
- High-difficulty mining
- Basic wallet system
- File locking

**Phase 2 (Q1 2026): Transactions**
- Send/receive L28
- Transaction validation
- Mempool

**Phase 3 (Q2 2026): Network**
- Robust P2P sync
- Fork resolution
- Mining pools

**Phase 4 (Q3 2026): Ecosystem**
- Smart contracts (optional)
- DEX integration
- Mobile wallets

---

## ⚠️ Final Reminder

**L28 is experimental software. Key points:**

1. ✅ **Backup wallets** - Multiple copies, encrypted
2. ✅ **Backup ledger** - Before any operation
3. ✅ **Verify regularly** - Check integrity weekly
4. ✅ **Test first** - Use testnet for experiments
5. ✅ **No guarantees** - Software provided AS-IS
6. ✅ **Report bugs** - Help improve security
7. ✅ **Stay updated** - Monitor GitHub for fixes

**You have been warned. Mine responsibly.** ⛏️

---

**Built with passion. Released to the world. May L28 prosper.** 🚀
