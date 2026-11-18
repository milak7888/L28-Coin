# SPDX-License-Identifier: Apache-2.0
"""Simulate or verify one proof-bound coinbase in disposable offline state."""

import argparse
import asyncio
import hashlib
import json
import os
import stat
from pathlib import Path

from coin import disposable_testnet_identity as identity
from coin.ledger import BlocklessLedger
from coin.mining import build_coinbase_tx
from coin.multi_coin_miner import l28_work_hash, mine_l28
from coin.tx_validation import compute_tx_id, transaction_identity_projection

PROFILE = "l28-offline-mining/v0.1"
NETWORK = "L28-DISPOSABLE-OFFLINE-MINING-V01"
MINER = "l28-disposable-offline-miner"
TIMESTAMP = 1_700_000_000
DIFFICULTY = 1
MAX_ATTEMPTS = 512
MAX_CANDIDATE_BYTES = 4096


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _digest(value):
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _state(ledger):
    if not ledger.is_canonical_issuance_ready():
        raise ValueError("disposable_state_uninitialized")
    height = getattr(ledger, "mint_height", None)
    supply = getattr(ledger, "issued_supply", None)
    if type(height) is not int or height < 0 or type(supply) is not int or supply < 0:
        raise ValueError("disposable_height_or_supply_unavailable")
    return {
        "balances": dict(ledger.balances),
        "transaction_ids": sorted(ledger.transactions),
        "mint_height": height,
        "issued_supply": supply,
    }


def _work_input(ledger):
    state = _state(ledger)
    predecessor = _digest({"profile": PROFILE, "network": NETWORK, "state": state})
    template = transaction_identity_projection(build_coinbase_tx(
        MINER, nonce=0, height=state["mint_height"], timestamp=TIMESTAMP, network=NETWORK,
    ))
    del template["nonce"]
    commitment = _digest({
        "profile": PROFILE,
        "network": NETWORK,
        "predecessor": predecessor,
        "coinbase_template": template,
    })
    return predecessor, template, commitment


def _coinbase(template, nonce):
    tx = {**template, "nonce": nonce}
    tx["id"] = compute_tx_id(tx)
    return tx


def _verify_candidate(candidate, predecessor, template, commitment):
    if (type(candidate) is not dict
            or set(candidate) != {"profile", "predecessor", "work_hash", "coinbase"}
            or candidate["profile"] != PROFILE):
        raise ValueError("candidate_schema_invalid")
    if candidate["predecessor"] != predecessor:
        raise ValueError("predecessor_mismatch")
    tx = candidate["coinbase"]
    if type(tx) is not dict or tx.get("network") != NETWORK:
        raise ValueError("coinbase_network_mismatch")
    nonce = tx.get("nonce")
    if type(nonce) is not int or not 0 <= nonce < MAX_ATTEMPTS:
        raise ValueError("nonce_out_of_bounds")
    if _json_bytes(tx) != _json_bytes(_coinbase(template, nonce)):
        raise ValueError("coinbase_template_mismatch")
    expected_hash = l28_work_hash(commitment, nonce)
    if expected_hash != candidate["work_hash"] or not expected_hash.startswith("0" * DIFFICULTY):
        raise ValueError("invalid_work")


def _read_candidate(path):
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    with open(os.open(path, flags), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("candidate_not_regular_file")
        raw = stream.read(MAX_CANDIDATE_BYTES + 1)
    if len(raw) > MAX_CANDIDATE_BYTES:
        raise ValueError("candidate_too_large")
    candidate = json.loads(raw.decode("utf-8"))
    if raw != _json_bytes(candidate) + b"\n":
        raise ValueError("candidate_not_canonical")
    return candidate


def _ledger_file_digest(data_dir):
    files = list(data_dir.glob("shard_*.jsonl"))
    if len(files) != 1:
        raise ValueError("expected_one_ledger_shard")
    return hashlib.sha256(files[0].read_bytes()).hexdigest()


async def _apply_and_verify_replay(ledger, tx):
    if not await ledger.add_transaction(tx):
        raise ValueError("canonical_validator_rejected")
    state = _state(ledger)
    file_digest = _ledger_file_digest(ledger.data_dir)
    tx_bytes = _json_bytes(tx)
    reopened = BlocklessLedger(data_dir=str(ledger.data_dir))
    await reopened.load_from_disk(
        validate_replay=True,
        acknowledge_disposable_test_only=True,
        expected_network=NETWORK,
        validate_record=lambda record: _json_bytes(record) == tx_bytes,
    )
    if _state(reopened) != state:
        raise ValueError("reloaded_state_mismatch")
    if await reopened.add_transaction(tx):
        raise ValueError("replay_accepted")
    if _state(reopened) != state or _ledger_file_digest(reopened.data_dir) != file_digest:
        raise ValueError("replay_mutated_state")
    return state, file_digest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    for mode in ("simulate", "verify"):
        command = modes.add_parser(mode)
        command.add_argument("--acknowledge-test-only", action="store_true", required=True)
        command.add_argument("--work-dir", type=Path, required=True, help="fresh scratch directory")
    modes.choices["verify"].add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        if any((identity.RUNTIME_AUTHORIZED, identity.NETWORK_AUTHORIZED,
                identity.TESTNET_START_AUTHORIZED, identity.MINING_AUTHORIZED,
                identity.SIGNING_AUTHORIZED, identity.BROADCAST_AUTHORIZED,
                identity.SETTLEMENT_AUTHORIZED)):
            raise ValueError("production_authority_active")
        args.work_dir.mkdir(mode=0o700, exist_ok=False)
        ledger = BlocklessLedger(data_dir=str(args.work_dir / "ledger"))
        ledger.initialize_disposable_test_issuance_state(
            mint_height=0, issued_supply=0, acknowledge_test_only=args.acknowledge_test_only,
        )
        predecessor, template, commitment = _work_input(ledger)

        attempts = 0
        if args.mode == "simulate":
            work = mine_l28(commitment, difficulty=DIFFICULTY, max_attempts=MAX_ATTEMPTS)
            if work is None:
                raise ValueError("work_search_exhausted")
            attempts = work["nonce"] + 1
            candidate = {
                "profile": PROFILE,
                "predecessor": predecessor,
                "work_hash": work["hash"],
                "coinbase": _coinbase(template, work["nonce"]),
            }
        else:
            candidate = _read_candidate(args.candidate)

        _verify_candidate(candidate, predecessor, template, commitment)
        tx = candidate["coinbase"]
        state, file_digest = asyncio.run(_apply_and_verify_replay(ledger, tx))
        if args.mode == "simulate":
            with (args.work_dir / "candidate.json").open("xb") as stream:
                stream.write(_json_bytes(candidate) + b"\n")
        print(_json_bytes({
            "profile": PROFILE,
            "network": NETWORK,
            "mode": args.mode,
            "nonce": tx["nonce"],
            "work_hash": candidate["work_hash"],
            "nonce_search_attempts": attempts,
            "predecessor": predecessor,
            "coinbase_id": tx["id"],
            "state": state,
            "state_commitment": _digest({"profile": PROFILE, "network": NETWORK, "state": state}),
            "ledger_file_sha256": file_digest,
            "validated_reload": True,
            "replay_rejected_without_mutation": True,
            "MINING_ACTIVE": identity.MINING_AUTHORIZED,
            "PUBLIC_NETWORK_ACTIVE": identity.NETWORK_AUTHORIZED,
            "PRODUCTION_SIGNER_ACTIVE": identity.SIGNING_AUTHORIZED,
            "BROADCAST": identity.BROADCAST_AUTHORIZED,
            "PRODUCTION_SETTLEMENT": identity.SETTLEMENT_AUTHORIZED,
        }).decode("utf-8"))
    except (OSError, ValueError, RecursionError) as error:
        parser.exit(1, f"offline mining: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
