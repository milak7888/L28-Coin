# SPDX-License-Identifier: Apache-2.0
"""Foundation 45 disposable Core lifecycle policy tests."""

from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path
from unittest import mock

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
        "ok": result.ok,
        "code": result.code,
        "network_id": result.network_id,
        "chain_id": result.chain_id,
        "genesis_digest": result.genesis_digest,
        "protocol_version": result.protocol_version,
        "execution_authorized": result.execution_authorized,
        "report_id": result.report_id,
    }


def _request(
    *,
    current_state: str = "CREATED",
    requested_state: str = "DISPOSABLE_TEST_READY",
    evidence: dict[str, object] | None = None,
    environment: str = "DISPOSABLE_TEST",
    execution_authorized: object = False,
    policy_version: str = policy.PROFILE,
) -> dict[str, object]:
    return {
        "policy_version": policy_version,
        "environment": environment,
        "identity_evidence": evidence if evidence is not None else _f39_projection(),
        "current_state": current_state,
        "requested_state": requested_state,
        "execution_authorized": execution_authorized,
    }


class SuccessPathTests(unittest.TestCase):
    def test_created_to_disposable_test_ready(self) -> None:
        result = policy.evaluate_core_lifecycle_policy_json(_wire(_request()))
        self.assertTrue(result.ok, result.code)
        self.assertEqual(result.code, "transitioned")
        self.assertEqual(result.previous_state, "CREATED")
        self.assertEqual(result.resulting_state, "DISPOSABLE_TEST_READY")
        self.assertIs(result.execution_authorized, False)
        self.assertFalse(hasattr(result, "admission_authorized"))
        self.assertEqual(result.detail, "")
        self.assertEqual(result.role, role.CORE_ROLE)

    def test_created_to_evidence_only(self) -> None:
        result = policy.evaluate_core_lifecycle_policy_json(
            _wire(_request(requested_state="EVIDENCE_ONLY"))
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.resulting_state, "EVIDENCE_ONLY")

    def test_helper_api(self) -> None:
        evidence = _f39_projection()
        result = policy.evaluate_core_lifecycle_policy(
            identity_evidence=evidence,
            current_state="CREATED",
            requested_state="PAUSED",
        )
        self.assertTrue(result.ok, result.code)
        self.assertEqual(result.resulting_state, "PAUSED")

    def test_all_legal_transitions(self) -> None:
        evidence = _f39_projection()
        for current, requested in sorted(role.CORE_ALLOWED_TRANSITIONS):
            with self.subTest(current=current, requested=requested):
                result = policy.evaluate_core_lifecycle_policy(
                    identity_evidence=evidence,
                    current_state=current,
                    requested_state=requested,
                )
                self.assertTrue(result.ok, result.code)
                self.assertEqual(result.code, "transitioned")
                self.assertEqual(result.resulting_state, requested)
                self.assertIs(result.execution_authorized, False)


class IdentityEvidenceTests(unittest.TestCase):
    def test_unsuccessful_evidence(self) -> None:
        evidence = _f39_projection()
        evidence["ok"] = False
        evidence["code"] = "network_id_invalid"
        result = policy.evaluate_core_lifecycle_policy_json(
            _wire(_request(evidence=evidence, requested_state="RUNNING_RESERVED"))
        )
        self.assertEqual(result.code, "identity_evidence_invalid")

    def test_wrong_success_code(self) -> None:
        evidence = _f39_projection()
        evidence["code"] = "transitioned"
        result = policy.evaluate_core_lifecycle_policy_json(_wire(_request(evidence=evidence)))
        self.assertEqual(result.code, "identity_evidence_invalid")

    def test_wrong_network_id(self) -> None:
        evidence = _f39_projection()
        evidence["network_id"] = "MAIN"
        result = policy.evaluate_core_lifecycle_policy_json(_wire(_request(evidence=evidence)))
        self.assertEqual(result.code, "identity_evidence_invalid")

    def test_empty_chain_id(self) -> None:
        evidence = _f39_projection()
        evidence["chain_id"] = ""
        result = policy.evaluate_core_lifecycle_policy_json(_wire(_request(evidence=evidence)))
        self.assertEqual(result.code, "identity_evidence_invalid")

    def test_invalid_genesis_digest(self) -> None:
        evidence = _f39_projection()
        evidence["genesis_digest"] = "not-hex"
        result = policy.evaluate_core_lifecycle_policy_json(_wire(_request(evidence=evidence)))
        self.assertEqual(result.code, "identity_evidence_invalid")

    def test_invalid_report_id(self) -> None:
        evidence = _f39_projection()
        evidence["report_id"] = "A" * 64
        result = policy.evaluate_core_lifecycle_policy_json(_wire(_request(evidence=evidence)))
        self.assertEqual(result.code, "identity_evidence_invalid")

    def test_missing_projection_field(self) -> None:
        evidence = _f39_projection()
        del evidence["report_id"]
        result = policy.evaluate_core_lifecycle_policy_json(_wire(_request(evidence=evidence)))
        self.assertEqual(result.code, "identity_evidence_invalid")

    def test_reordered_projection_fields(self) -> None:
        evidence = _f39_projection()
        reordered = {
            "report_id": evidence["report_id"],
            "ok": evidence["ok"],
            "code": evidence["code"],
            "network_id": evidence["network_id"],
            "chain_id": evidence["chain_id"],
            "genesis_digest": evidence["genesis_digest"],
            "protocol_version": evidence["protocol_version"],
            "execution_authorized": evidence["execution_authorized"],
        }
        result = policy.evaluate_core_lifecycle_policy_json(_wire(_request(evidence=reordered)))
        self.assertEqual(result.code, "identity_evidence_invalid")


class EnvironmentAuthorityTests(unittest.TestCase):
    def test_forbidden_environments(self) -> None:
        for env in ("MAIN", "CANONICAL", "HISTORICAL", "PRODUCTION"):
            with self.subTest(env=env):
                result = policy.evaluate_core_lifecycle_policy_json(
                    _wire(_request(environment=env, requested_state="RUNNING_RESERVED"))
                )
                self.assertEqual(result.code, "historical_import_forbidden")

    def test_generic_invalid_environment(self) -> None:
        result = policy.evaluate_core_lifecycle_policy_json(
            _wire(_request(environment="OTHER"))
        )
        self.assertEqual(result.code, "environment_invalid")

    def test_request_execution_authorized_true(self) -> None:
        result = policy.evaluate_core_lifecycle_policy_json(
            _wire(_request(execution_authorized=True))
        )
        self.assertEqual(result.code, "execution_authorized_invalid")

    def test_evidence_execution_authorized_true(self) -> None:
        evidence = _f39_projection()
        evidence["execution_authorized"] = True
        result = policy.evaluate_core_lifecycle_policy_json(_wire(_request(evidence=evidence)))
        self.assertEqual(result.code, "execution_authorized_invalid")

    def test_non_boolean_execution_authorized(self) -> None:
        result = policy.evaluate_core_lifecycle_policy_json(
            _wire(_request(execution_authorized=0))
        )
        self.assertEqual(result.code, "execution_authorized_invalid")

    def test_forbidden_env_precedes_reserved_request(self) -> None:
        result = policy.evaluate_core_lifecycle_policy_json(
            _wire(
                _request(
                    environment="CANONICAL",
                    requested_state="RUNNING_RESERVED",
                    execution_authorized=True,
                )
            )
        )
        self.assertEqual(result.code, "historical_import_forbidden")


class TransitionAndReservedTests(unittest.TestCase):
    def test_illegal_transition_stopped_to_created(self) -> None:
        result = policy.evaluate_core_lifecycle_policy_json(
            _wire(_request(current_state="STOPPED", requested_state="CREATED"))
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "transition_not_allowed")
        self.assertEqual(result.resulting_state, "STOPPED")

    def test_terminal_stopped(self) -> None:
        for dest in sorted(role.CORE_STATES - role.CORE_RESERVED_STATES):
            with self.subTest(dest=dest):
                result = policy.evaluate_core_lifecycle_policy(
                    identity_evidence=_f39_projection(),
                    current_state="STOPPED",
                    requested_state=dest,
                )
                self.assertEqual(result.code, "transition_not_allowed")

    def test_reserved_target_rejected(self) -> None:
        for reserved in sorted(role.CORE_RESERVED_STATES):
            with self.subTest(reserved=reserved):
                result = policy.evaluate_core_lifecycle_policy_json(
                    _wire(_request(requested_state=reserved))
                )
                self.assertEqual(result.code, "reserved_state_unreachable")
                self.assertEqual(result.resulting_state, "CREATED")

    def test_reserved_current_rejected(self) -> None:
        for reserved in sorted(role.CORE_RESERVED_STATES):
            with self.subTest(reserved=reserved):
                result = policy.evaluate_core_lifecycle_policy(
                    identity_evidence=_f39_projection(),
                    current_state=reserved,
                    requested_state="PAUSED",
                )
                self.assertEqual(result.code, "state_invalid")

    def test_injected_model_without_parallel_fsm(self) -> None:
        model = role.CoreNodeRoleModel()
        result = policy.evaluate_core_lifecycle_policy(
            identity_evidence=_f39_projection(),
            current_state="CREATED",
            requested_state="DISPOSABLE_TEST_READY",
            model=model,
        )
        self.assertTrue(result.ok)
        self.assertEqual(model.state, "CREATED")
        self.assertIs(result.execution_authorized, False)

    def test_injected_model_state_mismatch(self) -> None:
        model = role.CoreNodeRoleModel._from_valid_state("PAUSED")
        result = policy.evaluate_core_lifecycle_policy(
            identity_evidence=_f39_projection(),
            current_state="CREATED",
            requested_state="STOPPED",
            model=model,
        )
        self.assertEqual(result.code, "state_invalid")


class MalformedAndLimitTests(unittest.TestCase):
    def test_input_type_invalid(self) -> None:
        result = policy.evaluate_core_lifecycle_policy_json(123)  # type: ignore[arg-type]
        self.assertEqual(result.code, "input_type_invalid")

    def test_input_too_large(self) -> None:
        huge = b"{" + b"a" * (policy.MAX_REQUEST_BYTES + 1) + b"}"
        result = policy.evaluate_core_lifecycle_policy_json(huge)
        self.assertEqual(result.code, "input_too_large")

    def test_encoding_invalid(self) -> None:
        result = policy.evaluate_core_lifecycle_policy_json(b"\xff\xfe")
        self.assertEqual(result.code, "encoding_invalid")

    def test_json_invalid(self) -> None:
        result = policy.evaluate_core_lifecycle_policy_json("{")
        self.assertEqual(result.code, "json_invalid")

    def test_duplicate_key(self) -> None:
        result = policy.evaluate_core_lifecycle_policy_json('{"a":1,"a":2}')
        self.assertEqual(result.code, "duplicate_key")

    def test_invalid_top_level(self) -> None:
        result = policy.evaluate_core_lifecycle_policy_json("[]")
        self.assertEqual(result.code, "invalid_top_level")

    def test_unknown_field(self) -> None:
        req = _request()
        req["extra"] = "nope"
        result = policy.evaluate_core_lifecycle_policy_json(_wire(req))
        self.assertEqual(result.code, "schema_invalid")

    def test_reordered_top_level(self) -> None:
        req = _request()
        reordered = {
            "environment": req["environment"],
            "policy_version": req["policy_version"],
            "identity_evidence": req["identity_evidence"],
            "current_state": req["current_state"],
            "requested_state": req["requested_state"],
            "execution_authorized": req["execution_authorized"],
        }
        result = policy.evaluate_core_lifecycle_policy_json(_wire(reordered))
        self.assertEqual(result.code, "schema_invalid")

    def test_unsupported_policy_version(self) -> None:
        result = policy.evaluate_core_lifecycle_policy_json(
            _wire(_request(policy_version="l28-disposable-core-process-lifecycle-policy/v9"))
        )
        self.assertEqual(result.code, "policy_version_unsupported")

    def test_bool_rejected_for_state_fields(self) -> None:
        req = _request()
        req["current_state"] = True  # type: ignore[assignment]
        result = policy.evaluate_core_lifecycle_policy_json(_wire(req))
        self.assertEqual(result.code, "schema_invalid")


class DeterminismHygieneTests(unittest.TestCase):
    def test_determinism(self) -> None:
        raw = _wire(_request())
        one = policy.evaluate_core_lifecycle_policy_json(raw)
        two = policy.evaluate_core_lifecycle_policy_json(raw)
        self.assertEqual(one, two)

    def test_static_hygiene(self) -> None:
        source = Path(policy.__file__).read_text(encoding="utf-8")
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
            "wallet",
            "ledger",
            "mining",
        }
        self.assertTrue(imported.isdisjoint(forbidden))
        self.assertNotIn("Leap28", source)
        self.assertNotIn("Nova", source)
        self.assertNotIn("peer_admission", source)
        self.assertNotIn("peer_handshake", source)
        self.assertNotIn("l28_coin", source)
        self.assertNotIn("CoreNodeRoleState", source)
        self.assertIn("CoreNodeRoleModel", source)
        self.assertIn("validate_disposable_handshake_identity_binding", Path(__file__).read_text())

    def test_economics_unchanged(self) -> None:
        self.assertEqual(tx_validation.L28_MAX_SUPPLY, 28_000_000)
        self.assertEqual(tx_validation.L28_EMISSION_CEILING, 11_130_000)
        self.assertEqual(tx_validation.L28_REWARD_SCHEDULE, (28, 14, 7, 3, 1))

    def test_l28_coin_untouched(self) -> None:
        path = Path("coin/l28_coin.py")
        self.assertTrue(path.is_file())
        # Module under test must not import it.
        source = Path(policy.__file__).read_text(encoding="utf-8")
        self.assertNotIn("l28_coin", source)


class StableErrorCoverageTests(unittest.TestCase):
    def test_internal_error_monkeypatch(self) -> None:
        with mock.patch.object(
            policy,
            "_parse",
            side_effect=RuntimeError("forced-unexpected-failure"),
        ):
            first = policy.evaluate_core_lifecycle_policy_json(_wire(_request()))
            second = policy.evaluate_core_lifecycle_policy_json(_wire(_request()))
        self.assertEqual(first.code, "internal_error")
        self.assertEqual(first, second)
        self.assertEqual(first.detail, "")
        self.assertNotIn("forced-unexpected-failure", first.code)

    def test_all_17_stable_codes_asserted(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        self.assertEqual(len(policy.STABLE_CODES), 17)
        self.assertEqual(len(set(policy.STABLE_CODES)), 17)
        missing = [
            code
            for code in policy.STABLE_CODES
            if f'"{code}"' not in source and f"'{code}'" not in source
        ]
        self.assertEqual(missing, [], missing)
        ok = policy.evaluate_core_lifecycle_policy_json(_wire(_request()))
        self.assertEqual(ok.code, "transitioned")


if __name__ == "__main__":
    unittest.main()
