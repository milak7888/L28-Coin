# SPDX-License-Identifier: Apache-2.0
"""Foundation 49 offline disposable sandbox directory creation-plan tests."""

from __future__ import annotations

import ast
import hashlib
import json
import unittest
from pathlib import Path
from unittest import mock

from coin import disposable_network_identity_genesis_binding as identity
from coin import disposable_sandbox_directory_creation as plan
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


def _identity_digests() -> tuple[str, str, str]:
    genesis = identity.verify_disposable_network_genesis_json(identity.genesis_json_bytes())
    assert genesis.ok
    binding = identity.validate_disposable_handshake_identity_binding(
        network_id=identity.NETWORK_ID,
        chain_id=genesis.chain_id,
        protocol_version=identity.PROTOCOL_VERSION,
        genesis_digest=genesis.genesis_digest,
    )
    assert binding.ok
    return genesis.chain_id, genesis.genesis_digest, binding.report_id


def _preflight_evidence(
    *,
    chain_id: str | None = None,
    genesis_digest: str | None = None,
    identity_report_id: str | None = None,
    sandbox_instance_id: str | None = None,
    report_id: str | None = None,
    **overrides: object,
) -> dict[str, object]:
    cid, gdigest, ireport = _identity_digests()
    if chain_id is None:
        chain_id = cid
    if genesis_digest is None:
        genesis_digest = gdigest
    if identity_report_id is None:
        identity_report_id = ireport
    if sandbox_instance_id is None:
        sandbox_instance_id = "a" + chain_id[1:]
    if report_id is None:
        report_id = _hex64(f"preflight:{sandbox_instance_id}")
    base: dict[str, object] = {
        "ok": True,
        "code": "preflight_ok",
        "entrypoint_version": plan.ENTRYPOINT_PROFILE,
        "environment": identity.ENVIRONMENT,
        "network_id": identity.NETWORK_ID,
        "chain_id": chain_id,
        "genesis_digest": genesis_digest,
        "protocol_version": identity.PROTOCOL_VERSION,
        "identity_report_id": identity_report_id,
        "lifecycle_policy_version": plan.LIFECYCLE_POLICY_VERSION,
        "lifecycle_resulting_state": "DISPOSABLE_TEST_READY",
        "sandbox_instance_id": sandbox_instance_id,
        "preflight_ok": True,
        "process_launch_authorized": False,
        "execution_authorized": False,
        "report_id": report_id,
        "detail": "",
    }
    base.update(overrides)
    return base


def _sandbox(
    evidence: dict[str, object] | None = None,
    *,
    exclusive_ownership: object = True,
    instance_id: str | None = None,
    path_lexeme: str | None = None,
    **overrides: object,
) -> dict[str, object]:
    f47 = evidence if evidence is not None else _preflight_evidence()
    base: dict[str, object] = {
        "data_dir_tag": identity.DATA_DIR_TAG,
        "environment": identity.ENVIRONMENT,
        "network_id": identity.NETWORK_ID,
        "chain_id": f47["chain_id"],
        "genesis_digest": f47["genesis_digest"],
        "instance_id": instance_id
        if instance_id is not None
        else str(f47["sandbox_instance_id"]),
        "exclusive_ownership": exclusive_ownership,
        "path_lexeme": path_lexeme
        if path_lexeme is not None
        else f"/tmp/{identity.DATA_DIR_TAG}/core-1",
    }
    base.update(overrides)
    return base


def _creation_intent(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "create_mode": "exclusive_create_new",
        "existing_path_policy": "reject",
        "symlink_policy": "reject",
        "cleanup_ownership": "tagged_disposable_only",
        "deferred_filesystem_obligations": True,
    }
    base.update(overrides)
    return base


def _request(
    *,
    preflight_evidence: dict[str, object] | None = None,
    sandbox: dict[str, object] | None = None,
    creation_intent: dict[str, object] | None = None,
    environment: str = "DISPOSABLE_TEST",
    creation_profile: str = plan.PROFILE,
    execution_authorized: object = False,
    process_launch_authorized: object = False,
) -> dict[str, object]:
    f47 = preflight_evidence if preflight_evidence is not None else _preflight_evidence()
    return {
        "creation_profile": creation_profile,
        "environment": environment,
        "preflight_evidence": f47,
        "sandbox": sandbox if sandbox is not None else _sandbox(f47),
        "creation_intent": creation_intent
        if creation_intent is not None
        else _creation_intent(),
        "execution_authorized": execution_authorized,
        "process_launch_authorized": process_launch_authorized,
    }


class SuccessPathTests(unittest.TestCase):
    def test_valid_creation_plan(self) -> None:
        raw = _wire(_request())
        result = plan.evaluate_sandbox_directory_creation_plan_json(raw)
        self.assertTrue(result.ok, result.code)
        self.assertEqual(result.code, "creation_plan_ok")
        self.assertIs(result.creation_plan_ok, True)
        self.assertIs(result.execution_authorized, False)
        self.assertIs(result.process_launch_authorized, False)
        self.assertFalse(hasattr(result, "admission_authorized"))
        self.assertFalse(hasattr(result, "filesystem_create_authorized"))
        self.assertEqual(result.creation_profile, plan.PROFILE)
        self.assertEqual(result.detail, "")
        self.assertEqual(result.report_id, hashlib.sha256(raw).hexdigest())
        self.assertEqual(len(result.report_id), 64)

    def test_determinism_and_report_id(self) -> None:
        raw = _wire(_request())
        one = plan.evaluate_sandbox_directory_creation_plan_json(raw)
        two = plan.evaluate_sandbox_directory_creation_plan_json(raw)
        self.assertEqual(one, two)
        self.assertEqual(one.report_id, two.report_id)

    def test_slash_path_lexeme_not_rejected_by_f46_matrix(self) -> None:
        f47 = _preflight_evidence()
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(_request(sandbox=_sandbox(f47, path_lexeme="/")))
        )
        self.assertEqual(result.code, "creation_plan_ok")

    def test_result_immutability(self) -> None:
        result = plan.evaluate_sandbox_directory_creation_plan_json(_wire(_request()))
        with self.assertRaises(Exception):
            result.code = "x"  # type: ignore[misc]


class EnvironmentAuthorityTests(unittest.TestCase):
    def test_forbidden_environments(self) -> None:
        for env in ("MAIN", "CANONICAL", "HISTORICAL", "PRODUCTION"):
            with self.subTest(env=env):
                result = plan.evaluate_sandbox_directory_creation_plan_json(
                    _wire(_request(environment=env))
                )
                self.assertEqual(result.code, "historical_import_forbidden")
                self.assertIs(result.execution_authorized, False)
                self.assertIs(result.process_launch_authorized, False)
                self.assertEqual(result.report_id, "")
                self.assertEqual(result.detail, "")

    def test_generic_invalid_environment(self) -> None:
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(_request(environment="OTHER"))
        )
        self.assertEqual(result.code, "environment_invalid")

    def test_execution_authorized_true(self) -> None:
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(_request(execution_authorized=True))
        )
        self.assertEqual(result.code, "execution_authorized_invalid")

    def test_process_launch_authorized_true(self) -> None:
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(_request(process_launch_authorized=True))
        )
        self.assertEqual(result.code, "process_launch_authorized_invalid")

    def test_admission_authorized_top_level(self) -> None:
        req = _request()
        req["admission_authorized"] = False  # type: ignore[assignment]
        result = plan.evaluate_sandbox_directory_creation_plan_json(_wire(req))
        self.assertEqual(result.code, "schema_invalid")

    def test_admission_authorized_nested_sandbox(self) -> None:
        req = _request()
        sandbox = dict(req["sandbox"])  # type: ignore[arg-type]
        sandbox["admission_authorized"] = False
        req["sandbox"] = sandbox
        result = plan.evaluate_sandbox_directory_creation_plan_json(_wire(req))
        self.assertEqual(result.code, "schema_invalid")

    def test_admission_authorized_nested_preflight(self) -> None:
        req = _request()
        evidence = dict(req["preflight_evidence"])  # type: ignore[arg-type]
        evidence["admission_authorized"] = False
        req["preflight_evidence"] = evidence
        result = plan.evaluate_sandbox_directory_creation_plan_json(_wire(req))
        self.assertEqual(result.code, "schema_invalid")

    def test_filesystem_create_authorized_top_level(self) -> None:
        req = _request()
        req["filesystem_create_authorized"] = False  # type: ignore[assignment]
        result = plan.evaluate_sandbox_directory_creation_plan_json(_wire(req))
        self.assertEqual(result.code, "schema_invalid")

    def test_filesystem_create_authorized_nested_intent(self) -> None:
        req = _request()
        intent = dict(req["creation_intent"])  # type: ignore[arg-type]
        intent["filesystem_create_authorized"] = False
        req["creation_intent"] = intent
        result = plan.evaluate_sandbox_directory_creation_plan_json(_wire(req))
        self.assertEqual(result.code, "schema_invalid")


class EvidenceAndPlanTests(unittest.TestCase):
    def test_preflight_ok_false(self) -> None:
        f47 = _preflight_evidence(ok=False, preflight_ok=False, code="preflight_ok")
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(_request(preflight_evidence=f47))
        )
        self.assertEqual(result.code, "preflight_evidence_invalid")

    def test_preflight_wrong_code(self) -> None:
        f47 = _preflight_evidence(code="other")
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(_request(preflight_evidence=f47))
        )
        self.assertEqual(result.code, "preflight_evidence_invalid")

    def test_preflight_reordered_fields(self) -> None:
        f47 = _preflight_evidence()
        keys = list(f47.keys())
        keys[0], keys[1] = keys[1], keys[0]
        reordered = {k: f47[k] for k in keys}
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(_request(preflight_evidence=reordered))
        )
        self.assertEqual(result.code, "preflight_evidence_invalid")

    def test_preflight_zero_instance_id(self) -> None:
        f47 = _preflight_evidence(sandbox_instance_id=plan.ZERO_INSTANCE_ID)
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(_request(preflight_evidence=f47, sandbox=_sandbox(f47)))
        )
        self.assertEqual(result.code, "preflight_evidence_invalid")

    def test_sandbox_zero_instance_id(self) -> None:
        f47 = _preflight_evidence()
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(
                _request(
                    preflight_evidence=f47,
                    sandbox=_sandbox(f47, instance_id=plan.ZERO_INSTANCE_ID),
                )
            )
        )
        self.assertEqual(result.code, "sandbox_plan_invalid")

    def test_exclusive_ownership_false(self) -> None:
        f47 = _preflight_evidence()
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(
                _request(
                    preflight_evidence=f47,
                    sandbox=_sandbox(f47, exclusive_ownership=False),
                )
            )
        )
        self.assertEqual(result.code, "sandbox_plan_invalid")

    def test_empty_and_whitespace_path_lexeme(self) -> None:
        f47 = _preflight_evidence()
        for path in ("", "   ", "\t"):
            with self.subTest(path=repr(path)):
                result = plan.evaluate_sandbox_directory_creation_plan_json(
                    _wire(
                        _request(
                            preflight_evidence=f47,
                            sandbox=_sandbox(f47, path_lexeme=path),
                        )
                    )
                )
                self.assertEqual(result.code, "sandbox_plan_invalid")

    def test_wrong_data_dir_tag(self) -> None:
        f47 = _preflight_evidence()
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(
                _request(
                    preflight_evidence=f47,
                    sandbox=_sandbox(f47, data_dir_tag="other-tag"),
                )
            )
        )
        self.assertEqual(result.code, "sandbox_plan_invalid")

    def test_creation_intent_invalid_mode(self) -> None:
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(_request(creation_intent=_creation_intent(create_mode="shared")))
        )
        self.assertEqual(result.code, "creation_intent_invalid")

    def test_deferred_obligations_false(self) -> None:
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(
                _request(
                    creation_intent=_creation_intent(
                        deferred_filesystem_obligations=False
                    )
                )
            )
        )
        self.assertEqual(result.code, "creation_intent_invalid")

    def test_evidence_mismatch_instance_id(self) -> None:
        f47 = _preflight_evidence()
        other = "b" + str(f47["sandbox_instance_id"])[1:]
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(
                _request(
                    preflight_evidence=f47,
                    sandbox=_sandbox(f47, instance_id=other),
                )
            )
        )
        self.assertEqual(result.code, "evidence_mismatch")

    def test_evidence_mismatch_chain_id(self) -> None:
        f47 = _preflight_evidence()
        other_chain = "c" + str(f47["chain_id"])[1:]
        sandbox = _sandbox(f47)
        sandbox["chain_id"] = other_chain
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(_request(preflight_evidence=f47, sandbox=sandbox))
        )
        self.assertEqual(result.code, "evidence_mismatch")


class MalformedAndLimitTests(unittest.TestCase):
    def test_input_type_invalid(self) -> None:
        result = plan.evaluate_sandbox_directory_creation_plan_json(None)  # type: ignore[arg-type]
        self.assertEqual(result.code, "input_type_invalid")

    def test_input_too_large(self) -> None:
        huge = b'{"x":"' + (b"a" * plan.MAX_REQUEST_BYTES) + b'"}'
        self.assertGreater(len(huge), plan.MAX_REQUEST_BYTES)
        result = plan.evaluate_sandbox_directory_creation_plan_json(huge)
        self.assertEqual(result.code, "input_too_large")

    def test_encoding_invalid(self) -> None:
        result = plan.evaluate_sandbox_directory_creation_plan_json(b"\xff\xfe")
        self.assertEqual(result.code, "encoding_invalid")

    def test_json_invalid(self) -> None:
        result = plan.evaluate_sandbox_directory_creation_plan_json(b"{")
        self.assertEqual(result.code, "json_invalid")

    def test_duplicate_key(self) -> None:
        result = plan.evaluate_sandbox_directory_creation_plan_json(b'{"a":1,"a":2}')
        self.assertEqual(result.code, "duplicate_key")

    def test_non_finite_number(self) -> None:
        result = plan.evaluate_sandbox_directory_creation_plan_json(b'{"a":NaN}')
        self.assertEqual(result.code, "json_invalid")

    def test_invalid_top_level(self) -> None:
        result = plan.evaluate_sandbox_directory_creation_plan_json(b"[]")
        self.assertEqual(result.code, "invalid_top_level")

    def test_missing_top_level_field(self) -> None:
        req = _request()
        del req["sandbox"]
        result = plan.evaluate_sandbox_directory_creation_plan_json(_wire(req))
        self.assertEqual(result.code, "schema_invalid")

    def test_unknown_top_level_field(self) -> None:
        req = _request()
        req["extra"] = True  # type: ignore[assignment]
        result = plan.evaluate_sandbox_directory_creation_plan_json(_wire(req))
        self.assertEqual(result.code, "schema_invalid")

    def test_reordered_top_level_fields(self) -> None:
        req = _request()
        keys = list(req.keys())
        keys[0], keys[-1] = keys[-1], keys[0]
        reordered = {k: req[k] for k in keys}
        result = plan.evaluate_sandbox_directory_creation_plan_json(_wire(reordered))
        self.assertEqual(result.code, "schema_invalid")

    def test_wrong_top_level_type(self) -> None:
        req = _request()
        req["sandbox"] = "not-an-object"  # type: ignore[assignment]
        result = plan.evaluate_sandbox_directory_creation_plan_json(_wire(req))
        self.assertEqual(result.code, "schema_invalid")

    def test_creation_profile_unsupported(self) -> None:
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(_request(creation_profile="l28-disposable-sandbox-directory-creation/v9"))
        )
        self.assertEqual(result.code, "creation_profile_unsupported")
        self.assertEqual(
            result.creation_profile,
            "l28-disposable-sandbox-directory-creation/v9",
        )


class PrecedenceAndCoverageTests(unittest.TestCase):
    def test_execution_authorized_precedes_invalid_f47(self) -> None:
        f47 = _preflight_evidence(ok=False, preflight_ok=False)
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(_request(preflight_evidence=f47, execution_authorized=True))
        )
        self.assertEqual(result.code, "execution_authorized_invalid")

    def test_nested_admission_precedes_invalid_intent(self) -> None:
        req = _request(creation_intent=_creation_intent(create_mode="shared"))
        sandbox = dict(req["sandbox"])  # type: ignore[arg-type]
        sandbox["admission_authorized"] = False
        req["sandbox"] = sandbox
        result = plan.evaluate_sandbox_directory_creation_plan_json(_wire(req))
        self.assertEqual(result.code, "schema_invalid")

    def test_exclusive_ownership_precedes_binding_mismatch(self) -> None:
        f47 = _preflight_evidence()
        other = "b" + str(f47["sandbox_instance_id"])[1:]
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(
                _request(
                    preflight_evidence=f47,
                    sandbox=_sandbox(
                        f47, exclusive_ownership=False, instance_id=other
                    ),
                )
            )
        )
        self.assertEqual(result.code, "sandbox_plan_invalid")

    def test_binding_mismatch_after_local_ok(self) -> None:
        f47 = _preflight_evidence()
        other = "b" + str(f47["sandbox_instance_id"])[1:]
        result = plan.evaluate_sandbox_directory_creation_plan_json(
            _wire(
                _request(
                    preflight_evidence=f47,
                    sandbox=_sandbox(f47, instance_id=other),
                )
            )
        )
        self.assertEqual(result.code, "evidence_mismatch")

    def test_parse_failure_precedes_later_failures(self) -> None:
        result = plan.evaluate_sandbox_directory_creation_plan_json(b"{")
        self.assertEqual(result.code, "json_invalid")

    def test_all_stable_codes_exactly_once(self) -> None:
        f47 = _preflight_evidence()
        other = "b" + str(f47["sandbox_instance_id"])[1:]
        cases: dict[str, bytes | object] = {
            "input_type_invalid": None,
            "input_too_large": b'{"x":"' + (b"a" * plan.MAX_REQUEST_BYTES) + b'"}',
            "encoding_invalid": b"\xff\xfe",
            "json_invalid": b"{",
            "duplicate_key": b'{"a":1,"a":2}',
            "invalid_top_level": b"[]",
            "schema_invalid": _wire(
                {k: v for k, v in _request().items() if k != "sandbox"}
            ),
            "creation_profile_unsupported": _wire(
                _request(creation_profile="foreign/v0")
            ),
            "environment_invalid": _wire(_request(environment="OTHER")),
            "historical_import_forbidden": _wire(_request(environment="MAIN")),
            "execution_authorized_invalid": _wire(
                _request(execution_authorized=True)
            ),
            "process_launch_authorized_invalid": _wire(
                _request(process_launch_authorized=True)
            ),
            "preflight_evidence_invalid": _wire(
                _request(preflight_evidence=_preflight_evidence(code="nope"))
            ),
            "sandbox_plan_invalid": _wire(
                _request(
                    preflight_evidence=f47,
                    sandbox=_sandbox(f47, exclusive_ownership=False),
                )
            ),
            "creation_intent_invalid": _wire(
                _request(creation_intent=_creation_intent(create_mode="x"))
            ),
            "evidence_mismatch": _wire(
                _request(
                    preflight_evidence=f47,
                    sandbox=_sandbox(f47, instance_id=other),
                )
            ),
            "creation_plan_ok": _wire(_request()),
        }
        observed: list[str] = []
        for code, payload in cases.items():
            if code == "input_type_invalid":
                result = plan.evaluate_sandbox_directory_creation_plan_json(
                    payload  # type: ignore[arg-type]
                )
            else:
                result = plan.evaluate_sandbox_directory_creation_plan_json(
                    payload  # type: ignore[arg-type]
                )
            self.assertEqual(result.code, code, code)
            self.assertIs(result.execution_authorized, False)
            self.assertIs(result.process_launch_authorized, False)
            self.assertFalse(hasattr(result, "admission_authorized"))
            self.assertFalse(hasattr(result, "filesystem_create_authorized"))
            if code == "creation_plan_ok":
                self.assertNotEqual(result.report_id, "")
            else:
                self.assertEqual(result.report_id, "")
                self.assertEqual(result.detail, "")
            observed.append(result.code)

        with mock.patch.object(plan, "_parse", side_effect=RuntimeError("boom")):
            internal = plan.evaluate_sandbox_directory_creation_plan_json(
                _wire(_request())
            )
        self.assertEqual(internal.code, "internal_error")
        self.assertEqual(internal.report_id, "")
        self.assertEqual(internal.detail, "")
        observed.append(internal.code)

        self.assertEqual(len(plan.STABLE_CODES), 18)
        self.assertEqual(len(set(plan.STABLE_CODES)), 18)
        self.assertEqual(set(observed), set(plan.STABLE_CODES))

    def test_internal_error_monkeypatch(self) -> None:
        with mock.patch.object(plan, "_evaluate_parsed", side_effect=RuntimeError("x")):
            first = plan.evaluate_sandbox_directory_creation_plan_json(_wire(_request()))
            second = plan.evaluate_sandbox_directory_creation_plan_json(_wire(_request()))
        self.assertEqual(first.code, "internal_error")
        self.assertEqual(second.code, "internal_error")
        self.assertEqual(first, second)


class HygieneTests(unittest.TestCase):
    def test_module_static_hygiene(self) -> None:
        src = Path(plan.__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)
        imported: set[str] = set()
        from_mods: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    from_mods.append(node.module)
                    imported.add(node.module.split(".")[0].lstrip("."))
        forbidden = {
            "os",
            "pathlib",
            "tempfile",
            "shutil",
            "subprocess",
            "socket",
            "asyncio",
            "threading",
            "random",
            "secrets",
            "uuid",
            "time",
            "urllib",
            "http",
            "requests",
        }
        self.assertTrue(imported.isdisjoint(forbidden), imported)
        self.assertNotIn("disposable_core_process_entrypoint", "".join(from_mods))
        self.assertNotIn("disposable_core_process_lifecycle_policy", "".join(from_mods))
        self.assertNotIn("node_role_model", "".join(from_mods))
        for bad in (
            "Leap28",
            "Nova",
            "evaluate_core_entrypoint_preflight_json",
            "evaluate_core_lifecycle_policy",
            "CoreNodeRoleModel",
            ".transition(",
            "Popen",
            "os.symlink",
            "os.mkdir",
            "os.makedirs",
            "os.environ",
            "os.getenv",
            "pathlib",
            "tempfile",
            "shutil",
            "subprocess",
            "os.realpath",
            "os.path.realpath",
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
