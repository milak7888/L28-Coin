# SPDX-License-Identifier: Apache-2.0
"""Run two independent validators against pinned offline consensus vectors."""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from coin import disposable_testnet_identity as identity
from coin.ledger import BlocklessLedger
from coin.tx_validation import is_coinbase_tx, validate_transaction

PROFILE = "l28-offline-consensus-vectors/v0.1"
NETWORK = "L28-DISPOSABLE-CONSENSUS-VECTORS-V01"
POLICY = "l28-offline-consensus-policy/v0.1"
INITIAL_TARGET = 2**252 - 1
MIN_TARGET = 2**250 - 1
MAX_TARGET = 2**254 - 1
WINDOW = 2
INTERVAL = 12
MAX_FIXTURE_BYTES = 65536
FIXTURE_SHA256 = "fa61e7689be415ee68c47d1442c4db6c7d594b853340094be59f04feb1581239"
FIXTURE_NAME = "l28_offline_consensus_vectors_v0_1.json"
FIXTURE_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / FIXTURE_NAME


class Rejected(ValueError):
    """A rejected disposable candidate or a failed verification gate."""


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def parse_fixture(raw):
    if len(raw) > MAX_FIXTURE_BYTES or hashlib.sha256(raw).hexdigest() != FIXTURE_SHA256:
        raise Rejected("fixture_digest_mismatch")
    return json.loads(raw)


def check_offline_authority():
    if any((
        identity.RUNTIME_AUTHORIZED, identity.NETWORK_AUTHORIZED, identity.TESTNET_START_AUTHORIZED,
        identity.SIGNING_AUTHORIZED, identity.MINING_AUTHORIZED, identity.BROADCAST_AUTHORIZED,
        identity.SETTLEMENT_AUTHORIZED,
    )):
        raise Rejected("production_authority_active")


def ledger_state(ledger):
    return {"height": ledger.mint_height, "issued_supply": ledger.issued_supply,
            "balances": dict(ledger.balances), "transactions": list(ledger.transactions)}


def checkpoint_for(case, fixture, ledger):
    state = ledger_state(ledger)
    checkpoint = {
        "profile": PROFILE, "network": NETWORK, "policy": POLICY,
        "height": 0, "timestamp": 0, "target": INITIAL_TARGET, "state": digest(state),
    }
    if not case["checkpoint_present"] or fixture["checkpoint"] != checkpoint:
        raise Rejected("missing_consensus_state")
    return {**checkpoint, "id": digest(checkpoint)}


def new_ledger(path):
    return BlocklessLedger(data_dir=str(path), num_shards=1)


async def validate_and_apply(ledger, block):
    header = block["header"]
    transactions = block["transactions"]
    if digest(transactions) != header["transactions"]:
        raise Rejected("transaction_commitment_mismatch")
    if (type(transactions) is not list or len(transactions) != 1
            or type(transactions[0]) is not dict):
        raise Rejected("coinbase_required")
    tx = transactions[0]
    if not is_coinbase_tx(tx) or tx.get("network") != NETWORK:
        raise Rejected("coinbase_required")
    if not ledger.is_canonical_issuance_ready():
        raise Rejected("missing_consensus_state")

    # The checkpoint is height 0. The first event uses reward height 0.
    ok, tx_id, reason = validate_transaction(
        tx,
        policy=ledger.policy,
        current_balance_lookup=lambda address, _network: ledger.get_balance(address),
        seen_tx_lookup=ledger.transactions.__contains__,
        current_height_lookup=lambda: ledger.mint_height,
        current_issued_lookup=lambda: ledger.issued_supply,
        now_ts=header["timestamp"],
        network=NETWORK,
    )
    if not ok:
        raise Rejected(reason)
    if tx.get("id") != tx_id or tx["timestamp"] != header["timestamp"]:
        raise Rejected("coinbase_binding_mismatch")

    # Validate the commitment before writing, then check the real ledger result.
    state = ledger_state(ledger)
    state["height"] += 1
    state["issued_supply"] += tx["amount"]
    balances = state["balances"]
    receiver = tx["receiver"]
    balances[receiver] = balances.get(receiver, 0) + tx["amount"]
    state["transactions"].append(tx_id)
    if digest(state) != header["state"]:
        raise Rejected("state_commitment_mismatch")
    if not await ledger.add_transaction(tx) or ledger_state(ledger) != state:
        raise RuntimeError("ledger_application_mismatch")


async def verify_durable_replay(ledger):
    path = ledger.data_dir / "shard_0.jsonl"
    original = path.read_bytes()
    state = ledger_state(ledger)
    reopened = new_ledger(ledger.data_dir)
    await reopened.load_from_disk(
        validate_replay=True,
        acknowledge_disposable_test_only=True,
        expected_network=NETWORK,
        validate_record=lambda tx: encode(tx) == encode(ledger.transactions.get(tx["id"])),
    )
    if ledger_state(reopened) != state:
        raise RuntimeError("ledger_reload_mismatch")
    last = ledger.transactions[state["transactions"][-1]]
    if await reopened.add_transaction(last):
        raise RuntimeError("replay_accepted")
    if ledger_state(reopened) != state or path.read_bytes() != original:
        raise RuntimeError("replay_mutated_state")
    return hashlib.sha256(original).hexdigest()


async def evaluate(fixture, directory, reverse, verify_header, select):
    results = {}
    for case_name, case in fixture["cases"].items():
        names = sorted(case["branches"], reverse=reverse)
        histories, states, decisions = {}, {}, {}
        for name in names:
            history = histories[name] = []
            verdicts = decisions[name] = []
            ledger = new_ledger(directory / case_name / name)
            for block_name in case["branches"][name]:
                block = fixture["blocks"][block_name]
                try:
                    if not history:
                        checkpoint = checkpoint_for(case, fixture, ledger)
                        ledger.initialize_disposable_test_issuance_state(
                            mint_height=0, issued_supply=0, acknowledge_test_only=True,
                        )
                    block_id = verify_header(block["header"], history, checkpoint)
                    await validate_and_apply(ledger, block)
                except Rejected as error:
                    verdicts.append({"candidate": block_name, "result": str(error)})
                    break
                history.append((block["header"], block_id))
                verdicts.append({"candidate": block_name, "result": "accepted", "id": block_id,
                                 "height": block["header"]["height"], "target": block["header"]["target"]})
            if history:
                state = ledger_state(ledger)
                states[history[-1][1]] = {
                    **state, "state_commitment": digest(state),
                    "ledger_sha256": await verify_durable_replay(ledger),
                    "replay_rejected_without_mutation": True,
                }
        status, tip, work = select(histories)
        results[case_name] = {
            "status": status, "tip": tip, "branch_work": work,
            "branches": decisions, "selected_state": states.get(tip),
        }
    return results


def worker_main(verify_header, select):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--reverse", action="store_true")
    args = parser.parse_args()
    try:
        check_offline_authority()
        fixture = parse_fixture(sys.stdin.buffer.read(MAX_FIXTURE_BYTES + 1))
        args.work_dir.mkdir(mode=0o700)
        cases = asyncio.run(evaluate(fixture, args.work_dir, args.reverse, verify_header, select))
        print(encode({"cases": cases}).decode("utf-8"))
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"offline validator: {error}\n")
    return 0


def reconcile(left, right):
    if left != right:
        raise Rejected("validator_disagreement")
    return left["cases"]


def check_expectations(actual, expected):
    if actual.keys() != expected.keys():
        raise Rejected("unexpected_cases")
    for name, case in actual.items():
        oracle = expected[name]
        verdicts = {branch: [entry["result"] for entry in results]
                    for branch, results in case["branches"].items()}
        if (case["status"] != oracle["status"] or case["tip"] != oracle["tip"]
                or case["branch_work"] != oracle["branch_work"] or verdicts != oracle["verdicts"]):
            raise Rejected(f"unexpected_decision:{name}")
        winner = case["selected_state"]
        if winner != oracle["selected_state"]:
            raise Rejected(f"unexpected_state:{name}")


def run_worker(module, raw, path, reverse=False):
    command = [sys.executable, "-B", "-m", module, "--work-dir", str(path)]
    if reverse:
        command.append("--reverse")
    result = subprocess.run(command, input=raw, capture_output=True, timeout=30, check=False)
    if result.returncode != 0:
        raise Rejected(f"validator_failed:{module}:{result.returncode}:"
                       f"{result.stderr.decode('utf-8', errors='replace').strip()}")
    return json.loads(result.stdout)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acknowledge-test-only", action="store_true", required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--inject-disagreement", action="store_true")
    args = parser.parse_args(argv)
    try:
        check_offline_authority()
        with FIXTURE_PATH.open("rb") as stream:
            raw = stream.read(MAX_FIXTURE_BYTES + 1)
        fixture = parse_fixture(raw)
        args.work_dir.mkdir(mode=0o700)
        left = run_worker("coin.offline_consensus_validator_a", raw, args.work_dir / "a")
        right = run_worker("coin.offline_consensus_validator_b", raw, args.work_dir / "b", reverse=True)

        # Feed a divergent report to the same gate used for real worker output.
        divergent = {"cases": {**right["cases"], "injected_disagreement": None}}
        if args.inject_disagreement:
            right = divergent
        cases = reconcile(left, right)
        check_expectations(cases, fixture["expected"])
        try:
            reconcile(left, divergent)
        except Rejected as error:
            if str(error) != "validator_disagreement":
                raise
        else:
            raise Rejected("disagreement_probe_failed")

        report = {
            "result": "OFFLINE_CONSENSUS_VECTORS_PASS", "profile": PROFILE, "network": NETWORK,
            "fixture_sha256": FIXTURE_SHA256, "validator_exit_codes": {"a": 0, "b": 0},
            "branch_order": {"a": "ascending", "b": "descending"},
            "divergence_probe": "validator_disagreement", "cases": cases,
        }
        payload = encode(report) + b"\n"
        with (args.work_dir / "result.json").open("xb") as stream:
            stream.write(payload)
        sys.stdout.buffer.write(payload)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"offline consensus vectors: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
