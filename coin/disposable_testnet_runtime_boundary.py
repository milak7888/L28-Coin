# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Protocol

from .disposable_testnet_m2 import (
    DisposableLocalTipAuthority,
    DisposableM2Error,
    build_m2_offline_bundle,
)


PROFILE = "l28-disposable-runtime-boundary/v0.1"
GENESIS_ARTIFACT_PROFILE = "l28-disposable-runtime-genesis-artifact/v0.1"

RUNTIME_AUTHORIZED = False
PROCESS_START_AUTHORIZED = False
PROCESS_CONTROL_AUTHORIZED = False
FILESYSTEM_MUTATION_AUTHORIZED = False
NETWORK_AUTHORIZED = False
SOCKET_AUTHORIZED = False
RPC_AUTHORIZED = False
P2P_AUTHORIZED = False
WALLET_CREATION_AUTHORIZED = False
KEY_GENERATION_AUTHORIZED = False
SIGNING_AUTHORIZED = False
MINING_AUTHORIZED = False
BROADCAST_AUTHORIZED = False
TESTNET_START_AUTHORIZED = False
SETTLEMENT_AUTHORIZED = False


class DisposableRuntimeBoundaryError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class DisposableRuntimeBinding:
    profile: str
    network_id: str
    genesis_hash: str
    config_hash: str
    data_dir_tag: str
    lifecycle_state: str
    tip_height: int
    issued_supply: int
    runtime_authorized: bool = False
    process_start_authorized: bool = False
    filesystem_mutation_authorized: bool = False
    network_authorized: bool = False
    socket_authorized: bool = False
    signing_authorized: bool = False
    mining_authorized: bool = False
    broadcast_authorized: bool = False
    settlement_authorized: bool = False


@dataclass(frozen=True)
class DisposableGenesisArtifact:
    profile: str
    network_id: str
    genesis_hash: str
    config_hash: str
    payload: bytes
    payload_sha256: str
    bytes_only: bool = True
    file_written: bool = False
    runtime_authorized: bool = False


class DisposableProcessHooks(Protocol):
    def start(self, binding: DisposableRuntimeBinding) -> None:
        ...

    def stop(self, binding: DisposableRuntimeBinding) -> None:
        ...


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise DisposableRuntimeBoundaryError(
            "artifact_encoding_invalid"
        ) from exc


def prepare_runtime_boundary(
    config: Any,
    *,
    acknowledge_test_only: bool,
) -> tuple[DisposableRuntimeBinding, DisposableLocalTipAuthority]:
    try:
        bundle = build_m2_offline_bundle(
            config,
            acknowledge_test_only=acknowledge_test_only,
        )
    except DisposableM2Error as exc:
        raise DisposableRuntimeBoundaryError(
            "m2_preparation_invalid:" + exc.code
        ) from exc

    for field in (
        "runtime_authorized",
        "process_start_authorized",
        "network_authorized",
        "socket_authorized",
        "signing_authorized",
        "mining_authorized",
        "broadcast_authorized",
        "settlement_authorized",
    ):
        if bundle[field] is not False:
            raise DisposableRuntimeBoundaryError(
                "m2_authority_boundary_invalid"
            )

    preparation = bundle["preparation"]
    tip = bundle["tip_authority"]

    if preparation.lifecycle_state != "DISPOSABLE_TEST_READY":
        raise DisposableRuntimeBoundaryError(
            "core_lifecycle_not_ready"
        )

    if preparation.issuance_acknowledged is not True:
        raise DisposableRuntimeBoundaryError(
            "issuance_acknowledgement_missing"
        )

    try:
        tip_height = tip.read_height()
    except DisposableM2Error as exc:
        raise DisposableRuntimeBoundaryError(
            "tip_unavailable"
        ) from exc

    if type(tip_height) is not int or tip_height != 0:
        raise DisposableRuntimeBoundaryError(
            "initial_tip_invalid"
        )

    if (
        type(preparation.initial_issued_supply) is not int
        or preparation.initial_issued_supply != 0
    ):
        raise DisposableRuntimeBoundaryError(
            "initial_supply_invalid"
        )

    binding = DisposableRuntimeBinding(
        profile=PROFILE,
        network_id=preparation.network_id,
        genesis_hash=preparation.genesis_hash,
        config_hash=preparation.config_hash,
        data_dir_tag=preparation.data_dir_tag,
        lifecycle_state=preparation.lifecycle_state,
        tip_height=tip_height,
        issued_supply=preparation.initial_issued_supply,
    )

    return binding, tip


def validate_runtime_binding(
    binding: DisposableRuntimeBinding,
    tip: DisposableLocalTipAuthority,
) -> bool:
    if not isinstance(binding, DisposableRuntimeBinding):
        raise DisposableRuntimeBoundaryError(
            "runtime_binding_required"
        )

    if not isinstance(tip, DisposableLocalTipAuthority):
        raise DisposableRuntimeBoundaryError(
            "tip_authority_required"
        )

    if binding.profile != PROFILE:
        raise DisposableRuntimeBoundaryError(
            "runtime_profile_invalid"
        )

    if binding.lifecycle_state != "DISPOSABLE_TEST_READY":
        raise DisposableRuntimeBoundaryError(
            "core_lifecycle_not_ready"
        )

    if (
        binding.network_id != tip.network_id
        or binding.genesis_hash != tip.genesis_hash
        or binding.config_hash != tip.config_hash
    ):
        raise DisposableRuntimeBoundaryError(
            "runtime_binding_identity_mismatch"
        )

    try:
        current_height = tip.read_height()
    except DisposableM2Error as exc:
        raise DisposableRuntimeBoundaryError(
            "tip_unavailable"
        ) from exc

    if current_height != binding.tip_height:
        raise DisposableRuntimeBoundaryError(
            "stale_tip_binding"
        )

    for value in (
        binding.runtime_authorized,
        binding.process_start_authorized,
        binding.filesystem_mutation_authorized,
        binding.network_authorized,
        binding.socket_authorized,
        binding.signing_authorized,
        binding.mining_authorized,
        binding.broadcast_authorized,
        binding.settlement_authorized,
    ):
        if value is not False:
            raise DisposableRuntimeBoundaryError(
                "activation_authority_invalid"
            )

    return True


def materialize_genesis_artifact_bytes(
    binding: DisposableRuntimeBinding,
    tip: DisposableLocalTipAuthority,
) -> DisposableGenesisArtifact:
    validate_runtime_binding(binding, tip)

    material = {
        "profile": GENESIS_ARTIFACT_PROFILE,
        "network_id": binding.network_id,
        "genesis_hash": binding.genesis_hash,
        "config_hash": binding.config_hash,
        "data_dir_tag": binding.data_dir_tag,
        "lifecycle_state": binding.lifecycle_state,
        "initial_tip_height": binding.tip_height,
        "initial_issued_supply": binding.issued_supply,
        "historical_checkpoint_imported": False,
        "historical_balances_loaded": False,
        "runtime_authorized": False,
        "process_start_authorized": False,
        "filesystem_mutation_authorized": False,
        "network_authorized": False,
        "socket_authorized": False,
        "wallet_creation_authorized": False,
        "key_generation_authorized": False,
        "signing_authorized": False,
        "mining_authorized": False,
        "broadcast_authorized": False,
        "testnet_start_authorized": False,
        "settlement_authorized": False,
    }

    payload = _canonical_bytes(material)
    digest = hashlib.sha256(
        b"L28-DISPOSABLE-RUNTIME-GENESIS-V0.1"
        + bytes([0])
        + payload
    ).hexdigest()

    return DisposableGenesisArtifact(
        profile=GENESIS_ARTIFACT_PROFILE,
        network_id=binding.network_id,
        genesis_hash=binding.genesis_hash,
        config_hash=binding.config_hash,
        payload=payload,
        payload_sha256=digest,
    )


def describe_process_hook_boundary() -> dict[str, Any]:
    return {
        "profile": "l28-disposable-process-hook-interface/v0.1",
        "interface_only": True,
        "start_hook_defined": True,
        "stop_hook_defined": True,
        "hook_invocation_authorized": False,
        "process_control_authorized": False,
        "runtime_authorized": False,
        "network_authorized": False,
    }
