# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .disposable_testnet_identity import (
    DisposableTestnetConfigError,
    validate_and_bind_disposable_testnet_config,
)
from .node_role_model import CoreNodeRoleModel


M2_PROFILE = "l28-disposable-testnet-m2-offline/v0.1"

RUNTIME_AUTHORIZED = False
PROCESS_START_AUTHORIZED = False
NETWORK_AUTHORIZED = False
SOCKET_AUTHORIZED = False
WALLET_CREATION_AUTHORIZED = False
KEY_GENERATION_AUTHORIZED = False
SIGNING_AUTHORIZED = False
MINING_AUTHORIZED = False
BROADCAST_AUTHORIZED = False
SETTLEMENT_AUTHORIZED = False
FILESYSTEM_MUTATION_AUTHORIZED = False


class DisposableM2Error(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _exact_int(value: Any, code: str) -> int:
    if type(value) is not int:
        raise DisposableM2Error(code)
    return value


@dataclass(frozen=True)
class DisposableCorePreparation:
    profile: str
    network_id: str
    genesis_hash: str
    config_hash: str
    data_dir_tag: str
    lifecycle_state: str
    issuance_acknowledged: bool
    initial_tip_height: int
    initial_issued_supply: int
    runtime_authorized: bool = False
    process_start_authorized: bool = False
    network_authorized: bool = False
    signing_authorized: bool = False
    mining_authorized: bool = False
    settlement_authorized: bool = False


@dataclass(frozen=True)
class DisposableLocalTipAuthority:
    network_id: str
    genesis_hash: str
    config_hash: str
    height: int = 0
    available: bool = True
    network_consensus_authority: bool = False
    main_network_authority: bool = False

    def read_height(self) -> int:
        if self.available is not True:
            raise DisposableM2Error("tip_unavailable")
        return self.height

    def propose_advance(
        self,
        *,
        expected_current_height: Any,
        next_height: Any,
    ) -> "DisposableLocalTipAuthority":
        if self.available is not True:
            raise DisposableM2Error("tip_unavailable")

        expected = _exact_int(
            expected_current_height,
            "expected_height_invalid",
        )
        candidate = _exact_int(
            next_height,
            "next_height_invalid",
        )

        if expected != self.height:
            raise DisposableM2Error("tip_height_mismatch")

        if candidate != self.height + 1:
            raise DisposableM2Error("tip_advance_invalid")

        return replace(self, height=candidate)


@dataclass(frozen=True)
class DisposableWalletIsolationContract:
    network_id: str
    config_hash: str
    ephemeral_keys_required: bool = True
    key_generation_authorized: bool = False
    persistent_key_storage_authorized: bool = False
    production_key_loading_authorized: bool = False
    creator_private_material_authorized: bool = False
    external_wallet_paths_authorized: bool = False
    signing_authorized: bool = False


@dataclass(frozen=True)
class DisposableDataDirContract:
    network_id: str
    config_hash: str
    data_dir_tag: str
    disposable_only: bool = True
    filesystem_access_authorized: bool = False
    create_authorized: bool = False
    reset_authorized: bool = False
    cleanup_authorized: bool = False
    persistence_authorized: bool = False


def prepare_disposable_core(
    config: Any,
    *,
    acknowledge_test_only: bool,
) -> DisposableCorePreparation:
    if acknowledge_test_only is not True:
        raise DisposableM2Error(
            "issuance_acknowledgement_required"
        )

    try:
        binding = validate_and_bind_disposable_testnet_config(config)
    except DisposableTestnetConfigError as exc:
        raise DisposableM2Error(
            "m1_binding_invalid:" + exc.code
        ) from exc

    for field in (
        "runtime_authorized",
        "network_authorized",
        "testnet_start_authorized",
        "signing_authorized",
        "mining_authorized",
        "broadcast_authorized",
        "settlement_authorized",
    ):
        if binding[field] is not False:
            raise DisposableM2Error(
                "m1_authority_boundary_invalid"
            )

    core = CoreNodeRoleModel()
    prepared, result = core.transition(
        "DISPOSABLE_TEST_READY"
    )

    if not result.ok:
        raise DisposableM2Error(
            "core_preparation_transition_failed"
        )

    return DisposableCorePreparation(
        profile=M2_PROFILE,
        network_id=binding["network_id"],
        genesis_hash=binding["genesis_hash"],
        config_hash=binding["config_hash"],
        data_dir_tag=binding["data_dir_tag"],
        lifecycle_state=prepared.state,
        issuance_acknowledged=True,
        initial_tip_height=0,
        initial_issued_supply=0,
    )


def build_local_tip_authority(
    preparation: DisposableCorePreparation,
) -> DisposableLocalTipAuthority:
    if not isinstance(
        preparation,
        DisposableCorePreparation,
    ):
        raise DisposableM2Error(
            "core_preparation_required"
        )

    if preparation.lifecycle_state != "DISPOSABLE_TEST_READY":
        raise DisposableM2Error(
            "core_not_disposable_ready"
        )

    if preparation.issuance_acknowledged is not True:
        raise DisposableM2Error(
            "issuance_acknowledgement_required"
        )

    return DisposableLocalTipAuthority(
        network_id=preparation.network_id,
        genesis_hash=preparation.genesis_hash,
        config_hash=preparation.config_hash,
        height=preparation.initial_tip_height,
    )


def mark_tip_unavailable(
    authority: DisposableLocalTipAuthority,
) -> DisposableLocalTipAuthority:
    if not isinstance(authority, DisposableLocalTipAuthority):
        raise DisposableM2Error("tip_authority_required")
    return replace(authority, available=False)


def build_wallet_isolation_contract(
    preparation: DisposableCorePreparation,
) -> DisposableWalletIsolationContract:
    return DisposableWalletIsolationContract(
        network_id=preparation.network_id,
        config_hash=preparation.config_hash,
    )


def build_data_dir_contract(
    preparation: DisposableCorePreparation,
) -> DisposableDataDirContract:
    return DisposableDataDirContract(
        network_id=preparation.network_id,
        config_hash=preparation.config_hash,
        data_dir_tag=preparation.data_dir_tag,
    )


def plan_disposable_state_action(
    preparation: DisposableCorePreparation,
    action: Any,
) -> dict[str, Any]:
    if action not in {"stop", "reset", "cleanup"}:
        raise DisposableM2Error("state_action_invalid")

    return {
        "profile": "l28-disposable-state-action-plan/v0.1",
        "action": action,
        "network_id": preparation.network_id,
        "config_hash": preparation.config_hash,
        "data_dir_tag": preparation.data_dir_tag,
        "plan_only": True,
        "execution_authorized": False,
        "filesystem_mutation_authorized": False,
        "process_control_authorized": False,
        "network_authorized": False,
    }


def build_m2_offline_bundle(
    config: Any,
    *,
    acknowledge_test_only: bool,
) -> dict[str, Any]:
    preparation = prepare_disposable_core(
        config,
        acknowledge_test_only=acknowledge_test_only,
    )

    tip = build_local_tip_authority(preparation)
    wallet = build_wallet_isolation_contract(preparation)
    data_dir = build_data_dir_contract(preparation)

    return {
        "profile": M2_PROFILE,
        "preparation": preparation,
        "tip_authority": tip,
        "wallet_contract": wallet,
        "data_dir_contract": data_dir,
        "runtime_authorized": False,
        "process_start_authorized": False,
        "network_authorized": False,
        "socket_authorized": False,
        "signing_authorized": False,
        "mining_authorized": False,
        "broadcast_authorized": False,
        "settlement_authorized": False,
    }
