# SPDX-License-Identifier: Apache-2.0
"""Isolated disposable signer tests."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import coin.isolated_nonproduction_signer as signer
from coin.disposable_testnet_identity import (
    BROADCAST_AUTHORIZED,
    MINING_AUTHORIZED,
    NETWORK_AUTHORIZED,
    RUNTIME_AUTHORIZED,
    SETTLEMENT_AUTHORIZED,
    SIGNING_AUTHORIZED,
    TESTNET_START_AUTHORIZED,
)


def test_production_flags_stay_closed_and_signer_refuses_bad_requests() -> None:
    signer.assert_production_flags_closed()
    assert all(
        flag is False
        for flag in (
            RUNTIME_AUTHORIZED,
            NETWORK_AUTHORIZED,
            TESTNET_START_AUTHORIZED,
            SIGNING_AUTHORIZED,
            MINING_AUTHORIZED,
            BROADCAST_AUTHORIZED,
            SETTLEMENT_AUTHORIZED,
        )
    )
    disposable = signer.DisposableSigner()
    try:
        hello = disposable.hello()
        assert hello["production_signing"] is False
        assert hello["SIGNER_RUNTIME_ACTIVE"] is False
        assert hello["key_persisted"] is False
        with pytest.raises(signer.IsolatedSignerError) as purpose:
            disposable.sign_payload({"purpose": "arbitrary_bytes", "payload": "aa"})
        assert purpose.value.code == "purpose_rejected"
        with pytest.raises(signer.IsolatedSignerError) as amount:
            disposable.sign_payload(
                {
                    "purpose": "transfer",
                    "receiver": "l28disp_test",
                    "amount": 27,
                    "timestamp": 1,
                    "nonce": 1,
                }
            )
        assert amount.value.code == "wrong_amount"
    finally:
        disposable.close()
        with pytest.raises(signer.IsolatedSignerError) as closed:
            disposable.sign_payload({"purpose": "service_quote", "request": {}})
        assert closed.value.code == "signer_closed"


def test_real_processes_sign_outside_the_provider(tmp_path: Path) -> None:
    result = signer.execute_isolated_signer_purchase(tmp_path, "L28 enables machine payments between autonomous systems.")
    assert result["isolated_nonproduction_signer"] is True
    assert result["same_signer_identity_after_provider_restart"] is True
    assert result["key_persisted"] is False
    assert result["SIGNER_RUNTIME_ACTIVE"] is False
    assert result["production_signing"] is False
    assert result["F171_SIGNER_ELIGIBILITY_RESULT"] == "BLOCKED"
    run1 = result["run1"]
    replay = result["run2_replay"]
    run3 = result["run3"]
    assert run1["canonical_validation"] == "PASS"
    assert (run1["requester_balance_before"], run1["provider_balance_before"]) == (100, 0)
    assert (run1["requester_balance_after"], run1["provider_balance_after"]) == (72, 28)
    assert replay["replay_rejected"] is True
    assert replay["service_executed"] is False
    assert (replay["requester_balance_after"], replay["provider_balance_after"]) == (72, 28)
    assert run3["receiver"] == run1["receiver"]
    assert (run3["requester_balance_before"], run3["requester_balance_after"]) == (72, 44)
    assert (run3["provider_balance_before"], run3["provider_balance_after"]) == (28, 56)
    assert run3["result_verified"] is True
    assert run3["receipt_verified"] is True


def test_signer_source_has_no_secret_or_production_activation() -> None:
    source = Path(signer.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert "private_bytes" not in names and "private_bytes" not in attributes
    assert "from_private_bytes" not in names and "from_private_bytes" not in attributes
    assert "environ" not in names and "environ" not in attributes
    assert "0.0.0.0" not in source
    assert "SIGNER_RUNTIME_ACTIVE = True" not in source
    assert "SIGNING_AUTHORIZED = True" not in source
