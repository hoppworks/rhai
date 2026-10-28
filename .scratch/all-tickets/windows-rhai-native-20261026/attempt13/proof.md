# Native Windows process attempt13: failed test assumption

The packet's 439-file source manifest is
`829d6afa99eaf929c4c0bf17dda6af440dd0efee67cdad84a6209482e9be5a8a`;
the lock is `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
The independent pre-execution review returned READY. The native Driver exited 2
after 79.550 seconds. The original COM1 segment has 104 ordered frames and nine
hash-verified files; its SHA-256 is
`c857517641d6f988ce95f02d5213e630a94a86a0ee71e60b8f7f78dcd965c2ef`.
The observer confirms exact Driver exit, drained pipes, no pending custody and
owned executables stopped. Four journal records were exported; no runtime-removal
claim or product acceptance follows from this failed run.

The source compiled. The deliberate wrong-exit assertion failed as intended and
seven report tests passed. The public timeout case then failed with
`timeout_range_child_record=Some("pid=3260\n")`: its `1.0e19` seconds was still
representable by the Windows `Instant` in this run, so the test's premise was
incorrect. The original logs are in `original-export/`. The corrected test and
the actual overflow branch are verified separately in attempt14; this result
is retained as cause history, not counted as a product regression or GREEN.
