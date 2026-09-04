# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

PROFILE = "l28-disposable-testnet-m1-binding/v0.1"
GENESIS_PROFILE = "l28-disposable-genesis/v0.1"
PROTOCOL_VERSION = "1.0.0"
NETWORK_SCOPE = "DISPOSABLE_TEST_ONLY"

RUNTIME_AUTHORIZED = False
NETWORK_AUTHORIZED = False
TESTNET_START_AUTHORIZED = False
SIGNING_AUTHORIZED = False
MINING_AUTHORIZED = False
BROADCAST_AUTHORIZED = False
SETTLEMENT_AUTHORIZED = False

RESERVED_NETWORK_IDS = frozenset({"MAIN", "MAINNET", "L28-MAIN"})
NETWORK_ID_RE = re.compile(r"^L28-DISPOSABLE-[A-Z0-9][A-Z0-9_-]{2,63}$")
DATA_DIR_TAG_RE = re.compile(
    r"^l28-disposable-testnet:[a-z0-9][a-z0-9_-]{2,63}$"
)

PROTECTED_ECONOMIC_FACTS = {
    "hard_cap": 28_000_000,
    "emission_ceiling": 11_130_000,
    "historically_mined": 2_824_584,
    "treasury_locked": 500_000,
    "circulating_snapshot": 2_324_584,
    "halving_interval": 210_000,
    "reward_sequence": [28, 14, 7, 3, 1, 0],
    "historical_mined_through_entry": 100_877,
    "next_canonical_height": 100_878,
}

CONFIG_FIELDS = frozenset({
    "profile",
    "protocol_version",
    "network_scope",
    "network_id",
    "data_dir_tag",
    "genesis",
    "key_policy",
    "acknowledge_disposable_test_only",
})

GENESIS_FIELDS = frozenset({
    "profile",
    "network_id",
    "initial_height",
    "initial_issued_supply",
    "historical_checkpoint_imported",
    "historical_balances_loaded",
    "protected_economic_facts",
})

KEY_POLICY_FIELDS = frozenset({
    "allow_production_keys",
    "allow_creator_private_material",
    "allow_external_wallet_paths",
})


class DisposableTestnetConfigError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _exact(value: Any, fields: frozenset[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value.keys()) != fields:
        raise DisposableTestnetConfigError("schema_invalid")
    return value


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise DisposableTestnetConfigError("schema_invalid") from exc


def _digest(domain: bytes, value: Any) -> str:
    return hashlib.sha256(domain + b":" + _canonical(value)).hexdigest()


def _network_id(value: Any) -> str:
    if not isinstance(value, str):
        raise DisposableTestnetConfigError("network_id_invalid")
    if value in RESERVED_NETWORK_IDS:
        raise DisposableTestnetConfigError("main_identity_forbidden")
    if NETWORK_ID_RE.fullmatch(value) is None:
        raise DisposableTestnetConfigError("network_id_invalid")
    return value


def _data_dir_tag(value: Any) -> str:
    if not isinstance(value, str):
        raise DisposableTestnetConfigError("data_dir_tag_invalid")
    if DATA_DIR_TAG_RE.fullmatch(value) is None:
        raise DisposableTestnetConfigError("data_dir_tag_invalid")
    return value


def _key_policy(value: Any) -> None:
    policy = _exact(value, KEY_POLICY_FIELDS)
    for field in KEY_POLICY_FIELDS:
        if policy[field] is not False:
            raise DisposableTestnetConfigError(
                "production_key_reference_forbidden"
            )


def _genesis(value: Any, network_id: str) -> Mapping[str, Any]:
    genesis = _exact(value, GENESIS_FIELDS)

    if genesis["profile"] != GENESIS_PROFILE:
        raise DisposableTestnetConfigError("genesis_profile_invalid")

    if genesis["network_id"] != network_id:
        raise DisposableTestnetConfigError("network_binding_mismatch")

    if (
        type(genesis["initial_height"]) is not int
        or genesis["initial_height"] != 0
    ):
        raise DisposableTestnetConfigError("genesis_height_invalid")

    if (
        type(genesis["initial_issued_supply"]) is not int
        or genesis["initial_issued_supply"] != 0
    ):
        raise DisposableTestnetConfigError(
            "historical_supply_reuse_forbidden"
        )

    if genesis["historical_checkpoint_imported"] is not False:
        raise DisposableTestnetConfigError(
            "historical_checkpoint_import_forbidden"
        )

    if genesis["historical_balances_loaded"] is not False:
        raise DisposableTestnetConfigError(
            "historical_balances_forbidden"
        )

    if (
        _canonical(genesis["protected_economic_facts"])
        != _canonical(PROTECTED_ECONOMIC_FACTS)
    ):
        raise DisposableTestnetConfigError("economic_facts_mismatch")

    return genesis


def validate_and_bind_disposable_testnet_config(
    config: Any,
) -> dict[str, Any]:
    cfg = _exact(config, CONFIG_FIELDS)

    if cfg["profile"] != PROFILE:
        raise DisposableTestnetConfigError("profile_invalid")

    if cfg["protocol_version"] != PROTOCOL_VERSION:
        raise DisposableTestnetConfigError(
            "protocol_version_mismatch"
        )

    if cfg["network_scope"] != NETWORK_SCOPE:
        raise DisposableTestnetConfigError(
            "network_scope_invalid"
        )

    if cfg["acknowledge_disposable_test_only"] is not True:
        raise DisposableTestnetConfigError(
            "test_only_acknowledgement_required"
        )

    network_id = _network_id(cfg["network_id"])
    data_dir_tag = _data_dir_tag(cfg["data_dir_tag"])
    _key_policy(cfg["key_policy"])
    genesis = _genesis(cfg["genesis"], network_id)

    genesis_material = {
        "profile": GENESIS_PROFILE,
        "protocol_version": PROTOCOL_VERSION,
        "network_scope": NETWORK_SCOPE,
        "network_id": network_id,
        "initial_height": genesis["initial_height"],
        "initial_issued_supply": genesis["initial_issued_supply"],
        "historical_checkpoint_imported": False,
        "historical_balances_loaded": False,
        "protected_economic_facts": PROTECTED_ECONOMIC_FACTS,
    }

    genesis_hash = _digest(
        b"L28-DISPOSABLE-GENESIS-V0.1",
        genesis_material,
    )

    binding_material = {
        "profile": PROFILE,
        "protocol_version": PROTOCOL_VERSION,
        "network_scope": NETWORK_SCOPE,
        "network_id": network_id,
        "data_dir_tag": data_dir_tag,
        "genesis_hash": genesis_hash,
    }

    config_hash = _digest(
        b"L28-DISPOSABLE-CONFIG-V0.1",
        binding_material,
    )

    return {
        "ok": True,
        "binding_profile": PROFILE,
        "protocol_version": PROTOCOL_VERSION,
        "network_scope": NETWORK_SCOPE,
        "network_id": network_id,
        "data_dir_tag": data_dir_tag,
        "genesis_hash": genesis_hash,
        "config_hash": config_hash,
        "runtime_authorized": False,
        "network_authorized": False,
        "testnet_start_authorized": False,
        "signing_authorized": False,
        "mining_authorized": False,
        "broadcast_authorized": False,
        "settlement_authorized": False,
    }
