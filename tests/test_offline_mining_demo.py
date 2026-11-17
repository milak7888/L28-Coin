# SPDX-License-Identifier: Apache-2.0
"""Offline fixture tests for proof binding and use of the existing ledger."""

import hashlib
import json
import socket

import pytest

from coin import offline_mining_demo as mining
from coin.ledger import BlocklessLedger
from coin.multi_coin_miner import mine_l28
from coin.tx_validation import compute_tx_id


def run(mode, path, *args):
    return mining.main([mode, "--acknowledge-test-only", "--work-dir", str(path), *args])


def work_hash(commitment, nonce):
    return hashlib.sha256(f"L28:{commitment}:{nonce}".encode("utf-8")).hexdigest()


def test_existing_search_keeps_hash_and_first_nonce_behavior():
    addr = "unchanged-L28-helper"
    nonce = next(n for n in range(512) if work_hash(addr, n).startswith("0"))
    assert mine_l28(addr, difficulty=1, max_attempts=nonce) is None
    assert mine_l28(addr, difficulty=1, max_attempts=nonce + 1) == {
        "coin": "L28", "nonce": nonce, "hash": work_hash(addr, nonce),
    }


@pytest.fixture
def simulation(tmp_path, capsys):
    path = tmp_path / "simulate"
    assert run("simulate", path) == 0
    return path, json.loads(capsys.readouterr().out)


def test_verified_work_replays_with_no_nonce_search_or_network(
    simulation, tmp_path, monkeypatch, capsys,
):
    path, sim = simulation
    original_socket = socket.socket

    def local_sockets_only(family=socket.AF_INET, *args, **kwargs):
        if family in (socket.AF_INET, socket.AF_INET6):
            pytest.fail("offline verification tried to open an IP socket")
        return original_socket(family, *args, **kwargs)

    def forbidden_search(*args, **kwargs):
        pytest.fail("verification tried to search for a nonce")

    monkeypatch.setattr(socket, "socket", local_sockets_only)
    monkeypatch.setattr(mining, "mine_l28", forbidden_search)
    candidate_path = path / "candidate.json"
    before = candidate_path.read_bytes()
    assert run("verify", tmp_path / "verify", "--candidate", str(candidate_path)) == 0
    verified = json.loads(capsys.readouterr().out)
    assert candidate_path.read_bytes() == before
    assert sim.pop("mode") == "simulate"
    assert verified.pop("mode") == "verify"
    assert sim.pop("nonce_search_attempts") == sim["nonce"] + 1 <= 512
    assert verified.pop("nonce_search_attempts") == 0
    assert verified == sim
    assert verified["validated_reload"] is True
    assert verified["replay_rejected_without_mutation"] is True
    assert verified["state"] == {
        "balances": {mining.MINER: 28},
        "issued_supply": 28,
        "mint_height": 1,
        "transaction_ids": [verified["coinbase_id"]],
    }
    assert all(verified[key] is False for key in (
        "MINING_ACTIVE", "PUBLIC_NETWORK_ACTIVE", "PRODUCTION_SIGNER_ACTIVE",
        "BROADCAST", "PRODUCTION_SETTLEMENT",
    ))
    event_file, = (tmp_path / "verify" / "ledger").glob("shard_*.jsonl")
    assert hashlib.sha256(event_file.read_bytes()).hexdigest() == verified["ledger_file_sha256"]
    assert len(event_file.read_bytes().splitlines()) == 1


@pytest.mark.parametrize("field,value,reason", [
    ("profile", "MAIN", "candidate_schema_invalid"),
    ("predecessor", "0" * 64, "predecessor_mismatch"),
    ("work_hash", "0" * 64, "invalid_work"),
    ("network", "MAIN", "coinbase_network_mismatch"),
    ("nonce", True, "nonce_out_of_bounds"),
    ("nonce", 512, "nonce_out_of_bounds"),
    ("amount", 29, "coinbase_template_mismatch"),
    ("height", 100_878, "coinbase_template_mismatch"),
    ("receiver", "other-disposable-miner", "coinbase_template_mismatch"),
    ("signature", "other-signature", "coinbase_template_mismatch"),
])
def test_candidate_mutations_fail_before_issuance(
    field, value, reason, simulation, tmp_path, capsys,
):
    path, _ = simulation
    candidate = json.loads((path / "candidate.json").read_bytes())
    if field in candidate:
        candidate[field] = value
    else:
        tx = candidate["coinbase"]
        tx[field] = value
        tx["id"] = compute_tx_id(tx)
    input_path = tmp_path / "changed.json"
    input_path.write_bytes(mining._json_bytes(candidate) + b"\n")
    work_dir = tmp_path / "verify"
    with pytest.raises(SystemExit) as rejected:
        run("verify", work_dir, "--candidate", str(input_path))
    assert rejected.value.code == 1
    assert reason in capsys.readouterr().err
    assert not list((work_dir / "ledger").glob("*.jsonl"))


def test_recomputed_hash_without_target_is_rejected(tmp_path):
    ledger = BlocklessLedger(data_dir=str(tmp_path / "ledger"))
    ledger.initialize_disposable_test_issuance_state(
        mint_height=0, issued_supply=0, acknowledge_test_only=True,
    )
    predecessor, template, commitment = mining._work_input(ledger)
    nonce = next(n for n in range(512) if not work_hash(commitment, n).startswith("0"))
    candidate = {
        "profile": mining.PROFILE, "predecessor": predecessor,
        "work_hash": work_hash(commitment, nonce),
        "coinbase": mining._coinbase(template, nonce),
    }
    with pytest.raises(ValueError, match="invalid_work"):
        mining._verify_candidate(candidate, predecessor, template, commitment)


def test_work_input_requires_initialized_height_and_supply(tmp_path):
    ledger = BlocklessLedger(data_dir=str(tmp_path / "ledger"))
    with pytest.raises(ValueError, match="disposable_state_uninitialized"):
        mining._work_input(ledger)
    ledger.initialize_disposable_test_issuance_state(
        mint_height=0, issued_supply=0, acknowledge_test_only=True,
    )
    for attr in ("mint_height", "issued_supply"):
        setattr(ledger, attr, None)
        with pytest.raises(ValueError, match="disposable_height_or_supply_unavailable"):
            mining._work_input(ledger)
        setattr(ledger, attr, 0)


def test_search_limit_is_fixed_and_exhaustion_fails_closed(tmp_path, monkeypatch, capsys):
    def exhausted(commitment, *, difficulty, max_attempts):
        assert len(commitment) == 64
        assert difficulty == 1 and max_attempts == 512
        return None

    monkeypatch.setattr(mining, "mine_l28", exhausted)
    work_dir = tmp_path / "exhausted"
    with pytest.raises(SystemExit) as rejected:
        run("simulate", work_dir)
    assert rejected.value.code == 1
    assert "work_search_exhausted" in capsys.readouterr().err
    assert not (work_dir / "candidate.json").exists()
    assert not list((work_dir / "ledger").iterdir())


@pytest.mark.parametrize("body,reason", [
    (b'{"profile":"x","profile":"x"}\n', "candidate_not_canonical"),
    (b" " * 4097, "candidate_too_large"),
])
def test_bounded_canonical_candidate_file(tmp_path, body, reason):
    path = tmp_path / "candidate.json"
    path.write_bytes(body)
    with pytest.raises(ValueError, match=reason):
        mining._read_candidate(path)


def test_requires_opt_in_and_refuses_existing_directory(tmp_path, capsys):
    work_dir = tmp_path / "work"
    with pytest.raises(SystemExit) as rejected:
        mining.main(["simulate", "--work-dir", str(work_dir)])
    assert rejected.value.code == 2
    assert not work_dir.exists()
    work_dir.mkdir()
    marker = work_dir / "keep"
    marker.write_bytes(b"unchanged")
    with pytest.raises(SystemExit) as rejected:
        run("simulate", work_dir)
    assert rejected.value.code == 1
    assert marker.read_bytes() == b"unchanged"
    assert list(work_dir.iterdir()) == [marker]


def test_live_authority_flag_blocks_before_work(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mining.identity, "MINING_AUTHORIZED", True)
    work_dir = tmp_path / "work"
    with pytest.raises(SystemExit) as rejected:
        run("simulate", work_dir)
    assert rejected.value.code == 1
    assert "production_authority_active" in capsys.readouterr().err
    assert not work_dir.exists()
