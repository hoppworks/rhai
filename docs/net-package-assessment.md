# Optional `net` package: compatibility and behavior assessment

**Recommendation:** use the package as a reference for an optional TCP package,
but do not adopt it unchanged. Default builds work with this fork; reproduced Blob
defects and feature incompatibilities need to be resolved first.

This assessment evaluates the `rhai-net` source snapshot at commit [`59aa510a3d82bb8f4d60c62669df7d347cd3e3d4`](https://github.com/emesare/rhai-net/tree/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4). It combines source observations with build and behavioral diagnostics against Rhai commit `118745c6` (`1.26.1`), executed on macOS on 2026-09-30. No production API or dependencies are changed. The existing `sys` plan reserves networking for a separate optional package and separate feature, while deferring async/event-loop support ([sys plan, §1](sys-package-plan.md#1-goal-and-non-goals), [§6](sys-package-plan.md#6-phases)).

## Existing API inventory

The reference package is TCP-only. `NetworkingPackage` registers address and TCP modules; it exports `SocketAddr` address construction/accessors, TCP connect (address or string, with and without a millisecond timeout), listener bind and accept, stream shutdown, string and Blob reads, and string/Blob writes ([package registration](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/lib.rs#L13-L28), [address API](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/addr.rs#L8-L39), [TCP API](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/tcp.rs#L14-L237)). Its README describes the calls as blocking, and the `accept` docs say it blocks the engine thread ([README](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/README.md), [accept](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/tcp.rs#L36-L46)).

The reference manifest has an opt-in `no_index` flag and conditionally omits Blob APIs in source, but its feature declaration is `no_index = []`; it does not forward that feature to the Rhai dependency ([manifest](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/Cargo.toml#L13-L24), [Blob cfg](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/tcp.rs#L167-L169)). A new in-tree package should follow the host crate's feature convention and test the actual `no_index` combination; the host's `Array` and `Blob` aliases are unavailable under `no_index` ([Rhai aliases](../src/lib.rs#L308-L316)).

## Gaps and source-level observations

- **No authority/configuration surface is present in the reference.** The package constructor takes no policy object, and connect/listen accept arbitrary addresses. The `sys` package instead makes host-granted authority an explicit design concern ([sys config model](sys-package-plan.md#2-decisions)). A `net` package needs an owner decision on whether and how hosts restrict outbound destinations and inbound binds; this assessment does not choose that policy.
- **Address parsing is narrow and one overload casts the port.** `addr(raw)` parses a complete `SocketAddr`, so it accepts numeric IP socket addresses rather than a hostname form. `addr(ip, port)` casts `INT` to `u16` without a visible range check ([address source](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/addr.rs#L8-L20)). Existing address tests cover valid IPv4/IPv6 inputs only ([tests](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/tests/addr.rs#L6-L26)).
- **Read lengths and partial I/O need an explicit contract.** String/blob helpers allocate a buffer based on the requested `len` and engine maximum, then make one `Read::read` call except for the `read_to_end` branch. The string helper truncates to the returned count; the Blob helper returns the buffer after ignoring that count. The write helpers each call `Write::write` once and return its count ([read/write source](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/tcp.rs#L110-L165), [Blob source](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/tcp.rs#L171-L236)). These are observable implementation choices; positive reads are documented as “up to N bytes,” while finite engine limits change the documented zero-length read-to-EOF behavior into a single read. These distinctions are not pinned by the existing tests. The existing TCP tests exchange only short local payloads and assert the reported write count ([TCP tests](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/tests/tcp.rs#L10-L110)).
- **Bounds need careful treatment.** Positive read lengths are converted to `usize` and used for buffer sizing when the engine maximum is zero; the source does not visibly reject negative lengths before this conversion. With a nonzero engine maximum, allocation is capped by that maximum. `len == 0` has a distinct read-to-EOF or engine-limit path, documented as potentially blocking until peer close ([string length handling](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/tcp.rs#L110-L149), [Blob length handling](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/tcp.rs#L171-L207)). A future contract should define negative, zero, oversized, and short-read behavior before choosing implementation details.
- **Blocking calls have limited timeout coverage.** Only `tcp_connect` has a timeout overload. `accept`, stream reads, and writes are ordinary blocking calls, with no script-configured timeout surface in the inspected API ([TCP source](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/tcp.rs#L36-L87), [read/write source](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/tcp.rs#L98-L165)). This is consistent with the existing `sys` plan's async non-goal, but leaves potentially unbounded engine-thread blocking as an API decision ([sys plan, §1](sys-package-plan.md#1-goal-and-non-goals)).
- **Handle storage uses `Rc<RefCell<_>>`.** Both stream and listener aliases are local-thread shared mutable handles ([aliases](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/tcp.rs#L5-L18)). Rhai switches its `Shared` and `Locked` aliases between `Rc`/`RefCell` and `Arc`/`RwLock` with the `sync` feature ([Rhai aliases](../src/lib.rs#L280-L285)). The dependency-patched build fails with `rhai/sync`; an in-tree implementation should use the host aliases or explicitly constrain supported feature combinations.
- **Error mapping is string-based at the boundary.** Socket and I/O errors are converted to strings in the exported functions, rather than preserving structured operation/kind information ([TCP source](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/tcp.rs#L19-L23), [address source](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/addr.rs#L8-L20)). Whether a new package should reuse `SysError` or define a net-specific error type remains a contract choice.
- **Current tests are a smoke-test baseline, not a behavior matrix.** They cover valid address construction and two localhost TCP exchanges. The TCP tests bind fixed ports `8080` and `8081`, and the server-side test uses a spawned thread; there are no visible tests for port/address rejection, refusal/error handling, connect timeout, engine size limits, partial reads/writes, malformed UTF-8, Blob byte counts, sync/no_index feature builds, or permission policy ([address tests](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/tests/addr.rs#L6-L26), [TCP tests](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/tests/tcp.rs#L10-L110)). This describes visible coverage only; it does not assert that the APIs fail those cases.
- **Scope missing from this TCP package:** UDP, hostname resolution, TLS, HTTP, and async interfaces do not appear in its manifest or registered modules ([manifest](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/Cargo.toml), [registered modules](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/lib.rs#L23-L28)). These are capability gaps relative to a broader meaning of networking, not requirements for an initial package.

## Suggested small TDD slice

First resolve the four existing sys review findings and configure strict verification.
Networking then starts with the Blob read contract: adopt the reproduced short-read
and EOF regressions below, make them pass by returning only received bytes, then
verify engine limits and parity with string reads. The current helper ignores the
returned byte count ([source](https://github.com/emesare/rhai-net/blob/59aa510a3d82bb8f4d60c62669df7d347cd3e3d4/src/tcp.rs#L179-L205)).

Each new behavior starts with one failing public-API test, followed by implementation
and refactoring. This slice does not settle host authority, timeout defaults or
general input bounds. The script trust-boundary decision remains open.

Quality checks should fit the existing package/plugin architecture and MSRV: real
Engine-to-OS tests with independent read-back, isolated fixtures, Linux/macOS/Windows
checks and selected feature builds. Property tests can then cover parsing and integer
bounds; targeted mutation checks can confirm that regressions detect a removed
truncation or validation guard. These are proposed checks, not executed results.

## Executed checks

The reference's production source is unchanged. Its execution-copy manifest adds an
empty `[workspace]` to isolate it from the parent checkout. A command-line Cargo
patch points both normal and build dependencies at this Rhai worktree; Cargo resolved
one local `rhai` package. Subsequent assessment commits change only docs and workflow
instructions, so the evaluated production code remains at `118745c6`.

| Toolchain / features | Result | Cause or qualification |
|---|---|---|
| Rust 1.93.0 / default | Pass | `cargo check --tests`; two missing-documentation warnings |
| Rust 1.98.1 / default | Pass | Same warnings |
| Rust 1.98.1 / `no_index,rhai/no_index` | Pass | Both package and dependency features enabled |
| Rust 1.98.1 / `metadata` | Fail | Build script at `build.rs:129` decodes custom-type metadata as `DocFunc`: `missing field access` |
| Rust 1.98.1 / `rhai/sync` | Fail | `Rc<RefCell<TcpStream/TcpListener>>` lacks required `Send`/`Sync` |
| Rust 1.98.1 / `rhai/only_i32` | Fail | `Duration::from_millis` receives `u32`, requiring `u64` at `src/tcp.rs:73` |
| Rust 1.98.1 / `rhai/unchecked` | Fail | Engine size-limit getters are unavailable |

| Behavior check | Expected / observed | Result |
|---|---|---|
| Original address test | Valid IPv4 and IPv6 construction | 1 passed |
| Original `test_tcp` | Data exchange completes | Failed at peer shutdown: macOS `NotConnected`; peer thread panics |
| Original `test_tcp_server` | Client connects to ready listener | Failed with `ConnectionRefused`; listener readiness is not synchronized |
| Peer sends `ABC`, closes; `read_blob(10)` | Only received bytes; got `ABC` and seven zero bytes | Reproduced defect |
| Peer closes without data; `read_blob(10)` | Empty Blob; got ten zero bytes | Reproduced defect |
| `addr("127.0.0.1", -1)` | Proposed validation contract: reject; got port `65535` | Proposed contract fails |
| `addr("127.0.0.1", 65536)` | Proposed validation contract: reject; got port `0` | Proposed contract fails |
| Script writes `from Rhai`, shuts down | Independent Rust peer reads exactly nine bytes | Passed |

The [diagnostic harness](net-assessment/characterization.rs) intentionally produces
four failing assertions against the unchanged reference: two expose its documented
byte-read defect, two express proposed port-validation contracts. The passing write
test is a positive control. The harness is outside normal Rhai test targets; do not
add these failing diagnostics to this crate's CI.

The fixture binds `127.0.0.1:0` before connecting, uses bounded peer/socket waits,
joins its peer thread and uses an independent OS reader or writer. Its short-read
assertion accepts a nonempty prefix of the sent payload; it does not assume TCP
preserves write boundaries. Original TCP tests ran once after checking their fixed
ports were free. Failures were recorded without retries to obtain a green run.

No MSRV, Windows, Linux, `no_std`, wasm or exhaustive feature-matrix claim is made.
The host crate declares Rust 1.66.0; the sys plan declares a higher minimum for `sys`.
A networking package should define and verify its supported minimum without
incidentally raising the core crate's requirement.

These are build and behavioral diagnostics, not formal strict E2E acceptance.
At execution time `AGENTS.md` recorded `strict` but did not configure its required
tool, start command, test command and safe reset. No networking feature or fix is
claimed complete.

## Reproduction

Use a separate checkout of the pinned reference outside this workspace. Set
`RHAI_CHECKOUT` to the absolute path of this assessment branch and `NET_REFERENCE`
to the new reference checkout. Its production source must remain unchanged.

```sh
git clone https://github.com/emesare/rhai-net.git "$NET_REFERENCE"
git -C "$NET_REFERENCE" checkout 59aa510a3d82bb8f4d60c62669df7d347cd3e3d4
cp "$RHAI_CHECKOUT/docs/net-assessment/characterization.rs" "$NET_REFERENCE/tests/quality_characterization.rs"
cd "$NET_REFERENCE"
cargo +1.98.1 check --tests --config "patch.crates-io.rhai.path=\"$RHAI_CHECKOUT\""
cargo +1.98.1 test --test addr --config "patch.crates-io.rhai.path=\"$RHAI_CHECKOUT\""
cargo +1.98.1 test --test quality_characterization --config "patch.crates-io.rhai.path=\"$RHAI_CHECKOUT\"" -- --nocapture --test-threads=1
```

For feature checks, append the table's list with `--features`. The diagnostic target
intentionally exits nonzero until the implementation meets the asserted contracts.
Use an external deadline too: this assessment used a 60-second process-group deadline
per Cargo command. Original TCP tests require free ports 8080 and 8081.

Local logs, `compile-matrix.json`, `runtime-checks.json` and the execution checkout
with its dependency lockfile remain under `.scratch/stdlib-net-assessment/`. Scratch
artifacts are not pushed; the harness and commands are committed for reproduction.
Fresh dependency resolution can differ from the retained local lockfile.

## Reuse and attribution

The reference manifest declares `MIT OR Apache-2.0`, with both license files present.
Any copied or adapted implementation should retain the applicable license and
attribution. This assessment copies no production implementation code.
