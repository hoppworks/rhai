# Current default core Rust 1.66 proof

Frozen source: `52d9797b250abcd29ca3d264be9aa0e42acd43bb`. Darwin arm64;
direct installed Rust/Cargo1.66.0; full manifests/workspace preserved. Exact
v3 lock differs from the previous accepted core lock only by adding the existing
libc package to Rhai's dependencies. This closes changed default-core
applicability after manifest/token changes, not the optional or release matrix.

| Package | Observed outcome | Classification |
| --- | --- | --- |
| 01 | Offline resolver missing toml_write index | No compilation; index setup boundary |
| 02 | Exact resolution succeeded; offline check missing ahash archive | No compilation; private archive-cache boundary |
| 03 | Online locked core check0; offline example missing byteorder archive | Default-library gate passed; Engine not executed |
| 04 | Check0, real Engine42, wrong43 assertion101, restored42 | Current default-core gate accepted |

Original logs/locks remain in core-current-msrv-evidence{,-02,-03,-04} and
outer logs; original old seven attempts remain unchanged in
../core-msrv-compatible-resolution/proof.md. Expert10's single bounded repair
is recorded in escalations/10-current-core-example-inputs{,.answer}.md.

Package04 uses the exact package03 lock, SHA256
2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425,
checking unchanged bytes after every command. It exports provenance before
builds; root independently recomputed frozen git-archive SHA256
995b2fd04724d6f67798e6e020cb07be1f4e112f508670788a023bf08ed07ee3.
Only private copied cache/index/source/home/target/tmp are used. Public registry
inputs are acquired by locked Cargo check/positive; wrong and restored controls
are offline in that same build. No installation, credentials, shared-cache or
configuration changes. Default Engine compilation rejects reserved spawn().

Root independently read original statuses and assertion text, verified lock
identity/provenance, 119 present locked-cache archive checksum rows (not all
used packages), resource samples and absence of every exact owned scope.
Receipt: core-current-msrv-root-readback.json. Outer terminal0; exact empty
scope retired. Package04 sampled maxima: storage978720KiB, RSS804096KiB,
descendants6. Samples are not continuous peaks or enforcement.

Each of four packages allocated540s helper/600s outer, jobs2, sampled2GiB
storage/RSS stops and16-descendant stop. Cumulative allocations2160s helper/
2400s outer; actual cumulative elapsed was not captured. No process measurement
or invocation85 was allocated. Optional1.77.2, other targets/platforms, full
features/workspace tests, unlocked dependency compatibility and remaining
process/Windows/release requirements remain unverified.
