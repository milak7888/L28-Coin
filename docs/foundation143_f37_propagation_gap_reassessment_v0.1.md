# Foundation 143 - F37 Propagation Gap Reassessment v0.1

Foundation 143 adds real isolated IPv4 loopback transport evidence.

- F37-07 advances to PARTIAL_ISOLATED_LOOPBACK_TRANSPORT_EVIDENCE. Real TCP
  loopback framing, admission, bidirectional HELLO exchange, reconnect, and
  replay rejection are demonstrated within the exact Foundation 142 boundary.

- F37-10 advances to PARTIAL_ISOLATED_LOOPBACK_PROPAGATION_EVIDENCE. HELLO,
  TIP_EVIDENCE, and CANDIDATE_EVIDENCE are transported between the two
  disposable agents. This is isolated local evidence only and is not public,
  production, confirmation, or settlement evidence.

- F37-11 remains BLOCKED_REORG_POLICY. No confirmation policy, confirmation
  count, fork-choice, rollback, or reorganization policy is defined.

No persistent networking authorization exists after the experiment ends.
