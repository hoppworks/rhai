# Windows runtime disposition review in progress

Baseline: source-reviewed `03a56347` in
`/Users/hoppworks/projects/rhai-windows-scoped-runner`, task/windows-scoped-runner.
Brief: `briefs/windows-runtime-disposition.md`. The responsible live context
is implementing this related source requirement. No compiler/native/fixture
execution occurred. Final commit review and coverage accounting remain pending.

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
