# SPDX-License-Identifier: Apache-2.0
"""Exercise the disposable consensus vectors and the disagreement gate."""

import asyncio
from copy import deepcopy
import hashlib
import json
import subprocess
import sys

import pytest

from coin import offline_consensus_validator_a as validator_a
from coin import offline_consensus_validator_b as validator_b
from coin import offline_consensus_vectors as vectors


@pytest.fixture
def raw_fixture():
    return vectors.FIXTURE_PATH.read_bytes()


@pytest.mark.parametrize("validator,reverse,order", [
    (validator_a, False, ("fast", "slow")),
    (validator_b, True, ("slow", "fast")),
])
def test_validator_matches_independent_fixture_expectations(
    tmp_path, raw_fixture, validator, reverse, order,
):
    fixture = vectors.parse_fixture(raw_fixture)
    observed_orders = []

    def select(histories):
        observed_orders.append(tuple(histories))
        return validator.select(histories)

    results = asyncio.run(vectors.evaluate(
        fixture, tmp_path, reverse, validator.verify_header, select,
    ))
    vectors.check_expectations(results, fixture["expected"])
    assert observed_orders.count(order) == 2
    forks = results["competing"]
    assert forks["branch_work"] == {"fast": 96, "slow": 48}
    assert forks["tip"] == forks["branches"]["fast"][-1]["id"]
    assert [item["target"] for item in forks["branches"]["fast"]] == [
        2**252 - 1, 2**252 - 1, 2**250 - 1,
    ]
    assert [item["target"] for item in forks["branches"]["slow"]] == [
        2**252 - 1, 2**252 - 1, 2**254 - 4, 2**254 - 4, 2**253 - 2,
    ]
    assert forks["selected_state"]["height"] == 3
    assert forks["selected_state"]["issued_supply"] == 84
    assert forks["selected_state"]["balances"] == {"fixture-fast": 84}
    assert results["equal_work"]["tip"] is None
    assert results["equal_work"]["status"] == "pending_equal_work"
    assert results["replayed"]["branches"]["only"][-1]["result"] == "replay"
    ledger = tmp_path / "replayed" / "only" / "shard_0.jsonl"
    assert ledger.read_bytes().count(b"\n") == 1
    assert hashlib.sha256(ledger.read_bytes()).hexdigest() == (
        results["replayed"]["selected_state"]["ledger_sha256"]
    )
    for case_name in ("missing_state", "insufficient", "wrong_reward", "wrong_state"):
        assert not (tmp_path / case_name / "only" / "shard_0.jsonl").exists()


def test_fixture_bytes_are_pinned(raw_fixture):
    assert hashlib.sha256(raw_fixture).hexdigest() == vectors.FIXTURE_SHA256
    with pytest.raises(vectors.Rejected, match="fixture_digest_mismatch"):
        vectors.parse_fixture(raw_fixture + b" ")
    with pytest.raises(vectors.Rejected, match="fixture_digest_mismatch"):
        vectors.parse_fixture(b" " * (vectors.MAX_FIXTURE_BYTES + 1))


@pytest.mark.parametrize("validator", [validator_a, validator_b])
def test_context_and_work_header_encoding(raw_fixture, validator):
    fixture = vectors.parse_fixture(raw_fixture)
    checkpoint = deepcopy(fixture["checkpoint"])
    checkpoint["id"] = vectors.digest(checkpoint)
    block = fixture["blocks"]["fast1"]
    header = dict(reversed(tuple(block["header"].items())))
    # Literal serialization options keep this hash check outside either validator.
    payload = json.dumps(
        header, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    assert validator.verify_header(header, [], checkpoint) == hashlib.sha256(payload).hexdigest()
    header["checkpoint"] = "0" * 64
    with pytest.raises(vectors.Rejected, match="wrong_context"):
        validator.verify_header(header, [], checkpoint)


def test_cli_halts_on_injected_disagreement(tmp_path):
    target = tmp_path / "halted"
    process = subprocess.run(
        [sys.executable, "-B", "-m", "coin.offline_consensus_vectors",
         "--acknowledge-test-only", "--work-dir", str(target), "--inject-disagreement"],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert process.returncode == 1
    assert "validator_disagreement" in process.stderr
    assert process.stdout == ""
    assert not (target / "result.json").exists()
    assert (target / "a").is_dir() and (target / "b").is_dir()


def test_cli_refuses_existing_store_and_active_production(tmp_path, monkeypatch, capsys):
    existing = tmp_path / "existing"
    existing.mkdir()
    keep = existing / "keep"
    keep.write_text("preserve")
    with pytest.raises(SystemExit) as error:
        vectors.main(["--acknowledge-test-only", "--work-dir", str(existing)])
    assert error.value.code == 1
    assert list(existing.iterdir()) == [keep]
    assert keep.read_text() == "preserve"
    monkeypatch.setattr(vectors.identity, "MINING_AUTHORIZED", True)
    fresh = tmp_path / "fresh"
    with pytest.raises(SystemExit) as error:
        vectors.main(["--acknowledge-test-only", "--work-dir", str(fresh)])
    assert error.value.code == 1
    assert "production_authority_active" in capsys.readouterr().err
    assert not fresh.exists()
