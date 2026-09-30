# Windows scoped runner task record

Date: 2026-09-30. Worktree: `/Users/hoppworks/projects/rhai-windows-scoped-runner`,
branch `task/windows-scoped-runner`, base commit `4dbe23d8abb91c5a981a60c2d67d1c6a32af6f61`.

## Static deliverable

- Candidate source: `tools/windows-scoped-runner/ScopedRunner.cs`.
- Usage, bounds and explicit limitations: `tools/windows-scoped-runner/README.md`.
- Candidate behavior is not accepted for execution. It uses suspended creation,
  assignment to an unnamed kill-on-close job, then resume; assignment failure
  terminates/waits the exact still-suspended process. It scopes Cargo and temp
  environment paths to a generated runtime and has a fixed 30-minute deadline.
- The independent guest monitor that must retain lease/runtime ownership after
  runner or controlling-connection death is still undesigned and unimplemented.
  Runtime deletion and post-death diagnostic export therefore remain unverified;
  the candidate intentionally leaves runtime data instead of deleting without
  independent confirmation.

## Guest/native state observation

The only guest used was the authorized `rhai-win11-quality` domain
(`dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19`) on authorized `workhorse` via its
domain-specific `qemu:///system` console. Current hypervisor state and historical
serial records were inspected. The latest framebuffer was uniformly black. One
reversible 100ms Shift wake was sent to that exact domain, followed by a second
screenshot; it remained uniformly black. No further input was sent. The historical
desktop image in the baseline README is not evidence of current guest UI state.
No credential screen was entered, no credentials were requested or handled, and
the locked local Mac was not unlocked or changed.

Captured files: `guest-preflight.png` and `guest-after-shift.png` in this
directory. They document the two black captures. Current proof could not establish
an interactive desktop or a safe in-guest compiler/supervisor bootstrap path.
Both are 1280x800 PNG captures with SHA-256
`05713dbacb00cfa92e8cad1581147b0f1349f6ee14c97d122440aff36011bd53` (identical
frame contents before/after the Shift wake).

## Gate matrix

| Gate | Result |
| --- | --- |
| Source staged only inside unique runtime; environment/output isolation | Static candidate only; native unverified |
| Payload/grandchild actual job membership | Unverified |
| Success, failure, deadline and cleanup/readback | Unverified |
| Wrong assertion fails, restored assertion passes | Not run |
| Live grandchild interruption and exact runtime cleanup | Unverified; independent guest monitor absent |
| Independent monitor survives runner/SSH loss; bounded lease/evidence export | Unverified; design unresolved |
| Assignment failure and nested job restriction with no fallback | Unverified |
| Unrelated owned sentinel preserved | Unverified |
| Native compile/bootstrap and integration with Rhai Windows test command | Not run |

## Exact activity/resources

Completed actions: read-only project/VM evidence inspection; domain-specific
state/screenshot inspection; one reversible Shift wake and its follow-up
screenshot; static source/document edits. No build, package test, remote source
copy, remote runtime, guest process, service change, reset/reseed, admin operation,
or remote Git write was performed. The only task-owned local artifacts are this
worktree/branch, candidate source/docs, and the two ignored screenshots under
`.scratch/windows-scoped-runner/`. There is no live guest or workhorse command,
process, tunnel, or build from this task. Historical VM-owned domain/disk/runtime
resources remain untouched.

## Final state

Native acceptance is blocked by unavailable current guest UI and the unresolved
independent monitor requirement. Do not proceed to any Windows package build
using this candidate until the independent lease/cleanup design is implemented
and all native gates pass. No claim of ready-to-use behavior is made.

## Static correction follow-up

After the initial candidate commit, static review found that the basic job
accounting counters used pointer-sized fields instead of the Win32 `DWORD`
layout. The declarations now use `uint` for those four counters; the related
extended limit declaration explicitly models nested basic-limit, six 64-bit
I/O counters, and pointer-sized `SIZE_T` values. All `INFINITE` cleanup waits
were removed. The exact unassigned suspended child is terminated and waited for
with a 30-second bound; job cleanup polls active membership within the same
bound. Termination/query failures surface as errors. Microsoft's first-party
structure/API references are recorded in the candidate README.

This is static correction only: no C# compilation or Windows/native execution
occurred. The independent monitor/lease and safe runtime deletion design remain
unresolved, and the black-console evidence above is unchanged.
