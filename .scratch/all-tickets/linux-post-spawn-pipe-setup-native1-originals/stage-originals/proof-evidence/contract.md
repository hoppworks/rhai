# Linux post-spawn pipe-setup failure proof contract

Source-only preparation for the existing public-Engine regression test. This package is distinct from the stopped stdin and Native2 work and does not change production source.

## Frozen inputs and target

- Accepted source revision: `523608648dcae99bc0f6b46eaf2bb91fa4ecc752`.
- Accepted source archive: SHA-256 `998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b`.
- Accepted compatible `Cargo.lock`: SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- Test source `src/packages/sys/process/unix.rs`: SHA-256 `1b60751c6d9ed695f79edc4f8a7972338274684ef53583bd1ea1009c1aca822a`; Git blob `a80a4fb2e15f1331bd688e79a1d8fa9b8673b4da`.
- Existing test: `packages::sys::process::unix::tests::post_spawn_pipe_setup_failure_preserves_cause_and_reaps_child`.
- Features: `testing-environ,sys`, retaining default float and index.
- Native target: Linux x86_64, Rust/Cargo 1.77.2.

The test invokes the real public `Engine` and registered `SysPackage`, starts `/bin/sh`, and independently releases and reaps its nested child. In each process, the inner ESRCH/owner-retired receipt precedes the inner semantic assertions; the outer fixture waits for that child to exit and be reaped, prints its own ESRCH receipt, then checks the nested status. The two captured streams plus these source-ordered checkpoints establish the named RED assertion and both receipts without inventing cross-stream timestamps. The recipe reuses these receipts and adds no product test or source change.

## Required run sequence

Run the exact named test three times in one private extracted source tree, restoring and hash-checking the accepted test source between independent overlays, always with `--locked --lib --features testing-environ,sys ... --exact --nocapture --test-threads=1`:

1. Wrong cause: change only the expected configure-pipe error string. Require status 101, both ordered post-reap receipts, and the named `primary cause must remain configure-pipe Io` assertion failure.
2. Wrong incomplete report: restore the exact accepted source, invert only `!report.stdout_complete()`, and require status 101, both ordered receipts, and the named `setup failure must not fabricate EOF or timeout completion` assertion failure.
3. Restored GREEN: restore and hash-check the exact accepted test source, then require status 0 and the single named test passing with both receipts.

Each overlay starts from pristine source. Pin each overlay hash and record stdout, stderr, status, command argv, and restoration readback. A RED control must include the inner intended assertion and outer nested-test failure wrapper, plus exactly one of each post-reap receipt in source-defined order; an earlier setup failure without those records is invalid. Keep command output and samples in the scoped runtime until the launcher exports them.

## Stage, custody, and retirement

Unique proposed paths are `/root/rhai-linux-post-spawn-pipe-setup-523-20261004` and `/root/.local/share/agent-builds/rhai/linux-post-spawn-pipe-setup-523-20261004`. Any future staging must freshly establish both paths absent first. Use the existing scoped runner, bounded launcher, resource limits, exact source/tool pins, process start-tick checks, unknown-fails-closed rules, and independent original readback.

The collector must first export the complete stage and independently verify its file hashes, directory set, and tar bytes. It must save the original export manifest and fresh custody receipt locally before retirement. Only after fresh inventory equals the exported inventory and the complete custody consumer passes may the exact hardcoded stage path be removed. The retirement command must re-inventory and compare against that same expected file/directory set immediately before removal, refuse symlinks or scope/runtime presence, remove only that stage, then read back both stage and scope absence. Any mismatch preserves the remote tree and fails closed. No broad cleanup or retry is authorized by this recipe.

Preparation ran no SSH, Cargo, native test, signal, remote staging, or deletion. This package is not native acceptance and does not establish Linux behavior. Native acceptance still needs one reviewed bounded run with both intended RED controls, restored GREEN, original export/readback, custody, and exact retirement readback. Existing stopped stdin/native110, Darwin, Windows, and custody histories remain unchanged.
