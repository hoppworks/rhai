# Current Darwin filesystem and TCP behavior contract

This is a prepared acceptance runner for test/source revision
`2f795ecee8edd6ddf348f382e5397cc6e348ad37` (archive SHA-256
`43c8b8e43a2bcd3e74dd0be3d60a0dea2eab50eb5bfe65cc736684631523d52b`) and
compatible lock SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
It runs only on native Darwin arm64 with private Rust 1.77.2. Its nine behavior
rows exercise filesystem access, policy metadata, TCP connect/listen/read/write,
and combined sys/net use through the public Engine plus real OS resources. The
five assertion controls must fail for their intended incorrect expectation;
then the unchanged inputs must pass all nine behavior rows.

Every Cargo command retains original separate stdout and stderr files, status,
and command metadata. For each multi-target behavior row, the parser validates
the exact target-header sequence in stderr, then associates each successive
complete stdout libtest block with the corresponding header and frozen named
inventory. The resulting parser input is explicitly labeled as derived target
order, not captured cross-stream chronology. The expected test names are derived from active `#[test]` functions in
the frozen sources under the row's feature set and Darwin target cfg, then
compared exactly with names reported by libtest. Each target must have exactly
one result summary.

The runner rejects ignored, measured, filtered, missing, repeated, or failed
test coverage. It also recognizes the actual
`filesystem rejects non-UTF-8 fixture with EILSEQ:` early-return diagnostic
emitted by the frozen filesystem test. The test prints that diagnostic and
returns normally, so libtest can report it as passed with zero ignored tests.
The runner associates that diagnostic with the exact frozen producer
`sys_fs/test_non_utf8_file_name`. It consumes the diagnostic separately from
libtest structure, so stderr-only output cannot fabricate a test or summary.
An stderr diagnostic resolves only when `sys_fs` is selected and that named
test occurs exactly once in its frozen inventory. Inline stdout diagnostics
must be attached to that same target and test. Missing or conflicting producer
association is retained as unresolved evidence and fails closed: observed
outcomes remain recorded, but no named row is certified. A resolved occurrence
marks only the producer uncovered; siblings and other targets retain their
observed results. A successful Cargo exit alone is insufficient.

The macOS system-prefix policy test obtains distinct `/var/../../...` and
`/private/var/../../...` spellings for the same existing `real` fixture
directory beneath the central runtime. It configures the Engine root with the
first spelling, reads the file through both spellings, requires write denial,
and performs independent host readback. The fixture helper asserts distinct
strings and independently canonicalizes both spellings to the exact owned
directory before Engine construction. This fixture correction is included in
the source revision and archive hash above; previous mismatched-root assertions
are not acceptance evidence.

Before future dispatch, stage the source archive, accepted lock, this contract,
the runner, and the existing `run_scoped.py` package inputs under the unique
real directory named `current-darwin-sys-net-behavior-2f795ece-sampler2-20261002`.
Set `DARWIN_PROOF_STAGE` to that absolute stage, create a unique scope at
`~/.local/share/agent-builds/rhai/current-darwin-sys-net-behavior-2f795ece-sampler2-20261002`,
and invoke this helper through the existing `tools/run_scoped.py` with an
absolute `TMPDIR` equal to that scope. Run both the scoped runner and helper
with `/Users/hoppworks/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`,
set `PYTHONDONTWRITEBYTECODE=1`, and pass the runner `--timeout 600`. Its runtime owns the extracted source,
private Rustup/Cargo homes, target output, and temporary files. Export receipts
to the stage outside that disposable runtime. Use one heavy run at a time,
jobs=2, at most 16 descendants, sampled RSS stop at 2 GiB, storage preemption
at 1.5 GiB and hard stop at 2 GiB, and the helper's 510-second work / 540-second
total bounds. No shared-home toolchain install, process fixture, service,
credential or upstream write is part of this contract. There is no process API
fixture or service involved.

The parent runner must perform an independent cleanup readback of the exact
runtime path, confirm
the scoped runtime is gone, confirm the scope is empty before removing only
that exact directory, and query every recorded Darwin PID/start identity.
Permission failures and other query errors are unknown and fail closed;
reparenting or command changes do not hide a surviving PID/start identity. The
helper records itself, its supervisor, commands, and sampled owned descendants.
The readback also enumerates recorded helper/command process groups and fails
if any member remains. Preserve all exported receipts and prior accepted
compiler/example proof. Existing Linux behavior proof is useful for row design
but is not Darwin acceptance. Existing Darwin compiler and example proof applies
only to those unchanged requirements; combined filesystem/TCP behavior remains
unaccepted until this contract is executed and all row/control criteria pass.
