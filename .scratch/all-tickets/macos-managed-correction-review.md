# Managed control correction review

Reviewed baseline: `3e17e3f5c90d8f50fdbe6c0e1b8772851941d864`.
Corrected external source: `74943bb231f7f26e6951d946baa687465d72d3a8`,
including `9cadcfd7415a850e1db1efb64f3d870a19bf2bf9`.
OCR selects three changed Python files, all reviewed with affected callers and
applicable Python rules; total3, reviewed3, skipped0, coverage100%.
Preview and rules are preserved beside this record. Earlier unchanged source
review and narrow pure proof remain at macos-controls-review.md; no full review
or native acceptance is restarted merely because the checkout changed.

The corrected snapshot requires the fixture's own new PGID. Managed direct-child
KILL uses the exact retained unreaped Popen child PID without poll/wait/kill
side effects. Its controller confirmation and terminal status follow the single
anchored group signal and exact gate/anchor waits. The fixture in its separate
group still needs the existing passive termination and absence certificate;
this source correction does not assert it is killed by the command-group signal.
Both Managed Cargo commands retain separate stderr files and parse only JSON
stdout; other command callers retain their combined-output default. Strict JSON
rejection remains, so arbitrary diagnostic lines are not silently skipped.
No remaining material finding in this correction increment.

Independent original replay: macos-managed-root-regressions/receipt.json and
its logs. Frozen source inputs are copied into one private runtime; owner files
are untouched. Reader23 and adapter58 pass. Final tests against prior3e produce
meaningful wrong-PGID rejection and pre-group gate-poll AssertionErrors, each1.
The prior Cargo stream request check also fails1 because neither build separates
stderr; the corrected functional test additionally parses synthetic artifact JSON
with ordinary Cargo stderr retained separately. Restored adapter58 passes;
all ten input files restore byte-for-byte and Python AST parsing succeeds.
Runner0; 1.268 seconds measured helper interval. Cleanup readback confirms the
exact runtime absent and exact own empty session scope removed.

Acceptance is source-only, not strict native E2E. External corrected source is
not yet integrated wholesale into main: preserve its exact refs. Current public
API still lacks live identity-bound dual-stream read-progress evidence, so
Managed readiness stays fail-closed. Native ABI/tool confinement/interruption
and overhead requirements remain open; guardfalse and count84 unchanged.
The old hardcoded repository path is absent after an external checkout removal;
that independent setup prerequisite is returned to the existing owner as a
bounded source-only correction. No production process change or native/Cargo
launch is authorized by this review.
