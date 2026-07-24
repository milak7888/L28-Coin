# SPDX-License-Identifier: Apache-2.0
"""Foundation 53 disposable sandbox directory cleanup tests."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import stat
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from coin import disposable_network_identity_genesis_binding as identity
from coin import disposable_sandbox_directory_cleanup as clean
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


def _evidence(
    *,
    trusted_root: str,
    sandbox_instance_id: str | None = None,
    report_id: str | None = None,
    **overrides: object,
) -> dict[str, object]:
    instance = sandbox_instance_id or _hex64("cleanup-instance")
    if instance[0] == "0" and sandbox_instance_id is None:
        instance = "a" + instance[1:]
    child = f"{identity.DATA_DIR_TAG}-{instance}"
    path = f"{trusted_root}/{child}" if trusted_root != "/" else f"/{child}"
    base: dict[str, object] = {
        "ok": True,
        "code": "materialization_ok",
        "materialization_profile": clean.MATERIALIZATION_PROFILE,
        "environment": identity.ENVIRONMENT,
        "network_id": identity.NETWORK_ID,
        "chain_id": _hex64("chain"),
        "genesis_digest": _hex64("genesis"),
        "protocol_version": identity.PROTOCOL_VERSION,
        "plan_report_id": _hex64("plan"),
        "sandbox_instance_id": instance,
        "data_dir_tag": identity.DATA_DIR_TAG,
        "path_lexeme": "/correlation-only",
        "child_name": child,
        "materialization_path": path,
        "materialization_ok": True,
        "process_launch_authorized": False,
        "execution_authorized": False,
        "report_id": report_id or _hex64(f"mat:{instance}"),
        "detail": "",
    }
    base.update(overrides)
    return base


def _authority(
    *,
    trusted_root: str,
    evidence: dict[str, object],
    cleanup_authorized: object = True,
    attempt_id: str | None = None,
    not_after_unix: object | None = None,
    **overrides: object,
) -> dict[str, object]:
    base: dict[str, object] = {
        "cleanup_authorized": cleanup_authorized,
        "trusted_root": trusted_root,
        "sandbox_instance_id": evidence["sandbox_instance_id"],
        "data_dir_tag": identity.DATA_DIR_TAG,
        "materialization_report_id": evidence["report_id"],
        "attempt_id": attempt_id or _hex64("attempt"),
        "not_after_unix": not_after_unix
        if not_after_unix is not None
        else int(time.time()) + 3600,
    }
    base.update(overrides)
    return base


def _stop(
    evidence: dict[str, object],
    *,
    mode: str = "never_started",
) -> dict[str, object]:
    if mode == "never_started":
        return {
            "mode": "never_started",
            "sandbox_instance_id": evidence["sandbox_instance_id"],
        }
    return {
        "mode": "stopped",
        "sandbox_instance_id": evidence["sandbox_instance_id"],
        "listeners_cleared": True,
        "stop_report_id": _hex64("stop"),
    }


def _request(
    *,
    trusted_root: str,
    evidence: dict[str, object] | None = None,
    authority: dict[str, object] | None = None,
    process_stop_evidence: dict[str, object] | None = None,
    environment: str = "DISPOSABLE_TEST",
    cleanup_profile: str = clean.PROFILE,
    execution_authorized: object = False,
    process_launch_authorized: object = False,
) -> dict[str, object]:
    ev = evidence if evidence is not None else _evidence(trusted_root=trusted_root)
    return {
        "cleanup_profile": cleanup_profile,
        "environment": environment,
        "materialization_evidence": ev,
        "cleanup_authority": authority
        if authority is not None
        else _authority(trusted_root=trusted_root, evidence=ev),
        "process_stop_evidence": process_stop_evidence
        if process_stop_evidence is not None
        else _stop(ev),
        "trusted_root": trusted_root,
        "execution_authorized": execution_authorized,
        "process_launch_authorized": process_launch_authorized,
    }


def _ensure_target(evidence: dict[str, object], *, with_file: bool = False) -> None:
    path = str(evidence["materialization_path"])
    os.makedirs(path, mode=0o700, exist_ok=True)
    os.chmod(path, 0o700)
    if with_file:
        fp = os.path.join(path, "ledger.bin")
        with open(fp, "wb") as handle:
            handle.write(b"x")


class SuccessPathTests(unittest.TestCase):
    def test_cleanup_ok_empty_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            ev = _evidence(trusted_root=root)
            _ensure_target(ev)
            raw = _wire(_request(trusted_root=root, evidence=ev))
            result = clean.cleanup_disposable_sandbox_directory_json(raw)
            self.assertTrue(result.ok, result.code)
            self.assertEqual(result.code, "cleanup_ok")
            self.assertIs(result.cleanup_ok, True)
            self.assertIs(result.execution_authorized, False)
            self.assertIs(result.process_launch_authorized, False)
            self.assertEqual(result.detail, "")
            self.assertEqual(result.report_id, hashlib.sha256(raw).hexdigest())
            self.assertFalse(os.path.exists(str(ev["materialization_path"])))

    def test_cleanup_ok_with_nested_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            ev = _evidence(trusted_root=root, sandbox_instance_id=_hex64("nested"))
            _ensure_target(ev, with_file=True)
            result = clean.cleanup_disposable_sandbox_directory_json(
                _wire(_request(trusted_root=root, evidence=ev))
            )
            self.assertEqual(result.code, "cleanup_ok")
            self.assertFalse(os.path.exists(str(ev["materialization_path"])))

    def test_stopped_mode_and_immutability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            ev = _evidence(trusted_root=root)
            _ensure_target(ev)
            result = clean.cleanup_disposable_sandbox_directory_json(
                _wire(
                    _request(
                        trusted_root=root,
                        evidence=ev,
                        process_stop_evidence=_stop(ev, mode="stopped"),
                    )
                )
            )
            self.assertEqual(result.code, "cleanup_ok")
            with self.assertRaises(Exception):
                result.code = "x"  # type: ignore[misc]

    def test_report_id_is_content_derived(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            ev = _evidence(trusted_root=root, sandbox_instance_id=_hex64("rid"))
            _ensure_target(ev)
            raw = _wire(_request(trusted_root=root, evidence=ev))
            result = clean.cleanup_disposable_sandbox_directory_json(raw)
            self.assertEqual(result.code, "cleanup_ok")
            self.assertEqual(result.report_id, hashlib.sha256(raw).hexdigest())


class ParseAuthorityTests(unittest.TestCase):
    def test_parse_and_env_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(1).code,  # type: ignore[arg-type]
                "input_type_invalid",
            )
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(
                    b"{" + b"a" * 9000 + b"}"
                ).code,
                "input_too_large",
            )
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(b"\xff").code,
                "encoding_invalid",
            )
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(b"{").code,
                "json_invalid",
            )
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(b'{"a":1,"a":2}').code,
                "duplicate_key",
            )
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(b"[]").code,
                "invalid_top_level",
            )
            bad = _request(trusted_root=root)
            del bad["trusted_root"]
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(_wire(bad)).code,
                "schema_invalid",
            )
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, cleanup_profile="x"))
                ).code,
                "cleanup_profile_unsupported",
            )
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, environment="MAIN"))
                ).code,
                "historical_import_forbidden",
            )
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, environment="OTHER"))
                ).code,
                "environment_invalid",
            )
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, execution_authorized=True))
                ).code,
                "execution_authorized_invalid",
            )
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(
                    _wire(
                        _request(trusted_root=root, process_launch_authorized=True)
                    )
                ).code,
                "process_launch_authorized_invalid",
            )
            forbid = _request(trusted_root=root)
            forbid["wipe_authorized"] = True  # type: ignore[index]
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(_wire(forbid)).code,
                "schema_invalid",
            )

    def test_authority_and_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            ev = _evidence(trusted_root=root)
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(
                    _wire(
                        _request(
                            trusted_root=root,
                            evidence=ev,
                            authority=_authority(
                                trusted_root=root,
                                evidence=ev,
                                cleanup_authorized=False,
                            ),
                        )
                    )
                ).code,
                "cleanup_authority_invalid",
            )
            req = _request(trusted_root=root, evidence=ev)
            req["cleanup_authority"]["trusted_root"] = root + "z"  # type: ignore[index]
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(_wire(req)).code,
                "cleanup_authority_mismatch",
            )
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(
                    _wire(
                        _request(
                            trusted_root=root,
                            evidence=ev,
                            authority=_authority(
                                trusted_root=root,
                                evidence=ev,
                                not_after_unix=1,
                            ),
                        )
                    )
                ).code,
                "cleanup_authority_expired",
            )
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(
                    _wire(
                        _request(
                            trusted_root=root,
                            evidence=ev,
                            process_stop_evidence={"mode": "bogus"},
                        )
                    )
                ).code,
                "process_stop_evidence_invalid",
            )


class FsMatrixTests(unittest.TestCase):
    def test_target_absent_and_symlink_survey(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            ev = _evidence(trusted_root=root)
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, evidence=ev))
                ).code,
                "target_absent",
            )
            _ensure_target(ev)
            os.symlink(
                "somewhere",
                os.path.join(str(ev["materialization_path"]), "link"),
            )
            self.assertEqual(
                clean.cleanup_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, evidence=ev))
                ).code,
                "symlink_rejected",
            )

    def test_exclusive_and_partial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            ev = _evidence(trusted_root=root)
            _ensure_target(ev, with_file=True)
            with mock.patch.object(
                os, "unlink", side_effect=OSError(1, "eperm")
            ):
                self.assertEqual(
                    clean.cleanup_disposable_sandbox_directory_json(
                        _wire(_request(trusted_root=root, evidence=ev))
                    ).code,
                    "exclusive_cleanup_failed",
                )

        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            ev = _evidence(trusted_root=root)
            _ensure_target(ev, with_file=True)
            calls = {"n": 0}
            real_unlink = os.unlink

            def flaky_unlink(path: str) -> None:
                calls["n"] += 1
                if calls["n"] == 1:
                    real_unlink(path)
                    return
                raise OSError(1, "busy")

            with mock.patch.object(os, "unlink", side_effect=flaky_unlink):
                # only one file - first succeeds, then rmdir of target - need two files
                pass

        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            ev = _evidence(trusted_root=root)
            _ensure_target(ev)
            p = str(ev["materialization_path"])
            with open(os.path.join(p, "a"), "wb") as handle:
                handle.write(b"1")
            with open(os.path.join(p, "b"), "wb") as handle:
                handle.write(b"2")
            calls = {"n": 0}
            real_unlink = os.unlink

            def flaky(path: str) -> None:
                calls["n"] += 1
                if calls["n"] == 1:
                    real_unlink(path)
                    return
                raise OSError(1, "busy")

            with mock.patch.object(os, "unlink", side_effect=flaky):
                result = clean.cleanup_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, evidence=ev))
                )
            self.assertEqual(result.code, "cleanup_partial_failed")

    def test_post_cleanup_verification_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            ev = _evidence(trusted_root=root)
            _ensure_target(ev)
            real_lstat = os.lstat
            root_stat = os.lstat(root)

            def after_delete(path: str | bytes, *a: object, **k: object) -> os.stat_result:
                path_s = os.fsdecode(path)
                if path_s == root:
                    class _Fake:
                        st_mode = root_stat.st_mode
                        st_ino = root_stat.st_ino + 999
                        st_dev = root_stat.st_dev
                        st_uid = root_stat.st_uid
                        st_gid = root_stat.st_gid

                    # Only after target gone — detect via existence
                    target = str(ev["materialization_path"])
                    if not os.path.lexists(target):
                        return _Fake()  # type: ignore[return-value]
                return real_lstat(path)

            with mock.patch.object(os, "lstat", side_effect=after_delete):
                result = clean.cleanup_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, evidence=ev))
                )
            self.assertEqual(result.code, "post_cleanup_verification_failed")

    def test_tree_limit_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            ev = _evidence(trusted_root=root)
            _ensure_target(ev)
            with mock.patch.object(clean, "MAX_TREE_ENTRIES", 1):
                # target dir alone counts as 1; adding a file exceeds
                with open(
                    os.path.join(str(ev["materialization_path"]), "f"), "wb"
                ) as handle:
                    handle.write(b"1")
                result = clean.cleanup_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, evidence=ev))
                )
            self.assertEqual(result.code, "tree_limit_exceeded")


class ConcreteFirstFailureTests(unittest.TestCase):
    def test_zero_instance_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            zero = "0" * 64
            ev = _evidence(
                trusted_root=root,
                sandbox_instance_id=zero,
                child_name=f"{identity.DATA_DIR_TAG}-{zero}",
                materialization_path=f"{root}/{identity.DATA_DIR_TAG}-{zero}",
            )
            result = clean.cleanup_disposable_sandbox_directory_json(
                _wire(
                    _request(
                        trusted_root=root,
                        evidence=ev,
                        authority=_authority(trusted_root=root, evidence=ev),
                    )
                )
            )
            self.assertEqual(result.code, "materialization_evidence_invalid")

    def test_invalid_attempt_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            ev = _evidence(trusted_root=root)
            result = clean.cleanup_disposable_sandbox_directory_json(
                _wire(
                    _request(
                        trusted_root=root,
                        evidence=ev,
                        authority=_authority(
                            trusted_root=root, evidence=ev, attempt_id="not-hex-64"
                        ),
                    )
                )
            )
            self.assertEqual(result.code, "cleanup_authority_invalid")

    def test_tilde_home_and_env_roots(self) -> None:
        cases = ("~/sandbox", "$HOME/sandbox", "/tmp/${USER}/sandbox")
        for root in cases:
            with self.subTest(root=root):
                ev = _evidence(trusted_root=root)
                result = clean.cleanup_disposable_sandbox_directory_json(
                    _wire(
                        _request(
                            trusted_root=root,
                            evidence=ev,
                            authority=_authority(trusted_root=root, evidence=ev),
                        )
                    )
                )
                self.assertEqual(result.code, "trusted_root_invalid")

    def test_symlink_ancestry_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = _harness_root(tmp)
            real = os.path.join(base, "real")
            os.mkdir(real)
            link = os.path.join(base, "link")
            os.symlink(real, link)
            nested = os.path.join(link, "childroot")
            os.mkdir(nested)
            # Symlink appears in ancestry of nested trusted root.
            ev = _evidence(trusted_root=nested)
            _ensure_target(ev)
            result = clean.cleanup_disposable_sandbox_directory_json(
                _wire(
                    _request(
                        trusted_root=nested,
                        evidence=ev,
                        authority=_authority(trusted_root=nested, evidence=ev),
                    )
                )
            )
            self.assertEqual(result.code, "trusted_root_invalid")

    def test_traversal_rejected_via_derived_path_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            ev = _evidence(trusted_root=root, sandbox_instance_id=_hex64("trav"))
            _ensure_target(ev)
            real = clean._validate_derived_path

            def force_traversal(child_name: str, materialization_path: str) -> None:
                real("..", materialization_path)

            with mock.patch.object(
                clean, "_validate_derived_path", side_effect=force_traversal
            ):
                result = clean.cleanup_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, evidence=ev))
                )
            self.assertEqual(result.code, "traversal_rejected")
            self.assertTrue(os.path.isdir(str(ev["materialization_path"])))

    def test_containment_failure_via_parent_inode_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            ev = _evidence(trusted_root=root, sandbox_instance_id=_hex64("cont"))
            _ensure_target(ev)
            target = str(ev["materialization_path"])
            real_lstat = os.lstat
            real_vtr = clean._validate_trusted_root_filesystem
            fs_done = {"ok": False}

            def vtr(path: str) -> os.stat_result:
                st = real_vtr(path)
                fs_done["ok"] = True
                return st

            def lstat_side_effect(
                path: str | bytes, *args: object, **kwargs: object
            ) -> os.stat_result:
                path_s = os.fsdecode(path)
                if fs_done["ok"] and path_s == root and os.path.lexists(target):
                    base = real_lstat(root)

                    class _Fake:
                        st_mode = base.st_mode
                        st_ino = base.st_ino + 777
                        st_dev = base.st_dev
                        st_uid = base.st_uid
                        st_gid = base.st_gid

                    return _Fake()  # type: ignore[return-value]
                return real_lstat(path)

            with mock.patch.object(
                clean, "_validate_trusted_root_filesystem", side_effect=vtr
            ):
                with mock.patch.object(os, "lstat", side_effect=lstat_side_effect):
                    result = clean.cleanup_disposable_sandbox_directory_json(
                        _wire(_request(trusted_root=root, evidence=ev))
                    )
            self.assertEqual(result.code, "containment_failure")
            self.assertTrue(os.path.isdir(target))

    def test_untagged_or_protected_path_via_tagged_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            ev = _evidence(trusted_root=root, sandbox_instance_id=_hex64("untag"))
            _ensure_target(ev)
            real = clean._assert_tagged_disposable

            def force_untagged(
                child_name: str, materialization_path: str, trusted_root: str
            ) -> None:
                real("untagged-name", materialization_path, trusted_root)

            with mock.patch.object(
                clean, "_assert_tagged_disposable", side_effect=force_untagged
            ):
                result = clean.cleanup_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, evidence=ev))
                )
            self.assertEqual(result.code, "untagged_or_protected_path")
            self.assertTrue(os.path.isdir(str(ev["materialization_path"])))

    def test_path_lexeme_never_selects_delete_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            decoy = os.path.join(root, "decoy-should-survive")
            os.mkdir(decoy)
            marker = os.path.join(decoy, "keep.bin")
            with open(marker, "wb") as handle:
                handle.write(b"keep")
            ev = _evidence(
                trusted_root=root,
                sandbox_instance_id=_hex64("lexeme"),
                path_lexeme=decoy,
            )
            _ensure_target(ev, with_file=True)
            result = clean.cleanup_disposable_sandbox_directory_json(
                _wire(_request(trusted_root=root, evidence=ev))
            )
            self.assertEqual(result.code, "cleanup_ok")
            self.assertEqual(result.cleanup_path, str(ev["materialization_path"]))
            self.assertFalse(os.path.exists(str(ev["materialization_path"])))
            self.assertTrue(os.path.isdir(decoy))
            self.assertTrue(os.path.isfile(marker))

    def test_pre_delete_lstat_oserror_is_substitution_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            ev = _evidence(trusted_root=root, sandbox_instance_id=_hex64("ostat"))
            _ensure_target(ev)
            target = str(ev["materialization_path"])
            real_lstat = os.lstat

            def boom(path: str | bytes, *args: object, **kwargs: object) -> os.stat_result:
                if os.fsdecode(path) == target:
                    raise OSError(13, "eacces")
                return real_lstat(path)

            with mock.patch.object(os, "lstat", side_effect=boom):
                result = clean.cleanup_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, evidence=ev))
                )
            self.assertEqual(result.code, "substitution_ambiguous")


class InventoryAndHygieneTests(unittest.TestCase):
    def test_all_stable_codes_reachable(self) -> None:
        observed: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)

            def add(code: str, payload: object, *, raw: bool = False) -> None:
                if raw or isinstance(payload, (bytes, bytearray)):
                    result = clean.cleanup_disposable_sandbox_directory_json(payload)  # type: ignore[arg-type]
                elif isinstance(payload, str):
                    result = clean.cleanup_disposable_sandbox_directory_json(payload)
                else:
                    result = clean.cleanup_disposable_sandbox_directory_json(
                        _wire(payload)
                    )
                self.assertEqual(result.code, code, msg=result.code)
                self.assertIs(result.execution_authorized, False)
                self.assertIs(result.process_launch_authorized, False)
                if code == "cleanup_ok":
                    self.assertNotEqual(result.report_id, "")
                else:
                    self.assertEqual(result.report_id, "")
                    self.assertEqual(result.detail, "")
                observed.append(code)

            add("input_type_invalid", 1, raw=True)
            add("input_too_large", b"{" + b"a" * 9000 + b"}")
            add("encoding_invalid", b"\xff")
            add("json_invalid", b"{")
            add("duplicate_key", b'{"a":1,"a":2}')
            add("invalid_top_level", b"[]")
            bad = _request(trusted_root=root)
            del bad["environment"]
            add("schema_invalid", bad)
            add(
                "cleanup_profile_unsupported",
                _request(trusted_root=root, cleanup_profile="nope"),
            )
            add(
                "historical_import_forbidden",
                _request(trusted_root=root, environment="PRODUCTION"),
            )
            add(
                "environment_invalid",
                _request(trusted_root=root, environment="OTHER"),
            )
            add(
                "execution_authorized_invalid",
                _request(trusted_root=root, execution_authorized=True),
            )
            add(
                "process_launch_authorized_invalid",
                _request(trusted_root=root, process_launch_authorized=True),
            )
            forbid = _request(trusted_root=root)
            forbid["ledger_authorized"] = True  # type: ignore[index]
            add("schema_invalid", forbid)

            ev = _evidence(trusted_root=root)
            add(
                "cleanup_authority_invalid",
                _request(
                    trusted_root=root,
                    evidence=ev,
                    authority=_authority(
                        trusted_root=root, evidence=ev, cleanup_authorized=False
                    ),
                ),
            )
            req_mis = _request(trusted_root=root, evidence=ev)
            req_mis["cleanup_authority"]["trusted_root"] = root + "z"  # type: ignore[index]
            add("cleanup_authority_mismatch", req_mis)
            add(
                "cleanup_authority_expired",
                _request(
                    trusted_root=root,
                    evidence=ev,
                    authority=_authority(
                        trusted_root=root, evidence=ev, not_after_unix=1
                    ),
                ),
            )
            add(
                "process_stop_evidence_invalid",
                _request(
                    trusted_root=root,
                    evidence=ev,
                    process_stop_evidence={"mode": "x"},
                ),
            )
            add(
                "materialization_evidence_invalid",
                _request(
                    trusted_root=root,
                    evidence=_evidence(trusted_root=root, code="nope"),
                ),
            )
            add(
                "trusted_root_invalid",
                _request(
                    trusted_root="relative",
                    evidence=_evidence(trusted_root="relative"),
                    authority=_authority(
                        trusted_root="relative",
                        evidence=_evidence(trusted_root="relative"),
                    ),
                ),
            )

            ev2 = _evidence(trusted_root=root, sandbox_instance_id=_hex64("id2"))
            bad_path = dict(ev2)
            bad_path["materialization_path"] = root + "/wrong-name"
            add(
                "target_identity_invalid",
                _request(trusted_root=root, evidence=bad_path),  # type: ignore[arg-type]
            )

            ev_s = _evidence(trusted_root=root, sandbox_instance_id=_hex64("sym"))
            _ensure_target(ev_s)
            os.symlink("x", os.path.join(str(ev_s["materialization_path"]), "l"))
            add("symlink_rejected", _request(trusted_root=root, evidence=ev_s))

            ev_sub = _evidence(trusted_root=root, sandbox_instance_id=_hex64("sub"))
            _ensure_target(ev_sub)
            target_sub = str(ev_sub["materialization_path"])
            real_lstat = os.lstat

            def pre_lstat_oserror(
                path: str | bytes, *a: object, **k: object
            ) -> os.stat_result:
                if os.fsdecode(path) == target_sub:
                    raise OSError(13, "eacces")
                return real_lstat(path)

            with mock.patch.object(os, "lstat", side_effect=pre_lstat_oserror):
                add("substitution_ambiguous", _request(trusted_root=root, evidence=ev_sub))

            ev_abs = _evidence(trusted_root=root, sandbox_instance_id=_hex64("abs"))
            add("target_absent", _request(trusted_root=root, evidence=ev_abs))

            ev_lim = _evidence(trusted_root=root, sandbox_instance_id=_hex64("lim"))
            _ensure_target(ev_lim)
            with open(os.path.join(str(ev_lim["materialization_path"]), "f"), "wb") as h:
                h.write(b"1")
            with mock.patch.object(clean, "MAX_TREE_ENTRIES", 1):
                add("tree_limit_exceeded", _request(trusted_root=root, evidence=ev_lim))

            ev_ex = _evidence(trusted_root=root, sandbox_instance_id=_hex64("ex"))
            _ensure_target(ev_ex, with_file=True)
            with mock.patch.object(os, "unlink", side_effect=OSError(1, "eperm")):
                add("exclusive_cleanup_failed", _request(trusted_root=root, evidence=ev_ex))

            ev_part = _evidence(trusted_root=root, sandbox_instance_id=_hex64("part"))
            _ensure_target(ev_part)
            p = str(ev_part["materialization_path"])
            with open(os.path.join(p, "a"), "wb") as h:
                h.write(b"1")
            with open(os.path.join(p, "b"), "wb") as h:
                h.write(b"2")
            calls = {"n": 0}
            real_unlink = os.unlink

            def flaky(path: str) -> None:
                calls["n"] += 1
                if calls["n"] == 1:
                    real_unlink(path)
                    return
                raise OSError(1, "busy")

            with mock.patch.object(os, "unlink", side_effect=flaky):
                add("cleanup_partial_failed", _request(trusted_root=root, evidence=ev_part))

            ev_post = _evidence(trusted_root=root, sandbox_instance_id=_hex64("post"))
            _ensure_target(ev_post)
            root_stat = os.lstat(root)

            def after(path: str | bytes, *a: object, **k: object) -> os.stat_result:
                path_s = os.fsdecode(path)
                target = str(ev_post["materialization_path"])
                if path_s == root and not os.path.lexists(target):
                    class _Fake:
                        st_mode = root_stat.st_mode
                        st_ino = root_stat.st_ino + 1
                        st_dev = root_stat.st_dev
                        st_uid = root_stat.st_uid
                        st_gid = root_stat.st_gid

                    return _Fake()  # type: ignore[return-value]
                return real_lstat(path)

            with mock.patch.object(os, "lstat", side_effect=after):
                add(
                    "post_cleanup_verification_failed",
                    _request(trusted_root=root, evidence=ev_post),
                )

            with mock.patch.object(
                clean, "_evaluate_parsed", side_effect=RuntimeError("boom")
            ):
                add("internal_error", _request(trusted_root=root))

            # Defense-in-depth codes: exercise real helpers (not _evaluate_parsed).
            ev_tr = _evidence(trusted_root=root, sandbox_instance_id=_hex64("trav-inv"))
            _ensure_target(ev_tr)
            real_vdp = clean._validate_derived_path

            def force_traversal(child_name: str, materialization_path: str) -> None:
                real_vdp("..", materialization_path)

            with mock.patch.object(
                clean, "_validate_derived_path", side_effect=force_traversal
            ):
                add("traversal_rejected", _request(trusted_root=root, evidence=ev_tr))

            ev_cf = _evidence(trusted_root=root, sandbox_instance_id=_hex64("cont-inv"))
            _ensure_target(ev_cf)
            target_cf = str(ev_cf["materialization_path"])
            real_vtr = clean._validate_trusted_root_filesystem
            fs_done = {"ok": False}

            def vtr(path: str) -> os.stat_result:
                st = real_vtr(path)
                fs_done["ok"] = True
                return st

            def containment_lstat(
                path: str | bytes, *a: object, **k: object
            ) -> os.stat_result:
                path_s = os.fsdecode(path)
                if fs_done["ok"] and path_s == root and os.path.lexists(target_cf):
                    base = real_lstat(root)

                    class _Fake:
                        st_mode = base.st_mode
                        st_ino = base.st_ino + 4242
                        st_dev = base.st_dev
                        st_uid = base.st_uid
                        st_gid = base.st_gid

                    return _Fake()  # type: ignore[return-value]
                return real_lstat(path)

            with mock.patch.object(
                clean, "_validate_trusted_root_filesystem", side_effect=vtr
            ):
                with mock.patch.object(os, "lstat", side_effect=containment_lstat):
                    add(
                        "containment_failure",
                        _request(trusted_root=root, evidence=ev_cf),
                    )

            ev_ut = _evidence(trusted_root=root, sandbox_instance_id=_hex64("untag-inv"))
            _ensure_target(ev_ut)
            real_tag = clean._assert_tagged_disposable

            def force_untagged(
                child_name: str, materialization_path: str, trusted_root: str
            ) -> None:
                real_tag("untagged-name", materialization_path, trusted_root)

            with mock.patch.object(
                clean, "_assert_tagged_disposable", side_effect=force_untagged
            ):
                add(
                    "untagged_or_protected_path",
                    _request(trusted_root=root, evidence=ev_ut),
                )

            ev_ok = _evidence(trusted_root=root, sandbox_instance_id=_hex64("okfinal"))
            _ensure_target(ev_ok)
            add("cleanup_ok", _request(trusted_root=root, evidence=ev_ok))

        self.assertEqual(len(clean.STABLE_CODES), 31)
        self.assertEqual(len(set(clean.STABLE_CODES)), 31)
        self.assertEqual(set(observed), set(clean.STABLE_CODES))

    def test_module_static_hygiene(self) -> None:
        src = Path(clean.__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)
        from_mods: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                from_mods.append(node.module)
        joined = " ".join(from_mods)
        self.assertNotIn("disposable_sandbox_directory_materialization", joined)
        self.assertNotIn("disposable_sandbox_directory_creation", joined)
        for bad in (
            "Leap28",
            "Nova",
            "materialize_disposable_sandbox_directory_json",
            "import shutil",
            "rmtree",
            "subprocess",
            "socket",
            "os.environ",
            "os.getenv",
            "pathlib",
        ):
            self.assertNotIn(bad, src)
        rel = [
            (node.level, node.module)
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.level
        ]
        self.assertEqual(rel, [(1, "disposable_network_identity_genesis_binding")])

    def test_economics_unchanged(self) -> None:
        self.assertEqual(tx_validation.L28_MAX_SUPPLY, 28_000_000)
        self.assertEqual(tx_validation.L28_EMISSION_CEILING, 11_130_000)
        self.assertEqual(tx_validation.L28_REWARD_SCHEDULE, (28, 14, 7, 3, 1))


if __name__ == "__main__":
    unittest.main()
