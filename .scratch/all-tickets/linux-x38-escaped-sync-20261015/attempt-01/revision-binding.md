# X38 sync revision binding

- Integrated source revision: 2a1fce7916e9d6e97404f3d68caaf646dc3077a9.
- Cargo.lock SHA-256: 2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425.
- Cargo.toml SHA-256: cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e.
- src/packages/sys/process/unix.rs SHA-256: 2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6.
- tests/sys_process.rs SHA-256: 9b031886eb3b4d365664a244e68ab574ef110e3cc7d41efe5f457d0d1fcb1dbe.
- Host/toolchain/features and all eight test statuses: evidence/environment.txt, result.txt, statuses.txt.
- Scoped runner SHA-256: 25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e (evidence/runner-sha256.txt).

The accepted checked and unchecked base rows are reused from the prior reviewed X38 proof. Their source identity was compared against this revision: target selector bodies and the Unix process implementation path are unchanged; the delta is limited to unrelated stdin gating and later test additions. Thus the base rows remain applicable to these named selectors and do not need a rebuild. This binding is limited to the listed selectors and profiles.
