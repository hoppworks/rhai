# Close process lifecycle and resource-limit ambiguities

Type: grilling
Label: wayfinder:grilling
Status: open
Parent: [Plan a reliable Rhai host standard library](../map.md)
Blocked by: none

## Question

What observable outcomes must run/spawn guarantee when waits, stdin, output limits,
timeouts, shared handles and cleanup interact?

## Context

The sys plan already accepts options maps, nonzero exit as data, captured output,
timeouts, kill-on-drop and sync-compatible handles. Do not reopen those choices without
new evidence. Allow-listed programs run with host OS authority; neither filesystem
roots nor program names sandbox the child's subsequent actions.

## Resolution requirements

Clarify run timeout versus Child.wait timeout, repeated wait/kill, final-clone drop,
large simultaneous stdin/stdout/stderr, output-limit precedence, and cleanup/reaping.
Determine the policy for inherited pipe handles or descendants that can outlive the
direct child; distinguish guarantees from documented limits. Address command-name
versus absolute executable identity and inherited environment in the reviewed-script
trust model. Specify fixture-observable cases and platform differences.

Reference: ../../../docs/sys-package-plan.md sections 3.3, 4.4 and 5.
