# Actual monitor specification intake

## Goal and boundary

Continue the existing incomplete Windows custody correction from `53140bcf` in
the same owned worktree. Connect the reviewed transfer receiver to the actual
MonitorTransport.RunMonitor path. This is bounded source work, not native proof.
Do not enable workload invocation, allocation/staging, job creation/resume, or
ExactJobClosureProof issuance. Do not compile, run fixtures, touch the guest,
create runtime resources, install, publish, or use remote Git.

## Required source behavior

- Preserve original frame bytes including LF. Fixed 512-byte maximum includes
  that LF. Reject partial EOF and CR normalization; never reconstruct canonical
  input after stripping delimiters. Use the same bounded read path in production
  and deterministic fixture cases (memory streams are source-only coverage).
- Monitor generates one 32-lowercase-hex correlation token before accepting
  transfer input; advertise it in one bounded ready frame. It conveys no auth.
  Create one Receiver with the fixed setup deadline measured from monitor start.
- Dispatch original SPEC-XFER/1 BEGIN/DATA/END frames into the receiver in the
  real loop; queue returned ACK bytes nonblockingly. Any malformed transfer,
  active replay, deadline, queue admission failure, reader failure/EOF or writer
  failure stops the monitor irreversibly. Never wait or join an I/O worker.
- Store the completed immutable specification privately; completion/ACK does
  not renew the lease, authorize create/resume, reset deadlines, or allocate any
  runtime. Unexpected transfer input after completion fails closed.
- RESPONSE handling preserves canonical framing and current exact outstanding
  phase-bound challenge validation. Responses may renew the short lease during
  setup. Do not call AuthorizeCreate/AuthorizeResume in this slice, including
  before/after specification completion; backend remains unavailable. Future
  integration needs a new phase-bound challenge after staging before creation,
  rather than using a response collected before specification completion.
- Evaluate fresh monotonic time and stopping status for each dispatched frame,
  including END/ACK queue admission; a burst must not reuse one old timestamp.
  Preserve 32-frame/8192-byte queues, at most 16 dispatches per poll, 25-ms finite
  polling, independent setup/short-lease/absolute limits and closed workload CLI.
- Production dispatcher must actually call any extracted pure seam; do not add
  a disconnected model that cannot exercise the real dispatch decisions.

## Source fixtures before implementation

Author finite fixtures for original framing (511 bytes plus LF accepted, 512
plus LF rejected, CRLF rejected, partial EOF, invalid UTF8), real dispatcher
lease/transfer interleaving and ACK order, exact maximum-input transfer, completed
immutable intake without authority, replay/wrong token, queue pressure and
expired/stopped events including END equality. Show ACK alone cannot extend
lease and valid RESPONSE keeps setup alive without create/resume. No executed
RED/GREEN claim: compilation/native execution gates remain closed.

## Deliverable

Atomic local commit, clean worktree, whitespace check; README reports source-only
intake and all execution/custody gates honestly. Report paths and remaining
unverified behavior. Preserve cause history and existing review references.
