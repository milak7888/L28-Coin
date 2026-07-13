# SPDX-License-Identifier: Apache-2.0
"""
Offline tests for Foundation 14 M2M reference workflow.

Uses TemporaryDirectory fixtures outside the repository only. Does not sign,
create repository data, or perform network operations.
"""
from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from unittest.mock import patch

from coin.m2m_conformance_cli import MAX_INPUT_BYTES
from coin.m2m_reference_workflow import (
    APPROVED_INPUT_MODES,
    CLI_VERSION,
    DOMAIN_REPORT,
    EXIT_FAIL,
    EXIT_INTERNAL,
    EXIT_PASS,
    EXIT_USAGE,
    PROFILE,
    REPORT_FIELD_ORDER,
    REPORT_VERSION,
    STAGE_ORDER,
    STABLE_CODES,
    ReferenceWorkflowResult,
    _exit_for_result,
    _input_mode_is_valid,
    _require_terminal_is_valid,
    build_report,
    compute_report_id,
    run_reference_workflow_json,
)
from coin.m2m_registry_audit import RegistryAuditResult
from coin.m2m_registry_backup import RegistryBackupResult
from coin.m2m_replay_registry import ReplayResult
from coin.m2m_verifier import canonical_bytes

import coin.m2m_reference_workflow as workflow_mod

ROOT = Path(__file__).resolve().parents[1]
VECTOR_PATH = ROOT / "docs" / "m2m" / "test_vectors_reference_workflow_v0.1.json"
TRANSCRIPT_PATH = ROOT / "docs" / "m2m" / "test_vectors_transcript_v0.1.json"
WORKFLOW_PATH = ROOT / "coin" / "m2m_reference_workflow.py"
CLI_MODULE = "coin.m2m_reference_workflow"
MANIFEST_V01_PATH = ROOT / "docs" / "m2m" / "release_manifest_v0.1.json"
MANIFEST_V02_PATH = ROOT / "docs" / "m2m" / "release_manifest_v0.2.json"

HISTORICAL_V01_MANIFEST_SHA256 = (
    "fc721c1c188b2f0a0ba28fe7e06fcb1f1812363c9d611bd42ebc93d34362ca6c"
)
HISTORICAL_V02_MANIFEST_SHA256 = (
    "08c78b80c97557f82905b7df585ae4ec4643dc84f3c7304c00328d532241e04d"
)
HISTORICAL_V02_MANIFEST_ID = (
    "ffb5eb9eccd645e08877347dd2b5324c23dba7962d75e3f2aa40dbb509caa16d"
)

EXPECTED_STABLE_CODES = frozenset(
    {
        "workflow_verified",
        "invalid_input",
        "input_too_large",
        "conformance_failed",
        "terminal_required",
        "initial_admission_failed",
        "source_idempotency_failed",
        "source_audit_failed",
        "backup_failed",
        "restore_failed",
        "restored_audit_failed",
        "restored_idempotency_failed",
        "logical_state_mismatch",
        "unsafe_temporary_directory",
        "verification_backend_unavailable",
        "internal_error",
    }
)

FORBIDDEN_IMPORT_NAMES = frozenset({"Ed25519PrivateKey", "from_private_bytes"})
FORBIDDEN_IMPORT_MODULES = frozenset(
    {"subprocess", "socket", "urllib", "http", "requests", "httpx", "aiohttp"}
)
FORBIDDEN_CALL_ATTRS = frozenset({"sign", "generate"})
LEAK_MARKERS = (
    "/Users/",
    "C:\\\\",
    "hostname",
    "username",
    "getpass",
    "platform",
    "pid",
    "Traceback",
    "Exception",
    "sqlite",
    "SQL",
    "sender_public_key",
    "signature",
    "transaction_id",
    "message_id",
    "exchange_id",
    "wallet",
    "mnemonic",
    "seed",
)


def _run(args: Sequence[str], *, input_bytes: Optional[bytes] = None) -> Tuple[int, str, str]:
    completed = subprocess.run(
        [sys.executable, "-m", CLI_MODULE, *args],
        input=input_bytes,
        capture_output=True,
        cwd=str(ROOT),
    )
    return (
        completed.returncode,
        completed.stdout.decode("utf-8"),
        completed.stderr.decode("utf-8"),
    )


def _parse_single_json_object(stdout: str) -> Dict[str, Any]:
    assert stdout.endswith("\n")
    decoder = json.JSONDecoder()
    obj, end = decoder.raw_decode(stdout)
    assert stdout[end:] == "\n"
    return obj


def _transcript_raw(transcript_vector_id: str) -> bytes:
    doc = json.loads(TRANSCRIPT_PATH.read_text(encoding="utf-8"))
    transcripts = {
        **{v["vector_id"]: v for v in doc["valid_transcripts"]},
        **{v["vector_id"]: v for v in doc["invalid_transcripts"]},
    }
    return json.dumps(
        transcripts[transcript_vector_id]["envelopes"],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _vector_raw(vec: Dict[str, Any]) -> bytes:
    if "raw_text" in vec:
        return vec["raw_text"].encode("utf-8")
    if "raw_hex" in vec:
        return bytes.fromhex(vec["raw_hex"])
    assert "transcript_vector_id" in vec
    return _transcript_raw(vec["transcript_vector_id"])


_ORIGINAL_TEMPORARY_DIRECTORY = tempfile.TemporaryDirectory


class _TrackingTemporaryDirectory:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._inner = _ORIGINAL_TEMPORARY_DIRECTORY(*args, **kwargs)
        self.name = self._inner.name

    def __enter__(self) -> str:
        return self._inner.__enter__()

    def __exit__(self, *args: Any) -> None:
        return self._inner.__exit__(*args)


def _run_with_tracking(
    raw: bytes,
    *,
    require_terminal: bool = False,
    patches: Optional[Dict[str, Any]] = None,
) -> Tuple[ReferenceWorkflowResult, List[Path]]:
    created: List[Path] = []

    class Tracker(_TrackingTemporaryDirectory):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            created.append(Path(self.name))

    patchers = [patch("coin.m2m_reference_workflow.tempfile.TemporaryDirectory", Tracker)]
    if patches:
        for target, value in patches.items():
            patchers.append(patch(target, value))
    for patcher in patchers:
        patcher.start()
    try:
        result = run_reference_workflow_json(
            raw,
            require_terminal=require_terminal,
            input_mode="api",
        )
    finally:
        for patcher in reversed(patchers):
            patcher.stop()
    return result, created


class TestReferenceWorkflowParameterValidation(unittest.TestCase):
    def test_approved_input_modes_exact(self) -> None:
        self.assertEqual(APPROVED_INPUT_MODES, frozenset({"api", "file", "stdin"}))

    def test_unknown_input_mode_rejected(self) -> None:
        result = run_reference_workflow_json(b"[]", input_mode="network")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "internal_error")
        self.assertIsNone(result.failed_stage)
        self.assertIsNone(result.input_mode)

    def test_empty_input_mode_rejected(self) -> None:
        result = run_reference_workflow_json(b"[]", input_mode="")
        self.assertEqual(result.code, "internal_error")
        self.assertIsNone(result.input_mode)

    def test_absolute_path_input_mode_rejected(self) -> None:
        rejected = "/Users/operator/api"
        result = run_reference_workflow_json(b"[]", input_mode=rejected)
        self.assertEqual(result.code, "internal_error")
        self.assertIsNone(result.input_mode)

    def test_secret_looking_input_mode_rejected(self) -> None:
        rejected = "bearer-sk-secret"
        result = run_reference_workflow_json(b"[]", input_mode=rejected)
        self.assertEqual(result.code, "internal_error")
        self.assertIsNone(result.input_mode)

    def test_oversized_input_mode_rejected(self) -> None:
        rejected = "a" * 17
        result = run_reference_workflow_json(b"[]", input_mode=rejected)
        self.assertEqual(result.code, "internal_error")
        self.assertIsNone(result.input_mode)

    def test_non_string_input_mode_rejected(self) -> None:
        for value in (1, None, ["stdin"], {"mode": "api"}):
            with self.subTest(value=repr(value)):
                result = run_reference_workflow_json(b"[]", input_mode=value)  # type: ignore[arg-type]
                self.assertEqual(result.code, "internal_error")
                self.assertIsNone(result.input_mode)

    def test_non_boolean_require_terminal_rejected(self) -> None:
        for value in (0, 1, "true", None, [], {}):
            with self.subTest(value=repr(value)):
                result = run_reference_workflow_json(
                    b"[]",
                    require_terminal=value,  # type: ignore[arg-type]
                )
                self.assertEqual(result.code, "internal_error")
                self.assertFalse(result.require_terminal)

    def test_rejected_values_absent_from_serialized_report(self) -> None:
        rejected = "/Users/secret/bearer-token-sk_live_abc"
        result = run_reference_workflow_json(b"[]", input_mode=rejected)
        report = build_report(result)
        serialized = json.dumps(report, sort_keys=True)
        self.assertIsNone(report["input_mode"])
        self.assertNotIn(rejected, serialized)
        self.assertNotIn("/Users/", serialized)

    def test_parameter_validation_exit_code(self) -> None:
        result = run_reference_workflow_json(b"[]", input_mode="not-a-mode")
        self.assertEqual(_exit_for_result(result), EXIT_INTERNAL)

    def test_validators_require_exact_types(self) -> None:
        self.assertTrue(_input_mode_is_valid("api"))
        self.assertFalse(_input_mode_is_valid("api "))
        self.assertTrue(_require_terminal_is_valid(False))
        self.assertTrue(_require_terminal_is_valid(True))
        self.assertFalse(_require_terminal_is_valid(0))
        self.assertFalse(_require_terminal_is_valid(1))

    def test_cli_stderr_does_not_echo_rejected_input_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "transcript.json"
            path.write_bytes(_transcript_raw("valid_happy_path_completed"))
            code, out, err = _run(["--input", str(path), "--require-terminal"])
        self.assertEqual(code, EXIT_PASS)
        self.assertNotIn(str(path), out)
        self.assertEqual(err, "")


class TestReferenceWorkflowContracts(unittest.TestCase):
    def test_stable_code_set_exact(self) -> None:
        self.assertEqual(STABLE_CODES, EXPECTED_STABLE_CODES)

    def test_result_is_frozen(self) -> None:
        result = run_reference_workflow_json(
            _transcript_raw("valid_happy_path_completed"),
            require_terminal=True,
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.ok = False  # type: ignore[misc]

    def test_stage_codes_shape_and_order(self) -> None:
        result = run_reference_workflow_json(
            _transcript_raw("valid_happy_path_completed"),
            require_terminal=True,
        )
        self.assertEqual(tuple(result.stage_codes.keys()), STAGE_ORDER)
        self.assertEqual(len(result.stage_codes), len(STAGE_ORDER))


class TestReferenceWorkflowVectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        doc = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
        cls.vectors = {v["vector_id"]: v for v in doc["workflow_vectors"]}

    def _assert_stage_prefix_null_after_failure(self, result: ReferenceWorkflowResult) -> None:
        failed = result.failed_stage
        assert failed is not None
        seen_failed = False
        for stage in STAGE_ORDER:
            if stage == failed:
                seen_failed = True
                continue
            if seen_failed:
                self.assertIsNone(result.stage_codes[stage], stage)

    def test_happy_path_completed(self) -> None:
        vec = self.vectors["happy_path_completed"]
        result = run_reference_workflow_json(
            _vector_raw(vec),
            require_terminal=bool(vec["require_terminal"]),
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "workflow_verified")
        self.assertIsNone(result.failed_stage)
        for stage, code in vec["expected_stage_codes"].items():
            self.assertEqual(result.stage_codes[stage], code, stage)

    def test_partial_accepted_without_terminal(self) -> None:
        vec = self.vectors["partial_accepted_without_terminal"]
        result = run_reference_workflow_json(_vector_raw(vec), require_terminal=False)
        self.assertEqual(result.code, "workflow_verified")

    def test_partial_rejected_with_terminal(self) -> None:
        vec = self.vectors["partial_rejected_with_terminal"]
        result = run_reference_workflow_json(_vector_raw(vec), require_terminal=True)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "terminal_required")
        self.assertEqual(result.failed_stage, "transcript_validation")
        self._assert_stage_prefix_null_after_failure(result)

    def test_terminal_cancelled_completed(self) -> None:
        vec = self.vectors["terminal_cancelled_completed"]
        result = run_reference_workflow_json(_vector_raw(vec), require_terminal=True)
        self.assertEqual(result.code, "workflow_verified")

    def test_malformed_json(self) -> None:
        vec = self.vectors["malformed_json"]
        result = run_reference_workflow_json(_vector_raw(vec))
        self.assertEqual(result.code, "conformance_failed")
        self.assertEqual(result.component_code, "invalid_json")

    def test_malformed_utf8(self) -> None:
        vec = self.vectors["malformed_utf8"]
        result = run_reference_workflow_json(_vector_raw(vec))
        self.assertEqual(result.code, "conformance_failed")

    def test_invalid_signature(self) -> None:
        vec = self.vectors["invalid_signature"]
        result = run_reference_workflow_json(_vector_raw(vec))
        self.assertEqual(result.code, "conformance_failed")
        self.assertEqual(result.component_code, "bad_signature")

    def test_mixed_exchange(self) -> None:
        vec = self.vectors["mixed_exchange"]
        result = run_reference_workflow_json(_vector_raw(vec))
        self.assertEqual(result.code, "conformance_failed")

    def test_injected_initial_admission_failure(self) -> None:
        raw = _vector_raw(self.vectors["failed_initial_admission"])

        def fake_admit(path, *, raw, require_terminal, create):
            if create:
                return "recorded_extension", None
            return "already_recorded", None

        with patch.object(workflow_mod, "_admit_json", side_effect=fake_admit):
            result = run_reference_workflow_json(raw, require_terminal=True)
        self.assertEqual(result.code, "initial_admission_failed")
        self.assertEqual(result.component_code, "recorded_extension")
        self._assert_stage_prefix_null_after_failure(result)

    def test_injected_prefix_idempotency_rejected(self) -> None:
        raw = _vector_raw(self.vectors["failed_exact_idempotency"])
        original = workflow_mod._admit_json
        calls = {"n": 0}

        def fake_admit(path, *, raw, require_terminal, create):
            calls["n"] += 1
            if calls["n"] == 1:
                return original(
                    path,
                    raw=raw,
                    require_terminal=require_terminal,
                    create=create,
                )
            return "already_recorded_prefix", None

        with patch.object(workflow_mod, "_admit_json", side_effect=fake_admit):
            result = run_reference_workflow_json(raw, require_terminal=True)
        self.assertEqual(result.code, "source_idempotency_failed")
        self.assertEqual(calls["n"], 2)

    def test_injected_source_audit_failure(self) -> None:
        raw = _vector_raw(self.vectors["failed_source_audit"])
        healthy = RegistryAuditResult(
            ok=True,
            code="registry_healthy",
            schema_version=1,
            exchange_count=1,
            message_count=5,
            logical_registry_digest="a" * 64,
        )

        def fake_audit(path):
            if "restored" in str(path):
                return healthy
            return RegistryAuditResult(ok=False, code="registry_integrity_error")

        with patch.object(workflow_mod, "audit_registry", side_effect=fake_audit):
            result = run_reference_workflow_json(raw, require_terminal=True)
        self.assertEqual(result.code, "source_audit_failed")

    def test_injected_backup_failure(self) -> None:
        raw = _vector_raw(self.vectors["failed_backup"])
        with patch.object(
            workflow_mod,
            "create_registry_backup",
            return_value=RegistryBackupResult(ok=False, code="backup_failed", operation="backup"),
        ):
            result = run_reference_workflow_json(raw, require_terminal=True)
        self.assertEqual(result.code, "backup_failed")
        self.assertEqual(result.failed_stage, "backup")

    def test_injected_restore_failure(self) -> None:
        raw = _vector_raw(self.vectors["failed_restore"])
        with patch.object(
            workflow_mod,
            "restore_registry_backup",
            return_value=RegistryBackupResult(ok=False, code="restore_failed", operation="restore"),
        ):
            result = run_reference_workflow_json(raw, require_terminal=True)
        self.assertEqual(result.code, "restore_failed")

    def test_injected_restored_audit_failure(self) -> None:
        raw = _vector_raw(self.vectors["failed_restored_audit"])
        healthy = RegistryAuditResult(
            ok=True,
            code="registry_healthy",
            schema_version=1,
            exchange_count=1,
            message_count=5,
            logical_registry_digest="a" * 64,
        )
        calls = {"n": 0}

        def fake_audit(path):
            calls["n"] += 1
            if calls["n"] == 1:
                return healthy
            return RegistryAuditResult(ok=False, code="registry_integrity_error")

        with patch.object(workflow_mod, "audit_registry", side_effect=fake_audit):
            result = run_reference_workflow_json(raw, require_terminal=True)
        self.assertEqual(result.code, "restored_audit_failed")

    def test_injected_restored_idempotency_failure(self) -> None:
        raw = _vector_raw(self.vectors["failed_restored_idempotency"])
        original = workflow_mod._admit_json
        calls = {"n": 0}

        def fake_admit(path, *, raw, require_terminal, create):
            calls["n"] += 1
            if calls["n"] < 3:
                return original(
                    path,
                    raw=raw,
                    require_terminal=require_terminal,
                    create=create,
                )
            return "already_recorded_prefix", None

        with patch.object(workflow_mod, "_admit_json", side_effect=fake_admit):
            result = run_reference_workflow_json(raw, require_terminal=True)
        self.assertEqual(result.code, "restored_idempotency_failed")

    def test_injected_logical_state_mismatch(self) -> None:
        raw = _vector_raw(self.vectors["logical_state_mismatch"])
        with patch.object(workflow_mod, "_logical_states_equal", return_value=False):
            result = run_reference_workflow_json(raw, require_terminal=True)
        self.assertEqual(result.code, "logical_state_mismatch")

    def test_injected_unsafe_temporary_directory(self) -> None:
        raw = _vector_raw(self.vectors["unsafe_temporary_directory"])
        with patch.object(workflow_mod, "_assert_safe_temp_root", return_value="unsafe_temporary_directory"):
            result = run_reference_workflow_json(raw, require_terminal=True)
        self.assertEqual(result.code, "unsafe_temporary_directory")

    def test_injected_backend_unavailable(self) -> None:
        raw = _vector_raw(self.vectors["backend_unavailable"])
        from coin.m2m_transcript_validator import TranscriptResult

        with patch.object(
            workflow_mod,
            "verify_transcript_json",
            return_value=TranscriptResult(
                ok=False,
                code="envelope_verification_failed",
                envelope_code="verification_backend_unavailable",
                verified_messages=0,
            ),
        ):
            result = run_reference_workflow_json(raw)
        self.assertEqual(result.code, "verification_backend_unavailable")


class TestReferenceWorkflowDeterminism(unittest.TestCase):
    def test_report_id_recomputation(self) -> None:
        raw = _transcript_raw("valid_happy_path_completed")
        result = run_reference_workflow_json(raw, require_terminal=True)
        report = build_report(result)
        body = {k: v for k, v in report.items() if k != "report_id"}
        self.assertEqual(report["report_id"], compute_report_id(body))
        self.assertEqual(
            report["report_id"],
            hashlib.sha256(DOMAIN_REPORT + canonical_bytes(body)).hexdigest(),
        )

    def test_deterministic_repeated_report(self) -> None:
        raw = _transcript_raw("valid_happy_path_completed")
        first = run_reference_workflow_json(raw, require_terminal=True)
        second = run_reference_workflow_json(raw, require_terminal=True)
        self.assertEqual(build_report(first), build_report(second))

    def test_no_sqlite_byte_fields_in_report(self) -> None:
        result = run_reference_workflow_json(
            _transcript_raw("valid_happy_path_completed"),
            require_terminal=True,
        )
        report = build_report(result)
        forbidden = {
            "artifact_sha256",
            "input_audit_report_id",
            "output_audit_report_id",
            "backup_report_id",
            "restore_report_id",
        }
        self.assertFalse(forbidden & set(report.keys()))
        text = json.dumps(report, sort_keys=True)
        for marker in ("artifact_sha256", "backup_report_id", "restore_report_id"):
            self.assertNotIn(marker, text)

    def test_compact_pretty_equivalence(self) -> None:
        result = run_reference_workflow_json(
            _transcript_raw("valid_happy_path_completed"),
            require_terminal=True,
        )
        report = build_report(result)
        compact = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        pretty = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False)
        self.assertEqual(json.loads(compact), json.loads(pretty))

    def test_input_mode_documented_difference(self) -> None:
        raw = _transcript_raw("valid_happy_path_completed")
        api = run_reference_workflow_json(raw, require_terminal=True, input_mode="api")
        file_mode = run_reference_workflow_json(raw, require_terminal=True, input_mode="file")
        self.assertNotEqual(api.input_mode, file_mode.input_mode)
        api_report = build_report(api)
        file_report = build_report(file_mode)
        for key in api_report:
            if key in {"input_mode", "report_id"}:
                continue
            self.assertEqual(api_report[key], file_report[key], key)


class TestReferenceWorkflowCleanup(unittest.TestCase):
    def test_no_temp_state_after_success(self) -> None:
        result, created = _run_with_tracking(
            _transcript_raw("valid_happy_path_completed"),
            require_terminal=True,
        )
        self.assertTrue(result.ok)
        for path in created:
            self.assertFalse(path.exists())

    def test_no_temp_state_after_injected_backup_failure(self) -> None:
        with patch.object(
            workflow_mod,
            "create_registry_backup",
            return_value=RegistryBackupResult(ok=False, code="backup_failed", operation="backup"),
        ):
            result, created = _run_with_tracking(
                _transcript_raw("valid_happy_path_completed"),
                require_terminal=True,
            )
        self.assertEqual(result.code, "backup_failed")
        for path in created:
            self.assertFalse(path.exists())

    def test_unsafe_tmpdir_inside_repo_rejected(self) -> None:
        repo_tmp = ROOT / ".workflow-tmp-test-marker"
        repo_tmp.mkdir(exist_ok=True)
        try:
            with patch.dict(os.environ, {"TMPDIR": str(repo_tmp)}):
                result = run_reference_workflow_json(
                    _transcript_raw("valid_happy_path_completed"),
                    require_terminal=True,
                )
            self.assertEqual(result.code, "unsafe_temporary_directory")
        finally:
            repo_tmp.rmdir()


class TestReferenceWorkflowCLI(unittest.TestCase):
    def test_version(self) -> None:
        code, out, err = _run(["--version"])
        self.assertEqual(code, EXIT_PASS)
        self.assertEqual(out, CLI_VERSION + "\n")
        self.assertEqual(err, "")

    def test_usage_when_no_input(self) -> None:
        code, out, err = _run([])
        self.assertEqual(code, EXIT_USAGE)
        self.assertEqual(out, "")

    def test_happy_path_file_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "transcript.json"
            path.write_bytes(_transcript_raw("valid_happy_path_completed"))
            code, out, err = _run(["--input", str(path), "--require-terminal"])
        self.assertEqual(code, EXIT_PASS)
        report = _parse_single_json_object(out)
        self.assertTrue(report["ok"])
        self.assertEqual(report["code"], "workflow_verified")
        self.assertEqual(err, "")

    def test_happy_path_stdin_input(self) -> None:
        raw = _transcript_raw("valid_happy_path_completed")
        code, out, err = _run(["--stdin", "--require-terminal"], input_bytes=raw)
        self.assertEqual(code, EXIT_PASS)
        report = _parse_single_json_object(out)
        self.assertEqual(report["input_mode"], "stdin")
        self.assertEqual(err, "")

    def test_conformance_failure_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_bytes(b"{")
            code, out, err = _run(["--input", str(path)])
        self.assertEqual(code, EXIT_FAIL)
        report = _parse_single_json_object(out)
        self.assertFalse(report["ok"])

    def test_input_too_large_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "big.json"
            path.write_bytes(b"[" + b" " * (MAX_INPUT_BYTES + 1) + b"]")
            code, out, err = _run(["--input", str(path)])
        self.assertEqual(code, EXIT_USAGE)
        report = _parse_single_json_object(out)
        self.assertEqual(report["code"], "input_too_large")

    def test_symlink_input_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "real.json"
            real.write_bytes(_transcript_raw("valid_happy_path_completed"))
            link = Path(tmp) / "link.json"
            link.symlink_to(real)
            code, out, err = _run(["--input", str(link)])
        self.assertEqual(code, EXIT_USAGE)
        report = _parse_single_json_object(out)
        self.assertEqual(report["code"], "invalid_input")

    def test_only_exit_zero_may_be_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_bytes(b"{")
            code, out, _ = _run(["--input", str(path)])
        self.assertNotEqual(code, EXIT_PASS)
        report = _parse_single_json_object(out)
        self.assertFalse(report["ok"])


class TestReferenceWorkflowLeakage(unittest.TestCase):
    def test_report_field_order_and_bounded_fields(self) -> None:
        result = run_reference_workflow_json(
            _transcript_raw("valid_happy_path_completed"),
            require_terminal=True,
        )
        report = build_report(result)
        self.assertEqual(list(report.keys()), list(REPORT_FIELD_ORDER))
        self.assertEqual(report["report_version"], REPORT_VERSION)
        self.assertEqual(report["profile"], PROFILE)

    def test_no_path_or_identity_leakage_in_report(self) -> None:
        result = run_reference_workflow_json(
            _transcript_raw("valid_happy_path_completed"),
            require_terminal=True,
        )
        text = json.dumps(build_report(result), sort_keys=True).lower()
        for marker in LEAK_MARKERS:
            self.assertNotIn(marker.lower(), text)

    def test_component_code_contained_in_stage_codes_on_failure(self) -> None:
        result = run_reference_workflow_json(_vector_raw({"raw_text": "{"}))
        self.assertFalse(result.ok)
        self.assertEqual(result.component_code, result.stage_codes["transcript_validation"])

    def test_module_has_no_forbidden_imports(self) -> None:
        tree = ast.parse(WORKFLOW_PATH.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                self.assertNotIn(root, FORBIDDEN_IMPORT_MODULES)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name.split(".")[0], FORBIDDEN_IMPORT_MODULES)


class TestReferenceWorkflowHistoricalAnchors(unittest.TestCase):
    def test_v01_manifest_unchanged(self) -> None:
        digest = hashlib.sha256(MANIFEST_V01_PATH.read_bytes()).hexdigest()
        self.assertEqual(digest, HISTORICAL_V01_MANIFEST_SHA256)

    def test_v02_manifest_unchanged(self) -> None:
        digest = hashlib.sha256(MANIFEST_V02_PATH.read_bytes()).hexdigest()
        self.assertEqual(digest, HISTORICAL_V02_MANIFEST_SHA256)

    def test_v02_manifest_id_unchanged(self) -> None:
        manifest = json.loads(MANIFEST_V02_PATH.read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_id"], HISTORICAL_V02_MANIFEST_ID)


class TestReferenceWorkflowRepositoryHygiene(unittest.TestCase):
    def test_no_repository_data_side_effects(self) -> None:
        before = {
            p.relative_to(ROOT)
            for p in ROOT.rglob("*")
            if p.is_file()
            and p.suffix in {".sqlite", ".db", ".wal", ".shm", ".journal"}
        }
        run_reference_workflow_json(
            _transcript_raw("valid_happy_path_completed"),
            require_terminal=True,
        )
        after = {
            p.relative_to(ROOT)
            for p in ROOT.rglob("*")
            if p.is_file()
            and p.suffix in {".sqlite", ".db", ".wal", ".shm", ".journal"}
        }
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
