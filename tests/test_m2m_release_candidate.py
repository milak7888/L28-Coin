# SPDX-License-Identifier: Apache-2.0
"""
Offline tests for Foundation 11 L28 M2M v0.1.0 release candidate manifest.

Verifies deterministic artifact inventory, frozen contracts, and manifest_id.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import unittest
from pathlib import Path
from typing import Any, Dict, List, Set

from coin.m2m_conformance_cli import (
    ADMISSION_PROFILE,
    ADMISSION_REPORT_VERSION,
    CLI_CODES,
    CLI_VERSION as CONFORMANCE_CLI_VERSION,
    EXIT_FAIL,
    EXIT_IDEMPOTENT,
    EXIT_INTERNAL,
    EXIT_PASS,
    EXIT_USAGE,
    PROFILE as CONFORMANCE_PROFILE,
    REPORT_VERSION as CONFORMANCE_REPORT_VERSION,
    _REGISTRY_EXIT0_CODES,
    _REGISTRY_EXIT1_CODES,
    _REGISTRY_EXIT2_CODES,
    _REGISTRY_EXIT4_CODES,
)
from coin.m2m_registry_audit import STABLE_CODES as AUDIT_CODES
from coin.m2m_registry_audit_cli import (
    CLI_VERSION as AUDIT_CLI_VERSION,
    EXIT_FAILURE,
    EXIT_PASS as AUDIT_EXIT_PASS,
    EXIT_USAGE as AUDIT_EXIT_USAGE,
    PROFILE as AUDIT_PROFILE,
    REPORT_VERSION as AUDIT_REPORT_VERSION,
    _EXIT_USAGE_CODES,
)
from coin.m2m_replay_registry import SCHEMA_VERSION, STABLE_CODES as REPLAY_CODES
from coin.m2m_transcript_validator import STABLE_CODES as TRANSCRIPT_CODES
from coin.m2m_verifier import (
    DOMAIN_MESSAGE,
    DOMAIN_PAYLOAD,
    DOMAIN_SIGNATURE,
    MESSAGE_TYPES,
    STABLE_CODES as VERIFIER_CODES,
    canonical_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs" / "m2m" / "release_manifest_v0.1.json"
DOMAIN_MANIFEST = b"L28-M2M-V0.1-RELEASE-MANIFEST\x00"

# Historical v0.1.0 release anchor (immutable after tag l28-m2m-v0.1.0).
# The Git tag is the canonical snapshot for recomputing all v0.1 artifact hashes.
HISTORICAL_MANIFEST_SHA256 = (
    "fc721c1c188b2f0a0ba28fe7e06fcb1f1812363c9d611bd42ebc93d34362ca6c"
)
HISTORICAL_MANIFEST_ID = (
    "8e2b21b55306b3e0dedc2a87a7c607d4440ff6ac92f0b6a4653f9be0ef392366"
)
HISTORICAL_ARTIFACT_COUNT = 40
HISTORICAL_INTENDED_TAG = "l28-m2m-v0.1.0"

MANIFEST_EXCLUDE_ONLY = "docs/m2m/release_manifest_v0.1.json"

RELEASE_NOTES_PATH = "docs/m2m/release_notes_v0.1.md"
COMPATIBILITY_POLICY_PATH = "docs/m2m/compatibility_policy_v0.1.md"
RELEASE_TEST_PATH = "tests/test_m2m_release_candidate.py"

EXPLICIT_DEPENDENCY_PATHS = (
    ".github/workflows/ci.yml",
    "requirements-m2m.txt",
    "PROTOCOL.md",
    "coin/tx_validation.py",
    "LICENSE",
    "NOTICE",
)

APPROVED_ROLES = frozenset(
    {
        "runtime",
        "normative_document",
        "test_vector",
        "conformance_test",
        "protocol_dependency",
        "dependency_lock",
        "ci",
        "legal",
        "release_document",
    }
)

FORBIDDEN_MANIFEST_KEYS = frozenset(
    {
        "timestamp",
        "hostname",
        "username",
        "pid",
        "commit",
        "branch",
        "generated_at",
    }
)

FORBIDDEN_VALUE_MARKERS = (
    "/Users/",
    "C:\\",
    "hostname",
    "username",
    "getpass",
)


def _manifest_domain_literal(domain: bytes) -> str:
    if not domain.endswith(b"\x00"):
        raise ValueError("domain separator must end with NUL")
    return domain[:-1].decode("utf-8") + "\\x00"


def _load_manifest() -> Dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _collect_expected_artifact_paths() -> List[str]:
    paths: List[Path] = []
    paths.extend(sorted((ROOT / "coin").glob("m2m_*.py")))
    paths.extend(sorted((ROOT / "docs" / "m2m").glob("*.md")))
    paths.extend(sorted((ROOT / "docs" / "m2m").glob("test_vectors*.json")))
    paths.extend(sorted((ROOT / "tests").glob("test_m2m_*.py")))
    for rel in EXPLICIT_DEPENDENCY_PATHS:
        paths.append(ROOT / rel)
    out: List[str] = []
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        if rel == MANIFEST_EXCLUDE_ONLY:
            continue
        out.append(rel)
    return sorted(out)


def _sha256_file(rel: str) -> tuple[str, int]:
    data = (ROOT / rel).read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def _compute_manifest_id(body: Dict[str, Any]) -> str:
    without_id = {k: v for k, v in body.items() if k != "manifest_id"}
    return hashlib.sha256(DOMAIN_MANIFEST + canonical_bytes(without_id)).hexdigest()


def _artifact_index(manifest: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {entry["path"]: entry for entry in manifest["artifacts"]}


def _collect_keys(obj: Any, out: Set[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            out.add(str(key))
            _collect_keys(value, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_keys(item, out)


def _expected_role(path: str) -> str:
    if path in {RELEASE_NOTES_PATH, COMPATIBILITY_POLICY_PATH}:
        return "release_document"
    if path.startswith("coin/m2m_") and path.endswith(".py"):
        return "runtime"
    if path.startswith("docs/m2m/") and path.endswith(".md"):
        return "normative_document"
    if path.startswith("docs/m2m/test_vectors") and path.endswith(".json"):
        return "test_vector"
    if path.startswith("tests/test_m2m_") and path.endswith(".py"):
        return "conformance_test"
    if path == ".github/workflows/ci.yml":
        return "ci"
    if path == "requirements-m2m.txt":
        return "dependency_lock"
    if path in {"PROTOCOL.md", "coin/tx_validation.py"}:
        return "protocol_dependency"
    if path in {"LICENSE", "NOTICE"}:
        return "legal"
    raise AssertionError(f"no approved role mapping for artifact path: {path}")


def _role_counts(manifest: Dict[str, Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {role: 0 for role in sorted(APPROVED_ROLES)}
    for entry in manifest["artifacts"]:
        role = entry["role"]
        counts[role] = counts.get(role, 0) + 1
    return counts


class ReleaseManifestStructureTests(unittest.TestCase):
    def test_required_top_level_fields(self) -> None:
        manifest = _load_manifest()
        required = (
            "manifest_version",
            "release_name",
            "release_version",
            "intended_tag",
            "status",
            "compatibility_profile",
            "hash_algorithm",
            "manifest_id_algorithm",
            "supported_runtime",
            "dependencies",
            "contracts",
            "artifacts",
            "manifest_id",
        )
        for field in required:
            self.assertIn(field, manifest)

    def test_release_identity(self) -> None:
        manifest = _load_manifest()
        self.assertEqual(manifest["manifest_version"], "l28-m2m-release-manifest/v0.1")
        self.assertEqual(manifest["release_name"], "L28 M2M v0.1.0")
        self.assertEqual(manifest["release_version"], "0.1.0")
        self.assertEqual(manifest["intended_tag"], "l28-m2m-v0.1.0")
        self.assertEqual(manifest["status"], "frozen")
        self.assertEqual(manifest["compatibility_profile"], "l28-m2m/v0.1")
        self.assertEqual(manifest["hash_algorithm"], "sha256_hex")

    def test_supported_runtime(self) -> None:
        manifest = _load_manifest()
        runtime = manifest["supported_runtime"]
        self.assertEqual(runtime["implementation"], "CPython")
        self.assertEqual(runtime["python_release_line"], "3.11")
        self.assertEqual(runtime["cryptography"], "cryptography==49.0.0")
        req_text = (ROOT / "requirements-m2m.txt").read_text(encoding="utf-8")
        self.assertIn(runtime["cryptography"], req_text)

    def test_dependencies(self) -> None:
        manifest = _load_manifest()
        deps = manifest["dependencies"]
        self.assertEqual(deps["requirements_m2m"], "requirements-m2m.txt")
        self.assertEqual(deps["l28_protocol"], "PROTOCOL.md")
        self.assertEqual(deps["ci_workflow"], ".github/workflows/ci.yml")
        self.assertEqual(deps["settlement_tx_id"]["module"], "coin.tx_validation")
        self.assertEqual(deps["settlement_tx_id"]["function"], "compute_tx_id")

    def test_no_forbidden_manifest_keys(self) -> None:
        keys: Set[str] = set()
        _collect_keys(_load_manifest(), keys)
        self.assertFalse(FORBIDDEN_MANIFEST_KEYS & keys)

    def test_no_forbidden_value_markers(self) -> None:
        text = MANIFEST_PATH.read_text(encoding="utf-8")
        lowered = text.lower()
        for marker in FORBIDDEN_VALUE_MARKERS:
            self.assertNotIn(marker.lower(), lowered)

    def test_manifest_file_is_valid_json_with_trailing_newline(self) -> None:
        raw = MANIFEST_PATH.read_bytes()
        self.assertTrue(raw.endswith(b"\n"))
        parsed = json.loads(raw.decode("utf-8"))
        self.assertIsInstance(parsed, dict)


class ReleaseManifestIdTests(unittest.TestCase):
    def test_manifest_id_recomputation(self) -> None:
        manifest = _load_manifest()
        expected = _compute_manifest_id(manifest)
        self.assertEqual(manifest["manifest_id"], expected)
        self.assertRegex(manifest["manifest_id"], r"^[0-9a-f]{64}$")

    def test_manifest_id_changes_when_body_tampered(self) -> None:
        manifest = _load_manifest()
        tampered = dict(manifest)
        tampered["release_version"] = "0.1.1"
        self.assertNotEqual(_compute_manifest_id(tampered), manifest["manifest_id"])


class ReleaseHistoricalManifestTests(unittest.TestCase):
    def test_historical_manifest_byte_identity(self) -> None:
        digest = hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
        self.assertEqual(digest, HISTORICAL_MANIFEST_SHA256)

    def test_historical_manifest_id(self) -> None:
        manifest = _load_manifest()
        self.assertEqual(manifest["manifest_id"], HISTORICAL_MANIFEST_ID)
        self.assertEqual(_compute_manifest_id(manifest), HISTORICAL_MANIFEST_ID)

    def test_historical_manifest_self_exclusion(self) -> None:
        paths = {entry["path"] for entry in _load_manifest()["artifacts"]}
        self.assertNotIn(MANIFEST_EXCLUDE_ONLY, paths)

    def test_historical_artifact_count(self) -> None:
        self.assertEqual(len(_load_manifest()["artifacts"]), HISTORICAL_ARTIFACT_COUNT)

    def test_historical_intended_tag(self) -> None:
        self.assertEqual(_load_manifest()["intended_tag"], HISTORICAL_INTENDED_TAG)


class ReleaseArtifactInventoryTests(unittest.TestCase):
    def test_frozen_manifest_artifact_roles_are_explicit(self) -> None:
        for entry in _load_manifest()["artifacts"]:
            self.assertIn(entry["role"], APPROVED_ROLES, entry["path"])
            self.assertTrue(str(entry["role"]).strip(), entry["path"])

    def test_frozen_manifest_release_documents_present(self) -> None:
        index = _artifact_index(_load_manifest())
        self.assertIn(RELEASE_NOTES_PATH, index)
        self.assertEqual(index[RELEASE_NOTES_PATH]["role"], "release_document")
        self.assertIn(COMPATIBILITY_POLICY_PATH, index)
        self.assertEqual(index[COMPATIBILITY_POLICY_PATH]["role"], "release_document")
        self.assertIn(RELEASE_TEST_PATH, index)
        self.assertEqual(index[RELEASE_TEST_PATH]["role"], "conformance_test")

    def test_artifacts_sorted_lexicographically(self) -> None:
        manifest = _load_manifest()
        paths = [entry["path"] for entry in manifest["artifacts"]]
        self.assertEqual(paths, sorted(paths))

    def test_all_artifacts_have_required_fields(self) -> None:
        for entry in _load_manifest()["artifacts"]:
            self.assertIn("path", entry)
            self.assertIn("role", entry)
            self.assertIn("sha256", entry)
            self.assertIsInstance(entry["path"], str)
            self.assertIsInstance(entry["role"], str)
            self.assertIsInstance(entry["sha256"], str)

    def test_all_roles_non_empty(self) -> None:
        for entry in _load_manifest()["artifacts"]:
            role = entry.get("role")
            self.assertIsInstance(role, str, entry["path"])
            self.assertTrue(role.strip(), entry["path"])

    def test_all_roles_in_approved_set(self) -> None:
        for entry in _load_manifest()["artifacts"]:
            self.assertIn(entry["role"], APPROVED_ROLES, entry["path"])

    def test_role_counts_sum_to_artifact_total(self) -> None:
        manifest = _load_manifest()
        counts = _role_counts(manifest)
        self.assertEqual(sum(counts.values()), len(manifest["artifacts"]))
        self.assertEqual(len(manifest["artifacts"]), HISTORICAL_ARTIFACT_COUNT)


class ReleaseContractTests(unittest.TestCase):
    def test_envelope_and_suite(self) -> None:
        contracts = _load_manifest()["contracts"]
        self.assertEqual(contracts["envelope_protocol_version"], "0.1")
        self.assertEqual(contracts["signature_suite"], "ed25519")
        self.assertEqual(contracts["canonical_json"], "L28-M2M Canonical JSON v0.1")
        self.assertEqual(set(contracts["message_types"]), set(MESSAGE_TYPES))

    def test_domain_separators(self) -> None:
        separators = _load_manifest()["contracts"]["domain_separators"]
        self.assertEqual(separators["payload"], _manifest_domain_literal(DOMAIN_PAYLOAD))
        self.assertEqual(separators["message"], _manifest_domain_literal(DOMAIN_MESSAGE))
        self.assertEqual(separators["signature"], _manifest_domain_literal(DOMAIN_SIGNATURE))
        self.assertEqual(
            separators["release_manifest"],
            _manifest_domain_literal(DOMAIN_MANIFEST),
        )

    def test_registry_schema_version(self) -> None:
        self.assertEqual(
            _load_manifest()["contracts"]["registry_schema_version"],
            SCHEMA_VERSION,
        )

    def test_stable_result_codes(self) -> None:
        codes = _load_manifest()["contracts"]["stable_result_codes"]
        self.assertEqual(set(codes["verifier"]), set(VERIFIER_CODES))
        self.assertEqual(set(codes["transcript_validator"]), set(TRANSCRIPT_CODES))
        self.assertEqual(set(codes["replay_registry"]), set(REPLAY_CODES))
        self.assertEqual(set(codes["registry_audit"]), set(AUDIT_CODES))
        self.assertEqual(set(codes["conformance_cli"]), set(CLI_CODES))

    def test_report_profiles(self) -> None:
        profiles = _load_manifest()["contracts"]["report_profiles"]
        self.assertEqual(profiles["conformance"]["report_version"], CONFORMANCE_REPORT_VERSION)
        self.assertEqual(profiles["conformance"]["profile"], CONFORMANCE_PROFILE)
        self.assertEqual(profiles["admission"]["report_version"], ADMISSION_REPORT_VERSION)
        self.assertEqual(profiles["admission"]["profile"], ADMISSION_PROFILE)
        self.assertEqual(profiles["registry_audit"]["report_version"], AUDIT_REPORT_VERSION)
        self.assertEqual(profiles["registry_audit"]["profile"], AUDIT_PROFILE)

    def test_cli_contracts(self) -> None:
        cli = _load_manifest()["contracts"]["cli"]
        conf = cli["conformance"]
        self.assertEqual(conf["version"], CONFORMANCE_CLI_VERSION)
        self.assertEqual(conf["exit_codes"]["pass"], EXIT_PASS)
        self.assertEqual(conf["exit_codes"]["fail"], EXIT_FAIL)
        self.assertEqual(conf["exit_codes"]["usage"], EXIT_USAGE)
        self.assertEqual(conf["exit_codes"]["internal"], EXIT_INTERNAL)
        self.assertEqual(conf["exit_codes"]["idempotent"], EXIT_IDEMPOTENT)
        self.assertEqual(set(conf["registry_exit_codes"]["pass"]), set(_REGISTRY_EXIT0_CODES))
        self.assertEqual(set(conf["registry_exit_codes"]["fail"]), set(_REGISTRY_EXIT1_CODES))
        self.assertEqual(set(conf["registry_exit_codes"]["usage"]), set(_REGISTRY_EXIT2_CODES))
        self.assertEqual(set(conf["registry_exit_codes"]["idempotent"]), set(_REGISTRY_EXIT4_CODES))

        audit = cli["registry_audit"]
        self.assertEqual(audit["version"], AUDIT_CLI_VERSION)
        self.assertEqual(audit["exit_codes"]["pass"], AUDIT_EXIT_PASS)
        self.assertEqual(audit["exit_codes"]["usage"], AUDIT_EXIT_USAGE)
        self.assertEqual(audit["exit_codes"]["failure"], EXIT_FAILURE)
        self.assertEqual(set(audit["usage_codes"]), set(_EXIT_USAGE_CODES))

    def test_settlement_dependency_importable(self) -> None:
        tx_validation = importlib.import_module("coin.tx_validation")
        self.assertTrue(callable(tx_validation.compute_tx_id))


class ReleaseManifestDeterminismTests(unittest.TestCase):
    def test_manifest_json_sorted_keys(self) -> None:
        raw = MANIFEST_PATH.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        self.assertEqual(raw, json.dumps(parsed, sort_keys=True, indent=2, ensure_ascii=False) + "\n")

    def test_manifest_id_algorithm_documented(self) -> None:
        manifest = _load_manifest()
        self.assertIn("L28-M2M-V0.1-RELEASE-MANIFEST", manifest["manifest_id_algorithm"])
        self.assertIn("manifest object excluding manifest_id", manifest["manifest_id_algorithm"])

    def test_release_docs_do_not_embed_manifest_id_value(self) -> None:
        manifest_id = _load_manifest()["manifest_id"]
        for rel in (RELEASE_NOTES_PATH, COMPATIBILITY_POLICY_PATH):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn(manifest_id, text)


if __name__ == "__main__":
    unittest.main()
