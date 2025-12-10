# L28 Coin - Blockless Cryptocurrency

## Status: Production Ready

### Official Stats
- **Total Mined:** 2,824,584 L28 (10.09%)
- **Available:** 25,175,416 L28 (89.91%)
- **Max Supply:** 28,000,000 L28
- **Entries:** 100,878
- **Difficulty:** 18
- **Treasury:** 500,000 L28 (permanently locked)

## Quick Start
```bash
git clone https://github.com/milak7888/L28-Coin.git
cd L28-Coin
pip install -r requirements.txt
```

### Create Wallet
```python
from leap28.wallet.l28_wallet import L28Wallet

wallet = L28Wallet()
info = wallet.create_wallet("my_wallet")
print(f"Address: {info['address']}")
```

### Mine L28
```python
import asyncio
from leap28.miner import L28Miner

async def mine():
    miner = L28Miner(wallet_address="your_L28_address")
    block = await miner.mine_block(transactions=[], previous_hash="0"*64)
    print(f"Mined block: {block['hash']}")

asyncio.run(mine())
```

## Documentation
- [Whitepaper](docs/L28_COIN_WHITEPAPER.md)
- [Mining Guide](docs/MINING_GUIDE.md)
- [Architecture](docs/CHAIN_ARCHITECTURE.md)
- [Security](docs/SECURITY.md)

## Features
- Blockless DAG architecture
- SHA-256 PoW (Difficulty 18)
- Instant finality
- Fair launch - 89.91% available

## Treasury
500,000 L28 permanently locked for LEAP28 autonomous operations.
Address: L28882a7cccb94847c09a1d2e661d158a87028f17c3

## License
Apache 2.0

---
**89.91% still available. Fair launch. Start mining.**
