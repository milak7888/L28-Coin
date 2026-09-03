# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import re


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "sdk"
    / "typescript"
    / "uaii.mts"
)


def _text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_typescript_sdk_profile_and_operations():
    text = _text()

    assert '"l28-universal-ai-access-interface/v0.1"' in text

    operations = (
        "discover_capabilities",
        "get_protocol_status",
        "get_balance",
        "create_quote",
        "create_unsigned_payment_request",
        "validate_payment",
        "get_payment_receipt",
        "verify_signed_receipt",
    )

    positions = [
        text.index(f'"{operation}"')
        for operation in operations
    ]

    assert positions == sorted(positions)


def test_typescript_sdk_authority_flags_closed():
    text = _text()

    declarations = (
        "package_published = false",
        "runtime_activated = false",
        "network_activated = false",
        "signing_authorized = false",
        "spend_authorized = false",
        "settlement_authorized = false",
        "transaction_submission_authorized = false",
    )

    for declaration in declarations:
        assert declaration in text


def test_typescript_sdk_named_operations_exact():
    text = _text()

    methods = set(
        re.findall(
            r"^\s{2}([a-z_]+)\("
            r"(?:\n\s+)?request: UaiiEnvelope",
            text,
            flags=re.MULTILINE,
        )
    )

    expected = {
        "discover_capabilities",
        "get_protocol_status",
        "get_balance",
        "create_quote",
        "create_unsigned_payment_request",
        "validate_payment",
        "get_payment_receipt",
        "verify_signed_receipt",
    }

    assert expected.issubset(methods)


def test_typescript_sdk_has_no_network_imports():
    text = _text()

    assert re.search(
        r"^\s*import\s",
        text,
        flags=re.MULTILINE,
    ) is None

    forbidden = (
        "fetch(",
        "WebSocket",
        "XMLHttpRequest",
        "node:http",
        "node:https",
        "node:net",
        "node:tls",
    )

    for token in forbidden:
        assert token not in text
