# Combined independent acceptance review — Linux Child.wait decoded expansion

**Verdict: accepted for native Linux x86_64, Rust/Cargo 1.77.2, features `testing-environ,sys` plus defaults, checked development/test profile.** This covers the one recorded Child.wait selector only. Darwin, other features, interruption coverage and the broader A–F package remain open.

## Rules and binding

The reviewer reloaded central Agent Skills HEAD `1b6e1da85f87cad25f7aafc91aa782319ac6ef93`, central/global and common AGENTS, project AGENTS, current roles, build-efficiently/TDD/resource-lifecycle guidance, and the memory entrypoints. The removed `~/.agents/AGENTS.md` was absent; current central repository instructions were used.

The exact source archive SHA-256 `68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644` is already bound to Git revision `34e0fa61a3d12fe6c41902c44618ff44e20d73d4` by the accepted X35 archive-to-tree readback. Test source SHA-256 `86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41`, lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, toolchain, native OS/target, feature selection, actual default/std feature profile and test selector match the captured run outputs.

## Acceptance evidence

Attempt02's wrong expected first raw byte reached the actual `wait must retain exact raw bytes` assertion and exited 101 (observed 10, deliberately expected 11). The reviewer independently reconstructed the mutated test-source SHA `229d28b4b8de53c935bfa61ff1874c55b6f6e775d9315e5eb86c554418fd3381`, matching the recorded digest. The payload restored the test source and read back the exact baseline SHA before cleanup.

Attempt01's restored-source GREEN remains valid and ran exactly one test: `1 passed; 0 failed`. It exercises public Rhai `spawn`/`Child.wait`, cloned and repeated snapshots, exact raw bytes, both no-primary decoded-expansion and already-committed OutputLimit cases, and the independent child-written record plus ESRCH reap oracle. Build and run inputs are unchanged between that GREEN and corrected attempt02 RED, so reusing the GREEN is valid. Attempt01's unconditional forced-panic RED is explicitly excluded from acceptance history.

Both scoped runners exited 0; attempt02 elapsed 21 seconds. Each recorded session-scope identity matched before/after and the exact empty scope was retired. No unrelated X35 result or process was touched.

The X35 review remains a separate accepted package and does not broaden this verdict.
