# Accepted native Linux integer process examples

Scope: two previously unaccepted X23 / Ticket06 example slices, native Linux x86_64
on LLLM, Rust/Cargo1.77.2. Existing default Linux/Darwin and other Unix evidence
remain separately bound; this is not full X23, Windows or release acceptance.

| Features | Build exit / seconds | Wrong exit8 control | Restored exit7 |
|---|---|---|---|
| sys,no_float | 0 /22.124 |101, intended exit assertion /0.138s|0 /0.239s|
| sys,sync,only_i32,no_float |0 /9.298|101, intended exit assertion /0.140s|0 /0.140s|

Each row runs the actual example compiler artifact through the public Engine and
SysPackage. Before the control assertion, fresh host readback checks run/spawn
records, pending wait, all eight cached clone fields and immediate spawned-child
ESRCH. RED and GREEN use the same binary per profile; only the declared expected
exit changes8→7. Raw output/status, compiler artifact JSON, commands and phases
are preserved here. example_phase is the accepted Darwin oracle with only its
result-export filename changed; independent readiness review preceded execution.

Source binding: main0a0636f42533ec29170881ac9b14d50de758d6f9 plus selection.json's
owned source overlay; compatible lock00afc549… adds only the root Windows optional
dependency reference, not versions/checksums. Current Unix backend55dc5ad5… is
byte-identical to accepted Unix snapshots. Example b8674785… changes only private
module naming/platform cfg relative to main; its Linux body is unchanged.
native-environment.json, portable-1.77.2.json and source/archive/helper hashes
bind the actual platform/compiler/dependencies and explicit private source cwd.

Helper completed0 in44.562s. Samples observed max2,035,945,673bytes private
storage and965,283,840bytes owned RSS, within8GiB/32members/two-job bounds and
1200s whole-run timeout. Related profiles reused the same private dependency
cache. Native commands and observations were exported before cleanup.

The outer launcher exited1 AFTER spawning the finite runner: an incorrect Python
Path expression failed while writing its PID receipt. The run continued under
its original supervisor; it was never restarted. Its outer exit is unobserved
and is deliberately not labelled0. launcher-error.json preserves this bookkeeping
failure; original helper/product exits remain independently recorded. Exact live
PID/start readback recovered the running identities, followed by independent
absence of runner/supervisor/helper and the supervisor group. Runtime absence and
the empty outer scope's UID/device/inode were verified before exact rmdir.
cleanup.json records that disposition. No build/cache/toolchain remains reusable.

The same independent combined review accepts these two native example slices;
[combined-review.md](combined-review.md) is its verbatim bounded export, with
[acceptance.json](acceptance.json) binding the final disposition. Original
phases.json retains its pre-review accepted:false marker without rewriting history.
The prepared X23/R5 label does not establish R5 no_index/scalar acceptance; only
the named X23 and applicable Ticket06 example slices are accepted. No native Windows execution, VM/foreign resource
change, public upstream write, package release or deployment occurred.
