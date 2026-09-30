# Windows source staging review

Baseline: clean `08fb7cd5` in the owned candidate worktree
`/Users/hoppworks/projects/rhai-windows-scoped-runner`.
Implementation brief: `briefs/windows-source-staging.md`.
The source slice is committed as `b4c055ee`; related review corrections are
active in the same responsible context. No compiler/native/fixture execution
occurred. This review does not accept Windows custody or a ticket.

## Committed source review and coverage

OCR commit preview selected WindowsCustodyBackend.cs and excluded README.md
(unsupported extension) and fixtures/CustodyBackendFixture.cs (default path).
The default correctness/security/resource/test rules were read. All three
changed files were manually reviewed, including those exclusions:
total_files=3, reviewed_files=3, skipped_files=0, coverage_rate=100%.
This coverage is source review, not executed behavioral coverage.
`git diff --check 08fb7cd5..b4c055ee` passed. The candidate was clean when collected.

The committed source retains source file pins through final scan/receipt, reads
and hashes opened source/destination handles, verifies exclusive destination
ACLs and identity, and retains executable plus parent pins on the owner.
SafeCloseStagedExecutable now attempts all closures independently. Bounds are
2,048 entries (including the source root), depth 32, 64 MiB/file and 512 MiB/tree.
The README explicitly limits the scan to operational consistency rather than
an atomic or hostile-input snapshot. All native API semantics remain unproven.

Final related corrections requested:

- Supply the full sourceAncestors chain to the identity overlap helper. The
  single root pin has only its own identity, making the helper's intended
  ancestor check incomplete. Existing spelling/sharing failures are not proof
  of that identity-chain invariant.
- Assert intended failure diagnostics in inventory/total-byte fixtures; generic
  failure could satisfy them after an unrelated earlier error. Add distinct
  source cases for per-file/depth limits and cancellation, retained runtime and
  receipt absence after owner closure. No fixture run is authorized here.
- Correct README's remaining-boundary wording: executable validation source
  exists; native and launch acceptance remain pending. Record the total-bound
  fixture's large source/destination requirement before any native budget.

Correction commit `03a56347` was independently reviewed across all three files:
total_files=3, reviewed_files=3, skipped_files=0, coverage_rate=100%.
OCR exclusions and rules are unchanged. `git diff --check b4c055ee..03a56347`
passed; candidate is clean. The overlap helper now receives sourceAncestors,
whose leaf identity was compared with the separate root pin. Boundary fixtures
assert specific diagnostics and identity-recorded setup, then independently
read the journal after disposal and check runtime retention and absent STAGED.
Per-file, depth and canceled-token cases are distinct from total/inventory cases.
README accurately distinguishes present source from pending launch verification.
No compiler or fixture ran. Native depth/path-length and symlink privilege gates,
as well as the explicitly budgeted large fixture, still need real verification.

The bounded staging source requirement is ready for the next source substep;
operational acceptance remains open. Do not integrate the candidate.

## Draft findings delivered to responsible context

- Failure fixtures read the share-zero journal before disposing its owner;
  catching that read failure as false could falsely prove absence of STAGED.
  Read after disposal and fail the test if readback is unavailable.
- A single file larger than the total bound actually trips the single-file
  bound. Use separate fixtures that reach the intended total bound and partial
  copy failure; do not mistake a different failure for the requirement.
- CopyDirectoryTree and SafeCloseStagedExecutable were instance methods placed
  in the outer static class while accessing nested owner fields. Correct scope
  and field ownership before commit; whitespace checking cannot prove compilation.
- Reopening the runtime through PinDirectory used sharing that conflicts with
  its existing DELETE-access pin. Reuse that exact pin instead of reopening the
  runtime ancestor. Share checks are bidirectional for already-open handles.
- Executable parent pins were closed on helper return, leaving parent renames
  possible while only the final file stayed pinned. Retain the complete chain
  in the owner until launch custody ends.
- The source identity was used as expected executable identity for the new
  destination file. Record and verify the separate destination identity.
- Do not close already-checked source file handles during the remainder of the
  final scan. Retain bounded mutation/delete-denying handles and directory pins
  through the completion receipt. Directory pins alone do not freeze new child
  entries; explicitly retain the operational consistency/snapshot boundary and
  report any unfulfilled invariant rather than claim an atomic tree snapshot.
- Reject source/runtime/evidence overlap before copy, through checked identities
  as well as validated spelling; do not allow recursive self-copy or journals
  to enter the copied tree.

These are findings on an intermediate draft. Related corrections are running;
they do not establish behavior or spend a completed full-custody correction.
The final review must verify the corrected paths and account for every file,
including fixtures and README excluded by OCR defaults.

## Primary documentation consulted

[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
documents sharing through handle lifetime and component reparse handling.
[FindFirstFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-findfirstfilew)
warns that directory results can change before a subsequent operation.
[Windows naming](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file)
defines reserved components, device names with extensions and superscript
COM/LPT digits, and DOS aliases. These are API constraints, not native proof.

## Acceptance remains open

Source consistency, destination content/identity readback, actual executable
pinning, cancellation, finite inventory/bytes and retained partial failure need
final source review and native fixtures under an accepted custody harness.
Staging remains off the watchdog and public workload entry remains disabled.
Safe disposition, immutable specification, monitor integration, running lease
renewal, job/process custody, finalization/export and all native gates remain.
