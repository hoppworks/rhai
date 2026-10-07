# Workhorse post-install Rustup stop

## Verdict

The strongest supported explanation is that the **install command itself fails during Rustup's automatic self-update after successfully installing Rust 1.77.2**. The recipe runs a preinstalled Rustup while pointing `CARGO_HOME` at a new private directory containing no installed Rustup binary. Under `set -e`, a nonzero install-command status exits the script before the absolute compiler paths are reached. Adding those paths in launch 2 therefore would not address this failure.

This mechanism is supported by the retained recipe, upstream implementation and reported live error; it is **not a verified attribution of either historical exit**. Neither retained outer log contains the install status, stderr, installed-file inventory or next-phase marker. Do not claim that the direct `rustc` command failed, that a proxy selected another compiler, or that a Package B assertion ran.

The smallest justified correction is `--no-self-update` on the existing install command, plus durable setup stdout/stderr/status and phase evidence. Keep the direct private compiler/Cargo invocation. One fresh-admission bounded follow-up can test this hypothesis and run the unchanged acceptance case; no new installer, archive procurement or transport layer is indicated.

## Evidence and limits

| Evidence | Conclusion |
| --- | --- |
| Launch logs at 08:42:05Z and 08:43:38Z both end with the installed Rust 1.77.2 summary. | Installation reached its success-reporting phase; the complete command's exit status remains unknown. |
| Current pinned `inputs/run.sh`, SHA-256 `5c8730adecef29f8ec99f9dcec6d3fc907c090e017f1c1cd528164f0d874133f`, starts with `set -euo pipefail`; its unguarded install command precedes all direct binary checks/version commands. | An install-command failure exits before those checks. The second recipe still contains this failure opportunity. |
| It prepends `/root/.cargo/bin`, exports new private `CARGO_HOME`/`RUSTUP_HOME`, and creates directories without installing Rustup in private Cargo home. | The host installer and its configured Cargo installation root differ. PATH alone does not prove the resolved executable, so record it in the follow-up. |
| Persistent `evidence/` was empty; first version output would create `toolchain.txt`. | No durable successful version check is established. Failure can also occur at executable checks or pipeline startup; absence alone does not distinguish them. |
| The live error was reported as `rustup is not installed at <private CARGO_HOME>`, but not retained. | Corroborates the self-update hypothesis; it cannot substitute for original stderr/status. |

Rustup documents per-command suppression of automatic self-update with `--no-self-update` for `toolchain install`. [Rustup basic usage](https://rust-lang.github.io/rustup/basics.html).

The inspected upstream `update` implementation prints the toolchain summary, sets default selection when applicable, then invokes self-update. That call can propagate an error before returning success. This is current upstream code, not a verified identity match to Workhorse's installed Rustup. [Rustup command implementation](https://github.com/rust-lang/rustup/blob/main/src/cli/rustup_mode.rs#L1070-L1157).

Its self-update preparation checks for `CARGO_HOME/bin/rustup` and returns `NotSelfInstalled` when absent. This explains why a valid private toolchain can coexist with a failed overall installer command. [Rustup self-update implementation](https://github.com/rust-lang/rustup/blob/main/src/cli/self_update.rs#L1127-L1133).

Local historical corroboration exists in `process-overlap-review.md` under “Native allocation 1 collection diagnosis”: that reviewed Linux setup used `/root/.cargo/bin/rustup ... --no-self-update`, private homes and direct version commands, with retained setup status zero. It is a different accepted run, not Package B evidence; this review did not revalidate its originals. It supports reusing the existing setup technique rather than importing escalation 07's alternative.

Escalation 07 is materially distinct: Darwin component downloads timed out before installation completion. Here both Linux attempts report installation completion and the live symptom concerns Cargo-home installer placement. Preserve both histories. No evidence identifies download throughput, storage exhaustion or product code as this cause.

The scoped runner inherits stdout/stderr and returns child status; it does not save them itself. Thus complete preservation belongs in this recipe and the existing caller's capture. Its automatic runtime deletion explains why missing setup evidence cannot now be reconstructed. No live remote inventory or binary inspection was performed in this review.

## Concrete next action

Prepare one setup-only recipe amendment in the existing owner scope:

1. Keep all source/archive/patch/lock/test/runner pins unchanged. Repin only the intentionally amended recipe and its manifest; preserve both original launch logs and the original recipe hash. Do not describe a changed recipe as retaining the same hash.
2. Before install, record resolved Rustup path, selected private paths, Rustup version/help output and phase markers in persistent evidence. Check that this binary supports `--no-self-update`; no global configuration change is required. Keep HOME private as required by the launch contract—the retained script itself does not establish HOME isolation.
3. Change the command to `/root/.cargo/bin/rustup toolchain install 1.77.2 --profile minimal --no-self-update`, after verifying that exact existing executable is the intended installer. Run it in an explicit `if` branch with stdout and stderr redirected separately to persistent `install.stdout`/`install.stderr`; immediately record its real status and stop on nonzero. Do not ignore the status because a toolchain directory exists. Add a simple exit/phase receipt so failure before versions remains classifiable. Preserve caller stderr and terminal status too; no wrapper layer is needed.
4. Check the existing private `1.77.2-x86_64-unknown-linux-gnu/bin` executables, recording each check's result. Keep absolute Cargo and `RUSTC`; record actual `rustc -vV` and Cargo version, requiring Rust/Cargo 1.77.2 and the Linux host. Keep tool wrappers from redirecting compilation and direct any needed `RUSTDOC` to the same private toolchain. Stop on version/host mismatch.
5. Execute the unchanged reviewed wrong-expectation RED, restoration hash check and GREEN. Preserve the exact test's public Engine invocation, real child record/reaping checks, raw-output assertions and final independent read-back/cleanup. A compiler or setup error is not the intended RED. Keep all existing resource guards active.

Check the amended recipe's shell syntax, pin manifest, persistent evidence paths and failure branches before allocation; these checks require no install/build. Then recheck live Workhorse capacity, slot, input hashes and exact owned paths. Retain 600/585-second outer/runner limits, two Cargo jobs, existing process/RSS/storage limits and private homes/target/tmp. No additional toolchain-preparation invocation is proposed.

## Finite stop condition

Use at most **one** post-escalation native follow-up for this cause, bringing Package B cumulative launches from two to at most three; preserve two prior infrastructure recoveries and zero prior assertions/product corrections. No installation retries or fallback route inside that invocation. Stop on unsupported flag, install failure, executable/version mismatch, resource/timeout breach, wrong RED, GREEN failure, evidence loss or failed cleanup/read-back. Preserve the exact phase/status/stdout/stderr and report the remaining requirement; no second Expert chain.

If the retained records are required to prove the historical cause, they cannot do so. The exact missing evidence is the installer executable/version, argv, final exit status and stderr, followed by markers for executable checks and each version command. Read-only inventory of any separately retained original caller output could settle it if such output exists. Otherwise only the single authorized instrumented follow-up can establish whether disabling self-update resolves this setup path; success would validate the remedy without reconstructing the old exits.

This review wrote only this answer and performed zero installs, builds, tests, remote writes, commits or process changes. Package B acceptance remains open.
