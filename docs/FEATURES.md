# L28 Production Features - Integration Guide

## 🎯 New Features Added

1. **Wallet System** (`l28_wallet.py`) - ED25519 keypairs & addresses
2. **Safe Ledger** (`l28_safe_ledger.py`) - File locking, backups, verification
3. **P2P Networking** (`l28_p2p_node.py`) - Node sync, peer discovery

---

## 📦 Installation

```bash
cd ~/Projects/Leap28

# Copy new files
cp ~/Downloads/l28_wallet.py leap28/wallet/
cp ~/Downloads/l28_safe_ledger.py leap28/ledger/
cp ~/Downloads/l28_p2p_node.py leap28/network/

# Install dependencies
pip install cryptography --break-system-packages
```

---

## 1. Wallet System

### Create Wallets

```bash
# Create a wallet
python3 leap28/wallet/l28_wallet.py create my_wallet

# Output:
# ✅ Created wallet: my_wallet
#    Address: L28a1b2c3d4e5f6...
#    Saved to: ~/.l28/wallets/my_wallet.json
```

### List Wallets

```bash
python3 leap28/wallet/l28_wallet.py list

# Output:
# 📋 L28 Wallets (3):
#   my_wallet            L28a1b2c3d4e5f6...
#   miner_wallet         L28f6e5d4c3b2a1...
```

### Check Balance

```bash
python3 leap28/wallet/l28_wallet.py balance my_wallet \
  --ledger chain/data/l28_genesis_ledger.jsonl

# Output:
# 💰 Balance for my_wallet:
#    Address: L28a1b2c3d4e5f6...
#    Balance: 280.00 L28
```

### Update Miner to Use Wallet

```bash
# Instead of:
--worker-id "WORKER_1"

# Use:
--wallet my_wallet
```

---

## 2. Safe Ledger Operations

### Verify Integrity

```bash
python3 leap28/ledger/l28_safe_ledger.py \
  --ledger chain/data/l28_genesis_ledger.jsonl \
  verify

# Output:
# 🔍 Verifying ledger integrity...
# Total entries: 100,878
# Hash chain: ✅ Intact
# Overall: ✅ VALID
```

### Create Backup

```bash
python3 leap28/ledger/l28_safe_ledger.py \
  --ledger chain/data/l28_genesis_ledger.jsonl \
  backup

# Output:
# ✅ Backup created: chain/data/backups/l28_ledger_20251108_134500.jsonl
```

### Rollback Ledger

```bash
# Rollback to specific height
python3 leap28/ledger/l28_safe_ledger.py \
  --ledger chain/data/l28_genesis_ledger.jsonl \
  rollback 100500

# Output:
# 📦 Backup created: chain/data/backups/l28_ledger_20251108_134501.jsonl
# ✅ Rolled back to height 100500
```

### Use in Worker

```python
from leap28.ledger.l28_safe_ledger import SafeLedger

ledger = SafeLedger("chain/data/l28_genesis_ledger.jsonl")

# Instead of direct write:
with open(ledger_path, 'a') as f:
    f.write(json.dumps(entry) + '\n')

# Use safe append:
ledger.append_entry_safe(entry)
```

---

## 3. P2P Networking

### Start a Node

```bash
# Node 1 (main)
python3 leap28/network/l28_p2p_node.py \
  --host 0.0.0.0 \
  --port 28280 \
  --ledger chain/data/l28_genesis_ledger.jsonl

# Output:
# 🌐 Starting L28 node on 0.0.0.0:28280
```

### Start Additional Nodes (for testing)

```bash
# Node 2
python3 leap28/network/l28_p2p_node.py \
  --port 28281 \
  --ledger chain/data/l28_node2_ledger.jsonl &

# Node 3
python3 leap28/network/l28_p2p_node.py \
  --port 28282 \
  --ledger chain/data/l28_node3_ledger.jsonl &
```

### Connect Nodes

Edit `l28_p2p_node.py` bootstrap peers:

```python
bootstrap_peers = [
    ('127.0.0.1', 28280),  # Main node
    # ('your_vps_ip', 28280),  # Public node
]
```

### Features:
- ✅ Auto peer discovery
- ✅ Chain sync (pulls missing entries)
- ✅ Broadcast mined entries
- ✅ Detect chain forks

---

## 📋 Updated Mining Workflow

### Old Way (Local Only):
```bash
python3 chain/l28_pow_worker.py \
  --worker-id WORKER_1 \
  --ledger chain/data/l28_genesis_ledger.jsonl
```

### New Way (Production):
```bash
# 1. Create wallet
python3 leap28/wallet/l28_wallet.py create miner1

# 2. Start P2P node
python3 leap28/network/l28_p2p_node.py \
  --host 0.0.0.0 \
  --port 28280 \
  --ledger chain/data/l28_genesis_ledger.jsonl &

# 3. Mine with wallet + safe ledger
python3 chain/l28_pow_worker.py \
  --wallet miner1 \
  --ledger chain/data/l28_genesis_ledger.jsonl \
  --use-safe-ledger \
  --broadcast-to localhost:28280
```

---

## 🔧 Integration Checklist

### Phase 1: Safety (Do Now)
- [ ] Install cryptography
- [ ] Copy `l28_safe_ledger.py` to project
- [ ] Update worker to use `SafeLedger.append_entry_safe()`
- [ ] Verify existing ledger integrity
- [ ] Create backup before continuing

### Phase 2: Wallets (Next)
- [ ] Copy `l28_wallet.py` to project
- [ ] Create miner wallets
- [ ] Update worker to use wallet addresses
- [ ] Migrate miner_id → wallet_address

### Phase 3: Networking (Later)
- [ ] Copy `l28_p2p_node.py` to project
- [ ] Test locally with 2-3 nodes
- [ ] Deploy to VPS/cloud
- [ ] Configure bootstrap peers
- [ ] Open port 28280

---

## 🚀 Production Deploy Sequence

```bash
# 1. STOP all current miners
pkill -f l28_pow_worker

# 2. Backup ledger
python3 leap28/ledger/l28_safe_ledger.py \
  --ledger chain/data/l28_genesis_ledger.jsonl \
  backup

# 3. Verify integrity
python3 leap28/ledger/l28_safe_ledger.py \
  --ledger chain/data/l28_genesis_ledger.jsonl \
  verify

# 4. Create wallets
python3 leap28/wallet/l28_wallet.py create miner1
python3 leap28/wallet/l28_wallet.py create miner2

# 5. Start P2P node
python3 leap28/network/l28_p2p_node.py \
  --host 0.0.0.0 \
  --port 28280 \
  --ledger chain/data/l28_genesis_ledger.jsonl &

# 6. Resume mining (with new features)
# Update worker code to use wallets + safe ledger first
```

---

## 📊 What This Solves

### Before:
❌ Miner IDs (not addresses)  
❌ Race conditions (file corruption)  
❌ Single node only  
❌ No chain sync  
❌ Manual backups  

### After:
✅ Real wallet addresses (ED25519)  
✅ File locking (safe concurrent mining)  
✅ P2P network (multiple nodes)  
✅ Auto chain sync  
✅ Automatic backups/verification  

---

## ⚠️ Important Notes

1. **Wallets**: Private keys stored in `~/.l28/wallets/` - BACKUP THIS!
2. **File Locking**: Only works on same machine - P2P handles multi-machine
3. **P2P**: Still alpha - test locally before production
4. **Backups**: Always backup before rollback
5. **Port**: Open 28280 in firewall for P2P

---

## 🔮 Next Steps

**After integrating these:**
1. Add transaction support (send L28 between addresses)
2. Add mempool (queue pending transactions)
3. Add fork resolution (longest chain wins)
4. Add API endpoints (REST API for wallets/chain)
5. Add web dashboard (monitor network)

**For now:** Focus on wallets + safe ledger. P2P can wait until you're ready for multi-node.

---

## 📞 Quick Commands

```bash
# Create wallet
python3 leap28/wallet/l28_wallet.py create <name>

# Check balance
python3 leap28/wallet/l28_wallet.py balance <name> --ledger <path>

# Verify ledger
python3 leap28/ledger/l28_safe_ledger.py --ledger <path> verify

# Backup ledger
python3 leap28/ledger/l28_safe_ledger.py --ledger <path> backup

# Start node
python3 leap28/network/l28_p2p_node.py --port 28280 --ledger <path>
```

---

**Your L28 is leveling up! 🚀**

Start with wallets + safe ledger today. P2P when you're ready for distributed mining.
