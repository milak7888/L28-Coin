# SPDX-License-Identifier: Apache-2.0
"""Disposable test-only custody for one restart-stable signer identity.

The store is used only when the caller supplies an explicit directory. It is
not production custody. The private key is written only inside that directory
and is never printed, logged, or returned by the process entry point.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin.disposable_offline_transfer_demo import public_identity
from coin.two_agent_service_transaction_demo import _public_key_hex


CUSTODY_PROFILE = "L28-DISPOSABLE-CUSTODY-CONTINUITY001"
VERSION = 1
KEY_NAME = "custody-key"
PUBLIC_NAME = "custody-public.json"
PRIVATE_DIRECTORY_MODE = 0o700
PRIVATE_FILE_MODE = 0o600
PUBLIC_FIELDS = frozenset({"key_fingerprint", "profile", "public_identity", "public_key", "version"})
MAX_PUBLIC_BYTES = 4096


class CustodyError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def initialize_public(directory: str | Path) -> dict[str, Any]:
    signing_key = load_signer_key(directory, "init", None)
    del signing_key
    return read_public_record(directory)


def read_public_record(directory: str | Path) -> dict[str, Any]:
    path = Path(directory) / PUBLIC_NAME
    if path.is_symlink():
        raise CustodyError("custody_path_rejected")
    if not path.is_file():
        raise CustodyError("custody_missing")
    return _public_record(_read_bounded(path))


def reopen_identity(directory: str | Path, expected_identity: str) -> str:
    signing_key = load_signer_key(directory, "reuse", expected_identity)
    try:
        return public_identity(_public_key_hex(signing_key))
    finally:
        del signing_key


def load_signer_key(
    directory: str | Path,
    mode: str,
    expected_identity: str | None,
) -> Ed25519PrivateKey:
    if mode == "init":
        if expected_identity is not None:
            raise CustodyError("custody_mode_rejected")
        return _initialize(Path(directory))
    if mode == "reuse":
        if not isinstance(expected_identity, str) or not expected_identity:
            raise CustodyError("custody_continuity_required")
        return _open(Path(directory), expected_identity)
    raise CustodyError("custody_mode_rejected")


def execute_disposable_custody_continuity(
    custody_dir: str | Path,
    state_dir: str | Path,
    input_text: str,
) -> dict[str, Any]:
    custody = Path(custody_dir)
    state = Path(state_dir)
    _reject_nested(custody, state)
    state.mkdir(parents=True, exist_ok=True)
    observed: list[bytes] = []
    processes: list[tuple[subprocess.Popen[str], int, str]] = []
    try:
        result = _run_continuity(custody, state, input_text, observed, processes)
    except CustodyError:
        raise
    except Exception as exc:
        code = getattr(exc, "code", None)
        if isinstance(code, str) and code.isidentifier():
            raise CustodyError(code) from None
        raise CustodyError("signer_failed") from None
    finally:
        _drain(processes, observed)
    assert_material_unexposed(custody, state, observed + [_json_bytes(result)])
    return result


def assert_material_unexposed(custody: Path, state: Path, blobs: list[bytes]) -> None:
    raw = _read_key_bytes(custody / KEY_NAME)
    try:
        token = raw.hex().encode("ascii")
        payloads = list(blobs)
        payloads.append((custody / PUBLIC_NAME).read_bytes())
        for path in state.rglob("*"):
            if path.is_file() and not path.is_symlink():
                payloads.append(path.read_bytes())
        for blob in payloads:
            if raw in blob or token in blob:
                raise CustodyError("secret_material_forbidden")
    finally:
        del raw


def _initialize(directory: Path) -> Ed25519PrivateKey:
    directory = _prepare_init(directory)
    signing_key = Ed25519PrivateKey.generate()
    public_hex = _public_key_hex(signing_key)
    identity = public_identity(public_hex)
    raw = _raw_private(signing_key)
    try:
        fingerprint = hashlib.sha256(raw).hexdigest()
        public_text = _public_document(public_hex, identity, fingerprint)
        if raw.hex() in public_text:
            raise CustodyError("secret_material_forbidden")
        _write_new(directory / KEY_NAME, raw)
        _write_new(directory / PUBLIC_NAME, public_text.encode("utf-8"))
    finally:
        del raw
    _require_private(directory / KEY_NAME, directory=False)
    _require_private(directory / PUBLIC_NAME, directory=False)
    return signing_key


def _open(directory: Path, expected_identity: str) -> Ed25519PrivateKey:
    _prepare_reuse(directory)
    try:
        public_text = _read_bounded(directory / PUBLIC_NAME).decode("utf-8")
    except UnicodeError:
        raise CustodyError("custody_malformed") from None
    record = _public_record(public_text.encode("utf-8"))
    raw = _read_key_bytes(directory / KEY_NAME)
    try:
        if len(raw) != 32:
            raise CustodyError("custody_corrupt")
        if hashlib.sha256(raw).hexdigest() != record["key_fingerprint"]:
            raise CustodyError("custody_corrupt")
        if raw.hex() in public_text:
            raise CustodyError("custody_corrupt")
        signing_key = Ed25519PrivateKey.from_private_bytes(raw)
        derived_public = _public_key_hex(signing_key)
        derived_identity = public_identity(derived_public)
        if derived_public != record["public_key"] or derived_identity != record["public_identity"]:
            del signing_key
            raise CustodyError("custody_corrupt")
        if derived_identity != expected_identity:
            del signing_key
            raise CustodyError("custody_replaced")
        return signing_key
    except CustodyError:
        raise
    except Exception:
        raise CustodyError("custody_corrupt") from None
    finally:
        del raw


def _prepare_init(directory: Path) -> Path:
    if directory.is_symlink():
        raise CustodyError("custody_path_rejected")
    if directory.exists():
        if not directory.is_dir():
            raise CustodyError("custody_path_rejected")
        _require_private(directory, directory=True)
        if _custody_names_present(directory):
            raise CustodyError("custody_exists")
        return directory
    if directory.parent.is_symlink() or not directory.parent.is_dir():
        raise CustodyError("custody_path_rejected")
    directory.mkdir(mode=PRIVATE_DIRECTORY_MODE)
    os.chmod(directory, PRIVATE_DIRECTORY_MODE)
    _require_private(directory, directory=True)
    return directory


def _prepare_reuse(directory: Path) -> None:
    if directory.is_symlink():
        raise CustodyError("custody_path_rejected")
    if not directory.is_dir():
        raise CustodyError("custody_missing")
    _require_private(directory, directory=True)
    for name in (KEY_NAME, PUBLIC_NAME):
        path = directory / name
        if path.is_symlink():
            raise CustodyError("custody_path_rejected")
        if not path.is_file():
            raise CustodyError("custody_missing")
        _require_private(path, directory=False)


def _custody_names_present(directory: Path) -> bool:
    return any((directory / name).exists() or (directory / name).is_symlink() for name in (KEY_NAME, PUBLIC_NAME))


def _require_private(path: Path, *, directory: bool) -> None:
    if path.is_symlink():
        raise CustodyError("custody_path_rejected")
    if not path.exists():
        raise CustodyError("custody_missing")
    if os.name == "posix":
        if path.stat().st_mode & 0o077:
            raise CustodyError("permissions_invalid")
    if directory and not path.is_dir():
        raise CustodyError("custody_corrupt")
    if not directory and not path.is_file():
        raise CustodyError("custody_corrupt")


def _write_new(path: Path, data: bytes) -> None:
    if path.is_symlink() or path.exists():
        raise CustodyError("custody_exists")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, PRIVATE_FILE_MODE)
    except OSError:
        raise CustodyError("custody_path_rejected") from None
    try:
        written = os.write(descriptor, data)
        if written != len(data):
            raise CustodyError("custody_corrupt")
    finally:
        os.close(descriptor)
    os.chmod(path, PRIVATE_FILE_MODE)


def _read_key_bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise CustodyError("custody_corrupt")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError:
        raise CustodyError("custody_path_rejected") from None
    try:
        data = os.read(descriptor, 64)
    finally:
        os.close(descriptor)
    if len(data) != 32:
        raise CustodyError("custody_corrupt")
    return data


def _read_bounded(path: Path) -> bytes:
    data = path.read_bytes()
    if len(data) > MAX_PUBLIC_BYTES:
        raise CustodyError("custody_malformed")
    return data


def _public_document(public_hex: str, identity: str, fingerprint: str) -> str:
    body = {
        "key_fingerprint": fingerprint,
        "profile": CUSTODY_PROFILE,
        "public_identity": identity,
        "public_key": public_hex,
        "version": VERSION,
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def _public_record(data: bytes) -> dict[str, Any]:
    try:
        record = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise CustodyError("custody_malformed") from None
    if not isinstance(record, dict) or set(record) != PUBLIC_FIELDS:
        raise CustodyError("custody_malformed")
    if record["profile"] != CUSTODY_PROFILE:
        raise CustodyError("custody_profile_rejected")
    if type(record["version"]) is not int or record["version"] != VERSION:
        raise CustodyError("custody_version_rejected")
    public_hex = record["public_key"]
    identity = record["public_identity"]
    fingerprint = record["key_fingerprint"]
    if not all(isinstance(value, str) for value in (public_hex, identity, fingerprint)):
        raise CustodyError("custody_malformed")
    if len(public_hex) != 64 or len(fingerprint) != 64:
        raise CustodyError("custody_malformed")
    try:
        if public_identity(public_hex) != identity:
            raise CustodyError("custody_malformed")
    except CustodyError:
        raise
    except Exception:
        raise CustodyError("custody_malformed") from None
    return record


def _raw_private(signing_key: Ed25519PrivateKey) -> bytes:
    return signing_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )


def _reject_nested(custody: Path, state: Path) -> None:
    custody_path = custody.resolve()
    state_path = state.resolve()
    if custody_path == state_path or custody_path in state_path.parents or state_path in custody_path.parents:
        raise CustodyError("custody_path_rejected")


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _run_continuity(
    custody: Path,
    state: Path,
    input_text: str,
    observed: list[bytes],
    processes: list[tuple[subprocess.Popen[str], int, str]],
) -> dict[str, Any]:
    from coin.disposable_offline_transfer_demo import DEMO_TIMESTAMP
    from coin.durable_restart_safe_service_demo import PAYMENT_PATH, REQUEST_PATH, SHUTDOWN_PATH, _exchange
    from coin.durable_restart_safe_service_demo import _json_bytes as durable_json
    from coin.isolated_nonproduction_signer import SHUTDOWN_PATH as SIGNER_SHUTDOWN
    from coin.two_agent_service_transaction_demo import (
        PRICE_L28,
        structured_text_analysis,
        verify_service_quote,
        verify_service_receipt,
        verify_service_result,
    )

    _payer, payer = _track(
        ["-m", "coin.isolated_nonproduction_signer", "--role", "signer"],
        SIGNER_SHUTDOWN,
        observed,
        processes,
    )
    if payer.get("key_persisted") is not False or payer.get("production_signing") is not False:
        raise CustodyError("production_signer_refused")
    if payer.get("SIGNER_RUNTIME_ACTIVE") is not False or payer.get("SIGNING") is not False:
        raise CustodyError("production_signer_refused")
    _provider_signer, provider_signer = _track(
        [
            "-m",
            "coin.isolated_nonproduction_signer",
            "--role",
            "signer",
            "--custody-dir",
            str(custody),
            "--custody-mode",
            "init",
        ],
        SIGNER_SHUTDOWN,
        observed,
        processes,
    )
    identity_a = _require_custody_hello(provider_signer)
    provider_process, provider_ready = _track(
        [
            "-m",
            "coin.durable_restart_safe_service_demo",
            "--role",
            "provider",
            "--state-dir",
            str(state),
            "--port",
            "0",
            "--signer-port",
            str(provider_signer["port"]),
        ],
        SHUTDOWN_PATH,
        observed,
        processes,
    )
    if provider_ready.get("coordination") != "provider_ready":
        raise CustodyError("provider_start_failed")
    provider_port = int(provider_ready["port"])
    hello = _exchange(provider_port, "GET", "/v1/l28/production-entry/provider_hello")
    hello.pop("_status", None)
    if hello.get("provider_identity") != identity_a:
        raise CustodyError("identity_mismatch")
    request = _signer_sign(
        int(payer["port"]),
        "service_request",
        {"provider_identity": identity_a, "input_text": input_text},
    )
    quote = _exchange(provider_port, "POST", REQUEST_PATH, durable_json(request))
    quote.pop("_status", None)
    verify_service_quote(quote, request=request)
    payment_tx = _signer_sign(
        int(payer["port"]),
        "transfer",
        {"receiver": identity_a, "amount": PRICE_L28, "timestamp": DEMO_TIMESTAMP, "nonce": 100},
    )
    authorization = _signer_sign(
        int(payer["port"]),
        "payment_authorization",
        {"request": request, "quote": quote, "payment_tx": payment_tx},
    )
    package = {
        "request": request,
        "quote": quote,
        "payment_tx": payment_tx,
        "payment_authorization": authorization,
    }
    first = _exchange(provider_port, "POST", PAYMENT_PATH, durable_json(package))
    first.pop("_status", None)
    if first.get("ok") is not True:
        raise CustodyError(str(first.get("error", "payment_apply_failed")))
    verify_service_result(first["service_result"], request=request, quote=quote, payment_tx_id=payment_tx["id"])
    verify_service_receipt(
        first["receipt"],
        request=request,
        quote=quote,
        service_result=first["service_result"],
        payment_tx_id=payment_tx["id"],
    )
    if first["service_result"]["output"] != structured_text_analysis(input_text):
        raise CustodyError("tampered_result")
    if first["evidence"]["receiver"] != identity_a:
        raise CustodyError("identity_mismatch")
    _stop_matching(processes, provider_process)
    time.sleep(0.05)
    _stop_matching(processes, _provider_signer)
    _restarted, restarted = _track(
        [
            "-m",
            "coin.isolated_nonproduction_signer",
            "--role",
            "signer",
            "--custody-dir",
            str(custody),
            "--custody-mode",
            "reuse",
            "--expected-identity",
            identity_a,
        ],
        SIGNER_SHUTDOWN,
        observed,
        processes,
    )
    if _require_custody_hello(restarted) != identity_a or restarted.get("public_key") != provider_signer.get("public_key"):
        raise CustodyError("custody_replaced")
    restarted_provider, restarted_ready = _track(
        [
            "-m",
            "coin.durable_restart_safe_service_demo",
            "--role",
            "provider",
            "--state-dir",
            str(state),
            "--port",
            "0",
            "--signer-port",
            str(restarted["port"]),
        ],
        SHUTDOWN_PATH,
        observed,
        processes,
    )
    restarted_port = int(restarted_ready["port"])
    replay = _exchange(restarted_port, "POST", PAYMENT_PATH, durable_json(package))
    replay.pop("_status", None)
    if replay.get("ok") is not False or replay.get("error") != "replay":
        raise CustodyError("replay_not_rejected")
    if replay["evidence"]["service_executed"] is not False:
        raise CustodyError("replay_not_rejected")
    fresh_tx = _signer_sign(
        int(payer["port"]),
        "transfer",
        {"receiver": identity_a, "amount": PRICE_L28, "timestamp": DEMO_TIMESTAMP, "nonce": 101},
    )
    fresh_request = _signer_sign(
        int(payer["port"]),
        "service_request",
        {"provider_identity": identity_a, "input_text": input_text},
    )
    fresh_quote = _exchange(restarted_port, "POST", REQUEST_PATH, durable_json(fresh_request))
    fresh_quote.pop("_status", None)
    verify_service_quote(fresh_quote, request=fresh_request)
    fresh_authorization = _signer_sign(
        int(payer["port"]),
        "payment_authorization",
        {"request": fresh_request, "quote": fresh_quote, "payment_tx": fresh_tx},
    )
    fresh = _exchange(
        restarted_port,
        "POST",
        PAYMENT_PATH,
        durable_json(
            {
                "request": fresh_request,
                "quote": fresh_quote,
                "payment_tx": fresh_tx,
                "payment_authorization": fresh_authorization,
            }
        ),
    )
    fresh.pop("_status", None)
    if fresh.get("ok") is not True:
        raise CustodyError(str(fresh.get("error", "payment_apply_failed")))
    verify_service_result(fresh["service_result"], request=fresh_request, quote=fresh_quote, payment_tx_id=fresh_tx["id"])
    verify_service_receipt(
        fresh["receipt"],
        request=fresh_request,
        quote=fresh_quote,
        service_result=fresh["service_result"],
        payment_tx_id=fresh_tx["id"],
    )
    if fresh["evidence"]["receiver"] != identity_a:
        raise CustodyError("custody_replaced")
    if fresh["evidence"]["result_verified"] is not True or fresh["evidence"]["receipt_verified"] is not True:
        raise CustodyError("tampered_result")
    if first["evidence"]["service_executed"] is not True or first["evidence"]["result_verified"] is not True:
        raise CustodyError("tampered_result")
    if fresh["evidence"]["provider_balance_before"] != 28 or fresh["evidence"]["provider_balance_after"] != 56:
        raise CustodyError("balance_transition_mismatch")
    if fresh["evidence"]["requester_balance_before"] != 72 or fresh["evidence"]["requester_balance_after"] != 44:
        raise CustodyError("balance_transition_mismatch")
    _stop_matching(processes, restarted_provider)
    probes, probe_blobs = _fault_probes(custody.parent / f"{custody.name}-faults")
    observed.extend(probe_blobs)
    if reopen_identity(custody, identity_a) != identity_a:
        raise CustodyError("custody_replaced")
    run1 = first["evidence"]
    if run1["canonical_validation"] != "PASS":
        raise CustodyError("canonical_validation_failed")
    if (run1["requester_balance_before"], run1["provider_balance_before"]) != (100, 0):
        raise CustodyError("balance_transition_mismatch")
    if (run1["requester_balance_after"], run1["provider_balance_after"]) != (72, 28):
        raise CustodyError("balance_transition_mismatch")
    if (replay["evidence"]["requester_balance_after"], replay["evidence"]["provider_balance_after"]) != (72, 28):
        raise CustodyError("balance_transition_mismatch")
    return {
        "custody_profile": CUSTODY_PROFILE,
        "signer_public_identity": identity_a,
        "signer_identity_before_restart": identity_a,
        "signer_identity_after_restart": restarted["identity"],
        "signer_identity_continuity": True,
        "custody_reopened": True,
        "payment_tx_id": run1["payment_tx_id"],
        "canonical_validation": run1["canonical_validation"],
        "replay_rejected": True,
        "requester_balance_before": run1["requester_balance_before"],
        "requester_balance_after": run1["requester_balance_after"],
        "provider_balance_before": run1["provider_balance_before"],
        "provider_balance_after": run1["provider_balance_after"],
        "fresh_payment_tx_id": fresh["evidence"]["payment_tx_id"],
        "service_executed": True,
        "replay_service_executed": False,
        "result_verified": True,
        "receipt_verified": True,
        "custody_private_material_exposed": False,
        "canonical_history_touched": False,
        "production_keys_used": False,
        "production_signing": False,
        "canonical_broadcast_used": False,
        "mining_used": False,
        "production_settlement": False,
        "SIGNER_RUNTIME_ACTIVE": False,
        "SIGNING": False,
        "CUSTODY_READINESS": "UNRESOLVED",
        "RUNTIME_HARDENING": "UNRESOLVED",
        "FAULT_RECOVERY": "UNRESOLVED",
        "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
        "run1": run1,
        "run2_replay": replay["evidence"],
        "run3": fresh["evidence"],
        "custody_failure_verification": probes,
    }


def _require_custody_hello(ready: Mapping[str, Any]) -> str:
    if ready.get("coordination") != "signer_ready" or ready.get("host") != "127.0.0.1":
        raise CustodyError("provider_start_failed")
    if ready.get("production_signing") is not False or ready.get("SIGNER_RUNTIME_ACTIVE") is not False:
        raise CustodyError("production_signer_refused")
    if ready.get("SIGNING") is not False or ready.get("production_keys_used") is not False:
        raise CustodyError("production_signer_refused")
    if ready.get("key_persisted") is not True or ready.get("custody_profile") != CUSTODY_PROFILE:
        raise CustodyError("custody_profile_rejected")
    identity = ready.get("identity")
    public_hex = ready.get("public_key")
    if not isinstance(identity, str) or not isinstance(public_hex, str):
        raise CustodyError("identity_mismatch")
    if public_identity(public_hex) != identity:
        raise CustodyError("identity_mismatch")
    return identity


def _track(
    args: list[str],
    shutdown_path: str,
    observed: list[bytes],
    processes: list[tuple[subprocess.Popen[str], int, str]],
) -> tuple[subprocess.Popen[str], dict[str, Any]]:
    process = subprocess.Popen(
        [sys.executable, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    assert process.stdout is not None
    line = process.stdout.readline()
    observed.append(line)
    if not line:
        err = process.stderr.read() if process.stderr is not None else b""
        observed.append(err)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        text = err.decode("utf-8", errors="replace").strip()
        if "\n" not in text and text.isidentifier():
            raise CustodyError(text)
        raise CustodyError("provider_start_failed")
    try:
        ready = json.loads(line.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        process.kill()
        raise CustodyError("provider_start_failed") from None
    if not isinstance(ready, dict) or ready.get("host") != "127.0.0.1" or type(ready.get("port")) is not int:
        process.kill()
        raise CustodyError("provider_start_failed")
    processes.append((process, int(ready["port"]), shutdown_path))
    return process, ready


def _signer_sign(port: int, purpose: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    from coin.durable_restart_safe_service_demo import _exchange, _json_bytes
    from coin.isolated_nonproduction_signer import SIGN_PATH

    signed = _exchange(port, "POST", SIGN_PATH, _json_bytes({"purpose": purpose, **dict(payload)}))
    signed.pop("_status", None)
    if signed.get("ok") is False:
        raise CustodyError(str(signed.get("error", "signer_rejected")))
    return signed


def _stop_matching(
    processes: list[tuple[subprocess.Popen[str], int, str]],
    process: subprocess.Popen[str],
) -> None:
    from coin.isolated_nonproduction_signer import _stop

    for candidate, port, path in processes:
        if candidate is process and candidate.poll() is None:
            _stop(candidate, port, path)
            return


def _drain(
    processes: list[tuple[subprocess.Popen[str], int, str]],
    observed: list[bytes],
) -> None:
    from coin.isolated_nonproduction_signer import _stop

    for process, port, path in reversed(processes):
        if process.poll() is None:
            _stop(process, port, path)
        if process.stderr is not None:
            observed.append(process.stderr.read())


def _fault_probes(root: Path) -> tuple[dict[str, Any], list[bytes]]:
    root.mkdir(mode=PRIVATE_DIRECTORY_MODE)
    os.chmod(root, PRIVATE_DIRECTORY_MODE)
    blobs: list[bytes] = []
    truncated = _refusal_after(root / "truncated", _truncate)
    replaced = _refusal_after(root / "replaced", _replace_identity)
    loose = _refusal_after(root / "loose", _loosen_key)
    loose_dir = _refusal_after(root / "loose-dir", _loosen_directory)
    for code, stdout, stderr in (truncated, replaced, loose, loose_dir):
        blobs.extend((stdout, stderr))
    if truncated[0] != "custody_corrupt" or replaced[0] != "custody_replaced":
        raise CustodyError("custody_probe_failed")
    if loose[0] != "permissions_invalid" or loose_dir[0] != "permissions_invalid":
        raise CustodyError("custody_probe_failed")
    return {
        "truncated_custody_rejected": truncated[0],
        "replacement_rejected": replaced[0],
        "loose_key_rejected": loose[0],
        "loose_directory_rejected": loose_dir[0],
        "signed_after_rejection": False,
    }, blobs


def _refusal_after(directory: Path, mutate) -> tuple[str, bytes, bytes]:
    initialize_public(directory)
    expected = read_public_record(directory)["public_identity"]
    mutate(directory)
    return _refusal(directory, expected)


def _truncate(directory: Path) -> None:
    key_path = directory / KEY_NAME
    _overwrite(key_path, key_path.read_bytes()[:8])


def _replace_identity(directory: Path) -> None:
    other = directory.parent / "replacement-source"
    initialize_public(other)
    for name in (KEY_NAME, PUBLIC_NAME):
        _overwrite(directory / name, (other / name).read_bytes())


def _loosen_key(directory: Path) -> None:
    os.chmod(directory / KEY_NAME, 0o644)


def _loosen_directory(directory: Path) -> None:
    os.chmod(directory, 0o755)


def _overwrite(path: Path, data: bytes) -> None:
    if path.is_symlink():
        raise CustodyError("custody_path_rejected")
    flags = os.O_WRONLY | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError:
        raise CustodyError("custody_path_rejected") from None
    try:
        os.write(descriptor, data)
    finally:
        os.close(descriptor)
    os.chmod(path, PRIVATE_FILE_MODE)


def _refusal(directory: Path, expected_identity: str) -> tuple[str, bytes, bytes]:
    command = [
        sys.executable,
        "-m",
        "coin.isolated_nonproduction_signer",
        "--role",
        "signer",
        "--custody-dir",
        str(directory),
        "--custody-mode",
        "reuse",
        "--expected-identity",
        expected_identity,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=str(Path(__file__).resolve().parents[1]),
            capture_output=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise CustodyError("custody_probe_failed") from None
    stdout = completed.stdout
    stderr = completed.stderr
    if completed.returncode == 0 or b"signer_ready" in stdout or b"signature" in stdout:
        raise CustodyError("custody_probe_failed")
    code = stderr.decode("utf-8", errors="replace").strip()
    return code, stdout, stderr


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m coin.disposable_custody_continuity")
    parser.add_argument("--custody-dir")
    parser.add_argument("--state-dir")
    parser.add_argument("--input", default="L28 enables machine payments between autonomous systems.")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if not args.custody_dir or not args.state_dir:
            raise CustodyError("custody_dir_required")
        result = execute_disposable_custody_continuity(args.custody_dir, args.state_dir, args.input)
    except CustodyError as exc:
        sys.stderr.write(exc.code + "\n")
        return 1
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
