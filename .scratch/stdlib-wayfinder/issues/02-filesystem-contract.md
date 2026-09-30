# Settle path semantics before repairing filesystem access

Type: grilling
Label: wayfinder:grilling
Status: claimed
Assignee: current Codex session
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

## Concrete proposal awaiting owner decision

### Authority and path rules

1. **Configured roots identify the OS-resolved directory.** Preserve symlink/parent
   semantics when opening the host's root. For example, if `alias/link` points to
   `actual/child`, then `alias/link/../allowed` selects `actual/allowed`, not
   `alias/allowed`. Never silently grant the lexically substituted directory.
   Failed root opening is a configuration error, not a fallback to another root.
2. **Confined paths remain capability-relative.** Keep the opened root handle as
   the authority. A script path that leaves the selected root, even if it later
   re-enters, is denied. A lexical traversal guard is conservative rejection only;
   it must not rewrite a path into a different file or replace cap-std enforcement.
3. **Relative symlink targets may resolve inside the selected root.** A target
   outside it is denied. Preserve the accepted cap-std limitation: absolute symlink
   targets are denied in confined mode even when the target lies inside the root.
   Absolute script paths into a root remain supported; these are a different case.
4. **Absolute root spellings do not change authority.** Support the configured
   root spelling, the canonical root spelling and OS prefix aliases needed to
   express that same directory (the reviewed macOS `/var` versus `/private/var`
   case). All continue through the opened root; do not resolve arbitrary script
   paths with canonicalize and use a prefix check as the security boundary.
   Do not promise automatic discovery of every unrelated filesystem alias.
5. **Unrestricted mode has ordinary host filesystem path behavior.** Existing
   read/write/delete grants still apply, but there is no artificial confinement to
   a nearest ancestor. Legal absolute and relative symlink targets and symlink/`..`
   paths should behave as the corresponding host operation, including its errors.
   This is explicitly suitable only for host-authorized reviewed scripts.
6. **Multiple-root routing preserves the existing contract.** Relative script
   paths use the first configured root. Absolute paths use the most specific
   matching configured root; changing equivalent root spelling must not change
   the chosen permissions. A denied operation never falls back to a more permissive
   outer root. Copy checks read authority on the source and write authority on
   the destination; rename across roots remains denied.
7. **UTF-8 remains the script path boundary.** `read_dir` encountering a supported
   but non-UTF-8 name raises NotUtf8 as specified. A filesystem that cannot create
   that fixture is a documented coverage limitation, not a library failure or a
   passing proof of that behavior. Keep platform/filesystem availability explicit.

### Regression expectations from the review

| Finding | Contract expectation | Independent observation |
|---|---|---|
| Configured root with symlink then parent | Read/write only in the OS-selected directory | Sentinel in lexical directory unchanged; written file exists only in intended directory |
| Unrestricted absolute and sibling-relative symlinks | Read returns actual payload; operation-specific mutation matches host behavior | Host reads target data and checks unrelated entries |
| macOS configured/canonical/system-prefix root spellings | Read succeeds with identical authority through supported equivalent spellings | Host fixture payload and protected-state checks |
| Unsupported non-UTF-8 fixture | Do not mistake fixture creation failure for API behavior | Report actual filesystem capability and native coverage |

### Additional required cases

- Ordinary `sub/../file` inside the root versus a path that leaves and re-enters.
- Symlink/parent combinations that lexical simplification would redirect to a
  different sentinel, both in root configuration and unrestricted script paths.
- Confined relative inside/outside targets; confined absolute targets still denied.
- Nested roots with different access levels, equivalent root spellings, first-root
  relative routing and no fallback after denial.
- Missing targets, missing parent directories and dangling links: assert the
  documented operation/error, never manufacture success via path simplification.
- Read, create/write, copy, rename and removal cases retain their distinct host
  semantics; do not treat canonicalizing a final target as a universal resolver.

These are contract expectations for later TDD implementation, not newly executed
proof. The existing public-entry-point repro and independent read-back are captured
in `/Users/hoppworks/projects/rhai-review-sys-windows/.scratch/review-sys-windows/`
(`repro.rs`, `repro.log`, `native-tests.log`, `policy-tests.log`). No review artifact
or production source was modified.

## Comments

The proposal preserves the accepted confined/permissive split and cap-std limitation.
Owner confirmation is requested for this exact contract before closing the decision.
In particular, it makes ordinary OS symlink semantics explicit for unrestricted mode
and rejects lexical substitution when selecting the host-configured root.
