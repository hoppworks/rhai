## Workflow choices

- Verification: strict
- Push: automatic
- Merge: automatic

## E2E verification

Acceptance contract approved by the owner on 2026-09-30.

- **Tool:** Cargo integration tests through real Rhai scripts, Engine, the registered
  host package and the real OS. Acceptance proof does not mock files, sockets or
  process execution.
- **Start command:** No shared service is required. From the session worktree:
  `cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_env --test sys_fs --no-run`
  The test command launches the test executables and their scoped fixtures.
- **Test command:**
  `cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_env --test sys_fs`
  A real test name may filter a targeted regression. Add process and net targets
  when implemented. The release OS/feature/MSRV matrix remains a separate decision.
- **Safe data reset:** Fixtures own unique temporary roots, sockets and child
  processes. Clean up only those resources, using guards and explicit child
  termination/reaping on exceptional paths. Investigate interrupted-run leftovers
  by exact recorded path/PID before removal. Never reset shared services, delete
  another session's fixtures or mutate the parent test environment/current directory.

### Required evidence and test structure

- Exercise the public script API and independently observe the effect: fresh host
  file reads, an independent TCP peer, or child-written records plus exit/reaping.
  Read-only behavior is compared with independent fixture truth; it need not create
  a persistent write. Denied operations must leave protected state unchanged.
- Demonstrate that the assertion fails for a wrong expectation or known-broken state,
  restore the correct expectation, and show it passes before claiming acceptance.
- New behavior starts with a meaningful failing contract test. Preserve bug
  reproductions as regressions. Keep the existing sys test/support layout; supplement
  with focused unit tests only where useful. Test counts and coverage percentages
  are not substitutes for contract, policy and lifecycle evidence.
- Isolate environment fixtures in child processes; use OS-selected TCP ports,
  explicit readiness, bounded waits and cleanup/join/reap. Fixed sleeps do not prove
  readiness. Timeouts fail with diagnostics rather than silently skipping behavior.
- Record commands, features, OS/Rust versions, observed results, independent read-back,
  the failing control, cleanup and unverified paths. Compilation or Wine alone does
  not prove native platform behavior.
- Existing sys regressions and global environment mutation remain open work. This
  configuration defines acceptance; it does not certify the inherited implementation.

Decision detail: [.scratch/stdlib-wayfinder/issues/01-acceptance-contract.md](.scratch/stdlib-wayfinder/issues/01-acceptance-contract.md).

## Current remote authorization

The owner initially selected fully private work on 2026-09-30, then explicitly
authorized pushing this Session's integrated `task/all-tickets` branch to the
existing `https://github.com/hoppworks/rhai.git` fork. That later instruction
authorizes these pushes. Continue local and authorized workhorse VM work under
the recorded scope. Preserve the existing remote history and visibility.

The owner subsequently authorized merging this Session's verified work into
`main` on that same fork. This does not authorize any write or pull request to
the public upstream repository. Preserve foreign local main checkouts; use a
verified fast-forward ref update when no merge commit is required, and read back
the fork's exact main head after pushing.

## Resource lifecycle

For future POSIX builds and verification, use
`/Users/hoppworks/projects/agent-skills/tools/run_scoped.py -- <command>`.
Set `CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"` and
`CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"` inside that command. The runner sets
temporary-directory variables. Build from an owned source copy inside the runtime,
including the changes under test, so Cargo.lock and build.rs-generated source files
also stay scoped. Keep related compilation, tests and assertion controls in one
invocation, and export accepted evidence and needed diagnostics before it exits.

The POSIX runner does not supervise Windows guest descendants through SSH.
Before another native Windows build, supply equivalent guest process-tree ownership,
bounded execution, output/cache isolation and cleanup on failure or interruption;
the release ticket tracks this requirement. Reuse the accepted native baseline
while its relevant source, assertions and environment remain unchanged.

## Accepted package decisions

On 2026-09-30 the owner accepted the concrete TCP authority/lifecycle and release
proposals in `.scratch/all-tickets/tcp-proposal.md` and `release-proposal.md`.
Implement connect and separately authorized listen/accept, with the specified
bounds and shared lifecycle. Reject negative file reads and preserve resource
bounds under unchecked. Core MSRV remains 1.66.0; optional sys/net target 1.77.2
and require strict native Linux/macOS/Windows and the specified feature gates.

The owner permits a project-local copy of the scoped runner solely to establish
explicit POSIX supervision/runtime custody and whole-runner interruption proof.
Do not modify the global runner. Independent source review precedes execution;
record finite controls and limits before launching. Native Windows custody remains
an independent prerequisite, not waived by these decisions.

## Git attribution

The owner requires author and committer names to be exactly `hoppworks` (lowercase).
Keep the configured email. Use command-local `git -c user.name=hoppworks` when
committing or merging; do not modify global or shared configuration. No agent
co-author trailers or signatures.
