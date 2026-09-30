# Windows runtime allocation source review

Final candidate: `08fb7cd5d32240a96c92531ac7732db509d6ae9a` in
`/Users/hoppworks/projects/rhai-windows-scoped-runner`.
Scope: the independent allocation source substep in
`briefs/windows-runtime-allocation.md`; not full custody acceptance.

## Coverage and method

OCR commit and final range previews selected `WindowsCustodyBackend.cs` under its default
correctness, security, performance, maintainability and coverage rules.
README was excluded by extension and the fixture by default path; both were
manually reviewed. Total files 3, reviewed 3, skipped 0, coverage 100%.
The backend diff and complete relevant constructor, allocation, ownership,
journal, identity and ACL paths were read. No compiler or fixture ran.

## Source findings and corrections

- The allocation fixture deleted journals while retaining runtime directories,
  including an uncertain post-create case. Retain both together and print their
  exact paths; no recovery evidence should be destroyed by this fixture.
- Whole-message truncation at 512 characters could truncate a bounded but long
  journal path. Bound the descriptive error separately and preserve both exact
  paths in failure diagnostics, including setup and disposal failures.

Related draft corrections already retained in the implementation include
ownership transfer and exception cleanup, test-only failure injection, exact
identity field placement, DELETE access on the initial runtime pin without
delete sharing, and avoiding DELETE access on existing ancestor pins.

Both findings are corrected: `9a68a437` retains allocation journals and prints
runtime/journal pairs; `08fb7cd5` bounds only descriptive text and preserves full
paths, including setup and disposal errors. Both correction diffs were reviewed.
Final `git show --check` passed and the candidate worktree is clean. Candidate
path bounds include fixed generated suffixes on setup failures; diagnostics are
finite without truncating those paths. These checks are source/whitespace checks,
not compilation or behavior evidence.

## Applicability and limits

Source orders a flushed intent before exclusive directory creation, supplies
the protected DACL at creation, refuses existing names without adopting them,
verifies ACL and identity through the opened pin, and flushes identity before
reporting the recorded state. Failures retain the candidate and journal.
These are source observations, not Windows behavior or durability proof.

No monitor calls this backend. No handle-safe staging or disposition exists.
The current fixture deliberately retains allocations and must not be launched
outside a future accepted custody harness. No temporary resource was created
during this source review. Compilation, executed TDD RED/GREEN, native collision,
ACL, partial-failure, journal durability and exact cleanup proof remain absent.
Running lease renewal, immutable specification, monitor integration, payload
job ownership, finalization/export and all full-custody gates remain required.
No ticket is closed or source integrated into the coordinator's product tree.
