# Combined independent review: X36 Linux sync rows

**Result: PASS** for `managed_scope_kernel_setpgid_denial_cleans_created_group` on lllm Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, under checked `testing-environ,sys,sync` and unchecked `testing-environ,sys,sync,unchecked`.

The checked-sync expected RED is from the preceding invocation at the same pinned revision, selector, lock, feature profile and seam-disabling mutation. It exits 101 at `managed scope setup failure must not run the program`; that attempt has no separate mutated-source hash receipt, so its binding relies on the preserved run record and deterministic mutation recipe. The corrected invocation passes restored checked GREEN and unchecked RED/GREEN. In both GREEN runs, public `run` and `spawn` report the real kernel `setpgid` denial, do not execute marker commands, retire reservations, and independently establish exact child PID and process-group absence. The runner returned 0; restored source hash matches the archived input; checksums verify; all exact owned scopes are absent.

This accepts only the named selector and these two Linux sync profiles. It does not close other X36 setup paths, OS, toolchain, feature or Ticket03 rows. Two earlier invocation failures were setup/recovery failures, not product failures. The unrelated Tauron build was preserved.

## Standards

PASS. Source, lock, toolchain, runner, scope and cleanup are bound. The process-ownership evidence and protected fixture markers are read back independently. The checked-sync RED's missing mutated-source hash is a provenance limitation retained explicitly above.

## Spec

PASS for the exact acceptance slice and limits above. The test reaches the real Linux kernel `EPERM` by making the child a session leader before production setup, exercises both public `run` and `spawn`, and verifies cleanup rather than silent fallback.
