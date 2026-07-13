# L28 M2M Protocol Documentation Index

**Document:** L28 M2M Protocol v0.1 documentation index
**Status:** Specification (documentation only)
**Normative subordination:** This M2M layer is subordinate to [L28 Protocol v1.0.0](../../PROTOCOL.md). Where any M2M rule conflicts with L28 Protocol v1.0.0, L28 Protocol v1.0.0 prevails.

## Purpose

L28 M2M Protocol v0.1 specifies a deterministic coordination layer through which two machines can exchange an L28-denominated service request and payment evidence.

The initial reference case is:

1. A requesting machine asks a provider machine to perform a service.
2. The provider returns a signed quote.
3. The requester authorizes payment.
4. Settlement occurs through the existing L28 protocol.
5. The provider returns a signed service-completion receipt.

M2M v0.1 is a coordination and evidence-exchange layer. It is not a second ledger, consensus system, wallet, custody service, escrow system, or independent source of settlement truth.

## Document set

| Document | Role |
|---|---|
| [protocol_v0.1.md](protocol_v0.1.md) | Normative protocol purpose, message flow, amount rules, and settlement boundary |
| [message_schema_v0.1.md](message_schema_v0.1.md) | Common signed envelope and per-message payload schemas |
| [state_machine.md](state_machine.md) | Deterministic transaction states and permitted transitions |
| [security_model.md](security_model.md) | Identity, signature, replay, privacy, and settlement-verification boundaries |
| [interoperability_profile_v0.1.md](interoperability_profile_v0.1.md) | M2M canonical JSON, digests, Ed25519 suite, identity binding, verify-only runtime |
| [transcript_validation_v0.1.md](transcript_validation_v0.1.md) | Offline ordered exchange transcript validation (Foundation 6) |
| [conformance_cli_v0.1.md](conformance_cli_v0.1.md) | Offline conformance CLI and deterministic report (Foundation 7) |
| [replay_registry_v0.1.md](replay_registry_v0.1.md) | Offline local replay/idempotency registry (Foundation 8) |
| [admission_cli_v0.1.md](admission_cli_v0.1.md) | Offline CLI replay admission gate and admission report (Foundation 9) |
| [registry_audit_v0.1.md](registry_audit_v0.1.md) | Offline read-only replay registry audit and integrity report (Foundation 10) |
| [release_notes_v0.1.md](release_notes_v0.1.md) | L28 M2M v0.1.0 release candidate notes (Foundation 11) |
| [compatibility_policy_v0.1.md](compatibility_policy_v0.1.md) | Frozen public compatibility policy for v0.1.0 (Foundation 11) |
| [release_manifest_v0.1.json](release_manifest_v0.1.json) | Deterministic machine-verifiable release manifest (Foundation 11) |
| [test_vectors_v0.1.json](test_vectors_v0.1.json) | Deterministic offline unsigned digest vectors (non-operational) |
| [test_vectors_signed_v0.1.json](test_vectors_signed_v0.1.json) | Independently verified signed public fixtures (test-only; not settlement) |
| [test_vectors_transcript_v0.1.json](test_vectors_transcript_v0.1.json) | Independently verified signed transcript fixtures (test-only; not settlement) |
| [test_vectors_report_v0.1.json](test_vectors_report_v0.1.json) | Deterministic conformance-report fixtures (test-only; not settlement) |
| [test_vectors_replay_v0.1.json](test_vectors_replay_v0.1.json) | Replay/idempotency operation sequences (test-only; not settlement) |
| [test_vectors_admission_v0.1.json](test_vectors_admission_v0.1.json) | CLI replay admission operation sequences (test-only; not settlement) |
| [test_vectors_registry_audit_v0.1.json](test_vectors_registry_audit_v0.1.json) | Replay registry audit scenarios (test-only; not settlement) |

## Normative language

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted as described in RFC 2119 and RFC 8174 when, and only when, they appear in uppercase as shown here.

Text marked as explanatory or non-normative does not create protocol requirements.

## Scope

In scope for v0.1:

- Deterministic machine-to-machine message types for service request, quote, payment authorization, settlement reference, service receipt, and failure notice
- A common signed envelope for M2M messages
- A deterministic state machine for an M2M transaction
- Security rules that keep settlement truth in L28 Protocol v1.0.0
- Explicit identification of unresolved L28 primitive dependencies

## Non-goals

M2M Protocol v0.1 MUST NOT:

- Alter L28 Protocol v1.0.0 issuance, emission, treasury, circulation, or hard-cap rules
- Create a second ledger, consensus height source, or settlement finality rule
- Operate as a wallet, custody service, escrow, arbitration, refund, or chargeback system
- Claim live public-network availability or that a former hosted L28 server is online
- Enable or imply autonomous spending merely by defining coordination messages
- Invent a key format, address format, signature algorithm, hash algorithm, denomination subunit, finality rule, or timestamp representation when L28 Protocol v1.0.0 already defines one
- Invent such a primitive merely to appear complete when L28 Protocol v1.0.0 does not define it

Refunds, escrow, arbitration, and chargebacks are outside v0.1 unless already supported by L28 Protocol v1.0.0. L28 Protocol v1.0.0 does not define those mechanisms; therefore M2M v0.1 does not provide them.

## Relationship to L28 Protocol v1.0.0

- L28 remains the sole issuance and settlement authority.
- Coinbase remains the only issuance mechanism.
- Non-coinbase value movement remains subject to L28 transfer validation.
- M2M messages MAY reference L28 settlement records; they MUST NOT substitute for them.
- The blockless L28 architecture and frozen economic invariants are preserved unchanged by this documentation milestone.

## Implementation status

These documents specify the M2M coordination layer. They do not start services, wallets, miners, or networks, and do not assert that an always-on public L28 network is currently operating.

Foundation 5 provides a verify-only Ed25519 envelope verifier in `coin/m2m_verifier.py` with declared dependency `cryptography==49.0.0` (`requirements-m2m.txt`). The runtime verifies signatures only: it does not generate keys, sign messages, or store private material. Signature validity is not L28 settlement finality or service completion. Unsigned Foundation 4 digest vectors remain non-operational.

Foundation 6 provides offline ordered transcript validation in `coin/m2m_transcript_validator.py`. It verifies already-signed envelope sequences against chain, role, state-machine, and citation rules. It does not sign, spend, query a ledger, persist replay state, or claim settlement finality.

Foundation 7 provides an offline conformance CLI in `coin/m2m_conformance_cli.py` that reads one explicitly selected transcript (file or stdin) and emits one deterministic JSON report to stdout. It does not write report files, scan directories, sign, or claim settlement finality.

Foundation 8 provides a local offline replay/idempotency registry in `coin/m2m_replay_registry.py` (explicit path, hash-only SQLite). It is not an L28 ledger, consensus system, wallet, or settlement authority.

Foundation 9 optionally integrates Foundation 8 into the Foundation 7 CLI via explicit registry flags, emitting a deterministic admission report after verify-before-registry ordering. Without registry flags, Foundation 7 stdout bytes and exit codes remain unchanged.

Foundation 10 provides a strictly read-only replay-registry auditor in `coin/m2m_registry_audit.py` and `coin/m2m_registry_audit_cli.py`. It inspects existing registries without creating, modifying, repairing, or admitting state.

Foundation 11 freezes the L28 M2M v0.1.0 public surface on a release-candidate branch with manifest status `frozen`. It publishes `release_manifest_v0.1.json` with SHA-256 hashes of the complete tracked surface (excluding only the manifest file itself), `compatibility_policy_v0.1.md`, and `release_notes_v0.1.md`. Intended tag after merge: `l28-m2m-v0.1.0` (not created by this milestone). Foundation 11 does not change runtime behavior, normative protocol text (other than this index), vectors, CI, or dependencies.
