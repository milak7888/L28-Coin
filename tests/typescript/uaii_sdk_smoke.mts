// SPDX-License-Identifier: Apache-2.0

import {
  INTERFACE_PROFILE,
  OPERATIONS,
  UaiiTypeScriptSdk,
  UaiiTypeScriptSdkError,
  type UaiiEnvelope,
} from "../../sdk/typescript/uaii.mts";

function assert(
  condition: boolean,
  message: string,
): void {
  if (!condition) {
    throw new Error(message);
  }
}

function expectCode(
  fn: () => unknown,
  code: string,
): void {
  try {
    fn();
  } catch (error) {
    assert(
      error instanceof UaiiTypeScriptSdkError,
      "unexpected error type",
    );

    assert(
      error.code === code,
      `expected ${code}, got ${error.code}`,
    );

    return;
  }

  throw new Error(`expected error ${code}`);
}

const request: UaiiEnvelope = {
  interface_profile: INTERFACE_PROFILE,
  operation: "discover_capabilities",
  request_id:
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  created_at: 1699999000,
  expires_at: 1700000100,
  nonce: "foundation131",
  execution_authorized: false,
  params: {
    include_adapter_declarations: false,
  },
};

const sdk = new UaiiTypeScriptSdk();

assert(OPERATIONS.length === 8, "operation count");
assert(
  sdk.interface_profile === INTERFACE_PROFILE,
  "interface profile mismatch",
);

const encoded = sdk.discover_capabilities(request);

const expected =
  '{"interface_profile":"l28-universal-ai-access-interface/v0.1",' +
  '"operation":"discover_capabilities",' +
  '"request_id":"' +
  "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" +
  '","created_at":1699999000,' +
  '"expires_at":1700000100,' +
  '"nonce":"foundation131",' +
  '"execution_authorized":false,' +
  '"params":{"include_adapter_declarations":false}}';

assert(encoded === expected, "canonical serialization changed");

const { operation, ...rest } = request;

const reordered = {
  operation,
  ...rest,
} as UaiiEnvelope;

expectCode(
  () => sdk.invoke(reordered),
  "typescript_sdk_request_not_canonical",
);

expectCode(
  () => sdk.get_protocol_status(request),
  "typescript_sdk_operation_mismatch",
);

const secretRequest = {
  ...request,
  params: {
    password: "forbidden",
  },
} as UaiiEnvelope;

expectCode(
  () => sdk.invoke(secretRequest),
  "secret_material_forbidden",
);

const floatRequest = {
  ...request,
  params: {
    amount: 1.5,
  },
} as UaiiEnvelope;

expectCode(
  () => sdk.invoke(floatRequest),
  "typescript_sdk_number_invalid",
);

console.log("TYPESCRIPT_SDK_SMOKE=PASS");
