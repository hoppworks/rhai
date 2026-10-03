# Linux managed deadline escaped-pipe proof preparation

This is the escaped-pipe recipe record. Native107 was consumed: the intended control returned 101, but proof validation failed because its PIDFD parser expected the wrong receipt prefix. The corrected recipes ran in native108; the intended control returned 101 and the first three base regressions passed, then proof validation stopped on an incorrect `wait_unit=true` expectation. The retained-pipe test itself passed and its fixture cleanup completed. Four new-test feature rows did not run; acceptance is not claimed.

The immutable source input is `523608648dcae99bc0f6b46eaf2bb91fa4ecc752`. It adds `managed_run_deadline_cancels_escaped_pipe_holder_under_fixture_reaper` in `tests/sys_process.rs` (SHA-256 `5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb`). The test exercises the public Engine `run` timeout path while an independently adopted holder keeps both capture pipes open. It records the returned timeout report and incomplete captures, exact host/reaper/leader/holder/sentinel PID/start/group identities, leader and holder pidfds, live holder/reaper/host/sentinel at the API boundary, and a post-return challenge that requires EPIPE on both closed capture writers. The managed group is already absent at return. The exact fixture reaper then releases and waits for the escaped holder, and all assertions follow the complete cleanup receipts.

The bounded recipe has eight exact test invocations plus three private Rust 1.77.2 setup commands:

- One wrong-control invocation inverts the timeout-report assertion after the fixture has printed its completed boundary and cleanup receipts. It must return 101 at the named assertion, while the parser independently accepts the boundary, EPIPE challenge, exact reaper wait, and PID/start/group closure.
- Four GREEN invocations run the exact new test with `testing-environ,sys`; `testing-environ,sys,sync,metadata`; `testing-environ,sys,f32_float`; and `testing-environ,sys,unchecked`.
- Three base regressions run exact test filters for prompt success, held zombies, and `managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes`.

The base success and held-zombie runs reuse their accepted closure parsers and must produce the two original closure artifacts. Each new-test invocation produces one closure artifact, for seven required, pre-existing closure files total. The retained-pipe test is only an affected regression: it checks its exact outer test result, live escaped-holder/sentinel and EPIPE receipts, and its own fixture cleanup assertions. It does not emit the independently read-back PIDFD closure artifact used by the new deadline test, so the collector does not invent or require one.

The source archive excludes `.scratch` using the reviewed archive helper. Frozen input pins:

| Input | SHA-256 |
|---|---|
| Source archive at `523608648dcae99bc0f6b46eaf2bb91fa4ecc752` | `998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b` |
| `tests/sys_process.rs` | `5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb` |
| `Cargo.lock` | `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425` |
| Process contract | `0edcab444948bce58d7530202ca75688160efee80143f8be17fc29b96cd5da68` |
| Base proof helper | `59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06` |
| Prompt-success/held proof helper | `83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0` |
| Archive helper | `a75b4e807f03e8247ed821df871ceb35e776b7f699046d7a099dd0b85199fd8b` |

Recipe pins:

| Recipe | SHA-256 |
|---|---|
| `linux-managed-escaped-pipe-proof.py` | `890de4a18441e1240f20979748686bf66284b5798df116ddfae3165c259c0389` |
| `linux-managed-escaped-pipe-stage.sh` | `a438f4524a860d67b8d3ad1da9a468015c2d9a342460c55f0f27197fb789f7a0` |
| `linux-managed-escaped-pipe-launch.sh` | `4d9ae4c622462126aac08ab9c2d902cd09840ae40de40edc6e3235d9aa5ce899` |
| `collect-linux-managed-escaped-pipe.py` | `17af321661dee2b90bf8f49aaca3ebef2a65459461ad9c7a52731461a1e394cd` |

Native108 used `/root/rhai-linux-managed-escaped-pipe-20261003-52360864-108` and `/root/.local/share/agent-builds/rhai/linux-managed-escaped-pipe-20261003-52360864-108`; its terminal status was 1 because the proof helper rejected the truthful retained-pipe receipt. Do not reuse those paths. The PIDFD parser correction accepts the exact `managed_pipe_pidfd_acquired` prefix and rejects missing/wrong prefixes and mutated start/group identities. Limits remain 600 seconds outer, 585 seconds scoped runner, 540 seconds helper with 30 seconds for export, two Cargo jobs, 16 descendants, 1,572,864 KiB preemptive storage stop, and 2,097,152 KiB hard RSS/storage bounds.

The selected old fixtures and receipt helpers are gated out for `no_float` and `no_index`, so this package makes no claim for those feature configurations. The collector requires all seven original closure files before validating them, compares fresh exact PID/start/group readback without writing or repairing evidence, verifies source restoration and the complete export, and only then performs hash-gated exact cleanup. Full native acceptance remains pending a reviewed package, fresh machine inventory, and a new allocated run (native109).

Native108 original retained-pipe stdout/stderr are `/private/tmp/rhai-native108-retained-original.stdout` and `/private/tmp/rhai-native108-retained-original.stderr`. The independent source reading and raw stderr confirm `wait_result` is a completed report: `wait_result.as_ref().is_ok_and(|value| value.is_unit())` emits exactly `wait_unit=false`, followed by exact leader/holder/sentinel cleanup receipts. Proof and collector now require exactly one `wait_unit=false` marker, rejecting missing, duplicated, or true markers. The expected control and base-prompt/base-held regressions returned 101/0/0; retained-pipe returned 0, but its fixture closure artifact was not emitted before helper validation stopped. Root is preserving/exporting those three original closure artifacts separately; never regenerate or overwrite them. No new-test feature GREEN ran in108.

Prospective native109 paths are `/root/rhai-linux-managed-escaped-pipe-20261003-52360864-109` and `/root/.local/share/agent-builds/rhai/linux-managed-escaped-pipe-20261003-52360864-109`. Source revision/archive, Cargo.lock, test file, contract and base proof pins remain unchanged. Refreshed recipe pins: proof `890de4a18441e1240f20979748686bf66284b5798df116ddfae3165c259c0389`, stage `a438f4524a860d67b8d3ad1da9a468015c2d9a342460c55f0f27197fb789f7a0`, launch `4d9ae4c622462126aac08ab9c2d902cd09840ae40de40edc6e3235d9aa5ce899`; the collector embeds all three. Native109 remains unallocated pending the affected independent recipe review and fresh machine guard.

The collector additionally binds the original retained-regression leader/holder/sentinel PIDs and groups. Because those receipts have no start ticks, current and final readbacks require each PID absent (NotFound only), reject reused PIDs and unreadable identities, and require both groups empty. No closure artifact or start tick is fabricated.
