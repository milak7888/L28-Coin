# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "docs/l28_foundation164_live_adapter_candidate_gate_v0.1.json"
NEW_PYTHON_PATHS = (
    ROOT / "coin/future_live_adapter_candidate.py",
    ROOT / "coin/future_live_adapter_terminalization.py",
    ROOT / "tests/test_foundation164_live_adapter_candidate.py",
    ROOT / "tests/test_foundation164_live_adapter_security.py",
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_gate():
    return json.loads(GATE_PATH.read_text(encoding="utf-8"))


def test_all_historical_source_bindings_and_candidate_hashes_are_exact():
    gate = load_gate()
    for binding in gate["source_bindings"].values():
        assert sha256(ROOT / binding["path"]) == binding["sha256"]
    for binding in gate["candidate_bindings"].values():
        assert sha256(ROOT / binding["path"]) == binding["sha256"]
    assert gate["historical_state"] == {
        "F159_RESULT": "ABORT",
        "ROOT_CAUSE": "NOT_PROVEN",
        "SEMLOCK_EVIDENCE_CLASSIFICATION": (
            "OPERATOR_OBSERVED_NOT_MACHINE_PERSISTED"
        ),
        "F159_RETRY_FORBIDDEN": True,
    }
    assert gate["protected_invariants"]["protocol_sha256"] == sha256(
        ROOT / "PROTOCOL.md"
    )
    assert gate["protected_invariants"]["tx_validation_sha256"] == sha256(
        ROOT / "coin/tx_validation.py"
    )


def test_gate_json_has_no_duplicate_keys():
    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            assert key not in result, key
            result[key] = value
        return result

    json.loads(
        GATE_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )


def test_f164_python_capability_firewall():
    forbidden_imports = {
        "multiprocessing",
        "socket",
        "subprocess",
        "threading",
        "asyncio",
        "concurrent",
        "selectors",
        "ssl",
        "http",
        "urllib",
        "requests",
        "ctypes",
    }
    forbidden_calls = {
        "start",
        "fork",
        "spawn",
        "connect",
        "bind",
        "listen",
        "accept",
        "send",
        "sendall",
        "recv",
        "terminate",
        "kill",
        "Popen",
        "system",
        "exec",
        "run_authorized_experiment_once",
    }
    for path in NEW_PYTHON_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        calls = set()
        dynamic_imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
                elif isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                    if node.func.id in {"__import__", "eval"}:
                        dynamic_imports.add(node.func.id)
        assert forbidden_imports.isdisjoint(imports)
        assert forbidden_calls.isdisjoint(calls)
        assert not dynamic_imports


def test_no_existing_python_entrypoint_imports_f164_candidate():
    forbidden_modules = {
        "coin.future_live_adapter_candidate",
        "coin.future_live_adapter_terminalization",
        "future_live_adapter_candidate",
        "future_live_adapter_terminalization",
    }
    excluded = set(NEW_PYTHON_PATHS)
    for path in ROOT.rglob("*.py"):
        if path in excluded:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        assert forbidden_modules.isdisjoint(imported), path


def test_authority_offline_and_review_state_are_exact():
    gate = load_gate()
    assert gate["authority"] == {
        "NEW_AUTHORIZATION_REQUIRED": True,
        "SEPARATE_SECURITY_REVIEW_REQUIRED": True,
        "SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED": True,
        "F159_RETRY_FORBIDDEN": True,
        "OLD_AUTHORIZATION_REUSABLE": False,
        "F161_EXECUTION_AUTHORIZED": False,
        "F162_EXECUTION_AUTHORIZED": False,
        "F163_EXECUTION_AUTHORIZED": False,
        "F164_EXECUTION_AUTHORIZED": False,
    }
    assert gate["offline_boundary"] == {
        "NO_EXECUTION_OCCURRED": True,
        "PROCESSES_STARTED": False,
        "THREADS_STARTED": False,
        "SOCKETS_OPENED": False,
        "NETWORK_TRAFFIC_USED": False,
        "SIGNING_ACTIVITY": False,
        "AUTHORIZATION_GRANTED": False,
        "AUTHORIZATION_CONSUMED": False,
    }
    assert set(gate["protected_authority"].values()) == {False}
    assert gate["review_result"] == {
        "PASS": 13,
        "GAP": 0,
        "BLOCKED": 0,
        "COMMIT_READY": True,
        "NON_ACTIVATING": True,
    }
