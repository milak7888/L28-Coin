// SPDX-License-Identifier: Apache-2.0

import {
  INTERFACE_PROFILE,
  OPERATIONS,
  UaiiTypeScriptSdk,
  network_activated,
  package_published,
  runtime_activated,
  settlement_authorized,
  signing_authorized,
  spend_authorized,
  transaction_submission_authorized,
  type UaiiEnvelope,
} from "../../sdk/typescript/uaii.mts";

const request: UaiiEnvelope = {
  interface_profile: INTERFACE_PROFILE,
  operation: "discover_capabilities",
  request_id:
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  created_at: 1699999000,
  expires_at: 1700000100,
  nonce: "foundation132",
  execution_authorized: false,
  params: {
    include_adapter_declarations: false,
  },
};

const sdk = new UaiiTypeScriptSdk();

console.log(
  JSON.stringify({
    interface_profile: sdk.interface_profile,
    operations: [...OPERATIONS],
    encoded: sdk.discover_capabilities(request),
    authority: {
      package_published,
      runtime_activated,
      network_activated,
      signing_authorized,
      spend_authorized,
      settlement_authorized,
      transaction_submission_authorized,
    },
  }),
);
