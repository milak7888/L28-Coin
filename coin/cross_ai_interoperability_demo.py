# SPDX-License-Identifier: Apache-2.0
"""Cross-AI provider-format interoperability for the bounded L28 purchase flow.

This module accepts two provider-compatible request shapes:

- OpenAI-compatible function/tool call -> existing L28 HTTP/JSON runtime
- Anthropic-compatible tool_use -> existing L28 MCP stdio runtime

No live commercial provider API is contacted. No provider credentials are read.
Both paths delegate through the already-published external-access runtime, which
in turn delegates to the existing two-agent L28 transaction core.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from coin import two_agent_service_external_access_demo as ext

DEMO_PROFILE = "l28-cross-ai-interoperability/v0.1"
OPENAI_PROFILE = "openai-compatible-tool-call/v0.1"
ANTHROPIC_PROFILE = "anthropic-compatible-tool-use/v0.1"
OPENAI_REQUEST_ID = "call_001"
ANTHROPIC_REQUEST_ID = "toolu_001"


class CrossAiError(Exception):
    """Fail-closed provider-adapter error."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _validate_provider_arguments(arguments: Any) -> str:
    try:
        return ext._validate_purchase_payload(arguments)
    except ext.ExternalAccessError as exc:
        raise CrossAiError(exc.code) from exc


def build_openai_compatible_tool_call(input_text: str) -> dict[str, Any]:
    _validate_provider_arguments({"service_id": ext.SERVICE_ID, "input": input_text})
    return {
        "id": OPENAI_REQUEST_ID,
        "type": "function",
        "function": {
            "name": ext.MCP_TOOL_NAME,
            "arguments": _canonical_json(
                {
                    "service_id": ext.SERVICE_ID,
                    "input": input_text,
                }
            ),
        },
    }


def parse_openai_compatible_tool_call(tool_call: Any) -> tuple[str, str]:
    if not isinstance(tool_call, dict) or set(tool_call) != {"id", "type", "function"}:
        raise CrossAiError("openai_tool_call_invalid")
    request_id = tool_call.get("id")
    if not isinstance(request_id, str) or not request_id:
        raise CrossAiError("openai_request_id_invalid")
    if tool_call.get("type") != "function":
        raise CrossAiError("openai_type_invalid")

    function = tool_call.get("function")
    if not isinstance(function, dict) or set(function) != {"name", "arguments"}:
        raise CrossAiError("openai_function_invalid")
    if function.get("name") != ext.MCP_TOOL_NAME:
        raise CrossAiError("openai_tool_name_invalid")

    raw_arguments = function.get("arguments")
    if not isinstance(raw_arguments, str):
        raise CrossAiError("openai_arguments_invalid")
    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError as exc:
        raise CrossAiError("openai_arguments_json_invalid") from exc

    input_text = _validate_provider_arguments(arguments)
    return request_id, input_text


def build_anthropic_compatible_tool_use(input_text: str) -> dict[str, Any]:
    _validate_provider_arguments({"service_id": ext.SERVICE_ID, "input": input_text})
    return {
        "type": "tool_use",
        "id": ANTHROPIC_REQUEST_ID,
        "name": ext.MCP_TOOL_NAME,
        "input": {
            "service_id": ext.SERVICE_ID,
            "input": input_text,
        },
    }


def parse_anthropic_compatible_tool_use(tool_use: Any) -> tuple[str, str]:
    if not isinstance(tool_use, dict) or set(tool_use) != {"type", "id", "name", "input"}:
        raise CrossAiError("anthropic_tool_use_invalid")
    if tool_use.get("type") != "tool_use":
        raise CrossAiError("anthropic_type_invalid")
    request_id = tool_use.get("id")
    if not isinstance(request_id, str) or not request_id:
        raise CrossAiError("anthropic_request_id_invalid")
    if tool_use.get("name") != ext.MCP_TOOL_NAME:
        raise CrossAiError("anthropic_tool_name_invalid")

    input_text = _validate_provider_arguments(tool_use.get("input"))
    return request_id, input_text


def run_openai_compatible_purchase(tool_call: Any) -> dict[str, Any]:
    """Translate an OpenAI-compatible tool call into the existing HTTP purchase path."""
    request_id, input_text = parse_openai_compatible_tool_call(tool_call)

    try:
        status, payload, startup = ext._run_http_external_purchase(input_text)
        if status != 200:
            raise CrossAiError("openai_http_purchase_failed")
        if startup.get("host") != ext.LOOPBACK_HOST:
            raise CrossAiError("openai_http_not_loopback")
        purchase = ext._verified_purchase(payload)
    except ext.ExternalAccessError as exc:
        raise CrossAiError(exc.code) from exc

    return {
        "provider_profile": OPENAI_PROFILE,
        "provider_request_id": request_id,
        "provider_tool_name": ext.MCP_TOOL_NAME,
        "transport": "http_json",
        "external_call": True,
        "purchase_verified": True,
        "purchase": purchase,
    }


def run_anthropic_compatible_purchase(tool_use: Any) -> dict[str, Any]:
    """Translate an Anthropic-compatible tool_use into the existing MCP path."""
    request_id, input_text = parse_anthropic_compatible_tool_use(tool_use)

    try:
        payload, initialize = ext._run_mcp_external_purchase(input_text)
        if initialize.get("result", {}).get("protocolVersion") != ext.MCP_PROTOCOL_VERSION:
            raise CrossAiError("anthropic_mcp_initialize_invalid")
        purchase = ext._verified_purchase(payload)
    except ext.ExternalAccessError as exc:
        raise CrossAiError(exc.code) from exc

    return {
        "provider_profile": ANTHROPIC_PROFILE,
        "provider_request_id": request_id,
        "provider_tool_name": ext.MCP_TOOL_NAME,
        "transport": "mcp_stdio",
        "external_call": True,
        "purchase_verified": True,
        "purchase": purchase,
    }


def _provider_semantics_equivalent(
    openai_purchase: dict[str, Any],
    anthropic_purchase: dict[str, Any],
) -> bool:
    return ext._stable_semantics(openai_purchase, anthropic_purchase)


def execute_cross_ai_interoperability_demo(input_text: str) -> dict[str, Any]:
    """Execute both provider-compatible flows through real existing runtimes."""
    openai_call = build_openai_compatible_tool_call(input_text)
    anthropic_call = build_anthropic_compatible_tool_use(input_text)

    openai_result = run_openai_compatible_purchase(openai_call)
    anthropic_result = run_anthropic_compatible_purchase(anthropic_call)

    openai_purchase = openai_result["purchase"]
    anthropic_purchase = anthropic_result["purchase"]

    equivalent = _provider_semantics_equivalent(openai_purchase, anthropic_purchase)
    service_output_equivalent = (
        openai_purchase["service_output"] == anthropic_purchase["service_output"]
    )
    if not equivalent or not service_output_equivalent:
        raise CrossAiError("cross_ai_semantics_mismatch")

    return {
        "demo_profile": DEMO_PROFILE,
        "openai_compatible_call": True,
        "openai_provider_profile": openai_result["provider_profile"],
        "openai_provider_request_id": openai_result["provider_request_id"],
        "openai_tool_name": openai_result["provider_tool_name"],
        "openai_transport": openai_result["transport"],
        "openai_external_call": openai_result["external_call"],
        "openai_purchase_verified": openai_result["purchase_verified"],
        "openai_quoted_amount": openai_purchase["quoted_amount"],
        "openai_payment_tx_id": openai_purchase["payment_tx_id"],
        "openai_payment_verified": openai_purchase["payment_verified"],
        "openai_service_executed": openai_purchase["service_executed"],
        "openai_service_result_id": openai_purchase["service_result_id"],
        "openai_receipt_id": openai_purchase["receipt_id"],
        "openai_receipt_verified": openai_purchase["receipt_verified"],
        "anthropic_compatible_call": True,
        "anthropic_provider_profile": anthropic_result["provider_profile"],
        "anthropic_provider_request_id": anthropic_result["provider_request_id"],
        "anthropic_tool_name": anthropic_result["provider_tool_name"],
        "anthropic_transport": anthropic_result["transport"],
        "anthropic_external_call": anthropic_result["external_call"],
        "anthropic_purchase_verified": anthropic_result["purchase_verified"],
        "anthropic_quoted_amount": anthropic_purchase["quoted_amount"],
        "anthropic_payment_tx_id": anthropic_purchase["payment_tx_id"],
        "anthropic_payment_verified": anthropic_purchase["payment_verified"],
        "anthropic_service_executed": anthropic_purchase["service_executed"],
        "anthropic_service_result_id": anthropic_purchase["service_result_id"],
        "anthropic_receipt_id": anthropic_purchase["receipt_id"],
        "anthropic_receipt_verified": anthropic_purchase["receipt_verified"],
        "service_id": ext.SERVICE_ID,
        "service_output": openai_purchase["service_output"],
        "same_l28_service": openai_purchase["service_id"] == anthropic_purchase["service_id"] == ext.SERVICE_ID,
        "same_l28_core_transaction": True,
        "stable_semantics_equivalent": equivalent,
        "service_output_equivalent": service_output_equivalent,
        "canonical_history_touched": (
            openai_purchase["canonical_history_touched"]
            or anthropic_purchase["canonical_history_touched"]
        ),
        "public_network_used": (
            openai_purchase["public_network_used"]
            or anthropic_purchase["public_network_used"]
        ),
        "live_provider_api_used": False,
        "provider_credentials_used": False,
        "provider_billing_used": False,
        "production_keys_used": (
            openai_purchase["production_keys_used"]
            or anthropic_purchase["production_keys_used"]
        ),
        "production_settlement": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m coin.cross_ai_interoperability_demo",
        description="Run OpenAI-compatible + Anthropic-compatible L28 interoperability.",
    )
    parser.add_argument(
        "--input",
        default="L28 enables machine payments between autonomous systems.",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    try:
        result = execute_cross_ai_interoperability_demo(args.input)
    except CrossAiError as exc:
        sys.stderr.write(exc.code + "\n")
        return 1

    sys.stdout.write(_canonical_json(result) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
