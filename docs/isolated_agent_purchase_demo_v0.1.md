# Isolated Agent Purchase Demo v0.1

- **Status:** implemented (local simulation only)
- **Baseline:** `dbf123c7073d3a32f9548a913a2010153329310b` (Foundation 78 on main)
- **Branch:** `demo-v0.1-isolated-agent-purchase`
- **Module:** `coin/isolated_agent_purchase_demo.py`

Foundation 78 permanently ends the numbered scaffolding chain. This demo is a
**release-directed product slice**, not Foundation 79.

## 1. Product goal

Prove one complete local workflow in a single process:

1. Agent A builds a deterministic service request.
2. Agent B issues a signed quote (UAII quote field shape; non-monetary demo price).
3. Agent A signs a simulated payment approval (`simulation_only=true`).
4. Agent B returns SHA-256 of the canonical request input.
5. Agent B issues a Foundation 64/67 signed receipt binding request, quote,
   delivery, and identities.
6. Public verification recomputes digests and checks signatures with public keys
   only.

## 2. End-to-end sequence

| Step | Actor | Artifact |
|---|---|---|
| Request | A | `request` + `request_digest` |
| Quote | B | UAII-shaped `quote` + `quote_id` + `quote_signature` |
| Simulated approval | A | `simulated_approval` + signature |
| Delivery | B | `delivery` with recomputable `output` / `output_digest` |
| Receipt | B | F64 `signed_receipt` (`service_result_signed`) |
| Verify | public | `verify_isolated_agent_purchase_demo_result` |

Service id: `l28.demo.sha256.v0.1`
Demo profile: `l28-isolated-agent-purchase-demo/v0.1`

## 3. Trust and threat boundaries

**In scope**

- Disposable in-memory Ed25519 keys
- CanonUaii digests (`coin.uaii_json.canon_uaii`)
- Foundation 64/67 receipt signing/verification
- Tamper detection on public artifacts

**Out of scope / excluded**

- Real funds, balances, wallets, mining
- Ledger mutation or transaction submission
- Public networking, deployment, hosted services
- Adapter or autonomous runtime activation
- Production keys, seed phrases, credentials, persistence
- Claiming simulated approval is payment, settlement, or finality

## 4. Artifact relationships

- Quote `service_params.request_digest` and `service_terms.request_digest` bind
  the request.
- Simulated approval binds `quote_id` and buyer identity with
  `simulation_only=true` and all spend/settlement flags false.
- Delivery binds `quote_id`, `request_digest`, and SHA-256 output.
- Signed receipt binds `request_id=request_digest`, `quote_id`,
  `service_result_id=digest(delivery)`, buyer/seller identities; signer is the
  seller (`service_result_signed`).

## 5. What is cryptographically verified

- Seller signature over domain-separated quote bytes
- Buyer signature over domain-separated simulated-approval bytes
- Seller signature over domain-separated delivery bytes
- Seller PureEd25519 signature over Foundation 66 signable receipt bytes
- Independent recomputation of request/quote/delivery digests and service output

## 6. Meaning of simulated payment

`simulated_approval` is an explicit local attestation that Agent A accepts the
quote **for demo purposes only**. It is **not**:

- a payment
- a spend authorization
- settlement finality
- a ledger entry
- a submitted transaction
- an authorization grant under Foundations 74–78

## 7. How to run locally

```bash
PYTHONPATH=. /Users/pjaydondup/.pyenv/versions/l28-env/bin/python \
  -m coin.isolated_agent_purchase_demo --input "hello"

# Full public JSON (still no private keys):
PYTHONPATH=. /Users/pjaydondup/.pyenv/versions/l28-env/bin/python \
  -m coin.isolated_agent_purchase_demo --input "hello" --json
```

Callable API:

```python
from coin.isolated_agent_purchase_demo import (
    run_isolated_agent_purchase_demo,
    verify_isolated_agent_purchase_demo_result,
)

result = run_isolated_agent_purchase_demo(request_input="hello")
verify_isolated_agent_purchase_demo_result(result)
```

## 8. Expected safe output

Success flags (exact):

- `demo_completed=true`
- `service_output_verified=true`
- `receipt_signature_verified=true`
- `simulation_only=true`
- `real_payment_executed=false`
- `settlement_finalized=false`
- `transaction_submitted=false`
- `ledger_mutated=false`
- `persistent_state_created=false`
- `public_network_used=false`

Default CLI prints a public summary (digests/ids/flags only). `--json` emits the
full public result object. Private keys never appear.

## 9. Tamper / failure examples

Verification fails closed when any of the following are altered:

- request input, quote amount/parties/service id
- quote/delivery/approval signatures
- output digest or delivery payload
- receipt signature
- buyer/seller public key binding
- mixed artifacts from different runs

## 10. Disposable-key handling

- Keys are generated in-process via `Ed25519PrivateKey.generate()` unless the
  caller injects signer callables + public keys for deterministic tests.
- Private keys remain local to the run function and are not returned.
- Only public keys, public key ids, signatures, digests, and identifiers are
  exposed.

## 11. Implemented versus deferred

**Implemented:** local A→B workflow; signed quote/approval/delivery; F64 receipt;
public verification; CLI entry point; focused tests.

**Deferred:** real settlement, wallets, networking, adapters, hosted inference,
production key management, multi-agent runtime orchestration.

## 12. Changed paths and symbols

| Path | Symbols / role |
|---|---|
| `coin/isolated_agent_purchase_demo.py` | `run_isolated_agent_purchase_demo`, `verify_isolated_agent_purchase_demo_result`, `main` |
| `tests/test_isolated_agent_purchase_demo.py` | Focused demo tests |
| `docs/isolated_agent_purchase_demo_v0.1.md` | This record |

No UAII schema, protocol-core, economics, ledger, wallet, mining, network,
adapter, or runtime files were modified.

## 13. Next release-directed milestone

Not another numbered Foundation. Candidate next product slice: a bounded
operator-facing demo packaging/UX layer that still remains simulation-only and
offline, or a disposable local multi-run transcript viewer for public demo
artifacts — without enabling real funds, networking, or ledger settlement.
