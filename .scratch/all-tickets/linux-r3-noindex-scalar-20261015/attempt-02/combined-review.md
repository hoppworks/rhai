# Independent combined review - R3 no_index scalar Linux row

Freshly loaded lllm rules:
- agent-skills HEAD: `d6024420e9a829e97e1857ae3a853d832348c83f`
- central `AGENTS.md` SHA-256: `fa1c6e656d0f1d3e9c3c7596cf911203ae27094d38be5484d7a385ae11a3f65b`
- central common rules SHA-256: `989dcc707a9e561c5f3fab7a8a973bef3fd39a452a06476f928cf32885fe8c77`
- project `AGENTS.md` SHA-256: `37f95ff6a80be28bc21e9e523674f46f3ce6153a1923c708b86333bf21bba37c`
- `mattpocock-code-review/SKILL.md` SHA-256: `a9b6618b3c16759ddedf3e36b774cd0d76ee3fd122bbf3978c2166acad9df645`
- `build-efficiently/SKILL.md` SHA-256: `58f676b48691ea2ed476f67f13ef68aedcdb73cd4cabf13925db1927c9ccaf04`

## Standards

PASS for this named Linux partial row. Both attempts bind to fork-main revision `9b01104639c4032c892f142a4e049f66ea65fba2`, Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, default profile, and `testing-environ,sys,no_index,sync,unchecked`. They use the same Cargo.lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, Cargo.toml SHA-256 `cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e`, and Unix process source SHA-256 `2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6`. GREEN test source matches the unmodified source receipt; RED changes only the targeted final assertion in its private copy.

Attempt 01's Cargo result is a genuine expected RED: exit 101, outer selected test 0 passed / 1 failed, with `RED_CONTROL` at the deliberately inverted absent-`run_raw` assertion after the public scalar `run`, child-record readback, and ESRCH observation. Its wrapper status 1 is explained by the parser searching for `child-pid=` while the test diagnostic is `child_pid=`; the wrapper stopped before GREEN. Attempt 02 is a separate restored-source GREEN-only run: Cargo and runner status 0, 1/1 passed. RED is not repeated.

The scoped source, Cargo home, and target are isolated; both attempts record one Cargo job and removal of the runtime and owned scope. Attempt 02's two preflight snapshots show no Cargo/rustc process, about 95 GiB available RAM, and more than 642 GiB free disk. A foreign Tauron Cargo build appears in the post-run snapshot; it was left untouched. The timing suggests possible overlap near the tail, which is documented as a capacity caveat rather than grounds to misclassify the completed exact GREEN result.

## Spec / acceptance

PASS only for `scalar_run_with_cwd_works_without_collections` under this Linux feature/profile/toolchain slice. The test uses the public Rhai Engine API to run a real `/bin/sh` child with an explicit working directory; independently reads its PID record and confirms ESRCH; checks exact cwd stdout, complete stdout/stderr, successful status and exit code 0; and asserts that `run_raw` is not registered. Both the RED trace and GREEN trace show the child marker and ESRCH. GREEN confirms all assertions passed.

The R3 plan crosswalk now preserves its existing five-column schema and labels this evidence as partial. It explicitly leaves no-argument behavior and array-taking overload absence open; the coordinator entry likewise calls out this exact named test and remaining R3 scope. This does not accept full R3, other profiles/platforms/MSRVs, or broader process/Ticket03 requirements.
