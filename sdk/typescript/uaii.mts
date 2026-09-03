// SPDX-License-Identifier: Apache-2.0
/**
 * Offline TypeScript client binding for canonical UAII v0.1.
 *
 * No network transport, server, wallet, signing, broadcast, transaction
 * submission, settlement, deployment, or package publication.
 */

export const INTERFACE_PROFILE =
  "l28-universal-ai-access-interface/v0.1" as const;

export const OPERATIONS = [
  "discover_capabilities",
  "get_protocol_status",
  "get_balance",
  "create_quote",
  "create_unsigned_payment_request",
  "validate_payment",
  "get_payment_receipt",
  "verify_signed_receipt",
] as const;

export const ENVELOPE_FIELDS = [
  "interface_profile",
  "operation",
  "request_id",
  "created_at",
  "expires_at",
  "nonce",
  "execution_authorized",
  "params",
] as const;

export const sdk_implemented = true as const;
export const package_published = false as const;
export const runtime_activated = false as const;
export const network_activated = false as const;
export const signing_authorized = false as const;
export const spend_authorized = false as const;
export const settlement_authorized = false as const;
export const transaction_submission_authorized = false as const;

export type UaiiOperation = (typeof OPERATIONS)[number];

export type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | { [key: string]: JsonValue };

export interface UaiiEnvelope {
  interface_profile: typeof INTERFACE_PROFILE;
  operation: UaiiOperation;
  request_id: string;
  created_at: number;
  expires_at: number;
  nonce: string;
  execution_authorized: false;
  params: { [key: string]: JsonValue };
}

const SECRET_FIELD_NAMES = new Set([
  "api_key",
  "password",
  "private_key",
  "rpc_credentials",
  "rpc_password",
  "seed",
  "seed_phrase",
  "mnemonic",
  "token",
  "wallet_secret",
  "xprv",
]);

export class UaiiTypeScriptSdkError extends Error {
  readonly code: string;

  constructor(code: string) {
    super(code);
    this.name = "UaiiTypeScriptSdkError";
    this.code = code;
  }
}

function isPlainObject(
  value: unknown,
): value is Record<string, unknown> {
  if (
    value === null ||
    typeof value !== "object" ||
    Array.isArray(value)
  ) {
    return false;
  }

  const proto = Object.getPrototypeOf(value);
  return proto === Object.prototype || proto === null;
}

function assertJsonSafe(
  value: unknown,
  seen: Set<object> = new Set<object>(),
): void {
  if (
    value === null ||
    typeof value === "string" ||
    typeof value === "boolean"
  ) {
    return;
  }

  if (typeof value === "number") {
    if (!Number.isSafeInteger(value)) {
      throw new UaiiTypeScriptSdkError(
        "typescript_sdk_number_invalid",
      );
    }
    return;
  }

  if (typeof value !== "object") {
    throw new UaiiTypeScriptSdkError(
      "typescript_sdk_json_invalid",
    );
  }

  if (seen.has(value)) {
    throw new UaiiTypeScriptSdkError(
      "typescript_sdk_json_invalid",
    );
  }

  seen.add(value);

  if (Array.isArray(value)) {
    for (const item of value) {
      assertJsonSafe(item, seen);
    }
    seen.delete(value);
    return;
  }

  if (!isPlainObject(value)) {
    throw new UaiiTypeScriptSdkError(
      "typescript_sdk_json_invalid",
    );
  }

  if (Object.getOwnPropertySymbols(value).length !== 0) {
    throw new UaiiTypeScriptSdkError(
      "typescript_sdk_json_invalid",
    );
  }

  for (const [key, item] of Object.entries(value)) {
    if (SECRET_FIELD_NAMES.has(key.toLowerCase())) {
      throw new UaiiTypeScriptSdkError(
        "secret_material_forbidden",
      );
    }

    assertJsonSafe(item, seen);
  }

  seen.delete(value);
}

function assertCanonicalEnvelope(
  request: UaiiEnvelope,
  expectedOperation?: UaiiOperation,
): void {
  if (!isPlainObject(request)) {
    throw new UaiiTypeScriptSdkError(
      "typescript_sdk_request_invalid",
    );
  }

  const keys = Object.keys(request);

  if (
    keys.length !== ENVELOPE_FIELDS.length ||
    !keys.every(
      (key, index) => key === ENVELOPE_FIELDS[index],
    )
  ) {
    throw new UaiiTypeScriptSdkError(
      "typescript_sdk_request_not_canonical",
    );
  }

  if (request.interface_profile !== INTERFACE_PROFILE) {
    throw new UaiiTypeScriptSdkError(
      "interface_profile_unsupported",
    );
  }

  if (!OPERATIONS.includes(request.operation)) {
    throw new UaiiTypeScriptSdkError(
      "typescript_sdk_operation_unsupported",
    );
  }

  if (
    expectedOperation !== undefined &&
    request.operation !== expectedOperation
  ) {
    throw new UaiiTypeScriptSdkError(
      "typescript_sdk_operation_mismatch",
    );
  }

  if (request.execution_authorized !== false) {
    throw new UaiiTypeScriptSdkError(
      "execution_authorized_invalid",
    );
  }

  assertJsonSafe(request);
}

export function encodeUaiiRequest(
  request: UaiiEnvelope,
  expectedOperation?: UaiiOperation,
): string {
  assertCanonicalEnvelope(request, expectedOperation);

  const encoded = JSON.stringify(request);

  if (typeof encoded !== "string") {
    throw new UaiiTypeScriptSdkError(
      "typescript_sdk_json_invalid",
    );
  }

  return encoded;
}

export class UaiiTypeScriptSdk {
  readonly interface_profile = INTERFACE_PROFILE;
  readonly operations = OPERATIONS;

  invoke(request: UaiiEnvelope): string {
    return encodeUaiiRequest(request);
  }

  discover_capabilities(request: UaiiEnvelope): string {
    return encodeUaiiRequest(
      request,
      "discover_capabilities",
    );
  }

  get_protocol_status(request: UaiiEnvelope): string {
    return encodeUaiiRequest(
      request,
      "get_protocol_status",
    );
  }

  get_balance(request: UaiiEnvelope): string {
    return encodeUaiiRequest(request, "get_balance");
  }

  create_quote(request: UaiiEnvelope): string {
    return encodeUaiiRequest(request, "create_quote");
  }

  create_unsigned_payment_request(
    request: UaiiEnvelope,
  ): string {
    return encodeUaiiRequest(
      request,
      "create_unsigned_payment_request",
    );
  }

  validate_payment(request: UaiiEnvelope): string {
    return encodeUaiiRequest(
      request,
      "validate_payment",
    );
  }

  get_payment_receipt(request: UaiiEnvelope): string {
    return encodeUaiiRequest(
      request,
      "get_payment_receipt",
    );
  }

  verify_signed_receipt(request: UaiiEnvelope): string {
    return encodeUaiiRequest(
      request,
      "verify_signed_receipt",
    );
  }
}
