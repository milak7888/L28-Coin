# SPDX-License-Identifier: Apache-2.0
"""Foundation 55 disposable sandbox lifecycle integration tests."""

from __future__ import annotations

import ast
import contextlib
import hashlib
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from coin import disposable_network_identity_genesis_binding as identity
from coin import disposable_sandbox_directory_cleanup as clean
from coin import disposable_sandbox_directory_materialization as mat
from coin import disposable_sandbox_lifecycle_integration as life
from coin import tx_validation


def _wire(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")


def _hex64(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _harness_root(tmp: str) -> str:
    root = os.path.realpath(tmp)
    if root != "/" and root.endswith("/"):
        root = root.rstrip("/")
    return root


def _plan(*, sandbox_instance_id: str | None = None, **overrides: object) -> dict[str, object]:
    instance = sandbox_instance_id or _hex64("life-instance")
    if instance[0] == "0" and sandbox_instance_id is None:
        instance = "a" + instance[1:]
    base: dict[str, object] = {
        "ok": True,
        "code": "creation_plan_ok",
        "creation_profile": mat.PLAN_PROFILE,
        "environment": identity.ENVIRONMENT,
        "network_id": identity.NETWORK_ID,
        "chain_id": _hex64("chain"),
        "genesis_digest": _hex64("genesis"),
        "protocol_version": identity.PROTOCOL_VERSION,
        "preflight_report_id": _hex64("preflight"),
        "sandbox_instance_id": instance,
        "path_lexeme": "/correlation-only",
        "creation_plan_ok": True,
        "process_launch_authorized": False,
        "execution_authorized": False,
        "report_id": _hex64(f"plan:{instance}"),
        "detail": "",
    }
    base.update(overrides)
    return base


def _mat_request(
    *,
    trusted_root: str,
    plan: dict[str, object] | None = None,
    attempt_id: str | None = None,
    not_after_unix: object | None = None,
) -> dict[str, object]:
    p = plan if plan is not None else _plan()
    attempt = attempt_id or _hex64("attempt")
    not_after = (
        not_after_unix if not_after_unix is not None else int(time.time()) + 3600
    )
    return {
        "materialization_profile": mat.PROFILE,
        "environment": identity.ENVIRONMENT,
        "plan_evidence": p,
        "materialization_authority": {
            "materialization_authorized": True,
            "trusted_root": trusted_root,
            "sandbox_instance_id": p["sandbox_instance_id"],
            "data_dir_tag": identity.DATA_DIR_TAG,
            "plan_report_id": p["report_id"],
            "attempt_id": attempt,
            "not_after_unix": not_after,
        },
        "trusted_root": trusted_root,
        "execution_authorized": False,
        "process_launch_authorized": False,
    }


def _lifecycle_request(
    *,
    trusted_root: str,
    plan: dict[str, object] | None = None,
    attempt_id: str | None = None,
    not_after_unix: object | None = None,
    lifecycle_profile: str = life.PROFILE,
    environment: str = "DISPOSABLE_TEST",
    execution_authorized: object = False,
    process_launch_authorized: object = False,
    process_stop_evidence: dict[str, object] | None = None,
    lifecycle_authority: dict[str, object] | None = None,
    cleanup_handoff: dict[str, object] | None = None,
    materialization_request: dict[str, object] | None = None,
) -> dict[str, object]:
    p = plan if plan is not None else _plan()
    attempt = attempt_id or _hex64("attempt")
    not_after = (
        not_after_unix if not_after_unix is not None else int(time.time()) + 3600
    )
    mat_req = (
        materialization_request
        if materialization_request is not None
        else _mat_request(
            trusted_root=trusted_root,
            plan=p,
            attempt_id=attempt,
            not_after_unix=not_after,
        )
    )
    instance = str(p["sandbox_instance_id"])
    return {
        "lifecycle_profile": lifecycle_profile,
        "environment": environment,
        "lifecycle_authority": lifecycle_authority
        if lifecycle_authority is not None
        else {
            "lifecycle_authorized": True,
            "trusted_root": trusted_root,
            "sandbox_instance_id": instance,
            "data_dir_tag": identity.DATA_DIR_TAG,
            "attempt_id": attempt,
            "not_after_unix": not_after,
        },
        "materialization_request": mat_req,
        "cleanup_handoff": cleanup_handoff
        if cleanup_handoff is not None
        else {
            "cleanup_authorized": True,
            "trusted_root": trusted_root,
            "sandbox_instance_id": instance,
            "data_dir_tag": identity.DATA_DIR_TAG,
            "attempt_id": attempt,
            "not_after_unix": not_after,
        },
        "process_stop_evidence": process_stop_evidence
        if process_stop_evidence is not None
        else {"mode": "never_started", "sandbox_instance_id": instance},
        "execution_authorized": execution_authorized,
        "process_launch_authorized": process_launch_authorized,
    }


class SuccessPathTests(unittest.TestCase):
    def test_lifecycle_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            raw = _wire(_lifecycle_request(trusted_root=root))
            result = life.run_disposable_sandbox_lifecycle_json(raw)
            self.assertTrue(result.ok, result.code)
            self.assertEqual(result.code, "lifecycle_ok")
            self.assertIs(result.lifecycle_ok, True)
            self.assertIs(result.execution_authorized, False)
            self.assertIs(result.process_launch_authorized, False)
            self.assertEqual(result.detail, "")
            self.assertEqual(result.failed_stage, "")
            self.assertEqual(result.stage_code, "")
            self.assertEqual(result.report_id, hashlib.sha256(raw).hexdigest())
            self.assertNotEqual(result.materialization_report_id, "")
            self.assertNotEqual(result.cleanup_report_id, "")
            self.assertFalse(os.path.exists(result.materialization_path))

    def test_path_lexeme_unused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            decoy = os.path.join(root, "decoy")
            os.mkdir(decoy)
            plan = _plan(path_lexeme=decoy)
            result = life.run_disposable_sandbox_lifecycle_json(
                _wire(_lifecycle_request(trusted_root=root, plan=plan))
            )
            self.assertEqual(result.code, "lifecycle_ok")
            self.assertTrue(os.path.isdir(decoy))
            self.assertNotEqual(result.materialization_path, decoy)

    def test_immutability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            result = life.run_disposable_sandbox_lifecycle_json(
                _wire(_lifecycle_request(trusted_root=root))
            )
            self.assertEqual(result.code, "lifecycle_ok")
            with self.assertRaises(Exception):
                result.code = "x"  # type: ignore[misc]


class ParseAndAuthorityTests(unittest.TestCase):
    def test_parse_codes(self) -> None:
        self.assertEqual(
            life.run_disposable_sandbox_lifecycle_json(1).code,  # type: ignore[arg-type]
            "input_type_invalid",
        )
        self.assertEqual(
            life.run_disposable_sandbox_lifecycle_json(b"{" + b"a" * 20000 + b"}").code,
            "input_too_large",
        )
        self.assertEqual(
            life.run_disposable_sandbox_lifecycle_json(b"\xff").code,
            "encoding_invalid",
        )
        self.assertEqual(
            life.run_disposable_sandbox_lifecycle_json(b"{").code, "json_invalid"
        )
        self.assertEqual(
            life.run_disposable_sandbox_lifecycle_json(b'{"a":1,"a":2}').code,
            "duplicate_key",
        )
        self.assertEqual(
            life.run_disposable_sandbox_lifecycle_json(b"[]").code,
            "invalid_top_level",
        )

    def test_authority_and_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            self.assertEqual(
                life.run_disposable_sandbox_lifecycle_json(
                    _wire(_lifecycle_request(trusted_root=root, lifecycle_profile="x"))
                ).code,
                "lifecycle_profile_unsupported",
            )
            self.assertEqual(
                life.run_disposable_sandbox_lifecycle_json(
                    _wire(_lifecycle_request(trusted_root=root, environment="MAIN"))
                ).code,
                "historical_import_forbidden",
            )
            self.assertEqual(
                life.run_disposable_sandbox_lifecycle_json(
                    _wire(_lifecycle_request(trusted_root=root, environment="OTHER"))
                ).code,
                "environment_invalid",
            )
            self.assertEqual(
                life.run_disposable_sandbox_lifecycle_json(
                    _wire(
                        _lifecycle_request(
                            trusted_root=root, execution_authorized=True
                        )
                    )
                ).code,
                "execution_authorized_invalid",
            )
            self.assertEqual(
                life.run_disposable_sandbox_lifecycle_json(
                    _wire(
                        _lifecycle_request(
                            trusted_root=root, process_launch_authorized=True
                        )
                    )
                ).code,
                "process_launch_authorized_invalid",
            )
            forbid = _lifecycle_request(trusted_root=root)
            forbid["wipe_authorized"] = True  # type: ignore[index]
            self.assertEqual(
                life.run_disposable_sandbox_lifecycle_json(_wire(forbid)).code,
                "schema_invalid",
            )
            # authority transfer: cleanup_authorized inside materialization_request
            bad = _lifecycle_request(trusted_root=root)
            bad["materialization_request"]["cleanup_authorized"] = True  # type: ignore[index]
            self.assertEqual(
                life.run_disposable_sandbox_lifecycle_json(_wire(bad)).code,
                "schema_invalid",
            )

            plan = _plan()
            auth = {
                "lifecycle_authorized": True,
                "trusted_root": root,
                "sandbox_instance_id": plan["sandbox_instance_id"],
                "data_dir_tag": "wrong-tag",
                "attempt_id": _hex64("a"),
                "not_after_unix": int(time.time()) + 3600,
            }
            self.assertEqual(
                life.run_disposable_sandbox_lifecycle_json(
                    _wire(
                        _lifecycle_request(
                            trusted_root=root,
                            plan=plan,
                            lifecycle_authority=auth,
                            attempt_id=str(auth["attempt_id"]),
                            not_after_unix=auth["not_after_unix"],
                        )
                    )
                ).code,
                "lifecycle_authority_mismatch",
            )

            self.assertEqual(
                life.run_disposable_sandbox_lifecycle_json(
                    _wire(
                        _lifecycle_request(
                            trusted_root=root,
                            not_after_unix=1,
                        )
                    )
                ).code,
                "lifecycle_authority_expired",
            )

            stopped = {
                "mode": "stopped",
                "sandbox_instance_id": plan["sandbox_instance_id"],
                "listeners_cleared": True,
                "stop_report_id": _hex64("stop"),
            }
            self.assertEqual(
                life.run_disposable_sandbox_lifecycle_json(
                    _wire(
                        _lifecycle_request(
                            trusted_root=root,
                            plan=plan,
                            process_stop_evidence=stopped,  # type: ignore[arg-type]
                        )
                    )
                ).code,
                "stopped_mode_forbidden",
            )


def _mat_ok_then(mutator):
    real_mat = mat.materialize_disposable_sandbox_directory_json

    def _inner(payload: str | bytes) -> object:
        result = real_mat(payload)
        if result.code == "materialization_ok":
            mutator(result)
        return result

    return _inner


def _counting_cleanup():
    cleanup_calls = {"n": 0}
    real_cleanup = clean.cleanup_disposable_sandbox_directory_json

    def wrapped(payload: str | bytes) -> object:
        cleanup_calls["n"] += 1
        return real_cleanup(payload)

    return cleanup_calls, wrapped


class StageAndVerifyTests(unittest.TestCase):
    def test_stage_binding_all_bound_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            plan = _plan()

            # trusted_root
            req = _lifecycle_request(trusted_root=root, plan=plan)
            req["cleanup_handoff"]["trusted_root"] = root + "z"  # type: ignore[index]
            self.assertEqual(
                life.run_disposable_sandbox_lifecycle_json(_wire(req)).code,
                "stage_binding_invalid",
            )

            # sandbox_instance_id
            req = _lifecycle_request(trusted_root=root, plan=plan)
            req["cleanup_handoff"]["sandbox_instance_id"] = _hex64("other-inst")  # type: ignore[index]
            self.assertEqual(
                life.run_disposable_sandbox_lifecycle_json(_wire(req)).code,
                "stage_binding_invalid",
            )

            # data_dir_tag (handoff inequality — not lifecycle_authority_mismatch)
            req = _lifecycle_request(trusted_root=root, plan=plan)
            req["cleanup_handoff"]["data_dir_tag"] = "l28-disposable-testX"  # type: ignore[index]
            result = life.run_disposable_sandbox_lifecycle_json(_wire(req))
            self.assertEqual(result.code, "stage_binding_invalid")
            self.assertNotEqual(result.code, "lifecycle_authority_mismatch")

            # attempt_id
            req = _lifecycle_request(trusted_root=root, plan=plan)
            req["cleanup_handoff"]["attempt_id"] = _hex64("other-attempt")  # type: ignore[index]
            self.assertEqual(
                life.run_disposable_sandbox_lifecycle_json(_wire(req)).code,
                "stage_binding_invalid",
            )

            # not_after_unix freshness
            req = _lifecycle_request(trusted_root=root, plan=plan)
            req["cleanup_handoff"]["not_after_unix"] = int(time.time()) + 99999  # type: ignore[index]
            self.assertEqual(
                life.run_disposable_sandbox_lifecycle_json(_wire(req)).code,
                "stage_binding_invalid",
            )

            # lifecycle authority trusted_root ≠ nested trusted_root
            bind = _lifecycle_request(trusted_root=root, plan=plan)
            bind["lifecycle_authority"]["trusted_root"] = root + "/other"  # type: ignore[index]
            self.assertEqual(
                life.run_disposable_sandbox_lifecycle_json(_wire(bind)).code,
                "stage_binding_invalid",
            )

    def test_malformed_attempt_id_before_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            plan = _plan()
            result = life.run_disposable_sandbox_lifecycle_json(
                _wire(
                    _lifecycle_request(
                        trusted_root=root,
                        plan=plan,
                        lifecycle_authority={
                            "lifecycle_authorized": True,
                            "trusted_root": root,
                            "sandbox_instance_id": plan["sandbox_instance_id"],
                            "data_dir_tag": identity.DATA_DIR_TAG,
                            "attempt_id": "ZZ",
                            "not_after_unix": int(time.time()) + 3600,
                        },
                    )
                )
            )
            self.assertEqual(result.code, "lifecycle_authority_invalid")
            self.assertNotEqual(result.code, "stage_binding_invalid")

    def test_materialize_stage_failed_echoes_f51(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            result = life.run_disposable_sandbox_lifecycle_json(
                _wire(_lifecycle_request(trusted_root=root, plan=_plan(code="nope")))
            )
            self.assertEqual(result.code, "materialization_stage_failed")
            self.assertEqual(result.failed_stage, "materialize")
            self.assertEqual(result.stage_code, "plan_evidence_invalid")

    def test_identity_verify_target_absent_without_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            cleanup_calls, wrapped_cleanup = _counting_cleanup()

            def remove_target(result: object) -> None:
                os.rmdir(result.materialization_path)  # type: ignore[attr-defined]

            with mock.patch.object(
                life,
                "materialize_disposable_sandbox_directory_json",
                side_effect=_mat_ok_then(remove_target),
            ):
                with mock.patch.object(
                    life,
                    "cleanup_disposable_sandbox_directory_json",
                    side_effect=wrapped_cleanup,
                ):
                    result = life.run_disposable_sandbox_lifecycle_json(
                        _wire(
                            _lifecycle_request(
                                trusted_root=root,
                                plan=_plan(sandbox_instance_id=_hex64("abs")),
                            )
                        )
                    )
            self.assertEqual(result.code, "identity_verify_target_absent")
            self.assertEqual(result.failed_stage, "identity_verify")
            self.assertEqual(cleanup_calls["n"], 0)
            self.assertNotEqual(result.materialization_report_id, "")

    def test_identity_verify_symlink_rejected_without_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            cleanup_calls, wrapped_cleanup = _counting_cleanup()

            def make_symlink(result: object) -> None:
                path = result.materialization_path  # type: ignore[attr-defined]
                os.rmdir(path)
                os.symlink(root, path)

            with mock.patch.object(
                life,
                "materialize_disposable_sandbox_directory_json",
                side_effect=_mat_ok_then(make_symlink),
            ):
                with mock.patch.object(
                    life,
                    "cleanup_disposable_sandbox_directory_json",
                    side_effect=wrapped_cleanup,
                ):
                    result = life.run_disposable_sandbox_lifecycle_json(
                        _wire(
                            _lifecycle_request(
                                trusted_root=root,
                                plan=_plan(sandbox_instance_id=_hex64("sym")),
                            )
                        )
                    )
            self.assertEqual(result.code, "identity_verify_symlink_rejected")
            self.assertEqual(result.failed_stage, "identity_verify")
            self.assertEqual(cleanup_calls["n"], 0)
            self.assertTrue(os.path.lexists(result.materialization_path))

    def test_identity_verify_mismatch_without_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            cleanup_calls, wrapped_cleanup = _counting_cleanup()

            def make_file(result: object) -> None:
                path = result.materialization_path  # type: ignore[attr-defined]
                os.rmdir(path)
                with open(path, "wb") as handle:
                    handle.write(b"x")

            with mock.patch.object(
                life,
                "materialize_disposable_sandbox_directory_json",
                side_effect=_mat_ok_then(make_file),
            ):
                with mock.patch.object(
                    life,
                    "cleanup_disposable_sandbox_directory_json",
                    side_effect=wrapped_cleanup,
                ):
                    result = life.run_disposable_sandbox_lifecycle_json(
                        _wire(
                            _lifecycle_request(
                                trusted_root=root,
                                plan=_plan(sandbox_instance_id=_hex64("mis")),
                            )
                        )
                    )
            self.assertEqual(result.code, "identity_verify_mismatch")
            self.assertEqual(result.failed_stage, "identity_verify")
            self.assertEqual(cleanup_calls["n"], 0)
            self.assertTrue(os.path.exists(result.materialization_path))

    def test_identity_verify_containment_failure_without_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            cleanup_calls, wrapped_cleanup = _counting_cleanup()

            def inode_swap(result: object) -> None:
                child_name = result.child_name  # type: ignore[attr-defined]
                path = result.materialization_path  # type: ignore[attr-defined]
                old = root + ".old"
                os.rename(root, old)
                os.mkdir(root)
                os.rename(os.path.join(old, child_name), path)

            with mock.patch.object(
                life,
                "materialize_disposable_sandbox_directory_json",
                side_effect=_mat_ok_then(inode_swap),
            ):
                with mock.patch.object(
                    life,
                    "cleanup_disposable_sandbox_directory_json",
                    side_effect=wrapped_cleanup,
                ):
                    result = life.run_disposable_sandbox_lifecycle_json(
                        _wire(
                            _lifecycle_request(
                                trusted_root=root,
                                plan=_plan(sandbox_instance_id=_hex64("cont")),
                            )
                        )
                    )
            self.assertEqual(result.code, "identity_verify_containment_failure")
            self.assertEqual(result.failed_stage, "identity_verify")
            self.assertEqual(cleanup_calls["n"], 0)
            self.assertTrue(os.path.isdir(result.materialization_path))

    def test_identity_verify_substitution_ambiguous_without_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            cleanup_calls, wrapped_cleanup = _counting_cleanup()
            target_path: dict[str, str] = {}
            real_lstat = os.lstat

            def capture_path(result: object) -> None:
                target_path["path"] = result.materialization_path  # type: ignore[attr-defined]

            def lstat_skew(path: str | bytes | os.PathLike[str]) -> os.stat_result:
                st = real_lstat(path)
                captured = target_path.get("path")
                if captured and os.path.abspath(str(path)) == os.path.abspath(captured):
                    return os.stat_result(
                        (
                            st.st_mode,
                            st.st_ino,
                            st.st_dev + 1,
                            st.st_nlink,
                            st.st_uid,
                            st.st_gid,
                            st.st_size,
                            st.st_atime,
                            st.st_mtime,
                            st.st_ctime,
                        )
                    )
                return st

            with mock.patch.object(
                life,
                "materialize_disposable_sandbox_directory_json",
                side_effect=_mat_ok_then(capture_path),
            ):
                with mock.patch.object(
                    life,
                    "cleanup_disposable_sandbox_directory_json",
                    side_effect=wrapped_cleanup,
                ):
                    with mock.patch.object(life.os, "lstat", side_effect=lstat_skew):
                        result = life.run_disposable_sandbox_lifecycle_json(
                            _wire(
                                _lifecycle_request(
                                    trusted_root=root,
                                    plan=_plan(sandbox_instance_id=_hex64("sub")),
                                )
                            )
                        )
            self.assertEqual(result.code, "identity_verify_substitution_ambiguous")
            self.assertEqual(result.failed_stage, "identity_verify")
            self.assertEqual(cleanup_calls["n"], 0)
            self.assertTrue(os.path.isdir(result.materialization_path))

    def test_post_lifecycle_verification_failed_real_post_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            real_cleanup = clean.cleanup_disposable_sandbox_directory_json
            paths: dict[str, str] = {}

            def mat_capture(payload: str | bytes) -> object:
                result = mat.materialize_disposable_sandbox_directory_json(payload)
                if result.code == "materialization_ok":
                    paths["path"] = result.materialization_path
                return result

            def cleanup_ok_then_recreate(payload: str | bytes) -> object:
                result = real_cleanup(payload)
                self.assertEqual(result.code, "cleanup_ok")
                os.mkdir(paths["path"])
                return result

            with mock.patch.object(
                life,
                "materialize_disposable_sandbox_directory_json",
                side_effect=mat_capture,
            ):
                with mock.patch.object(
                    life,
                    "cleanup_disposable_sandbox_directory_json",
                    side_effect=cleanup_ok_then_recreate,
                ):
                    result = life.run_disposable_sandbox_lifecycle_json(
                        _wire(
                            _lifecycle_request(
                                trusted_root=root,
                                plan=_plan(sandbox_instance_id=_hex64("post")),
                            )
                        )
                    )
            self.assertEqual(result.code, "post_lifecycle_verification_failed")
            self.assertEqual(result.failed_stage, "cleanup")
            self.assertEqual(result.stage_code, "")

    def test_lifecycle_partial_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)

            def fail_cleanup(payload: str | bytes) -> object:
                class _R:
                    ok = False
                    code = "exclusive_cleanup_failed"
                    report_id = ""

                return _R()

            with mock.patch.object(
                life,
                "cleanup_disposable_sandbox_directory_json",
                side_effect=fail_cleanup,
            ):
                result = life.run_disposable_sandbox_lifecycle_json(
                    _wire(_lifecycle_request(trusted_root=root))
                )
            self.assertEqual(result.code, "lifecycle_partial_failed")
            self.assertEqual(result.failed_stage, "cleanup")
            self.assertEqual(result.stage_code, "exclusive_cleanup_failed")
            self.assertNotEqual(result.materialization_path, "")
            self.assertTrue(os.path.isdir(result.materialization_path))


class InventoryAndHygieneTests(unittest.TestCase):
    def test_all_stable_codes_reachable(self) -> None:
        observed: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)

            def add(code: str, payload: object, *, raw: bool = False) -> None:
                if raw or isinstance(payload, (bytes, bytearray)):
                    result = life.run_disposable_sandbox_lifecycle_json(payload)  # type: ignore[arg-type]
                else:
                    result = life.run_disposable_sandbox_lifecycle_json(_wire(payload))
                self.assertEqual(result.code, code, msg=result.code)
                self.assertIs(result.execution_authorized, False)
                self.assertIs(result.process_launch_authorized, False)
                self.assertEqual(result.detail, "")
                if code == "lifecycle_ok":
                    self.assertNotEqual(result.report_id, "")
                else:
                    self.assertEqual(result.report_id, "")
                observed.append(code)

            add("input_type_invalid", 1, raw=True)
            add("input_too_large", b"{" + b"a" * 20000 + b"}")
            add("encoding_invalid", b"\xff")
            add("json_invalid", b"{")
            add("duplicate_key", b'{"a":1,"a":2}')
            add("invalid_top_level", b"[]")
            bad = _lifecycle_request(trusted_root=root)
            del bad["environment"]
            add("schema_invalid", bad)
            add(
                "lifecycle_profile_unsupported",
                _lifecycle_request(trusted_root=root, lifecycle_profile="nope"),
            )
            add(
                "historical_import_forbidden",
                _lifecycle_request(trusted_root=root, environment="PRODUCTION"),
            )
            add(
                "environment_invalid",
                _lifecycle_request(trusted_root=root, environment="OTHER"),
            )
            add(
                "execution_authorized_invalid",
                _lifecycle_request(trusted_root=root, execution_authorized=True),
            )
            add(
                "process_launch_authorized_invalid",
                _lifecycle_request(
                    trusted_root=root, process_launch_authorized=True
                ),
            )
            forbid = _lifecycle_request(trusted_root=root)
            forbid["ledger_authorized"] = True  # type: ignore[index]
            add("schema_invalid", forbid)

            plan = _plan()
            add(
                "lifecycle_authority_invalid",
                _lifecycle_request(
                    trusted_root=root,
                    plan=plan,
                    lifecycle_authority={
                        "lifecycle_authorized": False,
                        "trusted_root": root,
                        "sandbox_instance_id": plan["sandbox_instance_id"],
                        "data_dir_tag": identity.DATA_DIR_TAG,
                        "attempt_id": _hex64("a"),
                        "not_after_unix": int(time.time()) + 3600,
                    },
                ),
            )
            # Malformed attempt_id (non-hex) before binding evaluation
            add(
                "lifecycle_authority_invalid",
                _lifecycle_request(
                    trusted_root=root,
                    plan=plan,
                    lifecycle_authority={
                        "lifecycle_authorized": True,
                        "trusted_root": root,
                        "sandbox_instance_id": plan["sandbox_instance_id"],
                        "data_dir_tag": identity.DATA_DIR_TAG,
                        "attempt_id": "ZZ",
                        "not_after_unix": int(time.time()) + 3600,
                    },
                ),
            )
            add(
                "lifecycle_authority_mismatch",
                _lifecycle_request(
                    trusted_root=root,
                    plan=plan,
                    lifecycle_authority={
                        "lifecycle_authorized": True,
                        "trusted_root": root,
                        "sandbox_instance_id": plan["sandbox_instance_id"],
                        "data_dir_tag": "not-the-tag",
                        "attempt_id": _hex64("a2"),
                        "not_after_unix": int(time.time()) + 3600,
                    },
                    attempt_id=_hex64("a2"),
                ),
            )
            add(
                "lifecycle_authority_expired",
                _lifecycle_request(trusted_root=root, not_after_unix=1),
            )

            # materialization_request_invalid: wrong field order
            bad_mat = _lifecycle_request(trusted_root=root)
            mr = bad_mat["materialization_request"]
            bad_mat["materialization_request"] = {  # type: ignore[index]
                "environment": mr["environment"],
                "materialization_profile": mr["materialization_profile"],
                "plan_evidence": mr["plan_evidence"],
                "materialization_authority": mr["materialization_authority"],
                "trusted_root": mr["trusted_root"],
                "execution_authorized": False,
                "process_launch_authorized": False,
            }
            add("materialization_request_invalid", bad_mat)

            # nested trusted_root lexical after shape
            bad_lex = _lifecycle_request(trusted_root=root)
            bad_lex["materialization_request"]["trusted_root"] = "~/x"  # type: ignore[index]
            # also fix authority to match so we pass earlier binds... shape ok, lexical fails
            # lifecycle authority still has root - but step 15 is nested lexical before binds
            add("materialization_request_invalid", bad_lex)

            add(
                "cleanup_handoff_invalid",
                _lifecycle_request(
                    trusted_root=root,
                    plan=plan,
                    cleanup_handoff={
                        "cleanup_authorized": False,
                        "trusted_root": root,
                        "sandbox_instance_id": plan["sandbox_instance_id"],
                        "data_dir_tag": identity.DATA_DIR_TAG,
                        "attempt_id": _hex64("h"),
                        "not_after_unix": int(time.time()) + 3600,
                    },
                ),
            )
            add(
                "process_stop_evidence_invalid",
                _lifecycle_request(
                    trusted_root=root,
                    process_stop_evidence={"mode": "bogus"},
                ),
            )
            add(
                "stopped_mode_forbidden",
                _lifecycle_request(
                    trusted_root=root,
                    plan=plan,
                    process_stop_evidence={
                        "mode": "stopped",
                        "sandbox_instance_id": plan["sandbox_instance_id"],
                        "listeners_cleared": True,
                        "stop_report_id": _hex64("s"),
                    },
                ),
            )

            # §6.4 binds — every bound field (never lifecycle_authority_mismatch)
            for mutate in (
                lambda r: r["cleanup_handoff"].__setitem__("trusted_root", root + "z"),
                lambda r: r["cleanup_handoff"].__setitem__(
                    "sandbox_instance_id", _hex64("bind-inst")
                ),
                lambda r: r["cleanup_handoff"].__setitem__(
                    "data_dir_tag", "l28-disposable-testX"
                ),
                lambda r: r["cleanup_handoff"].__setitem__(
                    "attempt_id", _hex64("bind-attempt")
                ),
                lambda r: r["cleanup_handoff"].__setitem__(
                    "not_after_unix", int(time.time()) + 99999
                ),
            ):
                bind_req = _lifecycle_request(trusted_root=root, plan=plan)
                mutate(bind_req)
                add("stage_binding_invalid", bind_req)

            bind_root = _lifecycle_request(trusted_root=root, plan=plan)
            bind_root["lifecycle_authority"]["trusted_root"] = root + "/other"  # type: ignore[index]
            add("stage_binding_invalid", bind_root)

            add(
                "materialization_stage_failed",
                _lifecycle_request(trusted_root=root, plan=_plan(code="nope")),
            )

            def add_identity(
                code: str,
                mutator,
                *,
                instance_seed: str,
                lstat_side_effect=None,
            ) -> None:
                cleanup_calls, wrapped_cleanup = _counting_cleanup()
                patches = [
                    mock.patch.object(
                        life,
                        "materialize_disposable_sandbox_directory_json",
                        side_effect=_mat_ok_then(mutator),
                    ),
                    mock.patch.object(
                        life,
                        "cleanup_disposable_sandbox_directory_json",
                        side_effect=wrapped_cleanup,
                    ),
                ]
                if lstat_side_effect is not None:
                    patches.append(
                        mock.patch.object(
                            life.os, "lstat", side_effect=lstat_side_effect
                        )
                    )
                with patches[0], patches[1]:
                    ctx = (
                        patches[2]
                        if lstat_side_effect is not None
                        else contextlib.nullcontext()
                    )
                    with ctx:
                        result = life.run_disposable_sandbox_lifecycle_json(
                            _wire(
                                _lifecycle_request(
                                    trusted_root=root,
                                    plan=_plan(
                                        sandbox_instance_id=_hex64(instance_seed)
                                    ),
                                )
                            )
                        )
                self.assertEqual(result.code, code, msg=result.code)
                self.assertEqual(result.failed_stage, "identity_verify")
                self.assertEqual(cleanup_calls["n"], 0)
                self.assertIs(result.execution_authorized, False)
                self.assertIs(result.process_launch_authorized, False)
                self.assertEqual(result.detail, "")
                self.assertEqual(result.report_id, "")
                observed.append(code)

            def remove_target(result: object) -> None:
                os.rmdir(result.materialization_path)  # type: ignore[attr-defined]

            add_identity(
                "identity_verify_target_absent",
                remove_target,
                instance_seed="abs",
            )

            def make_symlink(result: object) -> None:
                path = result.materialization_path  # type: ignore[attr-defined]
                os.rmdir(path)
                os.symlink(root, path)

            add_identity(
                "identity_verify_symlink_rejected",
                make_symlink,
                instance_seed="sym",
            )

            def make_file(result: object) -> None:
                path = result.materialization_path  # type: ignore[attr-defined]
                os.rmdir(path)
                with open(path, "wb") as handle:
                    handle.write(b"x")

            add_identity(
                "identity_verify_mismatch",
                make_file,
                instance_seed="mis",
            )

            def inode_swap(result: object) -> None:
                child_name = result.child_name  # type: ignore[attr-defined]
                path = result.materialization_path  # type: ignore[attr-defined]
                old = root + ".old"
                os.rename(root, old)
                os.mkdir(root)
                os.rename(os.path.join(old, child_name), path)

            add_identity(
                "identity_verify_containment_failure",
                inode_swap,
                instance_seed="cont",
            )

            target_path: dict[str, str] = {}
            real_lstat = os.lstat

            def capture_path(result: object) -> None:
                target_path["path"] = result.materialization_path  # type: ignore[attr-defined]

            def lstat_skew(path: str | bytes | os.PathLike[str]) -> os.stat_result:
                st = real_lstat(path)
                captured = target_path.get("path")
                if captured and os.path.abspath(str(path)) == os.path.abspath(captured):
                    return os.stat_result(
                        (
                            st.st_mode,
                            st.st_ino,
                            st.st_dev + 1,
                            st.st_nlink,
                            st.st_uid,
                            st.st_gid,
                            st.st_size,
                            st.st_atime,
                            st.st_mtime,
                            st.st_ctime,
                        )
                    )
                return st

            add_identity(
                "identity_verify_substitution_ambiguous",
                capture_path,
                instance_seed="sub",
                lstat_side_effect=lstat_skew,
            )

            # cleanup_stage_failed: _wire fails only on cleanup construction
            calls = {"n": 0}
            real_wire = life._wire

            def wire_flaky(value: object) -> bytes:
                calls["n"] += 1
                if calls["n"] >= 2:
                    raise TypeError("cannot serialize")
                return real_wire(value)  # type: ignore[arg-type]

            with mock.patch.object(life, "_wire", side_effect=wire_flaky):
                add(
                    "cleanup_stage_failed",
                    _lifecycle_request(
                        trusted_root=root,
                        plan=_plan(sandbox_instance_id=_hex64("csf2")),
                    ),
                )

            class _FailClean:
                ok = False
                code = "cleanup_partial_failed"
                report_id = ""

            with mock.patch.object(
                life,
                "cleanup_disposable_sandbox_directory_json",
                return_value=_FailClean(),
            ):
                add(
                    "lifecycle_partial_failed",
                    _lifecycle_request(
                        trusted_root=root,
                        plan=_plan(sandbox_instance_id=_hex64("part")),
                    ),
                )

            # post_lifecycle via real §13 check after cleanup_ok + recreated target
            paths: dict[str, str] = {}
            real_cleanup = clean.cleanup_disposable_sandbox_directory_json

            def mat_capture(payload: str | bytes) -> object:
                result = mat.materialize_disposable_sandbox_directory_json(payload)
                if result.code == "materialization_ok":
                    paths["path"] = result.materialization_path
                return result

            def cleanup_ok_then_recreate(payload: str | bytes) -> object:
                result = real_cleanup(payload)
                self.assertEqual(result.code, "cleanup_ok")
                os.mkdir(paths["path"])
                return result

            with mock.patch.object(
                life,
                "materialize_disposable_sandbox_directory_json",
                side_effect=mat_capture,
            ):
                with mock.patch.object(
                    life,
                    "cleanup_disposable_sandbox_directory_json",
                    side_effect=cleanup_ok_then_recreate,
                ):
                    result = life.run_disposable_sandbox_lifecycle_json(
                        _wire(
                            _lifecycle_request(
                                trusted_root=root,
                                plan=_plan(sandbox_instance_id=_hex64("post")),
                            )
                        )
                    )
            self.assertEqual(result.code, "post_lifecycle_verification_failed")
            self.assertEqual(result.failed_stage, "cleanup")
            self.assertEqual(result.stage_code, "")
            self.assertEqual(result.report_id, "")
            self.assertEqual(result.detail, "")
            observed.append("post_lifecycle_verification_failed")

            with mock.patch.object(
                life, "_evaluate_parsed", side_effect=RuntimeError("boom")
            ):
                add("internal_error", _lifecycle_request(trusted_root=root))

            add(
                "lifecycle_ok",
                _lifecycle_request(
                    trusted_root=root,
                    plan=_plan(sandbox_instance_id=_hex64("okfinal")),
                ),
            )

        self.assertEqual(len(life.STABLE_CODES), 31)
        self.assertEqual(len(set(life.STABLE_CODES)), 31)
        missing = set(life.STABLE_CODES) - set(observed)
        self.assertEqual(missing, set(), msg=f"missing={missing} observed={observed}")

    def test_module_static_hygiene(self) -> None:
        src = Path(life.__file__).read_text(encoding="utf-8")
        for bad in (
            "Leap28",
            "Nova",
            "import shutil",
            "rmtree",
            "subprocess",
            "socket",
            "os.environ",
            "os.getenv",
            "pathlib",
        ):
            self.assertNotIn(bad, src)
        self.assertIn("materialize_disposable_sandbox_directory_json", src)
        self.assertIn("cleanup_disposable_sandbox_directory_json", src)
        tree = ast.parse(src)
        modules = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        ]
        self.assertIn("disposable_sandbox_directory_materialization", " ".join(modules))
        self.assertIn("disposable_sandbox_directory_cleanup", " ".join(modules))

    def test_economics_unchanged(self) -> None:
        self.assertEqual(tx_validation.L28_MAX_SUPPLY, 28_000_000)
        self.assertEqual(tx_validation.L28_EMISSION_CEILING, 11_130_000)
        self.assertEqual(tx_validation.L28_REWARD_SCHEDULE, (28, 14, 7, 3, 1))


if __name__ == "__main__":
    unittest.main()
