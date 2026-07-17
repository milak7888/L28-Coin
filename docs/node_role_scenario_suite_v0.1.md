# L28 Offline Node-Role Scenario Suite v0.1

Status: public offline specification; non-activation

## 1. Purpose

This document specifies a deterministic, offline suite for exercising the
public L28 node-role lifecycle model.

The suite combines multiple caller-supplied Foundation 23 scenarios. Each
scenario is executed by the inert scenario runner, its generated transcript is
self-verified, and its accepted transitions and rejected reserved-state
requests are included in an aggregate coverage result.

The suite demonstrates that the public pure-data model can represent every
currently allowed lifecycle transition and reject every currently reserved
state.

It does not demonstrate that a runtime node, peer connection, listener,
network, ledger, miner, wallet, checkpoint, or deployment exists or is active.

## 2. Foundation relationship

The suite depends on the following public layers:

- Foundation 19 defines the Core and P2P role architecture and security
  boundaries.
- Foundation 20 verifies the public role profile offline.
- Foundation 21 supplies immutable in-memory lifecycle transitions.
- Foundation 22 verifies deterministic transition transcripts.
- Foundation 23 executes one inert scenario and self-verifies its transcript.
- Foundation 24 verifies a bounded collection of Foundation 23 scenarios and
  requires complete public transition and reserved-state rejection coverage.

Foundation 24 does not modify the behavior of Foundations 19 through 23.

## 3. Normative language

The words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, and
MAY are to be interpreted as normative requirements.

## 4. Versions and identifiers

The v0.1 identifiers are:

- suite: `l28-node-role-scenario-suite/v0.1`
- suite verifier: `l28-node-role-scenario-suite-verifier/v0.1`
- suite CLI: `l28-node-role-scenario-suite-cli/v0.1`
- suite report: `l28-node-role-scenario-suite-report/v0.1`
- suite verification profile:
  `l28-node-role-scenario-suite-verification/v0.1`
- scenario: `l28-node-role-scenario/v0.1`
- model: `l28-node-role-model/v0.1`
- transcript: `l28-node-role-transcript/v0.1`

An unsupported version MUST fail closed.

## 5. Roles

The supported role identifiers are exactly:

- `CoreL28Node`
- `L28P2PNode`

A conformant suite MUST contain successful scenarios for both roles.

The similarly named roles remain conceptually and structurally distinct. The
suite does not merge their responsibilities.

## 6. Input boundary

The core verifier accepts only an explicit UTF-8 JSON string or byte sequence.

It MUST NOT:

- discover suite files automatically;
- search directories;
- access the network;
- construct runtime nodes;
- open peer connections or listeners;
- read or mutate a ledger;
- activate checkpoints or canonical state;
- mine or issue L28;
- access wallets, keys, seeds, or signing services;
- start background threads or processes; or
- claim runtime evidence.

The command-line interface MAY read one explicit caller-supplied regular file.
The pure-data verifier performs no filesystem access.

## 7. Top-level JSON schema

The top-level value MUST be an object containing exactly these fields:

| Field | Type | Requirement |
| --- | --- | --- |
| `suite_version` | string | Exact v0.1 suite identifier |
| `scenario_version` | string | Exact Foundation 23 scenario identifier |
| `model_version` | string | Exact Foundation 21 model identifier |
| `transcript_version` | string | Exact Foundation 22 transcript identifier |
| `cases` | array | One through 64 case objects |

Missing fields, extra fields, or fields of the wrong type MUST fail closed.

JSON objects MUST NOT contain duplicate keys at any depth.

Non-finite numbers and invalid UTF-8 MUST be rejected.

The maximum encoded suite size is 1,048,576 bytes.

## 8. Case schema

Each case object MUST contain exactly:

| Field | Type | Requirement |
| --- | --- | --- |
| `case_id` | string | Unique bounded public identifier |
| `scenario` | object | Exact Foundation 23 scenario input |

The case identifier:

- MUST contain between 1 and 64 characters;
- MUST start with an ASCII letter or digit;
- MAY otherwise contain ASCII letters, digits, period, underscore, or hyphen;
- MUST be unique within the suite; and
- MUST NOT be interpreted as a filesystem path.

The effective identifier pattern is:

```text
^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$
```

## 9. Embedded scenario schema

Each `scenario` object is processed as a Foundation 23 scenario and therefore
contains exactly:

- `scenario_version`
- `model_version`
- `transcript_version`
- `role`
- `requested_states`

The scenario runner begins in `CREATED`, applies the bounded requested-state
sequence through the immutable Foundation 21 model, constructs a Foundation 22
transcript, and self-verifies that transcript.

Every suite case MUST produce:

- `ok` equal to true;
- code `scenario_valid`;
- final state `STOPPED`;
- a scenario commitment matching the canonical embedded scenario;
- transcript verification code `transcript_valid`; and
- the same role declared by the embedded scenario.

Any case failure causes the suite to fail closed.

## 10. Required transition coverage

Coverage is calculated only from steps where:

- `ok` is true; and
- the Foundation 21 result code is `transitioned`.

Each covered transition is represented as:

```text
PREVIOUS_STATE->REQUESTED_STATE
```

A conformant suite MUST cover all 11 currently allowed Core transitions and
all 8 currently allowed P2P transitions.

Repeated coverage is permitted but does not change the set or commitment.

Unknown or prohibited requests do not count as allowed-transition coverage.

## 11. Required reserved-state rejection coverage

The Core reserved states are:

- `CANONICAL_READY_RESERVED`
- `RUNNING_RESERVED`

The P2P reserved state is:

- `LISTENING_RESERVED`

A reserved state counts as covered only when a scenario step proves all of the
following:

- the request targets the reserved state for that role;
- `ok` is false;
- the result code is `reserved_state_unreachable`; and
- the resulting state is unchanged from the previous state.

A conformant suite MUST cover rejection of all three reserved states.

Reserved-state rejection evidence does not authorize future entry into those
states.

## 12. Deterministic canonicalization

The suite semantic commitment is:

```text
SHA-256(UTF-8(canonical JSON suite))
```

Canonical JSON uses:

- lexicographically sorted object keys;
- no insignificant whitespace;
- UTF-8 encoding;
- JSON array order preserved;
- non-ASCII text preserved; and
- non-finite values prohibited.

Semantically identical JSON formatting produces the same suite commitment.

A semantic change produces a different commitment.

Case order remains semantically significant because JSON array order is
preserved.

## 13. Immutable result

The suite result is immutable and includes:

- success status and stable code;
- case count and represented roles;
- suite SHA-256 commitment;
- covered and missing Core transitions;
- covered and missing P2P transitions;
- covered and missing Core reserved-state rejections;
- covered and missing P2P reserved-state rejections;
- immutable per-case results;
- completed checks;
- sanitized detail; and
- component versions.

Each case result includes:

- case identifier;
- scenario status and code;
- role and final state;
- request count;
- scenario and transcript commitments;
- covered transitions; and
- covered reserved-state rejections.

## 14. Stable verification codes

The stable core codes are:

| Code | Meaning |
| --- | --- |
| `suite_valid` | All requirements passed |
| `input_type_invalid` | Core input is not text or bytes |
| `suite_too_large` | Encoded suite exceeds the limit |
| `invalid_encoding` | Input is not valid UTF-8 |
| `invalid_json` | Input is not valid supported JSON |
| `duplicate_key` | A JSON object repeats a key |
| `schema_error` | Exact structural requirements failed |
| `version_unsupported` | A component version is unsupported |
| `case_count_invalid` | Case count is outside 1 through 64 |
| `case_id_invalid` | A case identifier is invalid |
| `duplicate_case_id` | A case identifier is repeated |
| `scenario_failed` | An embedded scenario failed verification |
| `role_coverage_incomplete` | Both roles are not represented |
| `transition_coverage_incomplete` | Allowed transitions are missing |
| `reserved_coverage_incomplete` | Reserved-state rejections are missing |
| `internal_error` | Sanitized verifier failure |

The CLI additionally reserves `usage_error` and `cli_internal_error`.

Details MUST NOT disclose exception text, private paths, secrets, or internal
configuration.

## 15. Deterministic CLI report

The CLI report includes the immutable verifier result plus:

- verification profile;
- report version;
- CLI version; and
- report identifier.

The report identifier is:

```text
SHA-256(
  UTF-8("l28-node-role-scenario-suite-report/v0.1") ||
  UTF-8(canonical JSON report body without report_id)
)
```

Pretty output changes presentation only. It MUST NOT change the logical report
or report identifier.

## 16. Command-line usage

Run from the L28-Coin repository root:

```console
python3 -m coin.node_role_scenario_suite_cli \
  --suite /explicit/path/to/scenario-suite.json
```

Pretty output:

```console
python3 -m coin.node_role_scenario_suite_cli \
  --suite /explicit/path/to/scenario-suite.json \
  --pretty
```

The CLI MUST NOT discover files automatically.

## 17. Path safety

The CLI accepts one explicit path and:

- rejects missing or unavailable files with sanitized output;
- rejects symbolic links;
- rejects directories and non-regular files;
- checks file size before payload parsing;
- confirms file identity after opening;
- bounds bytes read; and
- performs no writes.

## 18. Exit codes

| Exit | Meaning |
| --- | --- |
| `0` | Suite is conformant |
| `1` | Verification failed |
| `2` | Command usage failed |
| `3` | Internal verifier or CLI failure |

## 19. Security properties

The verifier fails closed on malformed, ambiguous, excessive, incomplete, or
unsupported data.

It provides no authority to:

- activate a reserved state;
- declare canonical readiness;
- start a node or network;
- listen for peers;
- read or mutate a ledger;
- issue or mine L28;
- access historical holdings or wallets; or
- deploy any component.

Suite output is simulation and conformance evidence only.

## 20. Acceptance criteria

A v0.1 implementation is acceptable only when:

1. input parsing is strict and bounded;
2. duplicate keys fail at every depth;
3. case identifiers are explicit, bounded, and unique;
4. every case passes Foundation 23 execution;
5. every generated transcript self-verifies through Foundation 22;
6. both public roles are represented;
7. all 11 Core transitions are covered;
8. all 8 P2P transitions are covered;
9. all three reserved states are proven unreachable;
10. commitments and reports are deterministic;
11. failures are sanitized;
12. the core performs no I/O or activation;
13. the CLI reads only one explicit regular file; and
14. the complete public test suite remains passing.
