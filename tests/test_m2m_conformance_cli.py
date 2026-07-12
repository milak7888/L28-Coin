# SPDX-License-Identifier: Apache-2.0
"""
Offline subprocess tests for Foundation 7 M2M conformance CLI.

TEST-ONLY. Uses TemporaryDirectory fixtures only. Does not sign, write reports
to disk as products, access private files, or perform network operations.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from coin.m2m_conformance_cli import (
    CLI_VERSION,
    MAX_INPUT_BYTES,
    compute_report_id,
    _exit_for_transcript,
)
from coin.m2m_verifier import canonical_bytes

ROOT = Path(__file__).resolve().parents[1]
REPORT_VECTORS = ROOT / "docs" / "m2m" / "test_vectors_report_v0.1.json"
TRANSCRIPT_VECTORS = ROOT / "docs" / "m2m" / "test_vectors_transcript_v0.1.json"
CLI_MODULE = "coin.m2m_conformance_cli"
CLI_PATH = ROOT / "coin" / "m2m_conformance_cli.py"

FORBIDDEN_IMPORT_NAMES = frozenset({"Ed25519PrivateKey", "from_private_bytes"})
FORBIDDEN_VECTOR_KEYS = frozenset(
    {
        "private_key",
        "seed",
        "seed_phrase",
        "mnemonic",
        "wallet_credential",
        "wallet_secret",
        "signing_secret",
        "secret_key",
    }
)
LEAK_MARKERS = (
    "hostname",
    "username",
    "getpass",
    "platform",
    "pid",
    "/Users/",
    "C:\\\\",
)


def _collect_keys(obj: Any, out: Set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(str(k))
            _collect_keys(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_keys(item, out)


def _run(
    args: Sequence[str],
    *,
    input_bytes: Optional[bytes] = None,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[int, str, str]:
    cmd = [sys.executable, "-m", CLI_MODULE, *args]
    completed = subprocess.run(
        cmd,
        input=input_bytes,
        capture_output=True,
        cwd=str(ROOT),
        env=env,
    )
    return (
        completed.returncode,
        completed.stdout.decode("utf-8"),
        completed.stderr.decode("utf-8"),
    )


def _parse_single_json_object(stdout: str) -> Dict[str, Any]:
    assert stdout.endswith("\n"), "stdout must end with one newline"
    # Exactly one JSON value: disallow trailing junk after the object.
    decoder = json.JSONDecoder()
    obj, end = decoder.raw_decode(stdout)
    rest = stdout[end:]
    assert rest == "\n", f"unexpected trailing stdout: {rest!r}"
    assert isinstance(obj, dict)
    return obj


class TestM2MConformanceCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report_doc = json.loads(REPORT_VECTORS.read_text(encoding="utf-8"))
        cls.transcript_doc = json.loads(TRANSCRIPT_VECTORS.read_text(encoding="utf-8"))
        cls.report_by_id = {v["vector_id"]: v for v in cls.report_doc["report_vectors"]}
        cls.transcript_by_id = {
            **{v["vector_id"]: v for v in cls.transcript_doc["valid_transcripts"]},
            **{v["vector_id"]: v for v in cls.transcript_doc["invalid_transcripts"]},
        }

    def _envelopes_bytes(self, transcript_vector_id: str) -> bytes:
        vec = self.transcript_by_id[transcript_vector_id]
        return json.dumps(vec["envelopes"], separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )

    def test_report_vector_metadata(self):
        self.assertTrue(self.report_doc["test_only"])
        self.assertFalse(self.report_doc["live"])
        self.assertFalse(self.report_doc["accepted_settlement"])
        self.assertFalse(self.report_doc["private_material_committed"])
        self.assertEqual(len(self.report_by_id), 9)

    def test_report_id_recompute_all_vectors(self):
        for vector_id, vec in self.report_by_id.items():
            with self.subTest(vector_id):
                body = {k: v for k, v in vec["expected_report"].items() if k != "report_id"}
                self.assertEqual(compute_report_id(body), vec["expected_report"]["report_id"])

    def test_file_input_success(self):
        raw = self._envelopes_bytes("valid_happy_path_completed")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            code, out, err = _run(["--input", str(path), "--require-terminal"])
        self.assertEqual(err, "")
        self.assertEqual(code, 0)
        report = _parse_single_json_object(out)
        expected = self.report_by_id["report_valid_completed_file"]["expected_report"]
        self.assertEqual(report, expected)

    def test_stdin_success(self):
        raw = self._envelopes_bytes("valid_happy_path_completed")
        code, out, err = _run(["--stdin", "--require-terminal"], input_bytes=raw)
        self.assertEqual(err, "")
        self.assertEqual(code, 0)
        report = _parse_single_json_object(out)
        expected = self.report_by_id["report_valid_completed_stdin"]["expected_report"]
        self.assertEqual(report, expected)

    def test_file_stdin_differ_only_documented_fields(self):
        file_report = self.report_by_id["report_valid_completed_file"]["expected_report"]
        stdin_report = self.report_by_id["report_valid_completed_stdin"]["expected_report"]
        self.assertEqual(file_report["input_sha256"], stdin_report["input_sha256"])
        self.assertEqual(file_report["input_size_bytes"], stdin_report["input_size_bytes"])
        self.assertEqual(file_report["ok"], stdin_report["ok"])
        self.assertEqual(file_report["code"], stdin_report["code"])
        self.assertEqual(file_report["state"], stdin_report["state"])
        self.assertNotEqual(file_report["input_mode"], stdin_report["input_mode"])
        self.assertNotEqual(file_report["report_id"], stdin_report["report_id"])

    def test_compact_and_pretty(self):
        raw = self._envelopes_bytes("valid_partial_quoted")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.json"
            path.write_bytes(raw)
            c_code, c_out, c_err = _run(["--input", str(path)])
            p_code, p_out, p_err = _run(["--input", str(path), "--pretty"])
        self.assertEqual(c_err, "")
        self.assertEqual(p_err, "")
        self.assertEqual(c_code, 0)
        self.assertEqual(p_code, 0)
        compact = _parse_single_json_object(c_out)
        pretty = _parse_single_json_object(p_out)
        self.assertEqual(compact, pretty)
        self.assertNotIn("\n  ", c_out)  # compact
        self.assertIn("\n  ", p_out)  # pretty indented

    def test_version(self):
        code, out, err = _run(["--version"])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(out, CLI_VERSION + "\n")

    def test_missing_input_mode(self):
        code, out, err = _run([])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("usage:", err)

    def test_mutually_exclusive_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.json"
            path.write_bytes(b"[]")
            code, out, err = _run(["--input", str(path), "--stdin"])
        self.assertEqual(code, 2)
        self.assertIn("usage:", err.lower() + out.lower())

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope.json"
            code, out, err = _run(["--input", str(missing)])
        self.assertEqual(code, 2)
        self.assertEqual(err, "")
        report = _parse_single_json_object(out)
        self.assertEqual(
            report,
            self.report_by_id["report_input_not_found_template"]["expected_report"],
        )
        self.assertNotIn(str(missing), out)
        self.assertNotIn(str(missing), err)

    def test_directory_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = _run(["--input", tmp])
        self.assertEqual(code, 2)
        report = _parse_single_json_object(out)
        self.assertEqual(report["code"], "input_not_regular_file")
        self.assertNotIn(tmp, out)

    def test_symlink_rejection(self):
        raw = self._envelopes_bytes("valid_partial_quoted")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "real.json"
            link = Path(tmp) / "link.json"
            target.write_bytes(raw)
            os.symlink(target.name, link)
            code, out, err = _run(["--input", str(link)])
        self.assertEqual(code, 2)
        self.assertEqual(err, "")
        report = _parse_single_json_object(out)
        self.assertEqual(
            report,
            self.report_by_id["report_input_symlink_rejected_template"]["expected_report"],
        )

    def test_fifo_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            fifo = Path(tmp) / "pipe.fifo"
            try:
                os.mkfifo(fifo)
            except (AttributeError, OSError):
                self.skipTest("mkfifo unavailable")
            code, out, err = _run(["--input", str(fifo)])
        self.assertEqual(code, 2)
        report = _parse_single_json_object(out)
        self.assertEqual(report["code"], "input_not_regular_file")

    def test_tty_rejection(self):
        # Safely simulate TTY stdin without hanging.
        script = (
            "import sys\n"
            "from coin import m2m_conformance_cli as c\n"
            "class T:\n"
            "    def isatty(self):\n"
            "        return True\n"
            "    @property\n"
            "    def buffer(self):\n"
            "        raise AssertionError('must not read')\n"
            "sys.stdin = T()\n"
            "raise SystemExit(c.main(['--stdin']))\n"
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            cwd=str(ROOT),
        )
        self.assertEqual(completed.returncode, 2)
        report = _parse_single_json_object(completed.stdout.decode("utf-8"))
        self.assertEqual(report["code"], "stdin_is_tty")

    def test_malformed_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.bin"
            path.write_bytes(b"\xff\xfe[")
            code, out, err = _run(["--input", str(path)])
        self.assertEqual(code, 1)
        self.assertEqual(err, "")
        report = _parse_single_json_object(out)
        self.assertEqual(report["code"], "invalid_json")

    def test_malformed_json_vector(self):
        vec = self.report_by_id["report_malformed_json"]
        raw = vec["inline_input_utf8"].encode("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.json"
            path.write_bytes(raw)
            code, out, err = _run(["--input", str(path)])
        self.assertEqual(code, 1)
        self.assertEqual(err, "")
        self.assertEqual(_parse_single_json_object(out), vec["expected_report"])

    def test_empty_transcript(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.json"
            path.write_bytes(b"[]")
            code, out, err = _run(["--input", str(path)])
        self.assertEqual(code, 1)
        report = _parse_single_json_object(out)
        self.assertEqual(report["code"], "empty_transcript")

    def test_oversized_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "big.bin"
            # Write MAX+1 without holding the whole payload in this process longer than needed.
            with open(path, "wb") as fh:
                fh.write(b"[" + (b"0" * MAX_INPUT_BYTES) + b"]")
            # Ensure file exceeds limit for the CLI read(+1) check.
            size = path.stat().st_size
            self.assertGreater(size, MAX_INPUT_BYTES)
            code, out, err = _run(["--input", str(path)])
        self.assertEqual(code, 2)
        self.assertEqual(err, "")
        report = _parse_single_json_object(out)
        self.assertEqual(
            report,
            self.report_by_id["report_input_too_large_template"]["expected_report"],
        )

    def test_partial_and_require_terminal_vectors(self):
        partial = self._envelopes_bytes("valid_partial_quoted")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "partial.json"
            path.write_bytes(partial)
            c1, o1, e1 = _run(["--input", str(path)])
            c2, o2, e2 = _run(["--input", str(path), "--require-terminal"])
        self.assertEqual(e1, "")
        self.assertEqual(e2, "")
        self.assertEqual(c1, 0)
        self.assertEqual(c2, 1)
        self.assertEqual(
            _parse_single_json_object(o1),
            self.report_by_id["report_valid_partial_quoted"]["expected_report"],
        )
        self.assertEqual(
            _parse_single_json_object(o2),
            self.report_by_id["report_incomplete_require_terminal"]["expected_report"],
        )

    def test_bad_signature_vector(self):
        raw = self._envelopes_bytes("invalid_bad_signature")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_bytes(raw)
            code, out, err = _run(["--input", str(path)])
        self.assertEqual(code, 1)
        self.assertEqual(err, "")
        self.assertEqual(
            _parse_single_json_object(out),
            self.report_by_id["report_bad_signature"]["expected_report"],
        )

    def test_backend_unavailable_exit_mapping(self):
        self.assertEqual(_exit_for_transcript("envelope_verification_failed", "verification_backend_unavailable"), 3)
        self.assertEqual(_exit_for_transcript("internal_error", None), 3)
        self.assertEqual(_exit_for_transcript("bad_signature", "bad_signature"), 1)

    def test_input_sha256_and_determinism(self):
        raw = self._envelopes_bytes("valid_happy_path_completed")
        expected_hash = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            c1, o1, e1 = _run(["--input", str(path), "--require-terminal"])
            c2, o2, e2 = _run(["--input", str(path), "--require-terminal"])
        self.assertEqual(e1, "")
        self.assertEqual(e2, "")
        self.assertEqual(c1, 0)
        self.assertEqual(c2, 0)
        self.assertEqual(o1, o2)
        report = _parse_single_json_object(o1)
        self.assertEqual(report["input_sha256"], expected_hash)
        body = {k: v for k, v in report.items() if k != "report_id"}
        self.assertEqual(report["report_id"], compute_report_id(body))
        # Canonical body bytes start with report domain when hashed externally.
        self.assertTrue(isinstance(canonical_bytes(body), (bytes, bytearray)))

    def test_no_path_hostname_time_process_leakage(self):
        raw = self._envelopes_bytes("valid_partial_quoted")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.json"
            path.write_bytes(raw)
            code, out, err = _run(["--input", str(path)])
        self.assertEqual(code, 0)
        blob = out + err
        self.assertNotIn(str(path), blob)
        self.assertNotIn(str(tmp), blob)
        report = _parse_single_json_object(out)
        for key in ("created_at", "timestamp", "hostname", "pid", "platform", "path"):
            self.assertNotIn(key, report)
        for marker in LEAK_MARKERS:
            self.assertNotIn(marker, blob)

    def test_ast_no_private_key_apis(self):
        tree = ast.parse(CLI_PATH.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in FORBIDDEN_IMPORT_NAMES:
                        self.fail(f"imports {alias.name}")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"generate", "sign"}:
                    self.fail(f"calls {node.func.attr}()")
        src = CLI_PATH.read_text(encoding="utf-8")
        self.assertNotRegex(src, r"import\s+.*Ed25519PrivateKey")

    def test_vector_keys_no_private_material(self):
        keys: Set[str] = set()
        _collect_keys(self.report_doc, keys)
        offenders = sorted(k for k in keys if k.lower() in FORBIDDEN_VECTOR_KEYS)
        self.assertEqual(offenders, [])

    def test_no_repo_data_or_report_files(self):
        data_dir = ROOT / "data"
        self.assertFalse(data_dir.exists() and any(data_dir.rglob("shard_*.jsonl")))
        # CLI must not create report artifacts in the repository root.
        stray = list(ROOT.glob("l28-m2m-conformance-report*"))
        self.assertEqual(stray, [])


if __name__ == "__main__":
    unittest.main()
