# Native Linux sys contract proof

## Task
Verify the integrated filesystem/isolated environment changes through the accepted
real-OS sys integration command on authorized workhorse Linux. This closes the
macOS unsupported invalid-UTF8 fixture coverage gap if its Linux filesystem supports
it; it does not settle the release matrix or certify process/TCP/file handles.

## References
- /Users/hoppworks/projects/rhai-all-tickets: current integrated HEAD and AGENTS.md.
- .scratch/all-tickets/verify-combined-sys.sh: source-copy/output/status conventions.
- .scratch/filesystem-contract/proof.md and .scratch/environment-fixtures/proof.md.
- /Users/hoppworks/projects/agent-skills/tools/run_scoped.py.

## Constraints
Fresh owned worktree task/linux-sys-proof based on current task/all-tickets.
No edits to production tests or source. Only private local/authorized workhorse
resources, no Git remote writes, installs, credentials or global cache changes.
Inspect available native Rust/tooling read-only first; if missing report limitation.
Use a source copy containing the exact accepted revision, scoped source/Cargo home/
target/temp and bounded native runner on workhorse. The existing POSIX scoped runner
must supervise work there, not only the SSH connection. Copy the configured runner
and its necessary helper modules to exact owned staging if absent; do not install it
or edit agent homes. Preserve remote scope/process ownership on disconnect and export
proof before cleanup. Avoid host shared service/global env mutations or cleanup.

## Acceptance
Run cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_env
--test sys_fs -- --nocapture. Inspect actual assertions and output; explicitly report
which OS-specific cases are excluded. Verify invalid-UTF8 fixture creation followed
by public Rhai read_dir NotUtf8 if supported. In the same reused build demonstrate
one deliberately wrong relevant expected payload fails, restore source bytes and
correct assertion passes. Retain exact OS/rust/version/command/source identity,
statuses and resource cleanup read-back. Do not copy full builds back locally.

## Attempt limit
Two same-cause failures or contradictory evidence: stop and report escalation brief
need to Coordinator rather than retry indefinitely. No new Expert chain yourself.

## Deliverable
Atomic proof/script commit in .scratch/linux-sys-proof, reference exact source revision
and applicability, report up to 15 lines with HEAD/evidence path/verified/unverified/
exact retained resources. Do not integrate or push. No package release claim.
