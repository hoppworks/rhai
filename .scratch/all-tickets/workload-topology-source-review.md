# Linux workload topology source gate

Runtime source: `fed0f173ac40f041a76803c9beecd5e74e407da0`.
Detached route: `8f5430f4c6ae868630767baa1329ad69beac18c1`.
Reviewed range starts at `282b075c35d073238dd2556424232c1f654079b6`.

All eleven changed paths reviewed: both Rust main files, controller, custodian,
process identity, native acceptance driver, both Python test modules, both new
shell route scripts and the responsible state. OCR range preview selects eight
source/script paths; its three excluded test/state paths were also read in full.
Coverage: eleven reviewed, zero skipped. Applicable Rust, Python and default
rules retrieved; no remaining blocking source finding identified in this range.
All four candidate commits have exact author and committer
`hoppworks <daniel@hoppworks.de>`; unpublished older child history is not approved
for import or push.

Resolved findings: managed child must retain original stdin; escaped holder must
be signaled before consuming its cleanup deadline; direct-child wait ownership
must follow subreaper adoption; pre-ACK failures must use the original unreaped
leader's pinned group and kernel-owned terminal-child waits. Post-ACK cleanup
signals the pinned group before querying adopted children, then independently
checks identities/parents and reaps. Normal success still requires leader exit0,
three fresh pending workers, bounded cancellation joins, live escaped pipe holder
through joins, exact SIGKILL wait statuses and unaffected sentinel.

This is a source gate, not runtime acceptance. Release staging/hash readback
only, then compare all fifteen staged inputs before releasing the single native
`topology-cancel` invocation. New exact stage:
`/root/rhai-linux-native-io-task/native-workload-topology-20261001-0700UTC`.
Runtime archive intentionally contains the frozen runtime source; external route
copies must match the route commit. Absolute launcher cutoff07:50UTC; invocation
at most600s, shared setup/build300s, case45s plus10s reserve, private1GiB/jobs2,
eight process resources including sampler, three Rust workers,32FD,2MiB streams.
No rerun or post-gate source change; preserve original history and stop criteria.

Source preparation began approximately06:26UTC; review reached07:09UTC with
concrete source corrections and zero native launches. Existing13-case Linux and
macOS I/O evidence applies unchanged to its original cases; this additional
case does not establish production Engine behavior, other OS topology or actual
workload topology interruption by TERM/KILL.

Runtime gate released after independent stage readback: all fifteen recorded
hashes matched fresh remote `sha256sum` and local frozen Git-object or configured
helper bytes. Exact results: `workload-topology-stage-readback.json`. One native
invocation authorized within the unchanged package; retain the stage for raw
acceptance and cleanup review. No runtime outcome is accepted by this release.

Attempt1 stopped at fixture compilation (E0308), with zero topology cases.
The raw compiler result disproved the prior source gate's type assumption;
no runtime requirement was accepted. Raw canonical export:
`../process-rust-io-followup-evidence/topology-attempt1-20261001-071148UTC/`;
all17 manifest entries and six ledger log hashes independently verified.

Follow-up immutable source gate07:19UTC: range8f5430f4..60dc01eb,
runtime archiveb7c725ccb3eeaa4dc9fd32e3df2cb18cd0242dd5,
detached route60dc01eb118858eb2975169888c6528ef65be66e.
All four OCR-selected paths reviewed, zero excluded/skipped, coverage100%.
The only runtime correction is `write_all(b"1")` (one-byte slice);
other changes give attempt2 its unique export/stage and archive parent.
Three new commits have exact lowercase author and committer. No source finding
remains in this correction range; no new build or runtime acceptance claimed.
Release staging only, then independent fifteen-input hash comparison before
exactly one finite attempt2 within unchanged safety limits and07:50 cutoff.

Attempt2 staged readback independently accepted: all15 hashes match frozen
local inputs, declared manifest and fresh remote sha256sum. Details in
workload-topology-attempt2-stage-readback.json. Runtime released07:20UTC
for exactly one invocation with unchanged limits; actual acceptance pending.
