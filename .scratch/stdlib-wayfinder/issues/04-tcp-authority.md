# Define host authority and limits for TCP

Type: grilling
Label: wayfinder:grilling
Status: resolved (specification only)
Assignee: current planning session
Parent: [Plan a reliable Rhai host standard library](../map.md)
Blocked by: none

## Question

Which TCP operations and endpoints can the host grant, and which blocking/resource
limits are mandatory for the initial package?

## Context

TCP is separate and optional. The owner chose owned/reviewed scripts with explicit,
deny-by-default authority. Existing rhai-net has no suitable authority model for this
contract. Reuse assessment: ../../../docs/net-package-assessment.md.

## Resolution requirements

Decide connect versus listen/accept grants, bind addresses/ports, endpoint matching,
hostname resolution if offered, and read/write/connect/accept timeout behavior.
Decide buffer/connection limits and name what these controls actually guarantee.
Prefer the narrowest useful policy; avoid a generic permissions framework.
Do not promise HTTP, UDP, TLS or arbitrary-untrusted-script isolation.

## Owner resolution — 2026-09-30

The owner accepted the recommended concrete specification in
[the approved proposal](../../all-tickets/tcp-proposal.md).
Implementation, documented behavior and strict native/feature/MSRV proof remain
open campaign requirements. No remote publication is authorized.
