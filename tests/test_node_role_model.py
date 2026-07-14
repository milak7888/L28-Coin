import ast
import dataclasses
import json
import unittest
from pathlib import Path

from coin import node_role_model as model


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "docs" / "l28_core_p2p_security_profile_v0.1.json"
MODEL_PATH = ROOT / "coin" / "node_role_model.py"


class NodeRoleModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))

    def test_public_construction_always_starts_created(self):
        core = model.CoreNodeRoleModel()
        p2p = model.P2PNodeRoleModel()
        self.assertEqual(core.state, "CREATED")
        self.assertEqual(p2p.state, "CREATED")
        with self.assertRaises(TypeError):
            model.CoreNodeRoleModel(state="PAUSED")
        with self.assertRaises(TypeError):
            model.P2PNodeRoleModel(state="CONFIGURED")

    def test_models_are_frozen_and_transitions_are_immutable(self):
        core = model.CoreNodeRoleModel()
        next_core, result = core.transition("EVIDENCE_ONLY")
        self.assertTrue(result.ok)
        self.assertIsNot(core, next_core)
        self.assertEqual(core.state, "CREATED")
        self.assertEqual(next_core.state, "EVIDENCE_ONLY")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            core.state = "PAUSED"

    def test_all_profile_core_transitions_are_implemented_exactly(self):
        lifecycle = self.profile["core_lifecycle"]
        expected = {tuple(item) for item in lifecycle["allowed_transitions"]}
        self.assertEqual(model.CORE_ALLOWED_TRANSITIONS, expected)
        self.assertEqual(model.CORE_STATES, set(lifecycle["states"]))
        self.assertEqual(
            model.CORE_RESERVED_STATES,
            set(lifecycle["reserved_unreachable_states"]),
        )

        for source, destination in sorted(expected):
            with self.subTest(source=source, destination=destination):
                current = model.CoreNodeRoleModel._from_valid_state(source)
                updated, result = current.transition(destination)
                self.assertTrue(result.ok)
                self.assertEqual(result.code, "transitioned")
                self.assertEqual(updated.state, destination)
                self.assertEqual(current.state, source)

    def test_all_profile_p2p_transitions_are_implemented_exactly(self):
        lifecycle = self.profile["p2p_lifecycle"]
        expected = {tuple(item) for item in lifecycle["allowed_transitions"]}
        self.assertEqual(model.P2P_ALLOWED_TRANSITIONS, expected)
        self.assertEqual(model.P2P_STATES, set(lifecycle["states"]))
        self.assertEqual(
            model.P2P_RESERVED_STATES,
            set(lifecycle["reserved_unreachable_states"]),
        )

        for source, destination in sorted(expected):
            with self.subTest(source=source, destination=destination):
                current = model.P2PNodeRoleModel._from_valid_state(source)
                updated, result = current.transition(destination)
                self.assertTrue(result.ok)
                self.assertEqual(result.code, "transitioned")
                self.assertEqual(updated.state, destination)
                self.assertEqual(current.state, source)

    def test_reserved_states_are_unreachable_for_both_roles(self):
        cases = (
            (model.CoreNodeRoleModel(), model.CORE_RESERVED_STATES),
            (model.P2PNodeRoleModel(), model.P2P_RESERVED_STATES),
        )
        for current, reserved_states in cases:
            for reserved in sorted(reserved_states):
                with self.subTest(role=current.role, reserved=reserved):
                    updated, result = current.transition(reserved)
                    self.assertFalse(result.ok)
                    self.assertEqual(result.code, "reserved_state_unreachable")
                    self.assertIs(updated, current)
                    self.assertEqual(result.resulting_state, current.state)

    def test_internal_factory_rejects_reserved_and_unknown_states(self):
        for role_model, states in (
            (model.CoreNodeRoleModel, model.CORE_RESERVED_STATES),
            (model.P2PNodeRoleModel, model.P2P_RESERVED_STATES),
        ):
            for reserved in states:
                with self.assertRaises(ValueError):
                    role_model._from_valid_state(reserved)
            with self.assertRaises(ValueError):
                role_model._from_valid_state("UNKNOWN")

    def test_unknown_empty_and_non_string_states_fail_closed(self):
        for current in (model.CoreNodeRoleModel(), model.P2PNodeRoleModel()):
            for requested in ("UNKNOWN", "", None, 7, False):
                with self.subTest(role=current.role, requested=requested):
                    updated, result = current.transition(requested)
                    self.assertFalse(result.ok)
                    self.assertEqual(result.code, "state_invalid")
                    self.assertIs(updated, current)
                    self.assertEqual(result.resulting_state, "CREATED")

    def test_known_but_disallowed_transitions_fail_closed(self):
        for role_model, states, allowed, reserved in (
            (
                model.CoreNodeRoleModel,
                model.CORE_STATES,
                model.CORE_ALLOWED_TRANSITIONS,
                model.CORE_RESERVED_STATES,
            ),
            (
                model.P2PNodeRoleModel,
                model.P2P_STATES,
                model.P2P_ALLOWED_TRANSITIONS,
                model.P2P_RESERVED_STATES,
            ),
        ):
            active_states = states - reserved
            for source in active_states:
                current = role_model._from_valid_state(source)
                for destination in active_states:
                    if (source, destination) in allowed:
                        continue
                    with self.subTest(
                        role=current.role,
                        source=source,
                        destination=destination,
                    ):
                        updated, result = current.transition(destination)
                        self.assertFalse(result.ok)
                        self.assertEqual(result.code, "transition_not_allowed")
                        self.assertIs(updated, current)
                        self.assertEqual(result.resulting_state, source)

    def test_role_identity_and_result_fields_are_explicit(self):
        cases = (
            (model.CoreNodeRoleModel(), "EVIDENCE_ONLY", "CoreL28Node"),
            (model.P2PNodeRoleModel(), "CONFIGURED", "L28P2PNode"),
        )
        for current, destination, expected_role in cases:
            updated, result = current.transition(destination)
            self.assertTrue(result.ok)
            self.assertEqual(result.role, expected_role)
            self.assertEqual(result.previous_state, "CREATED")
            self.assertEqual(result.requested_state, destination)
            self.assertEqual(result.resulting_state, destination)
            self.assertEqual(result.model_version, model.MODEL_VERSION)
            self.assertEqual(updated.state, destination)

    def test_stopped_state_is_terminal(self):
        for role_model in (model.CoreNodeRoleModel, model.P2PNodeRoleModel):
            stopped = role_model._from_valid_state("STOPPED")
            for destination in role_model.states - role_model.reserved_states:
                with self.subTest(role=role_model.role, destination=destination):
                    updated, result = stopped.transition(destination)
                    self.assertFalse(result.ok)
                    self.assertEqual(result.code, "transition_not_allowed")
                    self.assertIs(updated, stopped)

    def test_stable_codes_are_unique_and_exact(self):
        self.assertEqual(len(model.STABLE_CODES), len(set(model.STABLE_CODES)))
        self.assertEqual(
            set(model.STABLE_CODES),
            {
                "transitioned",
                "state_invalid",
                "reserved_state_unreachable",
                "transition_not_allowed",
            },
        )

    def test_production_model_has_no_io_or_activation_imports(self):
        source = MODEL_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(MODEL_PATH))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add((node.module or "").split(".", 1)[0])
        self.assertLessEqual(imports, {"__future__", "dataclasses", "typing"})
        self.assertNotIn('if __name__ == "__main__"', source)


if __name__ == "__main__":
    unittest.main()
