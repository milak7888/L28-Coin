# SPDX-License-Identifier: Apache-2.0
"""Offline Public Demo CLI v0.2 — machine-readable JSON envelope tests."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from coin.isolated_agent_purchase_demo import (
    CLI_ENVELOPE_COMPLETED_FIELDS,
    CLI_ENVELOPE_ERROR_FIELDS,
    CLI_ERROR_FIELDS,
    CLI_SCHEMA,
    CLI_SCHEMA_VERSION,
    DEFAULT_DEMO_INPUT,
    DemoError,
    main,
    run_isolated_agent_purchase_demo,
)
from coin.uaii_json import canon_uaii


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = "/Users/pjaydondup/.pyenv/versions/l28-env/bin/python"


def _run_main(argv: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def _module_cmd(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return subprocess.run(
        [PYTHON, "-m", "coin.isolated_agent_purchase_demo", *args],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


class TestOfflinePublicDemoCLIv02(unittest.TestCase):
    def test_default_module_invocation_succeeds(self) -> None:
        proc = _module_cmd([])
        self.assertEqual(proc.returncode, 0)
        summary = json.loads(proc.stdout)
        self.assertTrue(summary["demo_completed"])
        self.assertTrue(summary["simulation_only"])
        self.assertEqual(proc.stderr, "")

    def test_json_emits_exactly_one_document(self) -> None:
        code, out, err = _run_main(["--json", "--verify"])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertTrue(out.endswith("\n"))
        self.assertEqual(out.count("\n"), 1)
        envelope = json.loads(out)
        self.assertEqual(tuple(envelope.keys()), CLI_ENVELOPE_COMPLETED_FIELDS)
        self.assertEqual(envelope["schema"], CLI_SCHEMA)
        self.assertEqual(envelope["schema_version"], CLI_SCHEMA_VERSION)
        self.assertEqual(envelope["status"], "completed")
        result = envelope["result"]
        self.assertIsInstance(result, dict)
        self.assertIs(result["simulation_only"], True)
        self.assertIs(result["real_payment_executed"], False)
        self.assertIs(result["settlement_finalized"], False)
        self.assertIs(result["transaction_submitted"], False)
        self.assertIs(result["ledger_mutated"], False)
        self.assertIs(result["persistent_state_created"], False)
        self.assertIs(result["public_network_used"], False)
        self.assertIs(result["service_output_verified"], True)
        self.assertIs(result["receipt_signature_verified"], True)

    def test_json_pretty_remains_valid(self) -> None:
        code, out, err = _run_main(["--json", "--pretty", "--verify"])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        envelope = json.loads(out)
        self.assertEqual(envelope["status"], "completed")
        self.assertIn("\n  ", out)

    def test_custom_input_bound_and_verified(self) -> None:
        code, out, err = _run_main(
            ["--json", "--verify", "--input", "custom-cli-input-v0.2"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        envelope = json.loads(out)
        result = envelope["result"]
        self.assertEqual(result["request"]["input"], {"text": "custom-cli-input-v0.2"})
        expected = hashlib.sha256(
            canon_uaii({"text": "custom-cli-input-v0.2"})
        ).hexdigest()
        self.assertEqual(result["output_digest"], expected)

    def test_verify_success_requires_both_checks(self) -> None:
        code, out, err = _run_main(["--json", "--verify"])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        result = json.loads(out)["result"]
        self.assertIs(result["service_output_verified"], True)
        self.assertIs(result["receipt_signature_verified"], True)

    def test_forced_verification_failure_safe_json_error(self) -> None:
        with mock.patch(
            "coin.isolated_agent_purchase_demo.verify_isolated_agent_purchase_demo_result",
            side_effect=DemoError("verification_failed"),
        ):
            code, out, err = _run_main(["--json", "--verify", "--input", DEFAULT_DEMO_INPUT])
        self.assertEqual(code, 1)
        self.assertEqual(err, "")
        envelope = json.loads(out)
        self.assertEqual(tuple(envelope.keys()), CLI_ENVELOPE_ERROR_FIELDS)
        self.assertEqual(envelope["schema"], CLI_SCHEMA)
        self.assertEqual(envelope["schema_version"], CLI_SCHEMA_VERSION)
        self.assertEqual(envelope["status"], "error")
        self.assertEqual(tuple(envelope["error"].keys()), CLI_ERROR_FIELDS)
        self.assertEqual(envelope["error"]["code"], "verification_failed")
        self.assertIsInstance(envelope["error"]["message"], str)
        self.assertNotRegex(
            out + err,
            r"private_key|secret_key|seed_phrase|Traceback|BEGIN PRIVATE",
        )

    def test_unknown_arguments_nonzero_no_traceback(self) -> None:
        code, out, err = _run_main(["--json", "--not-a-real-flag"])
        self.assertEqual(code, 2)
        envelope = json.loads(out)
        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["error"]["code"], "invalid_argument")
        self.assertNotIn("Traceback", out + err)
        self.assertNotRegex(out + err, r"private_key|secret_key|seed_phrase")

    def test_no_private_material_in_json_output(self) -> None:
        code, out, err = _run_main(["--json", "--verify"])
        self.assertEqual(code, 0)
        blob = out + err
        self.assertNotRegex(
            blob,
            r"private_key|secret_key|seed_phrase|mnemonic|BEGIN PRIVATE|private_bytes",
        )
        envelope = json.loads(out)
        serialized = json.dumps(envelope)
        self.assertNotIn("private_key", serialized)

    def test_repeated_invocations_semantically_equivalent(self) -> None:
        code_a, out_a, err_a = _run_main(["--json", "--input", "same-cli-input"])
        code_b, out_b, err_b = _run_main(["--json", "--input", "same-cli-input"])
        self.assertEqual(code_a, 0)
        self.assertEqual(code_b, 0)
        self.assertEqual(err_a, "")
        self.assertEqual(err_b, "")
        a = json.loads(out_a)["result"]
        b = json.loads(out_b)["result"]
        for key in (
            "demo_profile",
            "demo_version",
            "service_id",
            "buyer_public_identity",
            "seller_public_identity",
            "simulation_only",
            "real_payment_executed",
            "ledger_mutated",
            "public_network_used",
        ):
            self.assertEqual(a[key], b[key])
        self.assertEqual(a["request"]["input"], b["request"]["input"])
        # Fresh disposable keys each run ⇒ digests/signatures may differ.
        self.assertEqual(a["request"]["input"]["text"], "same-cli-input")

    def test_callable_api_unchanged(self) -> None:
        result = run_isolated_agent_purchase_demo(request_input="callable-still-works")
        self.assertTrue(result["demo_completed"])
        self.assertTrue(result["simulation_only"])

    def test_subprocess_json_verify_pure_stdout(self) -> None:
        proc = _module_cmd(["--json", "--verify"])
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stderr, "")
        envelope = json.loads(proc.stdout)
        self.assertEqual(envelope["status"], "completed")
        self.assertEqual(envelope["schema_version"], CLI_SCHEMA_VERSION)

    def test_no_side_effect_imports(self) -> None:
        with mock.patch("coin.tx_validation.validate_transaction") as vt, mock.patch(
            "coin.uaii_reference_core.process_uaii_request"
        ) as proc:
            code, _out, _err = _run_main(["--json", "--verify"])
            self.assertEqual(code, 0)
            vt.assert_not_called()
            proc.assert_not_called()
        src = Path(main.__code__.co_filename).read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\bdatetime\.(now|utcnow)\b", src))
        self.assertNotIn("private_bytes", src)


if __name__ == "__main__":
    unittest.main()
