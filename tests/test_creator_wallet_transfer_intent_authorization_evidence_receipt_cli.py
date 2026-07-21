from __future__ import annotations

import ast
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from coin import creator_wallet_transfer_intent_authorization_evidence_receipt_cli as cli
from coin.creator_wallet_transfer_intent_authorization_evidence_receipt import (
    MAX_RECEIPT_BYTES,
    CreatorWalletTransferIntentAuthorizationEvidenceReceiptResult,
)

HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64


def _result(*, ok: bool = True, code: str = "ok"):
    return CreatorWalletTransferIntentAuthorizationEvidenceReceiptResult(
        ok=ok,
        code=code,
        checks=("schema_exact",) if ok else (),
        receipt_id=HEX_A if ok else "",
        evidence_sha256=HEX_B if ok else "",
        authorization_report_id=HEX_C if ok else "",
        authorization_sha256=HEX_A if ok else "",
        authorization_id=HEX_B if ok else "",
    )


def _invoke(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = cli.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


class CreatorWalletTransferIntentAuthorizationEvidenceReceiptCliTests(unittest.TestCase):
    def test_valid_result_is_reported(self) -> None:
        with mock.patch.object(
            cli,
            "verify_creator_wallet_transfer_intent_authorization_evidence_receipt_file",
            return_value=_result(),
        ):
            code, output, _ = _invoke(["receipt.json"])

        self.assertEqual(code, cli.EXIT_OK)
        report = json.loads(output)
        self.assertTrue(report["ok"])
        self.assertEqual(report["receipt_id"], HEX_A)
        self.assertEqual(report["evidence_sha256"], HEX_B)
        self.assertEqual(report["authorization_report_id"], HEX_C)
        self.assertFalse(report["execution_authorized"])
        self.assertFalse(report["signature_created"])
        self.assertFalse(report["transfer_created"])
        self.assertFalse(report["runtime_activation"])
        self.assertFalse(report["clock_access"])
        self.assertFalse(report["replay_state_access"])
        self.assertFalse(report["network_access"])

    def test_pretty_report_is_logically_equal(self) -> None:
        with mock.patch.object(
            cli,
            "verify_creator_wallet_transfer_intent_authorization_evidence_receipt_file",
            return_value=_result(),
        ):
            compact = _invoke(["receipt.json"])
            pretty = _invoke(["receipt.json", "--pretty"])

        self.assertEqual(compact[0], cli.EXIT_OK)
        self.assertEqual(pretty[0], cli.EXIT_OK)
        self.assertEqual(json.loads(compact[1]), json.loads(pretty[1]))

    def test_verification_failure_uses_verification_exit(self) -> None:
        with mock.patch.object(
            cli,
            "verify_creator_wallet_transfer_intent_authorization_evidence_receipt_file",
            return_value=_result(ok=False, code="evidence_invalid"),
        ):
            code, output, _ = _invoke(["receipt.json"])

        self.assertEqual(code, cli.EXIT_VERIFICATION)
        self.assertFalse(json.loads(output)["ok"])

    def test_regular_file_calls_core_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "receipt.json")
            path.write_bytes(b"{}")
            expected = _result()

            with mock.patch.object(
                cli,
                "verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json",
                return_value=expected,
            ) as verifier:
                actual = cli.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_file(
                    str(path)
                )

        self.assertEqual(actual, expected)
        verifier.assert_called_once_with(b"{}")

    def test_missing_directory_and_symlink_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            regular = root / "regular.json"
            regular.write_bytes(b"{}")
            symlink = root / "link.json"
            symlink.symlink_to(regular)

            for path in (root / "missing.json", root, symlink):
                with self.subTest(path=path):
                    with self.assertRaises(cli._CliError) as raised:
                        cli.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_file(
                            str(path)
                        )
                    self.assertEqual(raised.exception.code, "invalid_path")
                    self.assertEqual(raised.exception.exit_code, cli.EXIT_IO)

    def test_oversized_file_is_rejected_before_core(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "large.json")
            path.write_bytes(b"x" * (MAX_RECEIPT_BYTES + 1))

            with mock.patch.object(
                cli,
                "verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json",
            ) as verifier:
                with self.assertRaises(cli._CliError) as raised:
                    cli.verify_creator_wallet_transfer_intent_authorization_evidence_receipt_file(
                        str(path)
                    )

        self.assertEqual(raised.exception.code, "file_too_large")
        self.assertEqual(raised.exception.exit_code, cli.EXIT_IO)
        verifier.assert_not_called()

    def test_report_id_is_deterministic_and_body_bound(self) -> None:
        first = cli._build_report(_result())
        second = cli._build_report(_result())
        changed = cli._build_report(_result(ok=False, code="receipt_id_invalid"))

        self.assertEqual(first["report_id"], second["report_id"])
        self.assertNotEqual(first["report_id"], changed["report_id"])
        body = {key: value for key, value in first.items() if key != "report_id"}
        expected_id = hashlib.sha256(
            cli.REPORT_DOMAIN + cli._canonical_bytes(body)
        ).hexdigest()
        self.assertEqual(first["report_id"], expected_id)
        self.assertFalse(first["execution_authorized"])

    def test_unexpected_exception_is_sanitized(self) -> None:
        with mock.patch.object(
            cli,
            "verify_creator_wallet_transfer_intent_authorization_evidence_receipt_file",
            side_effect=RuntimeError("secret detail"),
        ):
            code, output, error = _invoke(["receipt.json"])

        self.assertEqual(code, cli.EXIT_INTERNAL)
        self.assertNotIn("secret detail", output + error)
        self.assertEqual(json.loads(output)["code"], "internal_error")

    def test_production_cli_has_no_wallet_network_or_private_key_imports(self) -> None:
        path = Path(cli.__file__)
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))

        modules = {
            (node.module or "").split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        modules |= {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }

        self.assertFalse(
            modules & {"socket", "requests", "urllib", "subprocess", "wallet", "ledger"}
        )
        self.assertNotIn("Ed25519PrivateKey", text)
        self.assertNotIn("load_wallet(", text)
        self.assertNotIn("sign_entry(", text)
        self.assertIn('if __name__ == "__main__":', text)


if __name__ == "__main__":
    unittest.main()
