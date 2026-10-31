# First Paid Text Summary v0.1

NON-PRODUCTION DISPOSABLE L28. This is a deterministic extractive service for
agents, not generative model inference, canonical issuance or production settlement.
No provider API, model installation, new dependency or external network is needed.

## Actual HTTP/JSON purchase

From this repository with the existing Python environment:

```sh
/Users/pjaydondup/.pyenv/versions/3.11.9/envs/l28-env/bin/python \
  -m coin.public_testnet_service_demo --role local-example \
  --service-id l28.service.text_summary/v0.1 \
  --input "Rare opener. L28 payments help agents. L28 payments buy summaries. L28 payments bind receipts."
```

The requester is the invoking process; the provider is a fresh child process.
Only the provider listens, on an ephemeral IPv4 127.0.0.1 port. No public/LAN
address is contacted. Both use existing disposable memory-only Ed25519 keys.
The command permits at most two concurrent processes, reserves cleanup time within
120 seconds, stops the child on failure and verifies listener closure on success.
The provider's deliberate replay rejection is printed to stderr; success is
determined by exit 0 and verified JSON output, not an empty stderr.

Reuse the identical command with different supplied text for a second independent
purchase. Each invocation uses fresh identities, payment and temporary ledger;
REUSE is interface reuse, not wallet persistence or a second spend of old funds.
No physical two-host session or certificate/pin exchange is needed for this slice.

## Machine contract and exact summary algorithm

Service: `l28.service.text_summary/v0.1`; price: integer 28; asset: `L28`.
Input: `{"text":"supplied text"}`, nonblank, valid UTF-8, at most 4096 Python
Unicode characters. Hash the exact input's UTF-8 bytes, without normalization or
trimming. Request IDs and signatures also bind that exact input and service ID.

Sentences are nonempty stripped spans matched by Python regular expression
`[^.!?\r\n]+(?:[.!?]+|(?=[\r\n]|$))`. Indices are zero-based in match order.
If no span exists (for example punctuation-only text), use the stripped text as
one sentence. This deliberately bounded segmentation is not linguistic parsing.
Tokenize each sentence using the existing `[A-Za-z0-9']+` expression, lowercase
tokens, and count token frequencies over all sentences. A sentence score is the
sum of its token frequencies divided by its token count, as an exact rational;
tokenless sentences score zero. Rank descending by score, breaking ties by the
original index. Choose at most three and restore original sentence order.
Join the selected sentence strings with one ASCII space. Non-ASCII text remains
intact; tokenless sentences retain source-order tie-breaking. Short inputs may
be returned in full. This contract proves deterministic extraction, not subjective
summary quality or factual accuracy of the supplied source.

Output fields:

```json
{"method":"extractive-term-frequency/v0.1","summary":"selected source sentences","source_sentence_indices":[1,2,3],"input_digest":"64 lowercase hexadecimal SHA-256 characters"}
```

The existing `l28.service.structured_text_analysis/v0.1` remains the default.
Neither its advertised catalog nor its output algorithm is replaced. Other
existing provider interfaces continue rejecting summary requests unless explicitly
configured to support that service; this slice adds no MCP/SDK feature or new route.

## Flow and cryptographic verification

Use the existing routes and versioned frames:

- `GET /v1/l28/public-testnet/services`: exact selected-service discovery.
- `GET /v1/l28/public-testnet/provider_hello`: disposable provider public identity.
- `POST /v1/l28/public-testnet/session`: signed request, signed quote, payment
  package, then signed result and receipt.

Discovery must match the requester's explicitly expected service, network and
configuration before payer creation. The signed request binds the full input,
service and parties. The signed quote binds the request, service, identities,
integer amount and expiry. Signed payment authorization binds the quote and exact
transaction ID. The existing transfer signature and canonical validator are
required before a disposable ledger is opened. Ledger application, acceptance and
replay checks precede service execution. The signed result binds request, quote,
payment, service, input digest and full output. The signed receipt binds that
result ID, request, quote, payment, parties and amount.

The result JSON includes `service_output` and `public_artifacts`: request, quote,
payment transaction, payment authorization, service result and receipt. It also
includes distinct requester/provider PIDs, child exit code, balance evidence and
listener closure. A requester or another local caller can verify the public bundle:

```python
from coin.public_testnet_service_demo import verify_purchase_artifacts

output = verify_purchase_artifacts(
    result["public_artifacts"], input_text=original_text,
    service_id="l28.service.text_summary/v0.1",
)
```

Verification recomputes the deterministic output and checks signatures/bindings;
it does not trust caller-provided success flags. Public receipt verification is
not proof of consensus finality or independently attested production settlement.
This local HTTP mode does not authenticate a real-world provider identity or
provide confidentiality against another process on the same machine. It is not
authorized for LAN/public exposure. The old public requester remains HTTPS-gated.

## Disposable accounting and safety

The existing fixture opens with payer/provider balances 100/0; exactly one payment
changes them to 72/28. Issued supply and mint height remain zero. No coinbase,
mining, historical import or canonical supply change occurs. Rejected payment
must open no ledger and perform no summary work. Accepted-payment replay rejects
without a second application or execution. Temporary ledgers are removed; no
private material is serialized. Do not publish supplied private input or public
artifact bundles unless separately authorized; verification evidence uses public
sample text only.

Protocol v1.0.0, protected economics/history, custody/F171 and production gates
are unchanged/BLOCKED. No EVD-001 integration or independent security audit is
claimed. Implementation remains uncommitted until separately authorized.

## Acceptance evidence

Verified on 2026-10-31 against:
- Core SHA-256: 9f49301f0cf43e483ba5adffa20b0508dc800797b434b92240060ca8dc033de8
- HTTP/CLI SHA-256: 02708016547d308fee6e67568386f6d0a29119396848372aa44627286f9a6323

54 unique focused cases are covered by passing results. Initial focused execution:
52 passed / 1 failed; the CLI artifact-ordering defect was diagnosed from
CanonUaii and fixed, then only that failed test was rerun (1 passed). A subsequent
absolute-deadline diagnostic demonstrated a slow response exceeding its active
budget; an absolute child-process watchdog corrected it. One new deadline test
plus the three affected startup/default/summary CLI checks passed (4 passed).
No passing full suite was repeated. Directly affected regressions ran once:
112 passed across external access, cross-AI interoperability, local-network and
limited-testnet services, durable service, disposable transfer and Protocol tests.

Final-code actual CLI evidence, not pytest-only evidence:
- Purchase: requester PID 9797, provider PID 9807, exit 0; input
  digest f029634275e18272928f6b883e53dff855d2bfd6f7d922085e48b5553b24e2fc.
  Payment f1135cf2bbbf73798d89e6f6484a7a3c06f82161b60aefc3e82f686b124be714;
  receipt 5aba849c83a6c65553431492166085354e0d5dfb5c3c91131eadea5abf3b9083.
- REUSE: requester PID 9816, provider PID 9826, exit 0; different input
  digest 73af3677acb7918f5229ffa7300cca3ec8ec4ced5d14c5295cdb82e1b11db9a1.
  Payment 255377ab2445fe6b1301666af8062d5527e28ada6ed2a879b2082da39402c920;
  receipt 3125445d5e302cf8a6afdc61ec4ec8f27b6444cdd0efe53fbcb7dc7b810c9d45.
  Summary: "Rain supplies water. Mulch retains water. Careful watering saves water."
- Each purchase independently verified its quote, transfer signature, summary and
  signed receipt; balances 100/0 -> 72/28, replay rejected, child exit 0 and listener
  closure verified. Payer/provider public identities and transaction IDs differ
  across the two fresh invocations. No issuance or canonical history was used.
- Five actual HTTP adversarial sessions returned 400: forged signature and wrong
  network -> canonical_validation_failed; wrong amount/recipient/quote ->
  payment_binding_invalid. Every temporary provider stopped and its listener closed.
- The final CLI public bundle below was separately reverified with public data
  only. Altered result/receipt/service/input/payment all rejected.
- Focused spies prove rejected payments open no ledger and execute no service;
  replay leaves accepted evidence unchanged. Failure tests verify child/pipe and
  listener cleanup, including incomplete startup and slow HTTP response.

One consolidated local diff/security review covered all ten paths and the reused
validator, payment acceptance, canonical bytes, signature domains and replay path.
The two concrete findings above were corrected and checked. No unresolved
Critical/High implementation finding remains in this bounded disposable scope.
NOT_INDEPENDENTLY_AUDITED=true. Residual limits: deterministic extraction is not
generative inference or semantic-quality assurance; receipts are not canonical
finality proofs; disposable fixed fixture timestamps are not production quote
expiry policy; loopback HTTP is not an authenticated/confidential public service.
No full physical-host, custody or production acceptance is implied.

ACCEPTANCE: PASS. Slice status: COMPLETE_PENDING_OPERATOR.
Operator authority: AUTHORIZE_L28_PAID_TEXT_SUMMARY_V0_1_ACCEPTANCE_AND_LOCAL_COMMIT.
Final read-only review reconciled every frozen criterion and the unchanged
source/test/evidence hashes; no new tests, execution or source changes were
required. Exactly one local ten-path implementation commit is authorized after
staged review. Earlier uncommitted statements describe the build phase.
PROJECT_STATE remains ACTIVE. STOP after commit/clean-worktree verification;
no merge/push/deployment, production activation or next slice.

### Public reproducible purchase record

Only public sample text, public identities, signatures and transaction/result
artifacts are retained here; no private signing material or ledger state.

<!-- L28_PUBLIC_PURCHASE_RECORD -->
```json
{
  "release_candidate": "l28-public-testnet-v0.1.0-rc1",
  "designation": "NON_PRODUCTION_DISPOSABLE_TESTNET",
  "verification_scope": "LOCAL_ONLY",
  "service_discovery_verified": true,
  "service_id": "l28.service.text_summary/v0.1",
  "network_id": "L28-DISPOSABLE-PUBLIC001",
  "quoted_amount": 28,
  "canonical_validation": "PASS",
  "payment_tx_id": "f1135cf2bbbf73798d89e6f6484a7a3c06f82161b60aefc3e82f686b124be714",
  "service_output": {
    "method": "extractive-term-frequency/v0.1",
    "summary": "L28 payments help agents. L28 payments buy summaries. L28 payments bind receipts.",
    "source_sentence_indices": [
      1,
      2,
      3
    ],
    "input_digest": "f029634275e18272928f6b883e53dff855d2bfd6f7d922085e48b5553b24e2fc"
  },
  "public_artifacts": {
    "request": {
      "profile": "l28-two-agent-service-transaction/v0.1",
      "message_type": "service_request",
      "service_id": "l28.service.text_summary/v0.1",
      "payer_identity": "l28disp_0cf42d7ed51c00d19eefb45fcdb03caa2e2c326e172cba127a858a1f64b6a456",
      "payer_public_key": "69e103841ecbfa7fe2180f0ca52b2aecda7454b8206f67e57ac6a1c8af5ba04c",
      "provider_identity": "l28disp_31bd3d060ba84d184fd892884c7f3e6fc60f7992ee22d8be8ce26065b41a819b",
      "input": {
        "text": "Rare opener. L28 payments help agents. L28 payments buy summaries. L28 payments bind receipts."
      },
      "created_at": 1700000000,
      "nonce": "request-001",
      "request_id": "e18370d03d1665b22e3c92e80b3f1435e175ce85693c80c64e4a85cce85b64fd",
      "signature": "feccdf90bacc20e9e9ce5ca90a5bc9b52fee7dc2993465bf0c5fabec0ae18678e3d2c955f673ff4958ae09df79317b03cbe9a69a13e9a4380fcbda79f323fc06"
    },
    "quote": {
      "profile": "l28-two-agent-service-transaction/v0.1",
      "message_type": "service_quote",
      "request_id": "e18370d03d1665b22e3c92e80b3f1435e175ce85693c80c64e4a85cce85b64fd",
      "service_id": "l28.service.text_summary/v0.1",
      "payer_identity": "l28disp_0cf42d7ed51c00d19eefb45fcdb03caa2e2c326e172cba127a858a1f64b6a456",
      "provider_identity": "l28disp_31bd3d060ba84d184fd892884c7f3e6fc60f7992ee22d8be8ce26065b41a819b",
      "provider_public_key": "3fe9ecfe7267b3ed238f95ecb40fe8df6659c69c6e95d81622d5c7b719b7b000",
      "amount": 28,
      "asset_id": "L28",
      "created_at": 1700000000,
      "expires_at": 1700000600,
      "nonce": "quote-001",
      "quote_id": "c82d947be60d0bd4c4bc982d48353aa388863bede48407ff58865d6b1e0f3358",
      "signature": "c5ee111b7fa7b6c85bc4e0f84e767a349faacf4bd70616bd20cc37a82f07dd37a2b6964e57ab22df3437d77439cdb2fb116d538625c1123e1bb61458ea31d70f"
    },
    "payment_tx": {
      "sender": "l28disp_0cf42d7ed51c00d19eefb45fcdb03caa2e2c326e172cba127a858a1f64b6a456",
      "receiver": "l28disp_31bd3d060ba84d184fd892884c7f3e6fc60f7992ee22d8be8ce26065b41a819b",
      "sender_public_key": "69e103841ecbfa7fe2180f0ca52b2aecda7454b8206f67e57ac6a1c8af5ba04c",
      "amount": 28,
      "timestamp": 1700000000,
      "type": "transfer",
      "network": "DISPOSABLE_OFFLINE",
      "profile": "l28-disposable-offline-transfer/v0.1",
      "nonce": 100,
      "signature": "6976c664a5a87b9c252548b0e8dad4051e3300eb3af1ec56c4daf932da8c68b497d6e4b8a0f134d18e8c3ee713bd6f56aff119444dacb4585ebd26746a8aec03",
      "id": "f1135cf2bbbf73798d89e6f6484a7a3c06f82161b60aefc3e82f686b124be714"
    },
    "payment_authorization": {
      "profile": "l28-two-agent-service-transaction/v0.1",
      "message_type": "payment_authorization",
      "request_id": "e18370d03d1665b22e3c92e80b3f1435e175ce85693c80c64e4a85cce85b64fd",
      "quote_id": "c82d947be60d0bd4c4bc982d48353aa388863bede48407ff58865d6b1e0f3358",
      "service_id": "l28.service.text_summary/v0.1",
      "payer_identity": "l28disp_0cf42d7ed51c00d19eefb45fcdb03caa2e2c326e172cba127a858a1f64b6a456",
      "payer_public_key": "69e103841ecbfa7fe2180f0ca52b2aecda7454b8206f67e57ac6a1c8af5ba04c",
      "provider_identity": "l28disp_31bd3d060ba84d184fd892884c7f3e6fc60f7992ee22d8be8ce26065b41a819b",
      "amount": 28,
      "asset_id": "L28",
      "payment_tx_id": "f1135cf2bbbf73798d89e6f6484a7a3c06f82161b60aefc3e82f686b124be714",
      "created_at": 1700000000,
      "nonce": "payment-auth-001",
      "authorization_id": "d0d54b08641a0e7d680a5b57abb936c5e4a907dcdc1e27b824541472468db254",
      "signature": "6f9e7c27606e3a6e3306ca1b8edc8fabde7caf4353476d32002670fee68e38925ec532bd679cc40cc65bb0de085ac4b050e6ccdad8a5c1ab43c55f4451d9ff09"
    },
    "service_result": {
      "profile": "l28-two-agent-service-transaction/v0.1",
      "message_type": "service_result",
      "request_id": "e18370d03d1665b22e3c92e80b3f1435e175ce85693c80c64e4a85cce85b64fd",
      "quote_id": "c82d947be60d0bd4c4bc982d48353aa388863bede48407ff58865d6b1e0f3358",
      "payment_tx_id": "f1135cf2bbbf73798d89e6f6484a7a3c06f82161b60aefc3e82f686b124be714",
      "service_id": "l28.service.text_summary/v0.1",
      "input_digest": "f029634275e18272928f6b883e53dff855d2bfd6f7d922085e48b5553b24e2fc",
      "output": {
        "method": "extractive-term-frequency/v0.1",
        "summary": "L28 payments help agents. L28 payments buy summaries. L28 payments bind receipts.",
        "source_sentence_indices": [
          1,
          2,
          3
        ],
        "input_digest": "f029634275e18272928f6b883e53dff855d2bfd6f7d922085e48b5553b24e2fc"
      },
      "provider_identity": "l28disp_31bd3d060ba84d184fd892884c7f3e6fc60f7992ee22d8be8ce26065b41a819b",
      "provider_public_key": "3fe9ecfe7267b3ed238f95ecb40fe8df6659c69c6e95d81622d5c7b719b7b000",
      "created_at": 1700000000,
      "service_result_id": "96b1ca955615d988e952e649fbe0a109b1f74d99718a8b03d304ed106be47a73",
      "signature": "10f8039db07571de763b8724a414f2422dd5130a52c2d1a5100780f83f5c0ce4e0b5c0d4a5b910389739922931cf06d0e5f48127feb97a5801314abd611ca90c"
    },
    "receipt": {
      "receipt_profile": "l28-two-agent-service-receipt/v0.1",
      "payer_identity": "l28disp_0cf42d7ed51c00d19eefb45fcdb03caa2e2c326e172cba127a858a1f64b6a456",
      "provider_identity": "l28disp_31bd3d060ba84d184fd892884c7f3e6fc60f7992ee22d8be8ce26065b41a819b",
      "request_id": "e18370d03d1665b22e3c92e80b3f1435e175ce85693c80c64e4a85cce85b64fd",
      "quote_id": "c82d947be60d0bd4c4bc982d48353aa388863bede48407ff58865d6b1e0f3358",
      "service_result_id": "96b1ca955615d988e952e649fbe0a109b1f74d99718a8b03d304ed106be47a73",
      "payment_tx_id": "f1135cf2bbbf73798d89e6f6484a7a3c06f82161b60aefc3e82f686b124be714",
      "amount": 28,
      "asset_id": "L28",
      "payment_verified": true,
      "service_executed": true,
      "provider_public_key": "3fe9ecfe7267b3ed238f95ecb40fe8df6659c69c6e95d81622d5c7b719b7b000",
      "created_at": 1700000000,
      "receipt_id": "5aba849c83a6c65553431492166085354e0d5dfb5c3c91131eadea5abf3b9083",
      "signature": "7bf1ca1290a0623407d7ca1347b75a3ef63f866db4247232d11db97be173558ef55df3d4b26bfd52a5008c71ba60b3099e5b9b3c8b2aece034f17057ca57c90c"
    }
  },
  "requester_pid": 9797,
  "provider_pid": 9807,
  "provider_exit": 0,
  "listener_closed": true,
  "requester_balance_before": 100,
  "requester_balance_after": 72,
  "provider_balance_before": 0,
  "provider_balance_after": 28,
  "payment_verified": true,
  "replay_rejected": true,
  "service_executed": true,
  "service_result_verified": true,
  "receipt_verified": true,
  "canonical_history_touched": false,
  "production_keys_used": false,
  "public_network_used": false,
  "external_https_exposure": false,
  "production_settlement": false,
  "bounded_provider_shutdown": true
}
```
<!-- /L28_PUBLIC_PURCHASE_RECORD -->

For offline reproduction, parse the JSON fenced block immediately following
L28_PUBLIC_PURCHASE_RECORD and call verify_purchase_artifacts with its
public_artifacts, the original sample input and the explicit summary service ID.
Preserve nested field order: CanonUaii is order-preserving; recursively sorting
the exported JSON would invalidate the original signed artifacts.
