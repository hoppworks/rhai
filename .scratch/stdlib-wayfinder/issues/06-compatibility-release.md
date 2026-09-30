# Choose supported platforms, features and release gates

Type: grilling
Label: wayfinder:grilling
Status: open
Parent: [Plan a reliable Rhai host standard library](../map.md)
Blocked by: none

## Question

Which platform, Rust-version and Rhai-feature combinations must sys and net support,
and what evidence is required before a release is declared ready?

## Context

Core MSRV is 1.66.0; sys documents 1.77.2. Existing sys decisions exclude no_std,
no_object and wasm. The network reference fails metadata, sync, only_i32 and unchecked
builds. GitHub Actions are disabled on the fork and real Windows has not been verified.

## Resolution requirements

Define required versus intentionally unsupported combinations, preserve core MSRV,
and decide gated-package MSRV/dependency policy. Choose a bounded feature matrix
based on semantic interactions, including sync/no_index/metadata/integer modes.
Agree how Linux/macOS/real-Windows evidence will be obtained without implying Wine
or a cross-compile proves native execution. State release blockers explicitly.

Clarify API review and documentation requirements for sys file-handle compatibility
and TCP. Do not introduce a CI service or enable fork settings without authorization.
