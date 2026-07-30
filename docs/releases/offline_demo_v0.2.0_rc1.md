# Offline Demo v0.2.0-rc1 — Local Release Candidate Notes

- **Candidate:** `offline-demo-v0.2.0-rc1`
- **Source commit:** `76335edf4734bb5874fd20722233ea71a3f51eee`
- **Branch (local preparation):** `release-v0.2-offline-demo-rc`
- **Protocol version (unchanged):** `1.0.0` (from `PROTOCOL.md` / frozen v1.0.0)
- **Publication status:** local release candidate only — not a published release

## Product purpose

Provide a locally verifiable, script-friendly offline package of the existing
Isolated Agent Purchase Demo CLI: Agent A buys one verifiable SHA-256 service
from Agent B and receives a signed receipt. Disposable in-memory keys and
simulated no-value settlement only.

## Complete offline workflow

1. Agent A builds a deterministic service request.
2. Agent B issues a signed quote (non-monetary demo price; simulation markers).
3. Agent A signs a simulated payment approval (`simulation_only=true`).
4. Agent B returns SHA-256 of the canonical request input.
5. Agent B issues a Foundation 64/67 signed receipt binding request, quote,
   delivery, and identities.
6. Optional independent public verification (`--verify`).

## Supported CLI commands

```bash
export PYTHONPATH=.

python -m coin.isolated_agent_purchase_demo
python -m coin.isolated_agent_purchase_demo --json
python -m coin.isolated_agent_purchase_demo --json --pretty
python -m coin.isolated_agent_purchase_demo --json --verify
python -m coin.isolated_agent_purchase_demo --input "example" --json --verify
```

Use the repository-supported local Python environment already used for this
project (for example the existing `l28-env` interpreter). No new install is
required for this candidate.

## JSON schema / version, exit codes, stdout/stderr

Under `--json`:

| Field | Value |
|---|---|
| `schema` | `l28.isolated-agent-purchase-demo` |
| `schema_version` | `0.2` |
| `status` | `completed` or `error` |

| Exit code | Meaning |
|---|---|
| `0` | Success |
| `1` | Generation or verification failure |
| `2` | Invalid arguments |

- `--json` success: exactly one JSON document on stdout; stderr empty.
- `--json` failure: one error envelope on stdout; no private material or stack traces.
- Default (no `--json`): public summary JSON on stdout.

## Cryptographic and verification guarantees

- CanonUaii digests for request/quote/delivery bindings.
- Domain-separated Ed25519 signatures for quote, simulated approval, and delivery.
- Foundation 64/67 PureEd25519 signed receipt (`service_result_signed`) verified
  with public keys only.
- `--verify` requires both service-output and receipt-signature verification.

## Simulation-only limitations

Successful results preserve:

- `simulation_only=true`
- `real_payment_executed=false`
- `settlement_finalized=false`
- `transaction_submitted=false`
- `ledger_mutated=false`
- `persistent_state_created=false`
- `public_network_used=false`

Simulated approval is not payment, settlement, spend authorization, or finality.

## Disposable-key handling

- Ed25519 keys are generated in-process (or injected by tests via signer callables).
- Private keys remain process-local and are never printed, logged, serialized in
  results, or persisted by this demo.
- Only public keys, public key ids, signatures, digests, and identifiers are exposed.

## Installation / runtime prerequisites

Already supported by the repository; no new dependencies for this candidate:

- Local Python environment with repository `PYTHONPATH`
- Existing project dependency set used by signed-receipt demos (`cryptography`)
- No package install, network fetch, node, miner, or wallet required to run the demo

## Included artifacts and checksum verification

Artifacts listed in `release/offline-demo-v0.2.0-rc1/manifest.json` and
`release/offline-demo-v0.2.0-rc1/SHA256SUMS`:

1. `coin/isolated_agent_purchase_demo.py`
2. `docs/isolated_agent_purchase_demo_v0.1.md`
3. `docs/offline_public_demo_cli_v0.2.md`
4. `tests/test_isolated_agent_purchase_demo.py`
5. `tests/test_isolated_agent_purchase_demo_cli.py`

Verify from the repository root:

```bash
shasum -a 256 -c release/offline-demo-v0.2.0-rc1/SHA256SUMS
```

## Known limitations and deferred release work

- Local candidate only; no git tag, GitHub Release, or publication in this step.
- No console-script packaging that would require dependency/metadata changes.
- No hosted demo service, multi-agent runtime, or operator UI.
- Deferred: public artifact packaging / versioned release publication after
  separate authorization.

## Explicit exclusions

This candidate does **not** include or authorize:

- real funds or balances
- settlement finality
- wallets
- mining activation
- public networking
- ledger mutation
- hosted service
- deployment
- adapters
- production keys
- Foundation 79 or additional numbered scaffolding
