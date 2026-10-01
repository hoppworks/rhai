# Exact Rust toolchain setup after bounded failures

## Question
How can the existing frozen Unix process proof safely obtain exact Rust/Cargo1.77.2 on aarch64-apple-darwin within the current scoped runtime policy, without repeating an uninformative full rustup download or substituting another Rust version?

## Why escalated
Two bounded setup executions failed before any Cargo/test assertion: invocation41 install watchdog180s and one invocation42 recovery450s. Same partial169-byte rustup log says syncing1.77.2 then downloading3components, no specific network error. The previous scoped runtimes were cleaned. Stop this route pending concrete diagnosis/alternative; do not infer whether transfer, extraction or installer internals caused the delay solely from du growth.

## Context by reference
- Root state: /Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/coordinator-state.md
- Owner state: /Users/hoppworks/projects/rhai-process-unix-run/.scratch/process-unix-run/coordinator-state.md
- Frozen harness: /Users/hoppworks/projects/rhai-process-unix-run/.scratch/process-unix-run/quarantine-reservation.py (28fc142261b6dd50ea6cf98f7f23236f53ec552f362037fcbe9c8a1a9b84a2b8)
- Raw attempts: owner evidence/quarantine-reservation.qyGAZk and quarantine-reservation.ecKi0j
- Source frozena41c1c9d; this setup cause is distinct from production cleanup-owner cause06. Do not reopen its design or start another cause06 escalation.

## Constraints and decisions
Read-only analysis only, except writing this answer. No download payload, install, build, native execution, home/config change, credentials, service/admin, process termination or remote writes. Small bounded primary-source metadata lookup is permitted if needed; no third installation measurement. Keep exact1.77.2, <=600s per scoped invocation, jobs2, private source/lock/CARGO_HOME/RUSTUP_HOME/target/tmp, inherited process group, 2GiB policy/conservative sampled1572864KiB stop. No global cache mutation. Preserve accepted proof and owned resources only. Source-only work continues independently. An exact installed toolchain inventory found stable1.93.0/nightly/1.66.0/1.93.0/1.96.0/1.98.1, no1.77.2. Root independently verified all10attempt-owned PIDs ESRCH and both exact runtimes absent; original/private5pathmanifests match. No tests/version checks/final manifests are accepted.

## Tried so far
Original180s and recovery450s watchdog inside unchanged600s outer runner. Actual cumulative setup windows630s; sampled runtime maxima72960KiB and224236KiB respectively. Samples are not peaks and do not identify individual components. No completed toolchain was retained; do not reconstruct nonexistent binary evidence. No third download.

## Deliverable
Write 07-rust-toolchain-setup.answer.md alongside this brief and reply in <=15lines plus its path. Distinguish measured facts from inference, give one minimal concrete next source/harness action and finite resume/stop contract. Consider a verified official artifact preparation/reuse route under scoped ownership if appropriate; acceptance still requires exactversion plus execution of the frozen tests, not metadata alone. Identify any actual external dependency without adding artificial user approval gates. Do not implement or execute the proposal.

## Budget
One fresh Expert for this setup cause, read-only planning checkpoint15minutes, zero installation/build/test launches. Existing cumulative42 and prior cause/history remain. No repeated advisory hierarchy or broader source audit.
