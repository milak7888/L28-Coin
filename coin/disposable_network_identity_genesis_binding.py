# SPDX-License-Identifier: Apache-2.0
"""Offline disposable network identity and genesis-binding verifier (Foundation 39 / M1).

Implements Foundation 38 identity, genesis, and binding-config verification only.
Does not start nodes, open sockets, mine, load wallets, mutate ledgers, import
historical state, or activate a testnet.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from .tx_validation import (
    L28_EMISSION_CEILING,
    L28_HALVING_INTERVAL,
    L28_MAX_COINBASE_REWARD,
    L28_MAX_SUPPLY,
    L28_REWARD_SCHEDULE,
)

PROFILE = "l28-disposable-network-identity-genesis-binding/v0.1"
VERIFIER_PROFILE = "l28-disposable-network-identity-genesis-binding-verifier/v0.1"
REPORT_PROFILE = "l28-disposable-network-identity-genesis-binding-report/v0.1"
NETWORK_ID = "l28-disposable-test/v0.1"
PROTOCOL_VERSION = "l28-protocol/1.0.0"
ENVIRONMENT = "DISPOSABLE_TEST"
ACKNOWLEDGEMENT = "disposable-test-only"
DATA_DIR_TAG = "l28-disposable-test"
FORBIDDEN_ENVIRONMENT_LABELS = frozenset(
    {"MAIN", "CANONICAL", "HISTORICAL", "PRODUCTION", "main"}
)

PROFILE_DOMAIN = (PROFILE + "\x00").encode("utf-8")
REPORT_DOMAIN = (REPORT_PROFILE + "\x00").encode("utf-8")

MAX_GENESIS_BYTES = 8192
MAX_BINDING_BYTES = 8192

GENESIS_FIELDS = (
    "genesis_version",
    "environment",
    "network_id",
    "chain_id",
    "protocol_version",
    "economics",
    "historical_state_imported",
    "canonical_continuation",
    "initial_issued_supply",
    "initial_height",
    "execution_authorized",
    "acknowledgement",
)

ECONOMICS_FIELDS = (
    "hard_cap",
    "emission_ceiling",
    "halving_interval",
    "max_coinbase_reward",
    "reward_schedule",
)

BINDING_FIELDS = (
    "binding_version",
    "environment",
    "network_id",
    "chain_id",
    "protocol_version",
    "genesis_digest",
    "data_dir_tag",
    "execution_authorized",
)

SUCCESS_CHECKS = (
    "schema_exact",
    "environment_disposable",
    "network_id_bound",
    "protocol_version_bound",
    "economics_v1_immutable",
    "historical_separated",
    "chain_id_bound",
    "genesis_digest_bound",
    "execution_authorized_false",
)

STABLE_CODES = (
    "ok",
    "input_type_invalid",
    "input_too_large",
    "encoding_invalid",
    "json_invalid",
    "duplicate_key",
    "invalid_top_level",
    "schema_invalid",
    "environment_invalid",
    "network_id_invalid",
    "protocol_version_invalid",
    "economics_invalid",
    "historical_import_forbidden",
    "chain_id_invalid",
    "genesis_digest_invalid",
    "acknowledgement_invalid",
    "execution_authorized_invalid",
    "binding_mismatch",
    "internal_error",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class _DuplicateKey(ValueError):
    pass


class _BindingError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class DisposableGenesisResult:
    ok: bool
    code: str
    network_id: str = ""
    chain_id: str = ""
    genesis_digest: str = ""
    protocol_version: str = ""
    checks: tuple[str, ...] = ()
    execution_authorized: bool = False
    report_id: str = ""


@dataclass(frozen=True)
class DisposableBindingResult:
    ok: bool
    code: str
    network_id: str = ""
    chain_id: str = ""
    genesis_digest: str = ""
    protocol_version: str = ""
    checks: tuple[str, ...] = ()
    execution_authorized: bool = False
    report_id: str = ""


@dataclass(frozen=True)
class DisposableIdentityBindingResult:
    """Future handshake / ledger-replay identity-tuple surface (M1 validation only)."""

    ok: bool
    code: str
    network_id: str = ""
    chain_id: str = ""
    genesis_digest: str = ""
    protocol_version: str = ""
    execution_authorized: bool = False
    report_id: str = ""


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise _BindingError("json_invalid")


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise _BindingError("schema_invalid") from exc


def _decode(payload: str | bytes, *, max_bytes: int) -> str:
    if isinstance(payload, bytes):
        if len(payload) > max_bytes:
            raise _BindingError("input_too_large")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _BindingError("encoding_invalid") from exc
    if isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _BindingError("encoding_invalid") from exc
        if len(encoded) > max_bytes:
            raise _BindingError("input_too_large")
        return payload
    raise _BindingError("input_type_invalid")


def _parse(payload: str | bytes, *, max_bytes: int) -> dict[str, Any]:
    try:
        value = json.loads(
            _decode(payload, max_bytes=max_bytes),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise _BindingError("duplicate_key") from exc
    except _BindingError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _BindingError("json_invalid") from exc
    if not isinstance(value, dict):
        raise _BindingError("invalid_top_level")
    return value


def _require_exact_int(value: Any, expected: int) -> None:
    if isinstance(value, bool) or type(value) is not int or value != expected:
        raise _BindingError("economics_invalid")


def _require_false(value: Any, *, code: str) -> None:
    if value is not False:
        raise _BindingError(code)


def _require_hex64(value: Any, *, code: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise _BindingError(code)
    return value


def compute_disposable_chain_id(
    *, network_id: str, protocol_version: str
) -> str:
    if not isinstance(network_id, str) or not isinstance(protocol_version, str):
        raise TypeError("network_id and protocol_version must be str")
    material = (
        PROFILE_DOMAIN
        + network_id.encode("utf-8")
        + b"\x00"
        + protocol_version.encode("utf-8")
    )
    return hashlib.sha256(material).hexdigest()


def compute_disposable_genesis_digest(genesis_object: Mapping[str, Any]) -> str:
    if not isinstance(genesis_object, Mapping):
        raise TypeError("genesis_object must be a mapping")
    return hashlib.sha256(
        PROFILE_DOMAIN + _canonical_bytes(dict(genesis_object))
    ).hexdigest()


def _report_id(body: Mapping[str, Any]) -> str:
    return hashlib.sha256(REPORT_DOMAIN + _canonical_bytes(dict(body))).hexdigest()


def _failure_genesis(code: str) -> DisposableGenesisResult:
    body = {
        "ok": False,
        "code": code,
        "network_id": "",
        "chain_id": "",
        "genesis_digest": "",
        "protocol_version": "",
        "checks": [],
        "execution_authorized": False,
    }
    return DisposableGenesisResult(
        False,
        code,
        execution_authorized=False,
        report_id=_report_id(body),
    )


def _failure_binding(code: str) -> DisposableBindingResult:
    body = {
        "ok": False,
        "code": code,
        "network_id": "",
        "chain_id": "",
        "genesis_digest": "",
        "protocol_version": "",
        "checks": [],
        "execution_authorized": False,
    }
    return DisposableBindingResult(
        False,
        code,
        execution_authorized=False,
        report_id=_report_id(body),
    )


def _failure_identity(code: str) -> DisposableIdentityBindingResult:
    body = {
        "ok": False,
        "code": code,
        "network_id": "",
        "chain_id": "",
        "genesis_digest": "",
        "protocol_version": "",
        "execution_authorized": False,
    }
    return DisposableIdentityBindingResult(
        False,
        code,
        execution_authorized=False,
        report_id=_report_id(body),
    )


def _validate_economics(economics: Any) -> None:
    if not isinstance(economics, dict) or tuple(economics.keys()) != ECONOMICS_FIELDS:
        raise _BindingError("schema_invalid")
    _require_exact_int(economics["hard_cap"], L28_MAX_SUPPLY)
    _require_exact_int(economics["emission_ceiling"], L28_EMISSION_CEILING)
    _require_exact_int(economics["halving_interval"], L28_HALVING_INTERVAL)
    _require_exact_int(economics["max_coinbase_reward"], L28_MAX_COINBASE_REWARD)
    schedule = economics["reward_schedule"]
    if not isinstance(schedule, list) or len(schedule) != len(L28_REWARD_SCHEDULE):
        raise _BindingError("economics_invalid")
    for index, expected in enumerate(L28_REWARD_SCHEDULE):
        item = schedule[index]
        if isinstance(item, bool) or type(item) is not int or item != expected:
            raise _BindingError("economics_invalid")


def _validate_genesis_object(genesis: dict[str, Any]) -> tuple[str, str]:
    if tuple(genesis.keys()) != GENESIS_FIELDS:
        raise _BindingError("schema_invalid")
    if genesis["genesis_version"] != PROFILE:
        raise _BindingError("schema_invalid")
    if not isinstance(genesis["environment"], str):
        raise _BindingError("schema_invalid")
    if genesis["environment"] != ENVIRONMENT:
        raise _BindingError("environment_invalid")
    if genesis["environment"] in FORBIDDEN_ENVIRONMENT_LABELS:
        raise _BindingError("environment_invalid")

    if not isinstance(genesis["network_id"], str):
        raise _BindingError("schema_invalid")
    if genesis["network_id"] != NETWORK_ID or genesis["network_id"] in {
        "MAIN",
        "main",
        "",
    }:
        raise _BindingError("network_id_invalid")

    if not isinstance(genesis["protocol_version"], str):
        raise _BindingError("schema_invalid")
    if genesis["protocol_version"] != PROTOCOL_VERSION:
        raise _BindingError("protocol_version_invalid")

    _validate_economics(genesis["economics"])

    _require_false(genesis["historical_state_imported"], code="historical_import_forbidden")
    _require_false(genesis["canonical_continuation"], code="historical_import_forbidden")
    if (
        isinstance(genesis["initial_issued_supply"], bool)
        or type(genesis["initial_issued_supply"]) is not int
        or genesis["initial_issued_supply"] != 0
        or isinstance(genesis["initial_height"], bool)
        or type(genesis["initial_height"]) is not int
        or genesis["initial_height"] != 0
    ):
        raise _BindingError("historical_import_forbidden")

    if genesis["execution_authorized"] is not False:
        raise _BindingError("execution_authorized_invalid")

    if not isinstance(genesis["acknowledgement"], str):
        raise _BindingError("schema_invalid")
    if genesis["acknowledgement"] != ACKNOWLEDGEMENT:
        raise _BindingError("acknowledgement_invalid")

    declared_chain_id = _require_hex64(genesis["chain_id"], code="schema_invalid")
    expected_chain_id = compute_disposable_chain_id(
        network_id=NETWORK_ID, protocol_version=PROTOCOL_VERSION
    )
    if declared_chain_id != expected_chain_id:
        raise _BindingError("chain_id_invalid")

    digest = compute_disposable_genesis_digest(genesis)
    return expected_chain_id, digest


def build_disposable_genesis_document() -> dict[str, Any]:
    """Construct the exact canonical disposable genesis object (in-memory only)."""
    chain_id = compute_disposable_chain_id(
        network_id=NETWORK_ID, protocol_version=PROTOCOL_VERSION
    )
    return {
        "genesis_version": PROFILE,
        "environment": ENVIRONMENT,
        "network_id": NETWORK_ID,
        "chain_id": chain_id,
        "protocol_version": PROTOCOL_VERSION,
        "economics": {
            "hard_cap": L28_MAX_SUPPLY,
            "emission_ceiling": L28_EMISSION_CEILING,
            "halving_interval": L28_HALVING_INTERVAL,
            "max_coinbase_reward": L28_MAX_COINBASE_REWARD,
            "reward_schedule": list(L28_REWARD_SCHEDULE),
        },
        "historical_state_imported": False,
        "canonical_continuation": False,
        "initial_issued_supply": 0,
        "initial_height": 0,
        "execution_authorized": False,
        "acknowledgement": ACKNOWLEDGEMENT,
    }


def build_disposable_binding_config(genesis_digest: str) -> dict[str, Any]:
    """Construct the exact binding-config object for a verified genesis digest."""
    if not isinstance(genesis_digest, str) or HEX64_RE.fullmatch(genesis_digest) is None:
        raise ValueError("genesis_digest must be 64 lowercase hex characters")
    return {
        "binding_version": PROFILE,
        "environment": ENVIRONMENT,
        "network_id": NETWORK_ID,
        "chain_id": compute_disposable_chain_id(
            network_id=NETWORK_ID, protocol_version=PROTOCOL_VERSION
        ),
        "protocol_version": PROTOCOL_VERSION,
        "genesis_digest": genesis_digest,
        "data_dir_tag": DATA_DIR_TAG,
        "execution_authorized": False,
    }


def _json_bytes_preserve_order(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")


def verify_disposable_network_genesis_json(
    payload: str | bytes,
) -> DisposableGenesisResult:
    try:
        genesis = _parse(payload, max_bytes=MAX_GENESIS_BYTES)
        chain_id, genesis_digest = _validate_genesis_object(genesis)
        body = {
            "ok": True,
            "code": "ok",
            "network_id": NETWORK_ID,
            "chain_id": chain_id,
            "genesis_digest": genesis_digest,
            "protocol_version": PROTOCOL_VERSION,
            "checks": list(SUCCESS_CHECKS),
            "execution_authorized": False,
        }
        return DisposableGenesisResult(
            True,
            "ok",
            NETWORK_ID,
            chain_id,
            genesis_digest,
            PROTOCOL_VERSION,
            SUCCESS_CHECKS,
            False,
            _report_id(body),
        )
    except _BindingError as exc:
        return _failure_genesis(exc.code)
    except Exception:
        return _failure_genesis("internal_error")


def _validate_binding_object(
    binding: dict[str, Any], *, expected_genesis_digest: str
) -> tuple[str, str]:
    if tuple(binding.keys()) != BINDING_FIELDS:
        raise _BindingError("schema_invalid")
    if binding["binding_version"] != PROFILE:
        raise _BindingError("schema_invalid")
    if not isinstance(binding["environment"], str):
        raise _BindingError("schema_invalid")
    if binding["environment"] != ENVIRONMENT:
        raise _BindingError("environment_invalid")
    if not isinstance(binding["network_id"], str):
        raise _BindingError("schema_invalid")
    if binding["network_id"] != NETWORK_ID:
        raise _BindingError("network_id_invalid")
    if not isinstance(binding["protocol_version"], str):
        raise _BindingError("schema_invalid")
    if binding["protocol_version"] != PROTOCOL_VERSION:
        raise _BindingError("protocol_version_invalid")

    expected_digest = _require_hex64(
        expected_genesis_digest, code="genesis_digest_invalid"
    )
    declared_digest = _require_hex64(binding["genesis_digest"], code="schema_invalid")
    if declared_digest != expected_digest:
        raise _BindingError("genesis_digest_invalid")

    declared_chain_id = _require_hex64(binding["chain_id"], code="schema_invalid")
    expected_chain_id = compute_disposable_chain_id(
        network_id=NETWORK_ID, protocol_version=PROTOCOL_VERSION
    )
    if declared_chain_id != expected_chain_id:
        raise _BindingError("chain_id_invalid")

    if not isinstance(binding["data_dir_tag"], str):
        raise _BindingError("schema_invalid")
    if binding["data_dir_tag"] != DATA_DIR_TAG:
        raise _BindingError("binding_mismatch")

    if binding["execution_authorized"] is not False:
        raise _BindingError("execution_authorized_invalid")

    return expected_chain_id, expected_digest


def verify_disposable_network_binding_config_json(
    payload: str | bytes,
    *,
    expected_genesis_digest: str,
) -> DisposableBindingResult:
    try:
        binding = _parse(payload, max_bytes=MAX_BINDING_BYTES)
        chain_id, genesis_digest = _validate_binding_object(
            binding, expected_genesis_digest=expected_genesis_digest
        )
        body = {
            "ok": True,
            "code": "ok",
            "network_id": NETWORK_ID,
            "chain_id": chain_id,
            "genesis_digest": genesis_digest,
            "protocol_version": PROTOCOL_VERSION,
            "checks": list(SUCCESS_CHECKS),
            "execution_authorized": False,
        }
        return DisposableBindingResult(
            True,
            "ok",
            NETWORK_ID,
            chain_id,
            genesis_digest,
            PROTOCOL_VERSION,
            SUCCESS_CHECKS,
            False,
            _report_id(body),
        )
    except _BindingError as exc:
        return _failure_binding(exc.code)
    except Exception:
        return _failure_binding("internal_error")


def validate_disposable_handshake_identity_binding(
    *,
    network_id: str,
    chain_id: str,
    protocol_version: str,
    genesis_digest: str,
) -> DisposableIdentityBindingResult:
    """Fail-closed identity tuple check for future P2P handshake wiring (no I/O)."""
    try:
        if (
            not isinstance(network_id, str)
            or not isinstance(chain_id, str)
            or not isinstance(protocol_version, str)
            or not isinstance(genesis_digest, str)
        ):
            raise _BindingError("schema_invalid")
        if network_id != NETWORK_ID or network_id in {"MAIN", "main", ""}:
            raise _BindingError("network_id_invalid")
        if protocol_version != PROTOCOL_VERSION:
            raise _BindingError("protocol_version_invalid")
        expected_chain_id = compute_disposable_chain_id(
            network_id=NETWORK_ID, protocol_version=PROTOCOL_VERSION
        )
        if chain_id != expected_chain_id:
            raise _BindingError("chain_id_invalid")
        _require_hex64(genesis_digest, code="genesis_digest_invalid")
        body = {
            "ok": True,
            "code": "ok",
            "network_id": NETWORK_ID,
            "chain_id": expected_chain_id,
            "genesis_digest": genesis_digest,
            "protocol_version": PROTOCOL_VERSION,
            "execution_authorized": False,
        }
        return DisposableIdentityBindingResult(
            True,
            "ok",
            NETWORK_ID,
            expected_chain_id,
            genesis_digest,
            PROTOCOL_VERSION,
            False,
            _report_id(body),
        )
    except _BindingError as exc:
        return _failure_identity(exc.code)
    except Exception:
        return _failure_identity("internal_error")


def validate_disposable_ledger_replay_identity_binding(
    *,
    network_id: str,
    chain_id: str,
    protocol_version: str,
    genesis_digest: str,
) -> DisposableIdentityBindingResult:
    """Fail-closed identity tuple check for future ledger/replay wiring (no I/O)."""
    return validate_disposable_handshake_identity_binding(
        network_id=network_id,
        chain_id=chain_id,
        protocol_version=protocol_version,
        genesis_digest=genesis_digest,
    )


def genesis_json_bytes() -> bytes:
    """Canonical wire-order JSON bytes for the disposable genesis document."""
    return _json_bytes_preserve_order(build_disposable_genesis_document())
