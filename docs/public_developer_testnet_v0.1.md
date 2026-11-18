# Public Developer Testnet v0.1

This rebuild passed one fresh disposable IPv4 loopback purchase using a
separate provider process, test mTLS edge, and MCP stdio requester. This
record does not authorize or establish external acceptance.

Provider entrypoint (for a separately authorized run):

```sh
python -B -m coin.public_testnet_service_demo --role developer-provider --port 28429 --state-dir "$FRESH_ABSOLUTE_STATE_DIR"
```

The provider listens on loopback. The independently approved HTTPS edge
must enroll exactly one client certificate, deny direct origin access, and
forward only GET service discovery, GET provider hello, and POST session
routes without rewriting signed bodies. Require a 64 KiB body cap,
one in-flight request, at most 12 requests, 10 seconds per request and
120 seconds including cleanup. Verify edge deadlines before external use.

```sh
python -B -m coin.two_agent_service_external_access_demo --runtime mcp \
  --developer-endpoint "$APPROVED_HTTPS_ORIGIN" \
  --expected-provider-key "$APPROVED_PROVIDER_PUBLIC_PIN" \
  --developer-client-cert "$TEST_CLIENT_CERT" --developer-client-key "$TEST_CLIENT_KEY"
```

Use the independently supplied provider pin. Invoke
`l28_purchase_developer_summary` with service ID
`l28.service.text_summary/v0.1` and one input. Reserve artifact capture
first. Verify one durable debit before work, then compare the signed
result, receipt and payment IDs. If outcome is uncertain, close ingress
and preserve state. Do not retry. Verify process and listener cleanup.

Sanitized projection of the preserved loopback record:

```json
{
  "result": "PUBLIC_DEVELOPER_TESTNET_LOOPBACK_PASS",
  "original_evidence_sha256": "98197b18aa001e57307ebb4f3c41428c377cc63baaa404f97496311ca325dbd8",
  "provider_source_digest": "0cf70d77f603674c2fe00cfe6d873456fa3b1cbc25a20cf3b714eca720238c8d",
  "mcp_sha256": "18ef62613b186827eaa32973d314f37b7e5aa9cdfa7fac8c2eb63db931bdff2f",
  "payment_tx_id": "5e66d4d6b68cb19153e9b522d86c5309aa99253ebfc5a85b5ef5a05b50d2dc4d",
  "receipt_id": "4410a084d6e5ebae97e370d23de84597f35259579c30ee8ea014c8842124da89",
  "balances": [
    [
      100,
      0
    ],
    [
      72,
      28
    ]
  ],
  "issued_supply": 0,
  "replay": "replay",
  "cleanup_verified": true
}
```

The test edge denied missing and unauthorized certificates. Wrong
provider pin, DNS stall and slow stream rejection were checked offline.
Replay was rejected by the canonical validator against read-only durable
state; no network replay was sent. The full 120-second timeout was not
exercised. External origin, ingress and cleanup ownership require separate
approval. No canonical currency or production signing was used.


### Private HTTPS requester opt-in

After separate activation approval, pass the same explicitly approved
certificate-valid HTTPS origin to both `--developer-endpoint` and
`--developer-private-origin`. Include the exact port when non-default.
The configured DNS hostname must resolve exclusively to Mac
100.66.229.15 on every request. Keep certificate and provider-pin options.
This mode cannot be combined with `--developer-loopback-test`. No private
origin is assumed or enrolled by this amendment.

### Configurable public-origin candidate

The edge can use one explicitly configured IPv4 listener, one DNS
hostname, one requester source IPv4, and one enrolled client certificate
leaf. Public listener activation requires separate host-specific approval.
The normal MCP HTTPS mode already verifies the server hostname, resolves
the origin to globally routable IPv4, and checks an independently supplied
provider signing-key pin. Use its existing command above without either
the private-origin or loopback-test option.

For one approved attempt, the same local owner captures a monotonic start
before launching the provider, passes that value to the edge, and controls
the provider, edge and requester lifetimes through the 120-second cutoff.

```sh
python -B -m coin.developer_mtls_edge --public-origin-single-purchase \
  --bind-ip "$APPROVED_LISTENER_IPV4" --bind-port "$APPROVED_LISTENER_PORT" \
  --hostname "$APPROVED_DNS_HOSTNAME" --source-ip "$APPROVED_REQUESTER_IPV4" \
  --server-cert "$EDGE_CERT" --server-key "$EDGE_KEY" --client-ca "$TEST_CLIENT_CA" \
  --client-sha256 "$APPROVED_CLIENT_LEAF_DER_SHA256" --attempt-start "$ATTEMPT_START"
```

The upstream is fixed to 127.0.0.1:28429. TLS SNI and HTTP Host must match
the configured origin. Client chain and leaf SHA-256 checks both apply.
Source admission uses the direct socket peer. Use end-to-end TLS and a
network path that preserves the approved requester source address. The
edge logs the admitted source and public leaf fingerprint to its
attempt log. Direct network restrictions and rate limits for a future
public deployment are a separate operator decision.

The edge reuses the discovery and hello GET routes and one session POST
route. It accepts one quote request and consumes the payment slot before
forwarding one payment package. Ingress closes by T+105; edge worker
cleanup is budgeted through T+115. The launch owner must complete
remaining process cleanup by T+120 and preserve evidence if delivery
is uncertain. No automatic payment retry or restart.

### Continuous disposable beta v0.1

The beta is an explicitly selected service lifecycle for two enrolled test
payers. It reuses the summary tool, HTTP/JSON routes, validator, mTLS and signed
result and receipt. The two 100-L28 opening balances exist only in the beta
database. Neither balance can be refilled through the service. Each payer can
make at most three 28-L28 purchases. Future allocation requires a separate
operator decision.

The same public JSON enrollment goes to the provider and edge. Its exact
fields are `profile` (`l28-public-disposable-beta/v0.1`),
`provider_public_key` (64 lowercase hexadecimal characters), and `clients`
(exactly two objects with `source_ipv4`, `client_sha256` and
`payer_public_key`). Leaf fingerprints are SHA-256 over DER. Public payer
keys, client leaf fingerprints and the provider key must be distinct within
their respective enrollment fields. Both clients can share an approved
egress IPv4, in which case they share its connection-rate budget. The pinned
provider and payer private keys are disposable unencrypted Ed25519 PKCS #8 PEM files. The
loopback origin credential is 32 random bytes shared only by the edge and
provider. Keep those files owner-only (0600), with the owning runtime's
state/marker directories at 0700. Use separate paths from any one-shot
evidence or canonical files. Pass file paths only and keep contents out of
the release and logs.

#### Approved-host procedure

These are the commands for a separately authorized activation. Verify the
Droplet ID, public IPv4 assignment, hostname, certificate SAN and lifetime,
source address of each independently operated requester, enrolled leaves,
independent provider pin, capacity, ownership, ingress and empty ports before
installation. Preserve the prior release, and keep the provider reachable
only on loopback. Allow TCP 8443 only from the enrolled requester IPv4s.
The edge binds an exact global IPv4, verifies the direct peer IPv4, mTLS
chain, exact leaf, SNI and Host, and rate limits by source before TLS.
A proxy must not replace the direct peer address. Use the existing host
supervisor and a dedicated unprivileged service account. Set `Restart=no`;
make the edge depend on the provider, and stop the edge before the provider.
Set a 15-second stop budget per process and bound or rotate logs.

Initialize the dedicated beta store once while ingress is closed. The parent
directory must exist with private permissions and the store path must be
absent. Then start the provider with the same invocation minus `--beta-init`
and require the readiness record to match the independently enrolled pin.

```sh
python -B -m coin.public_testnet_service_demo --role beta-provider \
  --port 28429 --state-dir "$BETA_STATE" --beta-config "$ENROLLMENT" \
  --beta-provider-key "$DISPOSABLE_PROVIDER_KEY" --beta-origin-token "$ORIGIN_CREDENTIAL" \
  --beta-init
```

```sh
python -B -m coin.developer_mtls_edge --public-beta \
  --bind-ip "$VERIFIED_PUBLIC_IPV4" --bind-port 8443 --hostname testnet.l28coin.com \
  --server-cert "$EDGE_CERT" --server-key "$EDGE_KEY" --client-ca "$CLIENT_CA" \
  --beta-config "$ENROLLMENT" --beta-origin-token "$ORIGIN_CREDENTIAL" \
  --beta-run-marker "$EDGE_RUN_MARKER"
```

Verify the intended IPv4 listeners and that the provider denies a direct
unauthenticated local request before opening ingress. On each independent
requester, use the existing MCP purchase-tool call with these launch options.
Use one MCP process per attempt. Use the issued client certificate and the
corresponding enrolled disposable payer key.

```sh
python -B -m coin.two_agent_service_external_access_demo --runtime mcp \
  --developer-endpoint https://testnet.l28coin.com:8443 \
  --expected-provider-key "$INDEPENDENT_PROVIDER_PIN" \
  --developer-client-cert "$CLIENT_CERT" --developer-client-key "$CLIENT_KEY" \
  --developer-beta-payer-key "$DISPOSABLE_PAYER_KEY"
```

The edge holds one session and one request at a time. The session starts
with provider hello, admits up to 12 connections from its source, and stops
admission by T+105 seconds. Each request is capped at 10 seconds, with an
8 KiB header bound and 64 KiB body bound. The requester retains a 120-second
total budget; the edge's active request and shutdown JOIN are bounded by the
session cutoff and a 15-second cleanup allowance. The connection bucket is
12 per minute per source with an initial burst of four. A session bound to
one enrolled leaf cannot be continued under the other. The provider rejects
a payer substitution and binds the signed quote to the current attempt.

With host-specific approval, make one purchase, close ingress, restart the
owned services against the same state, and make the second purchase. Capture
signed artifacts on the independent requester. Check the payment/audit and
artifact records, unchanged pin, balances 100/100/0 to 72/100/28 to 72/72/56,
zero issuance, and replay denial with the same database contents. Confirm
both listeners and every owned process stop. For rollback close ingress,
stop both processes and restore the prior release and rule configuration.
Preserve the latest beta state and evidence. A rollback never restores an
older version of that state. A later restart of the accepted beta is an
explicit operator action.

If forwarding fails after a payment may have reached the provider, the edge
closes ingress and leaves its durable run marker. A provider or edge crash
also leaves a run marker, and an incomplete committed payment prevents the
provider from reopening. Keep ingress closed and reconcile using the
requester's artifact and the committed ledger and audit rows. A complete
result can exist in the store even when the requester did not receive it.
A socket write does not prove requester receipt. Never retry the payment or
re-execute work. Preserve markers until the operator resolves the outcome.
There is no unattended recovery or automatic reversal.
