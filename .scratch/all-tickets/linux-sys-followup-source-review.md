# Linux sys follow-up source gate

Owner approved the existing single corrected package with "ok go". Original setup failure and elapsed history remain unchanged. Dispatch 2026-09-30 17:40:14 UTC; execution ends by 18:05:14, inclusive review ends by 18:10:14. No new runtime has started at this gate.

Reviewed immutable source 6da4e5d7bd10d2f3f9095133d73a0d4ae73b84a9 and corrections 552e957631e299451f7ca83fd5b4506d6a088418. OCR preview and rules account for all three files: prepare-followup.sh, launch-followup.sh and run-followup.py; reviewed 3/3, skipped 0, coverage 100%. Root read the complete source and correction diff.

Source-only findings corrected before execution: missing RUSTUP_HOME, unsupported generate-lockfile jobs argument, launcher self counted as cleanup failure, early grep SIGPIPE risk under pipefail, and generated lock preservation before any test failure. These are pre-launch corrections, not failed implementation measurements. Existing /root/.rustup is used without installation or configuration changes.

Complete production archive is e1db9baafaaf30d94085f0cc6f661f363399f193, SHA256 c934633c7889e4a427a87d557bbc578146e4db641c4fde2c93ff3fd4f047aa47; codegen manifest checked before staging and after extraction. Private Cargo home/target, debug and incremental disabled, jobs two, serial fixtures. Eight sys-only profiles, three real Engine/OS fixture targets each, exact wrong abc assertion101 and restored one-pass check. Per-command statuses/logs exported immediately, generated/final lock retained. First unexpected assertion stops. Absolute deadline and 900-second invocation cap do not renew between checks. One-second storage/ancestry sampling preempts at 1.5GiB under 2GiB hard allowance; sampled maxima do not prove continuous peaks.

Cargo inherits the scoped process group. Copied run_scoped runner owns group cleanup and runtime removal. Launcher verifies recorded identity/group absence after runner termination, explicitly leaves only its own still-running launcher for independent post-exit readback. Root must independently verify launcher, recorded PIDs/start identities, group and exact runtime/stage absence after export; unknown fast identities remain explicit limitations. Staged driver/launcher/runner hashes must match local frozen inputs before execution. No production edits, Windows scope or other stopped package resumed by this gate.

Source gate accepted at 17:50 UTC. This authorizes the one already approved private invocation, not runtime acceptance or another launch.
