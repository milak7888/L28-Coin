# L28 M2M Replay and Idempotency Registry v0.1

**Document:** Offline M2M Replay and Idempotency Registry v0.1
**Status:** Offline local registry (Foundation 8)
**Normative subordination:** Subordinate to [L28 Protocol v1.0.0](../../PROTOCOL.md) and [transcript_validation_v0.1.md](transcript_validation_v0.1.md).
**Related:** [test_vectors_replay_v0.1.json](test_vectors_replay_v0.1.json), [security_model.md](security_model.md), [conformance_cli_v0.1.md](conformance_cli_v0.1.md)

## 1. Purpose

Foundation 8 provides a local, explicit, hash-only SQLite registry that prevents a valid signed M2M transcript from causing repeated processing across separate local executions.

Runtime: `coin/m2m_replay_registry.py`.

The registry is:

- local and offline;
- not an L28 ledger;
- not consensus;
- not a wallet;
- not settlement authority.

Foundation 7 CLI does **not** integrate persistent replay by itself. Foundation 9 adds optional registry flags to `coin/m2m_conformance_cli.py`; see [admission_cli_v0.1.md](admission_cli_v0.1.md).

## 2. Public API

```
ReplayRegistry(path, *, create=False)
check_and_record(envelopes, *, require_terminal=False) -> ReplayResult
check_and_record_json(raw, *, require_terminal=False) -> ReplayResult
close() / context manager
```

`ReplayResult` includes: `ok`, `code`, `newly_recorded`, `new_messages`, `state`, `exchange_hash`, `transcript_fingerprint`, `head_message_id`, `message_count`, `verification_code`.

Callers MUST gate downstream work on `newly_recorded` / `new_messages`. Idempotent recognition (`already_recorded`, `already_recorded_prefix`) is not new acceptance.

## 3. Explicit creation and path safety

- Creation requires `create=True`.
- Path must be absolute.
- Path must not be inside the L28-Coin repository.
- Parent directory must already exist (parents are not created).
- Symlinks, directories, FIFOs, and special files are rejected.
- New registry files use owner-only mode `0600` on POSIX.
- Missing DB with `create=False` fails closed.

## 4. Schema and stored-data boundary

Tables:

1. `registry_metadata` — schema version
2. `exchanges` — `exchange_hash`, `transcript_fingerprint`, `head_message_id`, `state`, `message_count`
3. `messages` — `message_id`, `exchange_hash`, `ordinal`, `previous_message_id`

Stored: cryptographic message IDs and hashed exchange identifiers only.

Not stored: raw exchange IDs, transcript JSON, payloads, signatures, public keys, identities, balances, timestamps, paths, or private documents.

## 5. Hash algorithms

- Exchange hash: `SHA-256(L28-M2M-V0.1-REPLAY-EXCHANGE\x00 || UTF-8 exchange id)`
- Transcript fingerprint: `SHA-256(L28-M2M-V0.1-REPLAY-TRANSCRIPT\x00 || Canon(ordered message_id array))`

Lowercase hex. Raw exchange identifiers are never stored.

## 6. Idempotency model

| Case | Code | newly_recorded |
|---|---|---|
| New exchange | `recorded_new` | true |
| Exact repeat | `already_recorded` | false |
| Previously recorded prefix | `already_recorded_prefix` | false |
| Valid monotonic extension | `recorded_extension` | true |
| Fork | `exchange_fork` | false |
| Cross-exchange message ID | `message_replay` | false |
| Verification failure | `verification_failed` | false |
| Terminal extension | `terminal_exchange_extension` | false |

Verify with Foundation 6 before any write. Invalid transcripts write nothing.

Terminal exchanges may be recorded and exactly repeated, but cannot be extended. No registry result implies refund, reversal, settlement finality, or service completion.

## 7. Concurrency and atomicity

- `BEGIN IMMEDIATE` for check-and-record
- Unique constraints remain authoritative
- Concurrent duplicates yield one new record and one idempotent result
- Lock contention fails closed after a bounded busy timeout
- Full rollback on failure; no partial rows

## 8. Integrity

On open: schema version, required tables, foreign keys, integrity check, ordinal continuity, count/head/fingerprint recomputation. Corruption fails closed. No automatic repair.

SQLite settings: foreign keys on, `journal_mode=DELETE`, durable `synchronous=FULL`, parameterized SQL only.

## 9. Privacy and operational notes

- Message IDs and hashed exchange IDs remain correlatable metadata.
- Database is not encrypted and not authenticated against local tampering.
- Deleting the registry removes replay memory; copying it copies replay memory.
- Local filesystem security remains required.
- Registry state is local and not consensus.

## 10. Test vectors

Deterministic operation sequences: [test_vectors_replay_v0.1.json](test_vectors_replay_v0.1.json).

Foundation 10 adds a strictly read-only offline auditor. See [registry_audit_v0.1.md](registry_audit_v0.1.md).
