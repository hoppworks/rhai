# Darwin stdin run: preflight attempt 01

The first scoped-runner start stopped before source staging and before Cargo. The launcher assumed a root `Cargo.lock`, but this repository ignores that generated file and it was absent at invocation. No build, test executable, or fixture started. The exact new session scope was created for the runner and retired empty afterward. Runner exit status: 1.

Recovery: reuse the already accepted `Cargo.lock.accepted` from `linux-stdin-closure110-evidence/original-export/`, verify its recorded SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, and confirm `Cargo.toml` is unchanged since the baseline source revision. This preserves the existing dependency resolution without regenerating or changing a lock.
