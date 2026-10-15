# Combined independent review — X35 pipe-closed worker, sync profiles

**Result: PASS for these exact selectors and profiles only.** The review accepts direct_run_returns_with_pipe_closed_worker_live_control and managed_run_closes_pipe_closed_worker_before_return on Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, under checked testing-environ,sys,sync and unchecked testing-environ,sys,sync,unchecked.

Both intentionally inverted DirectChild controls exited Cargo 101 at the expected PIDFD assertion that a worker remained live at API return. The restored DirectChild and paired Managed runs passed 1/1. Each run acquired PIDFDs for the exact leader, worker and leaf with recorded PID/start-time/parent/group identity, and fixture cleanup is recorded.

The run binds to revision b289e6ab88890bbd469375acac561bdd950aa1e0, Cargo.toml SHA-256 cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e, Cargo.lock SHA-256 2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425, Unix source SHA-256 2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6, test source SHA-256 9b031886eb3b4d365664a244e68ab574ef110e3cc7d41efe5f457d0d1fcb1dbe, runner SHA-256 25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e, and outer runner status 0. The exact owned runtime and session scope are absent.

The selected test bodies are byte-identical to the previously accepted base X35 row. The intervening Unix product-source change is a cfg guard in an unrelated test. The earlier base and unchecked rows remain applicable and are reused without another build. A foreign Tauron one-job build appeared during this run and was preserved; memory and disk were ample, though swap was nearly full.

This review accepts only the two named sync-profile rows. It does not close other X35 selectors, features, platforms, MSRVs or Ticket03/A–F requirements.
