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
  Prior review has four unresolved sys findings; do not treat inherited phase-complete
  claims as verified acceptance. Review references are in the coordinator state.
- Workflow remains strict verification and automatic Coordinator merge only after
  selected checks pass. The owner's 2026-09-30 privacy decision overrides automatic
  push: this effort stays local and on authorized workhorse; no remote publication,
  upstream contact, PR, or merge is part of charting this map.
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
  consistent supported root spellings are required; reviewed defects remain open.

- [Close process lifecycle and resource-limit ambiguities](issues/03-process-contract.md#answer):
  the initial release includes direct-child supervision and explicitly selected
  managed groups/jobs, with cancellation-safe capture, no silent fallback and
  native cleanup proof. Exact config/error representation is reviewed in ticket 06.

## Not yet specified

- Exact implementation slices, ordered by the resolved contracts and quality gates.
  Do not turn the old session estimates into delivery promises.
- Shared host policy/configuration vocabulary across `sys` and `net`, if TCP authority
  decisions demonstrate a real need; avoid introducing a common framework in advance.
- Which property, fuzz, or mutation checks earn their maintenance cost after concrete
  invariants and acceptance requirements have been chosen.

## Out of scope

- Implementing production features or fixing the reviewed code during charting.
- Isolation of arbitrary untrusted scripts and child programs.
- UDP, HTTP, TLS, async runtime integration, and unrelated standard-library expansion
  in the initial TCP scope; revisit only through a new scope decision.
- Upstream publication or extraction into separate published crates in this effort.
