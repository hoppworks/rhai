# Question

Give an implementable bounded route to launch the frozen process overhead benchmark
on native macOS with verified setup/build/fixture interruption closure, without
unsafe numeric PID signaling. Resolve the current project-local launch custody gap.

# Why escalated

Independent source review of safeguards f7dab7934f7f7f42245ec23008fe8e2616606799
shows that the harness owns a Python measurement starter, whose subprocess.run
Cargo child has no signal forwarding/finally. Reaping that starter cannot prove
Cargo/descendant closure. Setup children now fail-retain, but are not proven
reaped. This is an uncovered benchmark-launch supervision decision, not another
attempt at Expert08's production Unix completion contract (already accepted on
Linux80/macOS81). No native overhead launch has occurred. No second Expert chain
for this launch custody cause is permitted.

# Context by reference

- Current authoritative state: /Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/coordinator-state.md
- Safeguards owned worktree: /Users/hoppworks/.codex/worktrees/macos-overhead-safeguards/rhai
- Frozen safeguards commit: f7dab7934f7f7f42245ec23008fe8e2616606799
- Three files: .scratch/all-tickets/macos-process-overhead.py,
  run-macos-process-overhead-scoped.py, run-macos-process-overhead.sh
- Frozen benchmark source00bed4a0dfeb103ff209ba4c76dac7ae797b7c56:
  tests/sys_process.rs, .scratch/managed-unix-scope-close/measure-process-overhead.py
- Prior accepted fixture-specific anchor/custodian protocol:
  .scratch/process-prototype/adapter/{README.md,run_scoped.py,custodian.py,controller.py}
- Prior production completion answer: .scratch/all-tickets/escalations/08-managed-unix-scope-completion.answer.md
- Approved ticket: .scratch/stdlib-wayfinder/issues/03-process-contract.md

# Constraints and decisions

Read-only source analysis and one answer artifact only. No native/Cargo workload,
VM control, install, configuration changes, Git mutation, or cleanup. Preserve
foreign and dirty worktrees. Repository prose English, no attribution branding.
Global runner unchanged; project-local custody adapter explicitly authorized.
Snapshots/PID+lstart are passive readback, never authority to signal a nonchild.
Existing anchor protocol is fixture-specific; justify any generalization.
Keep exact benchmark source/archive, 30 pairs per workload,120 calls, zero warmups,
no retries and unchanged timing/throughput semantics. Limits: outer600s,
scoped585s, driver580s, aggregateCargo540s, jobs2, descendants16, sampled RSS2GiB,
storage1572864KiB approximately1s. Setup/export/closure included in total bound.
Native launches consumed81 at dispatch; Linux82 subsequently failed at runner
import before runtime/measurement. Analysis consumes no native slot. Retained
runtime after interrupted unknown custody is honest failure, not acceptance.
Do not waive full goal scope or generic production process obligations.

# Tried so far

Source-only31f22/f7dab safeguards add sampled resource stops, exact direct starter
reap, conservative ledger and fail-retain. Root found nested Cargo ownership and
setup ledger issues; setup now records setup-in-progress and bounds final ps.
Still no whole interrupted tree closure. Root inspected io_stress: exact two
writer threads, no process descendants, finite8MiB per stream, stdinEOF and
write-error/failed-join unwind. Closing last pipe ends may stop escaped Managed
fixture, but no native proof exists. Direct Cargo Popen + frozen parsing could
remove the intermediate Python starter while preserving measurement semantics.
Anchor-owned Cargo group may cover normal compile/test descendants; justify
what the narrow finite benchmark can guarantee beyond that group.

# Deliverable

Write 09-macos-overhead-custody.answer.md beside this brief. Choose one practical
route meeting the same benchmark and cleanup acceptance. Specify exact source
changes, custody invariants, finite meaningful interruption controls (including
setup, build/test host and active managed capture), independent readback and
time allocations. Flag any actual impossible/uncovered requirement with evidence.
Do not substitute retention or narrowed success for required closure. Return at
most15 lines plus answer path. Hand the bounded implementation back to the
existing responsible macos_overhead_safeguards context after root review.

# Budget

One fresh read-only Expert analysis,15 minutes active-work planning checkpoint,
no build/native measurement slots, no resource-cap change. Only the answer file
may be written. Preserve this cause history and route rather than starting a
second escalation chain.
