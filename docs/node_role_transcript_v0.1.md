# L28 Offline Node-Role Transcript Verification v0.1

Status: public offline verification specification.

## Purpose

Foundation 22 verifies completed, inert node-role transition transcripts.
It replays caller-supplied transition declarations through the immutable
Foundation 21 lifecycle model and compares every declared result with the
model result.

A conformant transcript proves data-model consistency only. It does not prove
that a runtime node existed or operated.

## Non-activation boundary

Verification does not:

- construct or start a CoreL28Node;
- construct or start an L28P2PNode;
- open a listener or connect to peers;
- discover transcript files automatically;
- read or mutate a ledger;
- activate a historical checkpoint;
- perform mining;
- access wallets, keys, or signing services;
- create background threads or processes; or
- deploy a bridge, node, or network.

The core verifier accepts explicit JSON text or bytes. The CLI reads exactly
one explicit caller-supplied regular file.

## Versions

- Transcript: `l28-node-role-transcript/v0.1`
- Model: `l28-node-role-model/v0.1`
- Verifier: `l28-node-role-transcript-verifier/v0.1`
- CLI: `l28-node-role-transcript-cli/v0.1`
- Report: `l28-node-role-transcript-report/v0.1`

## Roles

Supported role identities are exact and case-sensitive:

- `CoreL28Node`
- `L28P2PNode`

One transcript describes one role. Core and P2P transitions cannot be mixed.

## Top-level schema

A transcript is one JSON object containing exactly:

- `transcript_version`
- `model_version`
- `role`
- `initial_state`
- `transitions`
- `final_state`

Unknown, missing, or incorrectly typed fields fail closed.

`transcript_version` and `model_version` must equal the versions above.

`initial_state` must equal `CREATED`.

`transitions` must contain between 1 and 256 entries.

`final_state` must match replay and equal `STOPPED`.

## Transition entries

Each transition entry contains exactly:

- `sequence`
- `previous_state`
- `requested_state`
- `resulting_state`
- `ok`
- `code`

Sequence numbers begin at zero and are contiguous. Boolean values are not
accepted as sequence numbers.

`previous_state` must equal the model state before the request.

`requested_state` is replayed through the immutable role model.

`resulting_state`, `ok`, and `code` must exactly match the model result.

Model result codes are:

- `transitioned`
- `state_invalid`
- `reserved_state_unreachable`
- `transition_not_allowed`

## Successful transitions

An allowed transition records `ok` as true, `code` as `transitioned`, and the
new immutable state as `resulting_state`. The previous model object is not
modified.

## Rejected attempts

A rejected request may be recorded only when the rejection is exact. Its code
must match the model and its resulting state must remain unchanged. Later
entries continue from that unchanged state.

Recording a rejection proves only that the inert model rejects that request.
It does not authorize the requested capability.

## Reserved states

Core reserved states are:

- `CANONICAL_READY_RESERVED`
- `RUNNING_RESERVED`

The P2P reserved state is:

- `LISTENING_RESERVED`

A reserved-state request may appear only as a correctly recorded
`reserved_state_unreachable` result. A transcript claiming entry into a
reserved state fails verification.

## Terminal requirement

Version 0.1 verifies completed lifecycle transcripts. Replay must finish in
`STOPPED`, and the declared final state must also be `STOPPED`.

A transcript ending in any non-terminal state is incomplete and fails.

## Input safety

Maximum encoded input size is 262,144 bytes.

The verifier rejects invalid UTF-8, invalid JSON, duplicate keys at any depth,
non-finite JSON numbers, unsupported versions or roles, schema errors,
non-contiguous sequences, replay mismatches, excessive entries, and
non-terminal transcripts.

## Semantic commitment

The transcript SHA-256 is calculated from canonical logical JSON using UTF-8,
sorted object keys, standard compact separators, and no non-finite numbers.

Formatting-only changes produce the same commitment. Semantic changes produce
a different commitment.

## Deterministic report

The JSON report includes status, stable code, component versions, role,
initial and final states, transition count, transcript SHA-256, completed
checks, and a domain-separated report identifier.

The report identifier binds the logical report body. Pretty output changes
presentation only.

## Command-line usage

From the L28-Coin repository root:

```console
python3 -m coin.node_role_transcript_cli --transcript /explicit/path/transcript.json
```

Pretty output:

```console
python3 -m coin.node_role_transcript_cli --transcript /explicit/path/transcript.json --pretty
```

The CLI does not search for transcripts. It rejects symbolic links,
directories, missing files, non-regular files, and oversized files. Failure
reports do not reproduce caller paths or internal exception text.

## Exit codes

- `0`: transcript verified
- `1`: path or transcript verification failure
- `2`: command-line usage failure
- `3`: sanitized internal failure

## Minimal Core example

```json
{
  "transcript_version": "l28-node-role-transcript/v0.1",
  "model_version": "l28-node-role-model/v0.1",
  "role": "CoreL28Node",
  "initial_state": "CREATED",
  "transitions": [
    {
      "sequence": 0,
      "previous_state": "CREATED",
      "requested_state": "PAUSED",
      "resulting_state": "PAUSED",
      "ok": true,
      "code": "transitioned"
    },
    {
      "sequence": 1,
      "previous_state": "PAUSED",
      "requested_state": "STOPPED",
      "resulting_state": "STOPPED",
      "ok": true,
      "code": "transitioned"
    }
  ],
  "final_state": "STOPPED"
}
```

## Interpretation boundary

A valid result proves only that supplied declarations conform to the public
inert lifecycle model. It does not prove node execution, network activity,
ledger loading, historical continuity activation, mining, runtime approval, or
availability of reserved capabilities.

## Acceptance criteria

Foundation 22 is acceptable only when:

- both roles replay deterministically;
- malformed input fails closed;
- reserved states remain unreachable;
- rejected attempts cannot change state;
- every transcript starts at `CREATED` and finishes at `STOPPED`;
- transcript and report commitments are deterministic;
- the CLI reads only one explicit regular file;
- no runtime node is constructed;
- no network operation occurs; and
- no ledger, wallet, key, miner, bridge, or deployment is activated.
