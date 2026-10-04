# Linux readable-output overflow and expired deadline proof

Status: accepted for Linux DirectChild and Managed same-step precedence only.

Ticket03 requires OutputLimit when readable output overflow and deadline expiration
are observed in the same supervision step. This closes only that Linux requirement
for DirectChild and Managed supervision. It does not establish all first-cause,
stdin, fault, macOS/Windows, API/documentation or release requirements.

## Source and real behavior

Production baseline8c0ee4634355aee4e841b455461a7dd5aac2aa18;
reviewed source9dc92b16dad173eaffbde521310d1e2480e7be9c. Selected unix.rs SHA
6b088870e6f4ed758c88e6fdc7e50475cae7cda90ba10dae58e45718a2ba3a98;
changes are206 test-only additions relative to production baseline, no production
behavior change. Source archive2b46a48f0978de3f7c1a7958678d3474232a0b2246ac8ff8f85e9e931345c039;
compatible lock2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425.

On native workhorse Linuxx86_64 with private Rust/Cargo1.77.2, Cargo ran each fully
qualified test under --locked --lib --features testing-environ,sys -- --exact
--nocapture --test-threads=1. Actual Rhai Engine/SysPackage script invokes the public
run API; a real child writes output, acknowledges it and waits. The scheduling
adapter makes the run deadline expire after the child-written readiness record;
ordinary OS poll/read and supervision handle both observations in that step.

| Case | Exact selected tests | Exit | Independently bound fixture receipt |
|---|---|---|---|
| timeout-first-direct |1|101|write acknowledged, expired deadline, stdout readable, overflow=false, child reaped/owner closed|
| timeout-first-managed |1|101|same actual observations, owned child group, child reaped/owner closed|
| restored-direct |1|0|same observations, overflow=true, typed OutputLimit, retained stdout x, timed_out=false, incomplete capture|
| restored-managed |1|0|same behavior, owned child group, child reaped/owner closed|

Both controls fail the intended overflow-precedence assertion after cleanup.
The actual timeout-first mutant hash53ce5a454661ffd08e6f3d0a9bbac15c8ccd8f1ea397c042b777a066be756b23
was checked before both controls. The source and lock were restored byte-for-byte
before the two pristine passes and at export. Four raw command streams/statuses,
control and fixture ledgers are in process-overlap-evidence/originals/stage-originals.

## Custody, resource bounds and collection recovery

One native allocation, terminal0. Initial180second slot wait allocated no build;
subsequent fresh zero-heavy observation verified14 input pins, available RAM/disk
and load before allocation. Limits600/585/540seconds, helper510work+30export,
2Cargo jobs,16descendants,1572864KiB storage preempt and2097152KiB RSS/storage hard
caps remained. Adaptive runner570seconds. Export began31.063seconds after helper
start;42 periodic samples observed maxima918416KiB RSS,685316KiB storage and6
descendants. These are sampled maxima, not continuous peaks.

Sole original archive e5f0bf6cc804db36347e9a0603eda64fd7432fd3b25213a85170c57de0bf2990,
6789120bytes,62files/5directories, independently inventory/hash checked.
Original collector stopped before custody on one empty observed rustup-install
cmdline. Its exact cause is unknown; observed setup argv is unavailable. All six
later command argv rows were populated and exact. The combined review approved
one collection-only recovery bound to this archive,10 original proof hashes,
actual reviewed Popen producer and exact installer PID1993181/start11387239/
parent1993179/group1993178, checked spawn/status/runtime and helper ancestry.
No populated mismatch or other empty command is admitted. Actual-corpus and
finite tamper probes cover this consumer correction, without modifying originals,
rebuilding or pretending setup argv was independently observed.

Reviewed recovery adapter edba89657810f2e8a5bf31debcf6f5a829969cf88b4a46134007b8d0bb1bff71
resumed the same archive. Live custody verified99 identities and four groups before
exact stage retirement. A separate fresh SSH read-back at2026-10-04T14:13:26Z
verified99 exact PID/start identities absent or reused, four owned groups empty,
and six specified path entries absent (some physical/logical aliases). The private
runtime, empty scope and exact owned stage are gone. No foreign process/resource
was stopped, removed or changed.

Source-readiness history retains two failed corrections, Expert22 and its sole
passed9dc followup. Recipe history retains one failed correction and passed dae
second correction. Collection infrastructure failure1 has one successful bounded
recovery. Expected control REDs are not failed corrections. Review and applicability
are recorded in process-overlap-review.md; original custody/retirement/fresh receipts
and admission sources are under process-overlap-evidence/originals.
