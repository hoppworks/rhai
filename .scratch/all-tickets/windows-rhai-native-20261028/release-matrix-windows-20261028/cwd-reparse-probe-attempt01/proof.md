# Native Windows cwd reparse prototype — 2026-10-29

This is OS investigation, not a Rhai product acceptance test. On Windows 11,
Rust/Cargo 1.77.2, source base `b2608fc7c` and the single probe overlay bound
by `original-export/source-manifest.json`, a directory opened with cap-std
without delete sharing could not be renamed, but could be changed in place
into a mount-point reparse entry. An exact waited child reading a relative
sentinel via `std::process::Command.current_dir` saw `missing` before the
change and `outside-only` after it. The source and target were both owned
fixture directories; this establishes only the observed OS configuration.

The intentionally inverted expectation failed with the named assertion and
exit 101; the restored probe passed 2/2. Both logs report deletion of the exact
junction tag and a no-reparse readback. The independent reviewer checked the
original control and suite, child wait, reported cleanup, and the limited
interpretation. Observer reports `prototype-pass`, `product_test_run=false`,
`product_acceptance=false`, all owned executables stopped, and no pending
custody. Driver elapsed 163.726 seconds under its 180-second bound.

The 208-frame export contains 16 originals whose saved lengths and SHA-256
were checked against `original-export-readback.json`. `journal-readback.json`
records eight length/CRC-checked records through REMOVED and zero payload
exit. Following export, the exact guest scope was checked for reparse entries,
removed and independently reported absent (`retired.png`). The exact owned
host scope and ISO were removed, original VM sdc restored and foreign sdb
preserved (`host-cleanup.json`).

The test is archived as `probe.rs`, outside Cargo test discovery. Its success
does not establish general Windows behavior, a Rhai vulnerability, or safe
process launch. The public Windows cwd contract and race-safe implementation
remain open. Earlier native Rhai cwd RED results remain in the sibling
`cwd-revised-baseline-attempt01/` evidence.

## Follow-up design constraint

The documented `CreateProcessW` current-directory argument is a path, and
`SetCurrentDirectory` affects all threads of its caller; neither alone binds the
launch to the already authorized capability. The existing managed launcher
already starts a child suspended. Comparing the child's actual opened directory
against the authorized directory before resuming is a possible investigation,
not an established solution: the Windows-documented PEB process parameters
hide the current-directory fields, and `NtQueryInformationProcess` is explicitly
subject to change. A candidate must establish that the checked object remains
the one used for relative resolution through initialization, cover architecture
and filesystem differences, and retain fail-closed process custody on errors.
File ID plus volume serial can identify two live handles when supported, but
does not by itself establish how to retrieve the child's cwd handle safely.
DirectChild currently uses `std::process::Command`, so this approach also needs
an equivalent suspended custody path there without weakening its semantics.

References: [CreateProcess](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw),
[SetCurrentDirectory](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setcurrentdirectory),
[RTL_USER_PROCESS_PARAMETERS](https://learn.microsoft.com/en-us/windows/win32/api/winternl/ns-winternl-rtl_user_process_parameters),
[NtQueryInformationProcess](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntqueryinformationprocess),
and [FILE_ID_INFO](https://learn.microsoft.com/windows/win32/api/winbase/ns-winbase-file_id_info).
