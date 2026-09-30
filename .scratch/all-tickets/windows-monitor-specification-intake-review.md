# Monitor specification intake source review

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

## Related draft corrections and remaining fixture boundaries

Updated full dispatcher/fixture source and actual MonitorTransport diff were
read. Production now calls the dispatcher and retains LF-inclusive frames;
its create/resume calls are removed. Maintenance clears old handshakes;
FormatException handling, ready/challenge liveness checks and clearing completed
input on stop are present. These close the corresponding source findings,
subject to immutable final review; no execution evidence is available.

Two remaining fixture issues were delivered immediately: helper challenge
interval is hardcoded2000 despite test policy period2, so interleaved renewals
cannot obtain a frame. Pass the selected policy period. END scripted readings
are consumed by Start/BEGIN/DATA, putting equality at END's first check rather
than receipt admission. Arm a clock immediately before END after stable setup
and assert failed admission leaves no completed input/receipt. Avoid null-result
exceptions concealing the failing precondition or unrelated coverage.

## Immutable final review

Reviewed `dd8c07dc` (six changed files) and related correction `24c3a19f`
(one fixture). All six source/diff files were read, including manually reviewed
OCR-excluded README/fixture; zero skipped files. OCR preview selected the four
production sources and the default rule was read. Final source, whole new
fixture and README changes were reread, supplementing truncated output with
bounded reads. Both committed whitespace checks pass; worktree is clean.

Reported clock/type/interval/END-precondition, frame exception, admission
liveness and stale-handshake findings are closed in source. Actual RunMonitor
uses the receiver dispatcher; original LF-inclusive frame limit is512. Valid
maintenance responses clear old transition handshakes; no production
AuthorizeCreate/AuthorizeResume call remains in these paths. ACK acceptance
cannot renew the lease. The fixture arms the END clock after successful
BEGIN/DATA and checks both readings9/12, no receipt and null completed input.
Ready/challenge admission and stopped stability are now explicit source cases.

The maximum-input helper's ten empty-argument wire overhead is224 bytes under
the reviewed serializer; the remaining7968 bytes are1992 CJK characters, each
adding four encoded bytes within field/command bounds. Actual interleave uses
selected policy period2 and fixed setup120 with finite28-frame pumping. This
is source arithmetic/review, not a surrogate execution proof.

Closed subrequirements: reviewed original-framing transport adapter, actual
bounded intake dispatch, maintenance lease separation and source contract
coverage. No compiler, fixture, native pipe/OS, staging, workload, exact-job or
cleanup acceptance occurred. PATH exposes no dotnet/csc/mcs compiler; no install
was attempted. Full Windows custody and product tickets remain open. The next
source requirement is monitor ownership of allocation/staging on a worker
without watchdog blocking; fixed repair bounds must be recorded before that
work. Existing Expert/cause history and native execution gates remain binding.
