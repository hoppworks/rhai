# Accepted Linux runnable examples — native example3

Scoped acceptance at frozen20d25ad8ed4483d4cd4079cf62c8481a629c00e3:
public Engine sys/net/sys_process examples, private Rust/Cargo1.77.2 on Linux
x86_64, compatible lock2ba4, features testing-environ,sys,net. One Cargo build0
and three intended wrong-expectation controls101 followed by correct runs0.
Original complete commands, tool output, source-lock bindings, restoration,
six raw outputs/status and resource observations are preserved in
process-example3-originals/stage-originals/proof-evidence/.

| Entry | Real OS effect and independent readback | Control |
| --- | --- | --- |
| sys | Script writes file; host fresh read sees Rhaiting data | Wrong host contents101; correct0 |
| net | Loopback script TCP; joined peer sees ping, script sees pong | Wrong peer bytes101; correct0 |
| sys_process | Self-executable run writes record/exits7; spawn atomic readiness, timed wait pending, fixture release, host completion record, all eight cloned-handle cached result fields agree | Expected exit8 vs7 fails101 after both records/cache markers; correct0 |

Combined independent review linux-process-example-review.md accepts actual
source, raw outcomes, launcher orchestration and cleanup. Launch3 allocated
2026-10-04T02:49:43Z on the140th checked empty-heavy observation; no expired
exception or foreign process/resource modification. Original source archive
SHA256e7a9a118bd29c05e8a70e284196837594fc97811f3d80688d17f55167008be93;
example SHA2564ef8c462221c237521a2554be4800b74852b3525e734fdbcab097e869fa12321.
All71 files/six directories match independently checked preservation inventory.
Raw tar SHA2564061bf5d3441d61e05aeb428bd69ca523d0966b229e5f1e51c90b05dd1d12756.
Reviewed collector immediately rechecks input/identity/group/runtime ownership
before exact retirement; original retirement-receipt.json confirms71files/six
dirs removed. Separate readback-process-example3-retirement.py and durable
process-example3-retirement-independent.json confirm102 original identities
absent/reused, groups3772732/3774195 empty and four exact paths absent.
Transient outer proc/3774192/stat disappearance retained verbatim; closure
is separately verified. No retained stage/runtime/scope/build remains.

About25seconds terminal duration;44 periodic samples observe923112KiB RSS,
743624KiB storage,7descendants (not continuous peaks). Bounds600/585/540seconds,
2Cargo jobs,16descendants,1572864KiB preemptive storage and2097152KiB hard
RSS/storage unchanged. Authorized Tauron terminal/cleanup notice delivered.

Root integration byte-compares all three files directly with20d Git blobs:
344-line process example, four-line Cargo declaration,22-line docs section.
Production/codegen/build script unchanged. Unaccepted492 stdin test lines are
excluded. Sys/net assertion instrumentation remains disposable proof-only.
A Git tracked-diff check listed the newly untracked example despite identical
working bytes; direct byte comparison resolves that local guard artifact.
Earlier phrase guard also stopped before writes; neither is a native failure.
No rebuild for unchanged proven inputs. Prior applicable proofs retained.

This closes only Linux MSRV runnable-example criteria in tickets03/06.
Non-Unix/no_float/full feature/platform matrix, stdin/post-spawn/drop-false,
performance and final release remain open. Native1/2 compiler history and one
pre-wrapper SSH quoting failure remain consumed; other stopped chains unchanged.
