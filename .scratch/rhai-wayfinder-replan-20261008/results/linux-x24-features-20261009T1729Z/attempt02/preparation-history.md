# Preparation history

The first launch stopped during its preflight before invoking `run_scoped.py`, Cargo, or a test: the launch script called the non-executable Python runner directly with `--help` (exit 126). Its exact session scope was created by this launch, verified empty and retired. Workhorse showed no Cargo/rustc build. The launcher now invokes the same pinned runner through `/usr/bin/python3`; inputs, test assertion, profile, resource limits and planned run are unchanged. This was a launcher invocation error, not a product failure or test RED.

Before the attempt02 launcher correction, the read-only `rustc +1.77.2 --version` preflight caused rustup to auto-install the missing Workhorse 1.77.2 toolchain components. Rustup's output confirmed the expected Rust commit/date; the package runner later read back Rust1.77.2/Cargo1.77.2. The toolchain is left installed as useful owned environment preparation. This did not build or test the project.
