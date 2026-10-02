# Darwin optional MSRV examples proof

Requirement: execute current sys/net documentation examples using optional MSRV
Rust1.77.2 through the real public Engine and independently check file/socket effects.
Source1ca21e32, Darwinarm64, compatible v3lock2ba4, exact helper/contract and
launch preconditions are identified in current-msrv-examples-review.md.

One integrated private Cargo build produced both examples. The sys script
writes `Rhai` over `existing data`; a fresh std::fs read observes `Rhaiting data`.
The net script connects to an OS-selected loopback endpoint; the independent
peer reads `ping` and returns `pong`, which the Engine script returns. The peer
is joined before assertion, and sys's owned temporary directory is dropped.

Intended wrong-expectation controls: sys-red101 with actual `Rhaiting data`
versus `deliberately wrong host contents`; net-red101 with actual ping bytes
versus wrong peer bytes. Both named assertion diagnostics are present in
original stderr. Unset seams/default frozen expectations: sys-green0,
net-green0 with exact independent readback outputs. Source bytes are restored;
binaries retain only the assertion expectation seam. No mocks or tracked source edits.

Original evidence at current-msrv-examples-evidence includes9commands with
argv/status/stdout/stderr, direct private rustc/cargo versions, seven manifests,
archive8251/lock2ba4, source restoration and cleanup. Independent root readback
checks those raw records against frozen Git bytes, exact expected commands,
intended panic diagnostics, samples and outerstatus0. See
current-msrv-examples-root-readback.json. Helper34.951s,49samples with observed
maxRSS794064KiB/storage754776KiB/descendants6, not continuous peaks.
Runtimeagent-build-ehwjvndb absent; exact empty owned scope retired.

Accepted only for current optional-MSRV examples on Darwinarm64. Native Linux/
Windows, feature behavior, process lifecycle, overhead, docs/API review and
full release acceptance remain open. Native process count84 unchanged.
