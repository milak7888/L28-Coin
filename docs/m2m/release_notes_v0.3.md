# L28 M2M v0.3.0 Release Notes (Release Candidate)

**Release name:** L28 M2M v0.3.0

**Status:** `frozen` (release candidate until merge, CI validation, and tagging)

**Release compatibility profile:** `l28-m2m-release-compatibility/v0.3`

**Protocol profile:** `l28-m2m/v0.1` (unchanged)

**Intended tag after merge:** `l28-m2m-v0.3.0` (not created by this milestone)

**Manifest:** [release_manifest_v0.3.json](release_manifest_v0.3.json)

## Summary

Foundation 15 freezes the L28 M2M v0.3.0 release candidate. The v0.3 manifest inventories the complete current public surface, includes immutable v0.1.0 and v0.2.0 manifests as historical artifacts, and records Foundation 14 reference-workflow contracts.

## Retained capabilities

All v0.1 protocol-profile and v0.2 tooling capabilities remain unchanged, including verify-only envelopes, transcript validation, conformance CLI, replay registry, admission gate, registry audit, and offline backup/recovery.

## v0.3 addition: Foundation 14 reference workflow

Foundation 14 adds the offline end-to-end reference workflow in `coin/m2m_reference_workflow.py`:

- profile `l28-m2m-reference-workflow/v0.1`
- report `l28-m2m-reference-workflow-report/v0.1`
- nine ordered stages from transcript validation through logical-state comparison
- exact `recorded_new` admission and exact `already_recorded` idempotency
- disposable temporary state outside the repository with mandatory cleanup

## Historical releases

- [release_manifest_v0.1.json](release_manifest_v0.1.json) — `l28-m2m-v0.1.0` at commit `7215d585a38155b5a36e7ebe077dcad43e810388`
- [release_manifest_v0.2.json](release_manifest_v0.2.json) — `l28-m2m-v0.2.0` at commit `4ea3c1b38a77d06f907baefb6783231f9bc84ce9`

## Limitations

- Reference workflow is verification tooling only, not deployment or spending authority
- Temporary workflow state is not operational registry state
- Backup files remain unencrypted and locally correlatable
- Supported runtime: CPython 3.11 with `cryptography==49.0.0` only
- Manifest IDs are integrity identifiers only, not trust anchors

## Verification

Offline tests in `tests/test_m2m_release_v0_3.py` independently verify the v0.3 manifest inventory, contracts, and historical v0.1/v0.2 anchoring.

**Validated test count:** 482 (full `unittest discover -s tests` on CPython 3.11)

## Non-goals

This release candidate does not create a Git tag, GitHub Release, package, or signature. It does not change runtime behavior beyond documenting and freezing the Foundation 14 surface.
