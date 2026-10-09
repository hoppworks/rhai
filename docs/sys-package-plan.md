# Rhai `sys` package: contract, requirements matrix, and plan

Current status (2026-10-08): implementation resumed by the owner's explicit
instruction. Package A, committed Child cause, is complete at its bounded Linux /
Rust 1.77.2 acceptance scope after five cumulative native allocations. Attempt 5
passed four intended baseline/mutant RED controls and both restored GREEN controls
in one archive. The production fix is present at the exact tested source hash
`d4fc28906b624f6e9368d0bef16e82e3fc29cada5142da67406fd95962153115`; the combined
independent review returned READY with no material code findings. A review of
attempt 4 had found that its process-identity observation could occur after child
exit; attempt 5 added and proved a live-identity acknowledgment before
cancellation. The 71 preserved originals were independently read back. The runner
removed its private runtime and scope after exporting evidence; the collector then
validated/exported the originals and retired the exact Workhorse stage. A fresh
closure afterward verified 113 process identities, five groups and six paths
absent. No compiled build is reusable.
The accepted evidence is under
`../.scratch/all-tickets/process-first-cause-evidence/attempt-05/originals/`;
attempt-4 evidence remains preserved as historical corroboration. Packages B–F,
the remaining ticket criteria, integrated platform acceptance and release closure
remain open; no full ticket or release completion is claimed.

On 2026-10-09, Ticket 03's separate pending-byte `Ok(0)` branch gained a
meaningful injected RED/GREEN and combined independent review. The helper now
maps zero progress to `io::ErrorKind::WriteZero`; the existing spawned-child
error path retains the cause and requests cleanup. Darwin arm64/macOS 27.0.0,
Rust/Cargo 1.77.2, `testing-environ,sys`: the exact library unit test passed
1/1 after its pre-fix assertion failed. This is deliberately injected writer
evidence, not a claim that a native pipe reliably returns `Ok(0)` or that the
full macOS stdin contract passed. Source SHA-256 is
`7abd009fcccf9ad81a5a60de4c5978177243c66c3a73118d44aa99b1bcdcc234`; pinned
lock SHA-256 is `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
RED/GREEN logs and classification are in
`../.scratch/all-tickets/writezero-unit-20261009T2025Z/`. The combined
Standards/Spec review passed. The real Linux BrokenPipe row above remains a
separate accepted criterion. After the source change, the unfiltered
`sys_process` target was rerun on Workhorse Linux x86_64 at integrated commit
`0c6c51b98f57cb2e3ca3c8a56a64ea84f93981e3`, Rust/Cargo 1.77.2,
`testing-environ,sys`; 60 passed, 0 failed, 3 ignored, including the real
public-Engine BrokenPipe regression. Its raw log and fresh run metadata were
hash-read after export, and the exact scope was retired. Details are appended
to `../.scratch/all-tickets/writezero-unit-20261009T2025Z/proof.md`. Remaining
Ticket 03 and A–F work is open.

The same unfiltered `sys_process` target also passed on native Darwin arm64,
macOS 27.0.0, Rust/Cargo 1.77.2, `testing-environ,sys` at source commit
`8da9a8750e38709551a6db31736cc869a60fc3f5`: 48 passed, 0 failed, 1 ignored.
This includes the public blocked-stdin/spawn snapshot regression. The actual
early-close/BrokenPipe fixture is Linux-only, so native Darwin stdin-error
acceptance remains open. Its log and run metadata are in the same proof folder.

Ticket 03 X4–X6 now have partial acceptance for Linux x86_64/Rust 1.93.0 with
`testing-environ,sys`: a public Engine `run` integration test independently reads
the child's NUL-delimited argv record, verifies literal spaces/quotes/metacharacters
and a trailing empty argument, confirms the command-substitution marker is absent,
and checks direct-child reaping. The assertion-sensitivity RED and restored GREEN,
source/lock identities and exported Workhorse logs are recorded in
`../.scratch/all-tickets/process-argv-evidence/attempt-01/proof.md`. Other OS,
MSRV and feature rows remain open, as do unrelated Ticket 03 requirements.

Ticket 03 X11 is also partially accepted for Linux x86_64/Rust 1.93.0 with
`testing-environ,sys`. Its public `run` test, sensitivity control, child
readback and reaping proof are recorded in
`../.scratch/all-tickets/process-env-remove-evidence/attempt-01/proof.md`; commit
`e234e3e13f617def5670f16e81c5e7a60f7334ba` was the fork `main` head before the
X14/X16/X17 package commit.
Ticket 03 X14/X16/X17 have partial acceptance for Workhorse Linux x86_64 and
Darwin arm64/macOS 27.0.1 (kernel 27.0.0), both with Rust/Cargo 1.93.0 and
`testing-environ,sys`. The public Engine tests prove ordinary successful `run`
with empty stdout/stderr, exact string stdin through `run`, and an exact 1 MiB
Blob round-trip through `run_raw` while the child concurrently writes 256 KiB to
each captured stream. Child-written readback and direct-child reaping are
asserted independently. The Linux wrong-expectation controls are reused for the
byte-identical Darwin test functions/helper; the combined review confirmed this
transfer is applicable. Linux evidence is in
`../.scratch/all-tickets/process-io-contract-evidence/attempt-01/proof.md`;
Darwin's run, cleanup readback and READY review are in
`../.scratch/all-tickets/darwin-io-contracts-20261008/attempt-01/proof.md`.
Other OS, MSRV, feature and unrelated Ticket 03 rows remain open.

Ticket 03 X24 is partially accepted for Workhorse Linux x86_64, Rust/Cargo
1.93.0 and 1.77.2, and `testing-environ,sys`; the combined review is READY.
Attempt 01 remains partial because `wait()` preceded the terminal `try_wait()`;
attempt 02 stopped before Cargo on a helper identity check. Attempt 03 passed
the direct post-exit observation and an exact assertion sensitivity control,
with independent PID/reaping readback; attempt 04 adds the exact Rust/Cargo
1.77.2 GREEN row. Preserve the attempt records under
`../.scratch/all-tickets/process-try-wait-evidence/x24-try-wait-20261007-1705z-6a92d/`.
Other OS, MSRV, feature and unrelated Ticket 03 rows remain open.

On 2026-10-09 the combined X24 review additionally accepted Linux x86_64
Rust/Cargo1.77.2 profiles `testing-environ,sys,sync`, `sys,no_float`,
`sys,sync,no_float`, and `sys,only_i32,no_float`, with exact assertion RED/restored
GREEN and independent PID readback. The same review accepts native Darwin arm64/macOS
27.0.1, Rust/Cargo1.77.2, `testing-environ,sys` and `testing-environ,sys,sync`,
also with RED/GREEN and exact PID readback. The first Linux standard row remains
reused from attempt04; it was not rerun. Full X24, other Darwin profiles, Windows,
and unrelated Ticket03 rows remain open. Proof and combined review: `../.scratch/rhai-wayfinder-replan-20261008/results/linux-x24-features-20261009T1729Z/`.

Historical status: decisions D1 to D12 accepted on 2026-09-29; phase 1 implemented on branch
`claude/vibrant-sagan-3g1pxn` (this fork only, no upstream submission yet). Supersedes the
2026-09-29 precedents survey; that survey is condensed into Appendix A.

Review update (2026-09-30): phase 1 is implemented but not accepted under the new
strict verification contract. Four filesystem/fixture findings remain open. The
owner-approved [path contract](../.scratch/stdlib-wayfinder/issues/02-filesystem-contract.md#answer)
clarifies required behavior; historical implementation notes below are not proof
that those requirements pass.

The package gives Rhai scripts access to the host filesystem, environment, and child
processes. The host decides how much authority a script gets. Nothing in this package is
enabled by default.

## 1. Goal and non-goals

Goal for the first release (v0.1 of the package, gated behind the `sys` cargo feature):

- Environment: read variables and the working directory.
- Filesystem: whole-file read and write, directory listing and mutation, metadata.
- Processes: run a program to completion with captured output, or spawn it and wait, with
  timeout, output cap, stdin data, and kill.
- Authority: every capability above is granted by a host-built `SysConfig`; the default
  config denies everything.

Non-goals for v0.1, deferred to later phases or separate packages:

- Networking (TCP, UDP, HTTP). Separate package, separate feature, separate plan.
- Async or event-loop integration. All calls block the calling thread.
- Shell execution. No `sh -c`, no `cmd /C`, no string command lines.
- Streaming file handles. rhai-fs already provides these; v0.2 adds a compatible subset.
- Mutating the process environment (`set_var`). Process-global, unsound with threads.

## 2. Decisions

Each decision names a recommendation. Items marked "needs owner sign-off" block the next phase.

| ID | Topic | Recommendation | Rationale | Status |
|---|---|---|---|---|
| D1 | Where the code lives | In-tree at `src/packages/sys/`, behind cargo feature `sys`, not part of `StandardPackage` or the `default` feature set. | Fastest path on this fork. Extracting to a `rhai-sys` crate later is mechanical, because the package only uses the public plugin API. | accepted |
| D2 | Authority model | Host constructs `SysConfig` (fs roots, program allow-list, env policy, limits) and builds `SysPackage::new(config)`. `SysConfig::default()` denies everything; `SysConfig::permissive()` allows everything for trusted scripts. | Matches Deno's permission model and the "explicit authority" conclusion of the survey. Deny-by-default means forgetting to configure is safe. | accepted |
| D3 | Filesystem confinement | Use the `cap-std` crate. Each configured root becomes a `cap_std::fs::Dir`; script paths resolve relative to a root and cannot escape it, including via symlinks. | Hand-rolled `canonicalize` + `starts_with` checks are racy against symlink changes. `cap-std` is maintained by the Bytecode Alliance and is the reference implementation of this idea. Optional dependency, pulled only by `sys`. | accepted |
| D4 | Process API shape | Options-map style, not a builder: `run(program, args)` and `run(program, args, options)` return a result map; `spawn(program, args, options)` returns a `Child` handle. | Rhai plugin methods on `&mut T` return unit, so builder chaining does not work without cloning. An options map is idiomatic Rhai, trivially serializable, and easy to test. Rune's process module shows the builder style and its awkwardness. | accepted |
| D5 | Error model | OS and policy failures raise `EvalAltResult::ErrorRuntime` whose payload is a `SysError` value (enum: `Denied`, `Io`, `Timeout`, `OutputLimit`, `NotUtf8`) registered as a script type with getters `kind`, `message`, `io_kind`, `op`, `target`. Scripts catch it with `try`/`catch`. A non-zero exit code is data in the result map, never an error. | Mirrors Rust: `Command::output()` succeeds on non-zero exit. Hosts get the value back with `Dynamic::try_cast::<SysError>()`. Rhai's `ErrorSystem` was the first choice but the interpreter marks it uncatchable (`EvalAltResult::is_catchable`), which would defeat script-side handling; `SysError::Io` therefore stores `io::ErrorKind` plus message instead of the non-`Clone` `io::Error`. | accepted, revised during phase 1 |
| D6 | Paths | Strings in, strings out. Non-UTF-8 names raise `SysError::NotUtf8`. No opaque path type in v0.1. | Rhai strings are UTF-8, `OsString` is not. Keep the surface small; a `Path` type can come with rhai-fs compatibility in v0.2. | accepted |
| D7 | Timeout | Poll `Child::try_wait()` at a coarse interval (10 ms) until the deadline, then kill and mark `timed_out: true`. No extra thread, no extra dependency. | `std` has no `wait` with timeout. Polling is portable and adequate for script use. | accepted |
| D8 | Windows batch files | Refuse programs ending in `.bat` or `.cmd` unless the config sets `allow_batch_files`. Document MSRV 1.77.2 for the `sys` feature. | CVE-2024-24576: Windows batch arguments pass through `cmd.exe` and were injectable. `std` fixed quoting in 1.77.2; refusing by default removes the whole class. | accepted |
| D9 | Child drop semantics | `kill_on_drop: true` by default; option to disable. `Child` is `Shared<Locked<...>>` so it works under `sync`. | Scripts are short-lived and error-prone; an orphaned child outliving the script is the surprising outcome. Rust's `Child` neither kills nor reaps on drop, so the package must. | accepted |
| D10 | Feature gating | `sys` implies `std`. Combining `sys` with `no_std` or a wasm32 target is a `compile_error!`. | Nothing here can work without an OS. Failing loudly beats an empty package. | accepted |
| D11 | Output encoding | `run` returns `stdout` and `stderr` as strings, lossily converted. `run_raw` returns blobs. | Most scripts want text. Lossy conversion never fails; scripts needing bytes opt in. | accepted |
| D12 | rhai-fs compatibility | Where a v0.1 function overlaps rhai-fs (`cwd`, `exists`, `create_dir`, `remove_dir`, `remove_file`), keep the same name and argument order. Divergences are listed in the docs. | Two incompatible fs APIs in one ecosystem help nobody. | accepted |

## 3. Script-facing contract (v0.1)

Names are final only after owner review. Everything below is registered by `SysPackage`
as global functions.

### 3.1 Environment

```rhai
env_var("HOME")            // String, or () when unset or not allowed by policy
env_vars()                 // Map of every variable the policy exposes
cwd()                      // String; the process working directory
```

Policy: `EnvPolicy::None` (both functions return empty), `EnvPolicy::AllowList(names)`,
`EnvPolicy::All`.

### 3.2 Filesystem

All paths are resolved against a configured root. An absolute path must lie inside a root;
a relative path is resolved against the first root. `..` and symlinks cannot leave a root
(enforced by `cap-std`, not by string inspection). The host-configured root must
identify the directory selected by OS path resolution, preserving symlink/parent
semantics. Unrestricted mode retains ordinary host filesystem path behavior while
still enforcing the configured access level. Exact alias, traversal, symlink and
multiple-root rules and regression expectations live in the accepted
[path contract](../.scratch/stdlib-wayfinder/issues/02-filesystem-contract.md#accepted-path-contract).

```rhai
read_file(path)                  // String
read_file_blob(path)             // Blob
write_file(path, data)           // data: String or Blob; creates or truncates
append_file(path, data)
exists(path)                     // bool
is_file(path)                    // bool
is_dir(path)                     // bool
metadata(path)                   // #{ size, is_file, is_dir, is_symlink, modified, readonly }
read_dir(path)                   // Array of entry names (not full paths), sorted
create_dir(path)
create_dir_all(path)
remove_file(path)
remove_dir(path)                 // empty directories only
remove_dir_all(path)             // requires FsAccess::ReadWriteDelete
rename(from, to)                 // both inside the same root
copy_file(from, to)
```

Policy: each root carries `FsAccess::Read`, `FsAccess::ReadWrite`, or
`FsAccess::ReadWriteDelete`. A write to a read-only root raises `SysError::Denied`.

### 3.3 Processes

```rhai
let r = run("git", ["status", "--short"]);
let r = run("git", ["status"], #{
    cwd:        "/repo",          // must be inside a configured fs root
    env:        #{ GIT_PAGER: "cat" },
    env_clear:  true,             // start from an empty environment
    env_remove: ["GIT_DIR"],
    stdin:      "input text",     // String or Blob; () closes stdin
    timeout:    5.0,              // seconds; () means none
    max_output: 1_000_000,        // bytes per stream; exceeding it raises SysError::OutputLimit
});
r.success       // bool: code == 0
r.code          // int, or () when killed by a signal (Unix) or timed out
r.signal        // int on Unix when signaled, else ()
r.timed_out     // bool
r.stdout_complete // bool: stdout reached EOF before the run returned
r.stderr_complete // bool: stderr reached EOF before the run returned
r.stdout        // String (lossy UTF-8)
r.stderr        // String
```

`run_raw` takes the same arguments and returns `stdout` and `stderr` as blobs.

```rhai
let c = spawn("long-task", [], #{ stdin: "..." });   // same options minus timeout
c.id            // int
c.try_wait()    // () while running, else the result map above
c.wait()        // blocks; result map
c.wait(10.0)    // blocks up to 10 s; () on timeout
c.kill()        // best effort; idempotent
```

Policy: `ProgramPolicy::None`, `ProgramPolicy::AllowList(names)`, `ProgramPolicy::Any`.
Names in the allow-list are compared against the program string as given; the config may
also pin absolute paths. `cwd` is validated against the fs roots. Arguments are always passed
as a vector, never through a shell.

The initial release also includes host-selected managed process groups/jobs,
alongside direct-child supervision. Managed mode terminates associated workers on
cancellation and closes its task scope at normal completion. Scripts cannot downgrade
host-required supervision; unavailable scope setup fails explicitly. This does not
sandbox file/network access or guarantee termination of escaped descendants.
The precise lifecycle, diagnostics and native acceptance contract is recorded in
[process contract](../.scratch/stdlib-wayfinder/issues/03-process-contract.md#answer).
Configuration spelling and Rust error compatibility remain API-review work.

### 3.4 Host API

```rust
let cfg = SysConfig::default()
    .fs_root("/srv/app/data", FsAccess::ReadWrite)
    .programs(ProgramPolicy::AllowList(vec!["git".into(), "ffmpeg".into()]))
    .env(EnvPolicy::AllowList(vec!["HOME".into(), "PATH".into()]))
    .default_timeout(Some(30.0))
    .max_output(8 * 1024 * 1024)
    .kill_on_drop(true);

let mut engine = Engine::new();
engine.register_global_module(SysPackage::new(cfg).as_shared_module());
```

Errors are values: a caught `SysError` prints as its message, and `type_of(err)` is
`"SysError"`.

```rhai
try {
    read_file("missing.txt");
} catch (err) {
    if err.kind == "Io" && err.io_kind == "NotFound" { /* ... */ }
}
```

## 4. Requirements and test matrix

Every row becomes at least one test. "Source" names the precedent that motivated the case;
tests are written from scratch against this contract. Phase numbers refer to section 6.

### 4.1 Policy (P)

| ID | Case | Expected | Source | Phase |
|---|---|---|---|---|
| P1 | Default config, any fs call | `SysError::Denied` | Deno permissions | 1 |
| P2 | Default config, `run` | `SysError::Denied` | Deno | 2 The reviewed Linux package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/linux-process-minimum-20261008T201200Z-6e2ba1d7/proof.md` additionally accepts this exact public-Engine assertion at Rust/Cargo1.77.2, `testing-environ,sys`, with unchanged oracles, reused original RED controls and fresh native GREEN/readback/reap. Other uncovered native/feature rows remain open. |
| P3 | Read on read-only root | succeeds | own | 1 |
| P4 | Write on read-only root | `Denied` | own | 1 |
| P5 | `remove_dir_all` on `ReadWrite` root | `Denied`; needs `ReadWriteDelete` | own | 1 |
| P6 | Path with `..` escaping root | `Denied`, and no fs access happened | cap-std, Lua `files.lua` | 1 |
| P7 | Symlink inside root pointing outside | `Denied` | cap-std | 1 |
| P8 | Absolute path inside root | resolves | own | 1 |
| P9 | Absolute path outside any root | `Denied` | own | 1 |
| P10 | Program not in allow-list | `Denied` before spawn | Deno `--allow-run` | 2 The reviewed Linux package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/linux-process-minimum-20261008T201200Z-6e2ba1d7/proof.md` additionally accepts this exact public-Engine assertion at Rust/Cargo1.77.2, `testing-environ,sys`, with unchanged oracles, reused original RED controls and fresh native GREEN/readback/reap. Other uncovered native/feature rows remain open. |
| P11 | `cwd` option outside fs roots | `Denied` | own | 2 |
| P12 | `env_var` not in allow-list | `()` | own | 1 |
| P13 | `.bat` / `.cmd` program on Windows, default config | `Denied` | CVE-2024-24576 | 3 |
| P14 | Host root contains symlink followed by `..` | OS-selected root only; lexical substitute untouched | review regression | phase 1 repair |

### 4.2 Environment (E)

| ID | Case | Expected | Source | Phase |
|---|---|---|---|---|
| E1 | Variable set in parent | returned | Lua `os.getenv` | 1 |
| E2 | Variable unset | `()` | Lua | 1 |
| E3 | `env_vars()` under `All` | contains a known variable | QuickJS `std.getenviron` | 1 |
| E4 | Non-UTF-8 variable value (Unix only) | `NotUtf8` or skipped in `env_vars`, documented | own | 3 |
| E5 | `cwd()` | equals `std::env::current_dir()` | rhai-fs `cwd` | 1 |

### 4.3 Filesystem (F)

| ID | Case | Expected | Source | Phase |
|---|---|---|---|---|
| F1 | Read existing text file | content | Lua `files.lua` | 1 |
| F2 | Read missing file | `Io` with `NotFound` kind, message includes path | Lua | 1 |
| F3 | Read empty file | `""` | Lua | 1 |
| F4 | Read binary file as string | lossy replacement chars; `read_file_blob` exact | Lua | 1 |
| F5 | Read large file (8 MiB) | exact round trip | own | 1 |
| F6 | Write then read | round trip; write truncates existing content | Lua | 1 |
| F7 | Append twice | concatenated | Lua | 1 |
| F8 | Write blob | bytes exact | rhai-fs `write_to_file` | 1 |
| F9 | Write into missing parent directory | `Io`, no partial file | Lua | 1 |
| F10 | `exists` / `is_file` / `is_dir` | correct on file, dir, missing | rhai-fs getters | 1 |
| F11 | `metadata` on file | size matches, `is_file` true | QuickJS `os.stat` | 1 |
| F12 | `read_dir` | sorted names, no `.`/`..`, no path prefix | mruby-io `Dir` | 1 |
| F13 | `read_dir` on a file | `Io` | Lua | 1 |
| F14 | `create_dir` when parent missing | `Io`; `create_dir_all` succeeds | QuickJS `os.mkdir` | 1 |
| F15 | `remove_dir` on non-empty dir | `Io`; `remove_dir_all` succeeds under `ReadWriteDelete` | Lua `os.remove` | 1 |
| F16 | `rename` across roots | `Denied` | own | 1 |
| F17 | `copy_file` | content equal, source untouched | own | 1 |
| F18 | Unicode filename | round trip | own | 1 |
| F19 | Non-UTF-8 filename in `read_dir` (Unix) | `NotUtf8` | own | 3 |
| F20 | Windows path with forward slashes | works | own | 3 |
| F21 | Windows reserved name (`CON`) | `Io`, does not hang | own | 3 |
| F22 | Unrestricted absolute/sibling-relative symlinks and symlink/parent paths | Corresponding host operation semantics; grants still enforced | review regression | phase 1 repair |
| F23 | Supported configured/canonical/macOS-prefix spellings of a root | Same authority and payload; no permission fallback | review regression | phase 1 repair |

### 4.4 Processes (X)

| ID | Case | Expected | Source | Phase |
|---|---|---|---|---|
| X1 | Program found, exit 0 | `success`, `code == 0` | all | 2 |
| X2 | Program not found | `Io` with `NotFound`, before any child exists | Lua, QuickJS | 2 The reviewed Linux package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/linux-process-minimum-20261008T201200Z-6e2ba1d7/proof.md` additionally accepts this exact public-Engine assertion at Rust/Cargo1.77.2, `testing-environ,sys`, with unchanged oracles, reused original RED controls and fresh native GREEN/readback/reap. Other uncovered native/feature rows remain open. |
| X3 | Exit code non-zero | `success == false`, `code == N`, no error raised | Rust `Command::output` | 2 |
| X4 | Arguments with spaces and quotes | fixture echoes argv exactly | Deno, Rust std tests | 2 The reviewed Linux package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/linux-process-minimum-20261008T201200Z-6e2ba1d7/proof.md` additionally accepts this exact public-Engine assertion at Rust/Cargo1.77.2, `testing-environ,sys`, with unchanged oracles, reused original RED controls and fresh native GREEN/readback/reap. Other uncovered native/feature rows remain open. |
| X5 | Argument containing `$HOME`, `|`, `;`, `&&` | passed literally, fixture sees the raw string | Lua `os.execute` (counter-example) | 2 The reviewed Linux package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/linux-process-minimum-20261008T201200Z-6e2ba1d7/proof.md` additionally accepts this exact public-Engine assertion at Rust/Cargo1.77.2, `testing-environ,sys`, with unchanged oracles, reused original RED controls and fresh native GREEN/readback/reap. Other uncovered native/feature rows remain open. |
| X6 | Empty argument `""` | preserved as an empty argv entry | Rust std tests | 2 The reviewed Linux package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/linux-process-minimum-20261008T201200Z-6e2ba1d7/proof.md` additionally accepts this exact public-Engine assertion at Rust/Cargo1.77.2, `testing-environ,sys`, with unchanged oracles, reused original RED controls and fresh native GREEN/readback/reap. Other uncovered native/feature rows remain open. |
| X7 | `cwd` option valid | fixture reports that directory | QuickJS `os.exec` | 2 |
| X8 | `cwd` option missing directory | `Io`, no child spawned | QuickJS | 2 The reviewed Linux package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/linux-process-minimum-20261008T201200Z-6e2ba1d7/proof.md` additionally accepts this exact public-Engine assertion at Rust/Cargo1.77.2, `testing-environ,sys`, with unchanged oracles, reused original RED controls and fresh native GREEN/readback/reap. Other uncovered native/feature rows remain open. |
| X9 | `env` override | fixture sees the value | QuickJS | 2 |
| X10 | `env_clear` | fixture sees only overrides | Rust `env_clear` | 2 |
| X11 | `env_remove` | fixture does not see the variable | Rust `env_remove` | 2 The reviewed Linux package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/linux-process-minimum-20261008T201200Z-6e2ba1d7/proof.md` additionally accepts this exact public-Engine assertion at Rust/Cargo1.77.2, `testing-environ,sys`, with unchanged oracles, reused original RED controls and fresh native GREEN/readback/reap. Other uncovered native/feature rows remain open. |
| X12 | stdout and stderr separate | each captured on its own | QuickJS | 2 |
| X13 | Both streams write 4 MiB interleaved | no deadlock, both complete | Rust `output()` uses concurrent reads | 2 |
| X14 | Empty output | `""` | Lua | 2 |
| X15 | Binary output | `run_raw` exact bytes; `run` lossy | own | 2 |
| X16 | stdin string | fixture echoes it back | QuickJS pipes | 2 |
| X17 | stdin blob 1 MiB | exact round trip, no deadlock while child also writes | own | 2 |
| X18 | stdin `()` | fixture sees EOF immediately | own | 2 |
| X19 | Timeout expires | `timed_out == true`, termination/reaping observed; watchdog bounds the test; OS latency limitations documented | own | 2 |
| X20 | Timeout not reached | normal result | own | 2 |
| X21 | `max_output` exceeded | `OutputLimit`, child killed | survey "output cap" | 2 |
| X22 | Child killed by signal (Unix) | `code == ()`, `signal == 9` | Rust `ExitStatusExt` | 2 |
| X23 | `spawn` then `wait` | same result map as `run` | Rune process | 2 |
| X24 | `spawn` then `try_wait` while running | `()`; after exit, result | Rune | 2 |
| X25 | `spawn` then `kill` then `wait` | terminated, no hang | Rune | 2 |
| X26 | `kill` twice | second is a no-op, no error | own | 2 |
| X27 | Drop `Child` while running, `kill_on_drop` true | child exits (Linux: verify via `/proc`), no zombie | own | 2 |
| X28 | Drop `Child`, `kill_on_drop` false | child keeps running; retained supervisor eventually reaps it | own | 2 |
| X29 | Script `throw` while child running | child cleaned up via drop | own | 2 |
| X30 | 200 sequential `run` calls | no fd or handle leak (Linux: `/proc/self/fd` count stable) | Lua cleanup tests | 2 |
| X31 | Under `sync` feature, `Child` shared across threads | compiles and works | Rhai `sync` | 2 |
| X32 | Windows: argument with embedded quote | argv reconstructed correctly | Rust std quoting rules | 3 |
| X33 | Windows: `.exe` suffix omitted | resolves via `PATH` | own | 3 |

| X34 | Managed scope cancellation | associated child/grandchild workers stop on timeout, overflow, kill and final drop; independent observations | process contract | 2 |
| X35 | Managed main process exits before workers | owned task scope closes before final result; direct mode remains distinct | process contract | 2 |
| X36 | Managed scope setup fails | no unmanaged work or silent fallback; partial setup cleaned up | process contract | 2 |
| X37 | Host group/job and unrelated sentinel | owned scope cleanup leaves host and sentinel intact | process contract | 2 |
| X38 | Descendant retains pipe or escapes membership | capture cancellation completes; membership limitation explicit; fixture owns escapee cleanup | process contract | 2 |

### 4.5 Engine integration (R)

| ID | Case | Expected | Source | Phase |
|---|---|---|---|---|
| R1 | `sys` off | no symbols exported, no dependency compiled | Rhai feature conventions | 1 |
| R2 | `sys` + `no_std` | `compile_error!` | D10 | 1 |
| R3 | `sys` + `no_index` | `run` without args still works; array-taking overloads absent | Rhai cfg conventions | 2 |
| R4 | `sys` + `no_object` | incompatible; explicit `compile_error!` | accepted D10 and ticket06 | 2 |
| R5 | `type_of` on `Child` | `"Child"` | Rhai time tests | 2 |
| R6 | `metadata` feature | doc-comments on every function render | Rhai conventions | 4 |
| R7 | `try { ... } catch (e)` around a denied call | `e` is a `SysError`; `e.kind` is the variant name, `e.message` starts with it, `e.io_kind` names the `io::ErrorKind` for I/O errors, and the script continues after the catch | D5 | 1 |

## 5. Test infrastructure

The fixture design is retained. Earlier Wine/install and CI proposals below are
historical; the native, no-install and disabled-Actions constraints in the accepted
release contract and current section6 govern future execution.

- Files: `tests/sys_policy.rs`, `tests/sys_env.rs`, `tests/sys_fs.rs`, `tests/sys_process.rs`,
  each starting with `#![cfg(feature = "sys")]`, following the existing `tests/time.rs` style.
- Fixture process: no separate binary. The process test binary re-executes itself via
  `std::env::current_exe()` with `--exact sys_fixture_entry --nocapture` and an environment
  variable `RHAI_SYS_FIXTURE=<mode>`. The `sys_fixture_entry` test function checks that variable
  and, when set, behaves as the fixture (echo argv as JSON lines, echo stdin, print env, write
  N bytes to both streams, sleep, exit with a code, or raise a signal on Unix) and exits. When
  the variable is unset it returns immediately, so normal test runs are unaffected. This is the
  pattern Rust's own `std::process` tests and `assert_cmd` use; it works under plain
  `cargo test` on every platform.
- Temporary directories: `std::env::temp_dir()` joined with the crate name, process id and an
  atomic counter. Cleaned up by a guard struct on drop. No `tempfile` dependency.
- Platform gating: Unix-only rows use `#[cfg(unix)]`, Windows-only rows `#[cfg(windows)]`.
  Every row runs on at least one CI OS.
- Windows without a Windows machine: the suite runs under Wine. Verified on 2026-09-29 with
  Wine 9 on Linux: 43 of 43 tests pass, the same as natively on Linux. Wine needs a UTF-8
  locale, otherwise non-ASCII file names fail with `NotFound`.

  ```bash
  rustup target add x86_64-pc-windows-gnu
  apt-get install -y --no-install-recommends wine64 gcc-mingw-w64-x86-64
  export WINEDEBUG=-all WINEPREFIX=/tmp/rhai-wine LANG=C.UTF-8 LC_ALL=C.UTF-8
  cargo test --features testing-environ,sys --target x86_64-pc-windows-gnu --no-run \
      --test sys_policy --test sys_env --test sys_fs
  for exe in target/x86_64-pc-windows-gnu/debug/deps/sys_*.exe; do wine64 "$exe"; done
  ```

  Wine is a check, not proof: quoting of process arguments and `cmd.exe` behaviour in
  phase 2 and 3 still need one run on real Windows via the CI matrix.
- CI: `.github/workflows/build.yml` gains matrix rows
  `--features testing-environ,sys` and `--features testing-environ,sys,sync,no_index` on
  ubuntu, plus `--features sys` on the existing windows and macos jobs. The wasm32 rows
  must not include `sys`.

## 6. Remaining acceptance plan — revised 2026-10-08

**Current execution plan.** The owner explicitly resumed implementation after this
plan was revised. Package A is complete at its recorded Linux/Rust 1.77.2 scope
after attempt 5 closed the live-child identity gap found in review of attempt 4;
Package B remains open after its documented infrastructure stops, with its
criterion map complete. Package E's Workhorse/native3 route remains stopped after
three pre-assertion infrastructure failures and its exhausted follow-up. A separate
bounded Darwin run passes the current sys/net metadata assertions and real
process-example readbacks. Public API documentation is now updated; after a reviewer
found the timed `Child.wait` comments omitted unit-on-timeout and non-cancellation,
the targeted sys metadata assertion passed in both default-float and `no_float`
profiles. The combined package review returned READY after rechecking the
corrected comments, assertions, evidence and docs. Package E is integrated at
fork main `04d9a797...`. The two Darwin system-prefix alias assertions are
reviewed and integrated at `ad980d80...`; this closes only those F23 subcriteria.
Packages B, C, D, F and release acceptance remain open. The remaining F23
root-spelling behavior is reviewed on native Darwin through the complete
`sys_policy` target: expected-RED sensitivity control, then 26/26 passing tests
with five root-path cases at `ad980d80...`. This closes only the macOS sys-policy
slice of F23, not the other platform/feature rows or Package C. The direct Darwin
combined sys/net target now passes at source `055a068...`: locked metadata and the
expected-RED assertion are preserved in attempt 01, and the green run passed 1/1
in attempt 02. Its initial wrapper stopped on Rust's multiline failure formatting,
not a product assertion. The combined independent review returned READY on 2026-10-08. This closes only one
`testing-environ,sys,net` coexistence slice; Package C remains open for native
process/lifecycle behavior and remaining OS/feature rows. Darwin X25 now has one
reviewed managed-spawn/kill/wait row. X26's repeat-kill row and X27's direct-child
final-drop row are also reviewed at arm64/macOS 27.0.1 with Rust/Cargo 1.93.0;
their managed final-drop reference is explicitly historical at e5b55460… / macOS
27.0. Existing full-suite evidence also contains both X28 `kill_on_drop=false`
cases at that older source and environment. Combined review confirmed the
relevant lease-drop logic and tests/helpers remain applicable through d3281a7;
reuse the historical named rows without claiming a fresh macOS 27.0.1 execution.
The exact X29 Darwin lifecycle test produced the intended RED and passed GREEN
on native arm64/macOS 27.0.1 with Rust/Cargo 1.93.0. Its combined independent
review returned READY and confirmed the fixture overlay preserves the committed
X29 behavior. The named Linux and Darwin X29 rows are accepted; Windows, other
OS, feature and MSRV rows remain open. This section is the single current plan;
the campaign state records evidence and ownership. Historical estimates do not
allocate retries or certify completion.

**Accepted partial criterion: X28, Darwin `unchecked`.** On Darwin arm64/macOS
27.0.1 with Rust/Cargo 1.77.2 and `testing-environ,sys,unchecked`, the public
Engine test `direct_spawn_kill_on_drop_false_preserves_child_and_capture` passed
with an assertion-sensitivity RED and restored GREEN. After dropping the final
client handle and Engine, the child remained alive, acknowledged an independent
challenge, completed 524288-byte stdout and stderr writes, and was independently
observed absent after natural exit. The exceptional cleanup guard also passed an
inverted-assertion RED after verifying exact process identity, issuing SIGKILL,
and reading ESRCH. Current source, mutant and lock hashes plus raw logs are in
`../.scratch/all-tickets/darwin-drop-false-unchecked-20261009/attempt-06.md` and
its attempt directory; combined independent review passed. Other X28 platforms
and feature profiles, and the remaining Ticket 03 criteria, remain open.

**Accepted partial criterion: X29, Darwin `unchecked`.** The exact
`script_throw_drops_and_reaps_a_live_child` public-Engine contract passed on
arm64/macOS 27.0.1 with Rust/Cargo 1.77.2 and `testing-environ,sys,unchecked`.
It exercised a live child through a Rhai throw, rejected a wrong-message
expectation, and independently verified controller/fixture ESRCH plus watchdog
closure. Cargo status was 0 and the scoped runtime/scope were retired. The outer
runner exit code is explicitly unknown because zsh bookkeeping failed after the
test; this is recorded without inferring it from Cargo's result. Raw evidence,
hashes and combined review are in
`../.scratch/all-tickets/darwin-x29-unchecked-20261009/attempt-01.md`. Other X29
platform, feature and toolchain rows remain open.

**Accepted partial criteria: X28/X29, Darwin base features.** One shared scoped
build and lock ran `direct_spawn_kill_on_drop_false_preserves_child_and_capture`
and `script_throw_drops_and_reaps_a_live_child`, each 1/1, on Darwin
arm64/macOS 27.0.1 with Rust/Cargo 1.77.2 and `testing-environ,sys`. X28 confirms
post-drop live-child challenge, complete 524288-byte capture on each stream and
natural exact-PID ESRCH. Its matching RED and exceptional cleanup control are
reused from the reviewed unchecked attempt because the source/assertion/guard
are byte-identical and not feature-gated. X29 confirms the live-child throw,
wrong-message control, independent controller/fixture ESRCH and watchdog
closure. Combined review, hashes, outputs and exact scope retirement are recorded
in `../.scratch/all-tickets/darwin-process-lifecycle-base-20261009/attempt-01.md`.
These are named partial rows only.

**Accepted partial criteria: X26/X27, Darwin base features.** One shared scoped
Rust/Cargo 1.77.2 build ran `spawn_returns_while_large_stdin_is_blocked_and_wait_snapshots_are_stable`
and `nonfinal_child_clone_drop_keeps_the_real_child_available`, each 1/1, on
arm64/macOS 27.0.1 with `testing-environ,sys`. X26 independently records exit
code 17, stable cached snapshots, two post-completion kills and ESRCH. X27
records operational nonfinal clone use followed by final `kill_on_drop=true`
termination and controller/fixture/watchdog ESRCH. Combined review reused the
Darwin 1.93 RED controls because their mutation targets, fixture and applicable
process path remain unchanged. Evidence and exact scope cleanup:
`../.scratch/all-tickets/darwin-child-drop-20261009/attempt-01.md`. These named
rows do not cover managed final-drop, other platforms or the full matrix.

**Accepted partial criterion: X30, Linux descriptor stability.** The real entry is
`tests/sys_process.rs::repeated_public_run_calls_keep_fd_count_stable`: the
ordinary acceptance test launches the ignored census test by exact name in a
fresh child process, isolating its process-wide descriptor census from other
integration tests. The child uses public Rhai `Engine::eval` to run `/bin/true`
200 times after one warm-up and compares its OS `/proc/self/fd` census before
and after. The exact command is
`cargo +1.93.0 test --locked --features testing-environ,sys --test sys_process repeated_public_run_calls_keep_fd_count_stable -- --exact --nocapture --test-threads=1`.
This is independent of the exhausted Package B and E routes and needs no shared
service. The first run initializes the persistent package cleanup worker before
the baseline. The parent test gives the isolated child a 60-second deadline,
captures stdout/stderr in temporary files, and on timeout kills its process
group, kills and reaps the direct child, and includes captured output in the
failure. On 2026-10-07 attempt 06, a wrong expected descriptor count failed at
the X30 assertion inside the isolated child, then the restored source passed
all 200 calls. The independent `/proc/self/fd` census read back four
descriptors both before and after; task and cleanup-worker counts also returned
to baseline. A combined review on 2026-10-08 confirms this proof remains
applicable at source revision `c644085ccf65160bd3d39f5353e8b933310ffe03`:
the X30 acceptance and census helpers are unchanged. `run_map` now adds
Managed-scope fault setup and takes fault state earlier; this test uses default
DirectChild scope, no injected fault and no custom cwd, so those changes do not
alter its descriptor path. This closes only the Linux x86_64, Rust/Cargo 1.93.0,
`testing-environ,sys` row. Other X30 matrix rows and Ticket 03 remain open. No
product correction or duplicate run was needed. The bounded run took
31.534 seconds of aggregate Cargo time; periodic samples observed up to four
owned processes, 910,152 KiB RSS, and 1,284,764 KiB private storage (not
continuous peaks), with no sampler retry. The canonical scoped runner followed
fresh Workhorse source/toolchain, active-slot and actual filesystem capacity
checks. All nine test-output hashes and 21 staged/exported file hashes matched
the Workhorse readback. The private runtime and exact owned scope were removed;
no private Cargo build is reusable.


**Native f32 process addendum (combined review READY, 2026-10-08).**
Darwin arm64 and Linux x86_64, Rust1.77.2,
`testing-environ,sys,net,f32_float`, accept the exact public Engine process test
`f32_process_timeouts_validate_before_launch_and_preserve_host_output_bounds`.
Five invalid duration values are denied before child effects; a finite fractional
timeout completes a real child normally; script4096 cannot raise the host4-byte
output cap. Fresh child records, exact bounded output and ESRCH reaping support
the result. Each OS has one intended equality-assertion RED101 and restored
GREEN0 with exact source/lock/profile bindings. Original export and owned scope
retirement are recorded in
[the f32 proof](../.scratch/rhai-wayfinder-replan-20261008/results/f32-process-20261008T162316Z-515571ed/proof.md).
Existing actual Condvar-entry X31 proofs remain applicable at unchanged Unix
backend bytes; a newer before-call fixture pass does not establish wait entry
or invalidate those original rows. These are narrow accepted rows; Windows,
unselected lifecycle/fault/profile work and integrated A–F closure remain open.

**Additional native result: X31, Linux blocking wait (combined review READY 2026-10-08).**
The accepted shared-Child proof above covers three named Rust/Cargo 1.77.2
feature rows, but its synchronization signal precedes the public wait call. A
separately retained Workhorse proof adds Linux x86_64 blocking-entry rows at
Rust/Cargo 1.77.2 for `testing-environ,sys,sync` and
`testing-environ,sys,sync,no_float`. Both profiles have the expected assertion
RED for a deliberately wrong wait-entry condition and a restored GREEN with one
passing test. They observe wait entry, a nonterminal child at cancellation,
waiter wakeup and exact-PID `ESRCH`; the compatible lock, restored test bytes,
toolchain and process identities are retained in
`../.scratch/all-tickets/linux-wait-entry-evidence-88/`; its inner
`package-result.json` left `acceptance_claim:false` pending an independent
cleanup readback. The outer evidence at
`../.scratch/all-tickets/linux-wait-entry-outer-evidence-88/` records exact PID,
scope and runtime cleanup, closing that dependency. The combined
current-source review returned READY, as recorded in
`../.scratch/all-tickets/linux-wait-entry-proof.md` and
`../.scratch/all-tickets/linux-wait-entry-review.md`: the blocking-entry test
function is byte-identical at its captured source
`08507d6831f73f28aa0b95a4255c5df8ebe2ec13`
and `c644085ccf65160bd3d39f5353e8b933310ffe03`, and the intervening production
deltas do not change the exercised wait/kill behavior.

On 2026-10-08, the current
`src/packages/sys/process/unix.rs::tests::public_wait_is_cancelled_after_entering_condvar`
test also passed on Workhorse Linux x86_64 with Rust/Cargo 1.97.1 and
`testing-environ,sys,sync`. It evaluates Rhai `spawn`, `wait`, and `kill` with a
real shell child held on a FIFO. The test observes the wait-entry counter and
reacquires the child snapshot mutex while the independently recorded child is
still nonterminal, confirming the waiter reached `Condvar::wait` before public
cancellation; the waiter wakes and the exact PID is independently confirmed
reaped with `ESRCH`. The retained compatible lock passed full
`cargo metadata --locked` against the current manifest before the test. Full
output, hashes, toolchain, resource measurements and cleanup readback are in
`../.scratch/all-tickets/linux-shared-child-evidence-87/blocking-entry-current/`.
These results add only the two Rust/Cargo 1.77.2 profiles above and the Linux
x86_64 Rust/Cargo 1.97.1 `testing-environ,sys,sync` blocking-entry row. Other
OS, MSRV and feature rows remain open; no product change or repeat of the
existing shared-child matrix was needed.

**X24 attempt 01 — partial historical evidence.** The test
`tests/sys_process.rs::direct_spawn_try_wait_returns_unit_until_child_exits`
started a real child through the public Rhai `spawn` API, matched the child PID
to its readiness record, verified it remained alive while `try_wait()` returned
unit, and later read a successful exit and reaping. Its test order called
`wait()` before terminal `try_wait()`, however, so `wait()` could have consumed
the exit and populated the cached snapshot. This run therefore did not establish
that `try_wait()` itself observes natural exit. The original RED/GREEN logs,
source identities, Workhorse export readback, nine case-output hashes and exact
scope-cleanup receipt remain valid for the pending-state observation only at
`../.scratch/all-tickets/process-try-wait-evidence/x24-try-wait-20261007-1705z-6a92d/attempt-01/`.

The focused test polls public `Child.try_wait()` after opening the release gate,
requires its non-unit exit map before any `wait()` call, validates code 0 and
success, and then confirms `wait()` returns the cached result and the exact PID
is reaped. Attempt 02 stopped before Cargo because its helper compared the
modified test overlay (`7ddc87f6…d14017`) with the immutable archive's baseline
test member (`166efccd…1013`); the frozen manifest confirms those are distinct
identities. The corrected helper checks the archive member against its frozen
per-file hash, then checks the replacement overlay separately. Attempt 03 reused
only the unchanged byte-verified source archive and accepted Cargo lock, not the
deleted private build. Its expected assertion RED reached the intended direct
post-exit assertion (exit 101), then restored GREEN passed (exit 0). The result
records PID 1760685 alive while pending, unit from pending `try_wait`, exit code
0 directly observed by terminal `try_wait()` before `wait()`, `wait()` returning
the cached result, and exact-PID ESRCH reaping. All nine proof-output hashes
matched local readback; the eight attempt-03 stage files other than its unpinned
staging note matched the stage. The remote 250-byte note is preserved at
`../.scratch/all-tickets/process-try-wait-evidence/x24-try-wait-20261007-1705z-6a92d/attempt-02/remote-stage/staging-note.txt`
and matches the cleanup receipt (SHA-256
`a4f02291fb1216e92c654af77905f0d541fe5f2e57618b2c0c3564cd3050768c`). The
later 459-byte attempt-03 local note was neither a pinned input nor uploaded.
Periodic samples observed at
most 3 owned processes, 884,124 KiB RSS, and 1,265,292 KiB private storage; these
are sampled values, not continuous peaks. The private runtime was removed by the
runner and the exact owned scope was retired after export; the cleanup receipt
records 34 files and 140,317,766 bytes removed. Evidence is under
`../.scratch/all-tickets/process-try-wait-evidence/x24-try-wait-20261007-1705z-6a92d/attempt-03/`.
**X24 attempt 04 — Workhorse Linux x86_64, Rust/Cargo 1.77.2; combined review READY.** The exact
filtered test passed with `testing-environ,sys`. It observed the real child alive
while public `try_wait()` returned unit, then obtained exit code 0 from terminal
`try_wait()` before `wait()`, confirmed the cached `wait()` result, and verified
the child was reaped (`ESRCH`). The assertion sensitivity control was reused from
attempt 03 because the test source hash and product source hash are unchanged;
the prior expected RED was not rerun. All six output hashes matched local
readback. Periodic samples observed at most 6 owned processes, 962,432 KiB RSS,
and 749,440 KiB private storage (not continuous peaks). The scoped runner removed
its private runtime; after export, the exact Workhorse stage/output scope was
removed and read back absent with no referencing processes. Evidence is under
`../.scratch/all-tickets/process-try-wait-evidence/x24-try-wait-20261007-1705z-6a92d/attempt-04/`.
The combined review found no material issue. X24 is partially accepted for
Workhorse Linux x86_64, Rust/Cargo 1.93.0 and 1.77.2, with
`testing-environ,sys`; other OS, feature and unrelated Ticket 03 rows remain
open.
### 6.1 Applicable rules and historical investigation

Current central repository: `/Users/hoppworks/projects/agent-skills`, local `main`
HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2`. The requested revision
`35ba734135a64100b891f422d4ced9d76795ab57` was inspected; the later local Main
delta changes the campaign and E2E rules to remove fixed machine-wide heavy-run
counts. The current supplied global rules agree with that delta. Loaded the current
global instructions, this worktree's `AGENTS.md`, `skills/campaign/SKILL.md` and
`skills/e2e-proof/SKILL.md`. Global AGENTS SHA-256 is
`7a0f59e741c84d87cdd7554c97d749ec641dbcb2132c3fe8b6c90423e12d16c4`; project
AGENTS SHA-256 is `06b73a9db5691ff5a0c5b34f98ce61e2c5df08e77161f3f93c7ce119d7c5de`.
The central checkout has no tracked changes; its unrelated untracked `.scratch`
material is preserved. `docs/agents/resource-lifecycle.md` is absent; the project
AGENTS resource procedure is applicable.
The central repository has no tracked modifications. Its untracked paths are
`.scratch/acceptance-overhead-plan-20261006/`, `build-age-automation-update.json`,
`campaign-calibration-budgets/`, `campaign-repair-packages/`, `central-build-paths/`,
`container-cleanup-automation-update.json`, `disk-pressure-cleanup-20261007/`,
`harness-efficiency-20261003/`, `machine-heavy-runs-20261004/`,
`owned-resource-cleanup/`, `periodic-sync/` and `streamline-acceptance/`, all below
`.scratch/`. These are not installed instructions. No installation, sync or Agent
configuration change was made. Other Sessions' loaded revisions are unverified;
no other Session was resumed or messaged for this planning request.

Compared with the previous campaign revision `6830c49ed962a3dc1937d72d0d182150bb4c935c`:

| Area | Applicable consequence for the open plan |
|---|---|
| Authorization and repairs | The owner's current instruction resumes the authorized implementation. Preserve consumed corrections and explicit finite actions; agent estimates and obsolete PENDING labels are not new approval gates. Reconcile existing human instructions before any later missing-authorization claim. |
| Review and delegation | One combined independent review per coherent change package, with affected-delta checks and evidence readback; specialist review only for a named risk. Keep related repairs with one responsible context. |
| Build/proof reuse | Reuse unchanged, applicable proof. Prefer related commands in one bounded build. Exceptional finite retention must be selected and recorded before use, with exact ownership, inputs, expiry and reuse boundary; a historical path or image ID is insufficient provenance. |
| Resource lifetime | Check free bytes on actual output/cache filesystems against additional occupancy and binding reserves. Recover storage only from proven own obsolete resources. Separate immutable builds from mutable fixtures; export before exact cleanup. |
| Acceptance/state | Validate the complete real entry/input/transport/export/consumer path before expensive execution. Record product RED, product failure and infrastructure abort separately. No new wrapper framework or repeated status hierarchy. |

The expired project concurrency exceptions do not reopen their named invocations.
There is no fixed machine-wide heavy-run count. Check active work and actual
CPU/RAM/disk pressure before a run, apply the limits and reserves attached to that
specific recipe, and do not wait for or claim a numerical slot. The first-cause
recipe's zero-foreign-heavy guard and its 600/585/540-second, two-job, descendant,
storage/RSS and 16 GiB admission limits remain specific to that recipe; they are
not a machine-wide convention. The general 16 GiB disk reserve in §6.5 remains
binding. Stopped repair routes below remain stopped; the new rules do not reset
their history. No unresolved rule conflict changes acceptance scope.

Read in full:
`/Users/hoppworks/Documents/Codex/2026-10-06/codex-threads-01a0fe32-5425-71d2-887b/outputs/session-review-2026-10-06.md`.
It describes four Tauron Sessions, not this Rhai Session. Its SQLx, UI, transport and
AUTHZ diagnoses are not Rhai findings. The useful hypotheses were checked here:
complete producer/consumer preflight, fewer handoffs, unchanged-proof reuse and
real acceptance. No Tauron test counts or failure causes are imported.

### 6.2 Reconstructed state and immediate bottleneck

The detailed first-cause attempt narrative in this subsection is historical through
native allocation 3. The attempt-4 record was also superseded as sole acceptance
evidence when combined review found its identity observation could race child exit.
Attempt 5 closes that specific gap; the accepted status and proof are recorded in
6.3–6.5 below. Do not treat old staged wrappers or source pins as current inputs.

At the earlier planning checkpoint, coordinator HEAD was
`8e5fe089fbcc86979ed3d5b73c393bf8fec72150` in
`/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery`;
that hash is historical, not the current implementation branch head.
All six local decision tickets are resolved as specifications. Feature completion
and release acceptance remain open. Existing filesystem/environment/file-handle/TCP
proof, core Darwin Rust 1.66 Engine proof, optional compiler/nonprocess feature
proof and named Linux lifecycle/example proofs remain accepted only within their
recorded source, assertion, toolchain and platform applicability. Compilation,
older native Windows 45-test proof and Wine do not close current process/TCP release
acceptance. No fresh remote-head claim is made by this implementation continuation.

At the historical checkpoint below, the first-cause writer was
`/Users/hoppworks/projects/rhai/.worktrees/process-first-cause`, HEAD
`77149f19e017007281396dcbf2eb8e69b7b90a37`, with preserved dirty source/recipe
corrections and untracked staging/collector files. At that checkpoint the
production fix remained unapplied. Native allocation 1 was admitted at
2026-10-07T06:47:41Z and reached
`baseline-red-direct`, but rustc stopped before any product assertion with E0308
at `src/packages/sys/process/unix.rs:4703`: the test adapter parsed PGID as `u32`
while the observed value is `i32`. The helper's missing raw-child receipt follows
from that compile abort; the later `/proc` diagnostic is secondary. This is a
fixture compilation failure, not a meaningful RED or completed failed product
correction. Its original output, allocation and cleanup receipts are preserved in
the writer's `attempts/attempt-01/`; the exact stage was retired after checking 72
PID/start identities and both owned groups, and the private scope is absent.

The one-line test-adapter correction parses PGID as `i32`; the production patch
remains unapplied. Attempt 2 used the reviewed stage and fresh admission at
2026-10-07T07:09:25Z (no heavy process; 81,014,168 KiB MemAvailable and
610,395,287,552 free bytes). Its exact `baseline-red-direct` command compiled
under Rust 1.77.2 and exited 101 at the intended public assertion: actual cause
was `OutputLimit("decoded process output exceeded the engine string limit of 512 bytes")`,
expected cause was `OutputLimit("stdout for `/usr/bin/python3` exceeded max_output of 512 bytes")`.
The stdout receipt independently confirms the child committed stdout overflow,
then observed stderr overflow and reaped the child. This is a meaningful product
RED and partial lifecycle proof. The producer then rejected the receipt because
libtest prefixes the selected test name on that same line; the helper exited 1
before the other five controls. No GREEN, mutant control, package acceptance or
production fix is claimed. The later `/proc/<pid>/stat` notice was a secondary
child-exit polling race; runtime and scope cleanup/readback both succeeded.

All 34 files from attempt-2 `proof-evidence` and `outer-evidence` were copied to
the writer and matched against fresh Workhorse SHA-256 readback. Exact originals
are under the writer's `attempts/attempt-02/`; no compiled artifact remains.
Local test-first probes now exercise exact selected-test receipt binding,
duplicate rejection, the split libtest `receipt\nok` / `receipt\nFAILED` status,
and missing/wrong statuses. The actual attempt-2 RED is accepted by producer,
collector and closure parsers. The same combined reviewer initially found the
GREEN status parser still expected contiguous `... ok`; that was fixed in the
same batch. The affected re-review returned READY. See
[the review history](../.scratch/all-tickets/process-first-cause-review.md) and
the current session state for exact evidence and consumed-work history.

Attempt 3 used the first parser-fixed stage and a fresh admission at
2026-10-07T07:36:39Z. Its 16 staged pins and wrapper/guard inputs were verified;
fresh admission found no heavy run, 81,120,748 KiB MemAvailable and
610,376,998,912 free bytes. Four controls—baseline RED and overwrite-mutant RED
for DirectChild and Managed—exited at the intended public cause assertion. The
DirectChild restored GREEN then reached the committed-cause, cached-result,
stdout/stderr byte, child-lifecycle and empty-cleanup-diagnostic assertions. It
stopped at the final completion-flag assertion because this exiting child had
reached EOF on both captured streams. The test's expectation of incomplete
streams was invalid; the corrected assertion now requires both streams complete.
The Managed restored GREEN was not reached. The combined reviewer rechecked this
test correction and returned READY. The exact test-only adapter changed after
attempt 3, so its stage is stale for the next run.

All 49 attempt-3 evidence files were copied and SHA-256 matched locally. A fresh
read-only closure confirmed all 120 recorded PID/start identities were absent or
reused, both owned process groups were empty, and the runtime scope and private
runtime were absent. No compiled artifact remains. Cumulative native allocations
are three; attempt 1 was a pre-assertion fixture compile failure, attempt 2 a
valid RED followed by a parser infrastructure stop, and attempt 3 four valid
REDs plus a restored-GREEN test assertion failure after the product assertions
passed. This last failure is a test correction, not evidence that the production
fix failed. Preserve all unaffected RED proof and partial OS evidence; no
full acceptance is claimed.

### 6.3 Open packages and observable exits

Packages are acceptance groups inside the existing tickets, not new tickets or
Sessions. Each may record partial criterion closures. They share the evidence and
resource rules in 6.4–6.6; no row is done merely because this plan names it.

| Package | Observable exit and dependencies | Cheap preflight and existing route | Real evidence, review and reuse |
|---|---|---|---|
| A. Committed Child cause | DirectChild and Managed retain the first actually committed stdout cause after gated stderr overflow/lossy expansion; cached results, captured bytes/EOF and cleanup agree. | Complete in native allocation 5 using the existing bounded six-control invocation: baseline RED and overwrite-mutant RED in both modes, followed by restored GREEN in both modes. All six expected statuses and assertions passed at one archive. The exact tested source hash is `d4fc28906b624f6e9368d0bef16e82e3fc29cada5142da67406fd95962153115`. Combined independent review returned READY. | Original proof, source-phase hashes, child acknowledgments/argv/PID/start/group, captured bytes/EOF, lifecycle and cleanup receipts, independent identity/group/path closure, and custody/readback receipts are preserved under `../.scratch/all-tickets/process-first-cause-evidence/attempt-05/originals/`. The live PID/PGID/start-ticks/argv handshake was acknowledged before cancellation; independent closure checked 113 process identities, five groups and six paths. Stage, scope and runtime are absent. This closes Package A only for Linux/Rust 1.77.2; it does not close ticket 03 or other platform/features. Preserve accepted overlap/setup/performance proof. |
| B. Remaining process terminal/cancellation semantics | First committed cause survives secondary cleanup; no-primary guard still reports the correct cause; stdin early close, cached wait/try_wait/kill, capture flags, owner/sentinel survival and bounded reaping meet ticket 03. Depends on A for the same Child capture path; stdin can be diagnosed independently. | The focused public-Engine Child.wait no-primary decoded-expansion regression and committed-primary cached-report branch are accepted on native Darwin arm64 and Linux x86_64, Rust 1.77.2, under `sys`, `sys,sync`, `sys,no_float`, and `sys,sync,no_float`. Eight platform/profile rows have intended assertion RED and restored GREEN with independent child-file/ESRCH observations. The public `spawn` pending-stdin BrokenPipe criterion is accepted for native Workhorse Linux x86_64, Rust/Cargo 1.77.2, `testing-environ,sys`, at integrated commit `0c6c51b9`: the prior attempt03 reached the intended missing-error RED; the full unfiltered `sys_process` rerun on this final source passed 60 tests, failed 0, ignored 3, including the exact real-OS regression. The regression's independently recorded typed BrokenPipe, child/group cleanup, host/sentinel survival and capture markers are in `../.scratch/all-tickets/writezero-unit-20261009T2025Z/linux-followup/`; the run log hash was read back. The original typed error/prefill receipts and classifier replay remain in `../.scratch/all-tickets/linux-stdin-closure110-evidence/original-export/`. The distinct pending-byte `Ok(0)` branch is accepted as a focused injected `WriteZero` RED/GREEN unit criterion on Darwin arm64/macOS 27.0.0, Rust/Cargo 1.77.2, `testing-environ,sys`; it supplements but does not replace native-OS acceptance. Evidence and lock/source hashes are recorded in `../.scratch/all-tickets/writezero-unit-20261009T2025Z/` and the status note above. The full Darwin `sys_process` target also passed 48/0/1 on the earlier fixture source; its log and exact profile are recorded in that proof folder. Native Darwin arm64/macOS 27.0.1, Rust/Cargo 1.77.2, `testing-environ,sys` now also accepts the exact public-Engine early-close/BrokenPipe criterion: the active SDK pipe held 65,536 unread bytes of 4 MiB input, independent readback observed fd 0 closed, expected RED returned `Ok(())` only on the private BrokenPipe-only revert while the same child remained live, and current-source GREEN retained typed `BrokenPipe` (`write child stdin`), complete captures and bounded child/group cleanup with host/sentinel identity preserved. The exact source, lock, SDK, commands, RED/GREEN logs, statuses and cleanup are recorded in `../.scratch/all-tickets/writezero-unit-20261009T2025Z/darwin-stdin-closure-20261009T204536Z/`; combined independent review passed. This closes only the named Darwin default-feature stdin row. Unchecked/no_index, Windows, other cancellation/capture/cache/owner/sentinel and bounded-reap rows remain open. These remain named partial criteria only. | [No-primary and cached-report proof](../.scratch/rhai-wayfinder-replan-20261008/results/unix-wait-20261008T131127Z-3fcea4ec/proof.md), [stdin-closure export](../.scratch/all-tickets/linux-stdin-closure110-evidence/original-export/), and the WriteZero logs preserve evidence and review context. No blanket repeat occurred. Unchecked/no_index, Windows, macOS native stdin, other cancellation/capture/cache/owner/sentinel and bounded-reap rows remain open unless covered by applicable proof. |
| C. Darwin native completion | Missing macOS lifecycle, process behavior and sys/net real examples/feature interactions pass on native Darwin at the selected Rust version. Depends on a proven custody/readback path; no dependence on re-running Linux foundations. | The actual process-monitor files are `.scratch/all-tickets/run-macos-process-overhead-scoped.py`, `.scratch/all-tickets/run-macos-process-overhead.sh`, `.scratch/all-tickets/darwin-process-reader.py`, and `.scratch/all-tickets/test-darwin-process-reader.py`. The prepared sys/net contract under `.scratch/all-tickets/current-darwin-sys-net-behavior-contract.md` pins commit `2f795ece...` on side branch `task/current-darwin-sys-net-behavior`, not an ancestor of current integrated `main`; its old lock/source pins are not validated for this checkout, so it is not the current execution route. F23's configured, dot-component, symlink-ancestor and macOS-prefix root spellings passed together in the current `sys_policy` target through the public Engine on native Darwin and received a combined READY review; this is only the macOS sys-policy slice, not C completion. The direct `tests/combined_sys_net.rs::sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors` target now passes one Darwin default-feature coexistence slice at source `055a068...`, using `testing-environ,sys,net` and lock SHA-256 `4ff0a7de...`. This does not close the full TCP/OS/feature matrix. A Darwin X24 process row is accepted in `.scratch/all-tickets/x24-darwin-trywait-20261008/attempt-02/proof.md` at arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`: the public Engine starts a real child, the test observes pending and terminal `try_wait`, checks cached `wait`, and independently observes ESRCH. Its raw RED/GREEN results passed combined review; the prior derived status classification is superseded because libtest output tokens were interleaved. A Darwin X23 example row is also accepted at source `443f15cc...`; `.scratch/all-tickets/darwin-process-example-20261008/attempt-01/proof.md` records the public Engine/`sys_process` example, real child-file readbacks, pending wait and identical cloned results, expected RED and restored GREEN, and scoped cleanup. Combined independent review returned READY. Both X23 and X24 close only their named rows/profile. A Darwin X25 row is now also accepted: `.scratch/all-tickets/darwin-x25-kill-20261008/proof.md` records expected RED/GREEN for the public managed `spawn` → `kill` → bounded `wait` test, independent absence of the leader, worker and leaf, unrelated sentinel survival and exact reaping; combined review returned READY. Its profile is arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`. These three named rows do not close the remaining Darwin lifecycle/features or Package C. | Attempt 01 under `.scratch/all-tickets/darwin-f23-sys-policy-20261008/attempt-01/` records exact source/lock/toolchain, expected-RED sensitivity control, all 26 target tests and the five named root tests. The F23 review returned READY. Combined sys/net evidence is in `.scratch/all-tickets/combined-sys-net-darwin-20261008/attempt-01/` and `attempt-02/`: source `055a068...`, identical Cargo.toml/test hashes, Rust 1.93.0 and lock SHA-256 `4ff0a7de...`. Attempt 01 confirms locked metadata and the wrong-expectation control failing at the host byte assertion; Rust printed its test status on a separate `FAILED` line, which the first wrapper did not recognize. Attempt 02 reused that valid RED and metadata, then passed the exact green target 1/1. The test reads the host file back, checks exact bytes received/sent by an independent OS-selected TCP peer, and checks typed SysError/NetError. The scoped green run exited 0 and removed its exact private runtime. The combined independent review returned READY on 2026-10-08. This closes only this default-feature sys/net coexistence slice, not all TCP/C/MSRV rows. Reuse compiler/nonprocess/EPERM proof where unchanged. Earlier overhead method measures API-entry-to-report, not spawn-to-first-byte; do not repeat a fulfilled measurement merely for a new plan. |
| D. Windows custody then native behavior | Exact owned job survives connection loss under an independent lease/monitor, bounds work, reports truthful nonzero failure and exports/cleans; then native sys/process/net and quoting/policy/feature criteria pass. Custody is a prerequisite with its own partial exit. | Existing `windows-runner-gate.md`, Windows scoped-runner brief, Expert02/13 and `windows-resume-20261003/harness-command.txt` are the canonical design/history. Before compiler use, check the full console/client/job/status/export path. Current self-inclusive teardown has a source-supported failure-status explanation, not proven kernel causation. Preserve exhausted two harness attempts; no automatic third. | Native setup-failure, real 0/17, mismatch/restored, interrupted connection/supervisor, exact job membership/closure and retained primary diagnostics. Observer stays outside the failed job. Then real Engine, actual filesystem/TCP peer/process readback. One combined package review, extra Windows specialist only for a named unresolved job risk. Preserve installation/activation/native baseline and backups; never drive the other Session's guest. |
| E. API metadata and usable documentation | Registered receiver/arity/type/doc-comments match actual Engine metadata; sys/net/process examples run with independent effects; public config/error compatibility and file API divergences are documented. | The Workhorse/native3 route remains closed after three pre-assertion infrastructure failures and its exhausted follow-up. Darwin attempt 11 passed the prior metadata checks and process example/readbacks. After the combined review found the timed-wait comment gap, attempt 12 passed the targeted sys metadata assertion with both default-float and `no_float` profiles; its first preparation stopped before Cargo because the checkout omitted ignored `Cargo.lock`, then used the exact hash-pinned accepted lock. It reuses attempt 10's inspected TCP RED; no repeated RED or example build is needed. | Current Darwin metadata/process evidence is under `.scratch/all-tickets/api-metadata-evidence/macos-direct-20261008-9bcf4822/attempt-11.*` and `attempt-12/`; reusable native TCP and file readbacks are in `.scratch/tcp-docs-example/proof.md` and `.scratch/file-handle-docs/proof.md`. README documents SysConfig names/defaults, SysError/Rust matching, and intentional rhai-fs overlap/streaming differences; timed `Child.wait` metadata comments and assertions now describe unit-on-timeout without cancellation. The combined independent review returned READY for the corrected package at this revision; this closes only Package E, and relevant metadata/doc rows should be shared with F. Reuse while cited source/test/environment hashes remain applicable. |
| F. Integrated compatibility/release closure | Every ticket criterion has applicable proof at the integrated revision: core1.66, optional1.77.2, native Linux/macOS/Windows, required semantic feature rows and explicit unsupported combinations. Depends only on relevant A–E criteria, not all preparation steps indiscriminately. | Diff source/assertions/manifests/lock/toolchain/config against existing accepted rows. Use project Cargo integration targets and the exact approved feature matrix in ticket06/release-proposal.md. Resolve actual archive inventory/tool availability/paths and expected error categories before compiling. | Share one build and real acceptance for related rows per machine/toolchain/feature identity. Reuse unaffected rows; rerun only changed dependency closures. Default sys/net and sync/no_index, metadata+serde/i32, unchecked/no_index/sync/metadata/f32 interactions remain covered. Core without OS deps; sys rejects no_std/no_object/WASM as decided. Combined integrated review/readback closes each criterion, not a count-only gate. Release readiness does not authorize publishing, deploying or enabling Actions. |

No UI is part of Rhai's acceptance stack. The full path is script → real Engine →
host package → OS. Storage proof is required for filesystem effects; independent
peers and process observations replace storage writes for networking/process
behavior. Read-only APIs compare independent truth. A mock or compiler success
cannot replace these checks.

Package A acceptance record: the entry point was a public `Engine::eval` call
running a Rhai `spawn` script through the registered `sys` package to a real
Unix child on Linux with Rust 1.77.2 and `testing-environ,sys`. The child emitted
stdout and stderr under deterministic gates; an independent `/proc` readback
matched its live PID, PGID, start ticks and argv before the parent released the
child. The six controls comprised four intentional REDs (baseline and
stderr-overwrite mutant, DirectChild and Managed) that exited 101 at the
first-cause assertion, followed by two restored GREENs that exited 0 and passed
the selected test. The green cases also verified cached results, exact captured
bytes, stream EOF, child reaping, Managed group closure and empty cleanup
diagnostics. The independent closure and preserved raw outputs are in
`../.scratch/all-tickets/process-first-cause-evidence/attempt-05/originals/`.
This proves Package A's stated Linux/Rust 1.77.2 criterion only; no cross-platform,
other-feature, Package B, ticket-wide or release acceptance is inferred.

### 6.4 Concrete command contract and current execution

All paths below were read. Attempt 3 provided four expected RED controls and a
DirectChild restored-GREEN partial result. Attempt 4 passed all six controls, but
the subsequent combined review found its parent identity observation did not
prove that the child was still live at observation time. Attempt 5 added a
parent-acknowledged live identity handshake before cancellation and passed all
six controls again; its exact phase hashes, original outputs and independent
closure are preserved. The combined review and custody/readback checks are
complete for this scoped criterion. Other proposed commands remain unexecuted
until their inputs are frozen.
POSIX commands run from an owned source copy within the existing bounded runner,
not the coordinator's mutable source. Project ID is `rhai`. The invocation creates
one unique owned absolute session scope and uses its path as `TMPDIR` for
`/Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout <bound> -- <command>`.
Inside it set target/private Cargo and Python caches to `AGENT_RUNTIME_DIR`, using
`CARGO_TARGET_DIR`, `CARGO_HOME`, `PYTHONPYCACHEPREFIX` (or disable bytecode) and the
recipe's private `RUSTUP_HOME`. Direct Rust/Cargo paths must match the intended
1.66 or 1.77.2 version; `stable` is not a substitute.

For A, the existing native argument shape is:

```text
<private Rust1.77.2 cargo> test --locked --lib --features testing-environ,sys   packages::sys::process::unix::tests::committed_stdout_cause_survives_stderr_overflow_direct_child   -- --exact --nocapture --test-threads=1
```

The second exact test ends in `_managed`. The recipe executes four intended REDs
and two restored GREENs in one bounded runtime, preserving phase hashes and raw
receipts. Attempts 1–3 and their fixture/parser corrections remain historical
and are detailed above. Attempt 4 passed all six controls, but the later review
found its parent identity observation could occur after child exit. Attempt 5
repeated the bounded six-control recipe with an explicit live-identity
acknowledgment before cancellation; all six expected statuses and assertions
passed at one exact archive. The phase hashes show the production fix in both
restored-GREEN cases and the baseline restored after the mutant. Attempt-5 evidence
was exported first; the runner removed its private runtime and scope, the collector
validated/exported originals and retired the stage, then fresh closure verified
that the identities, groups and paths were absent. No compiled build remains
reusable.

The accepted project baseline route remains:
`cargo test --locked --features testing-environ,sys,metadata --test sys_policy --test sys_env --test sys_fs`.
Add existing `sys_process`/net integration targets according to covered criteria,
not a fabricated universal command. E's existing recipe selects
`cargo test --locked --features testing-environ,sys,net,metadata --test <target> metadata -- --nocapture --test-threads=1`.
Its old mutable stable/pin/receiver assumptions must be corrected before use.
Windows has a design and recorded console command, not a proven executable
release runner; no POSIX SSH wrapper can establish guest cleanup by itself.

### 6.5 Evidence, actual artifact availability and lifecycle

Read-only existence checks on 2026-10-07:

| Resource | Actual availability and permitted reuse |
|---|---|
| Committed originals in this coordinator worktree | Overlap raw result/restoration/control ledgers and independent closure are present: source9dc, controls101/101 then0/0. Post-spawn setup originals are present: source523, wrong-cause101/wrong-completion101/restored0. These narrow accepted results remain proof, not new acceptance claims from producer acceptance_claim=false. |
| Overlap workhorse stage/scope | Exact `/root/rhai-linux-process-overlap-d79-20261004-1259` and its central scope are absent, including symlink checks. No reusable compiled build remains there. |
| First-cause attempt 1 | Original compile failure, raw diagnostics and allocation receipt remain under the writer's `attempts/attempt-01/`. The exact remote stage was independently retired; 72 PID/start identities and both owned groups were checked, scope is absent, and there is no reusable compiled output. One native allocation is consumed. |
| First-cause attempt 2 | Its stale stage was retired after attempt-3 stage readback; original partial proof is under the writer's `attempts/attempt-02/`, with 34 files hash-matched locally. It contains one valid baseline RED and process receipt, not full acceptance. |
| First-cause attempt 3 | Partial evidence is under the writer's `attempts/attempt-03/`; 49 files match Workhorse SHA-256 readback. Four expected REDs are valid. DirectChild restored GREEN reached the cause, cached-result, output-byte and child-lifecycle assertions, then failed at the old EOF assertion; the following cleanup-diagnostics assertion was not reached, and Managed GREEN did not run. Fresh closure verified 120 identities absent or reused, two owned groups empty and the private scope/runtime absent. Exact stale stage `parserfix-01` was retired at 2026-10-07T07:55:26Z after checking 120 PID/start identities and empty groups; the receipt also confirms scope absence. |
| First-cause attempt 4 | Complete originals are preserved under `../.scratch/all-tickets/process-first-cause-evidence/originals/stage-originals/proof-evidence/`, with outer custody and independent-closure receipts under `../.scratch/all-tickets/process-first-cause-evidence/originals/`. Four intended RED controls exited 101 at the first-cause assertion; both restored GREEN controls exited 0 and independently read back one passed test. The phase source hash is `fced800d5b05a1582a4d1c27cadabda32dc1517522e5ed733865d7faab48e5d4`; final baseline restoration matched. Resource samples (54 periodic samples) recorded maxima 950,608 KiB RSS, 697,712 KiB storage and four descendants, below the recorded limits; these are sampled, not continuous peaks. Independent closure verified 127 identities, five owned groups and six paths. The exact stage, scope and private runtime are absent. No compiled artifact is reusable. |
| First-cause attempt 5 (accepted) | All 71 original files are preserved under `../.scratch/all-tickets/process-first-cause-evidence/attempt-05/originals/`; source phases, raw outputs, parent child-identity acknowledgments, custody, independent closure and retirement receipts were read back. Four intentional RED controls exited 101 at the intended first-cause assertion and two restored GREEN controls exited 0; the final source hash is `d4fc28906b624f6e9368d0bef16e82e3fc29cada5142da67406fd95962153115`. A parent-acknowledged `/proc` observation proved PID/PGID/start ticks/argv while the child was live before cancellation. Independent closure verified 113 identities, five groups and six absent paths. Forty-seven periodic samples recorded maxima of 931,608 KiB RSS, 687,208 KiB storage and four descendants; sampled values are not continuous peaks and remained below recorded bounds. Exact stage, scope and private runtime are absent. No compiled artifact is reusable. |
| First-cause attempt-4 interpretation | Attempt 4's six controls and evidence remain preserved as historical corroboration, but the later independent review found its process-identity sampling could occur after child exit. Do not use attempt 4 alone to claim the live-identity criterion; attempt 5 supplies that missing proof. |
| First-cause stages | Attempt-4 `parserfix-02` was independently read back and retired. Attempt-5 stage `/root/rhai-linux-process-first-cause-fc-20261007-ack05-7d11e2c4` was retired after proof export; the fresh closure afterward confirmed stage, scope and runner runtime absence. Do not reuse historical stage paths or claim a reusable build. |
| Core private builds | All four paths in `core-current-msrv-root-readback.json` are still absent locally. Logs/control/restoration proof remains; no compiled-target reuse claim. |
| macOS locked source audit | Historical source-integrity receipt remains, but its exact `macos-overhead-safeguards/.../macos-overhead-custody-source-audit` path is absent. Restore only required source inputs from verified surviving archives or acquire needed inputs later; do not claim the old 131-archive tree is available. |
| Windows baseline/images | Read-only host listing confirms `/var/lib/libvirt/images/rhai-win11-quality` with system.qcow2, baseline and ready-baseline. Existence does not establish source/toolchain provenance or guest cache availability. Guest paths were not queried and remain unconfirmed; preserve this other owner's resources and snapshots. |

There is no currently verified reusable owned compiled build. Prefer build/test/
readback/export in the same invocation. Do not rebuild an unchanged artifact for
an assertion-only control: reset uniquely owned fixture data separately. If a later
package genuinely needs finite retained compilation, record exact central path,
owner, input identity (sources, lock, toolchain, flags, SDK), byte ceiling, finite
reuse boundary and expiry before configuring output outside the runner's private
runtime. No exceptional retained build is allocated for package A.

Before a heavy launch, measure free bytes on source/output/cache filesystems,
active machine-wide runs and available RAM against the preserved limits/reserves.
For each actual filesystem, require free bytes minus predicted additional occupancy
to retain the binding16 GiB reserve; budget private output up to its2 GiB hard ceiling
plus measured stage/export occupancy rather than treating16 GiB free as unlimited
build space. No new retention size is allocated.
Historical samples do not establish peaks or current slots. On insufficient disk,
export proof and perform one bounded cleanup of exact obsolete own resources,
recheck free bytes, then continue only if feasible. No broad cache purge, foreign
stop, VM reset, worktree removal or install follows from this plan.

Save source/lock/tool versions, raw stdout/stderr/status, phase identities, resource
samples, partial results and diagnostics outside private runtimes as they complete.
Independently read back actual effects and exact cleanup. Separate diagnostic
collection on failed/partial runs from the success-only acceptance validator.
Only then retire exact inactive own stage/runtime/containers and empty scope;
Windows cleanup requires job/monitor ownership. Durable proof and foreign assets
are preserved. Attempt 1's exact owned stage was retired after proof preservation.
Attempt 2's partial proof has been copied and hash-checked locally; its exact stale
stage was retired after the initial byte-level `parserfix-02` readback. A semantic
audit then found the generated preflight's mismatched physical-stage assertion.
The test caught this first as an expected local RED; after fixing the physical path
mapping, the full recipe probes passed and the combined review returned READY. The
old preflight and first receipt are retained; the corrected guard was read back
with the other 18 stage files. No run or compiled artifact was created. No foreign
or shared resource was cleaned. At this historical checkpoint Tauron Integration
reported its selftest green and was checking cleanup; the latest Workhorse process
listing showed no heavy process. The earlier authorized build-window request was
subsequently resolved: Tauron was informed that Rhai's run had ended and its slot
was available for Tauron's own fresh admission (see the later Package E record).
Do not wait for the old signal; any future launch still needs fresh admission.

### 6.6 Retry triggers, risk and critical path

Critical path: Package A is accepted only at Linux/Rust 1.77.2 → Package B remains
open with its bounded route stopped; Package E's reviewed metadata, process and
reusable TCP/file evidence are integrated at fork main `04d9a797...`, with no new
metadata/example build needed absent invalidating evidence. The two named Darwin
F23 alias assertions are integrated at fork main `ad980d80...`; their accepted
RED/GREEN and readback proof remains valid. The remaining configured, dot-component
and symlink-ancestor root spellings also pass as part of attempt 01's full 26-test
`sys_policy` target on Darwin arm64/macOS 27.0.1, Rust 1.93.0, with
`testing-environ,sys` and lock SHA-256 `4ff0a7de...`; its expected-RED control
failed at the permission assertion before the restored run passed. This closes
only the macOS F23 sys-policy slice. Independent review accepted the test evidence and verified the corrected
source-pin description. Commit/push this plan/state update without repeating the
build. The direct `combined_sys_net.rs` coexistence target and its locked metadata,
expected-RED, and green evidence are recorded under
`.scratch/all-tickets/combined-sys-net-darwin-20261008/`; its only proven scope is
default sys/net coexistence. The combined independent review returned READY.
X22 also has Darwin arm64/macOS 27.0.1, Rust/Cargo 1.93.0 execution evidence for
the real public-Engine SIGKILL child: the sensitivity control reports 9 versus
10, and the restored Cargo test passes with host-file and ESRCH readbacks. Raw
outputs and both validator-format errors are documented in
`.scratch/all-tickets/darwin-signal-x22-20261008/proof.md`; combined independent
review returned READY for this row only. Darwin X38's named
`managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes` test
also passed its reviewed assertion-sensitivity RED/GREEN at arm64/macOS 27.0.1,
Rust/Cargo 1.93.0 with `testing-environ,sys`; its independent pipe, process and
cleanup readbacks are in `.scratch/all-tickets/darwin-x38-20261008/attempt-03/`.
This closes only that named Darwin assertion row; other X38 platforms, features,
and MSRVs remain open. C and D retain unproven custody prerequisites → map remaining §6 criteria to existing proof and choose the
cheapest unspent route; close only
uncovered integrated rows in F → verified fork-main integration under existing
Git authorization. Do not rerun accepted X22 Linux toolchains or their sensitivity
control absent a relevant invalidating change. No upstream writes, production
release or new Goal are authorized.
Do not repeat Package A's build or six controls. Its accepted proof is tied to the
tested source/lock/toolchain and Linux environment recorded in the preserved
receipts. A later A rerun needs a relevant source, assertion, dependency, toolchain
or environment change that invalidates this proof, or a specific uncovered A
criterion. A new Session, rule revision or renamed cause is insufficient.
For Package B, first map the still-open ticket 03 criteria to existing code and
original evidence; run the cheapest source/test-target checks before selecting one
real-OS case for any genuinely uncovered behavior. A further expensive run needs
a new product diagnosis/fix, changed relevant inputs or an uncovered acceptance
criterion; do not respond to a new failure with a routine full-suite rerun or a
new transport/wrapper layer.
After repeated preparation failure inspect the entire actual composed path before
allocation; do not append another transport/wrapper layer or rerun all packages.
Expected assertion RED consumes its allocated command but is not a failed product
correction. Compiler/parser/export aborts before assertions are infrastructure
outcomes. Completed rejected repairs retain their cause counts. Two failed
corrections/recoveries require the prescribed independent diagnosis; exhausted
post-escalation follow-ups stop that route. No routine approval gates are added.

Preserved stopped paths: stdin Expert18 (two failed corrections plus rejected sole
follow-up2518238; native110 unallocated), Darwin custody Expert09/12, metadata
Expert21 (two corrections plus rejected09eb follow-up) and Windows Expert02/13
(two harness invocations consumed; real-client finite30-minute boundary unchanged).
The task's standing acceptance of recommendations must be reconciled with the
specific human limits before any later authorization conclusion. It cannot erase
consumption or authorize a third run by renaming a cause. These are open execution
risks, not reopened allowances or dropped acceptance criteria. A simpler route must
retain the same observation/custody contract and explain why it avoids the proven
failure mechanism; this plan does not assert such a route is already proven.

Risks/counterarguments: A's accepted proof is narrow to its exact Linux/Rust
1.77.2 source, lock and assertions; it does not prove B's other process semantics
or Darwin/Windows behavior. Shared builds save setup only when inputs match;
platform-specific cleanup cannot transfer from Linux to Windows. Package A's
combined reviewer returned READY; Windows guest ownership remains with its
recorded owner.
The current task has no unresolved result/design choice requiring a user answer.
Implementation feasibility of stopped routes remains explicit, not certified.

**Completed bounded Linux package:** Ticket 03 X14/X16/X17 as one public-Engine
process-I/O package. The exact source entry is the three tests in
`tests/sys_process.rs`; the canonical command is
`cargo test --locked --features testing-environ,sys --test sys_process run_io_contract_ -- --nocapture --test-threads=1`.
X14 launches `/bin/sh` with a normal positive output cap and independently checks
empty captured strings plus child exit/reaping; X16 launches `/bin/sh` and
`/bin/cat`, sends a Rhai string through `run`, and compares exact captured bytes
plus the child record/reaping; X17 uses the existing self-exec stress fixture
through `run_raw`, sends a varied 1 MiB Blob, drains concurrent 256 KiB stdout
and stderr payloads, and compares both the exact echoed bytes and a child-written
copy of the received input. Prerequisites are Workhorse Linux x86_64, `/bin/sh`,
`/bin/cat`, Rust/Cargo 1.93.0 and the accepted locked dependency graph; no shared
service is needed. The bounded Workhorse invocation established the fixture RED,
restored a three-test GREEN, rejected a wrong expected value for each criterion,
and exported checksummed results before runtime cleanup. The setup-only first
launch and its precise correction remain recorded; it ran no Cargo command. No
compiled artifact is reusable. The combined independent review returned READY
with no material findings. Commit `8532b375c0a6f8121fcbc587fd53eef3990c1b2a`
contains this package and was atomically pushed to the authorized fork `main`.
This proof accepts only the named Linux/Rust/feature rows.

The same acceptance package has a Darwin partial result at
`.scratch/all-tickets/darwin-io-contracts-20261008/attempt-01/proof.md`. One
bounded scoped Cargo command on arm64/macOS 27.0.1 (kernel 27.0.0), Rust/Cargo
1.93.0, `testing-environ,sys` passed all three public-Engine tests: empty output,
the exact 51-byte string round-trip, and the varied 1 MiB Blob round-trip with
exact 1,310,736-byte stdout and 262,144-byte stderr captured concurrently.
Child-written records/input readback and direct-child reaping were checked.
The combined independent review returned READY after a focused cleanup
readback follow-up; all five exported run/cleanup hashes verify. The existing
Linux wrong-expectation controls remain valid because the test bodies/helper
are byte-identical and the controls exercise ordinary Rust assertions. This
accepts only the named Darwin OS/toolchain/feature rows; other matrix and Ticket
03 requirements remain open. No compiled artifact is retained for reuse.

The earlier next-work snapshot for this X14/X16/X17 package is superseded by
`.scratch/all-tickets/coordinator-state.md`. Current accepted scope and remaining
criteria stay in §6.7; Package B/E stop causes and consumed counts remain in the
ticket records and archived coordinator state. Do not use the old snapshot as a
current next action.
The exact metadata command and its source/test mapping remain as recorded below.
The full archive and pinned lock provenance remain available locally; the attempt-03
preflight passed, then the launcher stopped at line 23 before extraction/Cargo due
to the `tar | grep -q` pipefail interaction. See the attempt-03 classification and
readback files. No metadata criterion, runnable example, OS effect, compatibility
row or release gate is closed by this attempt.

The exact command is
`cargo test --locked --features testing-environ,sys,net,metadata --test net_metadata --test sys_policy metadata -- --nocapture --test-threads=1`.
It selects `metadata_exposes_the_documented_tcp_surface` and
`metadata_documents_tcp_handle_operations_and_overloads` in
`tests/net_metadata.rs`, which register `NetPackage` in a real `Engine`, serialize
`gen_fn_metadata_to_json(false)`, and check exported TCP comments and signatures;
it also selects `test_function_metadata` in `tests/sys_policy.rs`, which builds
the sys `Engine` metadata and checks `SysError`/Unix `Child` comments and the exact
Child signatures. Thus this start path reaches the registered public metadata
criterion. It does not exercise socket, process or file effects and cannot close
Package E's example/readback requirements.

The following allocation1/allocation2 detail is historical and is superseded by
the terminal allocation3 result; remaining criteria stay in §6.7.

Native3 allocation1 reached Cargo compilation but stopped before assertions because
its staged source archive (SHA-256
`c34c9b889a1e9b4052f9c52b8256d6d7236b92baffdfc26784d1442fdc6381af`) omitted
tracked `build.template`; allocation2 stopped before Cargo because the
launcher expected `source.tar.gz` while the complete archive was staged as
`source-full.tar.gz`. Both are infrastructure outcomes in the unverified source
handoff path, not RED or product corrections. Cumulative native3 counts are two
allocations, two pre-Cargo/pre-assertion stops, zero assertions and zero product
corrections. Allocation2's raw outputs, input hashes and postrun scope/runtime
readback are under `.scratch/all-tickets/api-metadata-evidence/native3-20261007/attempt-02/`.
The exact owned staging files and empty scope were removed after preserving proof;
no compiled artifact is reusable. The full replacement source archive is
`.scratch/all-tickets/api-metadata-evidence/native3-20261007/source-full.tar.gz`
(422 current tracked inputs, SHA-256
`a243fc96c513c70d86e0281e0f178d91c95e6338ab3dda24d1656f7dd8863de5`); the archive
and each entry were checked against this worktree. Its pinned lock is
`.scratch/all-tickets/api-metadata-evidence/native3-20261007/Cargo.lock`
(SHA-256 `4ff0a7de6f504510af64092d446d411b86d95228b23a188b396bd188da367627`). The
corrected bounded launcher is
`.scratch/all-tickets/api-metadata-evidence/native3-20261007/run-recovery-red.sh`;
it validates both hashes and `build.template`, uses Rust 1.93.0 and `--locked`,
and preserves logs outside the runner's private runtime. Dependencies are the
exact complete archive/lock, the installed pinned Workhorse toolchain and runner,
at least the project admission reserves on the actual filesystem, and an available
heavy-run slot. The prior Tauron Cargo/rustc group ended; Workhorse's read-only
process/capacity snapshot at 2026-10-07T09:56:49Z found no active scoped
runner/compiler, 80,850,876 KiB MemAvailable and 610,347,319,296 bytes free on
the output filesystem. The owner-authorized message informed Tauron that Rhai is
terminal and its run slot is free; Tauron may proceed only under its own fresh
admission. That snapshot is not a slot reservation. The corrected launcher
samples the exact helper process tree and private runtime once per second,
records maxima and stops at the existing 16-descendant, 1,572,864 KiB
storage-preemption and 2,097,152 KiB RSS/storage thresholds. Its 510-second work
deadline leaves the existing 30-second reserve inside the 540-second helper cap;
the scoped-runner and outer bounds are 585 and 600 seconds. Sampling reports
bounded maxima, not continuous peaks. Guard/setup failures remain infrastructure
outcomes, separate from metadata assertion RED.

Historical escalation 24 asked for a read-only review of the complete archive-to-stage-to-
launcher path and a single minimal repair/preflight. It does not authorize another
wrapper, Cargo run during diagnosis, or product edit. After that bounded repair,
recheck exact names and hashes, the launcher/runner/toolchain, process absence,
Workhorse capacity and slot, then coordinate Tauron's own admission before one
bounded metadata run. Only a named missing/inadequate metadata assertion is RED;
another setup stop ends this route for diagnosis. After valid RED, make the
smallest accurate documentation correction and rerun only affected metadata
tests. Capture Engine JSON and exact test output, then perform one combined review.
That plan predates the local Darwin route and remains valid only for its stopped
Workhorse/native3 path. It does not authorize another Workhorse attempt or change
its consumed history. Current Package E evidence is the one bounded Darwin attempt
11 at Rust 1.93.0: the combined metadata command passed TCP and Child assertions;
the process example's expected-exit control failed at its final exit assertion
after both host records and cloned wait results were read back, and the restored
example passed with the same readbacks. After the combined review found that the
timed `Child.wait` overloads omitted unit-on-timeout and non-cancellation semantics,
attempt 12 passed the targeted sys metadata check in default-float and `no_float`
profiles. Its initial preparation stopped before Cargo because `Cargo.lock` was
absent from the checkout; the rerun copied the exact hash-pinned accepted lock.
Attempts 09–12, exact hashes, logs and
statuses remain under `.scratch/all-tickets/api-metadata-evidence/macos-direct-20261008-9bcf4822/`.
The existing `.scratch/tcp-docs-example/proof.md` and
`.scratch/file-handle-docs/proof.md` cover the unchanged real peer and file effects.
README and timed-wait metadata comments now cover the remaining public API details.
The combined independent reviewer returned READY for these artifacts and docs at
the corrected revision. Package E is integrated at fork main `04d9a797...`; no new
metadata or example build is planned absent a finding that invalidates current proof.

### 6.7 Ticket 03 criterion-to-evidence map — checked 2026-10-08

This map compares original requirements P2/P10/P11/P13 and X1–X38 with current
test source and accepted proof artifacts. “Accepted” means only the named OS,
toolchain, feature cases and rows below; “partial” preserves the stated gap. No
row is closed by a source test alone or by an unreviewed/provisional result.

| ID | Current test/evidence | Applicability and remaining gap |
|---|---|---|
| P2 | `tests/sys_process.rs::default_and_nonmatching_process_policies_deny_public_run_without_starting_child`; Linux proof in `.scratch/all-tickets/process-policy-proof/attempt-02/proof.md` | Partial: Workhorse Linux x86_64/Rust 1.96.0 proves public Engine denial under default policy and no child marker. Strict native OS/MSRV and feature-matrix rows remain open. The reviewed Linux package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/linux-process-minimum-20261008T201200Z-6e2ba1d7/proof.md` additionally accepts this exact public-Engine assertion at Rust/Cargo1.77.2, `testing-environ,sys`, with unchanged oracles, reused original RED controls and fresh native GREEN/readback/reap. Other uncovered native/feature rows remain open. |
| P10 | Same public Engine test and proof; exact allow-list success control | Partial: Workhorse Linux x86_64/Rust 1.96.0 proves a nonmatching allow-list returns `Denied`, leaves its child marker absent, and has an exact-match success control. Strict native OS/MSRV and feature-matrix rows remain open. The reviewed Linux package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/linux-process-minimum-20261008T201200Z-6e2ba1d7/proof.md` additionally accepts this exact public-Engine assertion at Rust/Cargo1.77.2, `testing-environ,sys`, with unchanged oracles, reused original RED controls and fresh native GREEN/readback/reap. Other uncovered native/feature rows remain open. |
| P11 | `process_cwd_uses_the_opened_filesystem_capability_after_root_replacement`; `linux-process-options-proof.md` | Partial: Linux capability-held cwd and denied symlink escape are accepted in named rows; escape denial proves no fixture record, not absence of every transient process, and does not cover every outside-root cwd form. |
| P13 | `tests/sys_process_windows.rs` | Open: existing Windows test covers raw output/nonzero exit, not default `.bat`/`.cmd` denial. |
| X1 | `scalar_run_with_cwd_works_without_collections`; `linux-scalar-process-proof.md` | Accepted for named Linux feature rows: public Engine success, exit 0 and independent child record; no wider matrix follows. |
| X2 | tests/sys_process.rs::missing_program_and_cwd_report_not_found_without_starting_child; .scratch/all-tickets/process-not-found-proof/proof.md | Partial: Workhorse Linux x86_64/Rust 1.93.0 proves public Engine run returns Io/NotFound for a missing program and the fixture record stays absent, with a valid-child control and independent reaping readback. Other OS, MSRV and feature rows remain open. The reviewed Linux package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/linux-process-minimum-20261008T201200Z-6e2ba1d7/proof.md` additionally accepts this exact public-Engine assertion at Rust/Cargo1.77.2, `testing-environ,sys`, with unchanged oracles, reused original RED controls and fresh native GREEN/readback/reap. Other uncovered native/feature rows remain open. |
| X3 | `run_raw_captures_exact_stream_bytes_and_nonzero_exit_as_data`; `linux-process-options-proof.md` | Accepted for named Linux rows: exit 0/7 and exact raw bytes as result data. |
| X4 | `tests/sys_process.rs::run_preserves_argv_boundaries_without_shell_interpolation`; `.scratch/all-tickets/process-argv-evidence/attempt-01/proof.md` | Partial: Workhorse Linux x86_64/Rust 1.93.0 `testing-environ,sys` proves spaces and both quote kinds round-trip byte-for-byte through public `Engine::run` to a real child. Other OS, MSRV and feature rows remain open. The reviewed Linux package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/linux-process-minimum-20261008T201200Z-6e2ba1d7/proof.md` additionally accepts this exact public-Engine assertion at Rust/Cargo1.77.2, `testing-environ,sys`, with unchanged oracles, reused original RED controls and fresh native GREEN/readback/reap. Other uncovered native/feature rows remain open. |
| X5 | Same test and proof | Partial: the named Linux row proves `$HOME`, `|`, `;`, `&&`, and a command-substitution payload remain literal; its marker is absent. Other OS, MSRV and feature rows remain open. The reviewed Linux package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/linux-process-minimum-20261008T201200Z-6e2ba1d7/proof.md` additionally accepts this exact public-Engine assertion at Rust/Cargo1.77.2, `testing-environ,sys`, with unchanged oracles, reused original RED controls and fresh native GREEN/readback/reap. Other uncovered native/feature rows remain open. |
| X6 | Same test and proof | Partial: the named Linux row proves a trailing empty argument is preserved as a distinct NUL-delimited argv entry. Other OS, MSRV and feature rows remain open. The reviewed Linux package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/linux-process-minimum-20261008T201200Z-6e2ba1d7/proof.md` additionally accepts this exact public-Engine assertion at Rust/Cargo1.77.2, `testing-environ,sys`, with unchanged oracles, reused original RED controls and fresh native GREEN/readback/reap. Other uncovered native/feature rows remain open. |
| X7 | `scalar_run_with_cwd_works_without_collections`; options proof | Accepted for named Linux rows: valid cwd is observed through child output and independent host readback. |
| X8 | tests/sys_process.rs::missing_program_and_cwd_report_not_found_without_starting_child; .scratch/all-tickets/process-not-found-proof/proof.md | Partial: Workhorse Linux x86_64/Rust 1.93.0 proves public Engine run returns Io/NotFound for a missing cwd and the fixture record stays absent, with a valid-child control and independent reaping readback. Other OS, MSRV and feature rows remain open. The reviewed Linux package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/linux-process-minimum-20261008T201200Z-6e2ba1d7/proof.md` additionally accepts this exact public-Engine assertion at Rust/Cargo1.77.2, `testing-environ,sys`, with unchanged oracles, reused original RED controls and fresh native GREEN/readback/reap. Other uncovered native/feature rows remain open. |
| X9 | Scalar process proof records explicit `RECORD` override | Accepted for named Linux rows; other platform/feature combinations remain open. |
| X10 | Scalar process proof uses `env_clear` and explicit override | Accepted for named Linux rows; does not imply every environment edge case. |
| X11 | `tests/sys_process.rs::run_removes_inherited_environment_variable_from_public_child`; `.scratch/all-tickets/process-env-remove-evidence/attempt-01/proof.md` | Partial: Workhorse Linux x86_64/Rust 1.93.0 with `testing-environ,sys` proves the public Engine `run` path removes inherited `PATH` from a real child, with an inherited-value control, independent child-written readback, direct-child reaping, and a run-only sensitivity mutation. Other OS, MSRV, and feature rows remain open. The reviewed Linux package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/linux-process-minimum-20261008T201200Z-6e2ba1d7/proof.md` additionally accepts this exact public-Engine assertion at Rust/Cargo1.77.2, `testing-environ,sys`, with unchanged oracles, reused original RED controls and fresh native GREEN/readback/reap. Other uncovered native/feature rows remain open. |
| X12 | Raw capture and options proof | Accepted for named Linux rows: stdout and stderr are separately observed. |
| X13 | `process_supervisor_handles_large_simultaneous_io_and_exact_per_stream_caps`; `linux-process-io-proof.md` | Accepted only for the two sensitivity-backed Linux claims and recorded feature rows; not a complete IO or platform matrix. |
| X14 | `tests/sys_process.rs::run_io_contract_empty_output`; `.scratch/all-tickets/process-io-contract-evidence/attempt-01/proof.md`; `.scratch/all-tickets/darwin-io-contracts-20261008/attempt-01/proof.md` | Partial accepted: Workhorse Linux x86_64 and Darwin arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`. Both real public `run` cases return empty stdout/stderr and assert child exit/reaping; the combined review accepts reuse of the Linux wrong-output sensitivity control because the assertion source/helper are byte-identical. The zero-cap silent-output branch is distinct. Other OS, MSRV and feature rows remain open. |
| X15 | Raw capture/options proof | Accepted for named Linux rows: exact raw bytes and lossy text behavior, including nonzero exit. |
| X16 | `tests/sys_process.rs::run_io_contract_string_stdin_round_trip`; `.scratch/all-tickets/process-io-contract-evidence/attempt-01/proof.md`; `.scratch/all-tickets/darwin-io-contracts-20261008/attempt-01/proof.md` | Partial accepted: Workhorse Linux x86_64 and Darwin arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`, prove the exact 51-byte string stdin round-trip through public `run`, child-written PID/exit record and direct-child reaping. Linux assertion-control reuse is covered by the combined review. Spawned stdin evidence is not applicable. Other OS, MSRV and feature rows remain open. |
| X17 | `tests/sys_process.rs::run_io_contract_blob_stdin_round_trip_with_concurrent_output`; `.scratch/all-tickets/process-io-contract-evidence/attempt-01/proof.md`; `.scratch/all-tickets/darwin-io-contracts-20261008/attempt-01/proof.md` | Partial accepted: Workhorse Linux x86_64 and Darwin arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`, prove a varied 1 MiB `run_raw` Blob round-trip, exact concurrent 256 KiB child streams, child-written input readback and direct-child reaping. Linux assertion-control reuse is covered by the combined review. Other OS, MSRV and feature rows remain open. |
| X18 | `unit_stdin_means_immediate_eof`; options proof; `.scratch/all-tickets/darwin-x18-unit-stdin-20261008/proof.md` | Partial accepted (combined review READY 2026-10-08): named Linux rows and Darwin arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys` prove unit stdin produces immediate EOF through the public Engine and a real child, with expected RED/GREEN, child-record readback, and direct-child reaping. Other OS, feature, and MSRV rows remain open. |
| X19 | Deadline tests; `linux-managed-deadline-proof.md`, options proof, and Darwin `.scratch/all-tickets/darwin-x19-deadline-20261008/proof.md` | Partial (combined reviews READY for the direct public-Engine timeout matrix on Linux x86_64 and Darwin arm64/macOS 27.0.1: standard `testing-environ,sys`, `no_float`, default-float `sync`, and `sync,no_float`, each at Rust/Cargo 1.77.2 and 1.93.0. The Linux attempt-10 and named Darwin rows bind the same test/lock and prove timeout classification, bounded/partial output, real-child record readback and termination/reaping. Existing named Linux managed-path cases remain separately applicable. The 100 ms API deadline is not a scheduler-independent latency guarantee. Other X19 test paths and any unproven OS/feature/MSRV rows remain open; this does not close all of X19, Ticket 03, or A–F. |
| X20 | Scalar success and `linux-managed-success-proof.md`; Darwin `.scratch/all-tickets/darwin-x20-20261008/attempt-01/proof.md`; Linux `.scratch/all-tickets/linux-x20-direct-20261008/attempt-02/proof.md` | Partial (combined independent review READY 2026-10-08): normal completion before deadline is accepted for the named Linux x86_64 rows on Rust/Cargo 1.77.2 and 1.93.0 across `testing-environ,sys`, `no_float`, `sync`, and `sync,no_float`, plus Darwin arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`. The same public-Engine test/lock is bound; expected `timed_out` assertion RED/restored GREEN, child-record readback and direct-child ESRCH are verified. Existing Linux managed-path proof remains separately applicable. The reviewed Darwin package-minimum addendum `.scratch/rhai-wayfinder-replan-20261008/results/darwin-process-minimum-20261008T153851Z-a0169b56/proof.md` additionally accepts the exact 1.77.2 baseline/representative process selectors and three promised Darwin1.93 sync/no_float endpoint rows. Corrected only_i32/no_float normal-output, host-cap and real signal/reap selectors pass on Darwin/Linux1.77.2. Other X20 paths, platforms, features, and MSRVs remain open; this does not close Ticket 03 or A–F. |
| X21 | `process_output_limit_is_primary_and_retains_each_stream_prefix_at_n_plus_one`; `zero_output_cap_reports_output_limit_with_an_empty_retained_prefix`; `linux-process-options-proof.md`; `linux-process-overlap-proof.md`; Darwin `.scratch/all-tickets/darwin-x21-cap-20261008/attempt-01/proof.md` | Partial (combined independent review READY 2026-10-08): accepted Linux cap cases and assertion controls on the five named feature rows at Rust/Cargo 1.77.2; Linux same-step overflow-vs-deadline precedence remains limited to DirectChild/Managed. Also accepted native Darwin arm64/macOS 27.0.1: zero-cap test on `testing-environ,sys`, `sync`, `no_float`, and `sync,no_float` at Rust/Cargo 1.77.2 and 1.93.0, plus cap+1 stdout/stderr prefix test on standard and `sync` at both toolchains. The Darwin run binds source/test/lock and proves real-child record readback and reaping. Also accepted: native Darwin arm64/macOS 27.0.1, Rust/Cargo 1.77.2, `testing-environ,sys,unchecked` host-cap case `process_script_output_option_cannot_raise_the_host_cap`; expected wrong-prefix RED101 and restored GREEN0 cover stdout and stderr, with independent child-record/reap checks before the exact 4096-byte prefix assertion. Source SHA-256 `a47197f8a2dd7cbdd59a4f1627715721129b62553c0adabc7a847b933f0c012a`, lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`; combined review PASS. Evidence: `../.scratch/all-tickets/darwin-unchecked-host-cap-20261009/attempt-02.md`. Other features, platforms, toolchains, process causes and paths remain open; this does not close all of X21, Ticket 03, or A–F. |
| X22 | `run_reports_a_real_unix_child_signal_without_an_exit_code`; Linux `.scratch/all-tickets/process-signal-evidence/proof.md`; Darwin `.scratch/all-tickets/darwin-signal-x22-20261008/proof.md` and `.scratch/all-tickets/darwin-x22-signal-20261008/attempt-01/proof.md` | Partial (combined review READY for Linux standard rows on Rust/Cargo 1.93.0 and 1.77.2, Darwin standard row on Rust/Cargo 1.93.0, and seven additional Darwin rows): native Darwin arm64/macOS 27.0.1 proves the real public-Engine SIGKILL child reports `success=false`, `code=()`, `signal=9`, is not timed out, has complete output, and is independently reaped (`ESRCH`) on Rust/Cargo 1.77.2 (`testing-environ,sys`, plus `sync`, `no_float`, and `sync,no_float`) and 1.93.0 (`sync`, `no_float`, and `sync,no_float`). Source, test, lock, environment, raw logs, status files and cleanup are bound in the new proof; combined review confirms the earlier same-assertion RED applies. The `--nocapture` helper exit-1 was an output-shape check after Cargo completed, not a test failure. Other Unix platform, toolchain and feature rows remain open; X22 and Ticket03 are not complete. |
| X23 | Shared-child and `linux-process-example3-proof.md`; Darwin `.scratch/all-tickets/darwin-process-example-20261008/attempt-01/proof.md` | Accepted for named Linux rows: real spawn/wait, result map, clone snapshots and cached results. Also accepted for the named Darwin example row (arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `sys`): public Engine with real child-file readbacks, pending wait and identical cloned-handle results; expected RED/GREEN passed and scoped cleanup was verified. Combined independent review READY. The two affected Darwin Rust 1.77.2 integer-only example rows (`sys,no_float`, `sys,sync,no_float`) are also accepted: `.scratch/rhai-wayfinder-replan-20261008/results/example-20261008T090938Z-zmj63_0i/proof.md` binds saved expected-exit RED101/GREEN0, independent child-file/clone/ESRCH observations, combined review and exact scoped cleanup. These existing results were finalized without another build. Other Darwin lifecycle, features, MSRV and OS rows remain open. Also accepted native Linux x86_64 / Rust1.77.2 integer examples with `sys,no_float` and `sys,sync,only_i32,no_float`: `.scratch/rhai-wayfinder-replan-20261008/results/linux-integer-example-20261008T214557Z-0fde4a20/proof.md` binds two intended exit8 RED101 / restored7 GREEN0 pairs, same binary per profile, fresh run/spawn records, pending/clone snapshots, immediate ESRCH and independent exact cleanup. The same combined review accepts only these slices. The outer launcher bookkeeping failure is preserved with its unobserved runner exit; no replay or clean-launcher claim. This does not close full X23, R5 no_index, Windows or the release matrix. |
| X24 | `tests/sys_process.rs::direct_spawn_try_wait_returns_unit_until_child_exits`; Linux `.scratch/all-tickets/process-try-wait-evidence/x24-try-wait-20261007-1705z-6a92d/attempt-03/` and `attempt-04/proof.md`; Darwin `.scratch/all-tickets/x24-darwin-trywait-20261008/attempt-02/proof.md` | Partial (combined reviews READY 2026-10-07/08): Workhorse Linux x86_64, Rust/Cargo 1.93.0 and 1.77.2, `testing-environ,sys`, plus Darwin arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`, prove pending `try_wait` returns unit and terminal result is observed directly before `wait`, with cached exit and independent ESRCH readback. Darwin raw expected RED/GREEN targets are valid; the wrapper status 1 was a separate-output-token validator error, superseded by the proof record. The Darwin RED mutates the cached `wait()` expectation; it does not claim a separate mutation of every `try_wait` assertion. Other OS, MSRV, and feature rows remain open. |
| X25 | Shared-child and managed-kill proofs; Darwin `.scratch/all-tickets/darwin-x25-kill-20261008/proof.md` | Partial (combined review READY 2026-10-08): Workhorse Linux named cases and native Darwin arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys` prove public managed `spawn` → `kill` → bounded `wait`, non-unit unsuccessful report, independent leader/worker/leaf ESRCH readbacks, and unrelated sentinel survival followed by exact reaping. Darwin expected RED/GREEN and scoped cleanup are recorded. Other OS, MSRV, feature, and remaining ticket 03 rows remain open. |
| X26 | Shared-child proof repeats kill after completion; Darwin `.scratch/all-tickets/darwin-x26-x27-20261008/proof.md`; current Darwin `.scratch/all-tickets/darwin-child-drop-20261009/attempt-01.md` | Partial (combined review READY 2026-10-08): named Linux row proves repeated kill is harmless and cached snapshots persist. Darwin arm64/macOS27.0.1 Rust/Cargo1.93.0 `testing-environ,sys` has expected RED/GREEN for repeated post-completion kill, stable cached snapshots, exit record and ESRCH. Fresh Darwin Rust/Cargo1.77.2 base-feature run also passes 1/1 with exit17, stable snapshots, two kills and exact ESRCH; accepted byte-identical 1.93 RED applies. Other platforms/features/MSRV remain open. |
| X27 | Shared-child and managed final-drop proofs; Darwin direct-child `.scratch/all-tickets/darwin-x26-x27-20261008/proof.md`; current Darwin `.scratch/all-tickets/darwin-child-drop-20261009/attempt-01.md` | Partial (combined review READY for direct-child Darwin row, 2026-10-08): named Linux direct/managed evidence remains applicable. Darwin27.0.1 Rust/Cargo1.93.0 `testing-environ,sys` expected RED/GREEN proves nonfinal clone usability and direct kill-on-drop termination with ESRCH. Fresh Darwin Rust/Cargo1.77.2 base-feature run adds the named direct-child row with operational nonfinal probe, final-drop termination and controller/fixture/watchdog ESRCH, reusing the byte-identical fixture RED. Managed final-clone-drop remains historical at e5b55460… / macOS27.0 and is not fresh at this source/environment. Other platform/feature/MSRV rows remain open. |
| X28 | `linux-drop-false-native2-proof.md`; historical Darwin direct/managed tests in `.scratch/all-tickets/macos-process-refresh-evidence/macos-process-refresh.pvRbIs.cargo.sys_process.log`; Darwin current rows `.scratch/all-tickets/darwin-drop-false-unchecked-20261009/attempt-06.md`, `.scratch/all-tickets/darwin-process-lifecycle-base-20261009/attempt-01.md` | Partial (combined review READY 2026-10-08): exact Linux direct/managed retention tests and independent group readback are accepted at the named default Linux row. Historical full Darwin `sys_process` at `e5b55460…`, arm64/macOS27.0, Rust/Cargo1.93.0 includes direct and managed retention, live challenge/readback, natural completion, ESRCH and sentinel preservation; review found inputs applicable through `d3281a7…`. Fresh Darwin27.0.1/Rust1.77.2 rows are accepted for `testing-environ,sys` and `testing-environ,sys,unchecked`, with RED sensitivity, exact cleanup, live challenge, 524288-byte capture per stream and natural ESRCH. Windows, other features/toolchains remain open. |
| X29 | `tests/fixtures/sys_process_shared_child_contract.rs::script_throw_drops_and_reaps_a_live_child`; `.scratch/all-tickets/x29-script-throw-20261007-9aec531ea61d42359544757b363f2422/proof.md`; Darwin `.scratch/all-tickets/darwin-process-lifecycle-base-20261009/attempt-01.md`, `.scratch/all-tickets/darwin-x29-unchecked-20261009/attempt-01.md` | Partial (combined review READY 2026-10-08). Accepted Workhorse Linux x86_64 rows at Rust/Cargo1.93.0 and1.77.2, and Darwin arm64/macOS27.0.1 at Rust/Cargo1.93.0, `testing-environ,sys`: challenge, live `try_wait`, wrong-message rejection and independent ESRCH. Fresh Darwin/Rust1.77.2 rows pass for `testing-environ,sys` and `testing-environ,sys,unchecked`, with exact child/controller readback and watchdog closure. The unchecked run's outer runner exit status is unknown due post-test bookkeeping; scope cleanup and Cargo result are verified and the limitation is recorded. Other OS/features/MSRV remain open. |
| X30 | `tests/sys_process.rs::repeated_public_run_calls_keep_fd_count_stable`; `.scratch/all-tickets/process-fd-stability-evidence/x30-fd-stability-20261007-1530z/attempt-06/` | Partial (combined review READY 2026-10-08 for current-source applicability): attempt 06 proves that the exact-filtered acceptance test isolates its `/proc/self/fd` census in a fresh process, where 200 sequential public `run` calls leave the count unchanged; a wrong-count control fails and restored GREEN passes. The parent enforces a 60-second child deadline and terminates/reaps on timeout. Review confirms the X30 test and census helpers remain unchanged at `c644085c`. `run_map` adds Managed-scope fault setup and takes fault state earlier; the test uses default DirectChild scope, no injected fault and no custom cwd, so the changed setup does not alter its descriptor path. This remains applicable to Linux x86_64, Rust/Cargo 1.93.0, `testing-environ,sys`; other OS, MSRV and feature rows, including Windows handle stability, remain open. The same combined independent review additionally accepts native LLLM Linux x86_64 / Rust/Cargo1.77.2, testing-environ,sys: .scratch/rhai-wayfinder-replan-20261008/results/linux-x30-minimum-20261008T223319Z-c8818e49/proof.md. The exact committed-source GREEN executes the real isolated200-call census with tasks3→3/fds4→4/workers1→1, reuses the byte-identical original wrong-count RED101, and exports runner0 plus exact runtime/scope/27-identity cleanup. No other OS/features or full X30/matrix closure follows. |
| X31 | `process_representation_is_send_sync_and_shareable`; `.scratch/all-tickets/linux-shared-child-proof.md`; `.scratch/all-tickets/linux-wait-entry-proof.md`; `.scratch/all-tickets/linux-wait-entry-review.md`; `.scratch/all-tickets/linux-wait-entry-evidence-88/`; `.scratch/all-tickets/linux-wait-entry-outer-evidence-88/`; `.scratch/all-tickets/linux-shared-child-evidence-87/blocking-entry-current/proof.md`; Darwin `.scratch/all-tickets/darwin-x31-wait-entry-20261008/attempt-02/proof.md` and `review.md`; Darwin `.scratch/all-tickets/darwin-x31-wait-entry-20261008/attempt-05/proof.md` and `review.md` | Partial (combined reviews READY 2026-10-08): existing proof accepts shared representation and concurrent cancellation/wait for named Linux Rust/Cargo 1.77.2 rows (`testing-environ,sys`; `testing-environ,sys,sync`; and `testing-environ,sys,sync,no_float`). Reviewed blocking-entry evidence adds the 1.77.2 `sync` and `sync,no_float` rows: expected assertion RED/restored GREEN, exact test-function byte identity at source `08507d6…` and `c644085c`, and applicable wait/kill behavior with cleanup readback. The current-source native Linux x86_64 Rust/Cargo 1.97.1 `testing-environ,sys,sync` test also directly observes entry into the public blocking wait before cancellation, waiter wakeup and independent PID reaping. Combined review accepts the native Darwin arm64/macOS 27.0.1, Rust/Cargo 1.93.0 blocking-entry rows at source `05320c2c9` for `testing-environ,sys,sync` and `testing-environ,sys,sync,no_float`: both expected assertion REDs and restored GREENs observe public wait entry before cancellation, waiter wakeup and exact-child `ESRCH` cleanup; the shared lock and environment are recorded in `attempt-02/proof.md`. The combined review also accepts the two native Darwin arm64/macOS 27.0.1 feature rows at Rust/Cargo 1.77.2 in attempt 05: pinned source and lock, expected assertion RED/restored GREEN, positive nonterminal wait-entry observation, cancellation/wakeup, exact-child `ESRCH` cleanup and scoped resource readback are recorded. Attempts 03/04 stopped in unfiltered metadata before the test and are infrastructure failures, not product results; attempt 05 used direct locked targeted tests. Attempt 01's compile error is a setup failure and is excluded as product evidence. Other OS, non-sync blocking-entry, MSRV and feature rows remain open. |
**Additional Linux shared-Child acceptance (2026-10-09):**
`../.scratch/rhai-wayfinder-replan-20261008/results/linux-shared-child-contracts-20261009T2025Z/combined-review.md`
accepts four standard and five sync exact selectors on Workhorse Linux x86_64,
Rust/Cargo 1.77.2, bound source `34e0fa61…` and lock `2ba4b3a0…`. It adds
meaningful blocked-stdin/wait-snapshot, shared clone lease, both final-drop policies,
script-throw cleanup and sync shared-handle result/reap evidence. The false-policy
final-drop control is in attempt03; the true-policy final-reap control is attempt06;
unchanged matching GREENs are reused from attempt02. The packet's before-call sync
notification is not actual wait-entry proof. Reuse the separately reviewed X31 Linux
`sync`/`sync,no_float` Condvar-entry rows only under their existing exact source-binding
review. These additions do not close X23-X31 or A-F beyond the named Linux rows.

| X32 | `tests/sys_process_windows.rs` | Open: no native Windows embedded-quote argv reconstruction test. |
| X33 | `tests/sys_process_windows.rs` | Open: no native Windows `.exe` suffix/PATH resolution test. |
| X34 | Managed deadline, output-limit, kill, final-drop and escaped-pipe proofs | Partial: selected Linux managed cancellation cases are accepted; exact platform/feature/fault breadth and Windows Job behavior remain open. |
| X35 | Managed success/held-zombie tests and `linux-managed-success-proof.md` | Partial: Linux managed leader-exit/worker closure is accepted; DirectChild distinction and other platform/feature rows need their own applicable proof. |
| X36 | `.scratch/all-tickets/x36-managed-scope-setup-20261008/proof.md` | Partial: Workhorse Linux x86_64, `testing-environ,sys`, proves public `run`/`spawn` cleanup for injected failure before and after successful `setpgid` (Rust/Cargo 1.96.0 and 1.97.1), real `fchdir` `EBADF`, and kernel-generated `setpgid` `EPERM` after the child becomes a session leader (Rust/Cargo 1.97.1). Restored runs prove no marker execution, exact PID/group absence and reservation retirement; attempts 07/08 pass all six affected setup tests on Rust/Cargo 1.97.1/1.77.2. Attempt 09 adds a targeted expected mutation RED and restored GREEN for the kernel-denial assertion on Rust/Cargo 1.77.2; combined review is READY for this named Linux row. Attempt 10 adds the named Darwin arm64/macOS 27.0.1 kernel-denial case at Rust/Cargo 1.93.0 with expected RED/restored GREEN and independent process readback; combined review is READY. Other Darwin failure points, platforms, features and MSRVs remain open. |
| X37 | Managed group/sentinel tests and accepted Linux managed proofs | Partial: named Linux host/sentinel survival is accepted; Windows Job membership and broader native rows are open. |
| X38 | Linux `.scratch/all-tickets/linux-managed-escaped-pipe-proof.md`; Darwin test `tests/sys_process.rs::managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes`; Darwin `.scratch/all-tickets/darwin-x38-20261008/attempt-03/` | Accepted for the named Linux escaped-reader case and the named Darwin assertion-sensitivity row (arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`). Darwin expected RED=101 and restored GREEN=0, independent pipe/process observations and exact cleanup readback passed; combined review READY. Other OS, feature, and MSRV rows remain open. |

The crosswalk above preserves rather than reduces the original contracts. It is
an applicability map, not new execution evidence. Package B remains open, and
all partial/open rows still require their listed real observations at an
applicable revision.

### 6.8 Coverage check — no open requirement removed

| Original requirement inventory | Preserved closure route |
|---|---|
| Ticket01 public API, independent observations, meaningful RED, isolation and cleanup | Applies to A–F; no mock/compile-only closure. |
| Ticket02; P1–P9/P12/P14, E1–E5, F1–F23 | Existing foundation proof retained; native/platform/feature gaps and any invalidated path assertions close through C/D/F. Includes non-UTF8, OS-selected roots, unrestricted symlinks and macOS aliases. Two system-prefix alias assertions are reviewed/integrated at `ad980d80...`; attempt 01 records the reviewed passing full Darwin `sys_policy` target (26 tests, including five root-path cases). This closes only the macOS F23 sys-policy slice; all remaining OS/feature rows stay open. |
| Ticket03; P2/P10/P11/P13, X1–X38 | A/B plus native C/D and affected F rows: stdin, caching, run/raw/spawn/kill/drop, fault/setup/no-primary/first-cause, managed cancellation/completion, honest incomplete cleanup, unrelated host/sentinel and escaped pipe. Linux X38 and the named Darwin X38 assertion row are accepted only at their listed scopes; remaining platform, feature and MSRV rows stay open. No stopped criterion is declared done. |
| Compatible shared file handles and rhai-fs divergences | Existing implementation/proof retained; API docs E and native/feature/readback gaps C/D/F. Includes bounds, negative reads and unchecked behavior. |
| Tickets04/05 TCP authority/API | Accepted separate connect/listen grants, numeric IPv4/IPv6, port0 listen, bytes/text/partial progress/EOF/half-close, clone close, resource limits and sync/cancellation remain; existing Linux proof plus missing C/D/F native/feature rows. The new Darwin test proves only one default-feature connect/read/write coexistence path with independent peer readback and typed denial. No DNS/UDP/HTTP/TLS added. |
| Ticket06; R1–R7 and release proposal | E/F preserve compatibility, metadata/docs/examples, core1.66/optional1.77.2, explicit no_std/no_object/WASM rejection, semantic feature matrix, native three-OS scope and source/dependency provenance. R4's historical alternative is resolved by rejection, not a new tuple API. |
| Process performance/diagnostics and resource safeguards | Accepted narrow Linux performance and lifecycle diagnostics remain with measurement scope; uncovered native requirements C/D/F. No duplicate benchmark solely for this revision. |
| Owner boundaries and repository outcome | No arbitrary-untrusted sandbox claim, parent env mutation, unrelated features, Actions enablement or publishing. Verified integration only to hoppworks/rhai main, lowercase hoppworks attribution, foreign work preserved. The owner explicitly authorized atomic commit and push of this verified package to the fork; no public-upstream write is authorized. |

All P1–P14, E1–E5, F1–F23, X1–X38, R1–R7 and the six accepted local ticket contracts
remain represented. This crosswalk is a coverage plan, not an executed acceptance
matrix or closure count. Historical implementation notes and estimates follow.

### 6.9 Historical phases — retained, superseded as execution instructions

| Phase | Deliverable | Exit criteria | Effort |
|---|---|---|---|
| 0 | This document; D1 and D2 signed off | owner reply | done |
| 1 | `sys` feature, `SysConfig`, `SysError`, env and fs functions, policy enforcement via `cap-std`, tests P1-P12, E1-E3, E5, F1-F18, R1, R2, R7 | `cargo test --features sys` green on Linux; `cargo build` without `sys` unchanged | done (30 tests in `tests/sys_policy.rs`, `tests/sys_env.rs`, `tests/sys_fs.rs`; verified under `sys`, `sys,sync`, `sys,no_index`, `sys,metadata,serde`, `sys,no_float,only_i32` and a combined minimal set) |
| 2 | `run`, `run_raw`, `spawn`, `Child`, timeout, output cap, stdin, kill-on-drop, self-reexec fixture, tests X1-X31, R3-R5 | green on Linux and macOS | one session |
| 3 | Windows pass: batch refusal, quoting, path quirks, non-UTF-8 rows, tests P13, E4, F19-F21, X32-X33; CI matrix rows | CI green on all three OS | half a session plus CI turnaround |
| 4 | Streaming file handles compatible with rhai-fs (`open_file`, `read_string`, `read_blob`, `write`, `seek`), doc-comments, `examples/sys.rs`, CHANGELOG entry, `README` section | R6; example runs | one session |
| 5 | Optional: `net` package as its own feature and plan; upstream discussion on rhaiscript/rhai issue 451 | separate document | not scheduled |

Owner time across phases 1 to 4: about three hours, mostly API review after phase 1 and
after phase 2. Names are cheap to change before phase 4 and expensive after.

## 7. Resolved questions

All five questions put to the owner on 2026-09-29 were answered with the recommendation:
in-tree behind `sys` (D1), deny-by-default (D2), `kill_on_drop` true (D9), MSRV 1.77.2 for
the gated feature only (D8), and `sys` incompatible with `no_object` via `compile_error!`
(R4, now part of D10).

## 8. Implementation notes from phase 1

- Layout: `src/packages/sys/{mod,config,error,env,fs}.rs`. Functions are closures capturing
  a `Shared<SysState>` and are registered through `FuncRegistration`, because plugin
  functions written with `#[export_module]` cannot carry per-instance configuration.
- `SysPackage::new(config)` returns `Result`, failing early when a root cannot be opened.
  `Package::init` is a no-op for the same reason.
- At that review's pinned source, absolute script paths matched configured and
  canonical root prefixes, while the equivalent macOS-prefix test spellings were
  not actually distinct under the scoped TMPDIR. The later F23 test correction
  and its narrow RED/GREEN proof are recorded in §§6.3 and 6.6; remaining F23
  variants and matrix rows stay open.
- Relative paths are checked lexically for `..` escapes before `cap-std` sees them, so the
  common case fails without touching the filesystem (P6); symlink escapes are caught by
  `cap-std` and mapped to `Denied` by inspecting its `PermissionDenied` error (P7).
- `read_file` is lossy on invalid UTF-8; `read_file_blob` is exact. `metadata().modified`
  is Unix seconds as `INT`, since Rhai's own time type is a monotonic `Instant`.
- Inside a confined root, symbolic links must have relative targets. `cap-std` treats an
  absolute link target as an escape even when it points back into the root. Documented in
  the module docs and covered by a test. The confined limitation remains accepted;
  unrestricted symlink handling has a reviewed defect and must satisfy F22.
- On Windows, `std::fs::canonicalize` returns verbatim paths (`\\?\C:\...`). Roots store
  the canonical form with that prefix stripped. The current configured-root lexical
  normalization is not the accepted contract for symlink/parent paths: P14 requires
  OS-selected root semantics. Wine evidence does not replace native Windows proof.
- Unrestricted mode currently opens the nearest existing ancestor as an ambient `Dir`.
  The review demonstrated that this imposes unintended symlink restrictions; F22
  requires ordinary host semantics. The mechanism is historical, not a design mandate.
- F19 requires a native filesystem that supports creating the non-UTF-8 fixture.
  The reviewed APFS fixture-creation failure is a coverage limitation; repair the
  fixture handling and obtain appropriate native evidence without weakening NotUtf8.

## Appendix A: precedents, condensed

What each reference contributed to sections 3 and 4. Nothing was copied; each row was
written against the contract above.

| Reference | Taken | Not taken |
|---|---|---|
| Rust `std::process::Command`, `std::fs` | API vocabulary (`env_clear`, `env_remove`, `current_dir`, `kill_on_drop`), non-zero exit as data, concurrent pipe draining in `output()`, `try_wait`, `ExitStatusExt::signal`, the self-reexec fixture pattern | nothing; this is the substrate |
| Deno `Deno.Command` and permissions | Options-object style, `--allow-run` and `--allow-read` as the authority model, `clearEnv`, signal degradation on Windows | async surface, `Deno.ChildProcess` streams |
| `cap-std` | Root-confined `Dir` handles; symlink-safe path resolution | its own I/O traits; scripts see strings only |
| rune-modules `process` | Confirmation that the builder style is awkward in a scripting binding; `kill_on_drop`; `Output` field names | builder API, tokio dependency |
| rhai-fs | Function names for overlapping fs operations, `Shared<Locked<File>>` handle pattern, `sync` handling | `PathBuf` opaque type in v0.1 |
| Lua 5.4 `io`/`os` and `testes/files.lua` | Failure-path cases: missing file, empty file, binary data, remove and rename errors, cleanup after many operations | `os.execute` and `io.popen` shell semantics |
| QuickJS `std`/`os` | Feature checklist: cwd, env, stdin/stdout/stderr control, `waitpid`, `stat`, `mkdir`, signals | fd-level API, POSIX-only errors |
| mruby `mruby-io`, `mruby-socket` | Confirmation that fs and net belong in separate optional packages | packaging and test layout (dictated by Cargo and Rhai here) |
| CVE-2024-24576 (Rust advisory) | D8 and P13 | |

## Appendix B: sources

- Rust `std::process`: https://doc.rust-lang.org/std/process/struct.Command.html
- Rust advisory for batch-file argument injection: https://blog.rust-lang.org/2024/04/09/cve-2024-24576.html
- Deno `Deno.Command`: https://docs.deno.com/api/deno/~/Deno.Command
- Deno permissions: https://docs.deno.com/runtime/fundamentals/security/
- cap-std: https://github.com/bytecodealliance/cap-std
- rune-modules process: https://github.com/rune-rs/rune/blob/main/crates/rune-modules/src/process.rs
- rhai-fs: https://github.com/rhaiscript/rhai-fs
- rhai-net (stalled, TCP only): https://github.com/emesare/rhai-net
- Lua 5.4 manual, I/O and OS libraries: https://www.lua.org/manual/5.4/manual.html#6.8
- Lua file tests: https://github.com/lua/lua/blob/master/testes/files.lua
- QuickJS `std` and `os` modules: https://bellard.org/quickjs/quickjs.html
- mruby gems: https://github.com/mruby/mruby/tree/master/mrbgems
- Original issue: https://github.com/rhaiscript/rhai/issues/451
