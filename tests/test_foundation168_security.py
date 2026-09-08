# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import json
from pathlib import Path

from coin.foundation168_bounded_runtime_driver import EXPECTED_SCOPE
from coin.foundation168_execution_authorization import INITIAL_STATE


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_NEW_PATHS = {
    "coin/foundation168_bounded_runtime_driver.py",
    "coin/foundation168_execution_authorization.py",
    "coin/foundation168_execution_evidence.py",
    "coin/foundation168_post_run_review.py",
    "tests/foundation168_execution_invocation_helper.py",
    "tests/test_foundation168_execution_authorization.py",
    "tests/test_foundation168_bounded_runtime_driver.py",
    "tests/test_foundation168_execution_evidence.py",
    "tests/test_foundation168_post_run_review.py",
    "tests/test_foundation168_security.py",
    "docs/l28_foundation168_execution_authorization_state_v1.0.json",
    "docs/l28_foundation168_execution_gate_v1.0.json",
    "docs/l28_foundation168_post_run_review_gate_v1.0.json",
    "docs/foundation168_bounded_runtime_security_review_v1.0.md",
}
NEW_PYTHON_PATHS = tuple(ROOT / path for path in ALLOWED_NEW_PATHS if path.endswith(".py"))
DRIVER_PATH = ROOT / "coin/foundation168_bounded_runtime_driver.py"
HELPER_PATH = ROOT / "tests/foundation168_execution_invocation_helper.py"
STATE_PATH = ROOT / "docs/l28_foundation168_execution_authorization_state_v1.0.json"
GATE_PATH = ROOT / "docs/l28_foundation168_execution_gate_v1.0.json"
POST_GATE_PATH = ROOT / "docs/l28_foundation168_post_run_review_gate_v1.0.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def duplicate_free_json(path):
    def reject(pairs):
        result = {}
        for key, value in pairs:
            assert key not in result, (path, key)
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject)


def test_all_f168_json_is_duplicate_free_and_source_hashes_are_exact():
    state = duplicate_free_json(STATE_PATH)
    gate = duplicate_free_json(GATE_PATH)
    post_gate = duplicate_free_json(POST_GATE_PATH)
    for binding in gate["source_bindings"].values():
        assert sha256(ROOT / binding["path"]) == binding["sha256"]
    assert state["state"] == INITIAL_STATE
    assert gate["authorization_state"] == INITIAL_STATE
    assert post_gate["POST_RUN_REVIEW_STATE"] == "NOT_RUN"
    assert post_gate["F168_EXECUTION_OCCURRED"] is False


def test_gate_scope_and_current_authority_are_exact_and_closed():
    gate = duplicate_free_json(GATE_PATH)
    json_scope = {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in EXPECTED_SCOPE.items()
    }
    assert gate["bounded_scope"] == json_scope
    assert gate["execution_gate"] == {
        "EXECUTION_GATE_OPEN": False,
        "RUNTIME_ACTIVATION_ALLOWED": False,
        "SEPARATE_F166_AUTHORIZE_EVIDENCE_REQUIRED": True,
        "SEPARATE_F168_INVOCATION_EVIDENCE_REQUIRED": True,
        "ATOMIC_PERSISTENT_ONE_SHOT_CLAIM_REQUIRED": True,
        "AUTO_RETRY_ALLOWED": False,
    }
    assert set(gate["protected_authority"].values()) == {False}
    assert gate["security_review"] == {
        "PASS": 16, "GAP": 0, "BLOCKED": 0, "COMMIT_READY": True
    }


def test_only_driver_or_helper_imports_runtime_capability_modules():
    runtime_modules = {
        "multiprocessing", "socket", "subprocess", "threading", "asyncio",
        "concurrent", "selectors", "ssl", "http", "urllib", "requests", "ctypes",
    }
    allowed = {DRIVER_PATH, HELPER_PATH}
    for path in NEW_PYTHON_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        if runtime_modules.intersection(imports):
            assert path in allowed


def test_runtime_construction_calls_are_never_at_import_time():
    forbidden_import_time_calls = {
        "socket", "Process", "Thread", "start", "connect", "bind", "listen",
        "accept", "get_context", "invoke_foundation168_once",
    }
    for path in (DRIVER_PATH, HELPER_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        top_level_calls = set()
        for statement in tree.body:
            for node in ast.walk(statement):
                if isinstance(statement, (ast.FunctionDef, ast.ClassDef, ast.If)):
                    break
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        top_level_calls.add(node.func.attr)
                    elif isinstance(node.func, ast.Name):
                        top_level_calls.add(node.func.id)
        assert forbidden_import_time_calls.isdisjoint(top_level_calls), path


def test_no_existing_production_entrypoint_imports_or_calls_f168():
    excluded = set(NEW_PYTHON_PATHS)
    for path in (ROOT / "coin").rglob("*.py"):
        if path in excluded:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        called = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    called.add(node.func.attr)
        assert not any("foundation168" in name for name in imported), path
        assert "invoke_foundation168_once" not in called, path


def test_explicit_helper_is_sole_future_invocation_entrypoint():
    definitions = []
    for path in NEW_PYTHON_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "invoke_foundation168_once"
            for node in ast.walk(tree)
        ):
            definitions.append(path)
    assert definitions == [HELPER_PATH]


def test_protected_hashes_and_exact_allowed_path_manifest():
    gate = duplicate_free_json(GATE_PATH)
    assert gate["protected_invariants"]["protocol_sha256"] == sha256(ROOT / "PROTOCOL.md")
    assert gate["protected_invariants"]["tx_validation_sha256"] == sha256(
        ROOT / "coin/tx_validation.py"
    )
    assert len(ALLOWED_NEW_PATHS) == 14
