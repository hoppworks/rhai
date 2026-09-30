# Monitor specification intake review in progress

Baseline is source-reviewed `53140bcf`; contract is
`briefs/windows-monitor-specification-intake.md`. The same responsible agent is
confirmed running. An untracked MonitorSpecificationIntakeFixture.cs now exists;
its complete intermediate source was read. No model implementation, compiler,
fixture execution or native operation is claimed.

## Intermediate fixture findings

Delivered for related correction in the active draft:

- NewDispatcher accepts FakeClock, but the END-admission case passes unrelated
  SequencedClock. The helper signature cannot express both clocks as written.
- END-admission starts with time9 against start0/short lease5: setup is already
  stopped before BEGIN. Its deadline12 is not reached by values9/10. Set live
  renewed lease and fixed setup preconditions explicitly and control only the
  END acceptance/admission readings to exercise the second-check equality.
- The interleave case transfers a small specification, despite its maximum-input
  label. Add actual exact8192-byte input through the production dispatcher with
  bounded pumping and lease renewal while preserving the fixed setup deadline.
- Renewal at4 followed by Poll at4 does not show survival beyond original expiry5;
  poll at6 while before renewed expiry9/setup12.
- ACK-only expiry has no successful receipt before expiry. Accept BEGIN and drain
  its ACK first, then advance to original expiry and assert stopping.
- Add stopped-event stability/no receipt and canonical RESPONSE framing coverage.
  Localize fixture precondition failures rather than silently bypassing the
  intended stage or terminating unrelated cases with sender exceptions.

These are intermediate source/coverage findings, not executed RED/GREEN or a
completed failed full-custody correction. Await exact implementation and commit;
review every changed file and actual production dispatch, keep workload gates
closed and execution subject to native custody prerequisites.

## Intermediate dispatcher and lease source review

The complete new untracked MonitorSpecificationIntake.cs and the dirty
LeaseMonitor.cs diff were independently read. The receiver is now intended to
be dispatched through a real production seam; the transport call is still
pending at this inspection. Findings delivered in the same responsible context:

- DecodeCanonicalFrame throws plain FormatException while Dispatch catches only
  the transfer subtype and DecoderFallbackException. Canonical control-frame
  failures can escape without the promised terminal result; catch appropriately
  and cover RESPONSE framing failures.
- Start lacks liveness checking before ready admission; TryIssueChallenge lacks
  fresh checking after nonce generation and before challenge admission.
- END stores CompletedSpecification before final receipt admission. A later
  stop/admission failure must not expose it as accepted live input for future
  creation; clear on failure or gate consumption explicitly.
- AcceptMaintenanceResponse avoids minting handshakes but initially preserves
  previously latched create/resume handshakes. Clear them on successful
  maintenance and cover mixed normal-then-maintenance use, so future integration
  cannot consume pre-staging permission accidentally.

No compiler, fixture execution or native resource occurred. These findings are
within the incomplete correction and await exact final source review.
