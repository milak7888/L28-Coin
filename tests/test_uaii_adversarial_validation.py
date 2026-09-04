# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from coin.uaii_json import (
    MAX_RECEIVED_REQUEST_BYTES,
    UaiiJsonError,
    canon_uaii,
    decode_uaii_json,
    enforce_uaii_property_names,
    strict_utf8_bytes,
)


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "uaii_community_conformance.sh"


def assert_code(call, code):
    with pytest.raises(UaiiJsonError) as exc:
        call()
    assert exc.value.code == code


def test_decode_fail_closed_matrix():
    cases = (
        (123, "input_type_invalid"),
        (b"\xff", "encoding_invalid"),
        ("\ufeff{}", "encoding_invalid"),
        (b"[]", "invalid_top_level"),
        (b'{"a":1.0}', "json_invalid"),
        (b'{"a":NaN}', "json_invalid"),
        (b'{"a":1,"a":2}', "duplicate_key"),
    )
    for raw, code in cases:
        assert_code(lambda raw=raw: decode_uaii_json(raw), code)


def test_received_size_boundary():
    prefix = b'{"a":"'
    suffix = b'"}'
    payload = prefix + b"x" * (
        MAX_RECEIVED_REQUEST_BYTES - len(prefix) - len(suffix)
    ) + suffix
    assert len(payload) == MAX_RECEIVED_REQUEST_BYTES
    assert decode_uaii_json(payload)["a"]
    oversize = b"{" + b"x" * MAX_RECEIVED_REQUEST_BYTES
    assert_code(lambda: decode_uaii_json(oversize), "input_too_large")


def test_duplicate_key_precedence():
    assert_code(
        lambda: decode_uaii_json(b'{"Bad":1,"Bad":2}'),
        "duplicate_key",
    )


def test_property_name_grammar_fails_closed_recursively():
    cases = (
        {"Bad": 1},
        {"ok": {"also-bad": 1}},
        {"ok": [{"UPPER": 1}]},
    )
    for obj in cases:
        assert_code(
            lambda obj=obj: enforce_uaii_property_names(obj),
            "schema_invalid",
        )


def test_canonicalization_and_unicode_are_deterministic():
    assert canon_uaii({"z": 1, "a": "\u00e9"}) == b'{"z":1,"a":"\xc3\xa9"}'
    assert_code(lambda: canon_uaii({"a": 1.0}), "json_invalid")
    assert_code(lambda: strict_utf8_bytes("\ud800"), "encoding_invalid")


def test_full_runner_includes_adversarial_matrix():
    text = RUNNER.read_text(encoding="utf-8")
    assert "tests/test_uaii_adversarial_validation.py" in text
    assert "ADVERSARIAL_VALIDATION=PASS" in text
