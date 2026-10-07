# X22 real Unix child-signal proof

This is a partial acceptance for X22 only. It covers Workhorse Linux x86_64,
Rust/Cargo 1.93.0 and 1.77.2 with `testing-environ,sys`. Other Unix platforms
and feature rows remain open.

## Frozen inputs and execution

- Source archive SHA-256: `0ffccc22a21bcc178638356cae582129af3213f3cefcb3bdd18507745b5cd2b3`.
- Archive manifest SHA-256: `fe0a1e0fa6eef7c2b2bee695e780444e362ed4a5c8576ee2648b5ab1da8f34509`.
- `Cargo.lock` SHA-256: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- `tests/sys_process.rs` SHA-256: `a93f42a8708f854ff1a8569ebd9290d6a27fb2183b23a6600fd435e6d200d270`.
- Agent Skills revision: `14617043b70d1ba2d40b720832cbad294fa8c008`.
- Workhorse runner `tools/run_scoped.py` SHA-256:
  `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`.
- OS: Linux x86_64, kernel `7.2.7-ogc1.1.fc44.x86_64`.
- Preflight found no competing heavy process, 92,200,308 KiB available memory,
  and 610,170,155,008 free bytes on the scope filesystem.
- Focused command, run from the frozen source root:
  `cargo test --locked --features testing-environ,sys --test sys_process run_reports_a_real_unix_child_signal_without_an_exit_code -- --exact --nocapture --test-threads=1`.

One bounded scoped invocation ran the sensitivity control and restored test. The
scoped runtime held Cargo outputs and caches and was removed by the runner at
exit. Raw admission, command, version, source-hash, RED, GREEN and export
readbacks are preserved under `attempt-02/`.

## Acceptance observations

The deliberate control changed the expected signal from 9 to 10. It exited 101
at the intended assertion after observing `left: 9`, `right: 10`; this is
assertion-sensitivity RED, not a product failure. The restored test exited 0
with exactly one passing test.

The test invoked `/bin/sh` through the public Rhai Engine process API. The child
wrote its own PID before sending itself SIGKILL. The Engine result was
`success=false`, `code=()`, `signal=9`, `timed_out=false`, with both captured
streams complete. After return, the test independently read the child's PID and
observed `kill(pid, 0) == -1` with `errno=ESRCH` (3), establishing that the child
was no longer present. The recorded test output includes PID `1688955`.

## Attempt and resource history

The first preflight could not execute Rustup through the inherited
`/root/.cargo/bin` path. A bounded runner-entry attempt then exited 126 because
the canonical Workhorse Python runner is not executable as a file; invoking it
with `/usr/bin/python3` passed the scoped no-op. Native allocation 1 started
Cargo but stopped before compilation or assertions when `rustc -vV` received
EACCES through the same inaccessible root shim. Its status 101 was infrastructure,
not test RED; no compiled artifact was reusable. The exact installed Workhorse
Rust proxy path and `RUSTUP_TOOLCHAIN=1.93.0` were then used for native allocation
2. Its expected RED and restored GREEN completed as described above.

Across this route: two native allocations, one native pre-assertion
infrastructure stop, one expected assertion-sensitivity RED, one passing GREEN,
zero product corrections. Before the native allocations, the preflight Rustup
path and runner file-mode issues each required one bounded setup repair. No
foreign process or shared service was changed.
After runner exit, the scoped runtime was absent and no Cargo/rustc or scoped
runner process remained. After exporting and hash-checking all 15 remote result
files, the exact owned Workhorse scope
`/var/home/workhorse/.local/share/agent-builds/rhai/x22-sigkill-20261007-a6df9e198fb3`
was retired. The final readback found the scope absent, no runtime or heavy
process, and 610,308,501,504 free bytes. The machine readback is preserved in
`attempt-02/cleanup-readback.json`. The local source archive, manifest and
launch helpers were removed after their pinned hashes and run outputs were
preserved.

This proof does not close the full X22 matrix, prove non-SIGKILL signals, or
establish macOS, Windows, other feature, or MSRV behavior.

## Post-run review correction and proof applicability

The combined independent review found that the test used Unix-only APIs while
its original compile gate excluded only `no_index`. The test is now gated with
`cfg(all(unix, not(feature = "no_index")))`. This is a compile-selection guard;
the test body and assertions are unchanged. On the tested Linux target `unix`
is enabled and `no_index` is disabled, so the frozen Linux run still exercises
the identical body and remains applicable. The guard prevents this Unix-specific
test from being compiled on Windows. No Windows run or broader platform
acceptance is claimed. The combined reviewer rechecked this correction and
returned READY without a build. The reviewed current `tests/sys_process.rs`
SHA-256 is `42afe230d8c386d77a3738a6a8bcd9ab32f946946eec70f93466060fbf5bb0f9`;
the frozen run hash above remains the original tested input, and the sole
post-run change is this compile-selection attribute.

## Additional Linux/MSRV acceptance (attempt-03)

- Source commit: `33fcfe2dce717f6df8c4d6f9dec248bce27c1a9b`.
- Source archive SHA-256: `752ce732a8480f3f19710d11f0f1e5e8e5231dc7f0f933bc4af3c3d95cba2499`.
- `Cargo.lock` SHA-256: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- `tests/sys_process.rs` SHA-256: `7ddc87f6e4b57d61d077445a81f1c3ef2f2e54cb35ac8c90a7ed328245d14017`.
- X22 test block SHA-256: `782758e80015a099f35d295aa1aa2a8a3cb0f7d3d571cb94a306073ca77b64ab` (2,238 bytes); the block in current HEAD and the archived source is byte-identical. The whole-file hash changed only because later tests were added.
- Agent-Skills Main: `0e846bfc577a51bd1a98a5606966aecda40320c2`, containing requested revision `35ba734135a64100b891f422d4ced9d76795ab57`. The Workhorse `tools/run_scoped.py` SHA-256 is `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`.
- Workhorse: Linux x86_64, kernel `7.2.8-ogc5.1.fc44.x86_64`, Rust/Cargo `1.77.2`.
- Fresh admission immediately before launch observed 32 CPUs, load averages `0.77/0.70/0.30`, 89,788,977,152 bytes available memory, and 663,682,400,256 free bytes. No Cargo or QEMU process was active. The admission reserved 16 GiB each for memory and disk plus an estimated 2 GiB additional build peak.
- Focused command: `cargo test --locked --jobs 2 --features testing-environ,sys --test sys_process run_reports_a_real_unix_child_signal_without_an_exit_code -- --exact --nocapture --test-threads=1`.
- Rust/Cargo 1.77.2 returned 0 with exactly one passing test. The public Engine result reported `success=false`, unit exit code, signal 9, no timeout, complete stdout/stderr, and child PID `33629`; the independent post-return `kill(pid, 0)` readback was `-1` with `errno=ESRCH` (3). The existing attempt-02 wrong-expectation sensitivity proof applies because the tested block and assertions are unchanged.
- The runner's private Cargo target/cache runtime peaked at 1,267,691,988 bytes and was removed automatically. All remote output files passed local SHA-256 readback. After export, the exact owned scope `/var/home/workhorse/.local/share/agent-builds/rhai/x22-sigkill-msrv-20261007-7dac936ff957` was removed; the cleanup receipt records no active process and confirms the path is absent. The shared Rust 1.77.2 toolchain remains untouched.
- Raw admission, compiler versions, command output, extracted source/lock hashes, archive-to-HEAD test-block identity, output checksums and cleanup receipt are preserved under `attempt-03/out/`.

This adds only the named Workhorse Linux x86_64 Rust/Cargo 1.77.2 row. Other Unix platforms and feature rows remain open; no broader X22 matrix is claimed.
