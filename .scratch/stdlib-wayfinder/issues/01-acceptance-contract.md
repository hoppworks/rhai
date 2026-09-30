# Define observable acceptance and test structure

Type: grilling
Label: wayfinder:grilling
Status: resolved
Assignee: current Codex session
Parent: [Plan a reliable Rhai host standard library](../map.md)
Blocked by: none

## Question

What evidence must each library behavior provide before we accept it, and how should
we organize that evidence to remain reliable and maintainable?

## Context

Verification is already strict; the missing choice is its concrete library-specific
method, not whether to relax it. AGENTS.md has no tool/start/test/safe-reset section.
Existing sys tests use the real Engine and independent filesystem read-back; env
fixtures still mutate process-global state. Reference TCP diagnostics used bound
listeners, OS-selected ports and an independent Rust peer.

## Proposed answer to discuss

Use Cargo integration tests through Engine plus registered Package plus the real OS.
Keep public contract, denied-authority/no-side-effect, lifecycle and regression cases
identifiable within the existing test layout. Use isolated child processes for env and
process fixtures, readiness signals, bounded waits, and per-test temporary resources.
Prove assertions can fail against a deliberately wrong expectation or a known defect.
Use independent file reads, peer observations or child-written records as appropriate;
do not fabricate storage requirements for pure/read-only behavior.

## Resolution requirements

Record tool, concrete start/test commands and safe reset in project config, the
read-back/false-green evidence required per behavior, and fixture cleanup expectations.
Choose checks for meaningful invariants, not a test count or a coverage percentage.
Do not install a test framework merely to resolve this ticket.

## Acceptance contract

Prepared and accepted by the owner on 2026-09-30. This contract defines required
evidence; it does not claim that the inherited tests satisfy it.

### Acceptance evidence

| Behavior | Public entry point | Independent observation | Negative control |
|---|---|---|---|
| File mutation | Rhai script through Engine and configured SysPackage | Host reads bytes/state afresh | Wrong expected bytes or known regression fails |
| Denied access | Same registered script API with restricted config | Sentinel content unchanged; forbidden target absent | Known denied-side-effect regression, or wrong sentinel expectation fails |
| Environment read | Script inside isolated child with Command-provided environment | Compare exact script value with the parent's fixture value | Wrong expected value fails |
| Process execution | Script run/spawn API driving real fixture executable | Child records argv/env/cwd/data; observe exit and reap | Wrong expected record or lifecycle result fails |
| TCP transfer | Script net API with real local sockets | Independent Rust peer observes exact bytes, EOF or shutdown | Wrong payload/length or existing short-read defect fails |

Read-only behavior is checked against independent fixture truth. It need not invent a
persistent write. Assertions must describe script-visible contracts rather than
implementation details. Compile-only checks prove compatibility, not OS behavior.

### Test layout and maintenance

Keep the existing sys_policy, sys_env, sys_fs and shared sys_support structure. Add
sys_process for process contracts and appropriate net test targets when implemented.
A test may cover several related requirement rows; test-function counts are not a
quality gate. Separate unrelated failures and name regressions after their behavior.

For each new behavior: demonstrate a meaningful failing contract test, implement the
smallest change that passes it, then refactor with the relevant tests green. For a
fix, preserve the reproducer as a regression. Unit tests may supplement integration
tests for difficult state transitions but cannot replace the real-entry-point proof.

Use isolated child environment fixtures, per-test temporary roots, bound port-0
listeners, explicit readiness, bounded waits and cleanup/join/reap. Fixed sleeps are
not readiness proof. A timeout must fail with diagnostic information rather than
turn a hang into a passing skip. Avoid shared environment/current-directory mutation.

Targeted property/fuzz/mutation checks are added only when a concrete invariant or
risk justifies them. Neither blanket snapshots nor a coverage percentage replaces
contract, policy or lifecycle cases. No new dependency is needed for this decision.

### Project E2E configuration

The following four items are recorded in the project AGENTS.md:

- **Tool:** Cargo integration tests exercising Engine plus the registered host package
  plus the real OS; no mocked files, sockets or process execution in acceptance proof.
- **Start command:** No shared service to start. From the session worktree, build the
  existing acceptance targets with:
  `cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_env --test sys_fs --no-run`
  Cargo's test command starts each test executable and its scoped fixtures.
- **Test command:**
  `cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_env --test sys_fs`
  Select a regression by its real test name when appropriate. Add concrete process
  and TCP targets when they exist; do not configure fictitious targets in advance.
  The required feature/OS/MSRV release matrix is resolved in ticket 06.
- **Safe data reset:** Tests own and clean up only their unique temporary roots,
  bound sockets and child processes. Guards perform normal cleanup; fixtures use
  explicit termination/reaping on exceptional paths. Investigate interrupted-run
  leftovers by exact recorded path/PID before cleanup. Never reset shared services,
  delete other sessions' fixtures or mutate the parent test environment.

These commands select real existing targets but are not a green acceptance claim:
reviewed sys regressions and global env mutation remain to be repaired test-first.
No runtime acceptance proof was performed while resolving this planning ticket.

### Completion evidence for each later implementation slice

Record tested behavior, exact commands/features/OS/Rust version, observed results,
independent read-back, one demonstrated failing assertion or known-broken control,
cleanup outcome and unverified paths. Native platform claims require native execution.
Documentation-only planning checks require read-back and link/dependency validation;
they do not establish runtime acceptance.

## Comments

The owner is being asked to accept the concrete proposal as the standard-library
acceptance contract. Leave this ticket claimed until that answer arrives; do not
resolve it, change project E2E configuration, or begin implementation by inference.

## Answer

The owner accepted the concrete contract above with “ok” on 2026-09-30 in response
to the explicit question whether to make it binding. The contract is now recorded
in [AGENTS.md](../../../AGENTS.md), including tool/start/test/safe-reset and the
required independent observation, failing control and fixture isolation.

This resolves the acceptance-method decision only. Known sys defects, fixture
repairs, process/TCP implementation and the release platform matrix remain open.

### Resolution comment

Owner acceptance recorded; proposal adopted without a new dependency or production
change. The earlier Comments entry documents the historical pending state.
