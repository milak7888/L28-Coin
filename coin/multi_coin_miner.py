import hashlib
import time

def mine_bitcoin(addr, difficulty=18, max_attempts=10000):
    for n in range(max_attempts):
        h = hashlib.sha256(f"BTC:{addr}:{n}".encode()).hexdigest()
        if h.startswith("0" * difficulty):
            return {"coin": "BTC", "nonce": n, "hash": h}
    return None

def mine_ethereum(addr, difficulty=10, max_attempts=10000):
    for n in range(max_attempts):
        h = hashlib.sha256(f"ETH:{addr}:{n}".encode()).hexdigest()
        if h.startswith("0" * difficulty):
            return {"coin": "ETH", "nonce": n, "hash": h}
    return None

def mine_solana(addr, difficulty=8, max_attempts=10000):
    for n in range(max_attempts):
        h = hashlib.sha256(f"SOL:{addr}:{n}".encode()).hexdigest()
        if h.startswith("0" * difficulty):
            return {"coin": "SOL", "nonce": n, "hash": h}
    return None

def l28_work_hash(work_input, nonce):
    return hashlib.sha256(f"L28:{work_input}:{nonce}".encode()).hexdigest()


def mine_l28(addr, difficulty=18, max_attempts=10000):
    for n in range(max_attempts):
        h = l28_work_hash(addr, n)
        if h.startswith("0" * difficulty):
            return {"coin": "L28", "nonce": n, "hash": h}
    return None
