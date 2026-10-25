# Independent combined review: native Windows Rhai file contract

Verdict: **PASS for the single `sys_fs::test_open_file_default_preserves_contents_and_shares_cursor` criterion at the recorded native Windows source/toolchain/features tuple**. Reviewed 2026-10-25. This is not whole-target, Windows package or release acceptance.

The reviewer re-read central rules at `e1a3b95a`, project AGENTS at `37f95ff6`, and the review skill at `a9b6618b`. The original serial export's 199 frames and all 12 files match the saved hashes and lengths; the raw serial hash and byte length match. The bound source contains the named public Engine/sys/real-OS test. The wrong-expectation RED failed at the intended assertion; restored GREEN passed, and both runs independently read the host file as `"original XYyload"`.

The bound public Driver exited 0 in about 63 seconds, drained its pipes, used no observer kill, and left no owned executables. The journal has the eight expected transitions, ending in `REMOVED`. `cargo clean --locked` removed 1,338 private target files, the owned-work hardlink and ReadOnly controls succeeded, and the observer checked that the exact runtime is absent.

The retained outer guest scope and host media/stage still require exact evidence-first retirement. Other Windows product paths and A–F/release criteria remain open. No build, test or edit was performed by the reviewer.
