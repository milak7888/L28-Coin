import ast
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from coin import creator_wallet_transfer_intent as intent
from coin import creator_wallet_transfer_intent_cli as cli


BUNDLE_SHA256 = "2" * 64
AGGREGATE_COMMITMENT = "3" * 64


def _json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )


def _valid_intent():
    value = {
        "intent_version": intent.INTENT_VERSION,
        "domain": intent.INTENT_DOMAIN,
        "creator_address": intent.FIXED_CREATOR_ADDRESS,
        "recipient_address": "L28" + "4" * 40,
        "amount": 28,
        "nonce": "1" * 64,
        "expires_at_unix": 2_000_000_000,
        "control_bundle_sha256": BUNDLE_SHA256,
        "control_bundle_aggregate_commitment": AGGREGATE_COMMITMENT,
        "intent_id": "0" * 64,
    }
    value["intent_id"] = intent._intent_id(value)
    return value


def _arguments(path, *, pretty=False):
    args = [
        str(path),
        "--control-bundle-sha256",
        BUNDLE_SHA256,
        "--control-bundle-aggregate-commitment",
        AGGREGATE_COMMITMENT,
    ]
    if pretty:
        args.append("--pretty")
    return args


def _run(args):
    output = io.StringIO()
    with redirect_stdout(output):
        code = cli.main(args)
    return code, json.loads(output.getvalue())


class CreatorWalletTransferIntentCliTests(unittest.TestCase):
    def test_valid_intent_file_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intent.json"
            path.write_text(_json(_valid_intent()), encoding="utf-8")
            code, report = _run(_arguments(path))
        self.assertEqual(code, cli.EXIT_OK)
        self.assertTrue(report["ok"])
        self.assertEqual(report["code"], "ok")
        self.assertEqual(tuple(report), cli.REPORT_FIELDS)
        self.assertEqual(report["intent_id"], _valid_intent()["intent_id"])
        self.assertEqual(report["control_bundle_sha256"], BUNDLE_SHA256)
        self.assertFalse(report["runtime_activation"])
        self.assertFalse(report["wallet_loaded"])
        self.assertFalse(report["private_key_read"])
        self.assertFalse(report["signature_created"])
        self.assertFalse(report["transfer_created"])
        self.assertFalse(report["ledger_mutated"])
        self.assertFalse(report["network_access"])
        self.assertFalse(report["execution_authorized"])

    def test_invalid_intent_is_verification_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intent.json"
            value = _valid_intent()
            value["amount"] = 0
            path.write_text(_json(value), encoding="utf-8")
            code, report = _run(_arguments(path))
        self.assertEqual(code, cli.EXIT_VERIFICATION)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "amount_invalid")

    def test_invalid_expected_commitment_precedes_path_access(self):
        output = io.StringIO()
        with mock.patch.object(cli, "_read_explicit_file", side_effect=AssertionError):
            with redirect_stdout(output):
                code = cli.main(
                    [
                        "/does/not/exist",
                        "--control-bundle-sha256",
                        "bad",
                        "--control-bundle-aggregate-commitment",
                        AGGREGATE_COMMITMENT,
                    ]
                )
        report = json.loads(output.getvalue())
        self.assertEqual(code, cli.EXIT_VERIFICATION)
        self.assertEqual(report["code"], "invalid_expected_commitment")

    def test_missing_directory_and_symlink_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / "intent.json"
            existing.write_text(_json(_valid_intent()), encoding="utf-8")
            link = root / "intent-link.json"
            link.symlink_to(existing)
            for path in (root / "missing.json", root, link):
                with self.subTest(path=path):
                    code, report = _run(_arguments(path))
                    self.assertEqual(code, cli.EXIT_IO)
                    self.assertEqual(report["code"], "invalid_path")

    def test_oversized_file_is_rejected_before_json_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.json"
            path.write_bytes(b"x" * (intent.MAX_INTENT_BYTES + 1))
            output = io.StringIO()
            with mock.patch.object(intent.json, "loads", side_effect=AssertionError):
                with redirect_stdout(output):
                    code = cli.main(_arguments(path))
            report = json.loads(output.getvalue())
        self.assertEqual(code, cli.EXIT_VERIFICATION)
        self.assertEqual(report["code"], "intent_too_large")

    def test_io_error_is_sanitized(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intent.json"
            path.write_text(_json(_valid_intent()), encoding="utf-8")
            with mock.patch.object(
                Path,
                "open",
                side_effect=OSError("private filesystem detail"),
            ):
                code, report = _run(_arguments(path))
        self.assertEqual(code, cli.EXIT_IO)
        self.assertEqual(report["code"], "io_error")
        self.assertNotIn("private filesystem detail", _json(report))

    def test_report_id_is_deterministic_and_body_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intent.json"
            path.write_text(_json(_valid_intent()), encoding="utf-8")
            _, first = _run(_arguments(path))
            _, second = _run(_arguments(path))
        self.assertEqual(first, second)
        body = dict(first)
        report_id = body.pop("report_id")
        expected = hashlib.sha256(
            cli.REPORT_DOMAIN + cli._canonical_bytes(body)
        ).hexdigest()
        self.assertEqual(report_id, expected)
        body["amount"] += 1
        self.assertNotEqual(report_id, cli._report_id(body))

    def test_pretty_output_is_logically_equal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intent.json"
            path.write_text(_json(_valid_intent()), encoding="utf-8")
            compact_code, compact = _run(_arguments(path))
            pretty_code, pretty = _run(_arguments(path, pretty=True))
        self.assertEqual(compact_code, pretty_code)
        self.assertEqual(compact, pretty)

    def test_file_wrapper_matches_core_result(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intent.json"
            payload = _json(_valid_intent())
            path.write_text(payload, encoding="utf-8")
            file_result = cli.verify_creator_wallet_transfer_intent_file(
                str(path),
                expected_control_bundle_sha256=BUNDLE_SHA256,
                expected_control_bundle_aggregate_commitment=(
                    AGGREGATE_COMMITMENT
                ),
            )
            core_result = intent.verify_creator_wallet_transfer_intent_json(
                payload,
                expected_control_bundle_sha256=BUNDLE_SHA256,
                expected_control_bundle_aggregate_commitment=(
                    AGGREGATE_COMMITMENT
                ),
            )
        self.assertEqual(file_result, core_result)

    def test_unexpected_cli_exception_is_sanitized(self):
        output = io.StringIO()
        with mock.patch.object(
            cli,
            "verify_creator_wallet_transfer_intent_file",
            side_effect=RuntimeError("private detail"),
        ):
            with redirect_stdout(output):
                code = cli.main(_arguments("ignored.json"))
        report = json.loads(output.getvalue())
        self.assertEqual(code, cli.EXIT_INTERNAL)
        self.assertEqual(report["code"], "internal_error")
        self.assertNotIn("private detail", _json(report))

    def test_usage_failures_are_argparse_exit_two(self):
        for args in ([], ["intent.json"]):
            with self.subTest(args=args):
                with redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as caught:
                        cli.main(args)
                self.assertEqual(caught.exception.code, cli.EXIT_USAGE)

    def test_production_cli_has_no_network_wallet_or_signing_imports(self):
        source = Path(cli.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertFalse(
            imports & {
                "socket",
                "subprocess",
                "urllib",
                "requests",
                "httpx",
            }
        )
        self.assertNotIn("Ed25519PrivateKey", source)
        self.assertNotIn("wallet_dir", source)
        self.assertIn('if __name__ == "__main__":', source)


if __name__ == "__main__":
    unittest.main()
