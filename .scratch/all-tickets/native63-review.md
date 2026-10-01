# Native63 immutable review

Reviewed commit: af18bb36a1cbe03563d67abebd1ee8a836922df4, fork task/process-unix-run.
Author and committer: hoppworks <daniel@hoppworks.de>; independent fork ref readback matches.

OCR delegate preview selected four files and excluded six by extension. All ten files are accounted for: the Python harness, shell wrapper, Unix production source and public integration test were reviewed against the source gate and actual raw native evidence; the state, raw evidence, log index, control log, integration log and unit log were reviewed manually. Review coverage: 10/10, no skipped files. The immutable production/test/harness/wrapper/raw blobs match their accepted frozen SHA-256 values.

No blocking correctness finding remains for the narrow Darwin natural-exit correction and post-cancellation capture closure. The fallback is restricted to WNOWAIT-confirmed natural leader exit and an exact, complete sole-leader group listing. Cancellation and ambiguous/extra-member listings retain errors. The public regression proves uncancelled observation waits remain pending while escapees hold pipes, then cancellation closes readers and preserves captured bytes/incomplete flags. Native omission control reaches the specific typed EPERM assertion; restored sys_process passes 24 tests and the outer Unix owner suite passes 12, including rejection shapes. Four source manifests match and exact runtime/process cleanup was independently checked.

Reporting limitation: the harness first-summary regex prints one nested unit test rather than the outer twelve. The complete raw terminal summary and named Darwin rejection test are authoritative; no test rerun is needed for this reporting discrepancy. Future harnesses should select the outer/last summary.

Integration scope: root main has not integrated the Unix process implementation ancestors (merge base c19e90d4b5be95f8598ec53dbcf497e09583f3eb). This is not an independent small main patch. Full ticket03/platform/MSRV/feature acceptance remains incomplete; this review does not authorize a broad GREEN claim. Retain the verified implementation on its fork branch while closing the remaining contracts, starting with direct and managed kill_on_drop:false lifetime.
