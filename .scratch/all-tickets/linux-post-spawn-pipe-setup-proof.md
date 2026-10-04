# Linux post-spawn pipe-setup proof

Status: ACCEPTED for the named Linux criterion. Native behavior, original
integrity, custody and exact retirement passed the final combined independent
read-back. This is partial process/release acceptance.

## Requirement and entry point

A pipe configuration failure after a real process starts must preserve its typed
primary I/O cause, return an honest incomplete capture report, and reap the child
before the process owner retires. The named Cargo test executes a real Rhai
`run` script through Engine and SysPackage, with a real `/bin/sh` child and
scoped FIFO/readiness files. A test-only post-spawn fault hook controls timing;
process creation, public error propagation and OS reaping remain real.

## Immutable inputs and execution

Production and nested test source revision523608648dcae99bc0f6b46eaf2bb91fa4ecc752
matches current root ba3b14988d9db9d1cfab191b6cbe404ec3c8248b for this criterion.
Archive SHA256998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b;
unix.rs SHA2561b60751c6d9ed695f79edc4f8a7972338274684ef53583bd1ea1009c1aca822a.
Private native Linux x86_64 Rust/Cargo1.77.2, accepted lock2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425,
features testing-environ,sys, default float/index. Native2 admitted at
2026-10-04T10:41:53Z with fresh zero-heavy inventory; no foreign resources changed.
Outer600, adaptive runner570 within585, helper540 seconds; two Cargo jobs,
16 descendants,1572864KiB preemptive storage and2097152KiB hard RSS/storage.

| Case | Result | Independent observation |
| --- | --- | --- |
| Wrong configure-pipe message expectation |101| Named primary-cause assertion after inner and outer ESRCH receipts |
| Wrong incomplete stdout expectation |101| Named nonfabricated-completion assertion after inner and outer ESRCH receipts |
| Restored original source |0| Exact named test, nested and outer one-pass results, owner retired and both ESRCH receipts |

Original source, manifests and accepted lock were restored and independently
read back.47 periodic samples reported maxima898500KiB RSS,687332KiB storage
and seven descendants; these are sampled maxima, not continuous peaks.

## Original evidence and history

All53 original files/five directories are preserved in
linux-post-spawn-pipe-setup-native2-originals; their hashes match the independent
remote inventory. Sole original tar SHA2563083b009dcfdbcb83f9d9acec60db250328de5d37fe73e9b5247f01624a2cca4.
The combined report is linux-post-spawn-pipe-setup-review.md.

Native1 failed before assertions because version queries selected source cwd
before extraction. Its36 originals/five directories and sole tar are preserved;
21 PID/start identities, two groups and exact stage/runtime/scope were verified
closed. The source-only explicit runtime-cwd repair and real startup probe passed
independent review. An initial native2 dispatch transport incorrectly nested SSH
and failed before allocation; corrected transport preserves unchanged remote
preflight code and all limits. Neither setup outcome is a product RED.

Native2 tests passed, but initial collector CUSTODY rejected the legitimate
version runtime cwd. A narrow correction now accepts runtime cwd only for the
three exact setup/version commands and retains source cwd for all three Cargo
tests. Real-emitter whole-consumer positive and wrong-version/test-cwd negatives
passed independent affected review. The sole existing export was resumed without
another build/archive or modifying original logs. Custody validates104 exact
PID/start identities,94 sampler instances, three Cargo cases and both post-reap
controls. Repeated full inventory preceded exact stage retirement. Root separately
queried the live OS after retirement: all104 identities absent/reused, owned
groups1022120/1022193 empty, logical/physical stage, scope and runtime absent.
Receipts fresh-custody-readback.json, retirement-readback.json and
root-fresh-closure.json are alongside the unchanged native2 originals.

The source-only writer commit89cc458d had incorrect human author spelling and
was excluded from integration. Only its three reviewed file contents are selected;
the coordinator integration uses the required lowercase human Git identity.

## Applicability

Only this named Linux post-spawn pipe-setup criterion is covered. Stdin, other fault/lifecycle paths, other platforms/feature rows,
performance, API metadata/docs and final release acceptance remain open. Earlier
stopped correction/escalation chains and cumulative history remain unchanged.
