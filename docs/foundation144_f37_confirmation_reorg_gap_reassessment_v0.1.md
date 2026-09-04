# Foundation 144 - F37 Confirmation/Reorg Gap Reassessment v0.1

Foundation 144 creates the decision package required before confirmation or
reorganization behavior may be implemented.

- F37-07 remains PARTIAL_ISOLATED_LOOPBACK_TRANSPORT_EVIDENCE.
- F37-10 remains PARTIAL_ISOLATED_LOOPBACK_PROPAGATION_EVIDENCE.
- F37-11 remains BLOCKED_REORG_POLICY.

No confirmation count is selected. No fork-choice rule is selected. No maximum
reorg depth is selected. No finality rule is selected.

Conflicting canonical evidence remains fail-closed and cannot trigger an
automatic canonical-state rewrite.

The next gate requires an explicit policy selection followed by separate
implementation authorization. A policy decision is a development/governance
choice and does not grant runtime consensus override authority to an operator.
