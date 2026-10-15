# Combined independent review — X24 try_wait sync profiles

**Result: PASS for the exact selector and profiles only.** Review accepts direct_spawn_try_wait_returns_unit_until_child_exits on Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, with checked testing-environ,sys,sync and unchecked testing-environ,sys,sync,unchecked.

Both intentionally incorrect terminal-code expectations exited Cargo 101 at the targeted assertion. Both restored GREEN runs passed 1/1. Logs show the real child ready and alive while pending try_wait returns unit, terminal status observed before wait, cached exit code 0, and ESRCH for the exact child PID. Revision, source/lock hashes, OS, toolchain, runner status 0 and cleanup are bound. The package checksum manifest verifies and the exact session scope is absent.

The accepted Linux base row remains applicable to its original scope. The selected test body differs from the previously accepted revision only by a semicolon, and ProcessChild::snapshot is byte-identical. The prior base row is reused; no base rerun occurred. Other X24 profiles, platforms, MSRVs and Ticket03 requirements remain open.
