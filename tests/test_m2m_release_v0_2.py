# SPDX-License-Identifier: Apache-2.0
"""
Offline tests for Foundation 13 L28 M2M v0.2.0 release candidate manifest.

Independently verifies dual-manifest anchoring, artifact inventory, contracts,
and manifest_id determinism.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import re
import unittest
from pathlib import Path
from typing import Any, Dict, List, Set

from coin.m2m_conformance_cli import (
    ADMISSION_PROFILE,
    ADMISSION_REPORT_VERSION,
    CLI_CODES,
    CLI_VERSION as CONFORMANCE_CLI_VERSION,
    DOMAIN_ADMISSION_REPORT,
    DOMAIN_REPORT,
    EXIT_FAIL,
    EXIT_IDEMPOTENT,
    EXIT_INTERNAL,
    EXIT_PASS,
    EXIT_USAGE,
    MAX_INPUT_BYTES,
    PROFILE as CONFORMANCE_PROFILE,
    REPORT_VERSION as CONFORMANCE_REPORT_VERSION,
    _REGISTRY_EXIT0_CODES,
    _REGISTRY_EXIT1_CODES,
    _REGISTRY_EXIT2_CODES,
    _REGISTRY_EXIT4_CODES,
)
from coin.m2m_registry_audit import (
    MAX_REGISTRY_EXCHANGES,
    MAX_REGISTRY_FILE_BYTES,
    MAX_REGISTRY_MESSAGES,
    STABLE_CODES as AUDIT_CODES,
)
from coin.m2m_registry_audit_cli import (
    CLI_VERSION as AUDIT_CLI_VERSION,
    DOMAIN_REPORT as AUDIT_DOMAIN_REPORT,
    EXIT_FAILURE,
    EXIT_PASS as AUDIT_EXIT_PASS,
    EXIT_USAGE as AUDIT_EXIT_USAGE,
    PROFILE as AUDIT_PROFILE,
    REPORT_VERSION as AUDIT_REPORT_VERSION,
    _EXIT_USAGE_CODES as AUDIT_USAGE_CODES,
)
from coin.m2m_registry_backup import (
    DOMAIN_BACKUP_REPORT,
    PROFILE as BACKUP_PROFILE,
    REPORT_VERSION as BACKUP_REPORT_VERSION,
    STABLE_CODES as BACKUP_CODES,
    _EXIT_USAGE_CODES as BACKUP_USAGE_CODES,
)
from coin.m2m_registry_backup_cli import (
    CLI_VERSION as BACKUP_CLI_VERSION,
    EXIT_FAILURE as BACKUP_EXIT_FAILURE,
    EXIT_PASS as BACKUP_EXIT_PASS,
    EXIT_USAGE as BACKUP_EXIT_USAGE,
)
from coin.m2m_replay_registry import (
    DOMAIN_EXCHANGE,
    DOMAIN_TRANSCRIPT,
    SCHEMA_VERSION,
    STABLE_CODES as REPLAY_CODES,
)
from coin.m2m_transcript_validator import MAX_TRANSCRIPT_MESSAGES, STABLE_CODES as TRANSCRIPT_CODES
from coin.m2m_verifier import (
    DOMAIN_MESSAGE,
    DOMAIN_PAYLOAD,
    DOMAIN_SIGNATURE,
    MESSAGE_TYPES,
    STABLE_CODES as VERIFIER_CODES,
    canonical_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_V01_PATH = ROOT / "docs" / "m2m" / "release_manifest_v0.1.json"
MANIFEST_PATH = ROOT / "docs" / "m2m" / "release_manifest_v0.2.json"
DOMAIN_MANIFEST_V01 = b"L28-M2M-V0.1-RELEASE-MANIFEST\x00"
DOMAIN_MANIFEST = b"L28-M2M-V0.2-RELEASE-MANIFEST\x00"

HISTORICAL_MANIFEST_SHA256 = (
    "fc721c1c188b2f0a0ba28fe7e06fcb1f1812363c9d611bd42ebc93d34362ca6c"
)
HISTORICAL_MANIFEST_ID = (
    "8e2b21b55306b3e0dedc2a87a7c607d4440ff6ac92f0b6a4653f9be0ef392366"
)
HISTORICAL_TAG = "l28-m2m-v0.1.0"
HISTORICAL_COMMIT = "7215d585a38155b5a36e7ebe077dcad43e810388"
HISTORICAL_MANIFEST_PATH = "docs/m2m/release_manifest_v0.1.json"

MANIFEST_EXCLUDE_ONLY = "docs/m2m/release_manifest_v0.2.json"

RELEASE_NOTES_V01 = "docs/m2m/release_notes_v0.1.md"
COMPATIBILITY_POLICY_V01 = "docs/m2m/compatibility_policy_v0.1.md"
RELEASE_NOTES_V02 = "docs/m2m/release_notes_v0.2.md"
COMPATIBILITY_V02 = "docs/m2m/release_compatibility_v0.2.md"
RELEASE_TEST_V01 = "tests/test_m2m_release_candidate.py"
RELEASE_TEST_V02 = "tests/test_m2m_release_v0_2.py"
README_PATH = "docs/m2m/README.md"

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
        "historical_release_manifest",
    }
)

ARTIFACT_FIELDS = frozenset({"path", "role", "sha256", "size_bytes"})

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

PRIVATE_KEY_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b[0-9a-f]{64}\b.*\bseed\b", re.IGNORECASE),
)

TAG_EXISTS_CLAIMS = (
    "tag `l28-m2m-v0.2.0` has been",
    "github release for v0.2.0",
    "published at tag l28-m2m-v0.2.0",
)


def _manifest_domain_literal(domain: bytes) -> str:
    if not domain.endswith(b"\x00"):
        raise ValueError("domain separator must end with NUL")
    return domain[:-1].decode("utf-8") + "\\x00"


def _load_manifest() -> Dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _load_manifest_v01() -> Dict[str, Any]:
    return json.loads(MANIFEST_V01_PATH.read_text(encoding="utf-8"))


def _collect_expected_artifact_paths() -> List[str]:
    paths: List[Path] = []
    paths.extend(sorted((ROOT / "coin").glob("m2m_*.py")))
    paths.extend(sorted((ROOT / "docs" / "m2m").glob("*.md")))
    paths.extend(sorted((ROOT / "docs" / "m2m").glob("test_vectors*.json")))
    paths.extend(sorted((ROOT / "tests").glob("test_m2m_*.py")))
    paths.append(ROOT / HISTORICAL_MANIFEST_PATH)
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
    if path == HISTORICAL_MANIFEST_PATH:
        return "historical_release_manifest"
    if path in {
        RELEASE_NOTES_V01,
        COMPATIBILITY_POLICY_V01,
        RELEASE_NOTES_V02,
        COMPATIBILITY_V02,
    }:
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


def _reject_duplicate_keys(pairs: List[tuple[str, Any]]) -> Dict[str, Any]:
    seen: Set[str] = set()
    out: Dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate key: {key}")
        seen.add(key)
        out[key] = value
    return out


class ReleaseV02ManifestStructureTests(unittest.TestCase):
    def test_required_top_level_fields(self) -> None:
        manifest = _load_manifest()
        required = (
            "manifest_version",
            "release_name",
            "release_version",
            "intended_tag",
            "status",
            "release_compatibility_profile",
            "protocol_profile",
            "hash_algorithm",
            "manifest_id_domain",
            "prior_release",
            "tested_python",
            "dependency_requirements",
            "public_contracts",
            "artifacts",
            "manifest_id",
        )
        for field in required:
            self.assertIn(field, manifest)

    def test_release_identity(self) -> None:
        manifest = _load_manifest()
        self.assertEqual(manifest["manifest_version"], "l28-m2m-release-manifest/v0.2")
        self.assertEqual(manifest["release_name"], "L28 M2M v0.2.0")
        self.assertEqual(manifest["release_version"], "0.2.0")
        self.assertEqual(manifest["intended_tag"], "l28-m2m-v0.2.0")
        self.assertEqual(manifest["status"], "frozen")
        self.assertEqual(
            manifest["release_compatibility_profile"],
            "l28-m2m-release-compatibility/v0.2",
        )
        self.assertEqual(manifest["protocol_profile"], "l28-m2m/v0.1")
        self.assertEqual(manifest["hash_algorithm"], "sha256_hex")
        self.assertEqual(
            manifest["manifest_id_domain"],
            _manifest_domain_literal(DOMAIN_MANIFEST),
        )

    def test_prior_release_anchor(self) -> None:
        prior = _load_manifest()["prior_release"]
        self.assertEqual(prior["tag"], HISTORICAL_TAG)
        self.assertEqual(prior["commit"], HISTORICAL_COMMIT)
        self.assertEqual(prior["manifest_id"], HISTORICAL_MANIFEST_ID)
        self.assertEqual(prior["manifest_sha256"], HISTORICAL_MANIFEST_SHA256)
        self.assertEqual(prior["manifest_path"], HISTORICAL_MANIFEST_PATH)

    def test_tested_python(self) -> None:
        tested = _load_manifest()["tested_python"]
        self.assertEqual(tested["implementation"], "CPython")
        self.assertEqual(tested["python_release_line"], "3.11")

    def test_dependency_requirements(self) -> None:
        deps = _load_manifest()["dependency_requirements"]
        self.assertEqual(deps["cryptography"], "cryptography==49.0.0")
        self.assertEqual(deps["requirements_m2m"], "requirements-m2m.txt")
        self.assertEqual(deps["settlement_tx_id"]["module"], "coin.tx_validation")
        self.assertEqual(deps["settlement_tx_id"]["function"], "compute_tx_id")
        req_text = (ROOT / "requirements-m2m.txt").read_text(encoding="utf-8")
        self.assertIn(deps["cryptography"], req_text)

    def test_no_forbidden_manifest_keys(self) -> None:
        manifest = _load_manifest()
        keys: Set[str] = set(manifest.keys())
        self.assertFalse(FORBIDDEN_MANIFEST_KEYS & keys)
        prior = manifest["prior_release"]
        self.assertEqual(
            set(prior.keys()),
            {"tag", "commit", "manifest_path", "manifest_id", "manifest_sha256"},
        )
        self.assertEqual(prior["commit"], HISTORICAL_COMMIT)

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

    def test_manifest_has_no_duplicate_keys_when_parsed_strictly(self) -> None:
        raw = MANIFEST_PATH.read_text(encoding="utf-8")
        parsed = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
        self.assertIsInstance(parsed, dict)

    def test_strict_duplicate_key_rejection_helper(self) -> None:
        with self.assertRaises(ValueError):
            json.loads('{"a":1,"a":2}', object_pairs_hook=_reject_duplicate_keys)


class ReleaseV02HistoricalManifestTests(unittest.TestCase):
    def test_v01_manifest_byte_identity(self) -> None:
        digest = hashlib.sha256(MANIFEST_V01_PATH.read_bytes()).hexdigest()
        self.assertEqual(digest, HISTORICAL_MANIFEST_SHA256)

    def test_v01_manifest_id_unchanged(self) -> None:
        manifest = _load_manifest_v01()
        without_id = {k: v for k, v in manifest.items() if k != "manifest_id"}
        expected = hashlib.sha256(
            DOMAIN_MANIFEST_V01 + canonical_bytes(without_id)
        ).hexdigest()
        self.assertEqual(manifest["manifest_id"], HISTORICAL_MANIFEST_ID)
        self.assertEqual(expected, HISTORICAL_MANIFEST_ID)

    def test_v01_manifest_included_as_historical(self) -> None:
        index = _artifact_index(_load_manifest())
        self.assertIn(HISTORICAL_MANIFEST_PATH, index)
        self.assertEqual(index[HISTORICAL_MANIFEST_PATH]["role"], "historical_release_manifest")
        digest, size = _sha256_file(HISTORICAL_MANIFEST_PATH)
        self.assertEqual(index[HISTORICAL_MANIFEST_PATH]["sha256"], digest)
        self.assertEqual(index[HISTORICAL_MANIFEST_PATH]["size_bytes"], size)


class ReleaseV02ManifestIdTests(unittest.TestCase):
    def test_manifest_id_recomputation(self) -> None:
        manifest = _load_manifest()
        expected = _compute_manifest_id(manifest)
        self.assertEqual(manifest["manifest_id"], expected)
        self.assertRegex(manifest["manifest_id"], r"^[0-9a-f]{64}$")

    def test_manifest_id_changes_when_body_tampered(self) -> None:
        manifest = _load_manifest()
        tampered = dict(manifest)
        tampered["release_version"] = "0.2.1"
        self.assertNotEqual(_compute_manifest_id(tampered), manifest["manifest_id"])

    def test_manifest_excludes_only_itself(self) -> None:
        paths = {entry["path"] for entry in _load_manifest()["artifacts"]}
        self.assertNotIn(MANIFEST_EXCLUDE_ONLY, paths)
        self.assertIn(HISTORICAL_MANIFEST_PATH, paths)


class ReleaseV02ArtifactInventoryTests(unittest.TestCase):
    def test_independent_inventory_matches_manifest(self) -> None:
        expected_paths = _collect_expected_artifact_paths()
        manifest_paths = [entry["path"] for entry in _load_manifest()["artifacts"]]
        self.assertEqual(manifest_paths, expected_paths)

    def test_artifacts_sorted_lexicographically(self) -> None:
        paths = [entry["path"] for entry in _load_manifest()["artifacts"]]
        self.assertEqual(paths, sorted(paths))

    def test_no_duplicate_paths(self) -> None:
        paths = [entry["path"] for entry in _load_manifest()["artifacts"]]
        self.assertEqual(len(paths), len(set(paths)))

    def test_all_artifacts_have_exact_fields(self) -> None:
        for entry in _load_manifest()["artifacts"]:
            self.assertEqual(set(entry.keys()), ARTIFACT_FIELDS, entry["path"])

    def test_all_roles_expected_and_non_empty(self) -> None:
        for entry in _load_manifest()["artifacts"]:
            role = entry["role"]
            self.assertIsInstance(role, str, entry["path"])
            self.assertTrue(role.strip(), entry["path"])
            self.assertIn(role, APPROVED_ROLES, entry["path"])
            self.assertEqual(role, _expected_role(entry["path"]), entry["path"])

    def test_role_counts_sum_to_artifact_total(self) -> None:
        manifest = _load_manifest()
        counts = _role_counts(manifest)
        self.assertEqual(sum(counts.values()), len(manifest["artifacts"]))
        self.assertEqual(len(manifest["artifacts"]), len(_collect_expected_artifact_paths()))

    def test_every_digest_and_size_recomputes(self) -> None:
        for entry in _load_manifest()["artifacts"]:
            digest, size = _sha256_file(entry["path"])
            self.assertEqual(entry["sha256"], digest, entry["path"])
            self.assertEqual(entry["size_bytes"], size, entry["path"])
            self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")

    def test_no_traversal_absolute_paths_symlinks_or_directories(self) -> None:
        for entry in _load_manifest()["artifacts"]:
            rel = entry["path"]
            self.assertFalse(rel.startswith("/"), rel)
            self.assertNotIn("..", rel.split("/"), rel)
            path = ROOT / rel
            self.assertTrue(path.is_file(), rel)
            self.assertFalse(path.is_symlink(), rel)

    def test_release_documents_present(self) -> None:
        index = _artifact_index(_load_manifest())
        for rel, role in (
            (RELEASE_NOTES_V01, "release_document"),
            (COMPATIBILITY_POLICY_V01, "release_document"),
            (RELEASE_NOTES_V02, "release_document"),
            (COMPATIBILITY_V02, "release_document"),
            (RELEASE_TEST_V01, "conformance_test"),
            (RELEASE_TEST_V02, "conformance_test"),
        ):
            self.assertIn(rel, index)
            self.assertEqual(index[rel]["role"], role)


class ReleaseV02ContractTests(unittest.TestCase):
    def test_envelope_and_suite(self) -> None:
        contracts = _load_manifest()["public_contracts"]
        self.assertEqual(contracts["envelope_protocol_version"], "0.1")
        self.assertEqual(contracts["signature_suite"], "ed25519")
        self.assertEqual(contracts["canonical_json"], "L28-M2M Canonical JSON v0.1")
        self.assertEqual(set(contracts["message_types"]), set(MESSAGE_TYPES))

    def test_domain_separators(self) -> None:
        separators = _load_manifest()["public_contracts"]["domain_separators"]
        self.assertEqual(separators["payload"], _manifest_domain_literal(DOMAIN_PAYLOAD))
        self.assertEqual(separators["message"], _manifest_domain_literal(DOMAIN_MESSAGE))
        self.assertEqual(separators["signature"], _manifest_domain_literal(DOMAIN_SIGNATURE))
        self.assertEqual(
            separators["release_manifest_v0_1"],
            _manifest_domain_literal(DOMAIN_MANIFEST_V01),
        )
        self.assertEqual(
            separators["release_manifest_v0_2"],
            _manifest_domain_literal(DOMAIN_MANIFEST),
        )
        self.assertEqual(
            separators["conformance_report"],
            _manifest_domain_literal(DOMAIN_REPORT),
        )
        self.assertEqual(
            separators["admission_report"],
            _manifest_domain_literal(DOMAIN_ADMISSION_REPORT),
        )
        self.assertEqual(
            separators["registry_audit_report"],
            _manifest_domain_literal(AUDIT_DOMAIN_REPORT),
        )
        self.assertEqual(
            separators["registry_backup_report"],
            _manifest_domain_literal(DOMAIN_BACKUP_REPORT),
        )
        self.assertEqual(
            separators["replay_exchange"],
            _manifest_domain_literal(DOMAIN_EXCHANGE),
        )
        self.assertEqual(
            separators["replay_transcript"],
            _manifest_domain_literal(DOMAIN_TRANSCRIPT),
        )

    def test_transcript_and_registry_bounds(self) -> None:
        contracts = _load_manifest()["public_contracts"]
        self.assertEqual(contracts["transcript_max_messages"], MAX_TRANSCRIPT_MESSAGES)
        self.assertEqual(contracts["registry_schema_version"], SCHEMA_VERSION)
        bounds = contracts["registry_bounds"]
        self.assertEqual(bounds["max_file_bytes"], MAX_REGISTRY_FILE_BYTES)
        self.assertEqual(bounds["max_exchanges"], MAX_REGISTRY_EXCHANGES)
        self.assertEqual(bounds["max_messages"], MAX_REGISTRY_MESSAGES)
        self.assertEqual(contracts["conformance_max_input_bytes"], MAX_INPUT_BYTES)

    def test_stable_result_codes(self) -> None:
        codes = _load_manifest()["public_contracts"]["stable_result_codes"]
        self.assertEqual(set(codes["verifier"]), set(VERIFIER_CODES))
        self.assertEqual(set(codes["transcript_validator"]), set(TRANSCRIPT_CODES))
        self.assertEqual(set(codes["replay_registry"]), set(REPLAY_CODES))
        self.assertEqual(set(codes["registry_audit"]), set(AUDIT_CODES))
        self.assertEqual(set(codes["conformance_cli"]), set(CLI_CODES))
        self.assertEqual(set(codes["registry_backup"]), set(BACKUP_CODES))
        self.assertEqual(len(codes["registry_backup"]), 23)

    def test_report_profiles(self) -> None:
        profiles = _load_manifest()["public_contracts"]["report_profiles"]
        self.assertEqual(profiles["conformance"]["report_version"], CONFORMANCE_REPORT_VERSION)
        self.assertEqual(profiles["conformance"]["profile"], CONFORMANCE_PROFILE)
        self.assertEqual(profiles["admission"]["report_version"], ADMISSION_REPORT_VERSION)
        self.assertEqual(profiles["admission"]["profile"], ADMISSION_PROFILE)
        self.assertEqual(profiles["registry_audit"]["report_version"], AUDIT_REPORT_VERSION)
        self.assertEqual(profiles["registry_audit"]["profile"], AUDIT_PROFILE)
        self.assertEqual(profiles["registry_backup"]["report_version"], BACKUP_REPORT_VERSION)
        self.assertEqual(profiles["registry_backup"]["profile"], BACKUP_PROFILE)

    def test_cli_contracts(self) -> None:
        cli = _load_manifest()["public_contracts"]["cli"]
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
        self.assertEqual(set(audit["usage_codes"]), set(AUDIT_USAGE_CODES))

        backup = cli["registry_backup"]
        self.assertEqual(backup["version"], BACKUP_CLI_VERSION)
        self.assertEqual(backup["exit_codes"]["pass"], BACKUP_EXIT_PASS)
        self.assertEqual(backup["exit_codes"]["usage"], BACKUP_EXIT_USAGE)
        self.assertEqual(backup["exit_codes"]["failure"], BACKUP_EXIT_FAILURE)
        self.assertEqual(set(backup["usage_codes"]), set(BACKUP_USAGE_CODES))

    def test_backup_publication_contract(self) -> None:
        backup = _load_manifest()["public_contracts"]["registry_backup"]
        self.assertEqual(backup["output_permission_mode"], "0600")
        self.assertTrue(backup["quiescence_required"])
        self.assertEqual(backup["backup_equality"], "logical_registry_state")
        self.assertEqual(backup["restore_equality"], "raw_byte_identity")
        publication = backup["publication"]
        self.assertEqual(publication["primitive"], "os.link")
        self.assertTrue(publication["follow_symlinks_false"])
        self.assertFalse(publication["uses_os_rename"])
        self.assertFalse(publication["uses_os_replace"])

    def test_settlement_dependency_importable(self) -> None:
        tx_validation = importlib.import_module("coin.tx_validation")
        self.assertTrue(callable(tx_validation.compute_tx_id))


class ReleaseV02ImplementationContractTests(unittest.TestCase):
    def test_backup_module_uses_link_not_rename_or_replace(self) -> None:
        source = (ROOT / "coin" / "m2m_registry_backup.py").read_text(encoding="utf-8")
        self.assertIn("os.link(", source)
        self.assertNotIn("os.rename(", source)
        self.assertNotIn("os.replace(", source)

    def test_backup_cli_exit_semantics(self) -> None:
        from coin.m2m_registry_backup_cli import _exit_for_result
        from coin.m2m_registry_backup import RegistryBackupResult

        ok = RegistryBackupResult(
            ok=True,
            code="backup_created",
            operation="backup",
            destination_created=True,
        )
        self.assertEqual(_exit_for_result(ok), BACKUP_EXIT_PASS)
        usage = RegistryBackupResult(
            ok=False,
            code="destination_exists",
            operation="backup",
        )
        self.assertEqual(_exit_for_result(usage), BACKUP_EXIT_USAGE)
        fail = RegistryBackupResult(
            ok=False,
            code="backup_failed",
            operation="backup",
        )
        self.assertEqual(_exit_for_result(fail), BACKUP_EXIT_FAILURE)


class ReleaseV02VectorTests(unittest.TestCase):
    def test_all_vectors_parse_without_duplicate_keys(self) -> None:
        for path in sorted((ROOT / "docs" / "m2m").glob("test_vectors*.json")):
            raw = path.read_text(encoding="utf-8")
            parsed = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
            self.assertIsInstance(parsed, dict, path.name)


class ReleaseV02DocumentTests(unittest.TestCase):
    def test_release_notes_required_content(self) -> None:
        text = (ROOT / RELEASE_NOTES_V02).read_text(encoding="utf-8")
        self.assertIn("v0.2.0", text)
        self.assertIn("release candidate", text.lower())
        self.assertIn("l28-m2m/v0.1", text)
        self.assertIn("l28-m2m-replay-registry-backup/v0.1", text)
        self.assertIn("os.link", text)
        self.assertIn("quiescent", text.lower())
        self.assertIn(HISTORICAL_TAG, text)
        self.assertIn("l28-m2m-v0.2.0", text)
        self.assertNotIn("tag has been created", text.lower())
        self.assertNotIn(_load_manifest()["manifest_id"], text)

    def test_compatibility_document_distinctions(self) -> None:
        text = (ROOT / COMPATIBILITY_V02).read_text(encoding="utf-8")
        self.assertIn("l28-m2m-release-compatibility/v0.2", text)
        self.assertIn("l28-m2m/v0.1", text)
        self.assertIn("l28-m2m-replay-registry-backup/v0.1", text)
        self.assertIn(HISTORICAL_TAG, text)
        self.assertIn("unencrypted", text.lower())
        self.assertIn("quiescent", text.lower())
        self.assertIn("os.link", text)

    def test_readme_links_v02_honestly(self) -> None:
        text = (ROOT / README_PATH).read_text(encoding="utf-8")
        self.assertIn("release_manifest_v0.2.json", text)
        self.assertIn("release_notes_v0.2.md", text)
        self.assertIn("release_compatibility_v0.2.md", text)
        self.assertIn(HISTORICAL_TAG, text)
        self.assertIn("release candidate", text.lower())
        self.assertIn("l28-m2m/v0.1", text)
        self.assertIn("l28-m2m-replay-registry-backup/v0.1", text)
        for claim in TAG_EXISTS_CLAIMS:
            self.assertNotIn(claim, text.lower())

    def test_docs_do_not_claim_v02_tag_or_release_exists(self) -> None:
        for rel in (RELEASE_NOTES_V02, COMPATIBILITY_V02, README_PATH):
            text = (ROOT / rel).read_text(encoding="utf-8").lower()
            self.assertNotIn("github release for l28 m2m v0.2.0", text)
            self.assertNotIn("tag l28-m2m-v0.2.0 is published", text)

    def test_no_private_material_in_release_surface(self) -> None:
        paths = [
            MANIFEST_PATH,
            ROOT / RELEASE_NOTES_V02,
            ROOT / COMPATIBILITY_V02,
            ROOT / README_PATH,
        ]
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for pattern in PRIVATE_KEY_PATTERNS:
                self.assertIsNone(pattern.search(text), f"private material pattern in {path}")


class ReleaseV02DeterminismTests(unittest.TestCase):
    def test_manifest_json_sorted_keys(self) -> None:
        raw = MANIFEST_PATH.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        self.assertEqual(
            raw,
            json.dumps(parsed, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        )

    def test_release_docs_do_not_embed_v02_manifest_id(self) -> None:
        manifest_id = _load_manifest()["manifest_id"]
        for rel in (RELEASE_NOTES_V02, COMPATIBILITY_V02):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn(manifest_id, text)


if __name__ == "__main__":
    unittest.main()
