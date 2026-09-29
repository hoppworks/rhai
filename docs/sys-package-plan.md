# Rhai `sys` package: contract, requirements matrix, and plan

Status: draft for review. Branch: `claude/vibrant-sagan-3g1pxn` (this fork only, no upstream
submission yet). Supersedes the 2026-09-29 precedents survey; that survey is condensed into
Appendix A.

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
| D1 | Where the code lives | In-tree at `src/packages/sys/`, behind cargo feature `sys`, not part of `StandardPackage` or the `default` feature set. | Fastest path on this fork. Extracting to a `rhai-sys` crate later is mechanical, because the package only uses the public plugin API. | needs owner sign-off |
| D2 | Authority model | Host constructs `SysConfig` (fs roots, program allow-list, env policy, limits) and builds `SysPackage::new(config)`. `SysConfig::default()` denies everything; `SysConfig::permissive()` allows everything for trusted scripts. | Matches Deno's permission model and the "explicit authority" conclusion of the survey. Deny-by-default means forgetting to configure is safe. | needs owner sign-off |
| D3 | Filesystem confinement | Use the `cap-std` crate. Each configured root becomes a `cap_std::fs::Dir`; script paths resolve relative to a root and cannot escape it, including via symlinks. | Hand-rolled `canonicalize` + `starts_with` checks are racy against symlink changes. `cap-std` is maintained by the Bytecode Alliance and is the reference implementation of this idea. Optional dependency, pulled only by `sys`. | proposed |
| D4 | Process API shape | Options-map style, not a builder: `run(program, args)` and `run(program, args, options)` return a result map; `spawn(program, args, options)` returns a `Child` handle. | Rhai plugin methods on `&mut T` return unit, so builder chaining does not work without cloning. An options map is idiomatic Rhai, trivially serializable, and easy to test. Rune's process module shows the builder style and its awkwardness. | proposed |
| D5 | Error model | OS and policy failures raise `EvalAltResult::ErrorSystem` carrying a `SysError` (enum: `Denied`, `Io`, `Timeout`, `OutputLimit`, `NotUtf8`). Scripts catch them with `try`/`catch`. A non-zero exit code is data in the result map, never an error. | Mirrors Rust: `Command::output()` succeeds on non-zero exit. Hosts can downcast the boxed error to `SysError` for structured handling. | proposed |
| D6 | Paths | Strings in, strings out. Non-UTF-8 names raise `SysError::NotUtf8`. No opaque path type in v0.1. | Rhai strings are UTF-8, `OsString` is not. Keep the surface small; a `Path` type can come with rhai-fs compatibility in v0.2. | proposed |
| D7 | Timeout | Poll `Child::try_wait()` at a coarse interval (10 ms) until the deadline, then kill and mark `timed_out: true`. No extra thread, no extra dependency. | `std` has no `wait` with timeout. Polling is portable and adequate for script use. | proposed |
| D8 | Windows batch files | Refuse programs ending in `.bat` or `.cmd` unless the config sets `allow_batch_files`. Document MSRV 1.77.2 for the `sys` feature. | CVE-2024-24576: Windows batch arguments pass through `cmd.exe` and were injectable. `std` fixed quoting in 1.77.2; refusing by default removes the whole class. | proposed |
| D9 | Child drop semantics | `kill_on_drop: true` by default; option to disable. `Child` is `Shared<Locked<...>>` so it works under `sync`. | Scripts are short-lived and error-prone; an orphaned child outliving the script is the surprising outcome. Rust's `Child` neither kills nor reaps on drop, so the package must. | proposed |
| D10 | Feature gating | `sys` implies `std`. Combining `sys` with `no_std` or a wasm32 target is a `compile_error!`. | Nothing here can work without an OS. Failing loudly beats an empty package. | proposed |
| D11 | Output encoding | `run` returns `stdout` and `stderr` as strings, lossily converted. `run_raw` returns blobs. | Most scripts want text. Lossy conversion never fails; scripts needing bytes opt in. | proposed |
| D12 | rhai-fs compatibility | Where a v0.1 function overlaps rhai-fs (`cwd`, `exists`, `create_dir`, `remove_dir`, `remove_file`), keep the same name and argument order. Divergences are listed in the docs. | Two incompatible fs APIs in one ecosystem help nobody. | proposed |

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
(enforced by `cap-std`, not by string inspection).

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

## 4. Requirements and test matrix

Every row becomes at least one test. "Source" names the precedent that motivated the case;
tests are written from scratch against this contract. Phase numbers refer to section 6.

### 4.1 Policy (P)

| ID | Case | Expected | Source | Phase |
|---|---|---|---|---|
| P1 | Default config, any fs call | `SysError::Denied` | Deno permissions | 1 |
| P2 | Default config, `run` | `SysError::Denied` | Deno | 2 |
| P3 | Read on read-only root | succeeds | own | 1 |
| P4 | Write on read-only root | `Denied` | own | 1 |
| P5 | `remove_dir_all` on `ReadWrite` root | `Denied`; needs `ReadWriteDelete` | own | 1 |
| P6 | Path with `..` escaping root | `Denied`, and no fs access happened | cap-std, Lua `files.lua` | 1 |
| P7 | Symlink inside root pointing outside | `Denied` | cap-std | 1 |
| P8 | Absolute path inside root | resolves | own | 1 |
| P9 | Absolute path outside any root | `Denied` | own | 1 |
| P10 | Program not in allow-list | `Denied` before spawn | Deno `--allow-run` | 2 |
| P11 | `cwd` option outside fs roots | `Denied` | own | 2 |
| P12 | `env_var` not in allow-list | `()` | own | 1 |
| P13 | `.bat` / `.cmd` program on Windows, default config | `Denied` | CVE-2024-24576 | 3 |

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

### 4.4 Processes (X)

| ID | Case | Expected | Source | Phase |
|---|---|---|---|---|
| X1 | Program found, exit 0 | `success`, `code == 0` | all | 2 |
| X2 | Program not found | `Io` with `NotFound`, before any child exists | Lua, QuickJS | 2 |
| X3 | Exit code non-zero | `success == false`, `code == N`, no error raised | Rust `Command::output` | 2 |
| X4 | Arguments with spaces and quotes | fixture echoes argv exactly | Deno, Rust std tests | 2 |
| X5 | Argument containing `$HOME`, `|`, `;`, `&&` | passed literally, fixture sees the raw string | Lua `os.execute` (counter-example) | 2 |
| X6 | Empty argument `""` | preserved as an empty argv entry | Rust std tests | 2 |
| X7 | `cwd` option valid | fixture reports that directory | QuickJS `os.exec` | 2 |
| X8 | `cwd` option missing directory | `Io`, no child spawned | QuickJS | 2 |
| X9 | `env` override | fixture sees the value | QuickJS | 2 |
| X10 | `env_clear` | fixture sees only overrides | Rust `env_clear` | 2 |
| X11 | `env_remove` | fixture does not see the variable | Rust `env_remove` | 2 |
| X12 | stdout and stderr separate | each captured on its own | QuickJS | 2 |
| X13 | Both streams write 4 MiB interleaved | no deadlock, both complete | Rust `output()` uses concurrent reads | 2 |
| X14 | Empty output | `""` | Lua | 2 |
| X15 | Binary output | `run_raw` exact bytes; `run` lossy | own | 2 |
| X16 | stdin string | fixture echoes it back | QuickJS pipes | 2 |
| X17 | stdin blob 1 MiB | exact round trip, no deadlock while child also writes | own | 2 |
| X18 | stdin `()` | fixture sees EOF immediately | own | 2 |
| X19 | Timeout expires | `timed_out == true`, child gone, call returns within timeout + 1 s | own | 2 |
| X20 | Timeout not reached | normal result | own | 2 |
| X21 | `max_output` exceeded | `OutputLimit`, child killed | survey "output cap" | 2 |
| X22 | Child killed by signal (Unix) | `code == ()`, `signal == 9` | Rust `ExitStatusExt` | 2 |
| X23 | `spawn` then `wait` | same result map as `run` | Rune process | 2 |
| X24 | `spawn` then `try_wait` while running | `()`; after exit, result | Rune | 2 |
| X25 | `spawn` then `kill` then `wait` | terminated, no hang | Rune | 2 |
| X26 | `kill` twice | second is a no-op, no error | own | 2 |
| X27 | Drop `Child` while running, `kill_on_drop` true | child exits (Linux: verify via `/proc`), no zombie | own | 2 |
| X28 | Drop `Child`, `kill_on_drop` false | child keeps running; test reaps it | own | 2 |
| X29 | Script `throw` while child running | child cleaned up via drop | own | 2 |
| X30 | 200 sequential `run` calls | no fd or handle leak (Linux: `/proc/self/fd` count stable) | Lua cleanup tests | 2 |
| X31 | Under `sync` feature, `Child` shared across threads | compiles and works | Rhai `sync` | 2 |
| X32 | Windows: argument with embedded quote | argv reconstructed correctly | Rust std quoting rules | 3 |
| X33 | Windows: `.exe` suffix omitted | resolves via `PATH` | own | 3 |

### 4.5 Engine integration (R)

| ID | Case | Expected | Source | Phase |
|---|---|---|---|---|
| R1 | `sys` off | no symbols exported, no dependency compiled | Rhai feature conventions | 1 |
| R2 | `sys` + `no_std` | `compile_error!` | D10 | 1 |
| R3 | `sys` + `no_index` | `run` without args still works; array-taking overloads absent | Rhai cfg conventions | 2 |
| R4 | `sys` + `no_object` | result returned as Array or tuple type instead of Map, or feature marked incompatible | decision pending | 2 |
| R5 | `type_of` on `Child` | `"Child"` | Rhai time tests | 2 |
| R6 | `metadata` feature | doc-comments on every function render | Rhai conventions | 4 |
| R7 | `try { ... } catch (e)` around a denied call | `e` is a string starting with the `SysError` variant name | D5 | 1 |

## 5. Test infrastructure

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
- CI: `.github/workflows/build.yml` gains matrix rows
  `--features testing-environ,sys` and `--features testing-environ,sys,sync,no_index` on
  ubuntu, plus `--features sys` on the existing windows and macos jobs. The wasm32 rows
  must not include `sys`.

## 6. Phases

| Phase | Deliverable | Exit criteria | Effort |
|---|---|---|---|
| 0 | This document; D1 and D2 signed off | owner reply | done except sign-off |
| 1 | `sys` feature, `SysConfig`, `SysError`, env and fs functions, policy enforcement via `cap-std`, tests P1-P12, E1-E3, E5, F1-F18, R1, R2, R7 | `cargo test --features sys` green on Linux; `cargo build` without `sys` unchanged | one session |
| 2 | `run`, `run_raw`, `spawn`, `Child`, timeout, output cap, stdin, kill-on-drop, self-reexec fixture, tests X1-X31, R3-R5 | green on Linux and macOS | one session |
| 3 | Windows pass: batch refusal, quoting, path quirks, non-UTF-8 rows, tests P13, E4, F19-F21, X32-X33; CI matrix rows | CI green on all three OS | half a session plus CI turnaround |
| 4 | Streaming file handles compatible with rhai-fs (`open_file`, `read_string`, `read_blob`, `write`, `seek`), doc-comments, `examples/sys.rs`, CHANGELOG entry, `README` section | R6; example runs | one session |
| 5 | Optional: `net` package as its own feature and plan; upstream discussion on rhaiscript/rhai issue 451 | separate document | not scheduled |

Owner time across phases 1 to 4: about three hours, mostly API review after phase 1 and
after phase 2. Names are cheap to change before phase 4 and expensive after.

## 7. Open questions for the owner

1. D1: in-tree behind `sys`, or a separate workspace crate `rhai-sys` from the start?
   Recommendation: in-tree.
2. D2: deny-by-default confirmed? Recommendation: yes.
3. D9: `kill_on_drop` defaulting to true confirmed? Recommendation: yes.
4. D8: is documenting MSRV 1.77.2 for the `sys` feature acceptable, given the crate-wide
   `rust-version` is 1.66? Recommendation: yes, gated features may have their own floor.
5. R4: under `no_object` there is no Map. Mark `sys` incompatible with `no_object`
   (`compile_error!`), or return arrays? Recommendation: incompatible; nobody disables
   maps and wants a process API.

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
