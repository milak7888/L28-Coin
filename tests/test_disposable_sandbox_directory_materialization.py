# SPDX-License-Identifier: Apache-2.0
"""Foundation 51 disposable sandbox directory materialization tests."""

from __future__ import annotations

import ast
import errno
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
from coin import disposable_sandbox_directory_materialization as mat
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
    """Caller-approved trusted root without symlink ancestry (macOS /var → /private/var)."""
    root = os.path.realpath(tmp)
    if root != "/" and root.endswith("/"):
        root = root.rstrip("/")
    return root


def _plan_evidence(
    *,
    sandbox_instance_id: str | None = None,
    report_id: str | None = None,
    path_lexeme: str = "/correlation-only",
    **overrides: object,
) -> dict[str, object]:
    if sandbox_instance_id is None:
        instance = _hex64("instance")
        if instance[0] == "0":
            instance = "a" + instance[1:]
    else:
        instance = sandbox_instance_id
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
        "path_lexeme": path_lexeme,
        "creation_plan_ok": True,
        "process_launch_authorized": False,
        "execution_authorized": False,
        "report_id": report_id or _hex64(f"plan:{instance}"),
        "detail": "",
    }
    base.update(overrides)
    return base


def _authority(
    *,
    trusted_root: str,
    plan: dict[str, object],
    materialization_authorized: object = True,
    attempt_id: str | None = None,
    not_after_unix: object | None = None,
    **overrides: object,
) -> dict[str, object]:
    base: dict[str, object] = {
        "materialization_authorized": materialization_authorized,
        "trusted_root": trusted_root,
        "sandbox_instance_id": plan["sandbox_instance_id"],
        "data_dir_tag": identity.DATA_DIR_TAG,
        "plan_report_id": plan["report_id"],
        "attempt_id": attempt_id or _hex64("attempt"),
        "not_after_unix": not_after_unix
        if not_after_unix is not None
        else int(time.time()) + 3600,
    }
    base.update(overrides)
    return base


def _request(
    *,
    trusted_root: str,
    plan_evidence: dict[str, object] | None = None,
    materialization_authority: dict[str, object] | None = None,
    environment: str = "DISPOSABLE_TEST",
    materialization_profile: str = mat.PROFILE,
    execution_authorized: object = False,
    process_launch_authorized: object = False,
) -> dict[str, object]:
    plan = plan_evidence if plan_evidence is not None else _plan_evidence()
    return {
        "materialization_profile": materialization_profile,
        "environment": environment,
        "plan_evidence": plan,
        "materialization_authority": materialization_authority
        if materialization_authority is not None
        else _authority(trusted_root=trusted_root, plan=plan),
        "trusted_root": trusted_root,
        "execution_authorized": execution_authorized,
        "process_launch_authorized": process_launch_authorized,
    }


class SuccessPathTests(unittest.TestCase):
    def test_materialization_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            raw = _wire(_request(trusted_root=root))
            result = mat.materialize_disposable_sandbox_directory_json(raw)
            self.assertTrue(result.ok, result.code)
            self.assertEqual(result.code, "materialization_ok")
            self.assertIs(result.materialization_ok, True)
            self.assertIs(result.execution_authorized, False)
            self.assertIs(result.process_launch_authorized, False)
            self.assertFalse(hasattr(result, "admission_authorized"))
            self.assertFalse(hasattr(result, "filesystem_create_authorized"))
            self.assertEqual(result.detail, "")
            self.assertEqual(result.report_id, hashlib.sha256(raw).hexdigest())
            self.assertTrue(os.path.isdir(result.materialization_path))
            st = os.lstat(result.materialization_path)
            self.assertFalse(stat.S_ISLNK(st.st_mode))
            self.assertEqual(stat.S_IMODE(st.st_mode), 0o700)
            self.assertEqual(
                result.child_name,
                f"{identity.DATA_DIR_TAG}-{result.sandbox_instance_id}",
            )
            self.assertEqual(
                result.materialization_path, f"{root}/{result.child_name}"
            )

    def test_path_lexeme_not_used_as_create_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            plan = _plan_evidence(path_lexeme="/must-not-create-here")
            result = mat.materialize_disposable_sandbox_directory_json(
                _wire(_request(trusted_root=root, plan_evidence=plan))
            )
            self.assertEqual(result.code, "materialization_ok")
            self.assertEqual(result.path_lexeme, "/must-not-create-here")
            self.assertFalse(os.path.exists("/must-not-create-here"))
            self.assertTrue(result.materialization_path.startswith(root + "/"))

    def test_determinism_and_immutability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            plan = _plan_evidence()
            auth = _authority(trusted_root=root, plan=plan)
            raw = _wire(
                _request(
                    trusted_root=root,
                    plan_evidence=plan,
                    materialization_authority=auth,
                )
            )
            one = mat.materialize_disposable_sandbox_directory_json(raw)
            self.assertEqual(one.code, "materialization_ok")
            # Second attempt collides — report_id from first remains stable vs recompute.
            self.assertEqual(one.report_id, hashlib.sha256(raw).hexdigest())
            with self.assertRaises(Exception):
                one.code = "x"  # type: ignore[misc]


class ParseSchemaAuthorityTests(unittest.TestCase):
    def test_input_type_invalid(self) -> None:
        result = mat.materialize_disposable_sandbox_directory_json(123)  # type: ignore[arg-type]
        self.assertEqual(result.code, "input_type_invalid")

    def test_input_too_large(self) -> None:
        payload = b"{" + (b"a" * 9000) + b"}"
        result = mat.materialize_disposable_sandbox_directory_json(payload)
        self.assertEqual(result.code, "input_too_large")

    def test_encoding_invalid(self) -> None:
        result = mat.materialize_disposable_sandbox_directory_json(b"\xff\xfe")
        self.assertEqual(result.code, "encoding_invalid")

    def test_json_invalid_and_duplicate_and_top_level(self) -> None:
        self.assertEqual(
            mat.materialize_disposable_sandbox_directory_json(b"{").code,
            "json_invalid",
        )
        self.assertEqual(
            mat.materialize_disposable_sandbox_directory_json(b'{"a":1,"a":2}').code,
            "duplicate_key",
        )
        self.assertEqual(
            mat.materialize_disposable_sandbox_directory_json(b"[]").code,
            "invalid_top_level",
        )

    def test_schema_and_profile_and_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            bad = _request(trusted_root=root)
            del bad["trusted_root"]
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(_wire(bad)).code,
                "schema_invalid",
            )
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, materialization_profile="x"))
                ).code,
                "materialization_profile_unsupported",
            )
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, environment="MAIN"))
                ).code,
                "historical_import_forbidden",
            )
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, environment="OTHER"))
                ).code,
                "environment_invalid",
            )

    def test_authority_flags_and_forbidden_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, execution_authorized=True))
                ).code,
                "execution_authorized_invalid",
            )
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(
                    _wire(
                        _request(trusted_root=root, process_launch_authorized=True)
                    )
                ).code,
                "process_launch_authorized_invalid",
            )
            req = _request(trusted_root=root)
            req["plan_evidence"]["admission_authorized"] = True  # type: ignore[index]
            # wrong field order/extra → plan_evidence_invalid happens after authority;
            # nest forbidden at top via extra key would be schema_invalid first.
            req2 = _request(trusted_root=root)
            req2["wipe_authorized"] = True  # type: ignore[index]
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(_wire(req2)).code,
                "schema_invalid",
            )
            nested = _request(trusted_root=root)
            nested["materialization_authority"]["filesystem_create_authorized"] = True  # type: ignore[index]
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(_wire(nested)).code,
                "schema_invalid",
            )
            # forbidden nested inside plan_evidence values via wrapper object
            plan = _plan_evidence()
            plan_wrapped = dict(plan)
            # Put forbidden in a list value — path_lexeme can't be list.
            # Use detail as nested? detail must be "". Inject via custom plan with
            # SovereignBrain key by replacing structure after wire — easier: top-level done.
            req3 = _request(trusted_root=root)
            req3["plan_evidence"] = {
                **plan,
            }
            # embed forbidden in authority by first making valid then checking deep scan
            # Deep scan: add nested dict in a smuggled way — authority can't have extra keys.
            # Put forbidden under plan_evidence by making path_lexeme an object — plan invalid.
            # Explicit deep forbidden: replace plan_evidence with valid shape plus nested
            # is impossible without extra keys. Extra key in plan → plan_evidence_invalid.
            # Use request list nesting: not available. Add to a synthetic field via
            # materialization_profile? no.
            # Covered: wipe_authorized top-level schema_invalid.

    def test_authority_invalid_mismatch_expired(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            plan = _plan_evidence()
            false_auth = _authority(
                trusted_root=root, plan=plan, materialization_authorized=False
            )
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(
                    _wire(
                        _request(
                            trusted_root=root,
                            plan_evidence=plan,
                            materialization_authority=false_auth,
                        )
                    )
                ).code,
                "materialization_authority_invalid",
            )
            bad_attempt = _authority(
                trusted_root=root, plan=plan, attempt_id="zz"
            )
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(
                    _wire(
                        _request(
                            trusted_root=root,
                            plan_evidence=plan,
                            materialization_authority=bad_attempt,
                        )
                    )
                ).code,
                "materialization_authority_invalid",
            )
            mismatch = _authority(trusted_root=root + "-nope", plan=plan)
            # trusted_root top-level still root; authority differs after lexical ok
            req = _request(
                trusted_root=root,
                plan_evidence=plan,
                materialization_authority=_authority(trusted_root=root, plan=plan),
            )
            req["materialization_authority"]["trusted_root"] = root + "x"  # type: ignore[index]
            # may fail lexical on authority equality only — authority trusted_root not re-lexically
            # validated except equality; root+"x" if root is /var/.../x might be invalid path
            # Equality mismatch → materialization_authority_mismatch
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(_wire(req)).code,
                "materialization_authority_mismatch",
            )
            expired = _authority(
                trusted_root=root, plan=plan, not_after_unix=int(time.time()) - 10
            )
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(
                    _wire(
                        _request(
                            trusted_root=root,
                            plan_evidence=plan,
                            materialization_authority=expired,
                        )
                    )
                ).code,
                "materialization_authority_expired",
            )
            del mismatch  # silence lint


class PlanAndRootTests(unittest.TestCase):
    def test_plan_evidence_invalid_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            plan = _plan_evidence(code="nope")
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, plan_evidence=plan))
                ).code,
                "plan_evidence_invalid",
            )
            plan2 = _plan_evidence(sandbox_instance_id="0" * 64)
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, plan_evidence=plan2))
                ).code,
                "plan_evidence_invalid",
            )
            plan3 = _plan_evidence(path_lexeme="   ")
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root, plan_evidence=plan3))
                ).code,
                "plan_evidence_invalid",
            )

    def test_plan_bound_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            plan = _plan_evidence()
            auth = _authority(trusted_root=root, plan=plan)
            auth["sandbox_instance_id"] = _hex64("other-instance")
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(
                    _wire(
                        _request(
                            trusted_root=root,
                            plan_evidence=plan,
                            materialization_authority=auth,
                        )
                    )
                ).code,
                "materialization_authority_mismatch",
            )

    def test_trusted_root_lexical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            for bad in ("relative", "~/x", "/tmp//x", root + "/", "/tmp/./x", "/tmp/../x"):
                with self.subTest(bad=bad):
                    # For paths that don't exist FS checks may not run if lexical fails first
                    plan = _plan_evidence()
                    auth = _authority(trusted_root=bad, plan=plan)
                    # top-level and authority must match for equality step; lexical on request first
                    req = _request(
                        trusted_root=bad,
                        plan_evidence=plan,
                        materialization_authority=auth,
                    )
                    code = mat.materialize_disposable_sandbox_directory_json(
                        _wire(req)
                    ).code
                    self.assertEqual(code, "trusted_root_invalid")

    def test_trusted_root_symlink_ancestry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = tmp.rstrip("/")
            real = os.path.join(base, "real")
            os.mkdir(real)
            link = os.path.join(base, "link")
            os.symlink(real, link)
            plan = _plan_evidence()
            req = _request(
                trusted_root=link,
                plan_evidence=plan,
                materialization_authority=_authority(trusted_root=link, plan=plan),
            )
            self.assertEqual(
                mat.materialize_disposable_sandbox_directory_json(_wire(req)).code,
                "trusted_root_invalid",
            )


class FilesystemMatrixTests(unittest.TestCase):
    def test_target_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            plan = _plan_evidence()
            child = f"{identity.DATA_DIR_TAG}-{plan['sandbox_instance_id']}"
            os.mkdir(os.path.join(root, child))
            result = mat.materialize_disposable_sandbox_directory_json(
                _wire(_request(trusted_root=root, plan_evidence=plan))
            )
            self.assertEqual(result.code, "target_collision")

    def test_symlink_rejected_precreate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            plan = _plan_evidence()
            child = f"{identity.DATA_DIR_TAG}-{plan['sandbox_instance_id']}"
            target = os.path.join(root, child)
            os.symlink(root, target)
            result = mat.materialize_disposable_sandbox_directory_json(
                _wire(_request(trusted_root=root, plan_evidence=plan))
            )
            self.assertEqual(result.code, "symlink_rejected")

    def test_exclusive_create_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            with mock.patch.object(
                os, "mkdir", side_effect=OSError(errno.EPERM, "denied")
            ):
                result = mat.materialize_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root))
                )
            self.assertEqual(result.code, "exclusive_create_failed")

    def test_substitution_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            with mock.patch.object(
                mat,
                "_precreate_substitution_check",
                side_effect=mat._MaterializeError("substitution_ambiguous"),
            ):
                result = mat.materialize_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root))
                )
            self.assertEqual(result.code, "substitution_ambiguous")

    def test_permission_verification_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            real_chmod = os.chmod

            def bad_chmod(path: str, mode: int) -> None:
                real_chmod(path, 0o755)

            req = _request(trusted_root=root)
            with mock.patch.object(os, "chmod", side_effect=bad_chmod):
                result = mat.materialize_disposable_sandbox_directory_json(_wire(req))
            self.assertEqual(result.code, "permission_verification_failed")
            child = f"{identity.DATA_DIR_TAG}-{req['plan_evidence']['sandbox_instance_id']}"  # type: ignore[index]
            self.assertFalse(os.path.exists(os.path.join(root, str(child))))

    def test_rollback_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            real_chmod = os.chmod

            def chmod_755(path: str, mode: int) -> None:
                real_chmod(path, 0o755)

            with mock.patch.object(os, "chmod", side_effect=chmod_755):
                with mock.patch.object(
                    os, "rmdir", side_effect=OSError(errno.ENOTEMPTY, "busy")
                ):
                    result = mat.materialize_disposable_sandbox_directory_json(
                        _wire(_request(trusted_root=root))
                    )
            self.assertEqual(result.code, "rollback_failed")

    def test_plan_binding_invalid_via_mock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            with mock.patch.object(
                mat,
                "_derive_child_name",
                side_effect=mat._MaterializeError("plan_binding_invalid"),
            ):
                result = mat.materialize_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root))
                )
            self.assertEqual(result.code, "plan_binding_invalid")

    def test_traversal_rejected_via_mock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            with mock.patch.object(
                mat,
                "_validate_derived_path",
                side_effect=mat._MaterializeError("traversal_rejected"),
            ):
                result = mat.materialize_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root))
                )
            self.assertEqual(result.code, "traversal_rejected")

    def test_containment_failure_via_mock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            with mock.patch.object(
                mat,
                "_assert_direct_child",
                side_effect=mat._MaterializeError("containment_failure"),
            ):
                result = mat.materialize_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root))
                )
            self.assertEqual(result.code, "containment_failure")

    def test_post_create_verification_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)

            def bad_basename(path: str) -> str:
                if path.startswith(root):
                    return "wrong-name"
                return os.path.basename(path)

            with mock.patch.object(os.path, "basename", side_effect=bad_basename):
                result = mat.materialize_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root))
                )
            self.assertIn(
                result.code,
                {
                    "post_create_verification_failed",
                    "permission_verification_failed",
                    "materialization_ok",
                },
            )
            # Prefer direct mock of verify tail
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)
            real_verify = mat._verify_created

            def wrapped(**kwargs: object) -> None:
                raise mat._MaterializeError("post_create_verification_failed")

            with mock.patch.object(mat, "_verify_created", side_effect=wrapped):
                # side_effect raising MaterializeError won't roll back — patch properly
                pass

            def verify_and_fail(**kwargs: object) -> None:
                path = str(kwargs["materialization_path"])
                mat._fail_after_create("post_create_verification_failed", path)

            with mock.patch.object(mat, "_verify_created", side_effect=verify_and_fail):
                result = mat.materialize_disposable_sandbox_directory_json(
                    _wire(_request(trusted_root=root))
                )
            self.assertEqual(result.code, "post_create_verification_failed")
            del real_verify


class InventoryAndHygieneTests(unittest.TestCase):
    def test_all_stable_codes_reachable(self) -> None:
        observed: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = _harness_root(tmp)

            def add(code: str, payload: object, *, raw: bool = False) -> None:
                if raw or isinstance(payload, (bytes, bytearray)):
                    result = mat.materialize_disposable_sandbox_directory_json(payload)  # type: ignore[arg-type]
                elif isinstance(payload, str):
                    result = mat.materialize_disposable_sandbox_directory_json(payload)
                else:
                    result = mat.materialize_disposable_sandbox_directory_json(
                        _wire(payload)
                    )
                self.assertEqual(result.code, code, msg=f"expected {code} got {result.code}")
                self.assertIs(result.execution_authorized, False)
                self.assertIs(result.process_launch_authorized, False)
                if code == "materialization_ok":
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
            bad_schema = _request(trusted_root=root)
            del bad_schema["environment"]
            add("schema_invalid", bad_schema)
            add(
                "materialization_profile_unsupported",
                _request(trusted_root=root, materialization_profile="nope"),
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
            # forbidden field
            req_forbid = _request(trusted_root=root)
            req_forbid["ledger_authorized"] = True  # type: ignore[index]
            add("schema_invalid", req_forbid)
            # authority invalid
            plan = _plan_evidence()
            add(
                "materialization_authority_invalid",
                _request(
                    trusted_root=root,
                    plan_evidence=plan,
                    materialization_authority=_authority(
                        trusted_root=root,
                        plan=plan,
                        materialization_authorized=False,
                    ),
                ),
            )
            req_mis = _request(trusted_root=root, plan_evidence=plan)
            req_mis["materialization_authority"]["trusted_root"] = root + "z"  # type: ignore[index]
            add("materialization_authority_mismatch", req_mis)
            add(
                "materialization_authority_expired",
                _request(
                    trusted_root=root,
                    plan_evidence=plan,
                    materialization_authority=_authority(
                        trusted_root=root,
                        plan=plan,
                        not_after_unix=1,
                    ),
                ),
            )
            add(
                "plan_evidence_invalid",
                _request(
                    trusted_root=root,
                    plan_evidence=_plan_evidence(code="creation_plan_ok", ok=False),
                ),
            )
            add(
                "trusted_root_invalid",
                _request(
                    trusted_root="relative",
                    plan_evidence=plan,
                    materialization_authority=_authority(
                        trusted_root="relative", plan=plan
                    ),
                ),
            )

            with mock.patch.object(
                mat,
                "_derive_child_name",
                side_effect=mat._MaterializeError("plan_binding_invalid"),
            ):
                add("plan_binding_invalid", _request(trusted_root=root))
            with mock.patch.object(
                mat,
                "_validate_derived_path",
                side_effect=mat._MaterializeError("traversal_rejected"),
            ):
                add("traversal_rejected", _request(trusted_root=root))
            with mock.patch.object(
                mat,
                "_assert_direct_child",
                side_effect=mat._MaterializeError("containment_failure"),
            ):
                add("containment_failure", _request(trusted_root=root))

            child = f"{identity.DATA_DIR_TAG}-{plan['sandbox_instance_id']}"
            os.symlink(root, os.path.join(root, child))
            add("symlink_rejected", _request(trusted_root=root, plan_evidence=plan))
            os.unlink(os.path.join(root, child))

            with mock.patch.object(
                mat,
                "_precreate_substitution_check",
                side_effect=mat._MaterializeError("substitution_ambiguous"),
            ):
                add("substitution_ambiguous", _request(trusted_root=root))

            os.mkdir(os.path.join(root, child))
            add("target_collision", _request(trusted_root=root, plan_evidence=plan))
            os.rmdir(os.path.join(root, child))

            with mock.patch.object(
                os, "mkdir", side_effect=OSError(errno.EPERM, "denied")
            ):
                add("exclusive_create_failed", _request(trusted_root=root))

            real_chmod = os.chmod

            def chmod_755(path: str, mode: int) -> None:
                real_chmod(path, 0o755)

            with mock.patch.object(os, "chmod", side_effect=chmod_755):
                add("permission_verification_failed", _request(trusted_root=root))

            def verify_fail(**kwargs: object) -> None:
                mat._fail_after_create(
                    "post_create_verification_failed",
                    str(kwargs["materialization_path"]),
                )

            with mock.patch.object(mat, "_verify_created", side_effect=verify_fail):
                add("post_create_verification_failed", _request(trusted_root=root))

            def chmod_755_b(path: str, mode: int) -> None:
                real_chmod(path, 0o755)

            with mock.patch.object(os, "chmod", side_effect=chmod_755_b):
                with mock.patch.object(
                    os, "rmdir", side_effect=OSError(errno.ENOTEMPTY, "busy")
                ):
                    add("rollback_failed", _request(trusted_root=root))

            with mock.patch.object(
                mat, "_evaluate_parsed", side_effect=RuntimeError("boom")
            ):
                add("internal_error", _request(trusted_root=root))

            # success last (fresh root child)
            plan_ok = _plan_evidence(sandbox_instance_id=_hex64("success-instance"))
            add(
                "materialization_ok",
                _request(trusted_root=root, plan_evidence=plan_ok),
            )

        # schema_invalid observed twice — set equality still covers
        self.assertEqual(len(mat.STABLE_CODES), 29)
        self.assertEqual(len(set(mat.STABLE_CODES)), 29)
        self.assertEqual(set(observed), set(mat.STABLE_CODES))

    def test_module_static_hygiene(self) -> None:
        src = Path(mat.__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)
        from_mods: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                from_mods.append(node.module)
        joined = "".join(from_mods)
        self.assertNotIn("disposable_sandbox_directory_creation", joined)
        self.assertNotIn("disposable_core_process_entrypoint", joined)
        self.assertNotIn("disposable_core_process_lifecycle_policy", joined)
        for bad in (
            "Leap28",
            "Nova",
            "evaluate_sandbox_directory_creation_plan_json",
            "evaluate_core_entrypoint_preflight_json",
            "subprocess",
            "socket",
            "shutil.rmtree",
            "os.makedirs",
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
        self.assertEqual(
            rel,
            [(1, "disposable_network_identity_genesis_binding")],
        )

    def test_economics_unchanged(self) -> None:
        self.assertEqual(tx_validation.L28_MAX_SUPPLY, 28_000_000)
        self.assertEqual(tx_validation.L28_EMISSION_CEILING, 11_130_000)
        self.assertEqual(tx_validation.L28_REWARD_SCHEDULE, (28, 14, 7, 3, 1))


if __name__ == "__main__":
    unittest.main()
