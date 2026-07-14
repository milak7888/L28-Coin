# L28 Offline Node-Role Scenario Runner v0.1

Status: public offline pure-data specification.

## Purpose

Foundation 23 defines a deterministic scenario runner for the inert L28 node
role models.

A caller supplies a role and a bounded sequence of requested states. The runner
starts from a new immutable `CREATED` model, derives every transition result,
constructs a Foundation 22 transcript, and independently verifies that
transcript.

The caller supplies requests only. The caller does not declare transition
outcomes.

## Non-activation boundary

Scenario execution does not:

- construct a runtime CoreL28Node;
- construct a runtime L28P2PNode;
- start a node or network listener;
- discover or connect to peers;
- read or mutate a ledger;
- load or activate a historical checkpoint;
- perform mining or issuance;
- access wallets, keys, or signing services;
- create background threads or processes;
- deploy a bridge or network; or
- claim that generated data represents runtime evidence.

The core accepts explicit JSON text or bytes. The CLI reads one explicit
caller-supplied regular file.

## Versions

- Scenario: `l28-node-role-scenario/v0.1`
- Model: `l28-node-role-model/v0.1`
- Transcript: `l28-node-role-transcript/v0.1`
- Runner: `l28-node-role-scenario-runner/v0.1`
- CLI: `l28-node-role-scenario-cli/v0.1`
- Report: `l28-node-role-scenario-report/v0.1`

## Supported roles

Role identity is exact and case-sensitive:

- `CoreL28Node`
- `L28P2PNode`

A scenario operates on one role only.

## Scenario schema

A scenario is one JSON object containing exactly:

- `scenario_version`
- `model_version`
- `transcript_version`
- `role`
- `requested_states`

Missing, extra, or incorrectly typed fields fail closed.

### scenario_version

Must equal `l28-node-role-scenario/v0.1`.

### model_version

Must equal `l28-node-role-model/v0.1`.

### transcript_version

Must equal `l28-node-role-transcript/v0.1`.

### role

Must equal `CoreL28Node` or `L28P2PNode`.

### requested_states

Must be a JSON array containing between 1 and 256 non-empty strings.

Each requested-state string is limited to 128 characters.

Requests are processed in array order.

## Initial state

The runner constructs a new inert role model for each scenario.

Public construction begins at `CREATED`. Callers cannot supply or restore an
alternative starting state.

## Derived outcomes

For each request, the runner records:

- zero-based sequence number;
- previous state;
- requested state;
- resulting state;
- success Boolean; and
- stable model code.

These values are derived from the Foundation 21 model. They are not accepted
from caller input.

## Rejected requests

Unknown, disallowed, and reserved-state requests are recorded using the actual
model rejection result.

A rejected request does not change state. Processing may continue from the
unchanged state.

Recording rejection does not authorize the requested capability.

## Reserved states

Core reserved states remain:

- `CANONICAL_READY_RESERVED`
- `RUNNING_RESERVED`

The P2P reserved state remains:

- `LISTENING_RESERVED`

A reserved request can produce only a `reserved_state_unreachable` result. The
runner cannot enter a reserved state.

## Terminal requirement

A conformant Foundation 23 scenario must finish in `STOPPED`.

A scenario finishing in any other state returns
`terminal_state_required` and does not pass.

This requirement ensures successful scenarios produce completed Foundation 22
transcripts.

## Transcript construction

The generated transcript contains:

- transcript and model versions;
- exact role identity;
- initial state `CREATED`;
- all derived transition entries; and
- the final derived state.

The transcript is serialized as canonical logical JSON and passed to the
Foundation 22 verifier.

A scenario cannot pass unless the generated transcript returns
`transcript_valid`.

## Input limits and failures

Maximum encoded scenario size is 131,072 bytes.

The runner rejects:

- unsupported input types;
- oversized input;
- invalid UTF-8;
- invalid JSON;
- duplicate JSON keys;
- non-finite JSON numbers;
- schema errors;
- unsupported versions;
- unsupported roles;
- empty request sequences;
- excessive request sequences;
- non-terminal results; and
- transcript self-verification failures.

Unexpected internal failures are sanitized.

## Deterministic commitments

The scenario SHA-256 commits to canonical logical scenario JSON.

The transcript SHA-256 is produced by Foundation 22 and commits to the derived
logical transcript.

Formatting-only changes produce the same commitments. Semantic changes produce
different commitments.

## Deterministic report

The CLI report includes:

- scenario status and stable code;
- component versions;
- role and final state;
- request count;
- scenario and transcript commitments;
- transcript verification code;
- generated transcript;
- derived steps;
- completed checks; and
- domain-separated report identifier.

Pretty output changes presentation only.

## Command-line usage

From the L28-Coin repository root:

```console
python3 -m coin.node_role_scenario_cli --scenario /explicit/path/scenario.json
```

Pretty output:

```console
python3 -m coin.node_role_scenario_cli --scenario /explicit/path/scenario.json --pretty
```

The CLI does not search for scenario files. It rejects symbolic links,
directories, missing files, non-regular files, and oversized files.

Caller paths and internal exception text are not emitted in failure reports.

## Exit codes

- `0`: scenario completed and its transcript verified
- `1`: path or scenario failure
- `2`: command-line usage failure
- `3`: sanitized internal failure

## Minimal Core scenario

```json
{
  "scenario_version": "l28-node-role-scenario/v0.1",
  "model_version": "l28-node-role-model/v0.1",
  "transcript_version": "l28-node-role-transcript/v0.1",
  "role": "CoreL28Node",
  "requested_states": [
    "PAUSED",
    "STOPPED"
  ]
}
```

The runner derives the transition results. The input does not contain `ok`,
`code`, `previous_state`, or `resulting_state` declarations.

## Interpretation boundary

A successful scenario proves that a requested-state sequence can be processed
by the public inert model and that its generated transcript conforms to
Foundation 22.

It does not prove:

- that a real node was constructed;
- that a node executed these transitions;
- that a network was contacted;
- that a ledger was loaded;
- that historical L28 continuity was activated;
- that mining or issuance occurred;
- that an operator approved activation; or
- that reserved capabilities are available.

Generated scenario data is simulation evidence only, not operational evidence.

## Acceptance criteria

Foundation 23 is acceptable only when:

- both role models execute deterministically;
- callers cannot declare transition outcomes;
- rejected requests cannot change state;
- reserved states remain unreachable;
- successful scenarios finish in `STOPPED`;
- generated transcripts self-verify through Foundation 22;
- logical commitments and reports are deterministic;
- the CLI reads only one explicit regular file;
- no runtime node is constructed;
- no network operation occurs; and
- no ledger, checkpoint, wallet, key, miner, bridge, or deployment is activated.
