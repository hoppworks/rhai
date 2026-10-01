# Linux workload-created topology proof review

Accepted standalone Linux `topology-cancel` requirement; public Engine/process API, native macOS topology, Windows supervision and release remain open. No fourth native run was used or authorized.

## Actual evidence

One attempt3 invocation launched07:33:23UTC, elapsed9.84s. Both Rust1.77.2 builds exited0. The native driver stopped on `KeyError('worker_joins')` after exporting the completed actual receipt; its cases=[] and wrapper/status1 are preserved. Canonical raw: ../process-rust-io-followup-evidence/topology-attempt3-20261001-073406UTC/.

The workload leader created a managed child, which created a grandchild sharing its original group and session before escaping into its own group. Exact PID/start, PPID, PGID and SID snapshots identify all three. Leader exit0 and managed-child subreaper adoption were observed before cancellation. All three Rust workers were active/pending; native_io records3started/3joined and0ms wake-to-join. The escaped grandchild remained live through worker joins, retaining output pipes. Afterwards the custodian signalled the managed group and exactly signalled the adopted escaped grandchild; child and grandchild SIGKILL wait statuses prove reaping, while the independent sentinel remained live. Runner exited0; no custodian error, descriptors closed.

Root independently reconstructed stdout1MiB patterni%256, stderr1MiB xor0xA5 and stdin1,114,112bytes pattern; all3SHA256 and both64byte prefixes match. Root24manifest entries and6ledger log hashes match. Fresh SSH readback07:41:46UTC checked13original PID/start identities absent with8candidate process groups empty and exact runtime absent; see workload-topology-attempt3-cleanup.json. All40sampler children terminal0. Sampled maximum565,753,897bytes/5resources is an observation, not a continuous peak. Native cumulative attempt1–3 elapsed29.268s; history retained, no allocation reset.

## Assertion repair and controls

Immutable range92e16447..1b684db5:2changed files fully reviewed, zero skipped/findings. OCR excludes both scratch paths by default; Python rules retrieved explicitly, test and state read in full. Canonical native_io case, exact-int worker-start/join counts3 and latency0..1000ms replace the nonexistent duplicate workload_topology.worker_joins. All prior lineage, liveness, signal, reaping and sentinel checks remain. Synthetic duplicate removed; focused incomplete/late joins regression added.

Scoped pure-Python replay reads the unchanged actual receipt SHA256e545dafd06694258e3342a7d9cb9a96e29097341330b6a21ef2df93d6479351e. Old assertion reproduced KeyError; fixed assertion passed. Actual-copy workers_joined2, wake1001ms and wrong pre-escape SID each failed AssertionError. Receipt/identity tests11passed. Root read full replay script/log, verified source SHA113a7d85333045d89f905df31b594e0d12b7781da24e72b9b521d3239bf545e6 and runtime absence. Replay preserved ../process-rust-io-followup-evidence/topology-receipt-replay-20261001-074056UTC/. Raw native receipts were not edited and no build/fixture rerun occurred.

Ten source/script/test paths copied byte-identically from final child1b684db5; older child history, README, proof-contract and responsible state not imported. Earlier full runtime source review and15-input staged hash gate apply to the actual unchanged native sources; only receipt verification changed afterwards. Existing13case proof remains scoped to its unchanged original binaries/cases. This closes only Linux standalone workload-created topology cooperative cancellation; direct production supervision and actual-topology TERM/KILL/platform coverage are not proven.
