import ast
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from coin import creator_wallet_transfer_intent_authorization_cli as cli
from coin.creator_wallet_transfer_intent_authorization import (
    MAX_AUTHORIZATION_BYTES,
    CreatorWalletTransferIntentAuthorizationResult,
)


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64
CREATOR = "L28" + "d" * 40
RECIPIENT = "L28" + "e" * 40


def _result(*, ok=True, code="ok"):
    return CreatorWalletTransferIntentAuthorizationResult(
        ok=ok,
        code=code,
        checks=("schema_exact",) if ok else (),
        authorization_sha256=HEX_A if ok else None,
        authorization_id=HEX_B if ok else None,
        intent_sha256=HEX_C if ok else None,
        intent_id=HEX_A if ok else None,
        creator_address=CREATOR if ok else None,
        recipient_address=RECIPIENT if ok else None,
        amount=28 if ok else None,
        expires_at_unix=2000000000 if ok else None,
        control_bundle_sha256=HEX_B if ok else None,
        control_bundle_aggregate_commitment=HEX_C if ok else None,
    )


def _invoke(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = cli.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


class CreatorWalletTransferIntentAuthorizationCliTests(unittest.TestCase):
    def test_valid_result_is_reported(self):
        with mock.patch.object(
            cli,
            "verify_creator_wallet_transfer_intent_authorization_file",
            return_value=_result(),
        ):
            code, output, _ = _invoke([
                "authorization.json",
                "--control-bundle-sha256", HEX_B,
                "--control-bundle-aggregate-commitment", HEX_C,
            ])

        self.assertEqual(code, cli.EXIT_OK)
        report = json.loads(output)
        self.assertTrue(report["ok"])
        self.assertEqual(report["authorization_id"], HEX_B)
        self.assertEqual(report["intent_sha256"], HEX_C)
        self.assertFalse(report["execution_authorized"])
        self.assertFalse(report["signature_created"])
        self.assertFalse(report["transfer_created"])
        self.assertFalse(report["runtime_activation"])

    def test_pretty_report_is_logically_equal(self):
        with mock.patch.object(
            cli,
            "verify_creator_wallet_transfer_intent_authorization_file",
            return_value=_result(),
        ):
            args = [
                "authorization.json",
                "--control-bundle-sha256", HEX_B,
                "--control-bundle-aggregate-commitment", HEX_C,
            ]
            compact = _invoke(args)
            pretty = _invoke([*args, "--pretty"])

        self.assertEqual(compact[0], cli.EXIT_OK)
        self.assertEqual(pretty[0], cli.EXIT_OK)
        self.assertEqual(json.loads(compact[1]), json.loads(pretty[1]))

    def test_verification_failure_uses_verification_exit(self):
        with mock.patch.object(
            cli,
            "verify_creator_wallet_transfer_intent_authorization_file",
            return_value=_result(ok=False, code="signature_invalid"),
        ):
            code, output, _ = _invoke([
                "authorization.json",
                "--control-bundle-sha256", HEX_B,
                "--control-bundle-aggregate-commitment", HEX_C,
            ])

        self.assertEqual(code, cli.EXIT_VERIFICATION)
        self.assertFalse(json.loads(output)["ok"])

    def test_regular_file_calls_core_verifier(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "authorization.json")
            path.write_bytes(b"{}")
            expected = _result()

            with mock.patch.object(
                cli,
                "verify_creator_wallet_transfer_intent_authorization_json",
                return_value=expected,
            ) as verifier:
                actual = cli.verify_creator_wallet_transfer_intent_authorization_file(
                    str(path),
                    expected_control_bundle_sha256=HEX_B,
                    expected_control_bundle_aggregate_commitment=HEX_C,
                )

        self.assertEqual(actual, expected)
        verifier.assert_called_once_with(
            b"{}",
            expected_control_bundle_sha256=HEX_B,
            expected_control_bundle_aggregate_commitment=HEX_C,
        )

    def test_missing_directory_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            regular = root / "regular.json"
            regular.write_bytes(b"{}")
            symlink = root / "link.json"
            symlink.symlink_to(regular)

            for path in (root / "missing.json", root, symlink):
                with self.subTest(path=path):
                    with self.assertRaises(cli._CliError) as raised:
                        cli.verify_creator_wallet_transfer_intent_authorization_file(
                            str(path),
                            expected_control_bundle_sha256=HEX_B,
                            expected_control_bundle_aggregate_commitment=HEX_C,
                        )
                    self.assertEqual(raised.exception.code, "invalid_path")
                    self.assertEqual(raised.exception.exit_code, cli.EXIT_IO)

    def test_oversized_file_is_rejected_before_core(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "large.json")
            path.write_bytes(b"x" * (MAX_AUTHORIZATION_BYTES + 1))

            with mock.patch.object(
                cli,
                "verify_creator_wallet_transfer_intent_authorization_json",
            ) as verifier:
                with self.assertRaises(cli._CliError) as raised:
                    cli.verify_creator_wallet_transfer_intent_authorization_file(
                        str(path),
                        expected_control_bundle_sha256=HEX_B,
                        expected_control_bundle_aggregate_commitment=HEX_C,
                    )

        self.assertEqual(raised.exception.code, "file_too_large")
        self.assertEqual(raised.exception.exit_code, cli.EXIT_IO)
        verifier.assert_not_called()

    def test_report_id_is_deterministic_and_body_bound(self):
        first = cli._build_report(_result())
        second = cli._build_report(_result())
        changed = cli._build_report(
            CreatorWalletTransferIntentAuthorizationResult(
                **{**_result().__dict__, "amount": 29}
            )
        )

        self.assertEqual(first["report_id"], second["report_id"])
        self.assertNotEqual(first["report_id"], changed["report_id"])

    def test_unexpected_exception_is_sanitized(self):
        with mock.patch.object(
            cli,
            "verify_creator_wallet_transfer_intent_authorization_file",
            side_effect=RuntimeError("secret detail"),
        ):
            code, output, error = _invoke([
                "authorization.json",
                "--control-bundle-sha256", HEX_B,
                "--control-bundle-aggregate-commitment", HEX_C,
            ])

        self.assertEqual(code, cli.EXIT_INTERNAL)
        self.assertNotIn("secret detail", output + error)

    def test_production_cli_has_no_wallet_network_or_private_key_imports(self):
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


if __name__ == "__main__":
    unittest.main()
