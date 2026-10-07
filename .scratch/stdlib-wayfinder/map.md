# Plan a reliable Rhai host standard library

Type: map
Label: wayfinder:map
Status: charted
Owner: repository owner
Tracker: local Markdown

## Destination

An owner-reviewed, implementation-ready specification for completing the optional
`sys` package and adding a separate optional TCP `net` package for owned or reviewed
scripts. Each planned slice has a public contract, a test-first route, explicit
compatibility requirements, and observable acceptance criteria.

The map is complete when all child decisions are resolved and no in-scope question
blocks implementation. Completing this map does not mean the library is implemented.

## Notes

- Scope and trust boundary accepted by the owner on 2026-09-30: complete `sys`
  (environment, filesystem, processes, compatible file handles); plan TCP separately.
  Host permissions are explicit and deny by default. Program permission is not OS
  isolation; running arbitrary untrusted programs is outside this effort.
- Quality and low maintenance take precedence over speed. Preserve Rhai conventions
  and existing accepted decisions unless a specific contradiction requires owner review.
- Use wayfinder for decisions, grilling and domain-modeling for owner choices,
  research only for missing facts, and TDD/e2e-proof during later implementation.
- Existing contract: [sys package plan](../../docs/sys-package-plan.md).
  Current evidence: [network assessment](../../docs/net-package-assessment.md).
  Current open packages and evidence applicability are in section 6 of that plan;
  historical phase-complete claims are not acceptance. Campaign state is
  [all-tickets/coordinator-state.md](../all-tickets/coordinator-state.md).
- Workflow remains strict. Later explicit owner instructions authorized verified
  pushes/Coordinator merges to the hoppworks/rhai fork main, superseding the earlier
  local-only privacy instruction for that scope. Never write upstream. The owner
  resumed implementation on 2026-10-07; current package status, proof and remaining
  work are tracked in the all-tickets coordinator state.
- Test patterns come from cap-std (path semantics), rustix (operation/platform cases),
  and Tokio (resource lifecycles); write tests against Rhai contracts rather than
  copying another library's expectations. Do not reopen the broad precedent survey.
- Tracker: one local child file per decision; scan open tickets and their `Blocked by`
  fields for the frontier. Claim before working; append the answer on resolution.
- Ticket gate: each question below blocks a concrete API or acceptance decision.
  No standalone tooling-shopping, framework-building, or speculative feature tickets.

## Decisions so far

- [Define observable acceptance and test structure](issues/01-acceptance-contract.md#answer):
  real Engine/package/OS tests, independent observation, a demonstrated failing
  control and isolated fixtures are binding; concrete commands are in AGENTS.md.
- [Settle path semantics before repairing filesystem access](issues/02-filesystem-contract.md#answer):
  OS-selected roots, capability confinement, unrestricted host semantics and
  consistent supported root spellings are required; foundation proof exists and
  current native/feature gaps remain in the campaign plan.

- [Close process lifecycle and resource-limit ambiguities](issues/03-process-contract.md#answer):
  the initial release includes direct-child supervision and explicitly selected
  managed groups/jobs, with cancellation-safe capture, no silent fallback and
  native cleanup proof. Exact config/error representation is reviewed in ticket 06.

- [TCP authority](issues/04-tcp-authority.md): separate connect/listen grants,
  numeric addresses, finite limits and no OS sandbox claim accepted.
- [TCP API](issues/05-tcp-api.md): streams/listeners, byte/text lifecycle and
  compatibility accepted; current native matrix remains implementation acceptance.
- [Compatibility and release](issues/06-compatibility-release.md): core1.66,
  optional1.77.2, native three-OS and feature/API/documentation gates accepted.

## Current frontier

All six decision tickets are resolved as specifications. Remaining implementation
and acceptance packages A–F live in the existing sys plan, section6; this index is
not a competing execution plan. The owner later resumed implementation under that
plan. No decision tickets are reopened, exhausted attempts are not renewed, and
the accepted contracts remain binding.

## Out of scope

- Implementing production features or fixing the reviewed code during charting.
- Isolation of arbitrary untrusted scripts and child programs.
- UDP, HTTP, TLS, async runtime integration, and unrelated standard-library expansion
  in the initial TCP scope; revisit only through a new scope decision.
- Upstream publication or extraction into separate published crates in this effort.
