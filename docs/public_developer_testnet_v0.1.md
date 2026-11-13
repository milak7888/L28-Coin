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
