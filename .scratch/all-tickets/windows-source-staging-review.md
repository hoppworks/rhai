# Windows source staging review in progress

Baseline: clean `08fb7cd5` in the owned candidate worktree
`/Users/hoppworks/projects/rhai-windows-scoped-runner`.
Implementation brief: `briefs/windows-source-staging.md`.
The responsible context is actively implementing this related requirement.
The current draft is uncommitted; final source review and coverage accounting
must use its eventual commit. No compiler/native/fixture execution occurred.

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
