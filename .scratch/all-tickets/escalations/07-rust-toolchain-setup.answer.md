# Exact Rust 1.77.2 setup: separate artifact preparation from proof

## Recommendation

Keep the failed rustup-install route stopped. Prepare and retain the three checksum-verified official 1.77.2 Darwin component archives in a separately bounded, campaign-owned artifact package; consume those archives offline into a fresh scoped prefix for the frozen proof. Invoke the prefix's actual Cargo and compiler by absolute path. This removes rustup's combined network/install operation and repeated loss of completed downloads while preserving the exact compiler, Cargo distribution and test requirements.

This is a proposal, not an executed recovery or acceptance. This review performed zero payload transfers, installations, builds or tests. Do not rerun the existing 450-second `rustup toolchain install` case, substitute an installed compiler, or reopen cause06. The next action is source/harness preparation only.

## Facts and limits of the diagnosis

The brief and owner state record two setup windows, 180 and 450 seconds, cumulative 630 seconds, within invocations41/42. Both logs end at three-component download reporting. Samples of 72,960 and 224,236 KiB are whole-runtime observations, not component measurements or peaks. No exact toolchain, version execution or test assertion completed; both runtimes were removed. These facts do not identify transfer, decompression, filesystem work or installer internals as the cause.

The inspected harness supplies a fresh private `RUSTUP_HOME` and `CARGO_HOME` on each run and installs the toolchain before testing. Therefore subsequent runs cannot reuse the deleted runtime's partially downloaded artifacts. The source/lock overlays and the frozen test/control logic need no setup-related change.

On 2026-10-01 this review fetched only bounded metadata over HTTPS: the official version manifest (731,990 bytes), its checksum, and three HEAD responses. The manifest SHA-256 equals the published checksum:

`ed07e41edcba852ae034cd1fb29c9c62445c07cd9e12a61ae02a0027da80ded5`

Its date is `2024-04-09`; all three `aarch64-apple-darwin` targets are available. HEAD requests returned HTTP200 with the sizes below. Metadata reachability does not establish payload throughput or local installation success.

Official manifest: [channel-rust-1.77.2.toml](https://static.rust-lang.org/dist/channel-rust-1.77.2.toml), [checksum](https://static.rust-lang.org/dist/channel-rust-1.77.2.toml.sha256).

| Component archive, under https://static.rust-lang.org/dist/2024-04-09/ | HEAD bytes | Manifest xz SHA-256 |
| --- | ---: | --- |
| rustc-1.77.2-aarch64-apple-darwin.tar.xz | 56,737,656 | eb530841527f601da0c2354182a740d67c9fa1345011c73907ba66a497300bdb |
| cargo-1.77.2-aarch64-apple-darwin.tar.xz | 6,545,836 | e20eb22ffb465a2de9c1f775992a17a096119025a04f901e8dc62e356c29aea2 |
| rust-std-1.77.2-aarch64-apple-darwin.tar.xz | 24,007,460 | 2251b669682bb1e4290c488d58574ba1eb332c1558a185aa2e9a5711aeb69648 |

Total compressed payload is 87,290,952 bytes. The official manifest's Cargo package version field is `0.78.1 (e52e36006 2024-03-26)`; that is not a reason to reject the official `cargo-1.77.2` artifact or substitute Cargo. Require executed Cargo output beginning `cargo 1.77.2` and rustc output beginning `rustc 1.77.2`, plus rustc's verbose host `aarch64-apple-darwin`; retain the complete outputs. Treat version expectations as unverified until those commands execute.

## One next source/harness action

Prepare one source-only replacement setup block plus its small archive-preparation script. Freeze and review both before executing anything. Preserve the existing five source hashes, accepted/private lock logic, exact test names, wrong controls, source restoration, post-test manifests, jobs2, storage sampling and inherited process group. Change only how the toolchain is supplied and selected.

The preparation script must name the three immutable URLs/hashes above, bounded downloads, phase timing/status/byte logs and exact owned export path. It must never mark partial files usable. Publish a completed archive set and manifest to a fresh directory such as `.scratch/process-unix-run/evidence/toolchain-1.77.2-aarch64-apple-darwin.<unique>/` only after all three sizes and hashes match. Retain this one necessary input set; no global cache or Agent-home change. A failed preparation keeps bounded diagnostic logs, not a purported toolchain.

The proof setup must verify the retained archives again, copy them into its private runtime, extract/install each official component sequentially into `runtime/toolchain` using that artifact's reviewed `install.sh --prefix=<absolute-private-prefix> --disable-ldconfig`, and remove each temporary extraction after installation. Check the actual archived installer/options before execution; today's upstream template is guidance, not verification of the historical payload. Account for archives, extraction, prefix and target together under the existing runtime sample stop. Never install to `/usr/local`, alter global rustup, or use sudo.

Select `runtime/toolchain/bin/cargo` for every Cargo argv; set `RUSTC` and `RUSTDOC` to that prefix's actual executables and put its bin directory first in the private PATH. Remove inherited Rust tool/wrapper overrides that can redirect compilation, and set `RUSTUP_AUTO_INSTALL=0`. Run actual version/host checks before any test. Avoid a custom rustup link: custom toolchains missing Cargo can fall back to another installed release, so direct absolute executable selection is simpler to audit. Keep private `CARGO_HOME`, `RUSTUP_HOME`, source, lock, target and tmp.

Upstream sources: [release manifest/component layout](https://forge.rust-lang.org/infra/channel-layout.html), [installer prefix and ldconfig options](https://raw.githubusercontent.com/rust-lang/rust-installer/master/install-template.sh), [rustup custom-toolchain Cargo fallback](https://rust-lang.github.io/rustup/concepts/toolchains.html), [rustup environment controls](https://rust-lang.github.io/rustup/environment-variables.html). These support the route; they do not prove this machine's archived installer or native behavior.

## Finite resume and stop contract

The completed verified archive set is the resume condition for the offline proof. The Coordinator can adopt this distinct ordinary setup package under existing human setup authorization; this review itself has no execution allocation. Record the package before launch and preserve all prior cause/history and cumulative42. Do not reinterpret the prior no-third-rustup-download stop as permission to repeat that path. If there is a broader explicit human prohibition on any new payload procurement, retain the source-only preparation and wait for an already available verified archive set instead.

Proposed finite allocation, if adopted: one archive-preparation scoped invocation and one offline installation/proof scoped invocation, cumulative maximum44. Count each launch even on infrastructure failure; no automatic retry, fallback mirror or new advisory chain. Preparation: outer600s; sequential component transfers with at most180s each, aggregate transfer deadline450s, no retries, at most90,000,000 payload bytes, <=20s connection timeout, and logged failures/throughput. The tighter aggregate/outer deadline always wins; abort and clean on byte/hash mismatch or timeout. Export only the complete verified archive set before scoped cleanup. Partial transfer is not progress sufficient to relaunch.

Offline proof: outer600s, setup extraction/install/version aggregate deadline150s, then the existing case watchdogs bounded by the remaining outer time. Keep jobs2, inherited process group, private paths, unchanged2GiB policy and sampled1,572,864KiB stop in both invocations. These remain sampled storage checks, not a continuous peak guarantee. Do not assume the payload's expanded size from HEAD; stop if the actual runtime crosses the existing threshold. Export setup/test logs and necessary manifests before cleanup; independently read back absence of the exact runtime and all tracked attempt-owned processes.

Stop this route on the first procurement, install, version/host, storage, cleanup or unexpected test/control failure. Retain specific phase evidence and report the still-open requirement; no third same-cause correction or further Expert chain. A completed preparation is input readiness only. Acceptance still requires actual exact-version execution, every frozen intended test and wrong control, restoration/final manifest checks, and cleanup readback. The wider Unix/platform/ticket03 requirements remain open.

The actual external dependency is obtaining the official checksum-matching payloads, followed by any already-required Cargo dependency fetch into private CARGO_HOME. Only metadata availability was verified here; neither payload delivery nor the remaining600-second proof fit is established. This is a concrete bounded alternative, not a guarantee of completion and not a reason to block independent source-only work.
