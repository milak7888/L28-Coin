# L28 Machine-to-Machine Transaction Protocol Specification v0.1

**Document:** L28 M2M Protocol v0.1
**Status:** Specification (documentation only)
**Normative subordination:** This document is subordinate to [L28 Protocol v1.0.0](../../PROTOCOL.md). If any requirement here conflicts with L28 Protocol v1.0.0, L28 Protocol v1.0.0 prevails.

## 1. Introduction

### 1.1 Purpose

L28 M2M Protocol v0.1 defines a deterministic coordination layer through which two machines exchange an L28-denominated service request and payment evidence.

Settlement truth remains exclusively in L28 Protocol v1.0.0. M2M messages coordinate intent, authorization, settlement citation, and completion assertions. They do not create value, finalize transfers, reverse settlements, or replace ledger validation.

### 1.2 Normative language

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted as described in RFC 2119 and RFC 8174 when, and only when, they appear in uppercase as shown here.

Sections labeled explanatory or non-normative do not create requirements.

### 1.3 Audience

This specification is intended for machines, implementers, and validators. It is not an investment document and MUST NOT be read as evidence of market value, live network availability, or autonomous spending capability.

### 1.4 Reference case (explanatory)

A requesting machine asks a provider machine to perform a service. The provider returns a signed quote. The requester authorizes payment. Settlement occurs through the existing L28 protocol. The provider returns a signed service-completion receipt.

## 2. Design invariants

M2M Protocol v0.1 MUST preserve all of the following:

- L28 Protocol v1.0.0 remains frozen and authoritative for issuance and settlement.
- The L28 architecture remains blockless as defined by the existing public repository boundary.
- The hard cap of 28,000,000 L28 MUST NOT be altered by any M2M rule.
- The emission ceiling of 11,130,000 L28 MUST NOT be altered by any M2M rule.
- The historically mined amount of 2,824,584 L28 MUST NOT be altered by any M2M rule.
- The locked treasury amount of 500,000 L28 MUST NOT be altered by any M2M rule.
- The circulating snapshot of 2,324,584 L28 MUST NOT be altered by any M2M rule.

M2M Protocol v0.1 MUST NOT become:

- a second ledger;
- a consensus system or canonical-height source;
- a wallet or custody service;
- an escrow system;
- an independent source of settlement truth.

## 3. Actors and roles

An M2M transaction involves exactly two coordination roles:

- **Requester:** the machine that requests a service and, when proceeding, authorizes payment.
- **Provider:** the machine that quotes, optionally performs the service, and asserts completion.

Cryptographic machine identity is defined in [security_model.md](security_model.md). A public key or L28 identity reference identifies a machine for coordination purposes. It is not proof of a human or legal identity.

## 4. Evidence classes

Implementations MUST distinguish three evidence classes:

1. **M2M coordination evidence**
   Signed M2M messages that record request, quote, authorization, settlement citation, receipt, or failure notice.

2. **L28 settlement evidence**
   An existing L28 settlement record accepted under L28 Protocol v1.0.0 validation rules. Only this class moves or creates L28 value.

3. **Service-delivery evidence**
   A provider's signed `service_receipt` asserting completion. This is proof of the provider's completion assertion, not independent proof that the service result is objectively correct.

## 5. Core message flow

### 5.1 Normative message types

M2M Protocol v0.1 defines exactly these message types:

| Message type | Purpose |
|---|---|
| `service_request` | Requester asks provider to perform a named service under stated constraints |
| `service_quote` | Provider offers terms, amount, and expiration for the requested service |
| `payment_authorization` | Requester authorizes payment against a specific quote |
| `settlement_reference` | Party cites an existing L28 settlement record for the authorized amount |
| `service_receipt` | Provider asserts service completion for a settled transaction |
| `failure_notice` | Party reports a non-settlement failure or rejection condition |

All messages MUST use the common signed envelope defined in [message_schema_v0.1.md](message_schema_v0.1.md).

### 5.2 Happy-path sequence

Unless a permitted rejection, expiration, cancellation, or failure transition occurs, the normative happy path is:

```
service_request
  -> service_quote
  -> payment_authorization
  -> settlement_reference
  -> service_receipt
```

Corresponding state progression is defined in [state_machine.md](state_machine.md):

```
requested -> quoted -> authorized -> settled -> completed
```

### 5.3 Settlement boundary rules

The following rules are normative:

- `payment_authorization` is NOT settlement. It is an authorization to attempt settlement through L28. It MUST NOT be treated as proof that L28 value moved.
- `settlement_reference` MUST point to an existing L28 settlement record. The cited record MUST be verified against the existing L28 source of truth before an M2M transaction may enter `settled`.
- `service_receipt` is proof of a provider's completion assertion. It MUST NOT be treated as independent objective proof that the service result is correct.
- `failure_notice` does NOT reverse an L28 settlement. If L28 settlement already occurred, any remediation remains outside M2M v0.1 unless already supported by L28 Protocol v1.0.0.
- Refunds, escrow, arbitration, and chargebacks are outside M2M v0.1. L28 Protocol v1.0.0 does not define those mechanisms; M2M MUST NOT invent them.

### 5.4 Who may send which message

| Message type | Allowed sender role |
|---|---|
| `service_request` | Requester |
| `service_quote` | Provider |
| `payment_authorization` | Requester |
| `settlement_reference` | Requester or Provider |
| `service_receipt` | Provider |
| `failure_notice` | Requester or Provider |

A message whose sender role is not allowed for its `message_type` MUST be rejected.

## 6. Amount rules

### 6.1 Integer-only amounts

M2M amounts MUST NEVER use floating-point values.

Every amount field MUST be represented as an integer using the same integer `amount` unit already used by L28 Protocol v1.0.0 for transaction amounts.

### 6.2 Smallest unit dependency

L28 Protocol v1.0.0 defines transaction `amount` as an integer and defines `IssuedSupply` in integer units with a hard cap of 28,000,000. The public repository does not separately name a fractional subunit (for example, a named decimal split of one L28).

Therefore:

- M2M v0.1 MUST represent amounts as positive integers in the L28 Protocol v1.0.0 integer `amount` unit.
- M2M v0.1 MUST NOT invent decimal places, fractional subunits, or a new denomination scale.
- If a future L28 major version normatively defines a smaller subunit, M2M would require a new major version to adopt it. That adoption is outside v0.1.

### 6.3 Economic non-interference

No M2M document or message MAY alter issuance, emissions, treasury balances, circulation, or the hard cap.

M2M payment amounts MUST refer only to non-coinbase transfer settlement under existing L28 rules when value is moved between requester and provider. M2M MUST NOT request or imply coinbase issuance as payment for a service.

## 7. Relationship to L28 settlement

### 7.1 Settlement authority

An L28 transfer becomes settlement evidence only when accepted under L28 Protocol v1.0.0 validation and recorded by the L28 ledger/consensus surface used by the implementation.

M2M MUST treat L28 as fail-closed: if required L28 settlement state cannot be verified, the M2M transaction MUST NOT transition to `settled`.

### 7.2 Settlement reference contents

A `settlement_reference` payload MUST include enough information to locate and verify one existing L28 settlement record, including at least:

- the L28 transaction identifier as computed or stored by the L28 implementation's canonical transaction identity mechanism;
- the payer identity reference used by L28 for the sender;
- the payee identity reference used by L28 for the receiver;
- the integer amount;
- the L28 transaction timestamp.

Exact field encoding is defined in [message_schema_v0.1.md](message_schema_v0.1.md).

### 7.3 Verification requirements

Before accepting a `settlement_reference` as valid for state transition:

1. The verifier MUST confirm the cited L28 record exists in the L28 source of truth.
2. The verifier MUST confirm sender, receiver, and amount match the accepted quote and authorization.
3. The verifier MUST confirm the cited record is not being reused for a different M2M `transaction_id` when local M2M state already binds that L28 record to another transaction.
4. If verification fails for any reason, the message MUST be rejected and the state MUST NOT advance to `settled`.

Finality semantics for "accepted by L28" are an L28 concern. Where L28 Protocol v1.0.0 does not publish an additional named finality primitive beyond validation/acceptance, M2M MUST NOT invent one. See Section 10.

## 8. Identity and cryptography reuse rules

M2M MUST reuse L28 primitives when they are already defined by L28 Protocol v1.0.0.

Normatively established by L28 Protocol v1.0.0 and therefore reusable without redefinition:

- Integer transaction `amount` values
- Integer `timestamp` fields on L28 transactions
- Opaque string identity references for sender/receiver fields on L28 transfers
- Policy-optional signatures on non-coinbase transfers, with verification supplied by the implementation

M2M-layer interoperability for digests, canonical JSON, Ed25519 suite selection, and machine-identity binding is defined by [interoperability_profile_v0.1.md](interoperability_profile_v0.1.md). That profile is subordinate to L28 Protocol v1.0.0 and MUST NOT be described as L28 consensus.

L28 settlement transaction identity for citations MUST use the stable Foundation 3 `compute_tx_id` behavior in `coin/tx_validation.py`.

## 9. Privacy boundary

L28 Protocol v1.0.0 does not normatively define an M2M privacy mode. The public repository references optional network preference labels in integration code, but those labels are not a normative confidentiality guarantee in PROTOCOL.md.

Therefore:

- M2M v0.1 MUST preserve any existing optional L28 privacy mechanisms without expanding their claims.
- M2M metadata can reveal relationships, timing, service identifiers, and amounts unless protected by an existing compatible mechanism.
- M2M v0.1 MUST NOT promise anonymity or confidentiality that this specification does not technically establish.
- Optional privacy transport semantics remain unresolved.

## 10. Unresolved protocol dependencies

The following remain unresolved or deferred for interoperable M2M runtime operation and MUST stay outside L28 consensus:

1. **Operational networking / transport binding**
   Envelope and transcript verification exist offline. Discovery, delivery, and live transport remain outside this specification.

2. **L28 address derivation / address grammar**
   L28 transfers continue to use opaque string sender/receiver identity references. This profile does not invent a new L28 address format.

3. **Named fractional subunit**
   Amounts remain integers. No fractional subunit is introduced.

4. **Settlement finality beyond acceptance**
   Settlement evidence remains verified acceptance in the consulted L28 source of truth. Irreversible finality / confirmations remain unresolved. Offline transcript validation recomputes citation IDs only and MUST NOT claim ledger acceptance.

5. **Optional privacy transport semantics**
   Unresolved; claims MUST NOT be expanded.

6. **Timestamp epoch interpretation**
   L28 Protocol v1.0.0 requires integer timestamps. Unix-second interpretation remains repository construction practice, not a PROTOCOL.md-named consensus rule.

Resolved at the M2M profile layer only (not as L28 consensus): canonical JSON subset, domain-separated SHA-256 digests, Ed25519 suite/encoding selection, machine-identity binding, settlement citation using Foundation 3 `compute_tx_id`, Foundation 5 verify-only envelope verification, and Foundation 6 offline transcript validation.

## 11. Out of scope for v0.1

The following are outside M2M Protocol v0.1:

- Runtime networking, discovery, or transport binding
- Wallet UX, custody, key generation, or autonomous spending engines
- Escrow, refunds, chargebacks, and arbitration
- Multi-party markets, auctions, or routing
- Service-result oracle correctness beyond provider assertion
- Any change to mining, emission, treasury, or supply logic
- Claims of live public-network availability

## 12. Document map

- Envelope and payload schemas: [message_schema_v0.1.md](message_schema_v0.1.md)
- States and transitions: [state_machine.md](state_machine.md)
- Security model: [security_model.md](security_model.md)
- Interoperability profile: [interoperability_profile_v0.1.md](interoperability_profile_v0.1.md)
- Transcript validation: [transcript_validation_v0.1.md](transcript_validation_v0.1.md)
- Offline test vectors: [test_vectors_v0.1.json](test_vectors_v0.1.json)
- Index: [README.md](README.md)
