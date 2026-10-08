# Combined independent IPv6 review

Verdict: **ACCEPTED within scope**. No actionable standards, specification, oracle, source-binding or resource-ownership findings were found in the two owned IPv6 test additions and their original native Darwin arm64/Linux x86_64 Rust 1.77.2 evidence, for `net` and `net,sync,no_index` with `testing-environ`. This closes these two IPv6 regression rows on those platforms. Windows IPv6, the broader TCP matrix and release acceptance remain open.

This was a source and saved-evidence review only. No build, test, native fixture, cleanup, product edit, commit or external write was performed. Only this report and its manifest entry were written.

## Instructions and review boundary

Loaded the unchanged installed Wayfinder revision `f3fc5632f401156837ee3872f14fe33ccf1024ea`, resolving to `/Users/hoppworks/.local/share/mattpocock-skills/f3fc5632f401156837ee3872f14fe33ccf1024ea/wayfinder/SKILL.md` (SHA-256 `9be7b478c389605a24517d27752f278933588da97a1b5921b165f455edf4c5b7`). Read current project `AGENTS.md` (SHA-256 `06b73a9db5691ff5a0c5b34f98ce61e2c5df08e77161f3f93c3f7ce119d7c5de`), the current autonomous implementation plan (SHA-256 `abd684c30562a2adcdbd13a391ffad7676bccc792d7efeeec5ef35e957428ddf`), especially **TCP native closure**, and the approved TCP authority/lifecycle proposal. The old global agent-skills layer remained disabled and was not loaded. The owner's October 8 autonomous implementation authorization is reflected in the current plan.

Reviewed only the additions in `tests/net_connect.rs` and `tests/net_listen.rs`, relevant unchanged public registration/policy/socket lifetime code, `proof.md`, both inputs, owned patches, proof helper and payloads, original compiler/list/exact-test logs and command records, phase/source/executable records, export manifests, runner status and cleanup receipts. Prior accepted Unix/example packages were not reviewed again.

## Standards, specification and independent observations

The additions follow the existing integration-test layout and exercise registered public Rhai calls through real `Engine` instances. They retain the existing `net`/`no_object` gate and use string I/O that remains available under `no_index`. They require actual IPv6 loopback: an unavailable `[::1]` bind fails the row rather than substituting IPv4 or silently skipping it. No production implementation changed.

The connect selector holds an independent host listener at OS-selected `[::1]:0`. Default denial, a same-port IPv4 grant, an IPv6 grant for a different port, and a listen-only grant for the exact endpoint all produce catchable `Denied`/`connect` results. A nonblocking accept then independently observes no queued peer. An exact IPv6 connect grant writes the nine bytes `ipv6-peer`; the host verifies its actual local endpoint, an IPv6 peer, the complete bytes and subsequent EOF. The negative control and positive connection use the same still-owned listener. Reviewed policy checks compare the numeric `SocketAddr` against the connect vector before reservation or OS connection.

The listen selector checks default denial, an outgoing grant at `[::1]:1`, IPv4 port-zero authority and IPv6 port-one authority against `listen("::1", 0)`. The exact `[::1]:0` listen grant succeeds. The reported endpoint has IPv6 loopback and a real nonzero OS-selected port; an independent host client connects, and the script's accepted peer address equals that client's actual local address. The client receives all eleven bytes `ipv6-listen`, then EOF. A fresh bounded connection returns `ConnectionRefused` after public listener close. The unchanged listener policy checks its separate exact listen vector before reservation or bind. The listener negative rows establish the listed denials; they do not claim an additional outgoing-port-zero grant control.

The close oracle is appropriate: EOF observes the stream, while fresh refusal observes listener closure. It does not infer listener ownership from an immediate rebind, which can be affected by an accepted connection's TIME_WAIT state.

Fixtures own only loopback sockets at OS-selected ports. Readiness follows successful bind/connect and bounded accept, with no fixture sleeps. Host accept and socket reads/connects have two-second limits; script accept requests 500 ms, and package connect/write retain finite five-second ceilings. Each selected test has a 15-second helper limit. There are no fixture threads or spawned children to join/reap within the selectors. Rust socket and Engine/scope ownership releases handles on assertion unwind, including the intentional RED failures; reviewed shared stream/listener `Drop` paths take their owned socket and release quota. Private compiler/test descendants remain under the recorded scoped runner, with isolated source, target and Cargo cache and two Cargo jobs; compilation commands have finite 600-second helper limits, and the Linux launcher supplies a 1200-second runner limit.

## Original RED/GREEN evidence and input binding

The accepted source archive is byte-for-byte the Git archive of `ef423a516617e128835d54af16d75f559b2b1bce`, SHA-256 `635a59827900b02ad82b0e53499f6b3fb2a5c5233326cac541c88c3e8b61265f`. Both platforms use the identical owned patch `e3bd8ba871f2f8e8c22be49544cdf59572d33402a3c778cf7c4d22b7137f426a`, accepted lock `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, and proof helper `11b5086e4fba894622406489b5812dc72cad51722a935c199de9451c905ee76e`. Platform inputs differ only in the archive location and Linux platform label. Linux payload explicitly pins cargo/rustc/rustdoc to `/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin`; Darwin command records select `+1.77.2`. Original environment records identify Rust/Cargo 1.77.2 and the native OS/architecture.

Independently reconstructed each private RED mutation from the current source. It replaces only the unique host byte expectation in that named function, leaving the script payload unchanged:

| Target | Restored GREEN source SHA-256 | Wrong-expectation RED source SHA-256 |
| --- | --- | --- |
| `net_connect` | `4d03943e8625cf08247068aa24b72bf87d3c505dfd4957634ed5f132a02356f4` | `5ddbdc353163a702f00c739a09488772b3d1f0d2924a33196552e01d4f46a47c` |
| `net_listen` | `c452d9625eb665dd7caee4ab185debeb71033cb30eeeecccc680061815995515` | `227bb6df67c6cdc85b1e8a72bcb95a5bc828f0f1e898cb5d59343ed21187aa16` |

These hashes match all phase rows and final restoration records on both platforms. The current owned file hashes match GREEN, and the exact current two-file diff matches `owned.patch`. At current fork head `8aba115b85f4ccfd46d4beddb73ddd7a0c2a7265`, committed non-evidence changes since the archive base are confined to the previously reviewed Unix example/test and their sys plan documentation. There is no net/backend, Cargo configuration, build-script or tracked lock drift; current relevant working changes are exactly the two owned net tests. The accepted lock is explicitly installed in each private source copy; there is no working-tree lockfile to incorporate accidentally.

Inspected all eight original compilation records, sixteen list records and sixteen direct exact-test executions. Every compile succeeds with `--locked`, the recorded profile and both test targets. Each phase's target executable is a fresh compiler artifact (`fresh: false`), its list contains the requested selector exactly once, and the direct command uses that artifact with `--exact --nocapture --test-threads=1`. Every RED has exit 101, exactly one failed selected test and the intended byte assertion: actual `ipv6-peer` versus `wrongpeer`, or actual `ipv6-listen` versus `wronglisten`. Every restored GREEN has exit 0 and exactly one passing selected test. Same-profile RED/GREEN executable digests differ, and each recorded source hash matches its intended phase.

The original GREEN readbacks are:

| Native platform | Profile | Connect endpoint | Listen endpoint | Both selectors, RED / GREEN |
| --- | --- | --- | --- | --- |
| Darwin arm64 | `net` | `[::1]:65461` | `[::1]:65463` | `101 / 0` |
| Darwin arm64 | `net,sync,no_index` | `[::1]:65475` | `[::1]:65477` | `101 / 0` |
| Linux x86_64 | `net` | `[::1]:41743` | `[::1]:44353` | `101 / 0` |
| Linux x86_64 | `net,sync,no_index` | `[::1]:37817` | `[::1]:45729` | `101 / 0` |

All connect readbacks occur after peer absence, exact-byte and EOF assertions. All listen readbacks occur after actual peer-identity, exact-byte, EOF and closed-listener-refusal assertions. These are original logs, not regenerated runs or the aggregate `accepted` flag alone.

## Evidence preservation, cleanup and foreign exclusion

Independently verified all 71 original Darwin manifest entries, all 77 Linux manifest entries, and all 71 Linux remote-export hashes against retained local bytes. Both runner statuses are zero with empty runner stderr; Linux's original SSH launch status is also zero. All original command/log/result/cleanup files remain readable. This report is added to the Darwin manifest without changing the 71 original entries; the Linux manifest/export receipts remain unchanged.

Darwin cleanup identifies outer scope `/Users/hoppworks/.local/share/agent-builds/rhai/ipv6-n2he8tjp` by device `16777234`, inode `226106836`, uid `501`, and runtime `agent-build-h1uzdcwo` by device `16777234`, inode `226106841`. The receipt matches `scope.json`, records runtime and exact outer-scope absence, and a fresh read-only local check confirms both paths are absent.

Linux cleanup identifies `/root/.local/share/agent-builds/rhai/ipv6-26e70d5b06` by device `58`, inode `117295393`, uid `0`, and runtime `agent-build-nybly4ni` by device `58`, inode `117295409`. Its exported original receipt matches the recorded scope and reports both absent after retirement. That remote absence is accepted from the preserved native receipt; no new remote probe or cleanup was performed for this review.

The owned patch contains only the two net test files. The build archive's committed shared process fixture has SHA-256 `1faf45c57a4fefeaa05683043e064d3485e892887986fef749bedc974230b217`, distinct from the foreign dirty fixture `14a0808a8a5735d8f141ca1533d638d7b460392332d0021793f08da5b92c4fc2`. That foreign delta was neither copied into the owned patch nor modified during this review. No shared service, parent environment or foreign resource was changed.

The available evidence supports the scoped verdict above without repeating accepted runs. It does not close other TCP contracts, unexecuted native Windows rows or the integrated release gate.
