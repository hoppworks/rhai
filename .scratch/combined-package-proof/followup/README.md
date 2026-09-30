# Combined sys/net bounded follow-up result

Source gate: `c2c76a1fac0ed48c5f7bae189c1eb0569ff7d756` (archive SHA-256 is recorded in `run-state.txt`). One approved invocation ran from 2026-09-30T18:16:06Z and stopped at 18:17:36Z with scoped status 89 when the fail-closed one-second `du -sk` sampler observed a transiently disappearing Cargo object during the f32 full-target compile. No retry was made.

The exact wrong-value control exited 101 as intended; the restored baseline and six non-f32 combined profiles passed. The f32 full eight-target row was launched but did not complete, so that requirement remains unverified. This is incomplete proof, not overall acceptance. The root reviewer independently read back cleanup: runtime absent, scoped group 71405 empty, launcher PID 71380 absent, and run_scoped PID 71400 absent. The finalizer nevertheless failed because 81 sampled identity rows (81 unique PIDs) had unavailable start identities; 35 unique PIDs had known start identities and read back absent. Individual process custody is therefore incomplete.

`case-status.tsv`, per-case logs/status files, `outer.log`, `process-identities.tsv`, `process-samples.tsv`, `storage-samples.tsv`, `environment.txt`, lock identities and `STOP-REASON.txt` are the exported raw evidence. The sibling `manifest.sha256` hashes these exported files and this note, excluding itself.
