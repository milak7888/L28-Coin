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
| [test_vectors_v0.1.json](test_vectors_v0.1.json) | Deterministic offline unsigned digest vectors (non-operational) |
| [test_vectors_signed_v0.1.json](test_vectors_signed_v0.1.json) | Independently verified signed public fixtures (test-only; not settlement) |

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
