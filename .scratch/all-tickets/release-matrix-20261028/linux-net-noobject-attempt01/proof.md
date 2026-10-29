# Native Linux Rust 1.77.2 Net `no_object` gate

Status: **the three `testing-environ,net,no_object` public script integration cases passed** on workhorse Linux x86_64. Independent combined review is recorded separately. Other platform/feature rows and the full release remain open.

## Binding and bounded execution

- [Preflight](preflight.json) compared all 448 source files in the reused immutable [archive](../macos-net-alone-attempt02/proof.md) against current fork-main `4ae12a438684c89496eac603df90d668441c33b1`: zero mismatches. Archive SHA-256 `6ff82b95cbbf65ba919161932a63d74f668f8e6e6d88682418797eca93565384`, manifest `b829308ab356d7aaaf7bf8d3acc9f65aab8fb316192d9b1b69e3365d78c834fd`, exact lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`. Remote input hashes matched before execution and are preserved in [export hashes](remote-export.sha256).
- [Launch](launch.sh) checked an absent unique owned scope, runner/source/lock hashes and 4 GiB free space. The existing POSIX runner SHA-256 `25d42cec...` bounded the invocation to 600 seconds with `TMPDIR` set to the absolute owned scope. [Run script](run.py) verified every archive member and copied source/lock inside `AGENT_RUNTIME_DIR`; Cargo home/target stayed private. It selected Rust/Cargo 1.77.2, set two build jobs, disabled incremental/debug and compiler wrappers, and ran `--locked` from that source directory. No foreign build or process was interrupted.

## Actual result and custody

- [Commands](commands.json) show `--no-run` exit 0, named wrong-peer test exit 101, and restored full dedicated suite exit 0. [RED](wrong-peer.log) failed at the deliberate independent peer byte assertion: actual `ping`, expected `pang`. [GREEN](suite.log) passed stream, listener and structured error getters (3/3) through the public Engine and registered NetPackage with real local TCP peers. [Readback](readback.json) verifies the same compiled executable for compile, RED and GREEN and validates every exported original against its remote hash. The control tests the stream-peer assertion; it does not establish sensitivity of every assertion.
- Outer runner status was 0. The own runtime/scope ended, and after export and hash verification the exact 14-file owned stage was removed. A separate [host readback](cleanup-readback.txt) found both stage and scope absent. The original logs and remote hash list remain in this proof folder; immutable source archive/lock remain in the earlier proof folder. [Combined review](combined-review.md) scopes acceptance to these three native Linux cases.
