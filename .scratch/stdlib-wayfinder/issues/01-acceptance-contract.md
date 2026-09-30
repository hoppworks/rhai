# Define observable acceptance and test structure

Type: grilling
Label: wayfinder:grilling
Status: open
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
