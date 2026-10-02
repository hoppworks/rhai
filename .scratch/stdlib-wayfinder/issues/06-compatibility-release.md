# Choose supported platforms, features and release gates

Type: grilling
Label: wayfinder:grilling
Status: resolved (specification only)
Parent: [Plan a reliable Rhai host standard library](../map.md)
Blocked by: none

## Question

Which platform, Rust-version and Rhai-feature combinations must sys and net support,
and what evidence is required before a release is declared ready?

## Context

Core MSRV is 1.66.0; sys documents 1.77.2. Existing sys decisions exclude no_std,
no_object and wasm. The network reference fails metadata, sync, only_i32 and unchecked
builds. GitHub Actions are disabled on the fork. Native Windows baseline evidence
now covers 45 selected sys tests on Rust 1.93.0/MSVC, with an assertion control for
write/truncate/append (../windows-vm/README.md); it does not certify the release matrix.

## Resolution requirements

Define required versus intentionally unsupported combinations, preserve core MSRV,
and decide gated-package MSRV/dependency policy. Choose a bounded feature matrix
based on semantic interactions, including sync/no_index/metadata/integer modes.
Agree how Linux/macOS/real-Windows evidence will be obtained without implying Wine
or a cross-compile proves native execution. State release blockers explicitly.

Clarify API review and documentation requirements for sys file-handle compatibility
and TCP. Do not introduce a CI service or enable fork settings without authorization.

## Process API and release obligations from ticket 03

The owner requires managed process groups/jobs in the first version, alongside
explicit direct-child supervision. Review exact host-config spelling and the proposed
`SysError.process` report without implying existing Rust enum variants can change
without compatibility assessment. Native scope setup, cancellation, retained pipes,
normal completion and cleanup failures must pass on every supported OS. An unavailable
managed mechanism fails explicitly; silently downgrading supervision is prohibited.

## Verification resource lifecycle

Before another Windows build, adapt scoped execution to the guest: identify owned
process trees, bound their lifetime, isolate Cargo outputs/caches and fixtures, export
proof, and clean on success, failure and interruption. The POSIX run_scoped.py runner
cannot clean guest descendants merely by stopping an SSH process. Preserve the
accepted baseline and diagnostics until replacement evidence is accepted. Validate
the adapter's interruption cleanup before relying on it for native release gates.

## Owner resolution — 2026-09-30

The owner accepted the recommended concrete specification in
[the approved proposal](../../all-tickets/release-proposal.md).
Implementation, documented behavior and strict native/feature/MSRV proof remain
open campaign requirements. No remote publication is authorized.

## Current-source optional compiler prerequisite — 2026-10-02

Native Darwin arm64 Rust/Cargo1.77.2 successfully ran
`cargo check --locked --lib --features testing-environ,sys,net` at frozen source
`9f84aa6d8163257b4e3f3c2fe4a1c7d7b7c3cce6`, with compatible lock SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
Original logs, direct versions, command statuses and seven manifest hashes are in
`../../all-tickets/current-optional-msrv-evidence/`; `root-readback.json` confirms
outer0, every command0, exact runtime absence and empty-only scope retirement.
No relevant source, build script or Cargo-manifest change exists between that
revision and integration1928c068, so this compile evidence applies there too.
The private toolchain and caches were disposable, with no shared-home install.

This closes only the current sys/net library compiler prerequisite on Darwin.
Script behavior, tests/examples, other feature combinations and native platforms
remain open. Native process invocation count84 is unchanged; no fixture/control
or overhead measurement was run. The earlier release specification stays intact.
