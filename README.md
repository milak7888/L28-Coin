# L28 Coin - Blockless Cryptocurrency

**Official L28 Coin Repository**

## Status: ✅ Production Ready

L28 Coin is a fully operational blockless cryptocurrency using DAG architecture.

### Quick Stats
- **Total Mined:** 2,824,584 L28 (10.09%)
- **Available:** 25,175,416 L28 (89.91%)
- **Max Supply:** 28,000,000 L28
- **Architecture:** Blockless DAG (5 shards)
- **Consensus:** SHA-256 Proof of Work (Difficulty 12)

## Documentation

- 📄 [Whitepaper](docs/L28_COIN_WHITEPAPER.md) - Complete technical overview
- 🏗️ [Chain Architecture](docs/CHAIN_ARCHITECTURE.md) - Blockless design
- ⛏️ [Mining Guide](docs/MINING_GUIDE.md) - How to mine L28
- 🎯 [Features](docs/FEATURES.md) - Capabilities overview
- 🔒 [Security](docs/SECURITY.md) - Security model

## Installation
```bash
git clone https://github.com/milak7888/L28-Coin.git
cd L28-Coin
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

### Create Wallet
```python
from leap28.wallet.l28_wallet import L28Wallet

wallet = L28Wallet()
info = wallet.create_wallet("my_wallet")
print(f"Address: {info['address']}")
```

### Start Mining
```python
import asyncio
from leap28.mining import L28Miner

async def mine():
    miner = L28Miner('your_address', difficulty=12)
    entry = await miner.mine_block([], '0'*64)
    print(f"Mined! Reward: 28 L28")

asyncio.run(mine())
```

## Key Features

✅ **Blockless Architecture** - DAG-based, no sequential blocks  
✅ **Instant Finality** - Transactions confirmed in <1 second  
✅ **Fair Launch** - Zero pre-mine, 90% still available  
✅ **Multi-Network** - MAIN/SPEED/PRIVACY/ENTERPRISE  
✅ **Quantum-Ready** - Post-quantum cryptography design  

## Powered By LEAP28

L28 Coin is the native currency of the LEAP28 autonomous AI system.

## License

Apache 2.0 - Fully open source

## Links

- **Website:** https://leap28.netlify.app
- **Main Project:** https://github.com/milak7888/Leap28 (Private - AI System)
- **API:** https://leap28-production.up.railway.app

---

**Start mining today. 89.91% still available. 100% fair launch.** 🚀💎
