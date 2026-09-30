# Specify TCP byte and connection lifecycle contracts

Type: grilling
Label: wayfinder:grilling
Status: resolved (specification only)
Parent: [Plan a reliable Rhai host standard library](../map.md)
Blocked by: 04, 06

## Question

What is the smallest useful Rhai TCP API consistent with the selected host policy,
byte semantics, errors, handle lifetimes and supported Rhai features?

## Context

The assessed rhai-net source is a reference, not an accepted dependency or API.
Diagnostics show zero padding on short/EOF Blob reads, integer port wrapping and
feature incompatibilities. A real script-to-independent-peer write passed.

## Resolution requirements

Specify read length, EOF, partial reads/writes, binary/text conversion, valid ports,
half-close/shutdown, repeated close and cloned/shared-handle behavior. Decide what
compatibility with rhai-net is useful without preserving demonstrated defects.
Resolve script-visible errors and absent Array/Blob support against ticket 06's
compatibility decisions. Link each promised behavior to a real-peer test scenario.

Reference: ../../../docs/net-package-assessment.md and
../../../docs/net-assessment/characterization.rs.

## Owner resolution — 2026-09-30

The owner accepted the recommended concrete specification in
[the approved proposal](../../all-tickets/tcp-proposal.md).
Implementation, documented behavior and strict native/feature/MSRV proof remain
open campaign requirements. No remote publication is authorized.
