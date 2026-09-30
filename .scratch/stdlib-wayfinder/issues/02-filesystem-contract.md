# Settle path semantics before repairing filesystem access

Type: grilling
Label: wayfinder:grilling
Status: open
Parent: [Plan a reliable Rhai host standard library](../map.md)
Blocked by: none

## Question

Which exact root, parent-component and symlink behaviors does the public filesystem
contract promise in confined and permissive modes?

## Context

The accepted sys contract uses cap-std confinement and string paths. Four review
findings cover root symlink/parent normalization, permissive symlink traversal,
macOS root aliases, and a non-UTF-8 fixture invalid on the tested filesystem.
The last is a test portability issue, not evidence to change the public path contract.

## Resolution requirements

Specify observable examples for configured/canonical root aliases, symlink then `..`,
relative and absolute symlink targets, multiple roots, and permitted/denied operations.
Distinguish OS-supported fixtures from contract failures. Link each review finding to
its intended regression expectation. Preserve accepted semantics unless explicitly
revised; identify cap-std constraints instead of weakening confinement silently.

Use ../../../docs/sys-package-plan.md as the existing contract. Production fixes
follow this decision and the acceptance contract; they are not part of resolution.
