from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from coin import cross_ai_interoperability_demo as cross
from coin import two_agent_service_external_access_demo as ext


def _fake_purchase(text: str, seed: str) -> dict:
    return {
        "service_id": ext.SERVICE_ID,
        "asset_id": "L28",
        "quoted_amount": 28,
        "canonical_validation": "PASS",
        "payment_applied": True,
        "payment_verified": True,
        "agent_a_balance_before": 100,
        "agent_b_balance_before": 0,
        "agent_a_balance_after": 72,
        "agent_b_balance_after": 28,
        "service_executed": True,
        "service_result_verified": True,
        "receipt_created": True,
        "receipt_verified": True,
        "payment_tx_id": seed * 64,
        "service_result_id": chr(ord(seed) + 1) * 64,
        "receipt_id": chr(ord(seed) + 2) * 64,
        "canonical_history_touched": False,
        "public_network_used": False,
        "production_keys_used": False,
        "service_output": {
            "character_count": len(text),
            "word_count": len(text.split()),
            "unique_word_count": len(set(text.lower().split())),
            "sentence_count": 1,
            "top_terms": [],
            "input_digest": "d" * 64,
        },
    }


def _http_payload(text: str) -> dict:
    return {
        "ok": True,
        "runtime_profile": ext.RUNTIME_PROFILE,
        "service_id": ext.SERVICE_ID,
        "purchase": _fake_purchase(text, "a"),
    }


def _mcp_payload(text: str) -> dict:
    return {
        "ok": True,
        "runtime_profile": ext.RUNTIME_PROFILE,
        "service_id": ext.SERVICE_ID,
        "purchase": _fake_purchase(text, "1"),
    }


def test_provider_request_builders_match_frozen_shapes():
    text = "alpha beta"
    openai_call = cross.build_openai_compatible_tool_call(text)
    assert openai_call["id"] == cross.OPENAI_REQUEST_ID
    assert openai_call["type"] == "function"
    assert openai_call["function"]["name"] == ext.MCP_TOOL_NAME
    assert json.loads(openai_call["function"]["arguments"]) == {
        "service_id": ext.SERVICE_ID,
        "input": text,
    }

    anthropic = cross.build_anthropic_compatible_tool_use(text)
    assert anthropic == {
        "type": "tool_use",
        "id": cross.ANTHROPIC_REQUEST_ID,
        "name": ext.MCP_TOOL_NAME,
        "input": {
            "service_id": ext.SERVICE_ID,
            "input": text,
        },
    }


def test_openai_compatible_adapter_uses_existing_http_runtime(monkeypatch):
    calls = []

    def fake_http(text):
        calls.append(text)
        return 200, _http_payload(text), {
            "event": "http_runtime_started",
            "host": ext.LOOPBACK_HOST,
            "port": 12345,
            "path": ext.PURCHASE_PATH,
            "service_id": ext.SERVICE_ID,
        }

    monkeypatch.setattr(ext, "_run_http_external_purchase", fake_http)

    result = cross.run_openai_compatible_purchase(
        cross.build_openai_compatible_tool_call("alpha beta")
    )
    assert calls == ["alpha beta"]
    assert result["provider_request_id"] == cross.OPENAI_REQUEST_ID
    assert result["transport"] == "http_json"
    assert result["purchase"]["quoted_amount"] == 28
    assert result["purchase"]["payment_verified"] is True
    assert result["purchase"]["receipt_verified"] is True


def test_anthropic_compatible_adapter_uses_existing_mcp_runtime(monkeypatch):
    calls = []

    def fake_mcp(text):
        calls.append(text)
        return _mcp_payload(text), {
            "result": {"protocolVersion": ext.MCP_PROTOCOL_VERSION}
        }

    monkeypatch.setattr(ext, "_run_mcp_external_purchase", fake_mcp)

    result = cross.run_anthropic_compatible_purchase(
        cross.build_anthropic_compatible_tool_use("alpha beta")
    )
    assert calls == ["alpha beta"]
    assert result["provider_request_id"] == cross.ANTHROPIC_REQUEST_ID
    assert result["transport"] == "mcp_stdio"
    assert result["purchase"]["quoted_amount"] == 28
    assert result["purchase"]["payment_verified"] is True
    assert result["purchase"]["receipt_verified"] is True


def test_openai_failures_do_not_reach_http_runtime(monkeypatch):
    called = {"count": 0}

    def fake_http(_text):
        called["count"] += 1
        raise AssertionError("must not run")

    monkeypatch.setattr(ext, "_run_http_external_purchase", fake_http)

    bad = [
        None,
        {},
        {"id": "x", "type": "tool_use", "function": {}},
        {"id": "x", "type": "function", "function": None},
        {
            "id": "x",
            "type": "function",
            "function": {"name": "wrong", "arguments": "{}"},
        },
        {
            "id": "x",
            "type": "function",
            "function": {"name": ext.MCP_TOOL_NAME, "arguments": "{bad"},
        },
        {
            "id": "x",
            "type": "function",
            "function": {
                "name": ext.MCP_TOOL_NAME,
                "arguments": json.dumps(
                    {"service_id": "wrong", "input": "x"}
                ),
            },
        },
        {
            "id": "x",
            "type": "function",
            "function": {
                "name": ext.MCP_TOOL_NAME,
                "arguments": json.dumps(
                    {"service_id": ext.SERVICE_ID, "input": ""}
                ),
            },
        },
        {
            "id": "x",
            "type": "function",
            "function": {
                "name": ext.MCP_TOOL_NAME,
                "arguments": json.dumps(
                    {
                        "service_id": ext.SERVICE_ID,
                        "input": "x",
                        "amount": 1,
                    }
                ),
            },
        },
    ]

    for item in bad:
        with pytest.raises(cross.CrossAiError):
            cross.run_openai_compatible_purchase(item)

    assert called["count"] == 0


def test_anthropic_failures_do_not_reach_mcp_runtime(monkeypatch):
    called = {"count": 0}

    def fake_mcp(_text):
        called["count"] += 1
        raise AssertionError("must not run")

    monkeypatch.setattr(ext, "_run_mcp_external_purchase", fake_mcp)

    bad = [
        None,
        {},
        {
            "type": "function",
            "id": "x",
            "name": ext.MCP_TOOL_NAME,
            "input": {"service_id": ext.SERVICE_ID, "input": "x"},
        },
        {
            "type": "tool_use",
            "id": "x",
            "name": "wrong",
            "input": {"service_id": ext.SERVICE_ID, "input": "x"},
        },
        {
            "type": "tool_use",
            "id": "x",
            "name": ext.MCP_TOOL_NAME,
            "input": None,
        },
        {
            "type": "tool_use",
            "id": "x",
            "name": ext.MCP_TOOL_NAME,
            "input": {"service_id": "wrong", "input": "x"},
        },
        {
            "type": "tool_use",
            "id": "x",
            "name": ext.MCP_TOOL_NAME,
            "input": {"service_id": ext.SERVICE_ID, "input": ""},
        },
        {
            "type": "tool_use",
            "id": "x",
            "name": ext.MCP_TOOL_NAME,
            "input": {
                "service_id": ext.SERVICE_ID,
                "input": "x",
                "payment_tx_id": "caller-controlled",
            },
        },
    ]

    for item in bad:
        with pytest.raises(cross.CrossAiError):
            cross.run_anthropic_compatible_purchase(item)

    assert called["count"] == 0


def test_oversized_input_rejected_for_both_provider_shapes():
    too_long = "x" * (ext.MAX_INPUT_CHARS + 1)
    with pytest.raises(cross.CrossAiError):
        cross.build_openai_compatible_tool_call(too_long)
    with pytest.raises(cross.CrossAiError):
        cross.build_anthropic_compatible_tool_use(too_long)


def test_cross_provider_semantics_ignore_ephemeral_ids():
    openai_purchase = _fake_purchase("same input", "a")
    anthropic_purchase = _fake_purchase("same input", "1")

    assert cross._provider_semantics_equivalent(
        openai_purchase, anthropic_purchase
    ) is True

    anthropic_purchase["quoted_amount"] = 27
    assert cross._provider_semantics_equivalent(
        openai_purchase, anthropic_purchase
    ) is False


def test_execute_cross_ai_demo_preserves_traceability_and_equivalence(monkeypatch):
    text = "same input"

    monkeypatch.setattr(
        cross,
        "run_openai_compatible_purchase",
        lambda _call: {
            "provider_profile": cross.OPENAI_PROFILE,
            "provider_request_id": cross.OPENAI_REQUEST_ID,
            "provider_tool_name": ext.MCP_TOOL_NAME,
            "transport": "http_json",
            "external_call": True,
            "purchase_verified": True,
            "purchase": _fake_purchase(text, "a"),
        },
    )
    monkeypatch.setattr(
        cross,
        "run_anthropic_compatible_purchase",
        lambda _call: {
            "provider_profile": cross.ANTHROPIC_PROFILE,
            "provider_request_id": cross.ANTHROPIC_REQUEST_ID,
            "provider_tool_name": ext.MCP_TOOL_NAME,
            "transport": "mcp_stdio",
            "external_call": True,
            "purchase_verified": True,
            "purchase": _fake_purchase(text, "1"),
        },
    )

    out = cross.execute_cross_ai_interoperability_demo(text)
    assert out["openai_provider_request_id"] == "call_001"
    assert out["anthropic_provider_request_id"] == "toolu_001"
    assert out["openai_quoted_amount"] == 28
    assert out["anthropic_quoted_amount"] == 28
    assert out["same_l28_service"] is True
    assert out["same_l28_core_transaction"] is True
    assert out["stable_semantics_equivalent"] is True
    assert out["service_output_equivalent"] is True
    assert out["live_provider_api_used"] is False
    assert out["provider_credentials_used"] is False
    assert out["production_settlement"] is False


def test_module_has_no_live_provider_or_secret_access_and_no_direct_core_path():
    path = Path(cross.__file__)
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)

    imported_roots = set()
    function_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_names.add(node.name)

    assert not (
        imported_roots
        & {
            "openai",
            "anthropic",
            "requests",
            "httpx",
            "aiohttp",
            "socket",
            "urllib",
            "keyring",
        }
    )
    assert "validate_transaction" not in function_names
    assert "execute_two_agent_service_transaction" not in src
    assert "two_agent_service_transaction_demo" not in src
    assert "api.openai.com" not in src
    assert "api.anthropic.com" not in src
    assert "OPENAI_API_KEY" not in src
    assert "ANTHROPIC_API_KEY" not in src
    assert "os.environ" not in src
    assert "getenv(" not in src
    assert "private_bytes" not in src
    assert "from_private_bytes" not in src
    assert "two_agent_service_external_access_demo" in src


def test_main_emits_one_json_document(monkeypatch, capsys):
    monkeypatch.setattr(
        cross,
        "execute_cross_ai_interoperability_demo",
        lambda _text: {
            "openai_compatible_call": True,
            "anthropic_compatible_call": True,
        },
    )
    assert cross.main(["--input", "x"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {
        "anthropic_compatible_call": True,
        "openai_compatible_call": True,
    }
    assert captured.err == ""
