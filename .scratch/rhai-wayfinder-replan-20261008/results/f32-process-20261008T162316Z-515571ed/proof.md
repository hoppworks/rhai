# Native f32 process duration and host-bound proof

Scope: one new public Engine/real-OS contract on Darwin arm64 and Linux x86_64,
Rust1.77.2, `testing-environ,sys,net,f32_float`. Windows, other profiles and the
remaining process lifecycle/whole A–F package are not accepted by these rows.

The engine permits exactly `/bin/sh` and caps each output stream at four bytes.
Five invalid f32 values (NaN, positive/negative infinity, -0.5, FLOAT::MAX) must
return typed Denied before any child record exists. The finite fractional0.5
option runs an actual child; an independent host read verifies its PID/exit record
and ESRCH after reaping. Success reports exact stdout `ok`, empty stderr, code0,
complete streams, no timeout. A second child emits `abcde`; the script requests
4096 bytes, but the host cap retains exactly `abcd` and OutputLimit stays primary
with incomplete output. This is real process output, not a constructed report.

The isolated RED mutates only the finite-success expected code0 to9, after the
independent child record/reap check. Both platforms compile/list the exact unique
selector, execute it, exit101 at the matching equality assertion (actual0,
expected9), and report one failed test. Restore byte-identical GREEN source,
rebuild in the same owned scope, and execute the same selector: exit0, one passed,
zero ignored. Original compiler, list, stdout, stderr and status records are kept.
The helper parses exit status, assertion and summary separately with explicit cwd.

Both original result.json files contain identical nine source bindings and the
accepted v3 lock. Frozen ef423 archive plus owned committed patch through733529434
and the explicit test overlay supply the sources. Current main31d361543 adds only
the already included INT signal assertion cast and proof; these relevant process
inputs remain unchanged. The foreign dirty shared fixture was excluded; both
builds used the committed fixture SHA1faf45c57a4fefeaa05683043e064d3485e892887986fef749bedc974230b217.
Current GREEN test SHA86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41.
No production process code changed for this package.

Each platform used one finite900-second private run_scoped scope, two Cargo jobs,
private source/target/cache, --locked, cleared compiler override flags and explicit
native toolchain paths. Original evidence was exported before exact runtime and
identity-checked empty outer-scope retirement. Darwin final size1041764352 and
Linux1317896192 bytes are final samples below8GiB, not continuous quota claims.
Linux launch rechecked absent Cargo/rustc and adequate current memory/disk, and its
21.20-second runner ended0. Independent export readback matched32 remote originals
by exact size and SHA256. Cleanup receipts state runtime/scope absence; they are
not substitutes for the child lifecycle assertions or full interruption controls.

Combined independent review ACCEPTED the two named native rows; existing report:
`../unix-wait-20261008T131127Z-3fcea4ec/attempt03/review.md`, SHA
`e8a291fdfcbbc8e8a70408f18baca258cc199c594412fe361b265c384f8588c5`.
Historical actual X31 Condvar-entry rows remain applicable; the new before-call
fixture restriction does not erase their accepted proof. Exact remote immutable
export root was retired only after all32 originals were independently exported,
hash-checked and confirmed terminal; retirement receipt is retained locally.
