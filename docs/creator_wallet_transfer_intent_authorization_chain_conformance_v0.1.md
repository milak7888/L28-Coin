# L28 Creator-Wallet Transfer-Intent Authorization Chain Conformance v0.1

**Status:** Offline conformance suite specification only; non-activation

## Purpose

Foundation 36 defines an end-to-end offline conformance suite for the complete
Foundations 31–35 creator-wallet authorization chain:

Foundation 31 commitments → Foundation 32 intent → Foundation 33 authorization →
Foundation 34 authorization evidence → Foundation 35 authorization-evidence
receipt.

The suite proves only that disposable synthetic fixtures pass the published
public verifiers and that targeted tampering fails closed with stable codes. It
does not create a new protocol layer, wrapper verifier, receipt format,
persistent state, wallet, ledger instruction, network message, or runtime
activation.

## Public identifiers

- Suite: `l28-creator-wallet-transfer-intent-authorization-chain-conformance/v0.1`
- Report profile:
  `l28-creator-wallet-transfer-intent-authorization-chain-conformance-report/v0.1`
- Bound layers:
  - Foundation 31: `l28-creator-wallet-control-evidence-bundle/v0.1`
  - Foundation 32: `l28-creator-wallet-transfer-intent/v0.1`
  - Foundation 33: `l28-creator-wallet-transfer-intent-authorization/v0.1`
  - Foundation 34:
    `l28-creator-wallet-transfer-intent-authorization-evidence/v0.1`
  - Foundation 35:
    `l28-creator-wallet-transfer-intent-authorization-evidence-receipt/v0.1`

## Conformance boundary

In scope:

- constructing disposable synthetic fixtures for the chain;
- invoking the authoritative Foundations 31–35 public verification APIs;
- asserting success-path digests, checks, and identifiers;
- applying a fixed tamper and malformed-input matrix;
- confirming repeated verification of identical bytes is deterministic.

Out of scope:

- duplicating or reimplementing Foundations 31–35 verifier logic;
- inventing a new wrapper protocol, evidence format, or receipt layer;
- loading real creator keys, wallets, seeds, or credentials;
- claiming live balances, spend permission, expiry enforcement, or replay
  prevention;
- reading or mutating ledgers;
- opening network connections;
- mining, deployment, discovery, or runtime activation;
- persistent suite state outside a single test process.

## Authoritative public APIs

The suite MUST call these public functions and MUST NOT copy their validation
rules into a parallel verifier:

1. `verify_creator_wallet_control_evidence_bundle_json`
2. `verify_creator_wallet_transfer_intent_json`
3. `verify_creator_wallet_transfer_intent_authorization_json`
4. `verify_creator_wallet_transfer_intent_authorization_evidence_json`
5. `verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json`

Optional explicit-path CLI helpers MAY be exercised for I/O boundary checks, but
core conformance decisions MUST come from the JSON/bytes public APIs above.

## Deterministic synthetic fixture construction

Fixtures MUST:

- use disposable ephemeral Ed25519 key material only;
- never use the real creator private key, seed, wallet file, or production
  credential;
- derive a fixed ephemeral suite keypair from a documented suite-local seed or
  constant test vector so fixture construction is repeatable;
- build Foundation 32–35 objects with exact required field order;
- bind both Foundation 31 commitment fields
  (`expected_control_bundle_sha256` /
  `control_bundle_sha256` and
  `expected_control_bundle_aggregate_commitment` /
  `control_bundle_aggregate_commitment`) consistently through the chain;
- recompute Foundation 33 `authorization_id`, Foundation 33 report identifier,
  Foundation 34 `evidence_sha256`, and Foundation 35 `receipt_id` using each
  layer’s published domain separation and canonical JSON rules;
- set `execution_authorized` to the JSON boolean `false` wherever that field
  exists.

Foundation 31 coverage MUST include either:

- a disposable synthetic Foundation 31 bundle verified through the public F31
  API whose aggregate commitment is then used by later layers; or
- disposable synthetic F31 commitment digests that are treated solely as the
  Foundation 31 binding surface and carried unchanged into F32–F35.

In both cases the suite MUST prove that tampering either commitment fails
closed at every subsequent layer that binds it.

## Success-path verification

A conforming suite MUST, in one process:

1. construct the synthetic chain fixtures;
2. verify Foundation 32 intent through the public F32 API when an intent object
   is material to authorization construction;
3. verify Foundation 33 authorization through the public F33 API with both
   Foundation 31 commitments;
4. verify Foundation 34 evidence through the public F34 API;
5. verify Foundation 35 receipt through the public F35 API;
6. assert each successful result has `ok == true` and `code == "ok"`;
7. assert Foundation 34 and Foundation 35 success checks match each layer’s
   published success-check tuple;
8. assert Foundation 35 `authorization_report_id` equals the verified Foundation
   34 embedded report `report_id`;
9. assert Foundation 35 `evidence_sha256`, `authorization_sha256`, and
   `authorization_id` equal the Foundation 34 verification result;
10. assert every observed `execution_authorized` value is exactly `false`.

When a disposable Foundation 31 bundle fixture is used, the suite MUST also
verify it through the public F31 API before consuming its commitments.

## Tamper matrix

The suite MUST include at least one failing case for each of the following
mutations applied to an otherwise valid fixture. Each case MUST fail closed
through the authoritative public API for the layer under test and MUST NOT
assert exception text.

Foundation 31 commitment coverage:

- mutate `control_bundle_sha256` / `expected_control_bundle_sha256`;
- mutate `control_bundle_aggregate_commitment` /
  `expected_control_bundle_aggregate_commitment`;
- introduce uppercase or non-hex commitment characters where lowercase hex is
  required.

Foundation 33 authorization / report binding:

- mutate authorization signature;
- mutate `authorization_id`;
- mutate embedded intent amount or intent identifier;
- mutate the Foundation 33 report body or `report_id` after recomputation.

Foundation 34 evidence binding / result:

- mutate embedded authorization after evidence construction;
- mutate `evidence_sha256`;
- mutate embedded report fields while keeping a forged `report_id`;
- reorder or add top-level evidence fields.

Foundation 35 receipt binding / ID:

- mutate either Foundation 31 commitment on the receipt while leaving embedded
  evidence unchanged;
- mutate `authorization_report_id`;
- mutate `evidence_sha256`, `authorization_sha256`, or `authorization_id`;
- mutate `checks`;
- set `execution_authorized` to `true`;
- mutate `receipt_id`;
- reorder top-level receipt fields.

## Malformed-input and policy checks

The suite MUST also cover, at the Foundation 33, 34, and 35 public JSON/bytes
APIs at minimum:

- unsupported input types;
- oversized inputs beyond each layer’s published maximum encoded size;
- invalid UTF-8;
- malformed JSON;
- duplicate keys at nested depth;
- non-finite JSON numbers;
- non-object top-level values;
- exact schema and field-order mismatches;
- stable sanitized failure codes with no raw exception, path, credential, or
  secret leakage.

## Deterministic repeated-run expectations

For one constructed fixture byte string:

- verifying the same bytes twice MUST return equal `ok`, `code`, checks, and
  commitment/identifier fields;
- compact and pretty JSON that parse to the same logical object MUST produce
  equal verification results for that layer;
- semantic mutation MUST change a digest, identifier, or cause failure.

Across separate suite process starts that use the same documented suite seed,
fixture construction MUST produce the same public digests and identifiers.

## Required test groups

A conforming implementation of this suite MUST provide all of the following
groups:

1. **Fixture determinism** — seeded synthetic construction is repeatable.
2. **Success-path chain** — F32/F33/F34/F35 public verification succeeds and
   bindings match.
3. **Foundation 31 commitment continuity** — both commitments are bound and
   each single-bit-class mutation fails closed.
4. **Foundation 33 tamper matrix** — authorization and report bindings fail
   closed.
5. **Foundation 34 tamper matrix** — evidence and result bindings fail closed.
6. **Foundation 35 tamper matrix** — receipt bindings and `receipt_id` fail
   closed.
7. **Malformed and size-limit matrix** — encoding, JSON, duplicate-key,
   non-finite, schema/order, and oversized inputs fail closed.
8. **Non-activation matrix** — every success and failure path keeps
   `execution_authorized == false` and never loads wallet/private-key material.
9. **Static hygiene** — suite/test modules do not import network, ledger,
   mining, wallet-loading, or private-key production paths beyond disposable
   ephemeral test-key generation.

## Pass / fail criteria

PASS only if every required test group succeeds.

FAIL if any required group fails, if any public API is bypassed by a local
reimplementation, if real creator secrets appear, if `execution_authorized` is
ever true, or if failure paths leak exception details, filesystem paths,
credentials, or secrets.

## Security boundary

The suite is offline and non-activating. It MUST NOT:

- load or unlock a wallet;
- access, import, reconstruct, or store private keys or seeds except disposable
  ephemeral test keys generated in memory;
- create production signatures for live assets;
- create, sign, broadcast, or execute a transfer;
- read or mutate a ledger;
- access a clock or replay database to claim current validity or uniqueness;
- open a network connection;
- activate mining, deployment, checkpoints, discovery, or runtime nodes.

## Non-authorization statement

A passing Foundation 36 conformance suite is offline verification evidence
about synthetic fixtures and public API behavior only. It is not permission to spend L28,
not an executable transaction, not a ledger command, not settlement finality,
and not runtime activation.
