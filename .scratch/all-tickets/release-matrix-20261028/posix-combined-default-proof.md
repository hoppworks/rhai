# Native POSIX Rust 1.77.2 default Sys+Net package gate

Status: **accepted for the ten executed `testing-environ,sys,net` integration targets on macOS and Linux** after one independent combined review. This closes the current-source POSIX default-profile package-minimum slice only. Ignored tests and the remaining OS/feature/release rows remain open.

## Bound inputs and execution

- The [macOS preflight](macos-combined-default-attempt01/preflight.json) and [Linux preflight](linux-combined-default-attempt01/preflight.json) compared all 448 archived product files to fork-main `41070b3c69ac4210b64c701ed2790e9b51e8eb70`: zero mismatches. The immutable [source archive and manifest](macos-net-alone-attempt02/proof.md) have SHA-256 `6ff82b95cbbf65ba919161932a63d74f668f8e6e6d88682418797eca93565384` and `b829308ab356d7aaaf7bf8d3acc9f65aab8fb316192d9b1b69e3365d78c834fd`; exact Cargo lock SHA-256 `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
- Both machines ran their native Cargo and rustc 1.77.2 with `--locked`, two build jobs, private Cargo home/target and an owned source copy below `AGENT_RUNTIME_DIR`. The existing POSIX runner SHA-256 `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e` bounded each whole run to 600 seconds. The [macOS launcher](macos-combined-default-attempt01/launch.sh) and [Linux launcher](linux-combined-default-attempt01/launch.sh) checked absent own scopes, input hashes and at least 4 GiB free space. Their [run scripts](macos-combined-default-attempt01/run.py) used the source copy as Cargo's explicit working directory.
- Each [macOS command record](macos-combined-default-attempt01/commands.json) and [Linux command record](linux-combined-default-attempt01/commands.json) contains: compile all ten targets with `cargo +1.77.2 test --locked --features testing-environ,sys,net --test <target> ... --no-run`; run the exact named `combined_sys_net` wrong-host control; then run each of the ten targets serially with `--test-threads=1 --nocapture` in the same owned build scope. The target list is `combined_sys_net`, `sys_policy`, `sys_env`, `sys_fs`, `sys_process`, `sys_process_report`, `net_connect`, `net_listen`, `net_reads`, `net_writes`. `net_metadata` needs the separate `metadata` feature; `sys_process_windows` is Windows-only.

## Real-OS results and sensitivity

| Native host | Wrong host readback | Executed target suites | Total passed | Ignored process cases |
|---|---|---:|---:|---:|
| macOS 27.2 arm64 | exit 101, intended assertion | 10/10 exit 0 | 157 | 1 |
| Linux 7.2.11 x86_64 | exit 101, intended assertion | 10/10 exit 0 | 165 | 3 |

The [macOS RED](macos-combined-default-attempt01/wrong-host-readback.log) and [Linux RED](linux-combined-default-attempt01/wrong-host-readback.log) failed after the public Rhai Engine ran both registered packages against a real temporary file and independent OS-selected TCP peer. The fresh host file read returned `filesystem-payload`; the deliberately wrong expectation was `incorrect filesystem expectation`. Each harness reported one failed test and exit 101. The restored [macOS combined GREEN](macos-combined-default-attempt01/green-combined_sys_net.log) and [Linux combined GREEN](linux-combined-default-attempt01/green-combined_sys_net.log) passed the same test with the same executable used by RED, and the fresh host readback, exact independent peer bytes and typed errors were asserted. This control establishes sensitivity of that host-readback assertion, not every assertion in the target suite.

The [macOS result](macos-combined-default-attempt01/result.json) and [Linux result](linux-combined-default-attempt01/result.json) give per-target counts and executable identities. Their `sys_process` logs contain intentionally failing nested child-test output; the outer target's final harness summary passed (52/0/1 on macOS; 61/0/3 on Linux). The ignored cases are outside this gate and retain their separate evidence/remaining status.

## Export, readback and scope

The [macOS readback](macos-combined-default-attempt01/readback.json) independently checked original result/log hashes, command statuses, the RED/GREEN assertion and executable identity, and confirmed the exact owned scope absent after outer exit 0. The [Linux remote export](linux-combined-default-attempt01/remote-export.sha256) was checked against every copied original; [Linux readback](linux-combined-default-attempt01/readback.json) checked statuses, RED/GREEN, per-target counts and 24 unique file hashes. `source-manifest.json` appears twice in the 25-line remote hash list because both `*.json` and its explicit name selected it; both hashes agree. After export, only the exact owned Linux stage files were removed and the stage was retired; a separate [SSH cleanup readback](linux-combined-default-attempt01/cleanup-readback.txt) found stage and scope absent. No foreign process or build was changed.

The [independent combined review](posix-combined-default-review.md) passed Standards and Spec for the named executed slices with no actionable finding. It excluded the ignored process cases, Windows, other profiles and overall release completion.
