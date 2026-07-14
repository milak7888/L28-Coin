# L28 Offline Node-Role Conformance Verifier v0.1

**Foundation:** 20
**Status:** Offline verifier; non-activation
**Profile:** `l28-node-role-conformance/v0.1`
**Input profile:** `l28-core-p2p-security/v0.1`
**Report:** `l28-node-role-conformance-report/v0.1`

## Purpose

The L28 Offline Node-Role Conformance Verifier validates the public Foundation
19 Core/P2P security profile without constructing a node or discovering runtime
state.

It provides a deterministic JSON report for independent review, automation,
and machine-to-machine policy checks.

The verifier does not implement the node architecture. It verifies the public
specification that separates `CoreL28Node` policy responsibilities from
`L28P2PNode` transport responsibilities.

## Security boundary

Version 0.1:

- accepts only an explicitly supplied profile path;
- performs no automatic file discovery;
- follows no symbolic links;
- accepts only a bounded regular file;
- requires strict UTF-8 JSON;
- rejects duplicate keys at every JSON depth;
- rejects non-finite JSON numbers;
- validates schema, invariants, and a semantic commitment;
- emits sanitized stable failure details;
- performs no network access; and
- performs no ledger, mining, wallet, signing, bridge, or deployment action.

The verifier does not read historical ledgers, checkpoints, wallet files,
private keys, logs, environment files, peer credentials, or private
infrastructure.

## Verification scope

The verifier checks:

1. profile identity, status, and architecture version;
2. exact separation of `CoreL28Node` and `L28P2PNode`;
3. role-owned and role-prohibited capability structure;
4. core lifecycle state and transition integrity;
5. P2P lifecycle state and transition integrity;
6. reserved activation-state unreachability;
7. trust-boundary identity and control structure;
8. future message-frame requirements;
9. stable profile failure-code structure;
10. threat and observability policy structure;
11. Foundation 19 non-activation claims;
12. acceptance-check structure; and
13. the canonical semantic commitment for profile v0.1.

The semantic commitment is calculated from strict JSON parsed into a logical
value and reserialized using sorted keys and compact separators. Whitespace and
object-key order therefore do not affect conformance. Any logical content
change requires a new supported profile version and commitment.

## Command-line usage

Run from the L28-Coin repository root:

```console
python3 -m coin.node_role_conformance_cli \
  --profile docs/l28_core_p2p_security_profile_v0.1.json
```

For indented JSON output:

```console
python3 -m coin.node_role_conformance_cli \
  --profile docs/l28_core_p2p_security_profile_v0.1.json \
  --pretty
```

The compact and pretty forms represent the same logical report and therefore
contain the same `report_id`.

## Report format

Successful and failed verification reports contain exactly these fields:

- `checks`
- `cli_version`
- `code`
- `detail`
- `ok`
- `profile`
- `profile_sha256`
- `profile_version`
- `report_id`
- `report_version`

The report identifier is SHA-256 over a domain separator followed by the
canonical JSON encoding of every report field except `report_id`.

The raw profile SHA-256 binds the report to the supplied file bytes. The
semantic commitment independently binds conformance to the logical v0.1
profile, allowing harmless JSON formatting differences while rejecting logical
changes.

## Exit codes

| Exit | Meaning |
|---:|---|
| `0` | Profile conforms. |
| `1` | Verification failed closed. |
| `2` | Command usage was invalid. |
| `3` | A sanitized internal failure occurred. |

Callers must evaluate both the process exit code and the JSON `ok` and `code`
fields. A report must not be treated as conformant solely because it is valid
JSON.

## Stable result categories

The core verifier distinguishes:

- path and file-boundary failures;
- size, encoding, JSON, and duplicate-key failures;
- schema, version, status, and invariant failures;
- semantic-commitment mismatches; and
- sanitized internal failures.

Details are stable category strings. They do not include supplied paths, host
information, raw exception text, process identifiers, credentials, or private
artifact contents.

## Reserved states

The profile contains reserved names for future review:

- `CANONICAL_READY_RESERVED`
- `RUNNING_RESERVED`
- `LISTENING_RESERVED`

These states are intentionally unreachable in Foundation 20. Passing this
verifier does not authorize entering them and does not demonstrate that any
node or network exists.

## Interpretation boundaries

A conformant report proves only that the supplied public profile matches the
supported Foundation 19 v0.1 logical specification.

It does not prove:

- that `CoreL28Node` or `L28P2PNode` runtime classes exist;
- that a node, listener, peer session, or network is running;
- that a historical ledger or checkpoint is canonical or active;
- that mining, transaction admission, or persistence is operational;
- that a wallet balance is owned or spendable;
- that a bridge or wrapped asset is deployed;
- that private prototype code is production-ready; or
- that future runtime resource limits have been selected.

L28 remains the native blockless/DAG coin described by its public protocol.
This verifier does not alter L28 identity, supply, reward, historical evidence,
or protocol economics.

## Determinism and review

Given identical logical input and verifier version, report content and
`report_id` are deterministic. Pretty printing changes presentation only.

All verification failures are fail-closed. Unexpected exceptions are converted
to sanitized internal result codes rather than exposing exception text.

Foundation 20 is an offline conformance surface. Any runtime implementation,
network configuration, activation transition, or canonical-state decision
requires a separate milestone, explicit review, and new tests.
