# L28 Offline Node-Role Composition Manifest v0.1

## Status

This document specifies an offline inert node-role composition manifest for
L28.

The specification is planning-only and non-activating.

It does not construct a `CoreL28Node` or `L28P2PNode` runtime object. It does
not initialize a network, listener, peer session, ledger, checkpoint, miner,
wallet, signer, bridge, or deployment.

The verifier consumes explicit caller-supplied JSON and produces deterministic
pure-data verification evidence.

## Versions

- Manifest: `l28-node-role-composition-manifest/v0.1`
- Verifier: `l28-node-role-composition-manifest-verifier/v0.1`
- CLI: `l28-node-role-composition-manifest-cli/v0.1`
- Report: `l28-node-role-composition-manifest-report/v0.1`
- Verification profile:
  `l28-node-role-composition-manifest-verification/v0.1`
- Security profile: `l28-core-p2p-security/v0.1`
- Foundation 25 evidence:
  `l28-node-role-scenario-suite-evidence/v0.1`
- Foundation 25 report:
  `l28-node-role-scenario-suite-evidence-report/v0.1`

## Purpose

The manifest describes how the two public L28 node roles may be composed in a
future system while remaining inert.

It binds:

- exactly one Core component;
- exactly one P2P component;
- the initial `CREATED` lifecycle state;
- role-owned capabilities;
- role-prohibited capabilities;
- public trust boundaries and required controls;
- the canonical Foundation 19 security profile commitment;
- a verified Foundation 25 scenario-suite evidence object;
- the deterministic Foundation 25 evidence report; and
- the explicit absence of runtime configuration and authorization.

Successful verification is simulation evidence only. It is not evidence that
a runtime node, network, or ledger exists.

## Canonical security-profile commitment

The required security profile is:

```text
profile_version = l28-core-p2p-security/v0.1
sha256 = 61e787f9f665d76a704d5e6dca8bccc6a80bb3ed231ac741fb5b7497383b04f6
```

Both values must match exactly.

The production verifier does not discover or read the profile from the
filesystem. The public commitment and required declarations are compiled into
the offline verifier.

## Top-level schema

The top-level JSON value must be an object containing exactly these fields:

```json
{
  "manifest_version": "l28-node-role-composition-manifest/v0.1",
  "security_profile": {},
  "components": [],
  "trust_boundaries": [],
  "runtime_configuration": {},
  "evidence": {},
  "evidence_report": {}
}
```

Missing and additional fields are rejected.

Duplicate keys are rejected at every JSON depth. Non-finite numbers and
invalid UTF-8 are rejected.

The maximum encoded manifest size is 2 MiB.

## Security-profile object

`security_profile` contains exactly:

```json
{
  "profile_version": "l28-core-p2p-security/v0.1",
  "sha256": "61e787f9f665d76a704d5e6dca8bccc6a80bb3ed231ac741fb5b7497383b04f6"
}
```

The digest must be 64 lowercase hexadecimal characters and equal the
canonical public commitment.

## Component declarations

`components` must contain exactly two objects: one `CoreL28Node` declaration
and one `L28P2PNode` declaration.

Component order is content-bound but does not change the requirement that
both unique roles be present.

Every component contains exactly:

```json
{
  "component_id": "bounded-identifier",
  "role": "CoreL28Node",
  "initial_state": "CREATED",
  "trust": "native_policy_coordinator",
  "owns": [],
  "prohibited": []
}
```

### Component identifiers

A component identifier:

- is a non-empty string;
- contains at most 64 characters;
- begins with a lowercase ASCII letter;
- continues with lowercase ASCII letters, digits, `_`, or `-`; and
- is unique within the manifest.

### Initial lifecycle state

Every component must declare `CREATED` as its initial state.

Reserved states are not valid initial states:

- `CANONICAL_READY_RESERVED`
- `RUNNING_RESERVED`
- `LISTENING_RESERVED`

The manifest does not perform lifecycle transitions.

## Core role declaration

The Core role identity is exactly `CoreL28Node`.

Its trust classification is exactly:

```text
native_policy_coordinator
```

Its ordered `owns` array is exactly:

1. `lifecycle_policy`
2. `native_validation_coordination`
3. `issuance_readiness_policy`
4. `persistence_authorization`
5. `checkpoint_admission_policy`

Its ordered `prohibited` array is exactly:

1. `network_listen`
2. `network_connect`
3. `peer_discovery`
4. `participant_signing`
5. `wallet_custody`
6. `automatic_historical_state_discovery`
7. `automatic_canonical_designation`
8. `automatic_creator_reward_routing`

## P2P role declaration

The P2P role identity is exactly `L28P2PNode`.

Its trust classification is exactly:

```text
untrusted_transport_boundary
```

Its ordered `owns` array is exactly:

1. `bounded_frame_decoding`
2. `peer_session_policy`
3. `peer_replay_policy`
4. `candidate_forwarding`
5. `transport_pause_and_shutdown`

Its ordered `prohibited` array is exactly:

1. `native_ledger_mutation`
2. `mint_authorization`
3. `issued_supply_change`
4. `checkpoint_canonicalization`
5. `core_decision_override`
6. `participant_signing`
7. `wallet_custody`
8. `private_historical_state_loading`
9. `wrapped_asset_identity_substitution`

## Trust-boundary declarations

`trust_boundaries` must contain all four public Foundation 19 trust
boundaries exactly once.

Every boundary contains exactly:

```json
{
  "id": "peer_to_p2p",
  "input_trust": "untrusted",
  "required_controls": []
}
```

### `peer_to_p2p`

Input trust is `untrusted`.

Required controls, in order:

1. `predecode_size_limit`
2. `deterministic_decode`
3. `network_and_protocol_binding`
4. `peer_identity_evidence`
5. `nonce_and_replay_validation`
6. `timestamp_and_expiry_validation`

### `p2p_to_core`

Input trust is `normalized_but_untrusted`.

Required controls, in order:

1. `immutable_candidate_projection`
2. `native_transaction_validation`
3. `signature_verification`
4. `issuance_and_supply_invariants`
5. `checkpoint_policy_when_applicable`
6. `no_transport_decision_override`

### `core_to_persistence`

Input trust is `validated_candidate_only`.

Required controls, in order:

1. `atomic_commit_boundary`
2. `deterministic_identity`
3. `replay_state_consistency`
4. `failure_before_partial_mutation`
5. `auditable_result`

### `checkpoint_to_core`

Input trust is `untrusted_evidence`.

Required controls, in order:

1. `explicit_caller_supplied_input`
2. `duplicate_key_rejection`
3. `schema_and_version_validation`
4. `hash_size_and_count_commitments`
5. `parent_graph_and_supply_checks`
6. `enforced_provenance`
7. `separate_canonical_authorization`

## Runtime-configuration absence

`runtime_configuration` contains exactly:

```json
{
  "endpoints": [],
  "listeners": [],
  "peers": [],
  "credentials": [],
  "automatic_discovery": false,
  "activation_authorized": false
}
```

The four arrays must be empty arrays. Values such as `null`, an empty object,
or a non-empty array are rejected.

Both flags must be the JSON Boolean value `false`. Numeric zero is rejected.

The manifest cannot store endpoint configuration, listener configuration,
peer addresses, or credentials.

Automatic discovery is not supported.

## Foundation 25 evidence binding

`evidence` is a complete Foundation 25 scenario-suite evidence object. The
Foundation 25 verifier is run against its canonical logical JSON.

The evidence must successfully bind:

- the Foundation 24 scenario suite;
- the Foundation 24 deterministic report;
- all 11 required Core transitions;
- all 8 required P2P transitions;
- both Core reserved-state rejection attempts;
- the P2P reserved-state rejection attempt; and
- terminal `STOPPED` evidence for every scenario.

`evidence_report` is the complete deterministic Foundation 25 report for that
evidence object.

The report is rebuilt from the verified evidence result and compared for exact
logical equality. A stale, mutated, or unrelated report is rejected.

The successful composition result records:

- the Foundation 25 evidence SHA-256;
- the Foundation 25 evidence-report identifier; and
- the canonical composition-manifest SHA-256.

## Canonical manifest commitment

The logical manifest is serialized with:

- UTF-8 encoding;
- object keys sorted lexicographically;
- no insignificant whitespace;
- `,` and `:` separators;
- Unicode preserved without ASCII escaping; and
- non-finite numbers forbidden.

The manifest commitment is:

```text
SHA-256(canonical_manifest_json)
```

Semantically identical JSON formatting produces the same commitment. A
semantic mutation produces a different commitment.

Array order is content-bound.

## Verification result

The immutable result contains:

- `ok`
- `code`
- `manifest_sha256`
- `security_profile_sha256`
- `evidence_sha256`
- `evidence_report_id`
- `component_ids`
- `roles`
- `trust_boundary_ids`
- `checks`
- `detail`
- component version fields

Internal exceptions are converted to a sanitized `internal_error`. Raw
exception text is not exposed.

## Stable verification codes

- `manifest_valid`
- `input_type_invalid`
- `manifest_too_large`
- `invalid_encoding`
- `invalid_json`
- `duplicate_key`
- `schema_error`
- `version_unsupported`
- `security_profile_mismatch`
- `component_invalid`
- `capability_invalid`
- `trust_boundary_invalid`
- `runtime_configuration_present`
- `evidence_invalid`
- `evidence_report_invalid`
- `evidence_binding_invalid`
- `internal_error`

Unknown, incomplete, or malformed data fails closed.

## Deterministic CLI report

The CLI report includes:

- status and stable code;
- sanitized detail;
- profile and component versions;
- manifest, security-profile, and evidence commitments;
- Foundation 25 evidence-report identifier;
- component identifiers and role identities;
- trust-boundary identifiers;
- completed checks; and
- a domain-separated report identifier.

The report identifier is:

```text
SHA-256(
  UTF8("l28-node-role-composition-manifest-report/v0.1")
  || canonical_report_without_report_id
)
```

Pretty output changes presentation only. It does not change the logical report
or report identifier.

## Command-line usage

Run from the L28-Coin repository root:

```console
python3 -m coin.node_role_composition_manifest_cli \
  --manifest /explicit/path/to/composition-manifest.json
```

For indented output:

```console
python3 -m coin.node_role_composition_manifest_cli \
  --manifest /explicit/path/to/composition-manifest.json \
  --pretty
```

Only the explicitly supplied path is examined.

Directories and symbolic links are rejected. The file is size-checked before
payload verification, opened without following links when the platform
supports it, and checked for replacement or size changes during the read.

## Exit status

- `0`: verification passed
- `1`: verification failed
- `2`: command usage failed
- `3`: internal verifier or CLI failure

## Security and activation boundary

The core verifier has no filesystem API and accepts only caller-supplied data.

The CLI performs a bounded read of one explicit regular file. It performs no
automatic file discovery and no filesystem mutation.

Foundation 26 performs no runtime, network, ledger, checkpoint, mining,
wallet, signing, bridge, or deployment activation.

It does not:

- instantiate runtime node classes;
- create listeners or outbound connections;
- discover or connect to peers;
- initialize or mutate a ledger;
- load or designate canonical historical state;
- authorize checkpoint admission;
- mine or change issued supply;
- access wallet or signing material;
- route creator rewards;
- configure a bridge; or
- create a deployment.

The presence of role names, capabilities, or trust-boundary declarations is a
pure-data planning statement. It is not a runtime claim.

## Acceptance criteria

A successful implementation must demonstrate:

- exact top-level schema enforcement;
- duplicate-key and strict-JSON rejection;
- bounded input processing;
- exact Foundation 19 profile commitment;
- exactly one Core and one P2P role;
- unique bounded component identifiers;
- `CREATED` initial states;
- exact role-owned and prohibited capabilities;
- all four exact trust boundaries;
- empty runtime configuration;
- Foundation 25 evidence re-verification;
- Foundation 25 report recomputation and binding;
- deterministic manifest and report commitments;
- immutable results;
- sanitized failures;
- explicit-path CLI behavior;
- symlink and directory rejection;
- no automatic discovery; and
- no runtime activation.
