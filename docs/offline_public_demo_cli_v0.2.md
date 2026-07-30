# Offline Public Demo CLI v0.2

- **Status:** implemented (local simulation packaging only)
- **Baseline:** `b6f77291ee62e9edbd158c1713a68c60fdae3529` (demo v0.1 on main)
- **Branch:** `demo-v0.2-public-cli-json`
- **Module:** `coin/isolated_agent_purchase_demo.py`

Packages the existing Isolated Agent Purchase Demo for script-friendly local use.
Does not redesign protocol behavior and is not Foundation 79.

## 1. Run commands

```bash
export PYTHONPATH=.
PY=/Users/pjaydondup/.pyenv/versions/l28-env/bin/python

# Default summary JSON (human-friendly public fields)
$PY -m coin.isolated_agent_purchase_demo

# Stable machine-readable envelope
$PY -m coin.isolated_agent_purchase_demo --json

# Pretty-indented envelope
$PY -m coin.isolated_agent_purchase_demo --json --pretty

# Custom public input
$PY -m coin.isolated_agent_purchase_demo --json --input "hello"

# Generate and independently verify before success
$PY -m coin.isolated_agent_purchase_demo --json --verify
```

Callable API from v0.1 remains available:

```python
from coin.isolated_agent_purchase_demo import run_isolated_agent_purchase_demo
```

## 2. JSON envelope and exit codes

### Success (`--json`)

```json
{
  "schema": "l28.isolated-agent-purchase-demo",
  "schema_version": "0.2",
  "status": "completed",
  "result": { "...existing public demo result..." }
}
```

### Failure (`--json`)

```json
{
  "schema": "l28.isolated-agent-purchase-demo",
  "schema_version": "0.2",
  "status": "error",
  "error": {
    "code": "<stable_safe_code>",
    "message": "<safe_public_message>"
  }
}
```

| Exit code | Meaning |
|---|---|
| `0` | Success |
| `1` | Generation or verification failure |
| `2` | Invalid arguments |

Stdout under `--json` is exactly one JSON document (plus final newline).
Stderr is empty on success. Human/non-JSON error codes go to stderr.

## 3. Example safe summary (shortened)

Default (no `--json`) emits public summary fields only, for example:

```json
{
  "demo_profile": "l28-isolated-agent-purchase-demo/v0.1",
  "demo_completed": true,
  "simulation_only": true,
  "real_payment_executed": false,
  "request_digest": "<64-hex>",
  "quote_id": "<64-hex>",
  "output_digest": "<64-hex>",
  "receipt_id": "<64-hex>"
}
```

## 4. stdout versus stderr

| Mode | stdout | stderr |
|---|---|---|
| `--json` success | one completed envelope | empty |
| `--json` failure | one error envelope | empty |
| default success | one summary JSON object | empty |
| default failure | empty | stable error code |
| invalid args + `--json` | error envelope | empty |
| invalid args (no `--json`) | empty | `invalid_argument` |

No banners, debug text, Python repr, stack traces, or private material.

## 5. Disposable-key containment

- Keys are generated in-process (or injected by tests via signer callables).
- Private keys never appear in stdout, stderr, returned envelopes, or docs examples.
- Only public keys, public key ids, signatures, digests, and identifiers are exposed.

## 6. Simulation-only limitations

Always preserved in successful `result`:

- `simulation_only=true`
- `real_payment_executed=false`
- `settlement_finalized=false`
- `transaction_submitted=false`
- `ledger_mutated=false`
- `persistent_state_created=false`
- `public_network_used=false`

Simulated approval is not payment, settlement, spend authorization, or finality.

## 7. Implemented versus deferred

**Implemented:** `--json` / `--pretty` / `--verify` / `--input`; stable v0.2 envelope;
safe error codes; module entry point; focused CLI tests.

**Deferred:** console-script packaging that requires dependency changes; hosted
demo service; artifact release bundles; real settlement.

## 8. Changed paths and tests

| Path | Role |
|---|---|
| `coin/isolated_agent_purchase_demo.py` | CLI envelope + args (`main`, builders) |
| `tests/test_isolated_agent_purchase_demo_cli.py` | v0.2 CLI tests |
| `docs/offline_public_demo_cli_v0.2.md` | This record |

Existing v0.1 callable/summary behavior remains compatible.

## 9. Next release-directed milestone

Public artifact packaging / versioned release preparation for offline demo
consumers — not another numbered Foundation.
