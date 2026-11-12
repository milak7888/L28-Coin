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
