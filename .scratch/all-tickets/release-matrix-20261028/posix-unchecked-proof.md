# Native POSIX combined `unchecked` profile — bounded acceptance slice

At fork-main base `2cc58ed009ed50dbeb609203decb90b517e8d404`, both native
macOS 27.2 arm64 and Workhorse Linux kernel 7.2.11 x86_64 ran Rust/Cargo
1.77.2 with `testing-environ,sys,net,unchecked` and lock SHA-256
`12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
The attempt64 manifest/archive bound 445 unchanged source files; the exact
current overlays were `tests/sys_process.rs`
(`cce4c03768a74cbb391fbc3369c4daf16b35a7f5a9b4eea071aca6b73a2ade31`),
`tests/serde.rs`
(`377d9d1c055085557aff1f9c5951978f58ea9211182d8d4f355730bcac0fc305`),
and `tests/net_reads.rs`
(`6e2ef50545fee75a39e3f9e9d6ee1fef52790b7e26b004699a218386b720e3f0`
in attempt 01; final corrected SHA-256
`6a8bb430ceef78277e2d884885f07510177bd41a54cc1f3c4f4b29543b6a2942`).
Both runners verified source hashes,
built from owned source copies, and scoped Cargo output/cache under
`AGENT_RUNTIME_DIR`. Exact scripts and raw command records are
`run-macos-unchecked.py`, `run-linux-unchecked.py`,
`macos-unchecked-attempt01/` and `linux-unchecked-attempt01/`; the focused
corrected follow-ups are in `macos-unchecked-attempt02/` and
`linux-unchecked-attempt02/` with their corresponding runner scripts.

Each OS compiled the same 11 integration targets with `cargo +1.77.2 test
--locked --features testing-environ,sys,net,unchecked --test ... --no-run`
(exit 0). Four exact expected-failure controls per OS exited 101 at their
intended assertions:

| Control | Independently observed actual value | Deliberately wrong expectation |
|---|---|---|
| Combined sys/net host readback | `filesystem-payload` | `incorrect filesystem expectation` |
| File handle capped first read | `abc` | `wrong expectation` |
| TCP host receive cap under `unchecked` | `ab` from peer-sent `abc` | `abc` |
| TCP Blob write peer readback | bytes `[0, 255, 65]` | `[0, 254, 65]` |

Restored 11-target execution then exited 0 on each OS. macOS passed 151
top-level tests with 1 ignored; Linux passed 160 with 3 ignored. `net_metadata`
compiled but ran zero tests because this profile omits `metadata`. The
`sys_fs` green target includes a negative-length file-read rejection and
unchanged file/cursor readback; the file wrong control calibrates the first
read's cap assertion, not the separate negative-length assertion. The
independent review found that attempt 01's one-shot TCP read could return
`ab` even without the host cap, so its net-cap wrong control did **not** prove
the cap caused the short result. The file and peer-write controls and other
unaffected target results remained applicable. Captured
nested child-harness `FAILED` lines in process tests are intentional negative
controls; the outer process target passed 49/0/1 on macOS and 59/0/3 on Linux.

The corrected test uses EOF-driven `read_to_end_string(8)` after the peer
writes all three bytes and shuts down its write half. It asks for eight bytes,
so a two-byte result under the configured host cap of two cannot be explained
by a single short TCP read: without that cap, it continues to `abc` and EOF.
Attempt 02 on each OS compiled the affected `net_reads` target, failed the
deliberately wrong expectation (actual `ab`, expected `abc`), then widened the
configured cap to eight in a known-broken-state control and failed the
unchanged assertion (actual `abc`, expected `ab`). Restored full `net_reads`
passed 7/7 on each OS in the same respective scoped run. The other two
overlays, product source, lock and feature profile were unchanged, so the
attempt 01 results outside `net_reads` remain applicable.
The combined independent Standards/Spec review and focused correction recheck
returned PASS for these named POSIX cases; the first one-shot cap result is
superseded and is not used to claim the corrected assertion.

Together these native paths support no bypass of the named host file/TCP
receive bounds under `unchecked`, plus independent TCP peer bytes and combined
package coexistence. They do not certify all possible bounds, Windows, other
features, core MSRV or full release acceptance. All four outer runner limits
were 1200 seconds; per-step limits and elapsed times are in the exported
`run.json`. All six attempt-01 and four attempt-02 step-log hashes were verified
on each OS. Each private runtime was removed; each exact session scope was
read back empty and retired. Owned Linux transfer and remote input/output
stages were removed only after export and hash verification. Foreign
resources were untouched.
