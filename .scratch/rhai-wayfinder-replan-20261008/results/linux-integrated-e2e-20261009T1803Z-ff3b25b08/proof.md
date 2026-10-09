# Linux integrated real-OS acceptance slice

The published source snapshot `ff3b25b0889c32e0e505517fc605d4b6cd2d5208` passed the combined Linux integration command on Workhorse x86_64 with Rust/Cargo 1.77.2 and the accepted lock. Cargo first parsed the complete workspace successfully with `metadata --locked --no-deps`; the actual integration command then returned 0 in a single scoped invocation. Eleven test targets reported 165 passed, 0 failed and 3 ignored. The outer `sys_process` target passed 58 and ignored its three separately invoked bounded/census controls; nested `1 passed; 60 filtered` summaries are intentional exact-selector child invocations, not filtered outer suite coverage.

Command:

```text
/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin/cargo test --locked --jobs 2 --features testing-environ,sys,net,metadata --no-fail-fast --test sys_policy --test sys_env --test sys_fs --test sys_process --test sys_process_report --test combined_sys_net --test net_connect --test net_listen --test net_metadata --test net_reads --test net_writes -- --test-threads=2
```

Targets: `sys_policy`, `sys_env`, `sys_fs`, `sys_process`, `sys_process_report`, `combined_sys_net`, `net_connect`, `net_listen`, `net_metadata`, `net_reads`, and `net_writes`. The combined test confirms sys/net coexistence in one real Engine; the net targets cover live loopback TCP peers, endpoint policy, byte readback and metadata; sys filesystem and process targets use the real host OS. Test source independently asserts host file, peer and child effects. Earlier focused RED/GREEN packets remain the assertion-sensitivity proof for their named criteria. This aggregate pass is a Linux integration checkpoint only, not completion of X24, the full feature/OS/MSRV matrix, A–F, Windows custody or release acceptance. `net_no_object` and the three ignored process-only drivers are outside this default-feature command and retain their own criteria.

Attempt history is retained. Attempt01 used a 1.0 MB reduced source archive; Cargo exited 101 before compilation because the workspace manifest references `examples/serde.rs`. Its stdout was empty, Cargo stderr records the missing path, the runner returned 101 in one second, and the private runtime was removed. This was setup failure, not product RED. Attempt02 includes the complete tracked examples and benches; source archive SHA-256 `4d3a8e3a1ddfa7608996b3d14c986b22737ab2a3f2e574893e13011453dc83a6`. It used the exact lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`; Cargo metadata and tests returned 0, elapsed 42 seconds, and the owned runtime was absent after runner exit.

Full commands, environment, raw stdout/stderr, target summaries, scope identities, cleanup and both original source inputs are retained under `attempt01/` and `attempt02/`. The combined independent review accepted this limited Linux slice; see `combined-review.md`. All files are covered by `manifest.sha256`.
