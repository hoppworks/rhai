# Windows runtime disposition source review

Baseline: source-reviewed `03a56347` in
`/Users/hoppworks/projects/rhai-windows-scoped-runner`, task/windows-scoped-runner.
Brief: `briefs/windows-runtime-disposition.md`. The responsible live context
is implementing this related source requirement. No compiler/native/fixture
execution occurred. Candidate `bb7060a2` was independently source-reviewed:
four changed files, all four reviewed, zero skipped (100% source coverage).
OCR selected the backend and monitor; excluded README and fixture were manually
reviewed as well. Default correctness/security/resource/coverage rules applied.
Whitespace checking passed; compilation and execution remain unverified.

## Commit findings and reviewed correction

- Partial-removal fixture observes failure/state/root presence but never proves
  a child was actually removed while other children remain. Require independent
  post-close inventory observation without assuming enumeration order.
- Exact `.` and `..` enumeration pseudoentries currently abort the scan. Skip
  these without opening/deleting them; preserve offset validation and a finite
  raw-record budget. Empty/malformed names must still fail closed.
- Enumeration records only a 64-bit ID and compares it with the low half of the
  held 128-bit identity. Require full 128-bit enumeration identity matching or
  a proven explicit filesystem restriction before deletion.

These findings were sent to the same responsible context for source corrections.
Production removal remains unavailable: no monitor issuer constructs the typed
exact-job closure proof. No complete custody correction has failed.

Correction `6c37071b` was independently reviewed across all three changed files:
backend, fixture and README; zero skipped, 100% source coverage. The complete
128-bit ID from FILE_ID_EXTD_DIR_INFO is compared with the held entry identity
and volume; unusable IDs and unsupported class errors refuse deletion. Header
offsets 88/72 and classes 19/20 match the documented field layout. Exact dot
entries are skipped without opens/deletion but count toward finite raw-record
limits and still pass native offset validation. Partial fixture independently
observes one absent and two remaining named leaves after owner disposal, without
assuming directory enumeration order. Both commits pass whitespace checking.

This closes the related source findings only. No compilation, executed fixture,
TDD RED/GREEN, native behavior, exact-job closure, forced interruption or E2E
acceptance is proven. Candidate stays separate and workload launch disabled.

## Intermediate source findings

- PrepareDispositionTree writes `data/data.txt` and `data/nested/inner.txt`;
  sharing and failed-journal fixtures initially targeted nonexistent
  `data.txt` and `keep/sentinel.txt`. Use actual staged entries, require recorded
  allocation/staging setup, and assert the intended failure diagnostic.
- `!File.Exists(runtime)` is true for a directory that still exists. Successful
  disposition requires backend absence readback plus independent directory
  absence observation; native semantics remain unverified.
- Cancellation alone is not inventory/depth-bound coverage. Add separate bound
  and read-only refusal source cases, with failure journal readback after closure.

These observations were delivered to the responsible context while its draft
was incomplete. They are not completed failed full-custody corrections.
Do not integrate source or accept cleanup from authored fixtures.

## Primary references

[SetFileInformationByHandle](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfileinformationbyhandle)
requires appropriate access and documents class 4 disposition.
[FILE_DISPOSITION_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_disposition_info)
uses a BOOLEAN member.
[Closing and Deleting Files](https://learn.microsoft.com/en-us/windows/win32/fileio/closing-and-deleting-files)
documents deferred deletion until outstanding handles close.
These constrain source review; they do not prove native behavior.

[FILE_ID_BOTH_DIR_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_both_dir_info)
documents its 64-bit ID and eight-byte record alignment.
[FILE_ID_EXTD_DIR_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_extd_dir_info)
provides a FILE_ID_128 and information classes 19/20; supported native behavior
must still be verified before acceptance.
