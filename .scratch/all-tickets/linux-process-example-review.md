# Process example combined independent review

## Verdict

**NOT READY for native execution preparation** at `012e20f70dbef81fe08954af96459e59a03d1caf`, compared with `2518238beae7ade7e59f5abd7edf1ce209a4c2e3`. Consolidate the two material findings below into one repair. This is a distinct example package; the stopped stdin classifier and its consumed Expert18 follow-up remain stopped, with no reset, allocation, or acceptance.

Applicable agent-skills revision independently confirmed unchanged: `faba3db3bef6891ad2c0b20d434963bb8fe9572d`. Named Expert review; campaign, e2e-proof and ocr-delegate instructions retained. No Cargo, native run, SSH, staging, push, source edits or runtime cleanup occurred. Preparation review is not compilation or OS acceptance.

## Material findings

1. **Readiness publication races the host reader** — `examples/sys_process.rs:64`, `:214`. The child uses `fs::write(spawn-ready.txt, ...)`, which creates/truncates the final path before writing the PID. The parent treats `is_file()` as complete publication and immediately reads/parses it once. A legitimate schedule lets the host read an empty or partial record, so a correct API run can fail before the intended pending-wait/RED assertion. Publish a complete record atomically (write a separate owned path, then rename), or poll complete validated content under the existing deadline with explicit I/O handling. Preserve exact child-ID validation, the release gate, and the meaningful pending-wait assertion. A lightweight local filesystem model independently observed `is_file() == true` with empty contents while the writer had opened the file but had not written its bytes; this is a model of the actual ordering, not native reproduction.

2. **Scoped runner has the wrong bound and races the outer deadline** — `launch-linux-current-msrv-examples.sh:59`, `:81` versus contract's 585-second scoped bound. The launcher prints `runner_timeout_seconds=600` and passes `run_scoped.py --timeout 600`, while its own wait limit is also 600 seconds measured before runner startup. At the outer limit it explicitly leaves the runner and scope for later readback. The contract instead requires 600 outer / 585 scoped / 540 helper including restoration/export/cleanup. Use the promised 585-second runner bound and leave finite outer time for exit, group/readback and scope cleanup; preserve failure/partial evidence if that margin is exhausted. The helper's 540-second deadline is cooperative: export checks between files, not during a `copy2`/`copytree` operation. Do not describe that as an independently enforced per-copy hard limit; retain the enclosing runner limit and honest partial-export failure handling.

## Coverage and reasoning

All seven changed files reviewed. OCR deterministic preview selected five code/manifest/script files and excluded the two Markdown files as `unsupported_ext`; both Markdown files were explicitly included in rule resolution and manually reviewed. Reviewable coverage is 7/7 (100%), skipped 0. `OCR_NO_UPDATE=1` used; no installation/update. Preview/rules covered correctness, manifest/feature compatibility, ownership/error handling, concurrency, resources, boundary checks and testing. No extra specialist pipeline was created.

The production public API was read only where needed: Unix `run` returns the text map; `spawn` returns `Child`; `child.id` is a property; floating-point `wait(0.0)` returns UNIT while pending and a text map when terminal; cloned handles share the lease/cache. Default scope is DirectChild and kill-on-drop is enabled. No production or test change occurs in this package. The example intentionally launches only its own absolute executable through `ProgramPolicy::AllowList`, clears the child environment to the two fixture values, uses finite release/wait deadlines, checks nonzero exit as data, success/completion/timeout flags and captured text, compares repeated maps, and reads child-created records through host filesystem calls.

The cleanup guard is installed immediately after successful spawn and inexpensive clone/path operations. Unwind writes release, requests kill and polls bounded wait; the fixture independently stops waiting after five seconds, and package-owned lease/service cleanup remains responsible for reap on error. Its `Err(_) => return` is not proof of terminal success; the example does not emit such a claim. Happy-path terminal waits precede setting `finished`. Temp-directory removal errors are ignored by the example but the helper explicitly rejects matching leftover directories in its private TMPDIR. Launcher readback checks recorded helper/supervisor/command PID-start identities and scoped groups, then removes only the empty exact scope. These are preparation safeguards, not observed child/host cleanup receipts. Actual failure and happy paths remain unverified.

Cargo's `sys` example requirement matches the package feature gate; `sys` requires std/object-map support and is incompatible with no_std/no_object/WASM. The docs honestly limit this runnable example to Unix with floating-point support. The non-Unix main only prints an unsupported message; its successful exit cannot satisfy process acceptance. The recipe's supported profile `testing-environ,sys,net` on Linux x86_64/private Rust 1.77.2 excludes no_float. No Darwin, Windows or all-feature acceptance is claimed.

The new stage/scope/proof destination are distinct from historical sys/net locations. Their old evidence is not written by these scripts or asserted to cover the process example. Source/archive/lock/helper pins are consistent with the reviewed package and source `c0d0afd63383065783794337749289ffd5831722`. The stage script hashes transferred files into its manifest and validates source/lock/runner/helper fixed pins; independent prelaunch comparison of every recipe byte to this frozen review is still required, because a self-generated manifest alone does not bind edited working-tree recipes to this commit.

The helper builds all three binaries once with locked Cargo/private toolchain/homes, jobs=2 and explicit runtime target/output paths. Sys/net assertion instrumentation is confined to the private source copy, unique anchors and original byte hashes are checked, and those files are restored before runs and again in finally. Process source remains unmodified. Six result rows distinguish intended status101 assertion controls from status0 positives. For process RED, changing only expected exit8 retains all earlier real behavior assertions before the named failure; GREEN omits that override. Provided the two blockers are fixed and actual receipts validate, this same-build pair plus host record readbacks can prove the exact example criterion. It cannot prove strict release acceptance or unrelated lifecycle guarantees.

Resources are sampled at one-second intervals during commands: descendants16, storage preempt1572864KiB/hard2097152KiB, RSS2097152KiB. Samples are honestly labelled sampled maxima. Setup/build commands use the work deadline510 and export reserve30. Finally records failures/restoration and attempts original stage export to the separate proof destination; an existing/partial proof destination is preserved, not overwritten. Export errors fail the invocation. The recipe does not itself perform local independent custody export or delete its retained stage; a later independent collector must preserve originals, compare inventory/hashes, read back exact process/group/runtime/scope absence and only then retire owned stage resources. Such readback remains an acceptance obligation, not evidence supplied here.

## Lightweight checks (modeled/structural only)

Python AST parsing and both Bash syntax checks passed. Independently executed the actual `verify_pass`/`verify_control` function bodies with bounded in-memory inputs: source-shaped process GREEN marker strings passed, nonzero GREEN and missing output rejected; intended101/named/left7/right8 passed, wrong status and missing diagnostics rejected. The Rust Debug newline spelling used by the helper matches the source-shaped stdout model. These checks do not compile Rust or establish OS behavior, toolchain installation, command custody or cleanup.

## Frozen identities

Accepted source archive SHA256: `d75e7b83289081ad95c097763ac93c55520815bb5ea20a2079834ad137fecd7e`; lock SHA256: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. Parent independently reproduced archive identity; this review does not convert that into executable evidence.

| Frozen file | SHA256 |
|---|---|
| Cargo.toml | cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e |
| docs/sys-process.md | bb26ebc50169a06b01fbe6ddc7f03560eb4c3b8c3a3924cae71dcd889af079f7 |
| examples/sys_process.rs | 520aefeef3857c7f6763b752438d9c3ea6db495f369178bd7dcbd4d85afd2640 |
| check-linux-current-msrv-examples.py | c0c80653674feda4d3834a202d5f23585d46b461cdccc9f517c3f6febe7d2544 |
| launch-linux-current-msrv-examples.sh | a2892f29e42ee456c4d2ca6e88944e0da1f69d8dbdff2a5512fe220401c4456a |
| stage-linux-current-msrv-examples.sh | 570af5413b0f2d6faf56e655a89bbfc8e886e20139868053bad86fbebcf487e5 |
| linux-sys-process-example-contract.md | 410055e2de6d9b856ab1a53f0fd07153c87369849bca11291f8753402d4c993c |
