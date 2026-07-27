# SPDX-License-Identifier: Apache-2.0
"""Focused Foundation 62/63 UAII resource-limit tests."""

from __future__ import annotations

import json
import unittest

from coin.uaii_json import UaiiJsonError, canon_uaii, decode_uaii_json, serialize_uaii_response
from coin.uaii_resource_limits import (
    F60_L1_MAX_DEPTH,
    F60_L2_MAX_OBJECT_MEMBERS,
    F60_L3_MAX_ARRAY_ELEMENTS,
    F60_L4_MAX_STRING_UTF8_BYTES,
    F60_L5_MAX_CANON_REQUEST_BYTES,
    F60_L6_MAX_SERIALIZED_RESPONSE_BYTES,
    LimitFailure,
    build_l6_fallback_envelope,
    enforce_l5_canon_bytes,
    enforce_l6_response_bytes,
    measured_l6_fallback_envelope,
    walk_enforce_l1_l4,
)


def _nest_depth(depth: int) -> dict:
    """Build an object whose maximum container depth equals `depth`."""
    node: dict | str = "x"
    # depth 1 is a single object; wrap (depth-1) times
    for _ in range(depth):
        node = {"a": node}
    assert isinstance(node, dict)
    return node


def _object_with_members(n: int) -> dict:
    return {f"k{i:04d}": i for i in range(n)}


class TestUaiiResourceLimits(unittest.TestCase):
    def test_constants(self) -> None:
        self.assertEqual(F60_L1_MAX_DEPTH, 32)
        self.assertEqual(F60_L2_MAX_OBJECT_MEMBERS, 256)
        self.assertEqual(F60_L3_MAX_ARRAY_ELEMENTS, 256)
        self.assertEqual(F60_L4_MAX_STRING_UTF8_BYTES, 4096)
        self.assertEqual(F60_L5_MAX_CANON_REQUEST_BYTES, 16384)
        self.assertEqual(F60_L6_MAX_SERIALIZED_RESPONSE_BYTES, 16384)

    def test_depth_boundary(self) -> None:
        walk_enforce_l1_l4(_nest_depth(31))
        walk_enforce_l1_l4(_nest_depth(32))
        with self.assertRaises(LimitFailure) as ctx:
            walk_enforce_l1_l4(_nest_depth(33))
        self.assertEqual(ctx.exception.code, "resource_limit_exceeded")

    def test_empty_containers_contribute_depth(self) -> None:
        # root depth 1, empty nested object depth 2
        walk_enforce_l1_l4({"a": {}})
        # chain of empty objects to depth 32
        walk_enforce_l1_l4(_nest_depth(32))

    def test_members_boundary(self) -> None:
        walk_enforce_l1_l4(_object_with_members(255))
        walk_enforce_l1_l4(_object_with_members(256))
        with self.assertRaises(LimitFailure) as ctx:
            walk_enforce_l1_l4(_object_with_members(257))
        self.assertEqual(ctx.exception.code, "resource_limit_exceeded")

    def test_elements_boundary(self) -> None:
        walk_enforce_l1_l4({"a": list(range(255))})
        walk_enforce_l1_l4({"a": list(range(256))})
        with self.assertRaises(LimitFailure) as ctx:
            walk_enforce_l1_l4({"a": list(range(257))})
        self.assertEqual(ctx.exception.code, "resource_limit_exceeded")

    def test_string_bytes_boundary_ascii(self) -> None:
        walk_enforce_l1_l4({"s": "a" * 4095})
        walk_enforce_l1_l4({"s": "a" * 4096})
        with self.assertRaises(LimitFailure) as ctx:
            walk_enforce_l1_l4({"s": "a" * 4097})
        self.assertEqual(ctx.exception.code, "resource_limit_exceeded")

    def test_string_bytes_boundary_multibyte(self) -> None:
        # U+1F600 is 4 UTF-8 bytes
        unit = "😀"
        self.assertEqual(len(unit.encode("utf-8")), 4)
        n4096 = 4096 // 4
        walk_enforce_l1_l4({"s": unit * (n4096 - 1) + "a" * 3})  # 4095
        walk_enforce_l1_l4({"s": unit * n4096})  # 4096
        with self.assertRaises(LimitFailure):
            walk_enforce_l1_l4({"s": unit * n4096 + "a"})  # 4097

    def test_nonce_carveout(self) -> None:
        walk_enforce_l1_l4({"nonce": "x"})
        walk_enforce_l1_l4({"nonce": "n" * 256})
        with self.assertRaises(LimitFailure) as ctx0:
            walk_enforce_l1_l4({"nonce": ""})
        self.assertEqual(ctx0.exception.code, "nonce_invalid")
        with self.assertRaises(LimitFailure) as ctx257:
            walk_enforce_l1_l4({"nonce": "n" * 257})
        self.assertEqual(ctx257.exception.code, "nonce_invalid")
        # Nonce must not be judged under L4=4096
        with self.assertRaises(LimitFailure) as ctx:
            walk_enforce_l1_l4({"nonce": "n" * 300})
        self.assertEqual(ctx.exception.code, "nonce_invalid")

    def test_mixed_nesting_and_wide(self) -> None:
        walk_enforce_l1_l4({"o": {"a": [1, {"b": []}]}, "w": list(range(10))})

    def test_l5_boundary(self) -> None:
        enforce_l5_canon_bytes(b"a" * 16383)
        enforce_l5_canon_bytes(b"a" * 16384)
        with self.assertRaises(LimitFailure) as ctx:
            enforce_l5_canon_bytes(b"a" * 16385)
        self.assertEqual(ctx.exception.code, "resource_limit_exceeded")

    def test_l6_boundary_and_fallback(self) -> None:
        enforce_l6_response_bytes(b"a" * 16383)
        enforce_l6_response_bytes(b"a" * 16384)
        with self.assertRaises(LimitFailure):
            enforce_l6_response_bytes(b"a" * 16385)
        env, raw = measured_l6_fallback_envelope(
            interface_profile="l28-universal-ai-access-interface/v0.1",
            operation="get_balance",
            request_id="a" * 64,
        )
        self.assertFalse(env["ok"])
        self.assertEqual(env["code"], "resource_limit_exceeded")
        self.assertEqual(env["detail"], "")
        self.assertEqual(env["result"], {})
        self.assertLessEqual(len(raw), 16384)
        # non-recursive: building again yields identical bytes
        env2 = build_l6_fallback_envelope(
            interface_profile="l28-universal-ai-access-interface/v0.1",
            operation="get_balance",
            request_id="a" * 64,
        )
        self.assertEqual(serialize_uaii_response(env), serialize_uaii_response(env2))

    def test_received_size_via_decode(self) -> None:
        decode_uaii_json(b'{"a":1}')
        decode_uaii_json(b"{" + b" " * 16370 + b"}")  # may be json_invalid but size ok path
        with self.assertRaises(UaiiJsonError) as ctx:
            decode_uaii_json(b"x" * 16385)
        self.assertEqual(ctx.exception.code, "input_too_large")

    def test_received_size_16383_16384(self) -> None:
        # exact-size legal JSON object padded inside string value under L4
        def make(n: int) -> bytes:
            # {"s":"<pad>"} minimal overhead
            overhead = len(b'{"s":""}')
            pad = n - overhead
            self.assertGreater(pad, 0)
            return b'{"s":"' + (b"a" * pad) + b'"}'

        b16383 = make(16383)
        b16384 = make(16384)
        self.assertEqual(len(b16383), 16383)
        self.assertEqual(len(b16384), 16384)
        decode_uaii_json(b16383)
        decode_uaii_json(b16384)
        with self.assertRaises(UaiiJsonError) as ctx:
            decode_uaii_json(make(16384) + b"x")
        self.assertEqual(ctx.exception.code, "input_too_large")

    def test_invalid_utf8_and_malformed_json(self) -> None:
        with self.assertRaises(UaiiJsonError) as e1:
            decode_uaii_json(b"\xff\xfe")
        self.assertEqual(e1.exception.code, "encoding_invalid")
        with self.assertRaises(UaiiJsonError) as e2:
            decode_uaii_json(b"{not-json")
        self.assertEqual(e2.exception.code, "json_invalid")

    def test_duplicate_keys_multiple_depths(self) -> None:
        with self.assertRaises(UaiiJsonError) as e1:
            decode_uaii_json(b'{"a":1,"a":2}')
        self.assertEqual(e1.exception.code, "duplicate_key")
        with self.assertRaises(UaiiJsonError) as e2:
            decode_uaii_json(b'{"o":{"x":1,"x":2}}')
        self.assertEqual(e2.exception.code, "duplicate_key")

    def test_lone_and_paired_surrogates(self) -> None:
        with self.assertRaises(UaiiJsonError) as e1:
            decode_uaii_json(b'{"s":"\\uD800"}')
        self.assertEqual(e1.exception.code, "encoding_invalid")
        with self.assertRaises(UaiiJsonError) as e2:
            decode_uaii_json(b'{"s":"\\uDC00"}')
        self.assertEqual(e2.exception.code, "encoding_invalid")
        obj = decode_uaii_json(b'{"s":"\\uD83D\\uDE00"}')
        self.assertEqual(obj["s"], "😀")
        literal = decode_uaii_json('{"s":"😀"}'.encode("utf-8"))
        self.assertEqual(literal["s"], obj["s"])
        self.assertEqual(canon_uaii(obj), canon_uaii(literal))

    def test_wire_vs_canonical_size(self) -> None:
        wire = b'{ "a" : 1 }'
        obj = decode_uaii_json(wire)
        canon = canon_uaii(obj)
        self.assertLess(len(canon), len(wire))
        enforce_l5_canon_bytes(canon)

    def test_input_type_invalid(self) -> None:
        with self.assertRaises(UaiiJsonError) as ctx:
            decode_uaii_json(123)  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.code, "input_type_invalid")

    def test_m2m_canonicalize_not_used_for_uaii_order(self) -> None:
        # UAII preserves insertion order; M2M sorts keys
        obj = {"b": 1, "a": 2}
        self.assertEqual(canon_uaii(obj), b'{"b":1,"a":2}')
        from coin import m2m_verifier as mv

        m2m = mv.canonicalize(obj)
        m2m_b = m2m if isinstance(m2m, bytes) else m2m.encode()
        self.assertEqual(m2m_b, b'{"a":2,"b":1}')
        self.assertNotEqual(canon_uaii(obj), m2m_b)

    def test_overlong_truncated_and_bad_continuation_utf8(self) -> None:
        for payload in (b"\xc0\xaf", b"\xe2\x82", b"\xe2\x28\xa1", b"\xf0\x9f"):
            with self.assertRaises(UaiiJsonError) as ctx:
                decode_uaii_json(payload)
            self.assertEqual(ctx.exception.code, "encoding_invalid")

    def test_surrogate_variants(self) -> None:
        for payload in (
            b'{"s":"\\uD800"}',
            b'{"s":"\\uDC00"}',
            b'{"s":"\\uDC00\\uD800"}',
            b'{"s":"\\uD800\\uD800"}',
        ):
            with self.assertRaises(UaiiJsonError) as ctx:
                decode_uaii_json(payload)
            self.assertEqual(ctx.exception.code, "encoding_invalid")
        pair = decode_uaii_json(b'{"s":"\\uD83D\\uDE00"}')
        lit = decode_uaii_json('{"s":"😀"}'.encode("utf-8"))
        self.assertEqual(pair["s"], lit["s"])
        self.assertEqual(canon_uaii(pair), canon_uaii(lit))
        a = serialize_uaii_response({"ok": False, "code": "encoding_invalid", "interface_profile": "", "operation": "", "request_id": "", "result": {}, "execution_authorized": False, "report_id": "", "detail": ""})
        b = serialize_uaii_response({"ok": False, "code": "encoding_invalid", "interface_profile": "", "operation": "", "request_id": "", "result": {}, "execution_authorized": False, "report_id": "", "detail": ""})
        self.assertEqual(a, b)

    def test_escape_equivalent_duplicate_keys(self) -> None:
        with self.assertRaises(UaiiJsonError) as ctx:
            decode_uaii_json(b'{"a":1,"\\u0061":2}')
        self.assertEqual(ctx.exception.code, "duplicate_key")

    def test_cycle_direct_indirect_and_shared_acyclic(self) -> None:
        direct: dict = {}
        direct["self"] = direct
        with self.assertRaises(LimitFailure) as c1:
            walk_enforce_l1_l4(direct)
        self.assertEqual(c1.exception.code, "json_invalid")

        a: dict = {}
        b: dict = {"a": a}
        a["b"] = b
        with self.assertRaises(LimitFailure) as c2:
            walk_enforce_l1_l4({"root": a})
        self.assertEqual(c2.exception.code, "json_invalid")

        shared = {"x": 1}
        root = {"left": shared, "right": shared}
        walk_enforce_l1_l4(root)
        walk_enforce_l1_l4(root)  # repeated-run

        # Shared acyclic array referenced from multiple locations (not a cycle).
        shared_arr = [1, 2, 3]
        arr_root = {"first": shared_arr, "second": shared_arr}
        walk_enforce_l1_l4(arr_root)
        walk_enforce_l1_l4(arr_root)  # repeated-run


if __name__ == "__main__":
    unittest.main()
