# SPDX-License-Identifier: Apache-2.0
"""Foundation 47 offline disposable Core entrypoint preflight tests."""

from __future__ import annotations

import ast
import hashlib
import json
import unittest
from pathlib import Path
from unittest import mock

from coin import disposable_core_process_entrypoint as entry
from coin import disposable_core_process_lifecycle_policy as policy
from coin import disposable_network_identity_genesis_binding as identity
from coin import node_role_model as role
from coin import tx_validation


def _wire(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")


def _f39_projection() -> dict[str, object]:
    genesis = identity.verify_disposable_network_genesis_json(identity.genesis_json_bytes())
    assert genesis.ok
    result = identity.validate_disposable_handshake_identity_binding(
        network_id=identity.NETWORK_ID,
        chain_id=genesis.chain_id,
        protocol_version=identity.PROTOCOL_VERSION,
        genesis_digest=genesis.genesis_digest,
    )
    assert result.ok
    return {
        "ok": True,
        "code": "ok",
        "network_id": result.network_id,
        "chain_id": result.chain_id,
        "genesis_digest": result.genesis_digest,
        "protocol_version": result.protocol_version,
        "execution_authorized": False,
        "report_id": result.report_id,
    }


def _f45_projection(evidence: dict[str, object] | None = None) -> dict[str, object]:
    f39 = evidence if evidence is not None else _f39_projection()
    result = policy.evaluate_core_lifecycle_policy(
        identity_evidence=f39,
        current_state="CREATED",
        requested_state="DISPOSABLE_TEST_READY",
    )
    assert result.ok, result.code
    return {
        "ok": True,
        "code": "transitioned",
        "role": result.role,
        "previous_state": result.previous_state,
        "requested_state": result.requested_state,
        "resulting_state": result.resulting_state,
        "model_version": result.model_version,
        "policy_version": result.policy_version,
        "network_id": result.network_id,
        "chain_id": result.chain_id,
        "genesis_digest": result.genesis_digest,
        "protocol_version": result.protocol_version,
        "identity_report_id": result.identity_report_id,
        "execution_authorized": False,
        "detail": "",
    }


def _sandbox(
    evidence: dict[str, object] | None = None,
    *,
    exclusive_ownership: object = True,
    instance_id: str | None = None,
    path_lexeme: str | None = None,
) -> dict[str, object]:
    f39 = evidence if evidence is not None else _f39_projection()
    digest = str(f39["chain_id"])
    return {
        "data_dir_tag": identity.DATA_DIR_TAG,
        "environment": identity.ENVIRONMENT,
        "network_id": identity.NETWORK_ID,
        "chain_id": f39["chain_id"],
        "genesis_digest": f39["genesis_digest"],
        "instance_id": instance_id if instance_id is not None else ("a" + digest[1:]),
        "exclusive_ownership": exclusive_ownership,
        "path_lexeme": path_lexeme
        if path_lexeme is not None
        else f"/tmp/{identity.DATA_DIR_TAG}/core-1",
    }


def _request(
    *,
    identity_evidence: dict[str, object] | None = None,
    lifecycle_policy_evidence: dict[str, object] | None = None,
    sandbox: dict[str, object] | None = None,
    process_intent: dict[str, object] | None = None,
    environment: str = "DISPOSABLE_TEST",
    entrypoint_version: str = entry.PROFILE,
    execution_authorized: object = False,
    process_launch_authorized: object = False,
) -> dict[str, object]:
    f39 = identity_evidence if identity_evidence is not None else _f39_projection()
    # Default F45/sandbox use a fresh successful identity projection so malformed
    # F39 fixtures do not break F45 helper construction before evaluation.
    f45 = (
        lifecycle_policy_evidence
        if lifecycle_policy_evidence is not None
        else _f45_projection()
    )
    return {
        "entrypoint_version": entrypoint_version,
        "environment": environment,
        "identity_evidence": f39,
        "lifecycle_policy_evidence": f45,
        "sandbox": sandbox if sandbox is not None else _sandbox(),
        "process_intent": process_intent
        if process_intent is not None
        else {
            "offline": True,
            "transport_enabled": False,
            "instance_mode": entry.INSTANCE_MODE,
        },
        "execution_authorized": execution_authorized,
        "process_launch_authorized": process_launch_authorized,
    }


class SuccessPathTests(unittest.TestCase):
    def test_valid_disposable_test_preflight(self) -> None:
        raw = _wire(_request())
        result = entry.evaluate_core_entrypoint_preflight_json(raw)
        self.assertTrue(result.ok, result.code)
        self.assertEqual(result.code, "preflight_ok")
        self.assertIs(result.preflight_ok, True)
        self.assertIs(result.execution_authorized, False)
        self.assertIs(result.process_launch_authorized, False)
        self.assertFalse(hasattr(result, "admission_authorized"))
        self.assertEqual(result.lifecycle_resulting_state, "DISPOSABLE_TEST_READY")
        self.assertEqual(result.entrypoint_version, entry.PROFILE)
        self.assertEqual(result.detail, "")
        expected = hashlib.sha256(raw).hexdigest()
        # report_id is digest of canonical JSON of accepted request object, which
        # matches the wire form produced by _wire for this fixture.
        self.assertEqual(result.report_id, expected)
        self.assertEqual(len(result.report_id), 64)

    def test_determinism_and_report_id(self) -> None:
        raw = _wire(_request())
        one = entry.evaluate_core_entrypoint_preflight_json(raw)
        two = entry.evaluate_core_entrypoint_preflight_json(raw)
        self.assertEqual(one, two)
        self.assertEqual(one.report_id, two.report_id)
        self.assertTrue(one.ok)


class EnvironmentAuthorityTests(unittest.TestCase):
    def test_forbidden_environments(self) -> None:
        for env in ("MAIN", "CANONICAL", "HISTORICAL", "PRODUCTION"):
            with self.subTest(env=env):
                result = entry.evaluate_core_entrypoint_preflight_json(
                    _wire(_request(environment=env))
                )
                self.assertEqual(result.code, "historical_import_forbidden")
                self.assertIs(result.execution_authorized, False)
                self.assertIs(result.process_launch_authorized, False)
                self.assertEqual(result.report_id, "")

    def test_generic_invalid_environment(self) -> None:
        result = entry.evaluate_core_entrypoint_preflight_json(
            _wire(_request(environment="OTHER"))
        )
        self.assertEqual(result.code, "environment_invalid")

    def test_request_execution_authorized_true(self) -> None:
        result = entry.evaluate_core_entrypoint_preflight_json(
            _wire(_request(execution_authorized=True))
        )
        self.assertEqual(result.code, "execution_authorized_invalid")

    def test_process_launch_authorized_true(self) -> None:
        result = entry.evaluate_core_entrypoint_preflight_json(
            _wire(_request(process_launch_authorized=True))
        )
        self.assertEqual(result.code, "process_launch_authorized_invalid")

    def test_admission_authorized_rejected(self) -> None:
        req = _request()
        req["admission_authorized"] = False  # type: ignore[assignment]
        result = entry.evaluate_core_entrypoint_preflight_json(_wire(req))
        self.assertEqual(result.code, "schema_invalid")

    def test_nested_admission_authorized_rejected(self) -> None:
        req = _request()
        sandbox = dict(req["sandbox"])  # type: ignore[arg-type]
        sandbox["admission_authorized"] = False
        # Keep sandbox field order invalid via extra key -> schema/sandbox path;
        # inject via process_intent instead for "anywhere" check after shape.
        intent = {
            "offline": True,
            "transport_enabled": False,
            "instance_mode": entry.INSTANCE_MODE,
            "admission_authorized": False,
        }
        req["process_intent"] = intent  # type: ignore[assignment]
        result = entry.evaluate_core_entrypoint_preflight_json(_wire(req))
        # Extra key makes process_intent field-set wrong at step 19 OR admission
        # at step 11 if we detect before intent validation. Step 11 runs first.
        self.assertEqual(result.code, "schema_invalid")


class EvidenceTests(unittest.TestCase):
    def test_malformed_f39(self) -> None:
        f39 = _f39_projection()
        f39["ok"] = False
        f39["code"] = "network_id_invalid"
        result = entry.evaluate_core_entrypoint_preflight_json(
            _wire(_request(identity_evidence=f39))
        )
        self.assertEqual(result.code, "identity_evidence_invalid")

    def test_malformed_f45_structure(self) -> None:
        f45 = _f45_projection()
        f45["ok"] = False
        f45["code"] = "identity_evidence_invalid"
        result = entry.evaluate_core_entrypoint_preflight_json(
            _wire(_request(lifecycle_policy_evidence=f45))
        )
        self.assertEqual(result.code, "lifecycle_policy_evidence_invalid")

    def test_reserved_lifecycle_state(self) -> None:
        f45 = _f45_projection()
        f45["requested_state"] = "RUNNING_RESERVED"
        result = entry.evaluate_core_entrypoint_preflight_json(
            _wire(_request(lifecycle_policy_evidence=f45))
        )
        self.assertEqual(result.code, "reserved_state_unreachable")
        self.assertEqual(result.lifecycle_resulting_state, "RUNNING_RESERVED")
        self.assertNotEqual(result.code, "lifecycle_policy_evidence_invalid")
        self.assertNotEqual(result.code, "lifecycle_state_invalid")

    def test_unsupported_non_reserved_lifecycle_state(self) -> None:
        f45 = _f45_projection()
        f45["previous_state"] = "PAUSED"
        result = entry.evaluate_core_entrypoint_preflight_json(
            _wire(_request(lifecycle_policy_evidence=f45))
        )
        self.assertEqual(result.code, "lifecycle_state_invalid")
        self.assertEqual(result.lifecycle_resulting_state, "PAUSED")
        self.assertNotEqual(result.code, "lifecycle_policy_evidence_invalid")
        self.assertNotEqual(result.code, "reserved_state_unreachable")

    def test_evidence_mismatch_chain_id(self) -> None:
        f39 = _f39_projection()
        f45 = _f45_projection(f39)
        sandbox = _sandbox(f39)
        # Mutate sandbox chain after structural constants still hex64.
        sandbox["chain_id"] = "b" * 64
        result = entry.evaluate_core_entrypoint_preflight_json(
            _wire(
                _request(
                    identity_evidence=f39,
                    lifecycle_policy_evidence=f45,
                    sandbox=sandbox,
                )
            )
        )
        self.assertEqual(result.code, "evidence_mismatch")

    def test_reserved_unreachable_on_success(self) -> None:
        result = entry.evaluate_core_entrypoint_preflight_json(_wire(_request()))
        self.assertTrue(result.ok)
        self.assertNotIn(
            result.lifecycle_resulting_state,
            role.CORE_RESERVED_STATES,
        )


class SandboxOwnershipTests(unittest.TestCase):
    def test_unsafe_paths(self) -> None:
        cases = (
            "",
            "/",
            ".",
            "./",
            "~",
            "~/l28-disposable-test",
            "/tmp/../l28-disposable-test",
            "/tmp/other/core",
            f"/tmp/{identity.DATA_DIR_TAG}/MAIN/core",
        )
        f39 = _f39_projection()
        for path in cases:
            with self.subTest(path=path):
                result = entry.evaluate_core_entrypoint_preflight_json(
                    _wire(_request(sandbox=_sandbox(f39, path_lexeme=path)))
                )
                self.assertEqual(result.code, "sandbox_descriptor_invalid")

    def test_non_exclusive_ownership(self) -> None:
        f39 = _f39_projection()
        result = entry.evaluate_core_entrypoint_preflight_json(
            _wire(_request(sandbox=_sandbox(f39, exclusive_ownership=False)))
        )
        self.assertEqual(result.code, "ownership_collision")
        self.assertNotEqual(result.code, "sandbox_descriptor_invalid")
        self.assertNotEqual(result.code, "schema_invalid")

    def test_zero_instance_id(self) -> None:
        f39 = _f39_projection()
        result = entry.evaluate_core_entrypoint_preflight_json(
            _wire(_request(sandbox=_sandbox(f39, instance_id=entry.ZERO_INSTANCE_ID)))
        )
        self.assertEqual(result.code, "ownership_collision")

    def test_deferred_symlink_verification_documented(self) -> None:
        source = Path(entry.__file__).read_text(encoding="utf-8")
        self.assertNotIn("os.symlink", source)
        self.assertNotIn("realpath", source)
        self.assertNotIn("pathlib", source)
        self.assertNotIn("os.path", source)
        # Lexical success is not FS proof — valid lexical path still preflight_ok.
        result = entry.evaluate_core_entrypoint_preflight_json(_wire(_request()))
        self.assertEqual(result.code, "preflight_ok")


class MalformedAndLimitTests(unittest.TestCase):
    def test_input_type_invalid(self) -> None:
        result = entry.evaluate_core_entrypoint_preflight_json(123)  # type: ignore[arg-type]
        self.assertEqual(result.code, "input_type_invalid")
        self.assertEqual(result.entrypoint_version, "")

    def test_input_too_large(self) -> None:
        huge = b"{" + b"a" * (entry.MAX_REQUEST_BYTES + 1) + b"}"
        result = entry.evaluate_core_entrypoint_preflight_json(huge)
        self.assertEqual(result.code, "input_too_large")

    def test_encoding_invalid(self) -> None:
        result = entry.evaluate_core_entrypoint_preflight_json(b"\xff\xfe")
        self.assertEqual(result.code, "encoding_invalid")

    def test_json_invalid(self) -> None:
        result = entry.evaluate_core_entrypoint_preflight_json("{")
        self.assertEqual(result.code, "json_invalid")

    def test_duplicate_key(self) -> None:
        result = entry.evaluate_core_entrypoint_preflight_json('{"a":1,"a":2}')
        self.assertEqual(result.code, "duplicate_key")

    def test_invalid_top_level(self) -> None:
        result = entry.evaluate_core_entrypoint_preflight_json("[]")
        self.assertEqual(result.code, "invalid_top_level")

    def test_schema_invalid_missing_field(self) -> None:
        req = _request()
        del req["sandbox"]
        result = entry.evaluate_core_entrypoint_preflight_json(_wire(req))
        self.assertEqual(result.code, "schema_invalid")

    def test_entrypoint_version_unsupported(self) -> None:
        result = entry.evaluate_core_entrypoint_preflight_json(
            _wire(_request(entrypoint_version="l28-disposable-core-process-entrypoint/v9"))
        )
        self.assertEqual(result.code, "entrypoint_version_unsupported")
        self.assertEqual(
            result.entrypoint_version,
            "l28-disposable-core-process-entrypoint/v9",
        )

    def test_process_intent_invalid(self) -> None:
        result = entry.evaluate_core_entrypoint_preflight_json(
            _wire(
                _request(
                    process_intent={
                        "offline": True,
                        "transport_enabled": True,
                        "instance_mode": entry.INSTANCE_MODE,
                    }
                )
            )
        )
        self.assertEqual(result.code, "process_intent_invalid")


class PrecedenceAndCoverageTests(unittest.TestCase):
    def test_forbidden_env_precedes_authority_and_reserved(self) -> None:
        f45 = _f45_projection()
        f45["requested_state"] = "RUNNING_RESERVED"
        result = entry.evaluate_core_entrypoint_preflight_json(
            _wire(
                _request(
                    environment="CANONICAL",
                    lifecycle_policy_evidence=f45,
                    execution_authorized=True,
                )
            )
        )
        self.assertEqual(result.code, "historical_import_forbidden")

    def test_structural_f45_precedes_reserved_classification(self) -> None:
        f45 = _f45_projection()
        f45["ok"] = False
        f45["code"] = "x"
        f45["requested_state"] = "RUNNING_RESERVED"
        result = entry.evaluate_core_entrypoint_preflight_json(
            _wire(_request(lifecycle_policy_evidence=f45))
        )
        self.assertEqual(result.code, "lifecycle_policy_evidence_invalid")

    def test_no_f21_transition_call(self) -> None:
        source = Path(entry.__file__).read_text(encoding="utf-8")
        self.assertNotIn(".transition(", source)
        self.assertNotIn("CoreNodeRoleModel", source)
        model = role.CoreNodeRoleModel()
        before = model.state
        _ = entry.evaluate_core_entrypoint_preflight_json(_wire(_request()))
        self.assertEqual(model.state, before)

    def test_internal_error_monkeypatch(self) -> None:
        with mock.patch.object(
            entry,
            "_parse",
            side_effect=RuntimeError("forced-unexpected-failure"),
        ):
            first = entry.evaluate_core_entrypoint_preflight_json(_wire(_request()))
            second = entry.evaluate_core_entrypoint_preflight_json(_wire(_request()))
        self.assertEqual(first.code, "internal_error")
        self.assertEqual(first, second)
        self.assertEqual(first.detail, "")
        self.assertNotIn("forced-unexpected-failure", first.detail)

    def test_all_22_result_codes_reachable(self) -> None:
        f39 = _f39_projection()
        f45 = _f45_projection(f39)
        fixtures: dict[str, object] = {
            "input_type_invalid": 1,
            "input_too_large": b"{" + b"a" * (entry.MAX_REQUEST_BYTES + 1) + b"}",
            "encoding_invalid": b"\xff\xfe",
            "json_invalid": "{",
            "duplicate_key": '{"a":1,"a":2}',
            "invalid_top_level": "[]",
            "schema_invalid": _wire({k: v for k, v in _request().items() if k != "sandbox"}),
            "entrypoint_version_unsupported": _wire(
                _request(entrypoint_version="other/v0")
            ),
            "historical_import_forbidden": _wire(_request(environment="MAIN")),
            "environment_invalid": _wire(_request(environment="OTHER")),
            "execution_authorized_invalid": _wire(_request(execution_authorized=True)),
            "process_launch_authorized_invalid": _wire(
                _request(process_launch_authorized=True)
            ),
            "identity_evidence_invalid": _wire(
                _request(identity_evidence={**f39, "ok": False, "code": "x"})
            ),
            "lifecycle_policy_evidence_invalid": _wire(
                _request(
                    lifecycle_policy_evidence={
                        **f45,
                        "ok": False,
                        "code": "x",
                    }
                )
            ),
            "reserved_state_unreachable": _wire(
                _request(
                    lifecycle_policy_evidence={
                        **f45,
                        "requested_state": "RUNNING_RESERVED",
                    }
                )
            ),
            "lifecycle_state_invalid": _wire(
                _request(
                    lifecycle_policy_evidence={**f45, "previous_state": "PAUSED"}
                )
            ),
            "sandbox_descriptor_invalid": _wire(
                _request(sandbox=_sandbox(f39, path_lexeme="/"))
            ),
            "ownership_collision": _wire(
                _request(sandbox=_sandbox(f39, exclusive_ownership=False))
            ),
            "evidence_mismatch": _wire(
                _request(
                    identity_evidence=f39,
                    lifecycle_policy_evidence=f45,
                    sandbox={**_sandbox(f39), "chain_id": "c" * 64},
                )
            ),
            "process_intent_invalid": _wire(
                _request(
                    process_intent={
                        "offline": True,
                        "transport_enabled": True,
                        "instance_mode": entry.INSTANCE_MODE,
                    }
                )
            ),
            "preflight_ok": _wire(_request()),
        }
        observed: dict[str, str] = {}
        for code, payload in fixtures.items():
            result = entry.evaluate_core_entrypoint_preflight_json(payload)  # type: ignore[arg-type]
            observed[code] = result.code
            self.assertEqual(result.code, code, code)
            self.assertIs(result.execution_authorized, False)
            self.assertIs(result.process_launch_authorized, False)
            self.assertFalse(hasattr(result, "admission_authorized"))

        with mock.patch.object(
            entry, "_parse", side_effect=RuntimeError("x")
        ):
            internal = entry.evaluate_core_entrypoint_preflight_json(_wire(_request()))
        self.assertEqual(internal.code, "internal_error")
        observed["internal_error"] = internal.code

        self.assertEqual(len(entry.STABLE_CODES), 22)
        self.assertEqual(len(set(entry.STABLE_CODES)), 22)
        self.assertEqual(set(observed), set(entry.STABLE_CODES))


class HygieneTests(unittest.TestCase):
    def test_static_hygiene(self) -> None:
        source = Path(entry.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        forbidden = {
            "socket",
            "subprocess",
            "threading",
            "asyncio",
            "requests",
            "urllib",
            "http",
            "sqlite3",
            "pathlib",
            "os",
            "sys",
            "tempfile",
            "wallet",
            "ledger",
            "mining",
        }
        self.assertTrue(imported.isdisjoint(forbidden), imported)
        for needle in (
            "Leap28",
            "Nova",
            "peer_admission",
            "peer_handshake",
            "l28_coin",
            "evaluate_core_lifecycle_policy",
            "import socket",
            "import subprocess",
            "os.environ",
            "time.time",
            "random.",
        ):
            self.assertNotIn(needle, source)
        self.assertIn("CORE_RESERVED_STATES", source)
        self.assertIn("DATA_DIR_TAG", source)

    def test_economics_unchanged(self) -> None:
        self.assertEqual(tx_validation.L28_MAX_SUPPLY, 28_000_000)
        self.assertEqual(tx_validation.L28_EMISSION_CEILING, 11_130_000)
        self.assertEqual(tx_validation.L28_HISTORICAL_MINED, 2_824_584)
        self.assertEqual(tx_validation.L28_HISTORICAL_LAST_ENTRY, 100_877)
        self.assertEqual(tx_validation.L28_NEXT_HEIGHT_AFTER_CHECKPOINT, 100_878)
        self.assertEqual(tx_validation.L28_HALVING_INTERVAL, 210_000)
        self.assertEqual(tx_validation.L28_REWARD_SCHEDULE, (28, 14, 7, 3, 1))

    def test_l28_coin_untouched(self) -> None:
        self.assertTrue(Path("coin/l28_coin.py").is_file())
        source = Path(entry.__file__).read_text(encoding="utf-8")
        self.assertNotIn("l28_coin", source)

    def test_result_is_frozen(self) -> None:
        result = entry.evaluate_core_entrypoint_preflight_json(_wire(_request()))
        with self.assertRaises(Exception):
            result.ok = False  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
