# SPDX-License-Identifier: Apache-2.0
"""Offline Python client binding for canonical UAII v0.1.

This module creates no server, network transport, wallet, signer, broadcast
path, transaction submission path, settlement process, or persistent state.
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

sdk_implemented = True
package_published = False
runtime_activated = False
network_activated = False
signing_authorized = False
spend_authorized = False
settlement_authorized = False
transaction_submission_authorized = False


class PythonSdkError(Exception):
    """Python client-boundary failure, not Protocol success."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class UaiiPythonClient:
    """Thin in-process client over the canonical UAII request processor."""

    interface_profile = INTERFACE_PROFILE
    operations = OPERATIONS

    def __init__(self, context: Any = None) -> None:
        self._context = context

    def invoke(self, request: dict[str, Any]) -> dict[str, Any]:
        """Submit one complete canonical UAII envelope unchanged."""
        if not isinstance(request, dict):
            raise PythonSdkError("python_sdk_request_invalid")

        if tuple(request.keys()) != ENVELOPE_FIELDS:
            raise PythonSdkError("python_sdk_request_not_canonical")

        try:
            request_bytes = canon_uaii(request)
        except UaiiJsonError as exc:
            raise PythonSdkError("python_sdk_request_not_canonical") from exc

        return process_uaii_request(request_bytes, self._context)

    def invoke_operation(
        self,
        operation: str,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """Bind a convenience method to exactly one canonical operation."""
        if operation not in OPERATIONS:
            raise PythonSdkError("python_sdk_operation_unsupported")

        if not isinstance(request, dict):
            raise PythonSdkError("python_sdk_request_invalid")

        if request.get("operation") != operation:
            raise PythonSdkError("python_sdk_operation_mismatch")

        return self.invoke(request)

    def discover_capabilities(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.invoke_operation("discover_capabilities", request)

    def get_protocol_status(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.invoke_operation("get_protocol_status", request)

    def get_balance(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.invoke_operation("get_balance", request)

    def create_quote(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.invoke_operation("create_quote", request)

    def create_unsigned_payment_request(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        return self.invoke_operation("create_unsigned_payment_request", request)

    def validate_payment(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.invoke_operation("validate_payment", request)

    def get_payment_receipt(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.invoke_operation("get_payment_receipt", request)

    def verify_signed_receipt(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.invoke_operation("verify_signed_receipt", request)
