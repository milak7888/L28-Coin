# SPDX-License-Identifier: Apache-2.0
"""Pure in-process REST/OpenAPI-to-UAII mapping.

No HTTP server, socket, listener, network transport, authentication service,
signing, broadcast, settlement, wallet, or persistent state is created here.
"""

from __future__ import annotations

from typing import Any

from .uaii_json import UaiiJsonError, canon_uaii
from .uaii_reference_core import (
    ENVELOPE_FIELDS,
    INTERFACE_PROFILE,
    OPERATIONS,
    process_uaii_request,
)

adapter_implemented = True
openapi_document_available = True
runtime_activated = False
network_activated = False
server_started = False
listener_started = False
signing_authorized = False
spend_authorized = False
settlement_authorized = False
transaction_submission_authorized = False

REST_PREFIX = "/v1/uaii"
REST_PATHS = {
    f"{REST_PREFIX}/{operation}": operation
    for operation in OPERATIONS
}


class RestAdapterError(Exception):
    """Transport-boundary failure; never Protocol or settlement success."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def invoke_rest_request(
    method: str,
    path: str,
    body: dict[str, Any],
    context: Any = None,
) -> dict[str, Any]:
    """Map one offline HTTP-style request 1:1 into canonical UAII evaluation."""
    if method != "POST":
        raise RestAdapterError("rest_method_unsupported")

    operation = REST_PATHS.get(path)
    if operation is None:
        raise RestAdapterError("rest_path_unsupported")

    if not isinstance(body, dict):
        raise RestAdapterError("rest_body_invalid")

    if tuple(body.keys()) != ENVELOPE_FIELDS:
        raise RestAdapterError("rest_body_not_canonical")

    if body["operation"] != operation:
        raise RestAdapterError("rest_operation_mismatch")

    try:
        request_bytes = canon_uaii(body)
    except UaiiJsonError as exc:
        raise RestAdapterError("rest_body_not_canonical") from exc

    return process_uaii_request(request_bytes, context)


def build_openapi_document() -> dict[str, Any]:
    """Return a static, non-server OpenAPI description of the UAII mapping."""
    envelope_schema = {
        "type": "object",
        "description": (
            "Canonical UAII v0.1 request envelope. Exact field order and "
            "operation-specific params remain enforced by UAII."
        ),
        "required": list(ENVELOPE_FIELDS),
        "additionalProperties": False,
        "properties": {
            "interface_profile": {
                "type": "string",
                "const": INTERFACE_PROFILE,
            },
            "operation": {
                "type": "string",
                "enum": list(OPERATIONS),
            },
            "request_id": {"type": "string"},
            "created_at": {"type": "integer"},
            "expires_at": {"type": "integer"},
            "nonce": {"type": "string"},
            "execution_authorized": {
                "type": "boolean",
                "const": False,
            },
            "params": {
                "type": "object",
                "description": "Canonical operation-specific UAII params.",
            },
        },
    }

    paths: dict[str, Any] = {}
    for path, operation in REST_PATHS.items():
        paths[path] = {
            "post": {
                "operationId": operation,
                "description": (
                    "Transport mapping only. HTTP transport success does not "
                    "mean L28 validation, authorization, or settlement."
                ),
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": envelope_schema,
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": (
                            "Canonical UAII response. HTTP 200 is not settlement."
                        )
                    }
                },
            }
        }

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "L28 UAII Offline REST Mapping",
            "version": "0.1",
        },
        "servers": [],
        "paths": paths,
        "x-l28-interface-profile": INTERFACE_PROFILE,
        "x-l28-runtime-activated": False,
        "x-l28-network-activated": False,
        "x-l28-settlement-authorized": False,
    }
