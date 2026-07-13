# L28 M2M v0.3.0 Release Compatibility

**Document:** L28 M2M Release Compatibility v0.3
**Status:** Frozen release compatibility policy (Foundation 15)
**Release:** L28 M2M v0.3.0 (`frozen`)
**Release compatibility profile:** `l28-m2m-release-compatibility/v0.3`
**Protocol profile:** `l28-m2m/v0.1`

## 1. Release scope

L28 M2M v0.3.0 is the overall offline M2M tooling release. It freezes the Foundation 14 offline end-to-end reference workflow while preserving the existing `l28-m2m/v0.1` protocol profile and all v0.1/v0.2 public contracts.

## 2. Protocol profile unchanged

Envelope, transcript, interoperability, replay registry, admission, audit, and backup/recovery profiles remain at their existing v0.1 versions. No v0.1 envelope, signature, transcript, replay, admission, audit, backup, or registry-schema contract changed in Foundation 14.

## 3. v0.3 tooling addition

Foundation 14 adds the offline reference workflow:

- `coin/m2m_reference_workflow.py`
- profile `l28-m2m-reference-workflow/v0.1`
- report `l28-m2m-reference-workflow-report/v0.1`

The workflow is offline verification tooling only. It does not deploy services, sign messages, access wallets, query ledgers, start networks, or claim settlement finality or spending authority.

## 4. Historical releases

- `l28-m2m-v0.1.0` remains immutable at commit `7215d585a38155b5a36e7ebe077dcad43e810388`
- `l28-m2m-v0.2.0` remains immutable at commit `4ea3c1b38a77d06f907baefb6783231f9bc84ce9`

Both historical manifests are inventoried in the v0.3 manifest as `historical_release_manifest` artifacts and must remain byte-for-byte unchanged.

## 5. Reference workflow boundary

The reference workflow:

- validates a signed transcript;
- admits to a disposable replay registry;
- requires exact `already_recorded` idempotency before and after backup/restore;
- audits, backs up, restores, and compares logical registry state;
- emits one deterministic report;
- removes all temporary state outside the checkout.

Approved API input modes are `api`, `file`, and `stdin`. `require_terminal` must be an exact boolean. Invalid parameters fail closed without leaking rejected values.

## 6. Compatibility classes

| Change class | v0.3.0 policy |
|---|---|
| Documentation clarifications outside hashed inventory | Allowed only outside the frozen v0.3 inventory |
| Bug fix changing bytes in any inventoried artifact | Requires explicit manifest and release-note update |
| New protocol message types or envelope rules | Requires a new protocol profile |
| Dependency pin change | Requires explicit manifest review |
| Security exception | Must be explicit in release notes and compatibility document |

## 7. Non-claims

Neither historical nor current release manifests prove authorship, safety, settlement, finality, service completion, or spending authority. Manifest IDs are integrity identifiers only.

## 8. Related documents

- [release_manifest_v0.3.json](release_manifest_v0.3.json)
- [release_notes_v0.3.md](release_notes_v0.3.md)
- [reference_workflow_v0.1.md](reference_workflow_v0.1.md)
- [release_manifest_v0.2.json](release_manifest_v0.2.json)
- [release_manifest_v0.1.json](release_manifest_v0.1.json)
- [README.md](README.md)
