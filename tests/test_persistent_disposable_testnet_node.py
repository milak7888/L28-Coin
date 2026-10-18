# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import asyncio
import ast
import json
from copy import deepcopy
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import persistent_disposable_testnet_node as node
from coin.tx_validation import (
    L28_EMISSION_CEILING,
    L28_HISTORICAL_LAST_ENTRY,
    L28_HISTORICAL_MINED,
    L28_MAX_SUPPLY,
    L28_NEXT_HEIGHT_AFTER_CHECKPOINT,
)


ROOT = Path(__file__).resolve().parents[1]
IMPL_PATH = ROOT / "coin/persistent_disposable_testnet_node.py"


def _events():
    private_key = Ed25519PrivateKey.generate()
    binding = node.persistent_testnet_binding()
    writer = node.public_identity(node._public_key_hex(private_key))
    events = [
        node._build_coinbase(writer),
        node._build_signed_transfer(private_key, node.follower_identity(binding)),
    ]
    del private_key
    return events


def test_binding_is_disposable_and_all_production_authority_stays_false():
    binding = node.persistent_testnet_binding()
    assert binding["network_id"] == node.NETWORK_ID
    assert binding["data_dir_tag"] == node.DATA_DIR_TAG
    assert binding["network_scope"] == "DISPOSABLE_TEST_ONLY"
    for field in (
        "runtime_authorized",
        "network_authorized",
        "testnet_start_authorized",
        "signing_authorized",
        "mining_authorized",
        "broadcast_authorized",
        "settlement_authorized",
    ):
        assert binding[field] is False


def test_coinbase_and_transfer_use_existing_validator_and_ledger(tmp_path):
    ledger = node._new_ledger(tmp_path)
    events = _events()
    assert asyncio.run(node._apply_events(ledger, events)) == [
        event["id"] for event in events
    ]
    state = node.ledger_state(ledger)
    assert state["transaction_ids"] == [event["id"] for event in events]
    assert state["issued_supply"] == 28
    assert state["mint_height"] == 1
    assert state["total_transactions"] == 2
    assert sorted(state["balances"].values()) == [0, 28]
    replay_ok, replay_id, replay_reason = node.classify_event(ledger, events[-1])
    assert (replay_ok, replay_id, replay_reason) == (
        False,
        events[-1]["id"],
        "replay",
    )


def test_validated_durable_replay_reconstructs_exact_state(tmp_path):
    ledger = node._new_ledger(tmp_path)
    events = _events()
    asyncio.run(node._apply_events(ledger, events))
    before = node.ledger_state(ledger)
    reopened = asyncio.run(node._load_ledger(tmp_path))
    assert reopened.is_canonical_issuance_ready() is True
    assert node.ledger_state(reopened) == before
    assert asyncio.run(reopened.add_transaction(events[-1])) is False
    assert node.ledger_state(reopened) == before


def test_persistence_failure_does_not_expose_memory_ahead_of_disk(
    tmp_path, monkeypatch
):
    ledger = node._new_ledger(tmp_path)
    coinbase = _events()[0]

    async def fail_persist(_transaction, _shard_id):
        raise OSError("test-only persistence failure")

    monkeypatch.setattr(ledger, "_save_transaction", fail_persist)
    assert asyncio.run(ledger.add_transaction(coinbase)) is False
    assert ledger.transactions == {}
    assert ledger.total_transactions == 0
    assert ledger.issued_supply == 0
    assert ledger.mint_height == 0
    assert ledger.get_balance(coinbase["receiver"]) == 0


def test_malformed_cross_network_and_noncanonical_frames_fail_closed():
    binding = node.persistent_testnet_binding()
    encoded = node.encode_frame("initial_events", 1, {"events": []}, binding)
    length = int.from_bytes(encoded[:4], "big")
    body = encoded[4:]
    assert length == len(body)
    assert node.decode_frame(
        body,
        expected_sequence=1,
        expected_message_type="initial_events",
        binding=binding,
    )["network_id"] == node.NETWORK_ID

    parsed = json.loads(body)
    parsed["network_id"] = "L28-DISPOSABLE-WRONG001"
    with pytest.raises(node.PersistentNodeError, match="frame_network_invalid"):
        node.decode_frame(
            node._canonical_bytes(parsed),
            expected_sequence=1,
            expected_message_type="initial_events",
            binding=binding,
        )
    with pytest.raises(node.PersistentNodeError, match="frame_malformed"):
        node.decode_frame(
            b"{",
            expected_sequence=1,
            expected_message_type="initial_events",
            binding=binding,
        )
    with pytest.raises(node.PersistentNodeError, match="frame_noncanonical"):
        node.decode_frame(
            json.dumps(json.loads(body), indent=2).encode("utf-8"),
            expected_sequence=1,
            expected_message_type="initial_events",
            binding=binding,
        )
    bool_version = json.loads(body)
    bool_version["version"] = True
    with pytest.raises(node.PersistentNodeError, match="frame_profile_invalid"):
        node.decode_frame(
            node._canonical_bytes(bool_version),
            expected_sequence=1,
            expected_message_type="initial_events",
            binding=binding,
        )
    bool_sequence = json.loads(body)
    bool_sequence["sequence"] = True
    with pytest.raises(node.PersistentNodeError, match="frame_sequence_invalid"):
        node.decode_frame(
            node._canonical_bytes(bool_sequence),
            expected_sequence=1,
            expected_message_type="initial_events",
            binding=binding,
        )


def test_option_a_halts_divergence_without_rewriting_local_state(tmp_path):
    ledger = node._new_ledger(tmp_path)
    asyncio.run(node._apply_events(ledger, _events()))
    local = node.ledger_state(ledger)
    local_before = deepcopy(local)
    peer = deepcopy(local)
    first_address = sorted(peer["balances"])[0]
    peer["balances"][first_address] += 1
    material = {
        key: peer[key]
        for key in node.STATE_FIELDS
        if key != "state_commitment"
    }
    peer["state_commitment"] = node._state_commitment(material)
    result = node.assess_state_agreement(
        local, peer, node.persistent_testnet_binding()
    )
    assert result["equal"] is False
    assert result["conflict"] is True
    assert result["policy_status"] == "HALTED_CONFLICT"
    assert result["policy_code"] == "HALTED_BY_OPTION_A"
    assert result["canonical_state_changed"] is False
    assert result["ledger_mutated"] is False
    assert local == local_before == node.ledger_state(ledger)


def test_corrupt_and_cross_network_persisted_events_fail_validated_replay(
    tmp_path
):
    source = tmp_path / "source"
    ledger = node._new_ledger(source)
    asyncio.run(node._apply_events(ledger, _events()))
    shard = next(path for path in sorted(source.glob("shard_*.jsonl")) if path.stat().st_size)

    corrupt = tmp_path / "corrupt"
    corrupt.mkdir()
    for path in source.glob("shard_*.jsonl"):
        (corrupt / path.name).write_bytes(path.read_bytes())
    corrupt_shard = corrupt / shard.name
    corrupt_shard.write_bytes(corrupt_shard.read_bytes()[:-1])
    with pytest.raises(ValueError, match="validated_replay_truncated_record"):
        asyncio.run(node._load_ledger(corrupt))

    blank = tmp_path / "blank-record"
    blank.mkdir()
    for path in source.glob("shard_*.jsonl"):
        content = path.read_text(encoding="utf-8")
        if path.name == shard.name:
            content += "\n"
        (blank / path.name).write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="validated_replay_blank_record"):
        asyncio.run(node._load_ledger(blank))

    unexpected = tmp_path / "unexpected-shard"
    unexpected.mkdir()
    for path in source.glob("shard_*.jsonl"):
        (unexpected / path.name).write_bytes(path.read_bytes())
    (unexpected / "shard_99.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="validated_replay_unexpected_shard_file"):
        asyncio.run(node._load_ledger(unexpected))

    wrong = tmp_path / "wrong-network"
    wrong.mkdir()
    for path in source.glob("shard_*.jsonl"):
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            event["network"] = "L28-DISPOSABLE-WRONG001"
            event["id"] = node.compute_tx_id(event)
            records.append(node._canonical_bytes(event).decode("utf-8"))
        (wrong / path.name).write_text(
            "\n".join(records) + ("\n" if records else ""), encoding="utf-8"
        )
    with pytest.raises(ValueError, match="validated_replay_wrong_network"):
        asyncio.run(node._load_ledger(wrong))


def test_real_two_process_restart_workflow_and_no_private_material_persists(
    tmp_path
):
    result = node.execute_persistent_two_node_workflow(tmp_path)
    assert result["transport"] == "IPv4_LOOPBACK_ONLY"
    assert result["node_processes_per_phase"] == 2
    assert result["initial_processes_terminal"] is True
    assert result["restart_processes_terminal"] is True
    assert result["processes_restarted"] is True
    assert result["independent_validation"] is True
    assert len(result["validated_event_ids"]) == 2
    assert result["issued_supply"] == 28
    assert result["mint_height"] == 1
    assert result["total_transactions"] == 2
    assert sorted(result["balances"].values()) == [0, 28]
    assert result["durable_restart_agreement"] is True
    assert result["replay_rejected_after_restart"] is True
    assert result["corruption_rejected"] is True
    assert result["malformed_input_rejected"] is True
    assert result["cross_network_input_rejected"] is True
    assert result["divergence_halted_by_option_a"] is True
    assert result["canonical_history_touched"] is False
    assert result["historical_state_imported"] is False
    assert result["production_keys_used"] is False
    assert result["private_test_material_persisted"] is False
    assert result["mining_used"] is False
    assert result["public_network_used"] is False
    assert result["broadcast_used"] is False
    assert result["production_settlement"] is False
    persisted = "\n".join(
        path.read_text(encoding="utf-8", errors="strict")
        for path in tmp_path.rglob("*")
        if path.is_file()
    )
    for forbidden in (
        "private_key",
        "seed_phrase",
        "mnemonic",
        "xprv",
        "BEGIN PRIVATE",
    ):
        assert forbidden not in persisted


def test_source_has_no_private_serialization_public_bind_or_mining_call():
    source = IMPL_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Attribute, ast.Name))
    }
    assert "private_bytes" not in source
    assert "from_private_bytes" not in source
    assert "mine_block" not in calls
    assert "0.0.0.0" not in source
    assert "validate_transaction" in calls
    assert "add_transaction" in calls
    assert "assess_option_a" in calls


def test_protected_economics_and_history_constants_are_unchanged():
    assert L28_MAX_SUPPLY == 28_000_000
    assert L28_EMISSION_CEILING == 11_130_000
    assert L28_HISTORICAL_MINED == 2_824_584
    assert L28_HISTORICAL_LAST_ENTRY == 100_877
    assert L28_NEXT_HEIGHT_AFTER_CHECKPOINT == 100_878
