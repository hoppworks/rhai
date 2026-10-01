# Native Linux I/O prototype acceptance

The fixed thirteen-case standalone Rust parent-I/O package is accepted on native Linux x86_64 with direct Rust/Cargo/rustdoc 1.77.2. This closes the Linux prototype requirement; public Engine process integration, Windows and workload-spawned escaped-descendant topology remain open.

## Source and execution

Source072e11f715d363435437d00727f8dd30e286632d, stage590b9c02b588b86db349e6918daa572c8179f9df; proofb8b2b73faee9a7cd11d85e006bb956a1c7f7d0bf and packaging correction282b075c35d073238dd2556424232c1f654079b6. Copy accepted five source files byte-identically without importing unpublished child history. Original source reviews and fourteen staged input hashes are retained in process-native-followup-stop-review.md and native-linux-stage-input-readback.json. Linux identity preflight records the real Darwin-only own-PID RED and six focused parser/unknown-state GREEN checks. Darwin behavior is unchanged; accepted macOS evidence remains applicable.

One detached launch at06:22:12UTC completed06:22:26UTC; wrapper0 and scoped-runner0. Dispatch06:08:39, initial preparation preserved, documented06:17 planning checkpoint extended review to06:48:39/cutoff06:38:39. Exactly one <=600s full13 invocation; actual build300s/case45s+10reserve/private1GiB/8processes/jobs2/threeRustworkers/32FD limits unchanged. Install8.067s/native build1.888s/fixture.114s. No rerun.

## Independent acceptance

Canonical export: ../process-rust-io-followup-evidence/linux1772-20261001-060839UTC/. Root checked all thirteen ordered receipts and finalizers, thirty-four ledger-linked hashes and all forty-four corrected manifest entries. Export metadata initially included an invalid empty-file self checksum; corrected manifest excludes itself, uses relative paths, and preserves every raw runtime byte. Validator and results: validate-native-linux-export.py, native-linux-independent-raw-check.json.

Normal stdin/stdout/stderr each exact2MiB and expected deterministic SHA; cancel/missing-wake exact bytes and three joined workers within1s, missing wake250ms wrong-state control. Eight output cases cover stdout/stderr N/N+1 at4096 and0 with exact captured prefix/hash,73728-byte stdin, first cause and end-state, readiness and held-output readback. Both protocol endpoints report actual131072-byte buffers against requested65536. Linux leader naturally exits before some cap snapshots; independent waitid record confirms status0 while anchor/sentinel and required holder remain live. This preserves the boundary and overflow acceptance rather than requiring an already exited leader to be live.

TERM15/KILL9 prove runner interruption and external custody, not worker joins. Every case has closed custodian FDs, live sentinel before cleanup, correct original identity finalizer outcomes. Fifty-one sampler children terminal/reaped0 and fifty-one valid resource samples; no sampler failure. Sampled maximum567,014,517bytes and8process resources; no continuous peak claim. Exported actual lockfiles and exact version logs independently match ledger.

Root queried native Linux /proc directly after completion: all80 distinct original PID/start identities absent, unknown0;55 recorded/source candidate groups empty, including33 groups actually observed by the live sampler; exact private runtime /tmp/agent-build-rf1abtjr absent. See native-linux-independent-cleanup.json. Source-derived candidate groups include short-lived groups not necessarily sampled; no observation claim for those. Remote stage retained until raw acceptance, then exact owned cleanup authorized separately.

This is a standalone prototype. External custodian-spawned pipe holders do not prove workload-spawned escaped descendants. Production public Engine/API and native Windows acceptance are not claimed.

Exact owned remote stage removed after raw acceptance. Independent root SSH readback confirmed stage and private runtime absent.
