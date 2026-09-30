# Windows handle-based source staging and executable validation

## Task and context

Continue the related Windows custody implementation in the owned candidate
`/Users/hoppworks/projects/rhai-windows-scoped-runner`, task/windows-scoped-runner,
from clean `08fb7cd5`. Read AGENTS.md and the existing Expert answer at
`/Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/escalations/02-windows-runtime-custody.answer.md`,
especially Filesystem custody and partial setup. Retain the source review at
`../windows-runtime-allocation-review.md` relative to this brief.

Implement the next actual source requirement: stage the supplied source tree
into the exact recorded runtime without following reparse points, and validate
and pin the actual staged executable through checked path components. Do not
wire the monitor or public workload entry yet. Do not call legacy CopyTree.

## Required behavior

- Operate only after recorded allocation identity; retain the sole runtime pin,
  ancestor pins and external journal across staging. No caller cleanup path.
- Pin the source root and every traversed ancestor/component without following
  reparses. Inspect attributes/identities through opened handles. Open source
  files for reads with mutation/deletion-denying sharing; copy from those handles,
  not a second path reopen. Reject sharing failures, unexpected reparses, path
  aliases/unsupported forms, identity changes and detected source mutation.
- Source directories and files need a finite inventory and byte/depth bounds;
  use fixed internal limits with overflow-safe accounting, bounded transfer
  buffers and explicit failure diagnostics. These are source policy constants,
  not permission to execute a measurement campaign. Make limits visible in docs
  for later immutable specification integration. Do not let caller input raise
  them. Preserve the full tree contract rather than staging only one file.
- A directory pin alone does not freeze child creation/removal. Define how the
  staged manifest and final source consistency check detect changed entries,
  identities or metadata; do not claim a pre-copy attributes check is sufficient.
  If the source cannot be staged consistently, fail and retain uncertainty.
  The scope is operational owned source, not hostile same-user isolation.
- Create destinations exclusively below the held runtime through validated,
  pinned components, explicit expected private ACL inheritance, no adoption of
  existing entries. Keep destination file handles through transfer/flush and
  inspect actual attributes/identity. Record a bounded staging completion receipt
  only after successful copy and validation. On any error do not mark staged or
  ready, do not launch, and retain exact runtime/journal evidence.
- Validate the relative executable using Windows component syntax before I/O:
  reject absolute/drive-relative, UNC/device, ADS, parent/current components,
  empty components, trailing dots/spaces, reserved DOS names and illegal/control
  characters. Do not rely on IsPathRooted plus prefix. Open each staged component
  through checked non-reparse pins and require a plain existing file under the
  staged tree. Preserve the exact final handle/identity for later launch custody.
- Release every temporary source/destination handle on partial setup independently;
  preserve the runtime and journal owner until its documented transfer/disposal.
  No path-based recursive deletion or safe-cleanup claim.
- All blocking filesystem I/O remains off the future watchdog path. Provide a
  worker-facing cancellation/deadline check between bounded steps, but do not
  claim a stuck synchronous Win32 call is forcibly bounded. Later monitor hard
  deadline/termination must retain incomplete journal state for such failures.

## Test-first source and verification boundaries

Write meaningful fixture source before implementation for nested contents and
independent readback, syntax rejection before I/O, missing/non-file executable,
source mutation/sharing refusal, source and staged reparse refusal, bounded
inventory/bytes, destination collision and retained partial staging failure.
Use only narrow test seams behind SCOPED_RUNNER_TESTING. Retain exact fixtures
and their journals if handle-safe cleanup is unavailable; never use fixture
path deletion to imply custody acceptance.

No compiler/bootstrap, native fixture, guest command/input, Rust build, install,
credentials/admin, global/home changes or remote publication. Unexecuted fixtures
are not TDD RED/GREEN or native evidence. Whitespace/static checks are permitted.
Commit atomically as configured human author and report ref, files, source
invariants, actual checks and remaining full-custody gates. If a concrete design
boundary prevents an invariant, report it with source references; no new Expert
chain or silent reduction of the contract. The single existing full Windows
custody correction remains incomplete, not a new attempt budget.
