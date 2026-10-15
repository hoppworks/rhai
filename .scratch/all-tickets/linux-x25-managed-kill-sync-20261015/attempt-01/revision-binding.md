# X25 sync revision binding

- Integrated source revision: 12adebd79b7454384e1d8c1d8a06e30fd6a7393a.
- Cargo.toml SHA-256: cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e.
- Cargo.lock SHA-256: 2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425.
- Unix process source SHA-256: 2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6.
- tests/sys_process.rs SHA-256: 9b031886eb3b4d365664a244e68ab574ef110e3cc7d41efe5f457d0d1fcb1dbe.
- Host, toolchain, profile and runner/session paths: evidence/environment.txt.
- Cargo statuses and durations: evidence/statuses.txt. Matching raw outputs and temporary RED/restored source hashes are retained beside it.
- Scoped runner SHA-256: 25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e.

The only source mutation changes the temporary expectation that managed members be gone to expect the opposite. GREEN sources are the restored test source hash above.
