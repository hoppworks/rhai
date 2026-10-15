Attempt 01 classification (2026-10-15)

Runner status 0. lllm Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, features `testing-environ,sys,unchecked`, default profile. HEAD, test/product/lock hashes and capacity are recorded alongside the invocation.

The wrong-expectation control inverted only the final sentinel-liveness assertion. It exited 101 at that assertion after observing the managed leader, worker, and leaf absent and the sentinel live in its separately identified process group. Panic cleanup killed and reaped the exact sentinel. Restored test passed 1/1: nonfinal clone drop kept all managed members live; final drop reaped all three; the unrelated sentinel remained live until explicit cleanup, then its exact child was reaped. Cargo statuses were 101 and 0.

The scoped runtime and exact session scope are absent; no compiled build remains. Raw logs and statuses are in this directory.
