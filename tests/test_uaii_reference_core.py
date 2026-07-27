# SPDX-License-Identifier: Apache-2.0
"""Focused Foundation 58/62/63 UAII reference-core tests."""

from __future__ import annotations

import hashlib
import json
import unittest
from typing import Any
from unittest import mock

from coin import tx_validation
from coin.uaii_json import canon_uaii, serialize_uaii_response
from coin.uaii_reference_core import (
    CORRELATION_FIELDS,
    INTERFACE_PROFILE,
    OPERATIONS,
    UAII_CLOCK_SKEW_TOLERANCE_SECONDS,
    execution_authorized,
    implementation_authorized,
    ledger_mutated,
    process_uaii_request,
    spend_authorized,
    uaii_m2m_correlation_id,
)
from coin.uaii_resource_limits import build_l6_fallback_envelope


def _hex64(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


class _Replay:
    def __init__(self, present: set[str] | None = None, unavailable: bool = False) -> None:
        self.present = present or set()
        self.unavailable = unavailable

    def lookup(self, key: str) -> str:
        if self.unavailable:
            return "unavailable"
        return "present" if key in self.present else "absent"


class _Ledger:
    def __init__(self, balances: dict[str, int] | None = None, height: int = 100878) -> None:
        self.balances = balances or {"alice": 1000, "bob": 0}
        self.height = height

    def read_binding(self) -> dict[str, Any]:
        return {
            "canonical_height": self.height,
            "issued_supply": 2824584,
            "canonical_issuance_ready": True,
            "accepted_tx_count": 0,
        }

    def get_balance(self, address: str) -> int:
        return int(self.balances.get(address, 0))


class _Protocol:
    def __init__(self, balances: dict[str, int] | None = None) -> None:
        self.balances = balances or {"alice": 1000, "bob": 0}
        self.seen: set[str] = set()

    def current_balance_lookup(self, address: str, _currency: str) -> int:
        return int(self.balances.get(address, 0))

    def seen_tx_lookup(self, tx_id: str) -> bool:
        return tx_id in self.seen


def _context(
    *,
    t_eval: int = 1_700_000_000,
    balances: dict[str, int] | None = None,
    replay: _Replay | None = None,
) -> dict[str, Any]:
    ledger = _Ledger(balances=balances)
    protocol = _Protocol(balances=balances or ledger.balances)
    return {
        "t_eval": t_eval,
        "ledger_state": ledger,
        "replay_state": replay or _Replay(),
        "protocol_validate": protocol,
    }


def _envelope(operation: str, params: dict[str, Any], *, nonce: str = "n1", request_id: str | None = None) -> dict[str, Any]:
    return {
        "interface_profile": INTERFACE_PROFILE,
        "operation": operation,
        "request_id": request_id or _hex64(operation + nonce),
        "created_at": 1_699_999_000,
        "expires_at": 1_700_000_100,
        "nonce": nonce,
        "execution_authorized": False,
        "params": params,
    }


def _call(env: dict[str, Any], ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = json.dumps(env, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return process_uaii_request(raw, ctx if ctx is not None else _context())


class TestUaiiReferenceCore(unittest.TestCase):
    def test_authorization_flags(self) -> None:
        self.assertIs(execution_authorized, False)
        self.assertIs(implementation_authorized, True)
        self.assertIs(spend_authorized, False)
        self.assertIs(ledger_mutated, False)

    def test_skew_constant(self) -> None:
        self.assertEqual(UAII_CLOCK_SKEW_TOLERANCE_SECONDS, 300)

    def test_seven_operations_tuple(self) -> None:
        self.assertEqual(len(OPERATIONS), 7)

    def test_input_type_and_size_and_encoding(self) -> None:
        r = process_uaii_request(123, _context())  # type: ignore[arg-type]
        self.assertEqual(r["code"], "input_type_invalid")
        self.assertFalse(r["ok"])
        self.assertEqual(r["detail"], "")
        r2 = process_uaii_request(b"x" * 16385, _context())
        self.assertEqual(r2["code"], "input_too_large")
        r3 = process_uaii_request(b"\xff\xfe{}", _context())
        self.assertEqual(r3["code"], "encoding_invalid")

    def test_json_duplicate_and_secret_precedence(self) -> None:
        r = process_uaii_request(b'{"a":1,"a":2}', _context())
        self.assertEqual(r["code"], "duplicate_key")
        env = _envelope("get_protocol_status", {})
        env["params"] = {"password": "x"}
        # secrets after L1-L4; schema would also fail but secret scan is Outer 4
        # put secret at top level
        bad = dict(env)
        bad["api_key"] = "x"
        # unknown field → still scanned; order of keys may break envelope schema after secrets
        raw = json.dumps(bad, separators=(",", ":")).encode()
        # duplicate-free decode then L1-L4 then secrets
        r2 = process_uaii_request(raw, _context())
        self.assertEqual(r2["code"], "secret_material_forbidden")

    def test_lone_surrogate_encoding_invalid(self) -> None:
        r = process_uaii_request(b'{"s":"\\uD800"}', _context())
        self.assertEqual(r["code"], "encoding_invalid")

    def test_discover_capabilities(self) -> None:
        r = _call(_envelope("discover_capabilities", {"include_adapter_declarations": False}))
        self.assertTrue(r["ok"])
        self.assertEqual(r["code"], "capabilities_ok")
        self.assertEqual(r["result"]["operations"], list(OPERATIONS))
        self.assertFalse(r["result"]["execution_authorized"])
        self.assertEqual(r["detail"], "")
        self.assertEqual(len(r["report_id"]), 64)

    def test_get_protocol_status_economics(self) -> None:
        r = _call(_envelope("get_protocol_status", {}))
        self.assertTrue(r["ok"])
        self.assertEqual(r["code"], "protocol_status_ok")
        self.assertEqual(r["result"]["max_supply"], 28_000_000)
        self.assertEqual(r["result"]["emission_ceiling"], 11_130_000)
        self.assertEqual(r["result"]["historical_mined"], 2_824_584)
        self.assertEqual(
            r["result"]["validation_authority"],
            "coin.tx_validation.validate_transaction",
        )
        self.assertEqual(
            (
                tx_validation.L28_MAX_SUPPLY,
                tx_validation.L28_EMISSION_CEILING,
                tx_validation.L28_HISTORICAL_MINED,
            ),
            (28_000_000, 11_130_000, 2_824_584),
        )

    def test_get_balance_success_code_empty(self) -> None:
        r = _call(_envelope("get_balance", {"address": "alice", "require_canonical_height": True}))
        self.assertTrue(r["ok"])
        self.assertEqual(r["operation"], "get_balance")
        self.assertEqual(r["code"], "")
        self.assertEqual(r["result"]["balance"], 1000)
        self.assertEqual(len(r["result"]["ledger_state_id"]), 64)
        self.assertFalse(r["result"]["execution_authorized"])

    def test_create_quote_and_payment_and_validate(self) -> None:
        ctx = _context()
        q_params = {
            "payer_identity": "alice",
            "payee_identity": "bob",
            "service_id": "svc",
            "service_params": {},
            "amount": 10,
            "currency": "L28",
            "purpose": "test",
            "quote_expires_at": 1_700_000_050,
            "quote_nonce": "qnonce1",
            "max_amount": 10,
            "rejectable": True,
            "service_terms": {},
        }
        rq = _call(_envelope("create_quote", q_params, nonce="nq"), ctx)
        self.assertTrue(rq["ok"], rq)
        self.assertEqual(rq["code"], "quote_created")
        quote = rq["result"]["quote"]
        quote_id = rq["result"]["quote_id"]
        self.assertFalse(rq["result"]["spend_authorized"])

        pay_params = {
            "quote": quote,
            "quote_id": quote_id,
            "payer_identity": "alice",
            "payee_identity": "bob",
            "amount": 10,
            "currency": "L28",
            "purpose": "test",
            "service_id": "svc",
            "payment_nonce": "pnonce1",
            "payment_expires_at": 1_700_000_040,
        }
        rp = _call(_envelope("create_unsigned_payment_request", pay_params, nonce="np"), ctx)
        self.assertTrue(rp["ok"], rp)
        payment = rp["result"]["unsigned_payment_request"]
        payment_request_id = rp["result"]["payment_request_id"]
        self.assertFalse(rp["result"]["spend_authorized"])

        transfer = {
            "sender": "alice",
            "receiver": "bob",
            "amount": 10,
            "timestamp": 1_700_000_000,
            "nonce": 1,
        }
        # UAII proposed_transfer is five fields only; delegate expands for Protocol.
        class _PV:
            def __init__(self) -> None:
                self.inner = _Protocol()

            def validate(self, transfer_dict: dict[str, Any]) -> tuple[bool, str, str]:
                tx = {
                    "version": 1,
                    "currency": "L28",
                    **transfer_dict,
                }
                return tx_validation.validate_transaction(
                    tx,
                    policy=tx_validation.TxPolicy(),
                    current_balance_lookup=self.inner.current_balance_lookup,
                    seen_tx_lookup=self.inner.seen_tx_lookup,
                    verify_signature=None,
                )

        ctx2 = _context()
        ctx2["protocol_validate"] = _PV()
        rv = _call(
            _envelope(
                "validate_payment",
                {
                    "quote": quote,
                    "quote_id": quote_id,
                    "unsigned_payment_request": payment,
                    "payment_request_id": payment_request_id,
                    "proposed_transfer": transfer,
                    "check_ledger_balance": True,
                },
                nonce="nv",
            ),
            ctx2,
        )
        self.assertTrue(rv["ok"], rv)
        self.assertEqual(rv["code"], "payment_validation_ok")
        self.assertTrue(rv["result"]["validate_transaction_invoked"])
        self.assertTrue(rv["result"]["validate_transaction_ok"])
        self.assertFalse(rv["result"]["ledger_mutated"])

    def test_get_payment_receipt(self) -> None:
        params = {
            "quote_id": _hex64("q"),
            "payment_request_id": _hex64("p"),
            "payer_identity": "alice",
            "payee_identity": "bob",
            "amount": 5,
            "currency": "L28",
            "service_id": "svc",
            "service_result_hash": _hex64("s"),
            "l28_tx_id": _hex64("t"),
            "l28_sender": "alice",
            "l28_receiver": "bob",
            "l28_amount": 5,
            "l28_timestamp": 1_700_000_000,
            "verification_status": "verified",
            "completed_at": 1_700_000_001,
            "receipt_nonce": "rnonce",
        }
        r = _call(_envelope("get_payment_receipt", params, nonce="nr"))
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["code"], "payment_receipt_ok")
        self.assertFalse(r["result"]["execution_authorized"])

    def test_replay_and_skew(self) -> None:
        env = _envelope("get_protocol_status", {}, nonce="unique-replay")
        # compute replay key like core
        from coin.uaii_reference_core import _replay_key

        key = _replay_key(operation="get_protocol_status", nonce="unique-replay")
        r = _call(env, _context(replay=_Replay(present={key})))
        self.assertEqual(r["code"], "nonce_replay")
        # expired
        r2 = _call(env, _context(t_eval=env["expires_at"] + 301))
        self.assertEqual(r2["code"], "request_expired")

    def test_no_tip_ledger_binding(self) -> None:
        # ledger.py still uses unordered set; binding uses cardinality only
        import pathlib

        text = pathlib.Path("coin/ledger.py").read_text()
        self.assertIn("self._seen_tx_ids: set[str] = set()", text)
        r = _call(_envelope("get_balance", {"address": "alice", "require_canonical_height": False}))
        self.assertTrue(r["ok"])
        self.assertNotIn("LEDGER-TIP", json.dumps(r))

    def test_response_field_order_and_repeated_bytes(self) -> None:
        env = _envelope("get_protocol_status", {}, nonce="stable")
        r1 = _call(env)
        r2 = _call(env)
        self.assertEqual(list(r1.keys()), [
            "ok",
            "code",
            "interface_profile",
            "operation",
            "request_id",
            "result",
            "execution_authorized",
            "report_id",
            "detail",
        ])
        self.assertEqual(serialize_uaii_response(r1), serialize_uaii_response(r2))
        self.assertEqual(r1["detail"], "")

    def test_l6_fallback_builder_unit(self) -> None:
        fb = build_l6_fallback_envelope(
            interface_profile=INTERFACE_PROFILE,
            operation="discover_capabilities",
            request_id=_hex64("x"),
        )
        self.assertFalse(fb["ok"])
        self.assertEqual(fb["code"], "resource_limit_exceeded")
        self.assertNotIn("limit_id", fb)
        raw = serialize_uaii_response(fb)
        self.assertLessEqual(len(raw), 16384)

    def _patch_oversized_first_serialize(self):
        real = serialize_uaii_response
        state = {"n": 0}

        def wrapper(envelope: dict[str, Any]) -> bytes:
            state["n"] += 1
            if state["n"] == 1:
                return b"x" * 16385
            return real(envelope)

        return mock.patch.multiple(
            "coin.uaii_reference_core",
            serialize_uaii_response=wrapper,
        ), mock.patch.multiple(
            "coin.uaii_resource_limits",
            serialize_uaii_response=wrapper,
        ), state

    def test_process_uaii_request_l6_oversized_success_fallback(self) -> None:
        p_core, p_lim, state = self._patch_oversized_first_serialize()
        with p_core, p_lim:
            r = _call(_envelope("get_protocol_status", {}, nonce="l6s"))
        self.assertGreaterEqual(state["n"], 2)
        self.assertFalse(r["ok"])
        self.assertEqual(r["code"], "resource_limit_exceeded")
        self.assertEqual(r["detail"], "")
        self.assertEqual(r["result"], {})
        self.assertEqual(r["report_id"], "")
        self.assertNotIn("limit_id", r)
        raw = serialize_uaii_response(r)
        self.assertLessEqual(len(raw), 16384)
        self.assertEqual(list(r.keys()), [
            "ok", "code", "interface_profile", "operation", "request_id",
            "result", "execution_authorized", "report_id", "detail",
        ])
        r2 = _call(_envelope("get_protocol_status", {}, nonce="l6s2"))
        # without patch, ordinary success still works
        self.assertTrue(r2["ok"])
        self.assertEqual(r2["code"], "protocol_status_ok")

    def test_process_uaii_request_l6_oversized_failure_fallback(self) -> None:
        p_core, p_lim, state = self._patch_oversized_first_serialize()
        with p_core, p_lim:
            r = process_uaii_request(b'{"a":1,"a":2}', _context())
        self.assertGreaterEqual(state["n"], 2)
        self.assertFalse(r["ok"])
        self.assertEqual(r["code"], "resource_limit_exceeded")
        self.assertEqual(r["detail"], "")
        self.assertEqual(r["result"], {})
        blob = serialize_uaii_response(r)
        self.assertLessEqual(len(blob), 16384)
        self.assertNotIn(b"limit_id", blob)
        # ordinary failure without patch
        r2 = process_uaii_request(b'{"a":1,"a":2}', _context())
        self.assertEqual(r2["code"], "duplicate_key")
        self.assertEqual(r2["detail"], "")

    def test_resource_limit_depth_via_request(self) -> None:
        # Build illegal depth inside params after a minimal envelope shell by
        # nesting in a side structure that still parses — use service_params path
        # through create_quote would need full schema; instead nest under a
        # temporary object passed only through decode+walk by calling walk via
        # process with deep params on discover which only allows one boolean.
        # Deep nesting under an unknown envelope is schema_invalid after secrets.
        # Use get_protocol_status with deep nesting inside a forged larger tree:
        deep = {"a": {}}
        cur = deep["a"]
        for _ in range(40):
            cur["a"] = {}
            cur = cur["a"]
        # Place deep structure as params illegally (extra nesting as value only if
        # params is deep object) — get_protocol_status requires empty params, so
        # L1-L4 fires first on the whole request tree.
        env = _envelope("get_protocol_status", deep)
        r = _call(env)
        self.assertEqual(r["code"], "resource_limit_exceeded")

    def test_no_secret_diagnostics(self) -> None:
        env = _envelope("get_protocol_status", {})
        env["private_key"] = "SUPER_SECRET"
        r = _call(env)
        self.assertEqual(r["code"], "secret_material_forbidden")
        blob = serialize_uaii_response(r)
        self.assertNotIn(b"SUPER_SECRET", blob)
        self.assertNotIn(b"limit_id", blob)

    def test_property_name_grammar_and_precedence(self) -> None:
        # valid names
        r_ok = _call(_envelope("get_protocol_status", {}))
        self.assertTrue(r_ok["ok"])
        # uppercase / hyphen / space / leading digit / empty / unicode / nested
        cases = [
            {"BadKey": 1},
            {"bad-key": 1},
            {"bad key": 1},
            {"1bad": 1},
            {"": 1},
            {"café": 1},
            {"outer": {"Inner": 1}},
            {"outer": {"mid": {"Also_Bad": 1}}},  # uppercase A — invalid
        ]
        # Also_Bad has uppercase — invalid. use nested Bad
        cases[-1] = {"outer": {"mid": {"Bad": 1}}}
        for extra in cases:
            env = _envelope("get_protocol_status", {})
            # inject invalid key at root beside envelope — breaks key order too,
            # but grammar runs after secrets before schema key-order check when
            # key is nested inside params:
            env["params"] = extra if "outer" in extra or any(
                k not in ("include_adapter_declarations",) for k in extra
            ) else extra
            # For get_protocol_status, non-empty params fail schema after grammar.
            # Put invalid name inside a wrapper under a forged tree by replacing params:
            if list(extra.keys()) == ["outer"]:
                env["params"] = extra
            else:
                env = _envelope("discover_capabilities", {"include_adapter_declarations": False})
                # nest invalid under a temporary object by adding sibling invalid key on params
                env["params"] = {"include_adapter_declarations": False, **extra}
            r = _call(env)
            self.assertEqual(r["code"], "schema_invalid", extra)
            self.assertFalse(r["ok"])
            self.assertEqual(r["detail"], "")
            self.assertEqual(list(r.keys())[0], "ok")
        # valid lowercase/number/underscore nested (but wrong schema for discover)
        env = _envelope(
            "discover_capabilities",
            {"include_adapter_declarations": False, "extra_field": 1},
        )
        # extra_field is grammatically valid → schema_invalid from key order, not grammar
        r = _call(env)
        self.assertEqual(r["code"], "schema_invalid")
        # secrets beat property grammar for ENV-like keys
        env = _envelope("get_protocol_status", {})
        env["AWS_SECRET"] = "x"
        r = _call(env)
        self.assertEqual(r["code"], "secret_material_forbidden")
        # duplicates beat grammar
        r = process_uaii_request(b'{"Bad":1,"Bad":2}', _context())
        self.assertEqual(r["code"], "duplicate_key")
        # create_quote rejects BadKey in service_params
        q_params = {
            "payer_identity": "alice",
            "payee_identity": "bob",
            "service_id": "svc",
            "service_params": {"BadKey": 1},
            "amount": 10,
            "currency": "L28",
            "purpose": "test",
            "quote_expires_at": 1_700_000_050,
            "quote_nonce": "qnonce1",
            "max_amount": 10,
            "rejectable": True,
            "service_terms": {},
        }
        r = _call(_envelope("create_quote", q_params, nonce="pg"))
        self.assertEqual(r["code"], "schema_invalid")
        self.assertFalse(r["ok"])

    def test_uaii_m2m_correlation_formula(self) -> None:
        oid = "a" * 64
        mid = "b" * 64
        corr = {
            "correlation_profile": "l28-uaii-m2m-correlation/v0.1",
            "uaii_interface_profile": INTERFACE_PROFILE,
            "uaii_object_kind": "quote",
            "uaii_object_id": oid,
            "m2m_protocol": "L28-M2M",
            "m2m_protocol_version": "0.1",
            "m2m_message_id": mid,
        }
        self.assertEqual(tuple(corr.keys()), CORRELATION_FIELDS)
        # Fixed normative CanonUaii preimage (exact field order, separators, UTF-8).
        # Intentionally NOT derived via production canon_uaii / json.dumps helpers.
        fixed_preimage = (
            b'{"correlation_profile":"l28-uaii-m2m-correlation/v0.1",'
            b'"uaii_interface_profile":"l28-universal-ai-access-interface/v0.1",'
            b'"uaii_object_kind":"quote",'
            b'"uaii_object_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
            b'"m2m_protocol":"L28-M2M",'
            b'"m2m_protocol_version":"0.1",'
            b'"m2m_message_id":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}'
        )
        domain = b"L28-UAII-V0.1-M2M-CORRELATION\x00"
        fixed_digest = (
            "162a8f9d2efe474492de5480b77108a144ade0da98ad50a7ec4427ad1342914e"
        )
        self.assertEqual(len(fixed_preimage), 370)
        self.assertTrue(fixed_preimage.startswith(b'{"correlation_profile":'))
        self.assertIn(b'"uaii_object_id":"' + oid.encode("ascii") + b'"', fixed_preimage)
        self.assertIn(b'"m2m_message_id":"' + mid.encode("ascii") + b'"', fixed_preimage)
        # Independent SHA-256 over domain || fixed preimage (stdlib only).
        self.assertEqual(
            hashlib.sha256(domain + fixed_preimage).hexdigest(),
            fixed_digest,
        )
        got = uaii_m2m_correlation_id(corr)
        self.assertEqual(got, fixed_digest)
        self.assertEqual(len(got), 64)
        self.assertEqual(uaii_m2m_correlation_id(corr), got)  # repeated-run
        # mutation-negative
        mutated = dict(corr)
        mutated["m2m_message_id"] = "c" * 64
        self.assertNotEqual(uaii_m2m_correlation_id(mutated), got)
        # collision when message_id == object_id
        bad = dict(corr)
        bad["m2m_message_id"] = oid
        with self.assertRaises(Exception) as ctx:
            uaii_m2m_correlation_id(bad)
        self.assertEqual(ctx.exception.code, "uaii_m2m_id_collision")
        # wrong kind
        bad2 = dict(corr)
        bad2["uaii_object_kind"] = "nope"
        with self.assertRaises(Exception) as ctx2:
            uaii_m2m_correlation_id(bad2)
        self.assertEqual(ctx2.exception.code, "uaii_m2m_mapping_mismatch")
        # operation-level: quote_id from create_quote can be correlated with distinct m2m id
        ctx = _context()
        q_params = {
            "payer_identity": "alice",
            "payee_identity": "bob",
            "service_id": "svc",
            "service_params": {},
            "amount": 10,
            "currency": "L28",
            "purpose": "test",
            "quote_expires_at": 1_700_000_050,
            "quote_nonce": "qnonce1",
            "max_amount": 10,
            "rejectable": True,
            "service_terms": {},
        }
        rq = _call(_envelope("create_quote", q_params, nonce="corrq"), ctx)
        self.assertTrue(rq["ok"], rq)
        quote_id = rq["result"]["quote_id"]
        corr_op = {
            "correlation_profile": "l28-uaii-m2m-correlation/v0.1",
            "uaii_interface_profile": INTERFACE_PROFILE,
            "uaii_object_kind": "quote",
            "uaii_object_id": quote_id,
            "m2m_protocol": "L28-M2M",
            "m2m_protocol_version": "0.1",
            "m2m_message_id": _hex64("m2m-envelope"),
        }
        cid = uaii_m2m_correlation_id(corr_op)
        self.assertEqual(len(cid), 64)
        self.assertNotEqual(cid, quote_id)

    def test_canon_uaii_distinct_from_m2m(self) -> None:
        obj = {"b": 1, "a": 2}
        self.assertEqual(canon_uaii(obj), b'{"b":1,"a":2}')


if __name__ == "__main__":
    unittest.main()
