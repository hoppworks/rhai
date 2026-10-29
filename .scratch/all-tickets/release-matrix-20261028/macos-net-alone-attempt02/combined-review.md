# Independent combined review: macOS Net fixture correction

Verdict: **PASS for the native macOS Rust/Cargo 1.77.2 `testing-environ,net` four-target slice** at fork-main `09cda922` plus the reviewed `tests/net_connect.rs` overlay. No actionable standards or specification finding remained.

The reviewer checked attempt01's actual `WouldBlock` at the IPv6 independent peer read, the narrow helper change that makes the accepted stream blocking while retaining two-second bounded reads and all assertions, and attempt02's source/archive/lock/toolchain pins. Attempt02's original logs show exact IPv6 peer bytes, EOF and denied-peer absence; the deliberate peer-EOF assertion fails with exit 101; the same `net_connect` executable then passes with the restored suite. Four targets pass 5/8/7/10, zero failed/ignored. Export hashes, outer/Cargo-clean exit 0 and exact owned stage/scope retirement check out.

The negative control covers the selected peer-EOF assertion. Pre-overlay Linux and Windows `net_connect` proof does not establish the changed helper at this candidate. Unaffected target evidence remains applicable; the full release matrix stays open.
